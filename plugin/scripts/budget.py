"""The instruction budget: refuses an instruction file that outgrows what Claude Code reads, or that points outside the
repository.

    python -I scripts/budget.py [--repo <path>]

Checks, with the limits from defaults.json laid over by the repository's .claude/bowline.json:
- every CLAUDE.md (the root and any nested one) is under the line target;
- every rules file under .claude/rules/ is under the line target and the per-file character cutoff;
- the scoped rules that load together for one area (the first folder of a rule's `paths:` glob, or its file type for
  a glob such as **/*.ps1) stay under the area budget together, and the unscoped rules, which load in every session,
  under theirs;
- every SKILL.md is under its line target;
- no instruction file names a path outside the repository (a scratch or temp folder, a home folder, a memory note).
Exit codes: 0 within budget, 1 something is over (each problem printed), 2 the script could not run.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def outside_pattern(config):
    parts = config.get("outsidePaths") or []
    return re.compile("|".join(f"(?:{p})" for p in parts), re.IGNORECASE) if parts else None


def paths_of(text):
    """The globs in a rules file's front matter, or [] when it has none (an unscoped rule)."""
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end < 0:
        return []
    front = text[3:end]
    globs = re.findall(r'^\s*-\s*"?([^"\n]+?)"?\s*$', front, re.MULTILINE)
    if not globs:
        inline = re.search(r"paths:\s*(.+)", front)
        if inline:
            globs = [g.strip().strip('"') for g in inline.group(1).strip("[]").split(",") if g.strip()]
    return globs


def area_of(glob):
    """The area a glob loads for: its first folder, the file type for **/*.ext, or None for everywhere."""
    parts = glob.replace("\\", "/").lstrip("./").split("/")
    first = parts[0]
    if not first.startswith("*"):
        return first
    last = parts[-1]
    if last.startswith("*.") and len(last) > 2:
        return last
    return None


