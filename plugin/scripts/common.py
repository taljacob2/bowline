"""What bowline's scripts share: where the repository and Claude Code's folders are, the configuration, and how a finding
is printed. Standard library only; Python 3.8 or later; Windows, Linux and macOS alike."""

import fnmatch
import json
import os
import re
import subprocess
import sys
import threading

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = ".claude/bowline.json"
# Claude Code reads both of these as the project's instructions, whole, at a session's start (docs/facts.md).
ROOT_CLAUDE_MD = ("CLAUDE.md", ".claude/CLAUDE.md")


def is_root_claude_md(path):
    """Whether a CLAUDE.md, by its path relative to the repository or the folder, is a root file: one of the two places
    Claude Code reads whole at a session's start and again after a compaction, never cut on demand like a nested one."""
    return path.replace("\\", "/") in ROOT_CLAUDE_MD


def root_claude_md(root):
    """The root CLAUDE.md files that exist under a repository or a folder, by their path relative to it."""
    return [path for path in ROOT_CLAUDE_MD if os.path.isfile(os.path.join(root, path))]


def run_git(args, cwd=None, check=True):
    """Runs git and returns its stdout as text. Exits with code 2 when git is missing or fails and check is set."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)
    except FileNotFoundError:
        print("bowline: git was not found on this machine.", file=sys.stderr)
        sys.exit(2)
    if check and result.returncode != 0:
        print("bowline: git failed: " + result.stderr.decode("utf-8", "replace").strip(), file=sys.stderr)
        sys.exit(2)
    return result.stdout.decode("utf-8", "replace")


# What a run learns about the folders' layout, kept for the rest of the run: which folder is a repository's top, and which
# repositories a folder holds. A doctor over a folder of N repositories asked both for each repository, and each answer
# rescanned the folder and started git, about N squared calls, minutes on a slow mount. A run of bowline is short and
# creates no repository, so an answer stays true for it; file listings are never kept, since a run writes files.
_LAYOUT = {}
_LAYOUT_LOCK = threading.Lock()


def _remembered(kind, path, compute):
    key = (kind, os.path.normcase(os.path.normpath(os.path.abspath(path))))
    with _LAYOUT_LOCK:
        if key in _LAYOUT:
            return _LAYOUT[key]
    value = compute()
    with _LAYOUT_LOCK:
        _LAYOUT.setdefault(key, value)
        return _LAYOUT[key]


def forget_layout():
    """Drops what the run learned about the folders' layout, for a caller that changes it."""
    with _LAYOUT_LOCK:
        _LAYOUT.clear()


def repo_root(start=None):
    """The repository's top folder for the given path, or None when it is not inside a git repository."""
    start = start or os.getcwd()

    def compute():
        result = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"], capture_output=True)
        if result.returncode != 0:
            return None
        return os.path.normpath(result.stdout.decode("utf-8", "replace").strip())
    return _remembered("root", start, compute)


def child_repositories(folder):
    """The git repositories directly under a folder: every child that holds a .git entry (a folder, or a worktree's file)."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.normpath(os.path.join(folder, name)) for name in names
            if not name.startswith(".") and os.path.isdir(os.path.join(folder, name))
            and os.path.exists(os.path.join(folder, name, ".git"))]


def untracked_child_repositories(root):
    """The git repositories directly under a repository's top folder that the repository does not track: repositories
    kept side by side inside one that holds only what they share. A submodule is tracked, so it is not one of them.
    One git call for all of them: the tracked paths under any child, by their first part."""
    children = child_repositories(root)
    if not children:
        return []
    names = [os.path.basename(child) for child in children]
    out = run_git(["-C", root, "ls-files", "-z", "--", *names], check=False)
    tracked = {path.replace("\\", "/").split("/")[0] for path in out.split("\0") if path}
    return [child for child, name in zip(children, names) if name not in tracked]


def count(number, one, many):
    """A number with its noun: 1 repository, 2 repositories."""
    return f"{number} {one if number == 1 else many}"


def names(items, verbose=False, limit=10):
    """A list of names as a reader takes it in: all of them up to the limit, else the first ones and how many more, so
    a folder of a hundred repositories is one line, not a page. verbose lists every one."""
    items = list(items)
    if verbose or len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f" and {len(items) - limit} more"


def is_repository(folder):
    """Whether a folder is the top folder of a git repository."""
    return folder is not None and repo_root(folder) == os.path.normpath(os.path.abspath(folder))


def roots_for(start=None):
    """Where bowline works from a path, as (folder of repositories or None, repository roots). A folder of repositories
    holds repositories side by side, as with services cloned next to one another: either a plain folder, or a git
    repository of its own that holds what they share and does not track them. From one: (the folder, their roots).
    Inside any other repository: (None, [its root]). Anywhere else: (None, []). Worked out once per run and path."""
    workspace, roots = _remembered("roots", start or os.getcwd(), lambda: _roots_for(start))
    return workspace, list(roots)


def _roots_for(start):
    root = repo_root(start)
    if root:
        children = untracked_child_repositories(root)
        return (root, children) if children else (None, [root])
    folder = os.path.normpath(os.path.abspath(start or os.getcwd()))
    repos = child_repositories(folder)
    return (folder if repos else None), repos


def folder_of(root):
    """The folder of repositories a repository sits in directly, or None when it sits in none."""
    root = os.path.normpath(root)
    parent = os.path.dirname(root)
    if not parent or parent == root:
        return None
    workspace, roots = roots_for(parent)
    return workspace if workspace and root in roots else None


def writes_allowed(root):
    """Whether bowline may write into this repository. Always, unless it sits in a folder of repositories whose own
    .claude/bowline.json sets writeToRepositories to false, or to a list of names that leaves it out. A repository's own
    file cannot change this: the choice is the folder's, made by the person who works from it."""
    folder = folder_of(root)
    if folder is None:
        return True
    return allowed_by(load_config(folder).get("writeToRepositories", True), root)


