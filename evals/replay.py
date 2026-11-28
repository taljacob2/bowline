"""Prepares the replay of how a decision was once missed, and prints or runs the command that plays it.

    python -I evals/replay.py                 build, and print the command
    python -I evals/replay.py --run           build, and run the command in this terminal
    python -I evals/replay.py --to <folder>   build there, for a test or a look

The replay is run by Claude Code's own `claude plugin eval`. Each case under evals/decisions/ is a prompt, the graders
that score the reply, and a made-up repository to start in: a small job runner whose page says "Running" after an
export failed, while its manual and the name of a test say "Failed", a comment cites a decision by its date, and the
record of that date says only "all three as recommended". Every case is run with the plugin and without it, and the
report gives both scores and their difference.

Claude Code loads a case only from inside the plugin it tests, and bowline's plugin folder holds only what ships. So
this script copies plugin/ to evals/.build/plugin, which git ignores, and puts the cases into the copy's evals/
folder. It writes each case's fixture.sh there, a bash script that holds the made-up repository's files, so that the
script needs nothing beside itself; the cases that have the starter rule take it from plugin/templates as it is now.

What the command does, so that the person who runs it knows: it starts real Claude Code sessions on their account,
about thirty with the defaults (three cases, five runs each, with and without the plugin), and stops starting new ones
at --max-cost-usd, 15 dollars by default. --scaffold lets each case's fixture.sh run, as that person, in an empty
temporary folder. --allow-tools Edit Write lets a session change files in that folder, because what a case measures is
whether it does. --no-publish keeps the report on this machine. The first run asks whether the copy is a plugin folder
to trust; that answer is the person's to give, so this script never passes --trust-plugin.

On Windows a case cannot be given a shell without WSL, so the sessions read and search with Claude Code's own tools
and never run `bowline decisions find`; the lookup has its own tests in tests/test_decisions.py.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLUGIN = os.path.join(ROOT, "plugin")
CASES = os.path.join(HERE, "decisions")
FIXTURE = os.path.join(CASES, "fixture")
RULE = os.path.join(PLUGIN, "templates", "rules", "recording-decisions.md")
BUILD = os.path.join(HERE, ".build", "plugin")
MARK = ".bowline-replay-build"
END = "BOWLINE_FIXTURE_END"
# The cases whose made-up repository has no rule about recording decisions.
WITHOUT_THE_RULE = ("the-same-without-the-rule",)
# A file of the made-up repository that is kept under another name here, so that bowline's own repository does not
# hold a second CLAUDE.md that Claude Code would load and the doctor would measure.
NAMES = {"CLAUDE.fixture.md": "CLAUDE.md"}


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read().replace("\r\n", "\n")


def fixture_files(with_rule):
    """The made-up repository as (path, text) pairs, the starter rule among them when the case has it."""
    files = []
    for folder, _, names in os.walk(FIXTURE):
        for name in sorted(names):
            path = os.path.relpath(os.path.join(folder, name), FIXTURE).replace("\\", "/")
            parts = path.split("/")
            parts[-1] = NAMES.get(parts[-1], parts[-1])
            files.append(("/".join(parts), read(os.path.join(folder, name))))
    if with_rule:
        files.append((".claude/rules/recording-decisions.md", read(RULE)))
    return sorted(files)


def fixture_script(with_rule):
    """A bash script that writes the made-up repository into the empty folder it is run in and commits it."""
    lines = ["#!/usr/bin/env bash",
             "# Written by evals/replay.py: the made-up repository of this case, as one script that needs nothing else.",
             "set -euo pipefail"]
    for path, text in fixture_files(with_rule):
        if END in text:
            raise RuntimeError(f"{path} holds the line that ends a file in the script, {END}")
        folder = os.path.dirname(path)
        if folder:
            lines.append(f"mkdir -p '{folder}'")
        if not text:
            lines.append(f": > '{path}'")
            continue
        lines += [f"cat > '{path}' <<'{END}'", text.rstrip("\n"), END]
    lines += ["git init -q",
              "git symbolic-ref HEAD refs/heads/main",
              "git config user.name Jobber",
              "git config user.email jobber@example.invalid",
              "git config core.autocrlf false",
              "git add -A",
              "GIT_AUTHOR_DATE=2026-03-03T10:00:00 GIT_COMMITTER_DATE=2026-03-03T10:00:00 "
              "git commit -q -m 'A failed export keeps the job waiting for a retry'"]
    return "\n".join(lines) + "\n"


def case_names():
    return sorted(name for name in os.listdir(CASES) if os.path.isfile(os.path.join(CASES, name, "prompt.md")))


def build(target):
    """Makes the copy of the plugin with the cases in it, and returns the cases' names. A folder that is in the way is
    removed only when an earlier build left its mark in it, so that a mistyped --to never deletes someone's folder."""
    if os.path.exists(target):
        if not os.path.isfile(os.path.join(target, MARK)):
            raise SystemExit(f"bowline replay: {target} exists and is not an earlier build of the replay, so it is left "
                             "alone. Name another folder with --to, or remove it yourself.")
        shutil.rmtree(target)
    shutil.copytree(PLUGIN, target, ignore=shutil.ignore_patterns("__pycache__", "evals"))
    with open(os.path.join(target, MARK), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("A copy of bowline's plugin folder with the replay's cases in it, written by evals/replay.py.\n")
    names = case_names()
    for name in names:
        case = os.path.join(target, "evals", name)
        shutil.copytree(os.path.join(CASES, name), case)
        with open(os.path.join(case, "fixture.sh"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(fixture_script(name not in WITHOUT_THE_RULE))
    return names


def command(target, options, results):
    """The command that plays the replay, as a list. It never holds --trust-plugin: whether the copy is a plugin folder
    to trust is asked of the person in the terminal, the first time."""
    out = ["claude", "plugin", "eval", target, "--scaffold", "--allow-tools", "Edit", "Write",
           "--runs", str(options.runs), "--concurrency", str(options.concurrency),
           "--max-cost-usd", f"{options.max_cost_usd:g}", "--no-publish", "--output-dir", results]
    if options.case:
        out += ["--case", options.case]
    if options.model:
        out += ["--model", options.model]
    return out


def shown(parts):
    return " ".join(f'"{part}"' if " " in part else part for part in parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepares the replay of how a decision was once missed, and prints or runs its command.")
    parser.add_argument("--run", action="store_true", help="run the command in this terminal, after the build")
    parser.add_argument("--to", metavar="FOLDER", help="where the copy of the plugin is built (default: evals/.build/plugin)")
    parser.add_argument("--runs", type=int, default=5, help="how many times each case is run with the plugin, and without it (default: 5)")
    parser.add_argument("--concurrency", type=int, default=3, help="how many sessions run at once (default: 3)")
    parser.add_argument("--max-cost-usd", type=float, default=15, help="the spending cap, in dollars, after which no new session starts (default: 15)")
    parser.add_argument("--case", help="only the cases whose name matches this pattern")
    parser.add_argument("--model", help="a model for every session (default: the account's own)")
    options = parser.parse_args(argv)
    target = os.path.abspath(options.to or BUILD)
    names = build(target)
    results = os.path.join(HERE, "results", time.strftime("%Y-%m-%d-%H%M%S"))
    parts = command(target, options, results)
    runs = len(names) * options.runs * 2
    print(f"bowline replay: {len(names)} cases built in {target}: {', '.join(names)}.")
    print(f"The command starts about {runs} Claude Code sessions on your account, half of them without the plugin, and "
          f"starts no new one after {options.max_cost_usd:g} dollars. Its report goes to {results}.")
    print("The first time, it asks whether you trust the folder it was built in; that answer is yours.")
    print()
    print(shown(parts))
    if not options.run:
        return 0
    program = shutil.which("claude")
    if not program:
        print("bowline replay: the claude command was not found on this machine.", file=sys.stderr)
        return 2
    return subprocess.call([program] + parts[1:])


if __name__ == "__main__":
    sys.exit(main())
