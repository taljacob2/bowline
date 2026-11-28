"""Scaffolds the repository's side of the layout: the files a plugin cannot ship.

    python -I scripts/bowline.py init [--repo <path>] [--plan | --write] [--only item,item] [--autosplit]
    python -I scripts/bowline.py init [--each] [--plan | --write]        from a folder of repositories
        [--leave-repositories] [--no-describe] [--verbose] [--autosplit]

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

Wherever the config item is planned, the plan also says whether autosplit is on, what it does and what one split may
spend, because autosplit is off by default and a person who is never told about it never turns it on. --autosplit
turns it on in the .claude/bowline.json that init creates; init never edits one that exists, so there the plan says
which key to set. A new file otherwise keeps the value of the folder's file below it, so that init never turns
autosplit off where a folder of repositories turned it on.

From a folder that is not a repository but holds several, init scaffolds the folder itself: its own CLAUDE.md, the
file that loads whole at the start of a session started there, as an index of the repositories (a table with a line
for each, taken from the repository's own CLAUDE.md), what applies to every repository, the Compact Instructions and
the memory section, which for a folder says that the memory is one for the whole folder; and the shared
.claude/bowline.json. With --each it plans or writes the repository scaffold in every repository of the folder instead.
Each row of the table is described from the repository's README, its package description or the opening of its
CLAUDE.md, and the plan says from where; --no-describe leaves every row for the person. The folder's rules, skills and
README are worded for a folder (templates/folder/), and name the folder's copy of the gate only when there is one:
scripts and githook need the folder to be a git repository. A list of repositories names ten, unless --verbose.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autosplit  # noqa: E402
import common  # noqa: E402

TEMPLATES = os.path.join(common.PLUGIN_ROOT, "templates")
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ITEMS = ["claude-md", "claude-readme", "rules", "skills", "scripts", "githook", "config", "gitignore"]
FOLDER_ITEMS = ["claude-md", "claude-readme", "rules", "skills", "scripts", "githook", "config", "gitignore"]
# Items that copy the gate into the folder: they need the folder to be a git repository, where commits are made.
GATE_ITEMS = ("scripts", "githook")
GITIGNORE_LINES = [
    "# A person's own Claude Code settings and worktrees for this repository, never the team's (bowline init).",
    ".claude/settings.local.json",
    ".claude/worktrees/",
    "__pycache__/",
]


def template(name):
    return common.read_text(os.path.join(TEMPLATES, name))


WIDTH = 120


def rewrap(text, width=WIDTH):
    """Re-wraps the prose of a Markdown text at the width bowline's templates use, after a placeholder was filled with
    a sentence of its own length: each paragraph, and each list item with its two-space continuation. Headings, tables,
    code fences, front matter and blank lines are left exactly as they are."""
    out, block, fenced, front = [], [], False, text.startswith("---\n")

    def flush():
        if not block:
            return
        first = block[0]
        bullet = first.startswith("- ")
        words = " ".join(line.strip() for line in block)
        if bullet:
            out.append(textwrap.fill(words[2:], width, initial_indent="- ", subsequent_indent="  ",
                                     break_long_words=False, break_on_hyphens=False))
        else:
            out.append(textwrap.fill(words, width, break_long_words=False, break_on_hyphens=False))
        block.clear()

    lines = text.split("\n")
    for index, line in enumerate(lines):
        if front:
            out.append(line)
            if index > 0 and line == "---":
                front = False
            continue
        if line.startswith("```"):
            flush()
            fenced = not fenced
            out.append(line)
        elif fenced or not line.strip() or line.startswith(("#", "|", "<!--")):
            flush()
            out.append(line)
        elif line.startswith("- "):
            flush()
            block.append(line)
        elif line.startswith("  ") and block and block[0].startswith("- "):
            block.append(line)
        else:
            if block and block[0].startswith("- "):
                flush()
            block.append(line)
    flush()
    return "\n".join(out)


def fill(text, values, wrapped):
    """Fills a template's placeholders, and re-wraps only the paragraphs that held one of those named in wrapped, so a
    substituted sentence never leaves a ragged paragraph while the rest keeps the template's own lines."""
    out = []
    for block in text.split("\n\n"):
        changed = any("{" + key + "}" in block for key in wrapped)
        for key, value in values.items():
            block = block.replace("{" + key + "}", value)
        out.append(rewrap(block) if changed else block)
    return "\n\n".join(out)


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
        self.rows = None    # for a folder's CLAUDE.md: where each row of the table came from
        self.autosplit = None   # what the plan says about autosplit, when it plans the config item

    def add(self, item, path, verb, do=None):
        self.actions.append((item, path.replace("\\", "/"), verb, do))

    def file(self, item, relative, content, note=""):
        full = os.path.join(self.root, relative)
        if os.path.exists(full):
            self.add(item, relative, "kept (exists)")
            return
        def do(full=full, content=content):
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        self.add(item, relative, "create" + note, do)