def measure(root, config):
    """Measures the instruction files and returns (findings, facts) where facts hold the sizes for the doctor."""
    limits = config["limits"]
    outside = outside_pattern(config)
    rules_dir = config.get("rulesDir", ".claude/rules").replace("\\", "/")
    skills_dirs = config.get("skillsDir", ".claude/skills")
    if isinstance(skills_dirs, str):
        skills_dirs = [skills_dirs]
    if os.path.isdir(os.path.join(root, ".claude-plugin")) or os.path.isdir(os.path.join(root, "skills")):
        skills_dirs = list(skills_dirs) + ["skills"]       # a plugin repository's own skills count too
    findings = []
    facts = {"claudeMd": [], "rules": [], "areas": {}, "unscoped": 0, "skills": []}

    for path in common.tracked_files(root, "*CLAUDE.md"):
        if os.path.basename(path) != "CLAUDE.md":
            continue        # Claude Code loads files named exactly CLAUDE.md; a template or a note named like one is not read
        text = common.read_text(os.path.join(root, path))
        lines = common.count_lines(text)
        facts["claudeMd"].append((path, lines, len(text)))
        if lines >= limits["claudeMdLines"]:
            findings.append(common.Finding(
                "problem", f"{path} has {lines} lines; the target is under {limits['claudeMdLines']}.",
                config["limitsWhy"]["claudeMdLines"],
                "Move what is only for part of the code into scoped rules, procedures into skills, and history into docs: /bowline:split-instructions."))
        if outside and outside.search(text):
            findings.append(common.Finding(
                "problem", f"{path} names a path outside the repository.", config["outsidePathsWhy"],
                "Replace the pointer with one every contributor can follow, or remove it."))

    for path in common.tracked_files(root, rules_dir + "/*"):
        if not path.endswith(".md"):
            continue
        text = common.read_text(os.path.join(root, path))
        lines = common.count_lines(text)
        chars = len(text)
        globs = paths_of(text)
        facts["rules"].append((path, lines, chars, globs))
        if lines >= limits["ruleLines"]:
            findings.append(common.Finding("problem", f"{path} has {lines} lines; the target is under {limits['ruleLines']}.",
                                           config["limitsWhy"]["ruleLines"], "Split it by topic, or move its history to a docs page."))
        if chars >= limits["ruleChars"]:
            findings.append(common.Finding("problem", f"{path} has {chars:,} characters; the limit is under {limits['ruleChars']:,}.",
                                           config["limitsWhy"]["ruleChars"], "Split it by topic, or move its history to a docs page."))
        if outside and outside.search(text):
            findings.append(common.Finding("problem", f"{path} names a path outside the repository.", config["outsidePathsWhy"],
                                           "Replace the pointer with one every contributor can follow, or remove it."))
        names = {area_of(g) for g in globs}
        if not globs or None in names:
            facts["unscoped"] += chars
        else:
            for name in names:
                facts["areas"][name] = facts["areas"].get(name, 0) + chars

    for name, chars in sorted(facts["areas"].items()):
        if chars >= limits["areaChars"]:
            findings.append(common.Finding(
                "problem", f"the scoped rules for {name} load {chars:,} characters together; the limit is under {limits['areaChars']:,}.",
                config["limitsWhy"]["areaChars"], "Move the longest explanations to docs pages and keep the imperatives; drop rules a test or a lint rule already enforces."))
    if facts["unscoped"] >= limits["unscopedChars"]:
        findings.append(common.Finding(
            "problem", f"the unscoped rules load {facts['unscoped']:,} characters in every session; the limit is under {limits['unscopedChars']:,}.",
            config["limitsWhy"]["unscopedChars"], "Give a rule a paths: list when it concerns one part of the code."))

    skill_paths = []
    for folder in skills_dirs:
        skill_paths += common.tracked_files(root, folder.replace("\\", "/") + "/*")
    for path in sorted(set(skill_paths)):
        if not path.endswith("SKILL.md"):
            continue
        text = common.read_text(os.path.join(root, path))
        lines = common.count_lines(text)
        facts["skills"].append((path, lines))
        if lines >= limits["skillLines"]:
            findings.append(common.Finding("problem", f"{path} has {lines} lines; the target is under {limits['skillLines']}.",
                                           config["limitsWhy"]["skillLines"], "Move reference material to files beside it and point to them."))
        if outside and outside.search(text):
            findings.append(common.Finding("problem", f"{path} names a path outside the repository.", config["outsidePathsWhy"],
                                           "Replace the pointer with one every contributor can follow, or remove it."))
    return findings, facts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refuses an instruction file over the sizes Claude Code reads.")
    parser.add_argument("--repo", help="a path inside the repository, or a folder of repositories (default: the current folder)")
    options = parser.parse_args(argv)
    workspace, roots = common.roots_for(options.repo)
    if not roots:
        print("bowline budget: not inside a git repository, and this folder holds none.", file=sys.stderr)
        return 2
    if workspace is None:
        config = common.load_config(roots[0])
        findings, facts = measure(roots[0], config)
        if findings:
            problems = common.print_findings(findings, "bowline budget")
            return 1 if problems else 0
        areas = ", ".join(f"{name} {chars:,}" for name, chars in sorted(facts["areas"].items())) or "none"
        print(f"bowline budget: within limits. Scoped rules per area: {areas}; unscoped, every session: {facts['unscoped']:,}; "
              f"{len(facts['claudeMd'])} CLAUDE.md file(s), {len(facts['skills'])} skill(s).")
        return 0
    findings, summaries = [], []
    for root in [workspace] + roots:
        name = os.path.basename(root)
        found, facts = measure(root, common.load_config(root))
        for finding in found:
            finding.what = f"{name}: {finding.what}"
        findings += found
        areas = ", ".join(f"{area} {chars:,}" for area, chars in sorted(facts["areas"].items())) or "none"
        summaries.append(f"  {name}: {len(facts['claudeMd'])} CLAUDE.md file(s); scoped rules per area: {areas}; unscoped: {facts['unscoped']:,}; {len(facts['skills'])} skill(s)")
    if findings:
        problems = common.print_findings(findings, "bowline budget")
        return 1 if problems else 0
    print(f"bowline budget: within limits across the folder and its {common.count(len(roots), 'repository', 'repositories')}.")
    for line in summaries:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
