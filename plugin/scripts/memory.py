"""The memory backup: Claude Code's memory folder for a repository becomes a git repository pushed to a private remote.

    python -I scripts/bowline.py memory setup <remote> [--repo <path>] [--no-hook] [--python <exe>] [--dry-run]
    python -I scripts/bowline.py memory restore <remote> [--repo <path>]     the same, in a new machine's words
    python -I scripts/bowline.py memory status [--repo <path>]
    python -I scripts/bowline.py memory push [--repo <path>] [--hook]        what the hook runs after every reply
    python -I scripts/bowline.py memory losses [--repo <path>] [--meant <commit>]   lines one session added and another removed

Claude Code keeps notes between sessions in <config>/projects/<project>/memory/, one folder per person per machine,
outside the repository; a lost machine loses them. setup ties that folder to a private remote: when the folder is
missing or empty it clones the remote (a new machine); when it holds notes and the remote is empty it initializes git
and pushes a first backup; when both hold content it stops and says how to merge by hand. Then, unless --no-hook, it
installs a hook for this machine in <config>/settings.json that runs `memory push --hook` after every reply (Stop) and
when a session ends (SessionEnd), with the absolute path of the interpreter that ran setup, so the name of Python on
this machine does not matter. The bowline plugin's own hooks.json does the same for every project once the plugin is
installed; pass --no-hook then.

push commits what changed as "Memory as of <date>" and pushes when the branch is ahead; with --hook it prints nothing
and always exits 0, so a failed push never interrupts a session. A project whose memory folder is not a git
repository is left alone. As a hook, the commit's message also names the session whose reply it follows, in a line
"Session: <id>", the identifier Claude Code gives the hook.

losses reads that line. Every worktree of a repository shares one memory folder, so a session that writes a note whole
from the copy it read earlier erases what another session added in between. losses lists, from the backup's history
of the last crew.memoryLossDays days, every commit after one session's reply that removed lines another session's
commit had added less than crew.memoryLossHours hours before, when those lines are in no note today; the doctor warns
about each. --meant <commit> records that a removal was meant, so that it is not reported again.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HOOK_MARKS = ("bowline", "push-memory")
SESSION_LINE = "Session: "


def git(folder, *args, capture=False):
    result = subprocess.run(["git", "-C", folder, *args], stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                            stderr=subprocess.PIPE if capture else subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
    return (result.returncode, result.stdout.decode("utf-8", "replace") if capture else "")


def folder_has_files(folder):
    return os.path.isdir(folder) and any(os.scandir(folder))


def remote_has_commits(remote):
    code, out = git(".", "ls-remote", "--heads", remote, capture=True)
    if code != 0:
        raise SystemExit(f"bowline memory: the remote {remote} could not be reached.")
    return bool(out.strip())


def memory_for(repo_path):
    checkout = common.main_checkout(repo_path)
    return checkout, common.memory_folder(checkout)


def tie(memory, remote, dry_run):
    if os.path.isdir(os.path.join(memory, ".git")):
        print(f"memory: {memory} is already a git repository; left alone.")
        return
    if not folder_has_files(memory):
        print(f"memory: cloning {remote} into {memory}")
        if not dry_run:
            os.makedirs(os.path.dirname(memory), exist_ok=True)
            if os.path.isdir(memory):
                os.rmdir(memory)
            code, out = git(".", "clone", "-q", remote, memory, capture=True)
            if code != 0:
                raise SystemExit("bowline memory: the clone failed: " + out.strip())
        return
    if remote_has_commits(remote):
        raise SystemExit(
            f"bowline memory: {memory} already holds notes and {remote} already holds commits. Merge them by hand: move the\n"
            "notes aside, clone the remote into the folder, copy the notes back, then commit and push.")
    print(f"memory: {memory} holds notes and the remote is empty; initializing git and pushing the first backup")
    if dry_run:
        return
    for args in (("init", "-q", "-b", "main"), ("add", "-A"), ("commit", "-q", "-m", "The memory folder, first backup"),
                 ("remote", "add", "origin", remote), ("push", "-q", "-u", "origin", "main")):
        code, out = git(memory, *args, capture=True)
        if code != 0:
            raise SystemExit(f"bowline memory: git {' '.join(args)} failed: {out.strip()}")


def hook_entry(python, bowline_py):
    return {"type": "command", "command": python, "args": ["-I", bowline_py.replace("\\", "/"), "memory", "push", "--hook"], "timeout": 60}


def hook_present(groups):
    for group in groups:
        for hook in group.get("hooks", []) or []:
            text = str(hook.get("command", "")) + " " + " ".join(str(a) for a in hook.get("args", []) or [])
            if any(mark in text for mark in HOOK_MARKS):
                return True
    return False


def install_hook(python, dry_run):
    path = os.path.join(common.config_dir(), "settings.json")
    settings = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            settings = json.load(handle)
    hooks = settings.setdefault("hooks", {})
    bowline_py = os.path.join(common.PLUGIN_ROOT, "scripts", "bowline.py")
    changed = False
    for event in ("Stop", "SessionEnd"):
        groups = hooks.setdefault(event, [])
        if hook_present(groups):
            print(f"hook: the {event} hook is already there.")
            continue
        groups.append({"hooks": [hook_entry(python, bowline_py)]})
        changed = True
        print(f"hook: adding the {event} hook to {path}")
    if changed and not dry_run:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(settings, handle, indent=2)
            handle.write("\n")


def hook_installed():
    path = os.path.join(common.config_dir(), "settings.json")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            settings = json.load(handle)
    except Exception:
        return False
    return any(hook_present((settings.get("hooks") or {}).get(event, []) or []) for event in ("Stop", "SessionEnd"))


def do_setup(options, words):
    repo = options.repo or os.getcwd()
    checkout, memory = memory_for(repo)
    project = os.path.dirname(memory)
    if not os.path.isdir(project):
        raise SystemExit(
            f"bowline memory: Claude Code has not made a project folder for {checkout} yet (expected {project}).\n"
            "Start Claude Code once inside the repository, then run this again.")
    print(f"{'repository' if common.repo_root(checkout) else 'folder'}: {checkout}")
    print(f"memory folder: {memory}")
    tie(memory, options.remote, options.dry_run)
    if options.no_hook:
        print("hook: not installed (--no-hook); the bowline plugin's own hook pushes when it is installed.")
    else:
        install_hook(options.python or sys.executable, options.dry_run)
    print("dry run: nothing was changed." if options.dry_run else f"done. {words}")
    return 0


def do_status(options):
    repo = options.repo or os.getcwd()
    checkout, memory = memory_for(repo)
    print(f"{'repository' if common.repo_root(checkout) else 'folder'}: {checkout}")
    print(f"memory folder: {memory}")
    if not os.path.isdir(memory):
        print("state: the folder does not exist yet; Claude Code makes it at the first memory it keeps.")
        return 0
    index = os.path.join(memory, "MEMORY.md")
    if os.path.isfile(index):
        text = common.read_text(index)
        print(f"index: {common.count_lines(text)} lines, {len(text.encode('utf-8')):,} bytes (only the first 200 lines or 25 KB load)")
    notes = [f for f in os.listdir(memory) if f.endswith(".md") and f != "MEMORY.md"]
    print(f"notes: {len(notes)}, the largest first")
    # Each note's size and the commits it names: a note that names many keeps finished work like a log, and is the
    # first one curate-memory trims (the doctor warns at memoryNoteCommits).
    for name in sorted(notes, key=lambda n: (-os.path.getsize(os.path.join(memory, n)), n)):
        text = common.read_text(os.path.join(memory, name))
        print(f"  {name}: {common.count_lines(text)} lines, {len(text.encode('utf-8')):,} bytes, "
              f"{len(common.commits_named(text))} commit(s) named")
    if not os.path.isdir(os.path.join(memory, ".git")):
        print("backup: none. Run: bowline memory setup <private remote>")
        return 1
    _, remote = git(memory, "remote", "get-url", "origin", capture=True)
    _, last = git(memory, "log", "-1", "--no-show-signature", "--format=%ci %s", capture=True)
    _, ahead = git(memory, "rev-list", "--count", "@{u}..HEAD", capture=True)
    _, dirty = git(memory, "status", "--porcelain", capture=True)
    print(f"remote: {remote.strip() or 'none'}")
    print(f"last commit: {last.strip() or 'none'}")
    print(f"not yet pushed: {ahead.strip() or '0'} commit(s); uncommitted changes: {len(dirty.strip().splitlines())} file(s)")
    print(f"hook on this machine: {'installed' if hook_installed() else 'not installed (the plugin hook may cover it)'}")
    return 0


def do_push(options):
    memory = None
    session = ""
    if options.hook:
        try:
            facts = json.load(sys.stdin)
            transcript = facts.get("transcript_path") or ""
            if transcript:
                memory = os.path.join(os.path.dirname(transcript), "memory")
            # The session whose reply this commit follows, so that `memory losses` can tell one session's lines from
            # another's. Only an identifier made of letters, digits and dashes is written into a commit message.
            session = str(facts.get("session_id") or "")
            session = session if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", session) else ""
        except Exception:
            memory = None
    if memory is None:
        try:
            _, memory = memory_for(options.repo or os.getcwd())
        except SystemExit:
            return 0 if options.hook else 2
    if not os.path.isdir(os.path.join(memory, ".git")):
        if not options.hook:
            print(f"bowline memory: {memory} is not a git repository; nothing to push.")
        return 0
    git(memory, "add", "-A")
    committed = False
    if git(memory, "diff", "--cached", "--quiet")[0] != 0:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        git(memory, "commit", "-q", "-m", "Memory as of " + stamp, *(["-m", SESSION_LINE + session] if session else []))
        committed = True
    if git(memory, "rev-parse", "--verify", "-q", "HEAD")[0] != 0:
        return 0
    pushed = False
    if git(memory, "rev-parse", "--abbrev-ref", "@{u}")[0] != 0:
        if git(memory, "remote", "get-url", "origin")[0] == 0:
            pushed = git(memory, "push", "-q", "-u", "origin", "HEAD")[0] == 0
    else:
        _, ahead = git(memory, "rev-list", "--count", "@{u}..HEAD", capture=True)
        if (ahead.strip() or "0") != "0":
            pushed = git(memory, "push", "-q")[0] == 0
    if not options.hook:
        print(f"bowline memory: {'committed' if committed else 'nothing new'}; {'pushed' if pushed else 'nothing to push'}.")
    return 0


def meant_path(memory):
    """Where the removals a person said were meant are recorded: beside the memory folder, in Claude Code's project
    folder, outside the backup."""
    return os.path.join(os.path.dirname(os.path.normpath(memory)), "bowline", "memory-meant.json")


def meant(memory):
    try:
        with open(meant_path(memory), encoding="utf-8") as handle:
            return [str(c) for c in json.load(handle).get("meant") or []]
    except (OSError, ValueError, AttributeError):
        return []


def lines_today(memory):
    """Every line the notes hold now, without its surrounding spaces, so that a line moved to another note or put
    back is not a loss."""
    held = set()
    for folder, dirs, files in os.walk(memory):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            if name.endswith(".md"):
                held.update(line.strip() for line in common.read_text(os.path.join(folder, name)).splitlines())
    return held


def losses(memory, config, now=None):
    """The lines one session added to a note and another session removed soon after, that no note holds today: a list
    of {commit, note, lines, when}, the oldest first. Read from the backup's history; a commit made before bowline
    wrote the session into its message names no session and is never part of a finding."""
    crew = config.get("crew") or {}
    days, hours = crew.get("memoryLossDays") or 0, crew.get("memoryLossHours") or 0
    if not days or not hours or not os.path.isdir(os.path.join(memory, ".git")):
        return []
    # --no-show-signature: a person whose git shows signatures (log.showSignature) would otherwise get a line of
    # words before every commit, inside the text read here, and a check of every signature in the week's history.
    code, out = git(memory, "-c", "core.quotepath=false", "log", "--no-show-signature", f"--since={int(days)}.days.ago",
                    "--max-count=2000", "--no-color", "--no-renames", "-p", "--unified=0",
                    "--format=%x1e%H%x1f%ct%x1f%B%x1f", "--", "*.md", capture=True)
    if code != 0:
        return []
    commits = []
    for block in out.split("\x1e")[1:]:
        parts = block.split("\x1f")
        if len(parts) < 4:
            continue
        found = re.search(r"^" + re.escape(SESSION_LINE) + r"(\S+)\s*$", parts[2], re.MULTILINE)
        changes, note, in_header = [], None, True
        for line in parts[3].splitlines():
            if line.startswith("diff --git "):
                note, in_header = None, True
            elif in_header:
                if line.startswith("+++ b/") or (line.startswith("--- a/") and note is None):
                    note = line[6:]
                elif line.startswith("@@"):
                    in_header = False
            elif note and line[:1] in ("+", "-") and line[1:].strip():
                changes.append((line[0], note, line[1:].strip()))
        commits.append((parts[0], int(parts[1] or 0), found.group(1) if found else "", changes))
    commits.reverse()                                   # the oldest first, as the notes were written
    added, candidates = {}, {}
    for commit, when, session, changes in commits:
        for sign, note, line in changes:
            if sign == "-":
                first = added.get((note, line))
                if session and first and first[1] and first[1] != session and when - first[0] <= hours * 3600:
                    candidates.setdefault((commit, note), {"commit": commit, "note": note, "lines": [], "when": when})["lines"].append(line)
        for sign, note, line in changes:
            if sign == "+":
                added[(note, line)] = (when, session)
    if not candidates:
        return []
    held, said = lines_today(memory), meant(memory)
    found = []
    for loss in candidates.values():
        loss["lines"] = [line for line in loss["lines"] if line not in held]
        if loss["lines"] and not any(loss["commit"].startswith(c) for c in said if len(c) >= 7):
            found.append(loss)
    return found


def do_losses(options):
    repo = options.repo or os.getcwd()
    checkout, memory = memory_for(repo)
    if options.meant:
        code, out = git(memory, "rev-parse", "--verify", "-q", options.meant + "^{commit}", capture=True)
        if code != 0:
            print(f"bowline memory: {options.meant} is not a commit of the memory folder {memory}.", file=sys.stderr)
            return 2
        path = meant_path(memory)
        said = meant(memory)
        if out.strip() not in said:
            said.append(out.strip())
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"meant": said}, handle, indent=2)
            handle.write("\n")
        print(f"bowline memory: recorded that what the commit {out.strip()[:12]} removed was meant; it is not reported again.")
        return 0
    found = losses(memory, common.load_config(checkout))
    print(f"memory folder: {memory}")
    if not found:
        print("losses: none. No commit of the last days removed lines that another session had just added.")
        return 0
    for loss in found:
        stamp = datetime.datetime.fromtimestamp(loss["when"]).strftime("%Y-%m-%d %H:%M")
        print(f"{loss['note']}: {len(loss['lines'])} line(s) that another session had added were removed by the commit "
              f"{loss['commit'][:12]} ({stamp}) and are in no note now:")
        for line in loss["lines"]:
            print(f"  {line}")
        print(f"  the whole change: git -C \"{memory}\" show {loss['commit'][:12]} -- \"{loss['note']}\"")
    print("Put back what was lost with the Edit tool, one addition at a time; for a removal that was meant: "
          "bowline memory losses --meant <commit>.")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Backs up Claude Code's memory folder to a private remote.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "restore"):
        p = sub.add_parser(name)
        p.add_argument("remote")
        p.add_argument("--repo")
        p.add_argument("--no-hook", action="store_true")
        p.add_argument("--python")
        p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("status")
    p.add_argument("--repo")
    p = sub.add_parser("push")
    p.add_argument("--repo")
    p.add_argument("--hook", action="store_true")
    p = sub.add_parser("losses")
    p.add_argument("--repo")
    p.add_argument("--meant", metavar="COMMIT")
    options = parser.parse_args(argv)
    if options.command == "push":
        try:
            return do_push(options)
        except Exception:
            return 0 if options.hook else 2
    if options.command == "status":
        return do_status(options)
    if options.command == "losses":
        return do_losses(options)
    words = "The notes are backed up." if options.command == "setup" else "The notes are back on this machine; start a session and type /memory to see them read."
    return do_setup(options, words)


if __name__ == "__main__":
    sys.exit(main())