def repository_config(enabled):
    """A repository's new .claude/bowline.json: the template as it is, with autosplit turned on when it should be."""
    text = template("bowline.json")
    if enabled:
        off = '"autosplit": {\n    "enabled": false'
        if off not in text:
            raise RuntimeError("templates/bowline.json no longer holds autosplit's enabled key where init looks for it")
        text = text.replace(off, '"autosplit": {\n    "enabled": true')
    return text


def autosplit_state(root, config, asked, below, folder=False):
    """What the plan says about autosplit in the .claude/bowline.json it creates or keeps. config is what the layers say
    today: the layers below the new file when there is none yet, the file with them when it exists."""
    whom = " for the folder and its repositories" if folder else ""
    if not os.path.exists(os.path.join(root, common.CONFIG_FILE)):
        if asked:
            return f"on{whom} in the new file (--autosplit)"
        if below:
            return "on in the new file, as the folder's file has it"
        return f"off; --autosplit turns it on{whom} in the new file"
    if autosplit.settings(config).get("enabled"):
        return "on"
    if asked:
        return ("off: --autosplit changed nothing, because init never edits a file that exists; set autosplit.enabled "
                "to true in it")
    return "off; set autosplit.enabled to true in the file to turn it on"


def about_autosplit(config, folder=False):
    """The sentence after the plans that says what autosplit does and what it may spend, said once for all of them."""
    text = (f"Autosplit, a setting in {common.CONFIG_FILE} and not an item: {autosplit.DOES}, and {autosplit.cost(config)}. "
            "It is off by default because it spends money on your account.")
    if folder:
        text += (f" The folder's {common.CONFIG_FILE} lies under every repository's own, so turned on there it holds for "
                 "each repository bowline may write into, unless the repository's own file turns it off.")
    return text


def build(root, config, only, asked=False):
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
        below = bool(autosplit.settings(config).get("enabled"))
        plan.autosplit = autosplit_state(root, config, asked, below)
        plan.file("config", common.CONFIG_FILE, repository_config(asked or below))
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


