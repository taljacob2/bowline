"""The commit gate: refuses a commit whose added lines hold what must never be committed.

    python -I scripts/gate.py                 the staged changes (the normal use; also what the pre-commit hook runs)
    python -I scripts/gate.py --all           every tracked text file, for a one-time sweep
    python -I scripts/gate.py --hook          as a Claude Code PreToolUse hook: reads the hook's JSON on stdin and
                                              answers with exit 2 and the findings when the commit must stop

It looks only at added lines, so an old line that already breaks a rule does not stop a commit that leaves it alone.
It prints the file and the line number of every hit, never the matched text, and exits with 1 when a problem is found.
The policies come from defaults.json, laid over by the repository's .claude/bowline.json (see the gate section there):
token-shaped strings, control bytes, a byte-order mark, a carriage return when the repository is LF only, characters
outside ASCII (ignored, warned about or refused), and the words of a private never-commit list that lives outside every
repository. Exit codes: 0 fine, 1 at least one problem, 2 the script could not run.

As a hook, the gate works out which repository the commit is for from the command itself, `git -C <path>` or
`cd <path> &&` before `commit`, resolved from the hook's working folder, so that a session started in a folder that
holds several repositories is gated too. When it cannot tell which repository is meant, it lets the command through and
says nothing: for a PreToolUse hook exit code 2 means "block", and the gate never blocks on its own confusion.
"""

import argparse
import fnmatch
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

BOM = b"\xef\xbb\xbf"
CONTROL = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def compile_tokens(config):
    patterns = []
    for name, pattern in (config.get("gate", {}).get("tokenPatterns") or {}).items():
        try:
            patterns.append((name, re.compile(pattern.encode("utf-8"))))
        except re.error as problem:
            print(f"bowline gate: the token pattern for '{name}' does not compile ({problem}).", file=sys.stderr)
            sys.exit(2)
    return patterns


def private_patterns(path):
    """The never-commit list: one regular expression per line, matched without regard to case; '#' starts a comment."""
    if not path or not os.path.isfile(path):
        return []
    patterns = []
    with open(path, "rb") as handle:
        for raw in handle:
            line = raw.decode("utf-8", "replace").strip()
            if not line or line.startswith("#"):
                continue
            try:
                patterns.append(re.compile(line.encode("utf-8"), re.IGNORECASE))
            except re.error as problem:
                print(f"bowline gate: the never-commit list has a pattern that does not compile ({problem}).", file=sys.stderr)
                sys.exit(2)
    return patterns


class Policy:
    def __init__(self, config, never_commit_override=None):
        gate = config.get("gate", {})
        self.tokens = compile_tokens(config) if gate.get("tokens", True) else []
        self.control = bool(gate.get("controlBytes", True))
        self.bom = bool(gate.get("byteOrderMark", True))
        self.cr = (gate.get("lineEndings") or "lf").lower() == "lf"
        self.crlf_files = list(gate.get("crlfFiles") or [])
        self.non_ascii = (gate.get("nonAscii") or "warn").lower()
        self.accepted = common.accepted_characters(gate.get("acceptedCharacters"))
        list_path = never_commit_override or gate.get("neverCommitList")
        self.private_path = common.expand_path(list_path) if list_path else None
        self.private = private_patterns(self.private_path)

    def allows_cr(self, path):
        """Whether a carriage return is fine in this file: a Windows batch file, by default."""
        name = os.path.basename(path)
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.crlf_files)


def problems_in(line, policy, path=""):
    """The rules one added line breaks, as (level, rule) pairs. The line is bytes without its line ending."""
    found = []
    for name, pattern in policy.tokens:
        if pattern.search(line):
            found.append(("problem", name))
    if policy.control and CONTROL.search(line):
        found.append(("problem", "a control character"))
    if policy.cr and b"\r" in line and not policy.allows_cr(path):
        found.append(("problem", "a carriage return (the repository is LF only)"))
    if policy.bom and BOM in line:
        found.append(("problem", "a byte-order mark"))
    if policy.non_ascii != "ignore":
        text = line.decode("utf-8", "replace")
        outside = sorted({ord(c) for c in text if ord(c) > 127 and ord(c) not in policy.accepted})
        if outside:
            names = ", ".join(f"U+{code:04X}" for code in outside[:4])
            level = "problem" if policy.non_ascii == "refuse" else "warning"
            found.append((level, f"a character outside ASCII ({names})"))
    if any(p.search(line) for p in policy.private):
        found.append(("problem", "a word from the never-commit list"))
    return found


