"""Prepares the replay of how a decision was once missed, and prints or runs the command that plays it.

    python -I evals/replay.py                 build, and print the command
    python -I evals/replay.py --run           build, and run the command in this terminal
    python -I evals/replay.py --to <folder>   build there, for a test or a look
    python -I evals/replay.py --read          read the newest result: each check's passes, and each reply as a file

The replay is run by Claude Code's own `claude plugin eval`. Each case under evals/decisions/ is a prompt, the graders
that score the reply, and a made-up repository to start in: a small job runner whose page says "Running" after an
export failed, while its manual and the name of a test say "Failed", a comment cites a decision by its date, and the
record of that date says only "all three as recommended". Every case is run with the plugin and without it, and the
report gives both scores and their difference.

Claude Code loads a case only from inside the plugin it tests, and bowline's plugin folder holds only what ships. So
this script copies plugin/ to evals/.build/plugin, which git ignores, and puts the cases into the copy's evals/
folder. It writes each case's fixture.sh there, a bash script that holds the made-up repository's files, so that the
script needs nothing beside itself; the cases that have the starter rule take it from plugin/templates as it is now.

Claude Code starts a session of the replay with the user's settings only, so the made-up repository's CLAUDE.md and
its rules are files on its disk and never instructions. A case that has the rule therefore hands the rule's text to
the session itself, in its prompt.md as `append_system_prompt`, written into the copy by this script. The first full
run was made before this was known: in it no session had the rule in front of it, in any case.

What the command does, so that the person who runs it knows: it starts real Claude Code sessions on their account,
about thirty with the defaults (three cases, five runs each, with and without the plugin), and stops starting new ones
at --max-cost-usd, 15 dollars by default. --scaffold lets each case's fixture.sh run, as that person, in an empty
temporary folder. --allow-tools Edit Write lets a session change files in that folder, because what a case measures is
whether it does. --no-publish keeps the report on this machine. The first run asks whether the copy is a plugin folder
to trust; that answer is the person's to give, so this script never passes --trust-plugin.

On Windows a case cannot be given a shell without WSL, so the sessions read and search with Claude Code's own tools
and never run `bowline decisions find`; the lookup has its own tests in tests/test_decisions.py.

Also on Windows, `claude plugin eval` starts each fixture.sh with the first `bash` on the search path and hands it the
script's path with its backslashes. Where that first bash is the one that starts WSL, the backslashes are lost and
every run ends with "scaffold failed (exit 127)" before a session starts. Git's own bash reads such a path as it is,
so --run puts Git's bash first on the path of the command it starts, and says so. The first run a person made here
stopped on exactly this.
"""

import argparse
import json
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
# The line Claude Code puts above a rule file it loads at a session's start.
LOADED = "Contents of .claude/rules/recording-decisions.md (project instructions, checked into the codebase):"
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


