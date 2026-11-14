"""A stand-in for the claude command in bowline's tests. It records how it was called, then behaves as the mode in
FAKE_CLAUDE_MODE says: "split" makes the two commits of a finished split in the working folder, "half" makes the
first commit and leaves a file uncommitted, "nothing" changes nothing. It prints the JSON result a headless session
prints, so the worker's reading of the cost and the session id is tested too."""

import json
import os
import re
import subprocess
import sys


def git(*args):
    subprocess.run(["git", *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write(path, text):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main():
    mode = os.environ.get("FAKE_CLAUDE_MODE", "split")
    with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "mode": mode,
                                 "worker": os.environ.get("BOWLINE_AUTOSPLIT_WORKER"),
                                 "claudecode": os.environ.get("CLAUDECODE"),
                                 "parent_session": os.environ.get("CLAUDE_CODE_SESSION_ID")}) + "\n")
    prompt = sys.argv[-1]
    found = re.search(r"instruction file (\S+CLAUDE\.md)", prompt)
    path = found.group(1) if found else "CLAUDE.md"
    if mode in ("split", "half"):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        write("docs/conventions/moved.md", "# The long form, moved\n\n" + text)
        write(path, "# Index\n\nThe long form is in docs/conventions/moved.md; the rules are under .claude/rules/.\n")
        git("add", "-A")
        git("commit", "-q", "-m", "Move the sections of " + path + " into a page\n\n"
            "Proposal: both sections became the page docs/conventions/moved.md; the index stays.")
        if mode == "split":
            write(".claude/rules/moved.md",
                  "---\npaths:\n  - \"sub/**\"\n---\n\n# Rules for sub\n\n"
                  "- **State a rule once.** The long form is in docs/conventions/moved.md.\n")
            git("add", "-A")
            git("commit", "-q", "-m", "Condense the page into a rule\n\nMAP: 2 entries, 1 RULE, 1 PAGE-ONLY.")
        else:
            write("left-over.txt", "not committed\n")
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": 0.42,
                      "num_turns": 3, "session_id": "fake-session", "result": "The split is done."}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
