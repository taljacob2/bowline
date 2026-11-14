"""What bowline's scripts share: where the repository and Claude Code's folders are, the configuration, and how a finding
is printed. Standard library only; Python 3.8 or later; Windows, Linux and macOS alike."""

import fnmatch
import json
import os
import re
import subprocess
import sys

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


def repo_root(start=None):
    """The repository's top folder for the given path, or None when it is not inside a git repository."""
    result = subprocess.run(["git", "-C", start or os.getcwd(), "rev-parse", "--show-toplevel"], capture_output=True)
    if result.returncode != 0:
        return None
    return os.path.normpath(result.stdout.decode("utf-8", "replace").strip())


def child_repositories(folder):
    """The git repositories directly under a folder: every child that holds a .git entry (a folder, or a worktree's file)."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.normpath(os.path.join(folder, name)) for name in names
            if not name.startswith(".") and os.path.isdir(os.path.join(folder, name))
            and os.path.exists(os.path.join(folder, name, ".git"))]


def roots_for(start=None):
    """Where bowline works from a path, as (folder of repositories or None, repository roots). Inside a repository:
    (None, [its root]). In a folder that is not a repository but holds repositories, as with services cloned side by
    side: (the folder, their roots). Anywhere else: (None, [])."""
    root = repo_root(start)
    if root:
        return None, [root]
    folder = os.path.normpath(os.path.abspath(start or os.getcwd()))
    repos = child_repositories(folder)
    return (folder if repos else None), repos


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
    if parent and parent != os.path.normpath(root) and os.path.isfile(os.path.join(parent, CONFIG_FILE)) and repo_root(parent) is None:
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

    def __init__(self, level, what, why, fix=None):
        self.level = level
        self.what = what
        self.why = why
        self.fix = fix

    def lines(self):
        head = {"problem": "PROBLEM", "warning": "WARNING", "note": "NOTE"}[self.level]
        out = [f"{head}  {self.what}", f"         why: {self.why}"]
        if self.fix:
            out.append(f"         fix: {self.fix}")
        return out


def print_findings(findings, prefix="bowline"):
    for finding in findings:
        for line in finding.lines():
            print(line)
        print()
    problems = sum(1 for f in findings if f.level == "problem")
    warnings = sum(1 for f in findings if f.level == "warning")
    notes = sum(1 for f in findings if f.level == "note")
    print(f"{prefix}: {problems} problem(s), {warnings} warning(s), {notes} note(s).")
    return problems
