"""The doctor: measures a repository and this machine against what Claude Code reads, and says what to do.

    python -I scripts/doctor.py [--repo <path>] [--no-memory]

For each finding it prints three lines: what it found, why it matters, what to do and which skill does it. It reports:
- every CLAUDE.md against the line target, and for a nested one how much of it is never read on a 200K and on a 1M
  context window, naming the section the cut falls in;
- the rules per area and the unscoped rules against their budgets, skills against theirs, and pointers outside the
  repository (the budget check);
- the memory folder Claude Code keeps for this repository on this machine: its index against the cap, whether the
  folder is a git repository with a remote, and whether the push hook is installed;
- whether the root CLAUDE.md has a compaction section, whether the gate and the budget check are installed, and
  whether the repository has a .claude/bowline.json;
- a split that autosplit prepared in the background, ready on its branch, still running or failed, and why one has
  not started, when the repository turned autosplit on.
Exit codes: 0 when nothing is a problem (warnings and notes allowed), 1 when at least one problem was found, 2 when the
script could not run.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autosplit  # noqa: E402
import budget  # noqa: E402
import common  # noqa: E402

HEADING = re.compile(r"^#{1,3} (.+)$", re.MULTILINE)


def cut_point(text, cutoff):
    """Where a cutoff falls in a file: (line number, the heading of the section it falls in, the sections never read)."""
    if len(text) <= cutoff:
        return None
    before = text[:cutoff]
    line = before.count("\n") + 1
    headings = [(m.start(), m.group(1).strip()) for m in HEADING.finditer(text)]
    current = None
    never = []
    for start, title in headings:
        if start <= cutoff:
            current = title
        else:
            never.append(title)
    return line, current, never


def claude_md_findings(root, config, facts):
    limits = config["limits"]
    small, large = limits["onDemandCutoffSmallWindow"], limits["onDemandCutoffLargeWindow"]
    findings = []
    for path, lines, chars in facts["claudeMd"]:
        nested = os.path.dirname(path) != ""
        if not nested:
            continue
        text = common.read_text(os.path.join(root, path))
        for cutoff, window in ((small, "a 200K context window"), (large, "a 1M context window")):
            cut = cut_point(text, cutoff)
            if not cut:
                continue
            line, section, never = cut
            share = 100 - int(100 * cutoff / max(chars, 1))
            where = f"inside the section \"{section}\"" if section else "before its first heading"
            lost = f"; never read: {', '.join(never[:6])}" + (" and more" if len(never) > 6 else "") if never else ""
            findings.append(common.Finding(
                "problem",
                f"{path} is cut at line {line} on {window}, {where}: about {share}% of the file is never read there{lost}.",
                config["limitsWhy"]["onDemandCutoffSmallWindow" if cutoff == small else "onDemandCutoffLargeWindow"],
                "Move the long form into docs pages and the rules into .claude/rules/ scoped by path, and keep this file an index: /bowline:split-instructions."))
            break
        if chars >= limits["skippedFileBytes"]:
            findings.append(common.Finding("problem", f"{path} is over 4 MiB and is skipped entirely.",
                                           config["limitsWhy"]["skippedFileBytes"], "Split it: /bowline:split-instructions."))
    return findings


def root_claude_md_findings(root, facts):
    findings = []
    roots = [p for p, _, _ in facts["claudeMd"] if os.path.dirname(p) == ""]
    if not roots:
        findings.append(common.Finding(
            "warning", "The repository has no root CLAUDE.md.",
            "The root CLAUDE.md is the one file every session loads whole and re-reads after a compaction; without it nothing standing survives a summary.",
            "Create one with the writing rules, where decisions are recorded, and a Compact Instructions section: /bowline:init."))
        return findings
    text = common.read_text(os.path.join(root, roots[0]))
    if not re.search(r"^#+\s*compact instructions", text, re.IGNORECASE | re.MULTILINE):
        findings.append(common.Finding(
            "warning", f"{roots[0]} has no \"Compact Instructions\" section.",
            "Claude Code replaces a long conversation with a summary, when the context fills and after about an hour of quiet; this section tells every summary what to keep.",
            "Add the section: /bowline:init offers the text, or see docs/conventions.md."))
    if not re.search(r"^#+\s*memory between sessions", text, re.IGNORECASE | re.MULTILINE):
        findings.append(common.Finding(
            "note", f"{roots[0]} does not say what the memory folder is for.",
            "A session that knows the index loads only to 200 lines keeps it short; one that does not fills it until the newest notes fall off.",
            "Add the section: /bowline:init offers the text."))
    return findings


def memory_findings(root, config):
    limits = config["limits"]
    findings = []
    checkout = common.main_checkout(root)
    folder = common.memory_folder(checkout)
    project = os.path.dirname(folder)
    if not os.path.isdir(project):
        findings.append(common.Finding(
            "note", f"Claude Code has no project folder for {checkout} on this machine (expected {project}).",
            "The folder is made the first time Claude Code runs in the repository; its name is the path with every other character replaced by a dash, as observed, not documented.",
            "Nothing to do until a session has run here."))
        return findings
    index = os.path.join(folder, "MEMORY.md")
    if not os.path.isfile(index):
        findings.append(common.Finding("note", "The memory folder has no MEMORY.md yet.", "Claude writes it at the first memory it keeps.", None))
    else:
        text = common.read_text(index)
        lines, size = common.count_lines(text), len(text.encode("utf-8"))
        if lines >= limits["memoryIndexLines"] or size >= limits["memoryIndexBytes"]:
            findings.append(common.Finding(
                "problem", f"MEMORY.md has {lines} lines and {size:,} bytes; only the first {limits['memoryIndexLines']} lines or {limits['memoryIndexBytes']:,} bytes load.",
                config["limitsWhy"]["memoryIndexLines"],
                "Fold finished items into one line each and promote project knowledge into the repository: /bowline:curate-memory."))
        elif lines >= int(limits["memoryIndexLines"] * 0.8) or size >= int(limits["memoryIndexBytes"] * 0.8):
            findings.append(common.Finding(
                "warning", f"MEMORY.md is at {lines} lines and {size:,} bytes, near the cap of {limits['memoryIndexLines']} lines or {limits['memoryIndexBytes']:,} bytes.",
                config["limitsWhy"]["memoryIndexLines"], "Curate before it passes the cap: /bowline:curate-memory."))
    if not os.path.isdir(os.path.join(folder, ".git")):
        findings.append(common.Finding(
            "warning", f"The memory folder {folder} is not backed up.",
            "Memory is per person and per machine, outside the repository; a lost or reinstalled machine loses every note.",
            "Make it a git repository pushed to a private remote after every reply: /bowline:memory-backup setup <remote>."))
    else:
        remote = common.run_git(["-C", folder, "remote", "get-url", "origin"], check=False).strip()
        if not remote:
            findings.append(common.Finding("warning", "The memory folder is a git repository with no remote.",
                                           "A local repository is lost with the machine like the folder itself.", "/bowline:memory-backup setup <remote>."))
        hooked = hook_installed()
        if not hooked:
            findings.append(common.Finding(
                "warning", "No hook pushes the memory folder after a reply.",
                "Without the hook the backup is only as fresh as the last push someone remembered to make.",
                "/bowline:memory-backup setup <remote> installs it for this machine."))
    return findings


def hook_installed():
    path = os.path.join(common.config_dir(), "settings.json")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            settings = json.load(handle)
    except Exception:
        return False
    for event in ("Stop", "SessionEnd"):
        for group in (settings.get("hooks") or {}).get(event, []) or []:
            for hook in group.get("hooks", []) or []:
                text = str(hook.get("command", "")) + " " + " ".join(str(a) for a in hook.get("args", []) or [])
                if "push-memory" in text or "bowline" in text:
                    return True
    return False


def layout_findings(root):
    findings = []
    if not os.path.isfile(os.path.join(root, common.CONFIG_FILE)):
        findings.append(common.Finding(
            "note", f"The repository has no {common.CONFIG_FILE}; the defaults apply.",
            "The file holds the repository's own limits and gate policy, so every contributor measures against the same numbers.",
            "/bowline:init writes it with the defaults and their reasons."))
    gate_local = os.path.isfile(os.path.join(root, ".claude", "scripts", "gate.py")) or os.path.isfile(os.path.join(root, ".githooks", "pre-commit"))
    hooks_path = common.run_git(["-C", root, "config", "--get", "core.hooksPath"], check=False).strip()
    if not gate_local and not hooks_path:
        findings.append(common.Finding(
            "note", "No commit gate is installed for this repository.",
            "A gate reads the staged lines before every commit and refuses a token, a stray byte or a word that must never be committed; a pushed secret cannot be taken back.",
            "/bowline:init installs a repository-local copy and the pre-commit hook; the bowline plugin's hook runs it from Claude Code too."))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measures a repository and this machine against what Claude Code reads.")
    parser.add_argument("--repo", help="a path inside the repository (default: the current folder)")
    parser.add_argument("--no-memory", action="store_true", help="skip the memory folder checks (for CI)")
    parser.add_argument("--brief", action="store_true",
                        help="one line per problem or warning and nothing when clean; always exit 0 (for a SessionStart hook)")
    options = parser.parse_args(argv)
    root = common.repo_root(options.repo)
    if not root:
        if options.brief:
            return 0
        print("bowline doctor: not inside a git repository.", file=sys.stderr)
        return 2
    config = common.load_config(root)
    if options.brief:
        try:
            budget_findings, facts = budget.measure(root, config)
            findings = [f for f in autosplit.findings(root, config, facts) if f.level != "note"]
            findings += claude_md_findings(root, config, facts)
            findings += [f for f in budget_findings if f.level == "problem"]
            findings += [f for f in root_claude_md_findings(root, facts) if f.level != "note"]
            if not options.no_memory:
                findings += [f for f in memory_findings(root, config) if f.level != "note"]
            autosplit.adjust(findings, root)
        except Exception:
            return 0
        urgent = [f for f in findings if f.level in ("problem", "warning")]
        if urgent:
            print(f"bowline found {len(urgent)} thing(s) about this repository's instructions or memory worth a look; run /bowline:doctor for the report. The first:")
            for finding in urgent[:3]:
                print(f"- {finding.what} Fix: {finding.fix or 'see the doctor'}")
        return 0
    print(f"bowline doctor: {root}")
    print(f"limits from defaults.json (facts checked against the Claude Code docs on {config.get('checkedAgainstDocs')})"
          + (f", with {common.CONFIG_FILE}" if os.path.isfile(os.path.join(root, common.CONFIG_FILE)) else ""))
    print()

    budget_findings, facts = budget.measure(root, config)
    findings = []
    findings += claude_md_findings(root, config, facts)
    findings += autosplit.findings(root, config, facts)
    findings += [f for f in budget_findings if "names a path" in f.what or "lines; the target" in f.what or "characters" in f.what]
    findings += root_claude_md_findings(root, facts)
    if not options.no_memory:
        findings += memory_findings(root, config)
    findings += layout_findings(root)

    for path, lines, chars in facts["claudeMd"]:
        print(f"  {path}: {lines} lines, {chars:,} characters")
    areas = ", ".join(f"{name} {chars:,}" for name, chars in sorted(facts["areas"].items())) or "none"
    print(f"  scoped rules per area: {areas}; unscoped: {facts['unscoped']:,}; skills: {len(facts['skills'])}")
    print()
    autosplit.adjust(findings, root)
    problems = common.print_findings(findings, "bowline doctor")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
