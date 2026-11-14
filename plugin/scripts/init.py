"""Scaffolds the repository's side of the layout: the files a plugin cannot ship.

    python -I scripts/bowline.py init [--repo <path>] [--plan | --write] [--only item,item]
    python -I scripts/bowline.py init [--each] [--plan | --write]        from a folder of repositories

Items, each a file or a set of files under the repository:
  claude-md      the root CLAUDE.md gets three sections (appended when missing, the file created when absent):
                 Where the rest of the rules are; Compact Instructions; Memory between sessions. A repository
                 whose root file is .claude/CLAUDE.md, the other place Claude Code reads, gets them there
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

From a folder that is not a repository but holds several, init scaffolds the folder itself: its own CLAUDE.md, the
file that loads whole at the start of a session started there, as an index of the repositories (a table with a line
for each, taken from the repository's own CLAUDE.md), what applies to every repository, the Compact Instructions and
the memory section, which for a folder says that the memory is one for the whole folder; and the shared
.claude/bowline.json. With --each it plans or writes the repository scaffold in every repository of the folder instead.
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
FOLDER_ITEMS = ["claude-md", "claude-readme", "rules", "skills", "config", "gitignore"]
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
        found = common.root_claude_md(root)
        relative = found[0] if found else "CLAUDE.md"
        path = os.path.join(root, relative)
        # Both root files load whole, so a section in either one is had; what is missing goes into the first.
        existing = "\n".join(common.read_text(os.path.join(root, p)) for p in found)
        have = {title.lower() for title, _ in sections_of(existing)}
        missing = [(t, b) for t, b in sections_of(template("CLAUDE.md.sections.md")) if t.lower() not in have]
        if not found:
            head = template("CLAUDE.md.head.md")
            body = head + "\n" + "\n".join(b for _, b in missing)
            plan.file("claude-md", "CLAUDE.md", body)
        elif missing:
            current = common.read_text(path)
            def do(path=path, current=current, missing=missing):
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(current.rstrip("\n") + "\n\n" + "\n".join(b for _, b in missing))
            plan.add("claude-md", relative, "append sections: " + ", ".join(t for t, _ in missing), do)
        else:
            plan.add("claude-md", relative, "kept (has every section)")

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


def repository_row(root):
    """A row of the folder's table: the repository's name and the first line of its own CLAUDE.md that is not a heading."""
    words = "(say in a line what it is)"
    found = common.root_claude_md(root)
    if found:
        for line in common.read_text(os.path.join(root, found[0])).split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("<!--") and not line.startswith("|"):
                words = line[:100].rstrip() + ("..." if len(line) > 100 else "")
                break
    return f"| `{os.path.basename(root)}/` | {words} |"


def folder_setting(folder, leave):
    """The writeToRepositories value init works with: the folder's own file's when it says, else false when the person
    asked to leave the repositories untouched (--leave-repositories), else true, today's default."""
    path = os.path.join(folder, common.CONFIG_FILE)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                own = json.load(handle)
            if "writeToRepositories" in own:
                return own["writeToRepositories"]
        except (OSError, ValueError):
            pass
    return False if leave else True


def about_folder(folder, count):
    """The opening sentences of a folder's CLAUDE.md: what kind of folder it is."""
    if common.is_repository(folder):
        return (f"This folder is a git repository of its own, which holds only what its {count} repositories share; it does "
                "not track them, and its `.gitignore` names them. Claude Code loads each repository's own `CLAUDE.md` when "
                "a file under that repository is read or edited.")
    return (f"This folder is not a repository. It holds {count} repositories side by side, and Claude Code loads each "
            "repository's own `CLAUDE.md` when a file under that repository is read or edited.")


def rules_for_one(roots, setting):
    """Where a rule for one repository goes, given which repositories bowline may write into."""
    kept = [os.path.basename(r) for r in roots if not common.allowed_by(setting, r)]
    own = [os.path.basename(r) for r in roots if common.allowed_by(setting, r)]
    here = ("in `.claude/rules/<repository>/`, with `paths: [\"<repository>/**\"]` in its front matter, because bowline "
            "leaves {which} untouched (`writeToRepositories` in `.claude/bowline.json`)")
    if not kept:
        return "a rule for one repository goes in that repository's own `.claude/rules/`."
    if not own:
        return "a rule for one repository goes here too, " + here.format(which="the repositories") + "."
    return (f"a rule for {', '.join(own)} goes in that repository's own `.claude/rules/`; a rule for "
            f"{', '.join(kept)} goes here, " + here.format(which="them") + ".")


