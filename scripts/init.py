"""Scaffolds the repository's side of the layout: the files a plugin cannot ship.

    python -I scripts/bowline.py init [--repo <path>] [--plan | --write] [--only item,item]

Items, each a file or a set of files under the repository:
  claude-md      the root CLAUDE.md gets three sections (appended when missing, the file created when absent):
                 Where the rest of the rules are; Compact Instructions; Memory between sessions
  claude-readme  .claude/README.md: what the folder holds, when Claude Code reads each part, the sizes and why
  rules          .claude/rules/before-a-commit.md and recording-decisions.md, two unscoped starter rules
  skills         .claude/skills/full-checks/SKILL.md and .claude/skills/push/SKILL.md, starters with placeholders
  scripts        .claude/scripts/: repository-local copies of the gate and the budget check with their defaults,
                 so CI and contributors without the plugin run the same checks
  githook        .githooks/pre-commit, running the gate; opt in with `git config core.hooksPath .githooks`
  config         .claude/bowline.json with the defaults a repository usually changes, each with its reason
  gitignore      .gitignore entries for a person's own Claude Code files

--plan prints what each item would do and changes nothing. --write does it: it creates what is missing and appends
the missing sections, and never overwrites or edits what exists. Without a flag it behaves as --plan.
"""

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

TEMPLATES = os.path.join(common.PLUGIN_ROOT, "templates")
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ITEMS = ["claude-md", "claude-readme", "rules", "skills", "scripts", "githook", "config", "gitignore"]
GITIGNORE_LINES = [
    "# A person's own Claude Code settings and worktrees for this repository, never the team's (bowline init).",
    ".claude/settings.local.json",
    ".claude/worktrees/",
    "__pycache__/",
]


def template(name):
    return common.read_text(os.path.join(TEMPLATES, name))


def sections_of(text):
    """The '## ' sections of a Markdown text as (title, body including the heading) pairs."""
    out, current, buffer = [], None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            if current is not None:
                out.append((current, "\n".join(buffer).rstrip("\n") + "\n"))
            current, buffer = line[3:].strip(), [line]
        elif current is not None:
            buffer.append(line)
    if current is not None:
        out.append((current, "\n".join(buffer).rstrip("\n") + "\n"))
    return out


class Plan:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.actions = []   # (item, path, verb, do) where do is a function that performs it

    def add(self, item, path, verb, do=None):
        self.actions.append((item, path.replace("\\", "/"), verb, do))

    def file(self, item, relative, content):
        full = os.path.join(self.root, relative)
        if os.path.exists(full):
            self.add(item, relative, "kept (exists)")
            return
        def do(full=full, content=content):
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        self.add(item, relative, "create", do)


def build(root, config, only):
    plan = Plan(root, config)
    wanted = set(only) if only else set(ITEMS)

    if "claude-md" in wanted:
        path = os.path.join(root, "CLAUDE.md")
        existing = common.read_text(path) if os.path.isfile(path) else ""
        have = {title.lower() for title, _ in sections_of(existing)}
        missing = [(t, b) for t, b in sections_of(template("CLAUDE.md.sections.md")) if t.lower() not in have]
        if not existing:
            head = template("CLAUDE.md.head.md")
            body = head + "\n" + "\n".join(b for _, b in missing)
            plan.file("claude-md", "CLAUDE.md", body)
        elif missing:
            def do(path=path, existing=existing, missing=missing):
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(existing.rstrip("\n") + "\n\n" + "\n".join(b for _, b in missing))
            plan.add("claude-md", "CLAUDE.md", "append sections: " + ", ".join(t for t, _ in missing), do)
        else:
            plan.add("claude-md", "CLAUDE.md", "kept (has every section)")

    if "claude-readme" in wanted:
        plan.file("claude-readme", ".claude/README.md", template("claude-readme.md"))
    if "rules" in wanted:
        for name in ("before-a-commit.md", "recording-decisions.md"):
            plan.file("rules", f".claude/rules/{name}", template(f"rules/{name}"))
    if "skills" in wanted:
        for name in ("full-checks", "push"):
            plan.file("skills", f".claude/skills/{name}/SKILL.md", template(f"skills/{name}/SKILL.md"))
    if "scripts" in wanted:
        for name in ("common.py", "gate.py", "budget.py"):
            plan.file("scripts", f".claude/scripts/{name}", common.read_text(os.path.join(SCRIPTS, name)))
        plan.file("scripts", ".claude/scripts/defaults.json", common.read_text(common.defaults_path()))
    if "githook" in wanted:
        plan.file("githook", ".githooks/pre-commit", template("githooks/pre-commit"))
    if "config" in wanted:
        plan.file("config", common.CONFIG_FILE, template("bowline.json"))
    if "gitignore" in wanted:
        path = os.path.join(root, ".gitignore")
        existing = common.read_text(path) if os.path.isfile(path) else ""
        missing = [l for l in GITIGNORE_LINES[1:] if l not in existing.split("\n")]
        if not missing:
            plan.add("gitignore", ".gitignore", "kept (has the entries)")
        else:
            def do(path=path, existing=existing, missing=missing):
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write((existing.rstrip("\n") + "\n\n" if existing else "") + GITIGNORE_LINES[0] + "\n" + "\n".join(missing) + "\n")
            plan.add("gitignore", ".gitignore", "append entries: " + ", ".join(missing), do)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scaffolds the repository's side of bowline's layout.")
    parser.add_argument("--repo")
    parser.add_argument("--plan", action="store_true", help="print what would be done (the default)")
    parser.add_argument("--write", action="store_true", help="do it: create what is missing, append missing sections, never overwrite")
    parser.add_argument("--only", help="a comma-separated list of items: " + ", ".join(ITEMS))
    options = parser.parse_args(argv)
    root = common.repo_root(options.repo)
    if not root:
        _, repos = common.roots_for(options.repo)
        hint = (f" This folder holds {len(repos)} repositories ({', '.join(os.path.basename(r) for r in repos)}): run init inside each;"
                " a scaffold for the folder itself is not here yet.") if repos else ", and this folder holds none."
        print("bowline init: not inside a git repository" + hint, file=sys.stderr)
        return 2
    only = [i.strip() for i in options.only.split(",")] if options.only else None
    if only and any(i not in ITEMS for i in only):
        print("bowline init: unknown item; the items are " + ", ".join(ITEMS), file=sys.stderr)
        return 2
    plan = build(root, common.load_config(root), only)
    print(f"bowline init: {root}")
    for item, path, verb, do in plan.actions:
        print(f"  {item:14} {path:40} {verb}")
    pending = [a for a in plan.actions if a[3] is not None]
    if not options.write:
        print(f"\n{len(pending)} change(s) would be made. Run with --write to make them; nothing that exists is overwritten.")
        return 0
    for item, path, verb, do in pending:
        do()
    print(f"\n{len(pending)} change(s) made. Next: fill the placeholders in .claude/skills/*/SKILL.md, run `git config core.hooksPath .githooks` "
          "to let git run the gate, and run `bowline doctor`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
