"""The memory backup: Claude Code's memory folder for a repository becomes a git repository pushed to a private remote.

    python -I scripts/bowline.py memory setup <remote> [--repo <path>] [--no-hook] [--python <exe>] [--dry-run]
    python -I scripts/bowline.py memory restore <remote> [--repo <path>]     the same, in a new machine's words
    python -I scripts/bowline.py memory status [--repo <path>]
    python -I scripts/bowline.py memory push [--repo <path>] [--hook]        what the hook runs after every reply

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
repository is left alone.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HOOK_MARKS = ("bowline", "push-memory")


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
    print(f"repository: {checkout}")
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
    print(f"repository: {checkout}")
    print(f"memory folder: {memory}")
    if not os.path.isdir(memory):
        print("state: the folder does not exist yet; Claude Code makes it at the first memory it keeps.")
        return 0
    index = os.path.join(memory, "MEMORY.md")
    if os.path.isfile(index):
        text = common.read_text(index)
        print(f"index: {common.count_lines(text)} lines, {len(text.encode('utf-8')):,} bytes (only the first 200 lines or 25 KB load)")
    notes = [f for f in os.listdir(memory) if f.endswith(".md") and f != "MEMORY.md"]
    print(f"notes: {len(notes)}")
    if not os.path.isdir(os.path.join(memory, ".git")):
        print("backup: none. Run: bowline memory setup <private remote>")
        return 1
    _, remote = git(memory, "remote", "get-url", "origin", capture=True)
    _, last = git(memory, "log", "-1", "--format=%ci %s", capture=True)
    _, ahead = git(memory, "rev-list", "--count", "@{u}..HEAD", capture=True)
    _, dirty = git(memory, "status", "--porcelain", capture=True)
    print(f"remote: {remote.strip() or 'none'}")
    print(f"last commit: {last.strip() or 'none'}")
    print(f"not yet pushed: {ahead.strip() or '0'} commit(s); uncommitted changes: {len(dirty.strip().splitlines())} file(s)")
    print(f"hook on this machine: {'installed' if hook_installed() else 'not installed (the plugin hook may cover it)'}")
    return 0


def do_push(options):
    memory = None
    if options.hook:
        try:
            facts = json.load(sys.stdin)
            transcript = facts.get("transcript_path") or ""
            if transcript:
                memory = os.path.join(os.path.dirname(transcript), "memory")
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
        git(memory, "commit", "-q", "-m", "Memory as of " + stamp)
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
    options = parser.parse_args(argv)
    if options.command == "push":
        try:
            return do_push(options)
        except Exception:
            return 0 if options.hook else 2
    if options.command == "status":
        return do_status(options)
    words = "The notes are backed up." if options.command == "setup" else "The notes are back on this machine; start a session and type /memory to see them read."
    return do_setup(options, words)


if __name__ == "__main__":
    sys.exit(main())