def staged_added_lines(root):
    """Yields (path, line number, line) for every line the staged changes add."""
    diff = common.run_git(["-C", root, "diff", "--cached", "-U0", "--no-color", "--no-ext-diff"]).encode("utf-8", "surrogateescape")
    path = None
    number = 0
    for raw in diff.split(b"\n"):
        if raw.startswith(b"+++ "):
            target = raw[4:]
            path = None if target == b"/dev/null" else target[2:].decode("utf-8", "replace")
            continue
        if raw.startswith(b"@@"):
            match = re.match(rb"@@ -\S+ \+(\d+)", raw)
            number = int(match.group(1)) if match else 0
            continue
        if path is None or raw.startswith(b"---"):
            continue
        if raw.startswith(b"+"):
            yield path, number, raw[1:]
            number += 1
        elif raw.startswith(b" "):
            number += 1


def all_tracked_lines(root):
    """Yields (path, line number, line) for every line of every tracked text file."""
    for path in common.tracked_files(root, "."):
        try:
            with open(os.path.join(root, path), "rb") as handle:
                content = handle.read()
        except OSError:
            continue
        if b"\0" in content[:8000]:
            continue
        for index, line in enumerate(content.split(b"\n"), start=1):
            yield path, index, line


def run(root, policy, everything=False):
    """Runs the gate and returns (problem lines, warning lines, lines checked)."""
    lines = all_tracked_lines(root) if everything else staged_added_lines(root)
    problems, warnings = [], []
    checked = 0
    for path, number, line in lines:
        checked += 1
        for level, rule in problems_in(line, policy, path):
            (problems if level == "problem" else warnings).append(f"{path}:{number}: {rule}")
    return problems, warnings, checked


def commit_repository(command, start):
    """The repository a `git ... commit` command would commit in: every `cd <path>` and `git -C <path>` before the word
    commit moves the folder on from the hook's working folder; the result is that folder's repository, or None."""
    where = start
    before = re.split(r"\bcommit\b", command, maxsplit=1)[0]
    for match in re.finditer(r"(?:\b(?:cd|pushd)\s+|\bgit\s+-C\s*)(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", before):
        path = match.group(1).strip("\"'")
        where = path if os.path.isabs(path) else os.path.join(where, path)
    return common.repo_root(where)


def run_many(roots, options):
    """The gate over every repository in a folder of them, each with its own policy, the repository named in every line."""
    total = 0
    what = "tracked lines" if options.all else "added lines"
    for root in roots:
        name = os.path.basename(root)
        policy = Policy(common.load_config(root), options.never_commit)
        problems, warnings, checked = run(root, policy, options.all)
        for line in warnings:
            print(f"warning: {name}: {line}")
        for line in problems:
            print(f"{name}: {line}")
        print(f"{name}: {checked} {what} checked, {len(problems)} problem(s), {len(warnings)} warning(s).")
        total += len(problems)
    if total:
        print(f"bowline gate: {total} problem(s) across {common.count(len(roots), 'repository', 'repositories')}. Fix them before committing.")
        return 1
    print(f"bowline gate: nothing found across {common.count(len(roots), 'repository', 'repositories')}.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refuses a commit whose added lines hold what must never be committed.")
    parser.add_argument("--all", action="store_true", help="check every tracked text file instead of the staged diff")
    parser.add_argument("--never-commit", metavar="FILE", help="the private pattern list to use instead of the configured one")
    parser.add_argument("--hook", action="store_true", help="run as a Claude Code PreToolUse hook (JSON on stdin, exit 2 to block)")
    parser.add_argument("--repo", help="a path inside the repository (default: the current folder)")
    options = parser.parse_args(argv)

    if options.hook:
        try:
            facts = json.load(sys.stdin)
        except Exception:
            return 0
        command = str((facts.get("tool_input") or {}).get("command") or "")
        if not re.search(r"\bgit\b.*\bcommit\b", command):
            return 0
        root = commit_repository(command, options.repo or facts.get("cwd") or os.getcwd())
        if not root:
            return 0
    else:
        root = common.repo_root(options.repo)
        if not root:
            workspace, roots = common.roots_for(options.repo)
            if roots:
                return run_many(roots, options)
            print("bowline gate: not inside a git repository, and this folder holds none.", file=sys.stderr)
            return 2
    config = common.load_config(root)
    policy = Policy(config, options.never_commit)

    problems, warnings, checked = run(root, policy, options.all)
    what = "tracked lines" if options.all else "added lines"
    private = "with the never-commit list" if policy.private else "without a never-commit list"
    if problems and options.hook:
        # A hook's stderr is what Claude Code shows as the reason for blocking; stdout would be ignored or duplicated.
        print(f"bowline gate: {len(problems)} problem(s) in {checked} {what}. The commit is blocked until they are fixed.", file=sys.stderr)
        for line in problems[:20]:
            print(line, file=sys.stderr)
        return 2
    for line in warnings:
        print("warning: " + line)
    for line in problems:
        print(line)
    if problems:
        print(f"bowline gate: {len(problems)} problem(s) in {checked} {what}. Fix them before committing.")
        return 1
    if checked == 0 and not options.all:
        print("bowline gate: nothing is staged.")
        return 0
    print(f"bowline gate: {checked} {what} checked, nothing found ({private}; {len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