def allowed_by(setting, root):
    """What a writeToRepositories value says about one repository: true, false, or a list of the names allowed."""
    if isinstance(setting, list):
        return os.path.basename(os.path.normpath(root)) in setting
    return bool(setting)


def left_alone(root, name=None):
    """Why bowline writes nothing into this repository, in one sentence, for every message that says so. name stands in
    for the repository's own when one sentence speaks for several (the doctor's grouped findings)."""
    name = name or os.path.basename(os.path.normpath(root))
    setting = load_config(folder_of(root) or root).get("writeToRepositories", True)
    if isinstance(setting, list):
        return (f"bowline leaves {name} untouched: the folder's {CONFIG_FILE} lists in writeToRepositories the "
                f"repositories bowline may write to, and {name} is not one of them")
    return f"bowline leaves {name} untouched: the folder's {CONFIG_FILE} sets writeToRepositories to false"


def left_alone_fix(root, name=None):
    """What a person can do about a finding in a repository bowline leaves untouched."""
    name = name or os.path.basename(os.path.normpath(root))
    return (f"{left_alone(root, name)}. Ask the repository's owners to change it, or put what this folder needs about {name} "
            f"in the folder's .claude/rules/{name}/, with paths: [\"{name}/**\"] in each rule's front matter.")


def main_checkout(start=None):
    """The repository's main checkout, even from a worktree: Claude Code keys the memory folder on it. Outside a
    repository, the folder itself: Claude Code keys the memory of a session started there on that folder."""
    if repo_root(start) is None:
        return os.path.normpath(os.path.abspath(start or os.getcwd()))
    out = run_git(["-C", start or os.getcwd(), "rev-parse", "--path-format=absolute", "--git-common-dir"]).strip()
    common = os.path.normpath(out)
    if os.path.basename(common) == ".git":
        return os.path.dirname(common)
    return repo_root(start)


def config_dir():
    """Claude Code's configuration folder: CLAUDE_CONFIG_DIR, or ~/.claude."""
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def project_folder_name(checkout):
    """Claude Code's name for a project's folder: the checkout's path with every character other than a letter or a digit
    replaced by a dash. Observed, not documented; the doctor says so when the folder is missing."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(checkout))


def project_folder(checkout):
    return os.path.join(config_dir(), "projects", project_folder_name(checkout))


def memory_folder(checkout):
    return os.path.join(project_folder(checkout), "memory")


def expand_path(path):
    """Expands ~ and environment variables, so the configuration can name a file under the home folder."""
    return os.path.expandvars(os.path.expanduser(path))


def deep_merge(base, over):
    out = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def defaults_path():
    """defaults.json beside the plugin, or beside the scripts when they are a repository-local copy."""
    for folder in (PLUGIN_ROOT, os.path.dirname(os.path.abspath(__file__))):
        path = os.path.join(folder, "defaults.json")
        if os.path.isfile(path):
            return path
    print("bowline: defaults.json was not found beside the scripts.", file=sys.stderr)
    sys.exit(2)


def load_config(root):
    """The plugin's defaults, with the repository's .claude/bowline.json laid over them when it exists. A repository that
    sits in a folder of repositories gets that folder's .claude/bowline.json laid in between, as the layer they share."""
    with open(defaults_path(), encoding="utf-8") as handle:
        config = json.load(handle)
    if not root:
        return config
    layers = []
    parent = os.path.dirname(os.path.normpath(root))
    if parent and parent != os.path.normpath(root) and os.path.isfile(os.path.join(parent, CONFIG_FILE)) and folder_of(root):
        layers.append(os.path.join(parent, CONFIG_FILE))
    layers.append(os.path.join(root, CONFIG_FILE))
    for path in layers:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                try:
                    config = deep_merge(config, json.load(handle))
                except json.JSONDecodeError as problem:
                    print(f"bowline: {path} is not valid JSON ({problem}); using what is below it.", file=sys.stderr)
    return config


