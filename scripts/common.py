"""What keel's scripts share: where the repository and Claude Code's folders are, the configuration, and how a finding
is printed. Standard library only; Python 3.8 or later; Windows, Linux and macOS alike."""

import json
import os
import re
import subprocess
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = ".claude/keel.json"


def run_git(args, cwd=None, check=True):
    """Runs git and returns its stdout as text. Exits with code 2 when git is missing or fails and check is set."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)
    except FileNotFoundError:
        print("keel: git was not found on this machine.", file=sys.stderr)
        sys.exit(2)
    if check and result.returncode != 0:
        print("keel: git failed: " + result.stderr.decode("utf-8", "replace").strip(), file=sys.stderr)
        sys.exit(2)
    return result.stdout.decode("utf-8", "replace")


def repo_root(start=None):
    """The repository's top folder for the given path, or None when it is not inside a git repository."""
    result = subprocess.run(["git", "-C", start or os.getcwd(), "rev-parse", "--show-toplevel"], capture_output=True)
    if result.returncode != 0:
        return None
    return os.path.normpath(result.stdout.decode("utf-8", "replace").strip())


def main_checkout(start=None):
    """The repository's main checkout, even from a worktree: Claude Code keys the memory folder on it."""
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


def load_config(root):
    """The plugin's defaults, with the repository's .claude/keel.json laid over them when it exists."""
    with open(os.path.join(PLUGIN_ROOT, "defaults.json"), encoding="utf-8") as handle:
        config = json.load(handle)
    if root:
        path = os.path.join(root, CONFIG_FILE)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                try:
                    config = deep_merge(config, json.load(handle))
                except json.JSONDecodeError as problem:
                    print(f"keel: {CONFIG_FILE} is not valid JSON ({problem}); using the defaults.", file=sys.stderr)
    return config


def tracked_files(root, pattern):
    """Files matching the pattern that git tracks or would add: committed, staged and untracked, ignored ones left out."""
    out = run_git(["-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", pattern])
    return sorted({p for p in out.split("\0") if p})


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


def print_findings(findings, prefix="keel"):
    for finding in findings:
        for line in finding.lines():
            print(line)
        print()
    problems = sum(1 for f in findings if f.level == "problem")
    warnings = sum(1 for f in findings if f.level == "warning")
    notes = sum(1 for f in findings if f.level == "note")
    print(f"{prefix}: {problems} problem(s), {warnings} warning(s), {notes} note(s).")
    return problems