PLACEHOLDER = "(say in a line what it is)"
# A description fits a table cell: whole sentences up to this length. A first sentence longer than LONGEST is not a
# one-line description, so the row waits for the person rather than carry half a sentence.
FITS, LONGEST = 160, 240
# The first words of a line that instructs or warns rather than describes.
COMMANDING = re.compile(r"^(never|always|must|stop|important|warning|caution|note|do|don't|dont|before|after|make sure|"
                        r"ensure|remember|please|run|use|read|follow|keep|avoid|only|see|todo)\b", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`(\"'])")


def describing(line):
    """Whether a line of prose may describe a repository: not a heading, a list item, a bold or quoted warning, an
    instruction, a line in capitals, a line that introduces a list (ending with a colon), a table, a comment, a badge
    or an HTML tag."""
    line = line.strip()
    if not line or line.endswith(":"):
        return False
    if line.startswith(("#", "-", "*", "+", ">", "|", "<", "!", "[", "__")) or re.match(r"^\d+[.)]\s", line):
        return False
    if COMMANDING.match(line):
        return False
    letters = [c for c in line if c.isalpha()]
    return not (letters and sum(c.isupper() for c in letters) > 0.6 * len(letters))


def plain(sentence):
    """A sentence as a table cell shows it: a link's text without its address, no bold or italic marks, no pipe."""
    sentence = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", sentence)
    sentence = re.sub(r"(\*\*|__)(.+?)\1", r"\2", sentence)
    return sentence.replace("|", "\\|").strip()


def first_sentences(paragraph):
    """Whole sentences from the start of a paragraph, as many as fit a cell; None when the first alone is too long."""
    sentences = [s.strip() for s in SENTENCE_END.split(" ".join(paragraph.split())) if s.strip()]
    if not sentences or len(sentences[0]) > LONGEST:
        return None
    if not sentences[0].endswith((".", "!", "?")):
        return None
    words = sentences[0]
    for sentence in sentences[1:]:
        if len(words) + 1 + len(sentence) > FITS or not sentence.endswith((".", "!", "?")):
            break
        words += " " + sentence
    return plain(words)


def prose_paragraphs(text, until_section=False):
    """The paragraphs of a Markdown text that may describe it, in order: front matter, code fences, and every line that
    does not describe (see describing) are left out; with until_section, only those before the first '## ' heading,
    the opening of an instruction file, because a description after it belongs to a section, not to the repository."""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        text = text[end + 4:] if end != -1 else text
    paragraphs, current, fenced = [], [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if until_section and line.startswith("## "):
            break
        if not line.strip():
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if describing(line):
            current.append(line.strip())
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def package_description(root):
    """The description a repository's package or project file gives: package.json, pyproject.toml, Cargo.toml, or a
    .csproj at its top folder; (words, file) or (None, None)."""
    for name in ("package.json", "composer.json"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as handle:
                    value = json.load(handle).get("description")
            except (OSError, ValueError, AttributeError):
                value = None
            if isinstance(value, str) and value.strip():
                return value.strip(), name
    for name in ("pyproject.toml", "Cargo.toml"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            match = re.search(r'^description\s*=\s*"([^"\n]+)"', common.read_text(path), re.MULTILINE)
            if match:
                return match.group(1).strip(), name
    for path in sorted(glob.glob(os.path.join(root, "*.csproj"))):
        match = re.search(r"<Description>([^<]+)</Description>", common.read_text(path))
        if match:
            return match.group(1).strip(), os.path.basename(path)
    return None, None


def describe(root):
    """What a repository is, in a sentence or two, and the file it came from: the README's first paragraph that
    describes, then the package's description, then the first describing sentence at the opening of its CLAUDE.md.
    (None, None) when none of them says it in whole sentences that fit a cell: the row then waits for the person."""
    readmes = sorted(n for n in os.listdir(root) if n.lower() in ("readme.md", "readme", "readme.txt", "readme.rst"))
    for name in readmes:
        for paragraph in prose_paragraphs(common.read_text(os.path.join(root, name))):
            words = first_sentences(paragraph)
            if words:
                return words, name
            break
    value, source = package_description(root)
    if value:
        words = first_sentences(value if value.endswith((".", "!", "?")) else value + ".")
        if words:
            return words, source
    for name in common.root_claude_md(root):
        for paragraph in prose_paragraphs(common.read_text(os.path.join(root, name)), until_section=True):
            words = first_sentences(paragraph)
            if words:
                return words, name
    return None, None


def repository_row(root, described=True):
    """A row of the folder's table, and where its description came from (None: it waits for the person)."""
    words, source = describe(root) if described else (None, None)
    return f"| `{os.path.basename(root)}/` | {words or PLACEHOLDER} |", source


def where_rows_came_from(sources, verbose):
    """The plan's line that says where each row of the table came from, so a person sees why a cell says what it says."""
    groups = {}
    for name, source in sources:
        groups.setdefault(f"from {source}" if source else "for you to fill", []).append(name)
    order = sorted(k for k in groups if k != "for you to fill") + (["for you to fill"] if "for you to fill" in groups else [])
    return "; ".join(f"{key} ({len(groups[key])}): {common.names(sorted(groups[key]), verbose)}" for key in order)


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


def folder_config(setting, asked=False):
    """The folder's .claude/bowline.json: the template, with the writeToRepositories choice and its reason, and
    autosplit on when the person asked for it."""
    data = json.loads(template("bowline.json"))
    if asked:
        data["autosplit"]["enabled"] = True
    data["_writeToRepositories"] = ("Whether bowline writes into the repositories of this folder: true, false, or a list "
                                    "of the names it may write into. With false, init, move and autosplit write nothing into "
                                    "them, and what this folder needs about each one lives here.")
    data["writeToRepositories"] = setting
    return json.dumps(data, indent=2) + "\n"


GATE_HERE = """- **Run the gate before every commit.** In this folder, `python -I .claude/scripts/gate.py --repo <repository>` checks
  the staged lines of a commit in a repository below it, and `python -I .claude/scripts/gate.py` those of this folder's
  own commit: a token-shaped string, a control byte, a carriage return, a byte-order mark, characters the repository
  does not accept, and the words of a private never-commit list. One hit stops the commit and the push. Never print a
  count and go on: a pushed secret cannot be taken back.
"""

GATE_NOT_HERE = """- **No copy of the gate is installed in this folder**, because {why}. When the bowline plugin is installed, its
  hook checks the staged lines of every `git commit` Claude issues in a repository below this folder, and stops it on a
  token-shaped string, a control byte, a carriage return, a byte-order mark, characters the repository does not accept,
  or a word of a private never-commit list. A commit made outside Claude Code is not checked: read its staged diff for a
  token or a secret before you commit. Never commit past a hit: a pushed secret cannot be taken back.
"""

PUSH_GATE_HERE = """From this folder, run the gate on that repository:

```
python -I .claude/scripts/gate.py --repo <repository>
```

Exit code 0 lets you go on. Any hit stops here: fix the line, stage again, run again. Never commit past a hit."""

PUSH_GATE_NOT_HERE = """No copy of the gate is installed in this folder, because {why}. With the bowline plugin installed, its hook runs the
gate when Claude issues the commit, and stops it on a hit. Without it, read the staged diff (`git diff --cached`) for
a token or a secret yourself. Never commit past a hit."""

BUDGET_HERE = """```
python -I .claude/scripts/budget.py
```

Run in this folder, it measures the folder's own instruction files and every repository's, and refuses when a
`CLAUDE.md` has 200 lines or more, a rules file is over its size, an area's rules load more than their budget
together, a `SKILL.md` has 500 lines or more, or an instruction file names a path outside its repository.
`.claude/README.md` says why these sizes."""

BUDGET_NOT_HERE = """`/bowline:doctor`, in a session started in this folder, measures the folder's own instruction files and every
repository's against the sizes Claude Code reads, and says what to do about each finding. No copy of the size check is
installed here, because {why}."""

README_SCRIPTS_ROW = ("| `scripts/` | The checks the rules name: the commit gate (`gate.py`) and the size budget of the instruction "
                      "files (`budget.py`), copies of bowline's, so a contributor without the plugin runs the same checks. | Run "
                      "by the skills and the pre-commit hook |\n")

README_GATE_HERE = """`scripts/gate.py` reads the staged diff and refuses a commit whose added lines hold a token, a control byte, a
carriage return, a byte-order mark, a character outside the accepted set when `bowline.json` says so, or a word from a
private list at `~/.claude/private/never-commit.txt` when that file exists. Run it from this folder: with
`--repo <repository>` it gates a commit in a repository below, and without it this folder's own commit. To have git run
it on this folder's own commits, once:

```
git config core.hooksPath .githooks
```

A repository below gets a gate of its own only from its own scaffold (`bowline init --each`)."""

README_GATE_NOT_HERE = """No copy of the gate is installed here, because {why}. With the bowline plugin installed, its hook checks every
`git commit` Claude issues in a repository below this folder and refuses one whose added lines hold a token, a control
byte, a carriage return, a byte-order mark, a character outside the accepted set, or a word from a private list at
`~/.claude/private/never-commit.txt` when that file exists."""


def folder_template(name, git_folder, gate_here, why):
    """A template of the folder scaffold, in words true for a folder, with the passages that depend on the gate filled
    for what is really installed: the copy of the gate when there is one, else the plugin's hook and why there is none."""
    text = template(f"folder/{name}")
    values = {
        "and_folder": ", and in this folder itself" if git_folder else "",
        "gate": (GATE_HERE if gate_here else GATE_NOT_HERE.format(why=why)) if name.startswith("rules/") else
                (PUSH_GATE_HERE if gate_here else PUSH_GATE_NOT_HERE.format(why=why)) if name.startswith("skills/") else
                (README_GATE_HERE if gate_here else README_GATE_NOT_HERE.format(why=why)),
        "budget": (BUDGET_HERE if gate_here else BUDGET_NOT_HERE.format(why=why)) if name.startswith("skills/") else
                  ("`scripts/budget.py` checks these; `bowline doctor` explains each finding." if gate_here else
                   "`bowline doctor` checks these and explains each finding."),
        "scripts_row": README_SCRIPTS_ROW if gate_here else "",
    }
    values = {key: value.rstrip("\n") if key != "scripts_row" else value for key, value in values.items()}
    return fill(text, values, ("and_folder", "gate", "budget"))


def build_folder(folder, roots, only, leave=False, described=True, verbose=False, asked=False):
    """The scaffold for a folder of repositories: its own CLAUDE.md, an index of the repositories with the sections every
    root file needs, and the shared .claude/bowline.json; the .claude/README.md, starter rules and skills too when the
    folder keeps the files of repositories bowline leaves untouched; and, when the folder is a git repository of its
    own, the .gitignore lines that keep its repositories out of it. The repositories get their own scaffold with --each."""
    plan = Plan(folder, common.load_config(folder))
    setting = folder_setting(folder, leave)
    keeps = any(not common.allowed_by(setting, r) for r in roots)
    git_folder = common.is_repository(folder)
    default = ["claude-md", "config"] + (["claude-readme", "rules", "skills"] if keeps else [])
    default += ["scripts", "githook", "gitignore"] if git_folder else []
    wanted = set(only) if only else set(default)
    # The rules, skills and README name the folder's copy of the gate only when there is one, or one is being written.
    gate_here = git_folder and ("scripts" in wanted or os.path.isfile(os.path.join(folder, ".claude", "scripts", "gate.py")))
    why = "the scripts item was not written here" if git_folder else "this folder is not a git repository"
    without = "" if gate_here else (" (without the gate: add scripts to install it)" if git_folder else
                                    " (without the gate: this folder is not a git repository)")
    if "claude-md" in wanted:
        compact = "".join(body for title, body in sections_of(template("CLAUDE.md.sections.md")) if title.lower() == "compact instructions")
        rows = [repository_row(root, described) for root in roots]
        plan.rows = where_rows_came_from([(os.path.basename(r), source) for r, (_, source) in zip(roots, rows)], verbose)
        if not described:
            plan.rows += " (--no-describe)"
        text = fill(template("CLAUDE.md.folder.md"),
                    {"about": about_folder(folder, len(roots)), "rules_for_one": rules_for_one(roots, setting),
                     "rows": "\n".join(row for row, _ in rows), "compact": compact},
                    ("about", "rules_for_one"))
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
        plan.file("claude-readme", ".claude/README.md", folder_template("claude-readme.md", git_folder, gate_here, why), without)
    if "rules" in wanted:
        plan.file("rules", ".claude/rules/before-a-commit.md",
                  folder_template("rules/before-a-commit.md", git_folder, gate_here, why), without)
        plan.file("rules", ".claude/rules/recording-decisions.md", folder_template("rules/recording-decisions.md", git_folder, gate_here, why))
    if "skills" in wanted:
        for name in ("full-checks", "push"):
            plan.file("skills", f".claude/skills/{name}/SKILL.md",
                      folder_template(f"skills/{name}/SKILL.md", git_folder, gate_here, why), without)
    if "scripts" in wanted:
        for name in ("common.py", "gate.py", "budget.py"):
            plan.file("scripts", f".claude/scripts/{name}", common.read_text(os.path.join(SCRIPTS, name)))
        plan.file("scripts", ".claude/scripts/defaults.json", common.read_text(common.defaults_path()))
    if "githook" in wanted:
        plan.file("githook", ".githooks/pre-commit", template("githooks/pre-commit"))
    if "config" in wanted:
        plan.autosplit = autosplit_state(folder, plan.config, asked, False, folder=True)
        plan.file("config", common.CONFIG_FILE, folder_config(setting, asked))
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
            own = [l for l in missing if l in GITIGNORE_LINES[1:]]
            repos = [l for l in missing if l not in GITIGNORE_LINES[1:]]
            said = ", ".join(own) + (", and " if own and repos else "") + (
                f"a line for each of {common.count(len(repos), 'repository', 'repositories')} ({common.names(repos, verbose)})"
                if repos else "")
            plan.add("gitignore", ".gitignore", "append entries: " + said, do)
    return plan


def which_repositories(own, kept, total, setting, verbose):
    """What bowline does with the folder's repositories, each list said once with its count and its reason, the names
    capped at ten unless verbose: the folder of a hundred repositories is two lines, not two pages."""
    lines = []
    whole = common.count(total, "repository", "repositories")
    if own:
        share = f"Its {whole}" if len(own) == total else f"{len(own)} of its {whole}"
        verb = "gets its" if len(own) == 1 else "get their"
        lines.append(f"{share} ({common.names(own, verbose)}) {verb} own scaffold with --each.")
    if kept:
        share = f"its {whole}" if len(kept) == total else f"{len(kept)} of its {whole}"
        why = ("the folder's .claude/bowline.json sets writeToRepositories to false" if not isinstance(setting, list) else
               "the folder's .claude/bowline.json lists in writeToRepositories only the repositories bowline may write into")
        lines.append(f"bowline writes nothing into {share} ({common.names(kept, verbose)}), because {why}: what this folder "
                     "needs about one of them goes in .claude/rules/<repository>/.")
    return lines


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
    parser.add_argument("--no-describe", action="store_true",
                        help="from a folder of repositories: leave every row of CLAUDE.md's table for you to fill, instead of "
                             "describing each repository from its README, its package description or its CLAUDE.md")
    parser.add_argument("--verbose", action="store_true", help="name every repository in a list, not the first ten and how many more")
    parser.add_argument("--autosplit", action="store_true",
                        help="turn autosplit on in the .claude/bowline.json init creates: a headless Claude Code session "
                             "prepares the split of a CLAUDE.md that outgrew the limits, on a branch, and spends money")
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
    if options.autosplit and only and "config" not in only:
        print(f"bowline init: --autosplit turns autosplit on in the {common.CONFIG_FILE} that the config item creates; "
              "add config to --only.", file=sys.stderr)
        return 2
    git_folder = bool(workspace) and common.is_repository(workspace)
    if workspace and not options.each and only and not git_folder and any(i in GATE_ITEMS for i in only):
        print("bowline init: scripts and githook copy the commit gate into this folder, and this folder is not a git "
              "repository, so no commit is made here for the gate to check. Run `git init` in the folder first, then init "
              "again; until then the bowline plugin's hook gates the commits Claude issues in the repositories below.",
              file=sys.stderr)
        return 2
    if root and not common.writes_allowed(root):
        print(f"bowline init: {common.left_alone(root)}. Run init from the folder, {common.folder_of(root)}, to keep its "
              "files there.", file=sys.stderr)
        return 1
    if root:
        plans = [(root, build(root, common.load_config(root), only, options.autosplit))]
    elif options.each:
        allowed = [r for r in roots if common.writes_allowed(r)]
        for r in roots:
            if r not in allowed:
                print(f"bowline init: {common.left_alone(r)}; skipped.")
        if not allowed:
            print("bowline init: nothing to do; the folder keeps the files of all its repositories. Run init without --each.")
            return 0
        plans = [(r, build(r, common.load_config(r), only, options.autosplit)) for r in allowed]
    else:
        plans = [(workspace, build_folder(workspace, roots, only, options.leave_repositories,
                                          described=not options.no_describe, verbose=options.verbose,
                                          asked=options.autosplit))]
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
            if item == "claude-md" and plan.rows and do is not None:
                print(f"  {'':14} the table's rows: {plan.rows}")
        if plan.autosplit:
            print(f"  {'autosplit':14} {common.CONFIG_FILE:40} {plan.autosplit}")
        pending = [a for a in plan.actions if a[3] is not None]
        total += len(pending)
        if options.write:
            for item, path, verb, do in pending:
                do()
    offered = [plan for _, plan in plans if plan.autosplit]
    if offered:
        print("\n" + about_autosplit(offered[0].config, folder=bool(workspace) and not options.each))
    if workspace and not options.each:
        setting = folder_setting(workspace, options.leave_repositories)
        own = [os.path.basename(r) for r in roots if common.allowed_by(setting, r)]
        kept = [os.path.basename(r) for r in roots if not common.allowed_by(setting, r)]
        said = which_repositories(own, kept, len(roots), setting, options.verbose)
    if not options.write:
        print(f"\n{total} change(s) would be made. Run with --write to make them; nothing that exists is overwritten.")
        if workspace and not options.each and not git_folder:
            print("This folder is not a git repository. After `git init` in it, init would also offer scripts and githook, "
                  "a copy of the commit gate and the hook that runs it, and write .gitignore entries that keep the "
                  "repositories out of the folder's history.")
        if workspace and not options.each:
            for line in said:
                print(line)
        return 0
    if workspace and not options.each:
        print()
        for line in said:
            print(line)
        then = " then `bowline init --each` for the repositories that get their own scaffold;" if own else ""
        keep = " put what this folder needs about a repository bowline leaves untouched in .claude/rules/<repository>/, scoped with paths;" if kept else ""
        hook = (" run `git config core.hooksPath .githooks` to let git run the gate on this folder's own commits;"
                if any(item == "githook" and do is not None for _, plan in plans for item, _, _, do in plan.actions) else "")
        print(f"{total} change(s) made. Next: say in CLAUDE.md's table what each repository still waiting is, in a line;"
              f"{then}{keep}{hook} and run `bowline doctor`.")
        return 0
    print(f"\n{total} change(s) made. Next: fill the placeholders in .claude/skills/*/SKILL.md, run `git config core.hooksPath .githooks` "
          "to let git run the gate, and run `bowline doctor`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