def tracked_files(root, pattern):
    """Files matching the pattern that git tracks or would add: committed, staged and untracked, ignored ones left out.
    In a folder that is not a repository, the files on disk under it, leaving out its child repositories (each is
    measured on its own), .git folders and node_modules."""
    if repo_root(root) is None:
        return walk_files(root, pattern)
    out = run_git(["-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", pattern])
    return sorted({p for p in out.split("\0") if p})


def listed_files(root):
    """Every file under a repository that git tracks or would add (committed, staged and untracked, ignored ones left
    out), or under a folder that is not one every file on disk but its child repositories': one listing, which a caller
    filters with matching(), so measuring a repository asks git once rather than once per pattern."""
    if repo_root(root) is None:
        return walk_files(root, ".")
    out = run_git(["-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"])
    return sorted({p for p in out.split("\0") if p})


def matching(files, pattern):
    """The paths of a listing that a git-style pattern matches, as tracked_files would give them: '*' crosses folders."""
    return [path for path in files if pattern == "." or fnmatch.fnmatchcase(path, pattern)]


def walk_files(root, pattern):
    """The files under a folder whose path, relative to it, matches a git-style pattern ('.' means every file); child
    repositories, .git folders and node_modules are not entered."""
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "node_modules") and not os.path.exists(os.path.join(folder, d, ".git")))
        rel_folder = os.path.relpath(folder, root).replace("\\", "/")
        for name in files:
            rel = name if rel_folder == "." else rel_folder + "/" + name
            if pattern == "." or fnmatch.fnmatchcase(rel, pattern):
                found.append(rel)
    return sorted(found)


def read_text(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        return handle.read()


def count_lines(text):
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


# A commit as a note names it: 7 to 40 lowercase hexadecimal digits, standing alone. A hyphen, an underscore or a slash
# next to it means part of a longer id or of a path, such as a session's UUID or a job's folder, so it does not count.
COMMIT = re.compile(r"(?<![0-9A-Za-z_/\\-])[0-9a-f]{7,40}(?![0-9A-Za-z_/\\-])")


def commits_named(text):
    """The distinct commits a memory note names in its body. The front matter is skipped: it holds ids, not commits.
    A run of hex digits counts only with a letter and a digit in it, so a plain number or a word is never a commit."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return {found for found in COMMIT.findall(text) if re.search(r"[a-f]", found) and re.search(r"[0-9]", found)}


def accepted_characters(values):
    """The configuration's accepted characters, given as the characters themselves or as U+XXXX."""
    out = set()
    for value in values or []:
        text = str(value)
        if re.fullmatch(r"U\+[0-9A-Fa-f]{4,6}", text):
            out.add(int(text[2:], 16))
        else:
            for ch in text:
                out.add(ord(ch))
    return out


class Finding:
    """One thing the doctor or a check found: what it is, why it matters, what to do. level is problem, warning or note."""

    def __init__(self, level, what, why, fix=None, many=None):
        self.level = level
        self.what = what
        self.why = why
        self.fix = fix
        # How the finding reads for several repositories at once, with {count}: "{count} repositories have no root
        # CLAUDE.md." The doctor groups identical findings in a folder of repositories; without one it says "In N
        # repositories: <what>".
        self.many = many
        self.where = None       # the repository's name, in a folder of repositories (doctor.label)
        self.bare = what        # what it found, without the repository's name in front
        self.fix_many = None    # the fix with <repository> for the name, when the fix names the repository
        self.names = None       # for a grouped finding: the repositories it is found in, as a reader takes them in

    def lines(self):
        head = {"problem": "PROBLEM", "warning": "WARNING", "note": "NOTE"}[self.level]
        out = [f"{head}  {self.what}"]
        if self.names:
            out.append(f"         in: {self.names}")
        out.append(f"         why: {self.why}")
        if self.fix:
            out.append(f"         fix: {self.fix}")
        return out


def print_findings(findings, prefix="bowline", counted=None):
    """Prints each finding and the totals; counted, when given, is the list the totals are taken from (the findings one
    by one when those printed are grouped), so the totals and the exit code never depend on the grouping."""
    for finding in findings:
        for line in finding.lines():
            print(line)
        print()
    counted = findings if counted is None else counted
    problems = sum(1 for f in counted if f.level == "problem")
    warnings = sum(1 for f in counted if f.level == "warning")
    notes = sum(1 for f in counted if f.level == "note")
    print(f"{prefix}: {problems} problem(s), {warnings} warning(s), {notes} note(s).")
    return problems