def folder_config(setting):
    """The folder's .claude/bowline.json: the template, with the writeToRepositories choice and its reason."""
    data = json.loads(template("bowline.json"))
    data["_writeToRepositories"] = ("Whether bowline writes into the repositories of this folder: true, false, or a list "
                                    "of the names it may write into. With false, init, move and autosplit write nothing into "
                                    "them, and what this folder needs about each one lives here.")
    data["writeToRepositories"] = setting
    return json.dumps(data, indent=2) + "\n"


def build_folder(folder, roots, only, leave=False):
    """The scaffold for a folder of repositories: its own CLAUDE.md, an index of the repositories with the sections every
    root file needs, and the shared .claude/bowline.json; the .claude/README.md, starter rules and skills too when the
    folder keeps the files of repositories bowline leaves untouched; and, when the folder is a git repository of its
    own, the .gitignore lines that keep its repositories out of it. The repositories get their own scaffold with --each."""
    plan = Plan(folder, None)
    setting = folder_setting(folder, leave)
    keeps = any(not common.allowed_by(setting, r) for r in roots)
    default = ["claude-md", "config"] + (["claude-readme", "rules", "skills"] if keeps else [])
    default += ["gitignore"] if common.is_repository(folder) else []
    wanted = set(only) if only else set(default)
    if "claude-md" in wanted:
        compact = "".join(body for title, body in sections_of(template("CLAUDE.md.sections.md")) if title.lower() == "compact instructions")
        text = (template("CLAUDE.md.folder.md").replace("{about}", about_folder(folder, len(roots)))
                .replace("{rules_for_one}", rules_for_one(roots, setting))
                .replace("{rows}", "\n".join(repository_row(root) for root in roots)).replace("{compact}", compact + "\n"))
        found = common.root_claude_md(folder)
        relative = found[0] if found else "CLAUDE.md"
        path = os.path.join(folder, relative)
        if not found:
            plan.file("claude-md", "CLAUDE.md", text)
        else:
            existing = "\n".join(common.read_text(os.path.join(folder, p)) for p in found)
            have = {title.lower() for title, _ in sections_of(existing)}
            missing = [(t, b) for t, b in sections_of(text) if t.lower() not in have]
            if missing:
                current = common.read_text(path)
                def do(path=path, current=current, missing=missing):
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(current.rstrip("\n") + "\n\n" + "\n".join(b for _, b in missing))
                plan.add("claude-md", relative, "append sections: " + ", ".join(t for t, _ in missing), do)
            else:
                plan.add("claude-md", relative, "kept (has every section)")
    if "claude-readme" in wanted:
        plan.file("claude-readme", ".claude/README.md", template("claude-readme.md"))
    if "rules" in wanted:
        for name in ("before-a-commit.md", "recording-decisions.md"):
            plan.file("rules", f".claude/rules/{name}", template(f"rules/{name}"))
    if "skills" in wanted:
        for name in ("full-checks", "push"):
            plan.file("skills", f".claude/skills/{name}/SKILL.md", template(f"skills/{name}/SKILL.md"))
    if "config" in wanted:
        plan.file("config", common.CONFIG_FILE, folder_config(setting))
    if "gitignore" in wanted:
        path = os.path.join(folder, ".gitignore")
        existing = common.read_text(path) if os.path.isfile(path) else ""
        lines = existing.split("\n")
        wanted_lines = GITIGNORE_LINES[1:] + [f"/{os.path.basename(r)}/" for r in roots]
        missing = [l for l in wanted_lines if l not in lines]
        if not missing:
            plan.add("gitignore", ".gitignore", "kept (has the entries)")
        else:
            header = "# The repositories this folder holds side by side; each is a git repository of its own (bowline init)."
            def do(path=path, existing=existing, missing=missing, header=header):
                body = [l for l in missing if l in GITIGNORE_LINES[1:]]
                repos = [l for l in missing if l not in GITIGNORE_LINES[1:]]
                parts = [existing.rstrip("\n")] if existing else []
                if body:
                    parts.append(GITIGNORE_LINES[0] + "\n" + "\n".join(body))
                if repos:
                    parts.append(header + "\n" + "\n".join(repos))
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n\n".join(parts) + "\n")
            plan.add("gitignore", ".gitignore", "append entries: " + ", ".join(missing), do)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scaffolds the repository's side of bowline's layout.")
    parser.add_argument("--repo")
    parser.add_argument("--plan", action="store_true", help="print what would be done (the default)")
    parser.add_argument("--write", action="store_true", help="do it: create what is missing, append missing sections, never overwrite")
    parser.add_argument("--only", help="a comma-separated list of items: " + ", ".join(ITEMS) + " (for a folder of repositories: " + ", ".join(FOLDER_ITEMS) + ")")
    parser.add_argument("--each", action="store_true", help="from a folder of repositories: plan or write the repository scaffold in every one of them")
    parser.add_argument("--leave-repositories", action="store_true",
                        help="from a folder of repositories: keep bowline's files in the folder and write nothing into the repositories"
                             " (writeToRepositories false in the folder's new .claude/bowline.json)")
    options = parser.parse_args(argv)
    workspace, roots = common.roots_for(options.repo)
    root = None if workspace else (roots[0] if roots else None)
    if not roots:
        print("bowline init: not inside a git repository, and this folder holds none.", file=sys.stderr)
        return 2
    items = FOLDER_ITEMS if workspace and not options.each else ITEMS
    only = [i.strip() for i in options.only.split(",")] if options.only else None
    if only and any(i not in items for i in only):
        print("bowline init: unknown item; the items are " + ", ".join(items), file=sys.stderr)
        return 2
    if root and not common.writes_allowed(root):
        print(f"bowline init: {common.left_alone(root)}. Run init from the folder, {common.folder_of(root)}, to keep its "
              "files there.", file=sys.stderr)
        return 1
    if root:
        plans = [(root, build(root, common.load_config(root), only))]
    elif options.each:
        allowed = [r for r in roots if common.writes_allowed(r)]
        for r in roots:
            if r not in allowed:
                print(f"bowline init: {common.left_alone(r)}; skipped.")
        if not allowed:
            print("bowline init: nothing to do; the folder keeps the files of all its repositories. Run init without --each.")
            return 0
        plans = [(r, build(r, common.load_config(r), only)) for r in allowed]
    else:
        plans = [(workspace, build_folder(workspace, roots, only, options.leave_repositories))]
        setting = folder_setting(workspace, options.leave_repositories)
        if options.leave_repositories and setting is not False and os.path.isfile(os.path.join(workspace, common.CONFIG_FILE)):
            print(f"bowline init: the folder's {common.CONFIG_FILE} exists and init never edits it; to leave the repositories "
                  f"untouched, set \"writeToRepositories\": false in it, then run init again.")
    total = 0
    for index, (where, plan) in enumerate(plans):
        if index:
            print()
        print(f"bowline init: {where}")
        for item, path, verb, do in plan.actions:
            print(f"  {item:14} {path:40} {verb}")
        pending = [a for a in plan.actions if a[3] is not None]
        total += len(pending)
        if options.write:
            for item, path, verb, do in pending:
                do()
    if workspace and not options.each:
        setting = folder_setting(workspace, options.leave_repositories)
        own = [os.path.basename(r) for r in roots if common.allowed_by(setting, r)]
        kept = [os.path.basename(r) for r in roots if not common.allowed_by(setting, r)]
    if not options.write:
        print(f"\n{total} change(s) would be made. Run with --write to make them; nothing that exists is overwritten.")
        if workspace and not options.each:
            if own:
                print(f"The folder's repositories {', '.join(own)} get their own scaffold with --each.")
            if kept:
                print(f"bowline writes nothing into {', '.join(kept)}: their rules go in this folder's .claude/rules/<repository>/.")
        return 0
    if workspace and not options.each:
        then = (" then `bowline init --each` for the own scaffold of " + ", ".join(own) + ";") if own else ""
        keep = (f" put what this folder needs about {', '.join(kept)} in .claude/rules/<repository>/, scoped with paths;"
                if kept else "")
        print(f"\n{total} change(s) made. Next: say in CLAUDE.md's table what each repository is, in a line;{then}{keep}"
              " and run `bowline doctor`.")
        return 0
    print(f"\n{total} change(s) made. Next: fill the placeholders in .claude/skills/*/SKILL.md, run `git config core.hooksPath .githooks` "
          "to let git run the gate, and run `bowline doctor`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