def with_the_rule_in_front(prompt, rule):
    """A case's prompt.md with the rule's text added to what the session is told at its start. Claude Code starts a
    session of the replay with the user's settings only, so the made-up repository's CLAUDE.md and its rules are
    files on its disk and never instructions; a one-turn control showed it, and Claude Code's page on memory says it.
    A real session has the rule loaded from its first moment, so a case that has the rule hands the text over itself,
    under the line Claude Code puts above a rule it loads."""
    head, body = prompt.split("\n---\n", 1)
    lines = [LOADED, ""] + rule.rstrip("\n").split("\n")
    block = "\n".join("  " + line if line else "" for line in lines)
    return f"{head}\nappend_system_prompt: |\n{block}\n---\n{body}"


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
        if name not in WITHOUT_THE_RULE:
            prompt = os.path.join(case, "prompt.md")
            told = with_the_rule_in_front(read(prompt), read(RULE))
            with open(prompt, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(told)
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
    if options.keep_temp:
        out.append("--keep-temp")
    if options.with_only:
        out += ["--ablation", "none"]
    return out


def shown(parts):
    return " ".join(f'"{part}"' if " " in part else part for part in parts)


def git_bash():
    """On Windows, the bash that comes with Git, or None when there is none. It is found from where git itself is:
    git.exe is in Git's cmd folder or in its mingw64/bin folder, and bash.exe is in the bin folder beside them."""
    git = shutil.which("git")
    if not git:
        return None
    top = os.path.dirname(git)
    for _ in (1, 2):
        top = os.path.dirname(top)
        for sub in ("bin", os.path.join("usr", "bin")):
            candidate = os.path.join(top, sub, "bash.exe")
            if os.path.isfile(candidate):
                return candidate
    return None


def environment_for_the_run():
    """The environment the command is started in, and a sentence for the person when it differs from their own.
    Only Windows needs a change: there the first bash on the path must be Git's, as the note at the top says. With
    no bash of Git's on the machine the environment is None, and the sentence says why nothing is started."""
    environment = dict(os.environ)
    if os.name != "nt":
        return environment, ""
    bash = git_bash()
    if not bash:
        return None, ("bowline replay: nothing was started. On Windows each case's fixture.sh needs the bash that comes "
                      "with Git, and no Git was found on the search path.")
    first = shutil.which("bash")
    folder = os.path.dirname(bash)
    if first and os.path.normcase(os.path.dirname(os.path.abspath(first))) == os.path.normcase(folder):
        return environment, ""
    environment["PATH"] = folder + os.pathsep + environment.get("PATH", "")
    return environment, (f"For this command only, {folder} is put first on the search path, so that each case's "
                         f"fixture.sh is run by Git's bash and not by {first or 'no bash at all'}.")


def newest_result():
    top = os.path.join(HERE, "results")
    names = sorted(name for name in os.listdir(top) if os.path.isfile(os.path.join(top, name, "aggregate-result.json"))) \
        if os.path.isdir(top) else []
    return os.path.join(top, names[-1]) if names else None


def read_result(folder):
    """Prints, for the result in this folder, how many runs passed each check with the plugin and without it, and
    writes each session's reply to a file under replies/. A case's score is one number, and what matters is which
    check failed and what the session said: the first full run was read this way, and a check that had passed a
    reply it should not have was found by reading the reply, not the score."""
    path = os.path.join(folder, "aggregate-result.json")
    if not os.path.isfile(path):
        print(f"bowline replay: {folder} holds no aggregate-result.json, so there is no result to read.", file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    replies = os.path.join(folder, "replies")
    os.makedirs(replies, exist_ok=True)
    runs_in_all = sum(len(runs) for case in data["cases"] for runs in case["arms"].values())
    print(f"bowline replay: {runs_in_all} sessions, {data.get('costUsd', 0):.2f} dollars, in {folder}.")
    for case in data["cases"]:
        arms = list(case["arms"])
        checks, passes = [], {}
        for arm in arms:
            for number, run in enumerate(case["arms"][arm], 1):
                reply, failed, skipped = "", [], []
                for grader in run["graders"]:
                    if grader["name"] not in checks:
                        checks.append(grader["name"])
                    passes.setdefault((grader["name"], arm), [])
                    # A check the cost cap skipped judged nothing: it is neither a pass nor a miss.
                    if str(grader.get("explanation") or "").startswith("skipped"):
                        skipped.append(grader["name"])
                        continue
                    passes[(grader["name"], arm)].append(bool(grader["passed"]))
                    if not grader["passed"]:
                        failed.append(grader["name"])
                    reply = grader.get("evidence") or reply
                left = f" Skipped at the cost cap: {', '.join(skipped)}." if skipped else ""
                head = (f"{case['name']}, {arm} the plugin, run {number}: score {run['score']:.2f}, {run['turns']} turns, "
                        f"{run['costUsd']:.2f} dollars.\nFailed: {', '.join(failed) or 'nothing'}.{left}\n\n")
                with open(os.path.join(replies, f"{case['name']}.{arm}.{number}.md"), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(head + (reply or "(The result holds no reply for this run.)") + "\n")
        print()
        print(case["name"])
        width = max(len(check) for check in checks) + 2
        print("  " + "check".ljust(width) + "".join(arm.ljust(10) for arm in arms))
        for check in checks:
            cells = []
            for arm in arms:
                marks = passes.get((check, arm))
                cells.append(("-" if not marks else f"{sum(marks)} of {len(marks)}").ljust(10))
            print("  " + check.ljust(width) + "".join(cells).rstrip())
    print()
    print(f"Each session's reply is a file in {replies}. Read them: a check is a first pass, and only a person can say "
          "whether the choices in a reply are complete and fair.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepares the replay of how a decision was once missed, and prints or runs its command.")
    parser.add_argument("--read", nargs="?", const="", metavar="FOLDER",
                        help="build and start nothing: print each check's passes for the result in this folder (default: "
                             "the newest under evals/results) and write each session's reply to a file beside it")
    parser.add_argument("--run", action="store_true", help="run the command in this terminal, after the build")
    parser.add_argument("--to", metavar="FOLDER", help="where the copy of the plugin is built (default: evals/.build/plugin)")
    parser.add_argument("--runs", type=int, default=5, help="how many times each case is run with the plugin, and without it (default: 5)")
    parser.add_argument("--concurrency", type=int, default=3, help="how many sessions run at once (default: 3)")
    parser.add_argument("--max-cost-usd", type=float, default=15, help="the spending cap, in dollars, after which no new session starts (default: 15)")
    parser.add_argument("--case", help="only the cases whose name matches this pattern")
    parser.add_argument("--model", help="a model for every session (default: the account's own)")
    parser.add_argument("--keep-temp", action="store_true",
                        help="keep each session's temporary folder, to read in its out/trace.jsonl what the session was "
                             "given and what it did; remove the folders afterwards, as the command's own lines say")
    parser.add_argument("--with-only", action="store_true",
                        help="run each case with the plugin only, and not without it: half the sessions, to try a change "
                             "to the plugin against a result that already has the runs without it")
    options = parser.parse_args(argv)
    if options.read is not None:
        folder = os.path.abspath(options.read) if options.read else newest_result()
        if not folder:
            print("bowline replay: there is no result under evals/results yet.", file=sys.stderr)
            return 2
        return read_result(folder)
    target = os.path.abspath(options.to or BUILD)
    names = build(target)
    results = os.path.join(HERE, "results", time.strftime("%Y-%m-%d-%H%M%S"))
    parts = command(target, options, results)
    runs = len(names) * options.runs * (1 if options.with_only else 2)
    print(f"bowline replay: {len(names)} cases built in {target}: {', '.join(names)}.")
    arms = "every one with the plugin" if options.with_only else "half of them without the plugin"
    print(f"The command starts about {runs} Claude Code sessions on your account, {arms}, and "
          f"starts no new one after {options.max_cost_usd:g} dollars. Its report goes to {results}.")
    print("The first time, it asks whether you trust the folder it was built in; that answer is yours.")
    print()
    print(shown(parts))
    if not options.run:
        if os.name == "nt":
            print()
            print("On Windows, start it with --run and not by copying the line above: --run makes sure that each case's "
                  "fixture.sh is run by Git's bash.")
        return 0
    program = shutil.which("claude")
    if not program:
        print("bowline replay: the claude command was not found on this machine.", file=sys.stderr)
        return 2
    environment, sentence = environment_for_the_run()
    if environment is None:
        print(sentence, file=sys.stderr)
        return 2
    if sentence:
        print(sentence)
    sys.stdout.flush()
    return subprocess.call([program] + parts[1:], env=environment)


if __name__ == "__main__":
    sys.exit(main())
