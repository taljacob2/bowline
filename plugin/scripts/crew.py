"""The crew: working beside other Claude Code sessions in one repository, each in its own worktree.

    python -I scripts/bowline.py crew [--repo <path>] [--verbose] [--json] who is here, and what each has taken
    python -I scripts/bowline.py crew watch [--every <seconds>]            the same, drawn again until Ctrl+C
    python -I scripts/bowline.py crew queue [join [--why <words>] | leave] the order in which the worktrees push
    python -I scripts/bowline.py crew prune [--remove <name>...]           the worktrees safe to remove; remove some
    python -I scripts/bowline.py crew claim <key> [--why <words>]          take a note, a file or a number, or refuse
    python -I scripts/bowline.py crew claim <list> --new [--why <words>]   take the next free number of a numbered list
    python -I scripts/bowline.py crew release <key>... | --all             give back what this worktree took
    python -I scripts/bowline.py crew run [--small] [--timeout <minutes>] [--every <seconds>] -- <command> [<argument>...]
    python -I scripts/bowline.py crew after-rebase [--hook]                what a rebase changed: numbers and stamps
    python -I scripts/bowline.py crew after-push [--hook]                  who waits on this worktree's push
    python -I scripts/bowline.py crew after-commit [--hook]                who waits on this worktree's commit
    python -I scripts/bowline.py crew refresh                              measure the worktrees again, for the record
    python -I scripts/bowline.py crew before-edit --file <path> | --hook   whether another worktree holds this file
    python -I scripts/bowline.py crew say [<words> | --clear]              what this worktree's session wants the others to know
    python -I scripts/bowline.py crew say --asks [<question> | --clear]    this session waits for the person's answer

Several sessions in one repository share more than they see: one machine's processor, one memory folder, one roadmap
whose numbers each of them extends, and the ports a person's own servers listen on. This command gives each session
what the others would otherwise have to say by hand.

With no word after it, crew lists every worktree of the repository: its branch, how far it is from the branch every
session pushes to, its changed files, the last sign of work there, the sessions at work in it, its processes that
count as heavy or that listen on a port, the claims it holds, the files changed in more than one worktree, and who
holds the turn for a heavy check. The sessions are the ones `claude agents --json` lists, Claude Desktop's included,
each joined to the worktree its folder is in, with whether it is busy, idle or blocked, or offline: a background
session listed with no process, which neither works nor waits; what claude listed is kept in the repository's git
folder (sessions.json) for the hooks, which never start claude. Where claude cannot be asked, a
transcript written lately stands for a session, named by the title line at its end. Claude Desktop keeps a record of
each of its Code sessions (crew.desktop says where, or false for none); a session it records is named by the app's
full title and given the app's id, and the printout, run inside a Claude Code session, ends with those ids, by which a
reply in the app links each session. Of a record only the ids, the title, whether it is archived, its folders and its
last activity are read. A process belongs to the worktree
of its session, else to the one its command line names, else to that of its children when all of them agree, else to
that of its nearest parent with one. A worktree whose folder has no .git file of its own, as while it is being
removed, is named as broken and left out, because git asked there answers for the main checkout. Each session comes
with the memory its process and every process below it hold, and the look says how much of the machine's is in use.

The printout puts what matters first, each worktree once: WAITS FOR YOU (a session asks the person a question or is
blocked, or its sessions are idle and it holds files not committed or commits not on the pushed branch, untracked
files that nobody has written for crew.oldUntrackedHours left out and shown with their age instead), AT WORK (a
session is busy, a heavy check runs, or a command a session started still runs after its turn ended, each such command
named under its session), IDLE (sessions idle, nothing held) a line each, and QUIET (no session, no sign
of work) folded into one line that says whether any of them holds work; a commit counts as held only when its change
is not on the pushed branch (git cherry), because a rebased commit reaches it under another hash. Then what concerns
more than one worktree. Every line is plain ASCII within 100 columns. --json prints the model the printout is drawn
from, for any other view; watch draws the printout again every crew.watchSeconds, measuring the worktrees in the
background, for a terminal kept beside the app. A question the person is waited on for is set by `crew say --asks`,
or by the Stop hook when a reply ends with one (crew.asksFromReply), and taken back at the person's next prompt.

queue keeps the order in which the worktrees push, in the repository's git folder: a session joins before its full
checks and is told which worktrees ahead of it change a file it changes, so that it rebases onto their push first;
crew run says the same, and after a push that the pushed branch holds, the hook gives the place up and names who
comes next with the same files. prune names the worktrees that are safe to remove (every file committed, every
commit's change on the pushed branch, no session, process, claim, lock or place in the queue, and no sign of work
for crew.pruneHours) and why each other one is not; --remove removes the ones named, each checked again, with plain
`git worktree remove` and no time limit, which takes ignored files and refuses a change, so nothing is ever forced;
the branch stays. A Claude Desktop session in the person's sidebar, not archived, whose process has ended is offline
and still a session of its worktree: `claude agents` does not list it, the app's record does, and reopened after a
removal it would find its folder gone, so prune names it and keeps the worktree until it is archived. The look lists
such sessions whose worktree is already gone, for the person to archive.
A sign of work is the newest of three times: when a transcript file in Claude Code's project folder for the worktree
was written (never what the file holds), when the worktree's own git folder was written (a commit, a staged file), and
when it took a claim. The last two matter because a session started in another folder can work in a worktree by its
path, and then leaves no transcript there. A write of HEAD that moved it to no other commit, with the index git
rewrites beside it, is not work, and neither is the transcript of an archived session: Claude Desktop does both when
it archives a session. The look names the archived sessions of a worktree no other session holds, and prune names
them beside a worktree that is safe to remove. Every git question is asked with --no-optional-locks, so that looking at
another session's worktree never takes the lock its own git commands need. What the look measured is kept in the
repository's git folder (changed.json), for a hook that must answer at once; `crew refresh` measures again and prints
nothing.

A claim is a name a worktree takes so that no other takes it: `roadmap:124`, `note:17`, `file:src/parser.py`. The
claims live in the repository's git folder, which every worktree shares, on this machine only, never committed. A
claim another worktree holds is refused with its holder's name. `claim <list> --new` takes one past the highest number
of a numbered list the repository names in .claude/bowline.json (crew.numbers): the highest in the branch every session
pushes to, in every worktree's copy of the file, committed or not, and in every claim. A key that starts with `waits:`
says this worktree waits for another's push, named by its folder or its branch, and several may hold it:
`claim waits:live-logs --why "the parser fix"`.
A claim of a worktree that no longer exists is dropped, and so is a number that has reached the pushed branch.

run waits for a slot of the turn, takes it, runs the command with its output and its exit code passed through, and
gives the slot back. crew.slots (1) full checks run at a time; a process that matches the repository's heavy patterns
(crew.heavy, regular expressions over command lines) and that no `crew run` started takes a slot too, one for each
worktree it runs in, so with one slot run waits for a quiet machine. --small is for a check of one file or a few: it
runs beside the full checks, one small check at a time. run measures the memory its command and every process below
it take, every five seconds, and keeps the most of each command's last three runs in the repository's git folder
(peaks.json); a check that would start beside another waits until that much and a tenth more is free. It never stops
a process. After the timeout it names what still runs and exits with code 3 without running the command.

after-rebase says, and only when something is wrong, that a number appears twice in a numbered list, that a number this
worktree claimed has reached the pushed branch, or that a stamp (crew.stamps, a file whose text names a commit) names
a commit that is not in the branch's history any more. after-push says who waits on this worktree and what it still
holds; after-commit says only who waits, because a session on a branch of its own commits long before it pushes. With
--hook they read a Claude Code PostToolUse hook's JSON on standard input, speak only after a `git rebase`, `git pull`,
`git push` or `git commit`, answer as the hook's additionalContext, and always exit 0.

before-edit says whether another worktree holds a file: changed there and not committed, committed there and in
neither the pushed branch nor this one, or claimed there. With --hook it is a PreToolUse hook on Edit, Write and
NotebookEdit that tells Claude once per session and file and never blocks the edit. It is a module of its own,
crew_edit.py, which reads what the look measured and measures nothing itself.

say keeps a few sentences a session writes about itself: what it finished, with the commits, what it waits on, what
it asks of the others or offers them. The look shows each worktree's with its age. One per worktree, replaced each
time, no longer than crew.sayChars, kept beside the claims and never committed; over the limit it is refused with exit code 1 and nothing changes. A message between sessions arrives
when the other one next looks, and may cross the answer on its way; what a session said is there whenever anyone
looks, and it is the session itself that chooses the words, so nothing is read out of a transcript. With no words it
prints what this worktree last said; --clear takes it back. A worktree that is removed takes its words with it.
"""

import argparse
import concurrent.futures
import datetime
import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

WINDOWS = os.name == "nt"
# How a numbered item starts when a repository names a list without a pattern: "12. ", "- **12. ", "#12:".
NUMBER_PATTERN = r"^\s*(?:[-*]\s+)?(?:\*\*)?#?(\d+)[.):]"
LOCK_WAIT_SECONDS = 10
LOCK_STALE_SECONDS = 30
TIMED_OUT = 3


def settings(config):
    return config.get("crew") or {}


def same(path):
    """A path as two spellings of it compare: the case folded where the system folds it, forward slashes."""
    return os.path.normcase(os.path.normpath(path)).replace("\\", "/")


def git(folder, *args):
    """Runs git in a folder and returns (exit code, its standard output as text); a failure is returned, never raised."""
    try:
        # --no-optional-locks: a look into another session's worktree must not refresh its index, which would take
        # the lock that session's own git command needs at that moment.
        result = subprocess.run(["git", "--no-optional-locks", "-c", "core.quotepath=false", "-C", folder, *args], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return result.returncode, result.stdout.decode("utf-8", "replace")


def state_dir(root):
    """Where the claims and the turn live: the repository's git folder, which every worktree shares, never committed."""
    dot = os.path.join(root, ".git")
    if os.path.isdir(dot):
        return os.path.join(os.path.normpath(dot), "bowline", "crew")
    code, out = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    folder = os.path.normpath(out.strip()) if code == 0 and out.strip() else os.path.normpath(dot)
    return os.path.join(folder, "bowline", "crew")


# The worktrees.

def worktrees(root, unreachable=None):
    """Every worktree of the repository that is still on disk, the main checkout first: its path, branch and name. The
    name is how a person says it: the path from the main checkout, or the path itself when it lies elsewhere. A
    worktree git lists but this system cannot enter, such as one made from another system's view of the same disk, is
    left out and its path added to unreachable, so that the caller can say so."""
    code, out = git(root, "worktree", "list", "--porcelain")
    found = []
    for block in out.split("\n\n") if code == 0 else []:
        entry = {}
        for line in block.splitlines():
            word, _, rest = line.partition(" ")
            entry[word] = rest
        if "worktree" not in entry or "bare" in entry:
            continue
        if not os.path.isdir(entry["worktree"]):
            if unreachable is not None:
                unreachable.append(entry["worktree"])
            continue
        branch = entry.get("branch", "")
        found.append({"path": os.path.normpath(entry["worktree"]), "head": entry.get("HEAD") or None,
                      "branch": branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else (branch or "no branch"),
                      # git keeps a worktree locked with `git worktree lock`, with a reason or none; None is not locked.
                      "locked": entry.get("locked") if "locked" in entry else None})
    if not found:
        found = [{"path": os.path.normpath(root), "branch": "no branch", "head": None}]
    main = found[0]["path"]
    for index, tree in enumerate(found):
        tree["main"] = index == 0
        # A worktree's folder holds a .git file that leads to its own git folder. Without it, as while the worktree is
        # being removed, git run in the folder walks up and answers for the main checkout: once, 5,781 files "not
        # committed" and twenty false overlaps, which were the main checkout's own diff.
        tree["broken"] = index > 0 and not os.path.exists(os.path.join(tree["path"], ".git"))
        inside = same(tree["path"]).startswith(same(main) + "/")
        tree["name"] = "the main checkout" if index == 0 else (
            os.path.relpath(tree["path"], main).replace("\\", "/") if inside else tree["path"].replace("\\", "/"))
        tree["short"] = os.path.basename(tree["path"])
    return found


def mine(trees, root):
    """The worktree a path is in, among the repository's."""
    for tree in trees:
        if same(tree["path"]) == same(root):
            return tree
    return trees[0]


def base_ref(root, config):
    """The branch every session pushes to, as this repository names it: crew.base, or what git says is origin's default
    branch, or origin/main or origin/master when one exists; None in a repository with no such branch."""
    named = settings(config).get("base")
    candidates = [named] if named else []
    code, out = git(root, "rev-parse", "--abbrev-ref", "origin/HEAD")
    if code == 0 and out.strip() and out.strip() != "origin/HEAD":
        candidates.append(out.strip())
    candidates += ["origin/main", "origin/master"]
    for name in candidates:
        if git(root, "rev-parse", "--verify", "-q", name + "^{commit}")[0] == 0:
            return name
    return None


def transcripts(tree_path):
    """The transcript files in Claude Code's project folder for a worktree, as (path, time last written). Only the
    folder's listing is read, never a transcript."""
    found = []
    try:
        entries = list(os.scandir(common.project_folder(tree_path)))
    except OSError:
        return found
    for entry in entries:
        if entry.name.endswith(".jsonl"):
            try:
                found.append((entry.path, entry.stat().st_mtime))
            except OSError:
                pass
    return found


def last_session(tree_path, skip=()):
    """When a session started in a worktree last worked: the time its newest transcript file was written, or None.
    skip names the sessions, by Claude Code's id, whose transcripts do not count, such as those of archived sessions:
    the app writes to a session's transcript as it archives it."""
    return max((stamp for path, stamp in transcripts(tree_path)
                if os.path.basename(path)[:-len(".jsonl")] not in skip), default=None)


REFLOG_LINE = re.compile(r"^([0-9a-f]{40,64}) ([0-9a-f]{40,64}) .*? (\d+) [+-]\d{4}(?:\t|$)")
REFLOG_TAIL = 16 * 1024
# How close to a HEAD write that moved no commit the index's own write must be to count as part of it. When Claude
# Desktop archived sessions on 2026-11-22, it wrote the index 2 seconds before the HEAD in a small repository and 12
# seconds before it in a large one. A wide margin costs nothing: a file staged in those minutes is still a change not
# committed, which the look and prune see on their own.
STILL_SECONDS = 120


def head_entries(folder):
    """The last entries of a git folder's log of HEAD, oldest first, as (time, whether HEAD moved to another commit),
    read from the end of the file only; None when there is no log."""
    try:
        with open(os.path.join(folder, "logs", "HEAD"), "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - REFLOG_TAIL))
            data = handle.read()
    except OSError:
        return None
    entries = []
    for line in data.decode("utf-8", "replace").splitlines():
        found = REFLOG_LINE.match(line)
        if found:
            entries.append((int(found.group(3)), found.group(1) != found.group(2)))
    return entries


def git_written(tree_path):
    """When a worktree's own git folder was last written for work: its index, its HEAD or its log, whichever is newest,
    or None. A commit, a staged file or a checkout of another commit writes one of them. Read from the file system,
    without starting git.

    A write of HEAD that moved it to no other commit is not work. When Claude Desktop archives a session, it detaches
    the HEAD of the session's worktree at the commit it was on, which writes HEAD, its log (an entry whose old and new
    commit are the same) and the index; on 2026-11-22 that put an archived session's worktree under AT WORK, "a sign of
    work less than a minute ago (its git folder)". When the newest entry of the log moved no commit, the sign is the
    newest entry that did, or the index when it was written apart from that entry."""
    dot = os.path.join(tree_path, ".git")
    folder = dot
    if os.path.isfile(dot):
        try:
            words = common.read_text(dot).strip()
        except OSError:
            return None
        if not words.startswith("gitdir:"):
            return None
        folder = words[len("gitdir:"):].strip()
        folder = folder if os.path.isabs(folder) else os.path.join(tree_path, folder)
    entries = head_entries(folder)
    if entries and not entries[-1][1]:
        still = entries[-1][0]
        signs = [stamp for stamp, moved in entries if moved]
        try:
            index = os.path.getmtime(os.path.join(folder, "index"))
        except OSError:
            index = None
        if index is not None and abs(index - still) > STILL_SECONDS:
            signs.append(index)
        return max(signs) if signs else None
    newest = None
    for name in ("index", "HEAD", os.path.join("logs", "HEAD")):
        try:
            stamp = os.path.getmtime(os.path.join(folder, name))
        except OSError:
            continue
        newest = stamp if newest is None or stamp > newest else newest
    return newest


def claimed_at(tree_path, claims):
    """When a worktree last took a claim, or None."""
    newest = None
    for claim in claims:
        if same(claim.get("worktree") or "") != same(tree_path):
            continue
        try:
            stamp = datetime.datetime.strptime(str(claim.get("since")), "%Y-%m-%d %H:%M").timestamp()
        except ValueError:
            continue
        newest = stamp if newest is None or stamp > newest else newest
    return newest


def last_sign(tree_path, claims, said=(), archived=()):
    """The last sign of work in a worktree, as (time, what it was), or (None, None): a session's transcript, the
    worktree's git folder, a claim, or what its session said of itself. A session started in another folder that
    works here by path leaves no transcript here. archived names the archived sessions, by Claude Code's id, whose
    transcripts are no sign of work."""
    spoke = said_by(tree_path, said)
    signs = [(last_session(tree_path, archived), "a session's transcript"), (git_written(tree_path), "its git folder"),
             (claimed_at(tree_path, claims), "a claim"), (said_at(spoke) if spoke else None, "what it said")]
    signs = [sign for sign in signs if sign[0] is not None]
    return max(signs) if signs else (None, None)


# The sessions.

DAY = 24 * 3600
# How much of a transcript's end is read for its title. Claude Code writes the title again as the session goes on, so
# the end of the file holds it; the rest of the file, the session's own work, is never read.
TITLE_TAIL = 256 * 1024


def claude_command(config):
    """The program that lists Claude Code's sessions (crew.claude), as a list: a name on the path or a full path, or a
    list for a program with its arguments."""
    command = settings(config).get("claude") or "claude"
    return [str(word) for word in command] if isinstance(command, list) else [str(command)]


def sessions_path(root):
    return os.path.join(state_dir(root), "sessions.json")


def fetch_sessions(root, config, timeout=15):
    """Every session Claude Code knows on this machine, Claude Desktop's included, as `claude agents --json` lists them:
    each with its name, its folder (cwd), its kind, its process id and whether it is busy, idle or blocked. Kept in the
    repository's git folder for the hooks, which must answer at once and so never start claude themselves. None when
    the command is missing or fails."""
    command = claude_command(config)
    program = shutil.which(command[0])
    if not program:
        return None
    try:
        result = subprocess.run([program, *command[1:], "agents", "--json"], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=timeout)
        rows = json.loads(result.stdout.decode("utf-8", "replace") or "null")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not isinstance(rows, list):
        return None
    rows = [row for row in rows if isinstance(row, dict)]
    try:
        write_json(sessions_path(root), {"at": time.time(), "sessions": rows})
    except OSError:
        pass                # the record is a convenience; a look that cannot keep it still answers
    return rows


def cached_sessions(root, max_age=DAY):
    """The sessions the last look listed, when that was within max_age seconds; else None."""
    record = read_json(sessions_path(root), None)
    if not isinstance(record, dict) or not isinstance(record.get("sessions"), list):
        return None
    return record["sessions"] if time.time() - (record.get("at") or 0) <= max_age else None


def session_title(path):
    """A session's title as its transcript records it (the `custom-title` line), read from the file's end only, or
    None. The fallback where `claude agents` cannot be asked; nothing else in the transcript is read."""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - TITLE_TAIL))
            data = handle.read()
    except OSError:
        return None
    title = None
    for line in data.decode("utf-8", "replace").splitlines():
        if '"custom-title"' not in line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("type") == "custom-title" and entry.get("customTitle"):
            title = " ".join(str(entry["customTitle"]).split())
    return title


def tree_of(folder, trees):
    """The worktree a folder is in: the one that is the folder or holds it, the deepest when one holds another."""
    here = same(folder)
    best = None
    for tree in trees:
        top = same(tree["path"])
        if (here == top or here.startswith(top + "/")) and (best is None or len(top) > len(same(best["path"]))):
            best = tree
    return best


def desktop_folder(config):
    """Where Claude Desktop keeps its record of each of its Code sessions: the folder crew.desktop names, else the
    app's own folder on this system; None when crew.desktop is false, which turns the records off."""
    named = settings(config).get("desktop")
    if named is False:
        return None
    if named:
        return os.path.expanduser(str(named))
    home = os.path.expanduser("~")
    if WINDOWS:
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, "Claude", "claude-code-sessions")


DESKTOP_RECORD_BYTES = 4 * 1024 * 1024


def desktop_sessions(config):
    """Claude Desktop's own record of each of its Code sessions on this machine, every account's, as [{"desktop": the
    session's id in the app, which a reply in the app links as [its title](#<id>), "cli": the ids Claude Code gave
    it, "title", "archived", "cwd", "worktree": the worktree the app made for it, "at": its last activity}]. The app
    writes one file per session, `<account>/<organization>/local_<id>.json` in desktop_folder; of each, only these
    fields are read, and the rest (its settings, its tools) never. An empty list when the app is not installed, the
    setting turns it off, or the files are not what this reads."""
    folder = desktop_folder(config)
    found = []
    if not folder or not os.path.isdir(folder):
        return found
    for top, dirs, files in os.walk(folder):
        if len(os.path.relpath(top, folder).split(os.sep)) >= 2:
            dirs[:] = []                                    # the records lie two folders down; nothing deeper is read
        for name in files:
            if not (name.startswith("local_") and name.endswith(".json")):
                continue
            path = os.path.join(top, name)
            try:
                if os.path.getsize(path) > DESKTOP_RECORD_BYTES:
                    continue
                with open(path, encoding="utf-8") as handle:
                    record = json.load(handle)
            except (OSError, ValueError):
                continue
            if not isinstance(record, dict) or not str(record.get("sessionId") or "").startswith("local_"):
                continue
            cli = [str(record[key]) for key in ("cliSessionId", "lastAssistantCliSessionId") if record.get(key)]
            at = record.get("lastActivityAt")
            found.append({"desktop": record["sessionId"], "cli": sorted(set(cli)),
                          "title": " ".join(str(record.get("title") or "").split()) or None,
                          "archived": record.get("isArchived") is True, "cwd": str(record.get("cwd") or "") or None,
                          "worktree": str(record.get("worktreePath") or "") or None,
                          "at": at / 1000.0 if isinstance(at, (int, float)) else None})
    return found


def sessions_by_tree(trees, rows, minutes=30, now=None, desktop=()):
    """The sessions in each worktree, as {same(worktree's path): [session]}, newest first. A session is {"name", "id",
    "kind", "status", "was", "pid", "started", "wrote", "cwd", "desktop"}: status is busy, idle or blocked as Claude
    Code says, or offline, wrote is when its transcript was last written, and desktop is its id in Claude Desktop, or
    None. rows are what `claude agents --json` listed; None means it could not be asked, and then each transcript
    written in the last `minutes` stands for a session, named by its title, with the status unknown. desktop is what
    desktop_sessions read: a session the app records gets the app's id, by which a reply links it, and the app's
    title, which `claude agents` cuts at 50 characters.

    A background session listed without a process id is offline, and was is the state it last recorded. Claude Code
    builds such a row from the background job's own record when no process of the job runs, and keeps it in the list
    while that record says "working" or "blocked"; on 2026-11-22 the list held five, the oldest started 112 days
    before and none with a process, each shown as blocked and waiting for the person."""
    now = time.time() if now is None else now
    found = {}
    if rows is None:
        for tree in trees:
            for path, stamp in transcripts(tree["path"]):
                if now - stamp <= minutes * 60:
                    found.setdefault(same(tree["path"]), []).append({
                        "name": session_title(path), "id": os.path.basename(path)[:-len(".jsonl")], "kind": None,
                        "status": "unknown", "was": None, "pid": None, "started": None, "wrote": stamp,
                        "cwd": tree["path"]})
    for row in rows or []:
        tree = tree_of(str(row.get("cwd") or ""), trees) if row.get("cwd") else None
        if tree is None or tree.get("broken"):
            continue
        sid = str(row.get("sessionId") or row.get("id") or "")
        try:
            wrote = os.path.getmtime(os.path.join(common.project_folder(row["cwd"]), sid + ".jsonl")) if sid else None
        except OSError:
            wrote = None
        started = row.get("startedAt")
        pid = row.get("pid") if isinstance(row.get("pid"), int) else None
        status = "blocked" if row.get("state") == "blocked" else str(row.get("status") or row.get("state") or "unknown")
        offline = row.get("kind") == "background" and pid is None
        found.setdefault(same(tree["path"]), []).append({
            "name": " ".join(str(row.get("name") or "").split()) or None, "id": sid, "kind": row.get("kind"),
            "status": "offline" if offline else status, "was": status if offline else None, "pid": pid,
            "started": started / 1000.0 if isinstance(started, (int, float)) else None, "wrote": wrote, "cwd": row["cwd"]})
    by_cli = {cli: record for record in desktop for cli in record["cli"]}
    joined = set()
    for sessions in found.values():
        for session in sessions:
            record = by_cli.get(session["id"])
            session["desktop"] = record["desktop"] if record else None
            if record:
                joined.add(record["desktop"])
                session["name"] = record["title"] or session["name"]
    # A session in the app's sidebar whose process has ended: `claude agents` does not list it, though the person can
    # reopen it at any time, in its folder. On 2026-11-22 four such sessions were in worktrees the look called quiet,
    # with no session, and that prune called safe to remove.
    for record in desktop:
        folder = record["cwd"] or record["worktree"]
        if record["desktop"] in joined or record["archived"] or not folder or not os.path.isdir(folder):
            continue
        tree = tree_of(folder, trees)
        if tree is None or tree.get("broken"):
            continue
        cli = record["cli"][0] if record["cli"] else ""
        try:
            wrote = os.path.getmtime(os.path.join(common.project_folder(folder), cli + ".jsonl")) if cli else None
        except OSError:
            wrote = None
        found.setdefault(same(tree["path"]), []).append({
            "name": record["title"], "id": cli, "kind": "desktop", "status": "offline", "was": None, "pid": None,
            "started": None, "wrote": wrote or record["at"], "cwd": folder, "desktop": record["desktop"]})
    for sessions in found.values():
        sessions.sort(key=lambda s: (s["status"] == "offline", -(s["wrote"] or s["started"] or 0)))
    return found


def archived_by_tree(trees, desktop):
    """The archived sessions of the app in each worktree, as {same(worktree's path): [{"name", "desktop"}]}, the
    newest first: what explains a worktree that no session holds any more, such as one whose HEAD the app detached
    when it archived the session."""
    found = {}
    for record in sorted(desktop, key=lambda r: -(r["at"] or 0)):
        folder = record["cwd"] or record["worktree"]
        if not record["archived"] or not folder or not os.path.isdir(folder):
            continue
        tree = tree_of(folder, trees)
        if tree is not None and not tree.get("broken"):
            found.setdefault(same(tree["path"]), []).append({"name": record["title"], "desktop": record["desktop"],
                                                             "cli": record["cli"]})
    return found


def gone_sessions(trees, desktop):
    """The sessions in the app's sidebar, not archived, whose folder was a worktree of this repository that is gone or
    is being removed: reopened, each would find its folder missing. As [{"name", "desktop", "folder"}], the folder
    named from the main checkout. A folder counts as a worktree when the app made it one for the session, or when it
    lay beside the repository's other worktrees; a deleted folder of the main checkout is not one."""
    main = trees[0]["path"]
    beside = {same(os.path.dirname(tree["path"])) for tree in trees if not tree["main"]}
    found = []
    for record in desktop:
        folder = record["worktree"] or record["cwd"]
        if record["archived"] or not folder:
            continue
        if os.path.isdir(folder) and not (tree_of(folder, trees) or {}).get("broken"):
            continue
        if not record["worktree"] and same(os.path.dirname(folder)) not in beside:
            continue
        if same(folder).startswith(same(main) + "/"):
            found.append({"name": record["title"], "desktop": record["desktop"],
                          "folder": os.path.relpath(folder, main).replace("\\", "/")})
    return found


def quoted(name):
    """A session's name in double quotes, which its own words never close."""
    return '"' + str(name).replace('"', "'") + '"'


def others_active(start, config, transcript=None, now=None):
    """The places where another session worked in the last crew.activeMinutes, as [{"name": the worktree's name,
    "own": whether it is this session's own folder, "sessions": the names of the sessions seen there}]: every other
    worktree of the repository with a sign of work that recent (a transcript, its git folder, a claim, what it said),
    and this worktree itself when a transcript other than this session's was written there. For the line at a
    session's start and the one before a prompt. transcript is this session's own transcript, or a function that gives
    it, asked only when this folder has a transcript written lately; without it, two such transcripts mean one is
    another session's. A session is named from what the last look listed, else from its transcript's title; claude
    itself is never started here, because a hook must answer at once."""
    minutes = settings(config).get("activeMinutes") or 0
    root = common.repo_root(start)
    if not minutes or not root:
        return []
    now = time.time() if now is None else now
    trees = worktrees(root)
    here = mine(trees, root)
    claims, said = load_claims(root), load_said(root)
    known = {str(row.get("sessionId")): row.get("name") for row in cached_sessions(root) or [] if row.get("sessionId")}

    def names(paths):
        found = []
        for path, _ in sorted(paths, key=lambda pair: -pair[1]):
            name = known.get(os.path.basename(path)[:-len(".jsonl")]) or session_title(path)
            if name and name not in found:
                found.append(" ".join(str(name).split()))
        return found

    places = []
    for tree in [tree for tree in trees if tree is not here] + [here]:          # this session's own folder last
        if tree.get("broken"):
            continue
        recent = [(path, stamp) for path, stamp in transcripts(tree["path"]) if now - stamp <= minutes * 60]
        if tree is not here:
            stamp, _ = last_sign(tree["path"], claims, said)
            if stamp is not None and now - stamp <= minutes * 60:
                places.append({"name": tree["name"], "own": False, "sessions": names(recent)})
            continue
        if not recent:
            continue
        own = transcript() if callable(transcript) else transcript
        others = [(path, stamp) for path, stamp in recent if not own or same(path) != same(own)]
        if others if own else len(recent) > 1:
            places.append({"name": tree["name"], "own": True, "sessions": names(others) if own else []})
    return places


def places_words(places):
    """The places of others_active in words, each on its own: which one is this session's own folder, and the sessions
    seen in each. With the number of sessions, counted as one for a place where none is named."""
    parts = []
    for place in places:
        where = f"in your own folder, {place['name']}" if place["own"] else f"in {place['name']}"
        parts.append(where + (", " + ", ".join(quoted(name) for name in place["sessions"]) if place["sessions"] else ""))
    return sum(max(1, len(place["sessions"])) for place in places), "; ".join(parts)


# The processes and the ports.

def processes():
    """Every process on the machine as {pid, ppid, name, command, memory}, or [] when the system would not say. The
    memory is the process's working set in bytes, the memory it has in RAM as Task Manager and ps report it, or None."""
    try:
        if WINDOWS and shutil.which("wmic"):
            # wmic answers in about a third of the time PowerShell takes to start, which matters on the busy machine
            # this command is for; newer Windows no longer installs it, and PowerShell below is the way there. Its
            # table has the columns in the alphabet's order, the command line first, so a comma inside one is kept.
            result = subprocess.run(["wmic", "process", "get", "CommandLine,Name,ParentProcessId,ProcessId,WorkingSetSize",
                                     "/format:csv"],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
            found, pending = [], ""
            node = (os.environ.get("COMPUTERNAME") or "").lower() + ","
            for line in result.stdout.decode("oem", "replace").splitlines():
                # A command line can hold a line break, as `python -c` with a script of several lines does, and wmic
                # writes it as it is: the row goes on until a line ends with the process's numbers. A row is begun
                # by the machine's name, so a row that never ended is let go when the next one begins.
                if not pending and (not line.strip() or line.startswith("Node,")):
                    continue
                if pending and node != "," and line.lower().startswith(node):
                    pending = ""
                pending = pending + "\n" + line if pending else line.strip()
                parts = pending.rstrip().split(",", 1)[-1].rsplit(",", 4)
                memory = parts[-1].strip()
                if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit() and (memory.isdigit() or not memory):
                    pending, parts[4] = "", memory
                    # wmic's table is made by a style sheet that writes &, < and > as &amp;, &lt; and &gt;: a build
                    # showed as "tsc -b &amp;&amp; vite build", and a heavy pattern was matched against that text.
                    command, name = html.unescape(parts[0]), html.unescape(parts[1])
                    found.append({"pid": int(parts[3]), "ppid": int(parts[2]), "name": name, "command": command or name,
                                  "memory": int(parts[4]) if parts[4].isdigit() else None})
            if found:
                return found
        if WINDOWS:
            script = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-CimInstance Win32_Process | "
                      "Select-Object ProcessId,ParentProcessId,Name,CommandLine,WorkingSetSize | ConvertTo-Json -Compress")
            result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
            rows = json.loads(result.stdout.decode("utf-8", "replace") or "[]")
            rows = [rows] if isinstance(rows, dict) else rows
            return [{"pid": int(row.get("ProcessId") or 0), "ppid": int(row.get("ParentProcessId") or 0),
                     "name": row.get("Name") or "", "command": row.get("CommandLine") or row.get("Name") or "",
                     "memory": int(row["WorkingSetSize"]) if str(row.get("WorkingSetSize") or "").isdigit() else None}
                    for row in rows]
        result = subprocess.run(["ps", "-e", "-ww", "-o", "pid=,ppid=,rss=,args="], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
        found = []
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
                found.append({"pid": int(parts[0]), "ppid": int(parts[1]),
                              "name": os.path.basename(parts[3].split(" ")[0]), "command": parts[3],
                              "memory": int(parts[2]) * 1024 if parts[2].isdigit() else None})    # ps counts in KB
        return found
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def children_of(snapshot):
    """Each process's children, as {pid: [child pids]}."""
    children = {}
    for process in snapshot:
        if process["ppid"] != process["pid"]:
            children.setdefault(process["ppid"], []).append(process["pid"])
    return children


def below(pids, snapshot, children=None):
    """The processes given and every process below them, as a set of pids."""
    children = children_of(snapshot) if children is None else children
    found, todo = set(), list(pids)
    while todo:
        pid = todo.pop()
        if pid not in found:
            found.add(pid)
            todo.extend(children.get(pid, []))
    return found


def memory_of(pids, snapshot):
    """The memory of the processes named, in bytes, each counted once; None when none of them is listed with it."""
    by_pid = {p["pid"]: p.get("memory") for p in snapshot}
    known = [by_pid[pid] for pid in pids if by_pid.get(pid) is not None]
    return sum(known) if known else None


def machine_memory():
    """The machine's memory as {"total", "available"} in bytes, or None where the system would not say. Available is
    what a new program can have without anything being written out to disk: on Linux MemAvailable, on macOS the pages
    free, inactive and speculative."""
    try:
        if WINDOWS:
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                    (name, ctypes.c_ulonglong) for name in ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile",
                                                           "ullAvailPageFile", "ullTotalVirtual", "ullAvailVirtual",
                                                           "ullAvailExtendedVirtual")]

            status = Status()
            status.dwLength = ctypes.sizeof(Status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            return {"total": int(status.ullTotalPhys), "available": int(status.ullAvailPhys)}
        if os.path.exists("/proc/meminfo"):
            values = {}
            with open("/proc/meminfo", encoding="ascii", errors="replace") as handle:
                for line in handle:
                    name, _, rest = line.partition(":")
                    words = rest.split()
                    if words and words[0].isdigit():
                        values[name] = int(words[0]) * 1024
            if "MemTotal" in values and "MemAvailable" in values:
                return {"total": values["MemTotal"], "available": values["MemAvailable"]}
            return None
        if sys.platform == "darwin":
            def run(*command):
                return subprocess.run(list(command), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                      stdin=subprocess.DEVNULL, timeout=10).stdout.decode("ascii", "replace")
            total, stat = run("sysctl", "-n", "hw.memsize").strip(), run("vm_stat")
            page = re.search(r"page size of (\d+) bytes", stat)
            pages = re.findall(r"^Pages (?:free|inactive|speculative):\s+(\d+)", stat, re.MULTILINE)
            if total.isdigit() and page and pages:
                return {"total": int(total), "available": sum(int(n) for n in pages) * int(page.group(1))}
        return None
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        return None


def size(amount):
    """A number of bytes as the person reads it: 1.2 GB, or 350 MB below a gigabyte."""
    if amount >= 1024 ** 3:
        return f"{amount / 1024 ** 3:.1f} GB"
    return f"{max(1, int(round(amount / 1024 ** 2)))} MB"


def listening():
    """The TCP ports each process listens on, as {pid: [ports]}, or None when the system has no tool that says."""
    def run(*command):
        try:
            result = subprocess.run(list(command), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.decode("utf-8", "replace") if result.returncode == 0 else None

    ports = {}

    def add(pid, port):
        if str(port).isdigit() and int(port) not in ports.setdefault(int(pid), []):
            ports[int(pid)].append(int(port))

    if WINDOWS:
        out = run("netstat", "-ano")
        if out is None:
            return None
        for line in out.splitlines():
            parts = line.split()
            # A listening row is the one whose far end is port 0; the word for "listening" depends on the language.
            if len(parts) == 5 and parts[0] == "TCP" and parts[2].endswith(":0") and parts[4].isdigit():
                add(parts[4], parts[1].rsplit(":", 1)[-1])
        return ports
    out = run("ss", "-ltnpH")
    if out is not None:
        for line in out.splitlines():
            parts = line.split()
            found = re.search(r"pid=(\d+)", line)
            if len(parts) >= 4 and found:
                add(found.group(1), parts[3].rsplit(":", 1)[-1])
        return ports
    out = run("lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-F", "pn")
    if out is None:
        return None
    pid = None
    for line in out.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = line[1:]
        elif line.startswith("n") and pid:
            add(pid, line.rsplit(":", 1)[-1])
    return ports


# Claude Desktop starts every session's claude.exe with the main checkout as --project-config-root, a session in a
# worktree too, so that path says where the project's settings are, not where the session works.
CONFIG_ROOT = re.compile(r"--project-config-root(?:=|\s+)(?:\"[^\"]*\"|'[^']*'|\S+)")


def owner(command, trees):
    """The worktree whose path a command line names, the longest when one path lies inside another, as a worktree
    under the main checkout does. None when it names none."""
    command = CONFIG_ROOT.sub(" ", command)
    text = same(command) if WINDOWS else command.replace("\\", "/")
    best = None
    for tree in trees:
        path = same(tree["path"])
        if re.search(re.escape(path) + r"(?![A-Za-z0-9._-])", text) and (best is None or len(path) > len(same(best["path"]))):
            best = tree
    return best


def owners(snapshot, trees, session_pids=None):
    """The worktree each process belongs to, as {pid: worktree or None}. A session's own process (session_pids, from
    the sessions Claude Code lists) belongs to the session's worktree; any other process to the worktree its command
    line names. A process that names none, such as `cmd.exe /d /s /c tsc -b && vite build`, takes the worktree of its
    children when every one of them belongs to the same, each judged the same way, and otherwise that of its nearest
    parent that belongs to one: a session's shell, the session itself. The children count only when all of them
    agree, because a system process such as services.exe has a hundred children and belongs to none of them."""
    session_pids = session_pids or {}
    direct = {p["pid"]: session_pids.get(p["pid"]) or owner(p["command"], trees) for p in snapshot}
    parent = {p["pid"]: p["ppid"] for p in snapshot}
    children = children_of(snapshot)
    judged = {}

    def from_below(pid, seen):
        # Judged from the bottom up, so that a chain of processes that name no path, such as Git Bash's
        # `bash -> npx -> cmd /c vitest -> node .../vitest.mjs`, takes the worktree its last one names. Git Bash's
        # processes report a parent that has already exited, so from them only the way down is open.
        if pid in judged:
            return judged[pid]
        if pid in seen:
            return None
        seen.add(pid)
        tree = direct.get(pid)
        if tree is None:
            kids = [from_below(kid, seen) for kid in children.get(pid, [])]
            if kids and all(kid is not None and kid is kids[0] for kid in kids):
                tree = kids[0]
        judged[pid] = tree
        return tree

    found = {}
    for process in snapshot:
        pid = process["pid"]
        tree = from_below(pid, set())
        if tree is not None and tree.get("main") and pid not in session_pids:
            # A path in the main checkout is a weak sign: worktrees share folders with it through links, such as
            # node_modules, and a test runner in a worktree starts its workers from there. The nearest parent that
            # belongs to a worktree decides.
            seen, up = {pid}, parent.get(pid)
            while up and up not in seen and direct.get(up) is None:
                seen.add(up)
                up = parent.get(up)
            if direct.get(up) is not None:
                tree = direct[up]
        seen, up = {pid}, parent.get(pid)
        while tree is None and up and up not in seen:
            seen.add(up)
            tree = direct.get(up)
            up = parent.get(up)
        found[pid] = tree
    return found


def heavy_patterns(config):
    """The repository's heavy patterns, compiled; one that is not a regular expression is named and left out."""
    compiled = []
    for words in settings(config).get("heavy") or []:
        try:
            compiled.append(re.compile(str(words), re.IGNORECASE))
        except re.error as problem:
            print(f"bowline crew: the heavy pattern {words!r} in {common.CONFIG_FILE} is not a regular expression ({problem}); left out.",
                  file=sys.stderr)
    return compiled


CREW_PROCESS = re.compile(r"(?:bowline\.py|run\.mjs|crew\.py)\S*[\"']?\s+(?:crew\b|run\b)")


def ancestors(starts, snapshot):
    """The processes given and every parent of each, up to the first that is not listed, as a set of pids."""
    parents = {process["pid"]: process["ppid"] for process in snapshot}
    chain = set()
    for pid in starts:
        while pid and pid not in chain:
            chain.add(pid)
            pid = parents.get(pid)
    return chain


def crew_chain(snapshot):
    """The processes that are a bowline crew command or one of its parents, this one included. A waiting
    `crew run -- <a heavy command>` names the heavy command in its own command line, and so does the shell that started
    it; neither is the heavy process, and two waiting sessions must not wait for each other."""
    return ancestors([os.getpid()] + [p["pid"] for p in snapshot
                                      if CREW_PROCESS.search(p["command"]) and re.search(r"\bcrew\b", p["command"])],
                     snapshot)


def heavy_now(snapshot, patterns):
    """The processes that match a heavy pattern, leaving out the crew commands and their parents."""
    if not patterns:
        return []
    skip = crew_chain(snapshot)
    return [p for p in snapshot if p["pid"] not in skip and any(pattern.search(p["command"]) for pattern in patterns)]


def shown(command, width=100):
    command = " ".join(command.split())
    return command if len(command) <= width else command[:width - 3] + "..."


# A session's own commands. Claude Code runs a command of its Bash tool in a shell that sources the session's shell
# snapshot and then runs `eval '<the command>' < /dev/null && pwd -P >| <a file>`, the file being where the shell's
# folder is kept for the next command; a command of its PowerShell tool runs in cmd.exe or PowerShell started with its
# script in the variable below, so the command line never shows the script. Its MCP servers, its hooks, its console
# host and the shell's startup, which writes the snapshot, are started otherwise. So a shell of that shape below a
# session's claude process is a command the session runs, and one that runs after the session's turn has ended is a
# background command: on 2026-11-21 a background `git push` of 21 MB ran for 45 minutes after its session went idle.
SHELL_EVAL = re.compile(r"\beval '((?:[^']|'\\'')*)'")
POWERSHELL_TOOL = "CLAUDE_CODE_SHELL_LAUNCHER_SCRIPT"
WRAPPERS = {"cmd.exe", "conhost.exe", "chcp.com", "powershell.exe", "pwsh.exe", "pwsh"}


def tool_shell(command):
    """Whether a command line is a shell Claude Code started for a command of its Bash or PowerShell tool."""
    return "pwd -P >|" in command or POWERSHELL_TOOL in command


def tool_command(process, by_pid, children, tree_path=None):
    """What a tool's shell runs, as a person reads it: the Bash tool's command as the shell evaluates it; for the
    PowerShell tool, the first process below its shell that is not a shell or a console, else only that a PowerShell
    command runs."""
    found = SHELL_EVAL.search(process["command"])
    if found:
        return plain_command(found.group(1).replace("'\\''", "'").replace('\\"', '"'), tree_path)
    todo, seen = list(children.get(process["pid"], [])), set()
    while todo:
        pid = todo.pop(0)
        if pid in seen or pid not in by_pid:
            continue
        seen.add(pid)
        if by_pid[pid]["name"].lower() not in WRAPPERS:
            return plain_command(by_pid[pid]["command"], tree_path)
        todo.extend(children.get(pid, []))
    return "a PowerShell command" if POWERSHELL_TOOL in process["command"] else "a shell command"


def live_commands(pid, by_pid, children, skip=(), tree_path=None):
    """The commands a session's own Bash and PowerShell tools run now, as [{"pid", "command"}]: each tool's shell below
    the session's claude process, the outermost of a chain, since Git Bash starts a second bash below the first. A
    shell in skip, such as the one that runs this look, is left out."""
    found, todo, seen = [], list(children.get(pid, [])), {pid}
    while todo:
        kid = todo.pop(0)
        if kid in seen or kid not in by_pid:
            continue
        seen.add(kid)
        if tool_shell(by_pid[kid]["command"]):
            if kid not in skip:
                found.append({"pid": kid, "command": tool_command(by_pid[kid], by_pid, children, tree_path)})
            continue                                # what runs below it is the command itself
        todo.extend(children.get(kid, []))
    return found


# The claims.

class Lock:
    """One writer of the crew's records at a time, across sessions: a file made only when it does not exist. A lock a
    stopped command left behind is taken over once it is older than any honest use of it."""

    def __init__(self, folder):
        self.path = os.path.join(folder, "lock")

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        deadline = time.time() + LOCK_WAIT_SECONDS
        while True:
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > LOCK_STALE_SECONDS:
                        os.remove(self.path)
                        continue
                except OSError:
                    continue
                if time.time() > deadline:
                    raise SystemExit("bowline crew: another session is writing the crew's records and did not finish; try again.")
                time.sleep(0.1)

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except OSError:
            pass
        return False


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = f"{path}.{os.getpid()}.tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
    common.replace_file(temp, path)


def claims_path(root):
    return os.path.join(state_dir(root), "claims.json")


def load_claims(root):
    return [c for c in read_json(claims_path(root), {}).get("claims") or [] if isinstance(c, dict) and c.get("key")]


def fold(key):
    """A key as two spellings of it compare. A claim keeps the spelling it was typed in, because a file's name is
    shown as its holder wrote it; File:README.md and file:readme.md are still one claim."""
    return str(key).strip().lower()


def exclusive(key):
    """Whether only one worktree may hold a key. Several may wait on the same push."""
    return not fold(key).startswith("waits:")


def number_lists(config):
    """The numbered lists the repository names, as {name: (file, compiled pattern)}."""
    lists = {}
    for name, entry in (settings(config).get("numbers") or {}).items():
        if not isinstance(entry, dict) or not entry.get("file"):
            continue
        try:
            lists[str(name).lower()] = (entry["file"], re.compile(entry.get("pattern") or NUMBER_PATTERN, re.MULTILINE))
        except re.error as problem:
            print(f"bowline crew: the pattern of the numbered list {name!r} in {common.CONFIG_FILE} is not a regular "
                  f"expression ({problem}); left out.", file=sys.stderr)
    return lists


def numbers_in(text, pattern):
    """The numbers a numbered list holds, as (number, line) pairs in the order they appear."""
    found = []
    for match in pattern.finditer(text or ""):
        digits = next((group for group in match.groups() if group and group.isdigit()), None)
        if digits:
            found.append((int(digits), text.count("\n", 0, match.start(match.lastindex or 0)) + 1))
    return found


def file_at(root, ref, path):
    """A file's text as a commit holds it, or '' when the commit has none."""
    code, out = git(root, "show", f"{ref}:{path.replace(os.sep, '/')}")
    return out if code == 0 else ""


def file_here(tree_path, path):
    try:
        return common.read_text(os.path.join(tree_path, path))
    except OSError:
        return ""


def number_of(key, lists):
    """(list name, number) when a key is a number of one of the repository's lists, else None."""
    name, _, digits = fold(key).partition(":")
    return (name, int(digits)) if name in lists and digits.isdigit() else None


def settle(claims, trees, here, lists, base, root, unreachable=()):
    """The claims that still stand, and why each of the others was dropped. A claim of a worktree that no longer exists
    is dropped by whoever looks. A number that has reached the pushed branch is dropped only from the worktree that
    holds it, so that its holder is the one told."""
    # A worktree this system cannot enter is still one git lists, and a session on the system that made it may hold
    # claims there; only a worktree git no longer lists has given its claims up.
    alive = {same(tree["path"]) for tree in trees} | {same(path) for path in unreachable}
    landed = {}
    kept, dropped = [], []
    for claim in claims:
        if same(claim.get("worktree") or "") not in alive:
            dropped.append((claim, "its worktree is gone"))
            continue
        numbered = number_of(claim["key"], lists)
        if numbered and base and same(claim["worktree"]) == same(here["path"]):
            name = numbered[0]
            if name not in landed:
                landed[name] = {n for n, _ in numbers_in(file_at(root, base, lists[name][0]), lists[name][1])}
            if numbered[1] in landed[name]:
                dropped.append((claim, f"{base} now holds it"))
                continue
        kept.append(claim)
    return kept, dropped


def holder_name(claim, trees):
    for tree in trees:
        if same(tree["path"]) == same(claim.get("worktree") or ""):
            return tree["name"]
    return claim.get("worktree") or "a worktree that is gone"


def now_stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class Place:
    """Where a crew command runs: the repository, its worktrees, this worktree, the configuration and the base."""

    def __init__(self, start):
        self.root = common.repo_root(start)
        if not self.root:
            raise SystemExit("bowline crew: not inside a git repository. Run it from a repository, or name one with --repo.")
        self.config = common.load_config(self.root)
        self.unreachable = []
        self.trees = worktrees(self.root, self.unreachable)
        self.here = mine(self.trees, self.root)
        self.lists = number_lists(self.config)
        self.base = base_ref(self.root, self.config)

    def settled(self, write=True):
        """The standing claims, after dropping the ones that no longer hold; call with the lock held to write."""
        kept, dropped = settle(load_claims(self.root), self.trees, self.here, self.lists, self.base, self.root,
                               self.unreachable)
        if dropped and write:
            write_json(claims_path(self.root), {"claims": kept})
        return kept, dropped


def do_claim(options):
    place = Place(options.repo)
    key = options.key.strip()
    with Lock(state_dir(place.root)):
        claims, _ = place.settled()
        if options.new:
            key = fold(key)
            if key not in place.lists:
                known = ", ".join(sorted(place.lists)) or "none"
                print(f"bowline crew: {common.CONFIG_FILE} names no numbered list called {key!r} (crew.numbers names: {known}).",
                      file=sys.stderr)
                return 2
            path, pattern = place.lists[key]
            seen = [n for n, _ in numbers_in(file_at(place.root, place.base, path), pattern)] if place.base else []
            for tree in place.trees:
                seen += [n for n, _ in numbers_in(file_here(tree["path"], path), pattern)]
            for claim in claims:
                numbered = number_of(claim["key"], place.lists)
                if numbered and numbered[0] == key:
                    seen.append(numbered[1])
            key = f"{key}:{max(seen or [0]) + 1}"
        elif not re.fullmatch(r"[^\s:]+:\S.*", key):
            print("bowline crew: a claim is a kind and a name with a colon between them, such as roadmap:124, note:17 "
                  "or file:src/parser.py.", file=sys.stderr)
            return 2
        for claim in claims:
            if fold(claim["key"]) != fold(key) or not exclusive(key):
                continue
            if same(claim["worktree"]) == same(place.here["path"]):
                claim["why"] = options.why or claim.get("why") or ""
                write_json(claims_path(place.root), {"claims": claims})
                print(f"bowline crew: {key} was already this worktree's.")
                return 0
            why = f": {claim['why']}" if claim.get("why") else ""
            print(f"bowline crew: {key} is taken by {holder_name(claim, place.trees)} since {claim.get('since')}{why}. "
                  "Take another, or ask that session with SendMessage.")
            return 1
        claims = [c for c in claims if not (fold(c["key"]) == fold(key) and same(c["worktree"]) == same(place.here["path"]))]
        claims.append({"key": key, "worktree": place.here["path"], "why": options.why or "", "since": now_stamp()})
        write_json(claims_path(place.root), {"claims": claims})
    if options.new:
        print(f"bowline crew: {key} is this worktree's: no copy of {place.lists[key.split(':')[0]][0]} in any worktree, "
              f"{place.base or 'no pushed branch'}, or claim holds a number that high. Tell the other sessions with SendMessage.")
    else:
        print(f"bowline crew: {key} is this worktree's. Tell the other sessions with SendMessage.")
    return 0


def do_release(options):
    place = Place(options.repo)
    wanted = {fold(key) for key in options.keys}
    if not wanted and not options.all:
        print("bowline crew: name the claims to give back, or --all for every claim of this worktree.", file=sys.stderr)
        return 2
    with Lock(state_dir(place.root)):
        claims, _ = place.settled()
        own = [c for c in claims if same(c["worktree"]) == same(place.here["path"])]
        gone = [c for c in own if options.all or fold(c["key"]) in wanted]
        kept = [c for c in claims if c not in gone]
        if gone:
            write_json(claims_path(place.root), {"claims": kept})
    others = sorted(wanted - {fold(c["key"]) for c in own})
    if gone:
        print("bowline crew: given back: " + ", ".join(c["key"] for c in gone) + ".")
    for key in others:
        held = [c for c in claims if fold(c["key"]) == key]
        if held:
            print(f"bowline crew: {key} is {holder_name(held[0], place.trees)}'s, not this worktree's; it was left.")
        else:
            print(f"bowline crew: nothing holds {key}.")
    if not gone and not others:
        print("bowline crew: this worktree holds no claim.")
    return 0


# What a session says of itself.

def said_path(root):
    return os.path.join(state_dir(root), "said.json")


def load_said(root):
    """What each worktree's session last said of itself: a list of {worktree, words, at, seconds}."""
    return [s for s in read_json(said_path(root), {}).get("said") or [] if isinstance(s, dict) and s.get("worktree")]


def said_by(tree_path, said):
    """What one worktree's session last said, or None."""
    for entry in said:
        if same(entry.get("worktree") or "") == same(tree_path):
            return entry
    return None


def said_at(entry):
    """When something was said, in seconds since 1970, or None."""
    if isinstance(entry.get("seconds"), (int, float)):
        return float(entry["seconds"])
    try:
        return datetime.datetime.strptime(str(entry.get("at")), "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return None


def do_say(options):
    place = Place(options.repo)
    limit = int(settings(place.config).get("sayChars") or 0)
    words = " ".join(" ".join(options.words).split())
    here = place.here["path"]
    if options.asks:
        return say_asks(place, words, options.clear, limit)
    with Lock(state_dir(place.root)):
        # A worktree git no longer lists has nobody left to speak for it.
        alive = {same(tree["path"]) for tree in place.trees} | {same(path) for path in place.unreachable}
        said = [entry for entry in load_said(place.root) if same(entry["worktree"]) in alive]
        mine_now = said_by(here, said)
        others = [entry for entry in said if same(entry["worktree"]) != same(here)]
        if options.clear:
            write_json(said_path(place.root), {"said": others})
            print("bowline crew: taken back; this worktree says nothing now." if mine_now
                  else "bowline crew: this worktree had said nothing.")
            return 0
        if not words:
            if mine_now:
                print(f"bowline crew: this worktree said, at {mine_now.get('at')}: \"{mine_now.get('words')}\"")
            else:
                print("bowline crew: this worktree has said nothing. Say what you finished, what you wait on and what "
                      "you ask: crew say \"<a few sentences>\"")
            return 0
        if limit and len(words) > limit:
            print(f"bowline crew: that is {len(words)} characters, and what a session says of itself may hold {limit} "
                  f"({common.CONFIG_FILE}, crew.sayChars), so that every session can read every other's in one look. "
                  "Say what is done, what you wait on and what you ask; the rest belongs in a commit message or a "
                  "note. Nothing was changed.", file=sys.stderr)
            return 1                # refused, as a claim another worktree holds is: 2 is for a command that could not run
        write_json(said_path(place.root), {"said": others + [
            {"worktree": here, "words": words, "at": now_stamp(), "seconds": time.time()}]})
    print(f"bowline crew: said, for every session that looks with `bowline crew`: {words}")
    return 0


# A question for the person.
#
# `claude agents` shows a session that ended its reply with a question to the person as plain "idle", the same as one
# that is done, and on the day this was built three such sessions were in fact waiting for the person. A session says
# so with `crew say --asks`, and the Stop hook says so for it when its last reply ends with a question; the person's
# next prompt in that session takes it back.

QUESTION_CHARS = 300


def asks_path(root):
    return os.path.join(state_dir(root), "asks.json")


def load_asks(root):
    """The questions sessions wait on the person for, as [{"worktree", "session", "words", "seconds", "by"}]: by "say"
    when a session said so itself, by "reply" when its last reply ended with a question. session is Claude Code's id
    for the session, or None when it was not known."""
    return [a for a in read_json(asks_path(root), {}).get("asks") or [] if isinstance(a, dict) and a.get("worktree")]


def change_asks(root, change):
    """Changes the questions under the crew's lock: change takes the list and returns the new one."""
    with Lock(state_dir(root)):
        asks = change(load_asks(root))
        write_json(asks_path(root), {"asks": asks})
    return asks


def question_in(text):
    """The question a reply ends with, or None: the last sentence of its last line that holds words, without the marks
    Markdown puts around a line, when it ends with a question mark. A question in the middle of a reply that goes on
    to say something else is not one the person is waited on for."""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return None
    last = lines[-1].strip("*_`>#- \t").strip()
    if not last.endswith("?"):
        return None
    words = " ".join(re.split(r"(?<=[.!?])\s+", last)[-1].split())
    return words if len(words) <= QUESTION_CHARS else "..." + words[-(QUESTION_CHARS - 3):]


def note_reply(facts):
    """For the Stop hook: when the reply that just ended asks the person a question, record that its session waits for
    them; when it does not, take back what an earlier reply of the same session recorded. Claude Code gives the reply's
    text as last_assistant_message, and nothing else of it is kept. crew.asksFromReply false turns this off."""
    root = common.repo_root(facts.get("cwd") or os.getcwd())
    session = str(facts.get("session_id") or "")
    message = facts.get("last_assistant_message")
    if not root or not session or not isinstance(message, str):
        return
    if not settings(common.load_config(root)).get("asksFromReply", True):
        return
    words = question_in(message)
    earlier = any(a.get("session") == session and a.get("by") == "reply" for a in load_asks(root))
    if not words and not earlier:
        return

    def change(asks):
        kept = [a for a in asks if not (a.get("session") == session and a.get("by") == "reply")]
        if words:
            kept.append({"worktree": root, "session": session, "words": words, "seconds": time.time(), "by": "reply"})
        return kept
    change_asks(root, change)


def clear_asks(facts):
    """For the hook before a prompt: the person has answered, so this session's questions are taken back, and any in
    its worktree that name no session."""
    root = common.repo_root(facts.get("cwd") or os.getcwd())
    session = str(facts.get("session_id") or "")
    if not root:
        return

    def answered(entry):
        return (session and entry.get("session") == session) or (not entry.get("session") and same(entry["worktree"]) == same(root))
    if any(answered(entry) for entry in load_asks(root)):
        change_asks(root, lambda asks: [entry for entry in asks if not answered(entry)])


def say_asks(place, words, clear, limit):
    """`crew say --asks`: this session waits for the person's answer to a question, shown first in every look until the
    person's next prompt. The session is the one Claude Code names in CLAUDE_CODE_SESSION_ID."""
    here = place.here["path"]
    session = os.environ.get("CLAUDE_CODE_SESSION_ID") or None

    def mine(entry):
        return same(entry["worktree"]) == same(here) and (entry.get("session") or None) == session
    current = [entry for entry in load_asks(place.root) if mine(entry)]
    if clear:
        change_asks(place.root, lambda asks: [entry for entry in asks if not mine(entry)])
        print("bowline crew: taken back; this session asks nothing now." if current else "bowline crew: this session had asked nothing.")
        return 0
    if not words:
        print(f"bowline crew: this session asks: \"{current[-1]['words']}\"" if current else
              "bowline crew: this session asks nothing. When you wait for the person's answer: crew say --asks \"<the question>\"")
        return 0
    if limit and len(words) > limit:
        print(f"bowline crew: that is {len(words)} characters, and a question may hold {limit} ({common.CONFIG_FILE}, "
              "crew.sayChars). Nothing was changed.", file=sys.stderr)
        return 1
    change_asks(place.root, lambda asks: [entry for entry in asks if not mine(entry)] + [
        {"worktree": here, "session": session, "words": words, "seconds": time.time(), "by": "say"}])
    print(f"bowline crew: asked; every look shows it first, until the person's next prompt here: {words}")
    return 0


# What a rebase and a push change.

def repeated_numbers(tree_path, lists):
    """The numbers a numbered list holds more than once in a worktree's copy, as (list, file, number, lines)."""
    found = []
    for name, (path, pattern) in sorted(lists.items()):
        lines = {}
        for number, line in numbers_in(file_here(tree_path, path), pattern):
            lines.setdefault(number, []).append(line)
        found += [(name, path, number, where) for number, where in sorted(lines.items()) if len(where) > 1]
    return found


def stale_stamps(tree_path, config):
    """The stamps that name a commit this branch does not hold, as (file, commit, how to remake it). A stamp is a file
    a build writes with the commit it was built from; a rebase gives every commit a new name, so the old name points at
    nothing. A stamp that is not there yet, or names no commit, is nobody's finding."""
    found = []
    for entry in settings(config).get("stamps") or []:
        if not isinstance(entry, dict) or not entry.get("file"):
            continue
        match = common.COMMIT.search(file_here(tree_path, entry["file"]))
        if not match:
            continue
        commit = match.group(0)
        if (git(tree_path, "cat-file", "-e", commit + "^{commit}")[0] != 0
                or git(tree_path, "merge-base", "--is-ancestor", commit, "HEAD")[0] != 0):
            found.append((entry["file"], commit, entry.get("remake") or ""))
    return found


def findings(root, config):
    """What the doctor says about a repository's numbered lists and stamps. Both are silent in a repository that names
    none in its .claude/bowline.json."""
    out = []
    for name, path, number, lines in repeated_numbers(root, number_lists(config)):
        out.append(common.Finding(
            "warning", f"{path} holds the number {number} {len(lines)} times, at lines {', '.join(str(n) for n in lines)}.",
            "Two sessions that each add an item to a numbered list take the same number unless one of them knows about the "
            "other, and a rebase joins both without a conflict; everything that names the number then names two items.",
            f"Give one of the items the next free number: bowline crew claim {name} --new. /bowline:crew says how sessions take numbers."))
    for path, commit, remake in stale_stamps(root, config):
        out.append(common.Finding(
            "warning", f"The stamp {path} names the commit {commit[:12]}, which is not in this branch's history.",
            "A stamp records the commit a build was made from; after a rebase that commit has a new name, so the stamp "
            "points at nothing and whatever reads it reports a build from a commit nobody can find.",
            ("Remake it: " + remake + ".") if remake else f"Remake the stamp, and name the command in {common.CONFIG_FILE} (crew.stamps)."))
    return out


def git_folder(command, word, start):
    """The folder a `git ... <word>` command works in: every `cd <path>` and `git -C <path>` before the word moves the
    folder on from the hook's working folder."""
    where = start
    before = re.split(r"\b" + word + r"\b", command, maxsplit=1)[0]
    for match in re.finditer(r"(?:\b(?:cd|pushd|Set-Location|sl)\s+|\bgit\s+-C\s*)(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", before):
        path = match.group(1).strip("\"'")
        where = path if os.path.isabs(path) else os.path.join(where, path)
    return where


def hook_place(words):
    """For a hook: the place the git command worked in, when the command is one of the given git commands; else None."""
    try:
        facts = json.load(sys.stdin)
    except Exception:
        return None
    command = str((facts.get("tool_input") or {}).get("command") or "")
    for word in words:
        if re.search(r"\bgit\b[^;&|]*\b" + word + r"\b", command):
            start = git_folder(command, word, facts.get("cwd") or os.getcwd())
            return Place(start) if common.repo_root(start) else None
    return None


def say(lines, hook):
    """Prints what a check found: as a PostToolUse hook's additionalContext, which Claude Code puts next to the
    command's result, or as plain lines for a person."""
    if not lines:
        return
    if hook:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": "bowline crew, after this command:\n" + "\n".join(lines)}}))
    else:
        for line in lines:
            print(line)


def do_after_rebase(options):
    place = hook_place(("rebase", "pull")) if options.hook else Place(options.repo)
    if place is None:
        return 0
    lines = []
    for name, path, number, where in repeated_numbers(place.here["path"], place.lists):
        lines.append(f"- {path} now holds the number {number} {len(where)} times (lines {', '.join(str(n) for n in where)}). "
                     f"Give this session's item the next free number with `crew claim {name} --new`, and correct every mention of it.")
    with Lock(state_dir(place.root)):
        _, dropped = place.settled()
    for claim, reason in dropped:
        numbered = number_of(claim["key"], place.lists)
        if numbered and same(claim["worktree"]) == same(place.here["path"]):
            lines.append(f"- {claim['key']}, which this worktree claimed, is dropped: {reason}. If the item with that "
                         f"number there is not this session's, take a new one with `crew claim {numbered[0]} --new`.")
    for path, commit, remake in stale_stamps(place.here["path"], place.config):
        lines.append(f"- The stamp {path} names the commit {commit[:12]}, which is not in this branch's history any more."
                     + (f" Remake it: {remake}." if remake else " Remake it before anything reads it."))
    say(lines, options.hook)
    return 0 if options.hook or not lines else 1


def do_after_push(options, word="push"):
    """After a push, and after a commit: who waits on this worktree. A session on a branch of its own commits long
    before it pushes, and whoever waits on it would otherwise hear nothing until then. After a push only, what this
    worktree still holds, since a push is when a piece of work ends."""
    place = hook_place((word,)) if options.hook else Place(options.repo)
    if place is None:
        return 0
    with Lock(state_dir(place.root)):
        claims, _ = place.settled()
    here = place.here
    # A session that waits names the worktree as it knows it: by its folder, its path from the main checkout, or its branch.
    names = {here["short"].lower(), here["name"].lower(), here["branch"].lower()} | ({"main-checkout"} if here["main"] else set())
    waiting = [c for c in claims if fold(c["key"]).startswith("waits:") and fold(c["key"])[len("waits:"):] in names
               and same(c["worktree"]) != same(here["path"])]
    lines = []
    if waiting:
        code, head = git(here["path"], "rev-parse", "--short", "HEAD")
        lines.append(f"- {common.count(len(waiting), 'session waits', 'sessions wait')} on this worktree; after this {word} "
                     f"its HEAD is {head.strip() or 'unknown'} on {here['branch']}. If this {word} holds what one waits for, "
                     "send it the hash with SendMessage:")
        for claim in waiting:
            why = f", for: {claim['why']}" if claim.get("why") else ""
            lines.append(f"  - {holder_name(claim, place.trees)}{why} (since {claim.get('since')})")
    held = [c["key"] for c in claims if same(c["worktree"]) == same(here["path"])] if word == "push" else []
    if held:
        lines.append(f"- This worktree still holds: {', '.join(held)}. Give back what this push finished with `crew release <key>`.")
    if word == "push":
        lines += queue_after_push(place)
    say(lines, options.hook)
    return 0


# The turn for a heavy check.

# The first slot is the file every version of bowline knows, so that an older one waits for a newer one's check; the
# other slots are turn-2.json and on, and the small check's is turn-small.json.
TURN_FILE = re.compile(r"^turn(?:-(\d+|small))?\.json$")
SMALL = "small"
SAMPLE_SECONDS = 5
PEAK_RUNS = 3
PEAKS_KEPT = 40
ROOM = 1.1                      # a check beside another one waits for its peak and a tenth more to be free


def turn_path(root, slot=1):
    return os.path.join(state_dir(root), "turn.json" if slot == 1 else f"turn-{slot}.json")


def live_turn(path, live):
    """The turn a file holds, or None. A turn whose process is gone was left by a command that was stopped, and is
    removed; so is a file nobody finished writing. live is the set of pids running now, or None when not known."""
    turn = read_json(path, None)
    if not isinstance(turn, dict):
        if turn is not None or os.path.exists(path):
            try:
                if time.time() - os.path.getmtime(path) > LOCK_STALE_SECONDS:
                    os.remove(path)
            except OSError:
                pass
        return None
    if live and turn.get("pid") not in live:
        try:
            os.remove(path)
        except OSError:
            pass
        return None
    return turn


def turn_holders(root, snapshot):
    """Every turn held now, the oldest first, each with its slot: 1, 2 and on for a full check, "small" for the small
    one."""
    folder = state_dir(root)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    live = {p["pid"] for p in snapshot} if snapshot else None
    found = []
    for name in names:
        match = TURN_FILE.match(name)
        turn = live_turn(os.path.join(folder, name), live) if match else None
        if turn:
            slot = match.group(1) or "1"
            found.append(dict(turn, slot=int(slot) if slot.isdigit() else slot))
    return sorted(found, key=lambda turn: str(turn.get("since") or ""))


def take_turn(root, here, command, slot=1):
    """Takes a slot of the turn when nobody holds it; only one of two sessions that try at the same moment succeeds."""
    path = turn_path(root, slot)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
        json.dump({"pid": os.getpid(), "worktree": here["path"], "command": shown(" ".join(command)), "since": now_stamp()}, out)
        out.write("\n")
    return True


def give_turn(root, slot=1):
    turn = read_json(turn_path(root, slot), None)
    if isinstance(turn, dict) and turn.get("pid") == os.getpid():
        try:
            os.remove(turn_path(root, slot))
        except OSError:
            pass


def turn_words(turn, trees):
    kind = "the small check's turn" if turn.get("slot") == SMALL else "the turn"
    return f"{kind}, held since {turn.get('since')} by {holder_name(turn, trees)} for: {turn.get('command')}"


def peaks_path(root):
    return os.path.join(state_dir(root), "peaks.json")


def load_peaks(root):
    """The memory the checks run through the turn took, newest first, as [{"command", "recent": [bytes of each of the
    last runs, newest first], "runs", "seconds", "at", "time", "small", "worktree"}]."""
    return [p for p in read_json(peaks_path(root), {}).get("peaks") or [] if isinstance(p, dict) and p.get("command")]


def peak(entry):
    """The most a command took in its last runs, in bytes, or None."""
    recent = [int(n) for n in (entry or {}).get("recent") or [] if isinstance(n, (int, float)) and n > 0]
    return max(recent) if recent else None


def record_peak(root, here, words, held, seconds, small):
    def change(peaks):
        entry = next((p for p in peaks if p["command"] == words), {"command": words})
        entry = dict(entry, recent=([held] + list(entry.get("recent") or []))[:PEAK_RUNS], runs=int(entry.get("runs") or 0) + 1,
                     seconds=int(round(seconds)), at=now_stamp(), time=time.time(), small=small, worktree=here["path"])
        rest = [p for p in peaks if p["command"] != words]
        return ([entry] + sorted(rest, key=lambda p: -float(p.get("time") or 0)))[:PEAKS_KEPT]
    with Lock(state_dir(root)):
        write_json(peaks_path(root), {"peaks": change(load_peaks(root))})


class Sampler(threading.Thread):
    """Measures the memory of a process and of every process below it, every few seconds, and keeps the most."""

    def __init__(self, pid, every):
        super().__init__(daemon=True)
        self.pid, self.every, self.peak = pid, every, None
        self.done = threading.Event()

    def run(self):
        wait = min(1.0, self.every)
        while not self.done.wait(wait):
            snapshot = processes()
            held = memory_of(below([self.pid], snapshot), snapshot) if any(p["pid"] == self.pid for p in snapshot) else None
            if held is not None and (self.peak is None or held > self.peak):
                self.peak = held
            wait = self.every


def room_for(small, slots, holders, outside):
    """Whether a check may start now, as far as the slots go. A full check needs a slot that neither a turn nor a heavy
    process outside the turn takes (each worktree that runs one takes a slot); the small check runs beside them, one at
    a time, while they do not already take more than the slots."""
    full = sum(1 for turn in holders if turn.get("slot") != SMALL) + outside
    if small:
        return not any(turn.get("slot") == SMALL for turn in holders) and full <= slots
    return full < slots


def run_measured(command, every):
    """Runs the command with its output passed through; returns (exit code, peak memory in bytes or None)."""
    try:
        if len(command) == 1:
            child = subprocess.Popen(command[0], shell=True)
        else:
            child = subprocess.Popen([shutil.which(command[0]) or command[0]] + command[1:])
    except OSError as problem:
        print(f"bowline crew: {command[0]} could not be started: {problem}", file=sys.stderr)
        return 2, None
    sampler = Sampler(child.pid, every)
    sampler.start()
    with child:
        try:
            code = child.wait()
        except BaseException:
            child.kill()            # as subprocess.call does when it is stopped
            raise
        finally:
            sampler.done.set()
    sampler.join(timeout=2 * every + 1)
    return code, sampler.peak


def do_run(options):
    command = [word for word in options.command if word != "--"] if options.command[:1] == ["--"] else list(options.command)
    if not command:
        print("bowline crew: name the command after two dashes: crew run -- <command> [<argument>...]", file=sys.stderr)
        return 2
    place = Place(options.repo)
    patterns = heavy_patterns(place.config)
    crew = settings(place.config)
    behind = queue_warning(place)
    if behind:
        print("\n".join(lines_of(behind, "", "  ")), file=sys.stderr, flush=True)
    minutes = options.timeout if options.timeout is not None else (crew.get("waitMinutes") or 30)
    every = max(1, options.every if options.every is not None else (crew.get("waitEverySeconds") or 15))
    sample = max(0.1, options.sample if options.sample is not None else SAMPLE_SECONDS)
    slots = max(1, int(crew.get("slots") or 1)) if str(crew.get("slots") or 1).isdigit() else 1
    small = bool(options.small)
    words = shown(" ".join(command))
    if not patterns:
        print(f"bowline crew: {common.CONFIG_FILE} names no heavy processes (crew.heavy), so only the turn is waited for.",
              file=sys.stderr)
    entry = next((p for p in load_peaks(place.root) if p["command"] == words), None)
    needs = peak(entry)
    deadline = time.time() + minutes * 60
    said, slot = None, None
    while True:
        snapshot = processes()
        holders = turn_holders(place.root, snapshot)
        managed = below([turn["pid"] for turn in holders if isinstance(turn.get("pid"), int)], snapshot)
        busy = [p for p in heavy_now(snapshot, patterns) if p["pid"] not in managed]
        pids = session_pids(place.trees, sessions_by_tree(place.trees, cached_sessions(place.root) or [])) if busy else {}
        found = owners(snapshot, place.trees, pids) if busy else {}
        outside = len({same(found[p["pid"]]["path"]) if found.get(p["pid"]) else None for p in busy})
        room = room_for(small, slots, holders, outside)
        free = machine_memory() if room and needs and (holders or busy) else None
        short = free is not None and free["available"] < needs * ROOM
        if room and not short:
            choices = [SMALL] if small else [n for n in range(1, slots + 1)
                                             if n not in {turn.get("slot") for turn in holders}]
            slot = next((n for n in choices if take_turn(place.root, place.here, command, n)), None)
            if slot is not None:
                break
        waits = []
        for process in busy[:5]:
            whose = found.get(process["pid"])
            waits.append(f"pid {process['pid']} {shown(process['command'], 70)}" + (f" ({whose['name']})" if whose else ""))
        if len(busy) > 5:
            waits.append(f"and {len(busy) - 5} more")
        waits += [turn_words(turn, place.trees) for turn in holders]
        if short:
            waits.append(f"too little memory beside them: this command took at most about {size(needs)} in its last "
                         f"runs, and {size(free['available'])} is free")
        reason = "; ".join(waits) or "another session that took the turn at the same moment"
        if reason != said:
            print(f"bowline crew: waiting for a quiet machine, up to {minutes:g} minute(s), looking every {every:g} "
                  f"second(s). Running now: {reason}." + (f" crew.slots lets {slots} full checks run at once." if slots > 1 else ""),
                  file=sys.stderr, flush=True)
            said = reason
        if time.time() >= deadline:
            print(f"bowline crew: the machine was not quiet within {minutes:g} minute(s), so the command did not run. "
                  f"Still running: {reason}. Nothing was stopped; ask that session, or try again later.", file=sys.stderr)
            return TIMED_OUT
        time.sleep(min(every, max(0.1, deadline - time.time())))
    try:
        others = [turn for turn in holders if turn.get("slot") != slot]
        if not others and not busy:
            print(f"bowline crew: the machine is quiet and the turn is this worktree's; running: {words}",
                  file=sys.stderr, flush=True)
        else:
            beside = common.count(len(others) + outside, "other check", "other checks")
            print(f"bowline crew: {'the small check' if small else 'a turn'} is this worktree's, beside {beside}"
                  + (f", with {size(free['available'])} free and at most {size(needs)} taken by this command before"
                     if free and needs else "") + f"; running: {words}", file=sys.stderr, flush=True)
        started = time.time()
        code, held = run_measured(command, sample)
        if held:
            seconds = time.time() - started
            try:
                record_peak(place.root, place.here, words, held, seconds, small)
            except (OSError, SystemExit):           # the lock was not had: the command's exit code still counts
                pass
            print(f"bowline crew: the command ended after {how_long(seconds)}, with exit code {code}; it and the processes "
                  f"it started held at most about {size(held)} of memory, measured every {sample:g} second(s).",
                  file=sys.stderr, flush=True)
        return code
    finally:
        give_turn(place.root, slot)


# Who is here.

def how_long(seconds):
    minutes = int(max(0, seconds) // 60)
    if minutes < 1:
        return "less than a minute"
    if minutes < 120:
        return common.count(minutes, "minute", "minutes")
    if minutes < 48 * 60:
        return common.count(minutes // 60, "hour", "hours")
    return common.count(minutes // (24 * 60), "day", "days")


def ago(stamp, now):
    return how_long(now - stamp) + " ago"


def survey_tree(tree, base):
    """One worktree's distance from the base and the files it changed, committed or not, as a record."""
    path = tree["path"]
    ahead = behind = not_on_base = None
    blobs = {}
    if tree.get("broken"):
        # git asked there would answer for the main checkout; nothing it said would be this worktree's.
        return {"path": path, "name": tree["name"], "branch": tree["branch"], "main": False, "head": tree.get("head"),
                "ahead": None, "behind": None, "notOnBase": None, "uncommitted": 0, "untracked": 0, "untrackedAt": None,
                "files": [], "blobs": {}, "dirty": [], "broken": True}
    if base:
        code, out = git(path, "rev-list", "--left-right", "--count", f"{base}...HEAD")
        if code == 0 and len(out.split()) == 2:
            behind, ahead = (int(n) for n in out.split())
            not_on_base = ahead
        if ahead:
            # A rebased commit reaches the pushed branch under another hash. git cherry compares the changes
            # themselves, and marks with + each commit whose change the pushed branch does not hold.
            code, out = git(path, "cherry", base, "HEAD")
            if code == 0:
                not_on_base = sum(1 for line in out.splitlines() if line.startswith("+"))
        # Each committed change with the id of the content it ends in, so that two worktrees whose branches hold the
        # same commit are seen to hold the same file, not two changes of it.
        code, out = git(path, "diff", "--raw", "--no-abbrev", "--no-renames", f"{base}...HEAD")
        for line in out.splitlines() if code == 0 else []:
            facts, _, name = line.partition("\t")
            if line.startswith(":") and name and len(facts.split()) >= 4:
                blobs[name.strip('"')] = facts.split()[3]
    code, out = git(path, "status", "--porcelain", "--untracked-files=all")
    dirty, untracked = [], []
    for line in out.splitlines() if code == 0 else []:
        if len(line) > 3:
            dirty.append(line[3:].split(" -> ")[-1].strip('"'))
            blobs.setdefault(dirty[-1], None)                           # changed here, in no commit yet
            if line.startswith("??"):
                untracked.append(dirty[-1])
    return {"path": path, "name": tree["name"], "branch": tree["branch"], "main": tree["main"],
            "head": tree.get("head"), "ahead": ahead, "behind": behind, "notOnBase": not_on_base,
            "uncommitted": len(dirty), "untracked": len(untracked), "untrackedAt": newest_written(path, untracked),
            "files": sorted(blobs), "blobs": blobs, "dirty": sorted(dirty), "broken": False}


UNTRACKED_STATS = 2000


def newest_written(folder, paths):
    """When the newest of some files in a folder was last written, or None. Only the first UNTRACKED_STATS are asked,
    because a folder of thousands that git does not ignore, such as a dependency cache, would make every look slow."""
    newest = None
    for path in paths[:UNTRACKED_STATS]:
        try:
            stamp = os.path.getmtime(os.path.join(folder, path))
        except OSError:
            continue
        newest = stamp if newest is None or stamp > newest else newest
    return newest


def collisions(trees):
    """The files that more than one worktree changed differently, as {path: [the worktrees' names]}, from the records
    of a survey. Two worktrees whose commits end in the same content of a file, because one branch was cut from the
    other or both took the same commit, did not change it differently, and neither did one of them that goes on from
    there without a commit yet. It is a collision when their commits end in different content, or when two of them
    each hold a change that is not committed."""
    holders = {}
    for tree in trees:
        if tree.get("broken"):
            continue
        dirty = set(tree.get("dirty") or [])
        for path, blob in (tree.get("blobs") or {}).items():
            holders.setdefault(path, []).append((tree["name"], blob, path in dirty))
    return {path: [name for name, _, _ in held] for path, held in holders.items()
            if len({blob for _, blob, _ in held}) > 1 or sum(1 for _, _, dirty in held if dirty) > 1}


def survey_path(root):
    return os.path.join(state_dir(root), "changed.json")


def survey(place):
    """Measures every worktree, eight at a time, and keeps the result in the repository's git folder for whoever must
    answer at once. The record is what cached_survey returns."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        trees = list(pool.map(lambda tree: survey_tree(tree, place.base), place.trees))
    record = {"at": time.time(), "base": place.base, "trees": trees}
    try:
        write_json(survey_path(place.root), record)
    except OSError:
        pass                # the record is a convenience; a look that cannot keep it still answers
    return record


def cached_survey(root):
    """What the last look or `crew refresh` measured, without starting git, or None when nothing was measured yet:
    {"at": seconds since 1970, "base": the pushed branch or None, "trees": [{"path", "name", "branch", "main", "head":
    the commit the worktree is at, "ahead", "behind", "notOnBase": how many of the commits ahead hold a change the
    pushed branch does not (git cherry), "broken": its folder has no .git file and nothing was measured, "uncommitted":
    how many files hold a change not committed, "untracked": how many of those git does not track yet, "untrackedAt":
    when the newest of those was last written, "files": every file the worktree changed, committed or not, by its path from the
    repository's top, "blobs": {each of those files: the id of the content its commits end in, or None when no commit
    of the worktree changed it}, "dirty": the files with a change that is not committed}]}. collisions(record["trees"]) gives the files two worktrees changed differently. Measuring a large repository's worktrees cold took over two minutes on the first one that
    was tried, so a hook that runs before every edit reads this and lets `crew refresh` measure in the background."""
    record = read_json(survey_path(root), None)
    return record if isinstance(record, dict) and isinstance(record.get("trees"), list) else None


def shared_record(path, config):
    """Whether a file is one the repository says every session adds to (crew.shared, paths or patterns): a roadmap, a
    design document, a changelog. Two worktrees that both changed one is how the work is meant to go."""
    return any(fnmatch.fnmatchcase(path, str(pattern)) for pattern in settings(config).get("shared") or [])


def do_refresh(options):
    survey(Place(options.repo))
    return 0


def session_pids(trees, by_tree):
    """{pid: worktree} for every session whose process id is known."""
    return {session["pid"]: tree for tree in trees for session in by_tree.get(same(tree["path"]), []) if session["pid"]}


def session_state(session, now):
    """How a session stands, in a few words: busy, idle for how long, blocked, or when it last wrote."""
    status = session["status"]
    if status == "busy":
        return "busy"
    if status == "blocked":
        return "blocked in the background" if session.get("kind") == "background" else "blocked"
    if status == "idle":
        return "idle" + (f" for {how_long(now - session['wrote'])}" if session.get("wrote") else "")
    if status == "offline" and session.get("kind") == "desktop":
        return ("offline: it is in Claude Desktop's sidebar, not archived, and no process of it runs. Archive it before "
                "this worktree is removed: reopened after, it would find its folder gone")
    if status == "offline":
        return (f"offline: Claude Code lists it as {session.get('was') or 'blocked'} from when it last ran, and no "
                "process of it runs now")
    return f"last wrote {ago(session['wrote'], now)}" if session.get("wrote") else f"{status}"


def session_name(session):
    return quoted(session["name"]) if session.get("name") else f"{session.get('id', '')[:8] or 'with no id'} (no title)"


# The push queue.
#
# Two worktrees that change one file meet at the second one's rebase. When the second runs its full checks first and
# rebases after, the checks ran on code that changed under them, and a full check of the first repository that used
# this takes twenty minutes or more. So the sessions take places in one queue, and the one behind another that
# changes the same file rebases onto that push before its full checks.

def queue_path(root):
    return os.path.join(state_dir(root), "queue.json")


def load_queue(root, trees=None):
    """The places in the push queue, first first, as [{"worktree", "why", "since", "seconds"}]; with trees given, only
    those of worktrees that still exist."""
    places = [p for p in read_json(queue_path(root), {}).get("queue") or [] if isinstance(p, dict) and p.get("worktree")]
    if trees is not None:
        alive = {same(tree["path"]) for tree in trees}
        places = [p for p in places if same(p["worktree"]) in alive]
    return places


def change_queue(root, change):
    with Lock(state_dir(root)):
        places = change(load_queue(root))
        write_json(queue_path(root), {"queue": places})
    return places


def shared_files(record, one, other):
    """The files two worktrees changed differently, from a survey's record, by their paths."""
    trees = [t for t in (record or {}).get("trees") or [] if same(t["path"]) in (same(one), same(other))]
    return sorted(collisions(trees)) if len(trees) == 2 else []


def queue_rows(place, record):
    """The queue as the views show it: [{"place", "worktree", "path", "since", "why", "shares": [{"with", "files"}]}],
    where shares names the places ahead that change a file this one changes too."""
    names = display_names(place.trees)
    places = load_queue(place.root, place.trees)
    rows = []
    for index, entry in enumerate(places):
        shares = []
        for ahead in places[:index]:
            files = shared_files(record, ahead["worktree"], entry["worktree"])
            if files:
                shares.append({"with": names.get(same(ahead["worktree"]), ahead["worktree"]), "files": files})
        rows.append({"place": index + 1, "worktree": names.get(same(entry["worktree"]), entry["worktree"]),
                     "path": entry["worktree"], "since": entry.get("since"), "why": entry.get("why") or "", "shares": shares})
    return rows


def shares_words(shares, before="your full checks"):
    return " ".join(f"{share['with']} is ahead of you and changes {', '.join(share['files'])} too: rebase onto its push "
                    f"before {before}." for share in shares)


def do_queue(options):
    place = Place(options.repo)
    here = place.here["path"]
    names = display_names(place.trees)
    mine = names[same(here)]
    if options.step == "leave":
        before = load_queue(place.root)
        change_queue(place.root, lambda places: [p for p in places if same(p["worktree"]) != same(here)])
        held = any(same(p["worktree"]) == same(here) for p in before)
        print(f"bowline crew: {mine} left the push queue." if held else f"bowline crew: {mine} had no place in the push queue.")
        return 0
    if options.step == "join":
        def join(places):
            places = [p for p in places if same(p["worktree"]) in {same(t["path"]) for t in place.trees}]
            for entry in places:
                if same(entry["worktree"]) == same(here):
                    entry["why"] = options.why or entry.get("why") or ""
                    return places
            return places + [{"worktree": here, "why": options.why or "", "since": now_stamp(), "seconds": time.time()}]
        change_queue(place.root, join)
    record = survey(place)
    rows = queue_rows(place, record)
    if options.step == "join":
        row = next(r for r in rows if same(r["path"]) == same(here))
        words = f"bowline crew: {mine} has place {row['place']} in the push queue."
        words += (" " + shares_words(row["shares"])) if row["shares"] else (
            " Nobody ahead of you changes a file you change." if row["place"] > 1 else " Nobody is ahead of you.")
        print("\n".join(lines_of(words, "", "  ")))
        return 0
    if not rows:
        print("bowline crew: the push queue is empty. Take a place with `crew queue join` before your full checks.")
        return 0
    print(f"bowline crew: the push queue of {place.trees[0]['path']}, first first:")
    for line in queue_lines(rows, place.here and mine):
        print(line)
    return 0


def queue_lines(rows, mine=None):
    out = []
    for row in rows:
        words = f"{row['place']}. {row['worktree']}" + (" (this one)" if row["worktree"] == mine else "")
        words += f", since {row['since']}" + (f": {row['why']}" if row["why"] else "")
        out += lines_of(words, "      ", "         ")
        for share in row["shares"]:
            out += lines_of(f"shares {', '.join(share['files'])} with {share['with']}: rebase onto its push before the "
                            "full checks", "         ", "           ")
    return out


def pushed(tree_path, base):
    """Whether everything this worktree's HEAD holds is on the pushed branch: its commit is there, or every change of
    its commits is (git cherry), as after a rebase."""
    if not base:
        return False
    if git(tree_path, "merge-base", "--is-ancestor", "HEAD", base)[0] == 0:
        return True
    code, out = git(tree_path, "cherry", base, "HEAD")
    return code == 0 and not any(line.startswith("+") for line in out.splitlines())


def queue_after_push(place):
    """After a push: when the pushed branch holds this worktree's work, its place in the queue is given up, and the
    lines say who comes next and changes the same files, for the session to tell."""
    here = place.here["path"]
    places = load_queue(place.root, place.trees)
    index = next((i for i, p in enumerate(places) if same(p["worktree"]) == same(here)), None)
    if index is None or not pushed(here, place.base):
        return []
    change_queue(place.root, lambda current: [p for p in current if same(p["worktree"]) != same(here)])
    names = display_names(place.trees)
    record = cached_survey(place.root)
    lines = [f"- {names[same(here)]}'s place in the push queue is given up, since {place.base} holds this push."]
    for position, entry in enumerate(places[index + 1:]):
        files = shared_files(record, here, entry["worktree"])
        if files:
            who = names.get(same(entry["worktree"]), entry["worktree"])
            lines.append(f"- {who} {'comes next' if position == 0 else 'waits in the push queue'} and changes "
                         f"{', '.join(files)} too: tell it to rebase onto this push now, before its full checks, with "
                         "SendMessage.")
    return lines


def queue_warning(place):
    """For crew run: the worktrees ahead of this one in the queue that change a file it changes, in words, or ''."""
    record = cached_survey(place.root)
    for row in queue_rows(place, record):
        if same(row["path"]) == same(place.here["path"]) and row["shares"]:
            return " ".join(f"bowline crew: {share['with']} is ahead of you in the push queue and changes "
                            f"{', '.join(share['files'])} too. Rebase onto its push before this check, or the check runs "
                            "on code that will change; it runs now all the same." for share in row["shares"])
    return ""


# Worktrees that are safe to remove.

def prune_reasons(item, model, hours, queued):
    """Why a worktree is not safe to remove, as a list of reasons; empty when it is. Safe means: nothing in it is not
    committed (ignored files aside, which `git worktree remove` takes with it), every commit's change is on the pushed
    branch, no session, process, claim, lock or place in the push queue holds it, and it showed no sign of work for
    crew.pruneHours."""
    base, now = model["base"], model["at"]
    reasons = []
    if item["this"]:
        reasons.append("it is the worktree this command runs in")
    if item["broken"]:
        reasons.append("it is broken or being removed; `git worktree prune` clears what git keeps of it")
    if item.get("locked") is not None:
        reasons.append("git keeps it locked" + (f" ({item['locked']})" if item["locked"] else ""))
    live = [s for s in item["sessions"] if s["status"] != "offline"]
    parked = [s for s in item["sessions"] if s["status"] == "offline" and s.get("kind") == "desktop"]
    listed = [s for s in item["sessions"] if s["status"] == "offline" and s.get("kind") != "desktop"]
    if live:
        reasons.append("a session is open in it, " + ", ".join(session_name(s) for s in live))
    if parked:
        # The session still belongs to the worktree: the person can reopen it at any time, and it would then find its
        # folder gone. Only the person can say it is finished, by archiving it.
        reasons.append(("its session " if len(parked) == 1 else "its sessions ") + ", ".join(session_name(s) for s in parked)
                       + (" is" if len(parked) == 1 else " are") + " offline in Claude Desktop's sidebar, not archived: "
                       "reopened after a removal, " + ("it" if len(parked) == 1 else "each") + " would find its folder "
                       "gone, so archive " + ("it" if len(parked) == 1 else "them") + " first")
    if listed:
        reasons.append("Claude Code still lists its background " + ("session " if len(listed) == 1 else "sessions ")
                       + ", ".join(session_name(s) for s in listed) + ", offline: opened again after a removal, "
                       + ("it" if len(listed) == 1 else "each") + " would find its folder gone")
    if item["processes"]:
        pids = ", ".join(str(process["pid"]) for process in item["processes"][:3])
        reasons.append(f"{common.count(len(item['processes']), 'process runs', 'processes run')} in it (pid {pids})")
    if item["claims"]:
        reasons.append(("it holds the claim " if len(item["claims"]) == 1 else "it holds the claims ")
                       + ", ".join(claim["key"] for claim in item["claims"]))
    if same(item["path"]) in queued:
        reasons.append("it has a place in the push queue")
    if item["uncommitted"]:
        words = changed_words(item, now)
        if item.get("untracked"):
            # git worktree remove refuses an untracked file as it refuses a change, so the person decides first.
            words += " (git worktree remove refuses untracked files too: commit or delete them first)"
        reasons.append(words)
    if not base:
        reasons.append("there is no pushed branch to compare its commits with")
    elif item["notOnBase"]:
        reasons.append(common.count(item["notOnBase"], "commit", "commits") + f" not on {base}")
    sign = item["lastSign"]
    if sign and now - sign["at"] < hours * 3600:
        reasons.append(f"a sign of work {ago(sign['at'], now)} ({sign['what']})")
    return reasons


def prune_safe_words(item, model):
    sign, now, base = item["lastSign"], model["at"], model["base"]
    words = f"quiet for {how_long(now - sign['at'])}" if sign else "no sign of work on this machine"
    if item["ahead"]:
        words += f"; its {common.count(item['ahead'], 'commit is', 'commits are')} on {base} by content"
    if item.get("archived"):
        words += "; " + archived_words(item["archived"])
    return words


def archived_words(archived):
    """The archived sessions of a worktree, in words: 'its session "X" is archived'."""
    return (("its session " if len(archived) == 1 else "its sessions ") + ", ".join(session_name(s) for s in archived)
            + (" is archived" if len(archived) == 1 else " are archived"))


def remove_worktree(main, path):
    """Runs `git worktree remove` from the main checkout and returns (exit code, what git said, its errors included).
    It has no time limit: git deletes the folder file by file, which on Windows took more than two minutes for a
    worktree with its own node_modules, and a git stopped halfway leaves a folder with no .git file and part of its
    files."""
    try:
        result = subprocess.run(["git", "-C", main, "worktree", "remove", path], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    except OSError as problem:
        return 1, str(problem)
    return result.returncode, result.stdout.decode("utf-8", "replace")


def do_prune(options):
    place = Place(options.repo)
    hours = settings(place.config).get("pruneHours") or 6
    record = survey(place)
    model = look(place, verbose=True, record=record)
    queued = {same(p["worktree"]) for p in load_queue(place.root, place.trees)}
    items = [item for item in model["worktrees"] if not item["main"]]
    if options.remove:
        wanted = []
        for name in options.remove:
            folded = name.strip().lower().replace("\\", "/").rstrip("/")
            match = [item for item in items if folded in {item["display"].lower(), item["name"].lower(),
                     os.path.basename(item["path"]).lower(), item["branch"].lower(), same(item["path"]).lower()}]
            if not match:
                print(f"bowline crew: no worktree of this repository is called {name}; nothing was removed. "
                      "`crew prune` lists them.", file=sys.stderr)
                return 2
            wanted.append(match[0])
        code = 0
        for index, item in enumerate(wanted):
            if index:
                # A removal can take minutes, so whether a session, a process or a claim came to this worktree since
                # is measured again; the files it changed are not, because git refuses a change on its own.
                model = look(place, verbose=True, record=record)
                item = next((i for i in model["worktrees"] if same(i["path"]) == same(item["path"])), item)
                queued = {same(p["worktree"]) for p in load_queue(place.root, place.trees)}
            reasons = prune_reasons(item, model, hours, queued)
            if reasons:
                print("\n".join(lines_of(f"bowline crew: {item['display']} is not removed: {'; '.join(reasons)}.", "", "  ")),
                      flush=True)
                code = 1
                continue
            print(f"bowline crew: removing {item['display']}; a worktree with its own node_modules takes minutes.", flush=True)
            status, out = remove_worktree(place.trees[0]["path"], item["path"])
            if status == 0:
                print(f"bowline crew: removed {item['display']} ({item['path']}); its branch {item['branch']} stays.",
                      flush=True)
                continue
            words = f"bowline crew: git did not remove {item['display']}: {' '.join(out.split()) or 'it gave no reason'}."
            if os.path.isdir(item["path"]) and not os.path.exists(os.path.join(item["path"], ".git")):
                words += (" git stopped partway, so the folder is left with no .git file and part of its files. Everything "
                          f"in it was committed and is on {model['base']}, so nothing is lost: close what holds the "
                          "files git names, then delete the folder.")
            print("\n".join(lines_of(words + " Nothing was forced.", "", "  ")), flush=True)
            code = 1
        return code
    print("\n".join(lines_of(f"bowline crew prune: {model['repository']}, " + (f"measured against {model['base']}"
                                                                             if model["base"] else "with no pushed branch"), "", "  ")))
    safe = [item for item in items if not prune_reasons(item, model, hours, queued)]
    rest = [(item, prune_reasons(item, model, hours, queued)) for item in items if item not in safe]
    if safe:
        out = lines_of(f"Safe to remove: {common.count(len(safe), 'worktree', 'worktrees')}. Each has every file "
                       f"committed and every commit on {model['base']} by content; no session (an offline one in Claude "
                       "Desktop's sidebar counts until it is archived), process, claim, lock or place in the push queue "
                       f"holds it, and it showed no sign of work for {hours} hours:")
        for item in safe:
            out += lines_of(f"{item['display']}: {prune_safe_words(item, model)}", "      ", "        ")
    else:
        out = lines_of("Safe to remove: none.")
    if rest:
        out += lines_of(f"Not safe: {common.count(len(rest), 'worktree', 'worktrees')}.")
        for item, reasons in rest:
            out += lines_of(f"{item['display']}: {'; '.join(reasons)}", "      ", "        ")
    if model["unreachable"]:
        out += lines_of(f"Left out: {common.count(len(model['unreachable']), 'worktree', 'worktrees')} that git lists and "
                        "this system cannot enter, never offered here, since the system that made them may use them: "
                        + common.names([os.path.basename(path) for path in model["unreachable"]]) + ".")
    if safe:
        out += lines_of("To remove them, with the person's yes: crew prune --remove <name> [<name>...]. Each is checked "
                        "again first and removed with git worktree remove, which never removes a change; its branch stays.")
    if wants_links():
        linked = link_lines([session for item in items for session in item["sessions"]]
                            + [session for item in safe for session in item.get("archived", [])])
        out += [""] + linked if linked else []
    print("\n".join(out))
    return 0


# Who is here: the model every view draws from, and the views.
#
# `crew --json` prints the model; the printout, `crew watch` and anything later (a page, a status line) draw from it,
# so that every view says the same thing. The printout is plain ASCII, needs no colour for its meaning, and keeps every
# line within WIDTH columns, because Claude Desktop shows a command's output in a narrow pane.

WIDTH = 100
GROUPS = ("waits", "work", "idle", "quiet", "broken")


def display_names(trees):
    """How the printout names each worktree: "the main checkout", else its folder's name, or its path from the main
    checkout when two worktrees' folders have one name."""
    seen = {}
    for tree in trees:
        seen[tree["short"].lower()] = seen.get(tree["short"].lower(), 0) + 1
    return {same(tree["path"]): "the main checkout" if tree["main"] else
            (tree["short"] if seen[tree["short"].lower()] == 1 else tree["name"]) for tree in trees}


def plain_command(command, tree_path=None):
    """What a process runs, as a person reads it: a Claude Code shell by the command it evaluates, the worktree's own
    path left out, a first `cd` into it dropped, quotation marks dropped, and node_modules/.bin/.. folded into
    node_modules."""
    found = SHELL_EVAL.search(command)
    if found and "shell-snapshots" in command:
        command = "a shell: " + found.group(1).replace("'\\''", "'").replace('\\"', '"')
    text = " ".join(command.replace('"', "").split())
    for path in sorted({tree_path, tree_path.replace("\\", "/")} if tree_path else (), key=len, reverse=True):
        text = re.sub(r"^(a shell: )?cd " + re.escape(path) + r"[\\/]*\s*&&\s*", r"\1", text, flags=re.IGNORECASE)
        text = re.sub(re.escape(path) + r"[\\/]+", "", text, flags=re.IGNORECASE)
    return re.sub(r"node_modules([\\/])\.bin[\\/]+\.\.[\\/]+", r"node_modules\1", text)


def standing(item, minutes, now):
    """The group a worktree goes in and why, as (group, reason). The first that fits: a session asks the person a
    question or is blocked (waits); a session is busy, or a heavy check runs (work); a session's state is not known
    but its transcript was written lately (work); a session's own command runs, though Claude Code calls the session
    idle because its turn has ended (work); its sessions are idle and it holds files not committed or commits not on
    the pushed branch (waits); its sessions are idle and it holds nothing (idle); no session, but a sign of work
    lately, as from a session that works here by path (work); nothing (quiet). An offline session neither asks, works
    nor waits: no process of it runs, so it counts only as a session that is not at work. Untracked files that none of
    has been written for crew.oldUntrackedHours, such as a tool's old cache, are not work that waits for the person:
    they are shown with their age, and the worktree is idle."""
    if item["broken"]:
        return "broken", "broken"
    sessions = item["sessions"]
    live = [session for session in sessions if session["status"] != "offline"]
    if item["asks"] or any(session.get("asks") for session in live):
        return "waits", "asks"
    if any(session["status"] == "blocked" for session in live):
        return "waits", "blocked"
    if any(session["status"] == "busy" for session in live):
        return "work", "busy"
    if item["turn"] or any(process["heavy"] for process in item["processes"]):
        return "work", "heavy"
    if any(session["status"] == "unknown" for session in live):
        return "work", "wrote"
    if any(session.get("commands") for session in live):
        return "work", "command"
    fresh = item["uncommitted"] - (item.get("untracked") or 0) or (item.get("untracked") and not item.get("untrackedOld"))
    if sessions and (fresh or item["notOnBase"]):
        return "waits", "idle-uncommitted" if fresh else "idle-unpushed"
    if sessions:
        return "idle", "idle"
    if item["lastSign"] and now - item["lastSign"]["at"] <= minutes * 60:
        return "work", "sign"
    return "quiet", "quiet"


def newest(item):
    """When a worktree last showed anything: its newest session's transcript or start, or its last sign of work."""
    stamps = [session.get("wrote") or session.get("started") or 0 for session in item["sessions"]]
    stamps += [(session.get("asks") or {}).get("at") or 0 for session in item["sessions"]]
    stamps += [question.get("at") or 0 for question in item["asks"]] + [(item["lastSign"] or {}).get("at") or 0]
    return max(stamps)


def gather(place, record, rows, snapshot, ports, claims, dropped, spoken, asks, now, verbose=False, desktop=()):
    """The model of a look, from what was measured: the worktrees in the order the printout shows them, each with its
    group, its sessions, its processes, its claims and what it said; then what concerns more than one worktree.
    desktop is Claude Desktop's record of its sessions (desktop_sessions)."""
    crew = settings(place.config)
    minutes = crew.get("activeMinutes") or 30
    old_hours = crew.get("oldUntrackedHours") or 24
    by_tree = sessions_by_tree(place.trees, rows, minutes, now, desktop)
    archived = archived_by_tree(place.trees, desktop)
    patterns = heavy_patterns(place.config)
    heavy = {p["pid"] for p in heavy_now(snapshot, patterns)}
    whose = owners(snapshot, place.trees, session_pids(place.trees, by_tree))
    holders = turn_holders(place.root, snapshot)
    turn = holders[0] if holders else None
    children = children_of(snapshot)
    listed_pids = {p["pid"] for p in snapshot}
    by_pid = {p["pid"]: p for p in snapshot}
    this_look = ancestors([os.getpid()], snapshot)        # the shell that runs this look is not a command to report
    names = display_names(place.trees)
    measured = {same(tree["path"]): tree for tree in record["trees"]}
    keep = [int(p) for p in crew.get("keepPorts") or [] if str(p).isdigit()]
    listed = {str(row.get("sessionId")) for row in rows or [] if row.get("sessionId")}
    items = []
    for tree in place.trees:
        key = same(tree["path"])
        m = measured.get(key) or {}
        sessions = [dict(session) for session in by_tree.get(key, [])]
        for session in sessions:
            # The session's own process and every process below it: what closing the session gives back.
            pid = session.get("pid")
            session["memory"] = memory_of(below([pid], snapshot, children), snapshot) if pid in listed_pids else None
            session["commands"] = (live_commands(pid, by_pid, children, this_look, tree["path"])
                                   if pid in listed_pids else [])
        loose = []
        for question in asks:
            if same(question["worktree"]) != key:
                continue
            entry = {"words": question.get("words"), "at": question.get("seconds"), "by": question.get("by")}
            match = next((s for s in sessions if question.get("session") and s["id"] == question["session"]), None)
            if match:
                match["asks"] = entry
            elif question.get("session") and rows is not None and question["session"] not in listed:
                continue                                    # its session is closed: nobody waits any more
            else:
                loose.append(entry)
        own = [p for p in snapshot if whose.get(p["pid"]) is tree and p["pid"] != os.getpid()]
        named = []
        for process in own:
            listens = sorted((ports or {}).get(process["pid"], []))
            if verbose or process["pid"] in heavy or listens:
                named.append({"pid": process["pid"], "command": shown(process["command"], 300),
                              "shown": plain_command(process["command"], tree["path"]), "heavy": process["pid"] in heavy,
                              "ports": listens, "keep": [port for port in listens if port in keep]})
        stamp, what = last_sign(tree["path"], claims, spoken,
                                {cli for session in archived.get(key, []) for cli in session["cli"]})
        spoke = said_by(tree["path"], spoken)
        ahead = m.get("ahead")
        untracked, untracked_at = m.get("untracked") or 0, m.get("untrackedAt")
        item = {"name": tree["name"], "display": names[key], "path": tree["path"], "branch": tree["branch"],
                "main": tree["main"], "this": tree is place.here, "broken": bool(tree.get("broken")),
                "locked": tree.get("locked"), "ahead": ahead, "behind": m.get("behind"),
                "notOnBase": m.get("notOnBase") if m.get("notOnBase") is not None else ahead,
                "uncommitted": m.get("uncommitted") or 0, "untracked": untracked, "untrackedAt": untracked_at,
                # Untracked files that nobody has written for a while, such as a tool's cache, are not work in hand.
                "untrackedOld": bool(untracked and untracked_at and now - untracked_at > old_hours * 3600),
                "lastSign": {"at": stamp, "what": what} if stamp else None,
                "sessions": sessions, "asks": loose, "processes": named, "otherProcesses": len(own) - len(named),
                "claims": [{"key": c["key"], "since": c.get("since"), "why": c.get("why") or ""}
                           for c in claims if same(c.get("worktree") or "") == key],
                "said": {"words": spoke.get("words"), "at": said_at(spoke)} if spoke else None,
                "turn": any(same(held.get("worktree") or "") == key for held in holders),
                "archived": archived.get(key, [])}
        item["group"], item["reason"] = standing(item, minutes, now)
        items.append(item)
    order = {"asks": 0, "blocked": 1}
    items.sort(key=lambda item: (GROUPS.index(item["group"]), order.get(item["reason"], 2), -newest(item)))
    by_name = {tree["name"]: names[same(tree["path"])] for tree in place.trees}
    quiet = {item["display"] for item in items if item["group"] == "quiet"}
    both = sorted(collisions(record["trees"]).items())
    shared = [(path, held) for path, held in both if shared_record(path, place.config)]
    groups = {}
    for path, held in both:
        if (path, held) not in shared:
            groups.setdefault(tuple(by_name.get(name, name) for name in held), []).append(path)
    port_owner = {port: pid for pid, found in (ports or {}).items() for port in found}
    keep_rows = []
    for port in keep:
        pid = port_owner.get(port)
        tree = whose.get(pid) if pid else None
        keep_rows.append({"port": port, "pid": pid, "worktree": names[same(tree["path"])] if tree else None,
                          "command": shown(by_pid[pid]["command"], 300) if pid in by_pid else None})
    counts = {group: sum(1 for item in items if item["group"] == group) for group in GROUPS}
    counts["worktrees"] = len(items) - counts["broken"]
    counts["sessions"] = sum(1 for item in items for s in item["sessions"] if s["status"] != "offline")
    counts["offline"] = sum(1 for item in items for s in item["sessions"] if s["status"] == "offline")
    trees_folder = {os.path.dirname(tree["name"]) for tree in place.trees if not tree["main"]}
    session_pids_listed = [s["pid"] for item in items for s in item["sessions"] if s.get("pid") in listed_pids]
    machine = machine_memory()
    slots = crew.get("slots")
    turns = [{"worktree": by_name.get(holder_name(held, place.trees), holder_name(held, place.trees)),
              "path": held.get("worktree"), "since": held.get("since"), "command": held.get("command"),
              "small": held.get("slot") == SMALL, "pid": held.get("pid")} for held in holders]
    peaks = sorted(((peak(entry), entry) for entry in load_peaks(place.root) if peak(entry)), key=lambda pair: -pair[0])
    return {
        "repository": place.trees[0]["path"], "base": place.base, "at": now, "measuredAt": record.get("at"),
        "activeMinutes": minutes, "sessionsListed": rows is not None, "claude": claude_command(place.config),
        "processesListed": bool(snapshot), "portsListed": ports is not None, "heavyPatterns": bool(patterns),
        "worktreesFolder": trees_folder.pop() if len(trees_folder) == 1 and "" not in trees_folder else None,
        "oldUntrackedHours": old_hours, "counts": counts, "worktrees": items,
        "overlaps": [{"worktrees": list(held), "quiet": [name for name in held if name in quiet], "files": paths}
                     for held, paths in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))],
        "shared": [{"file": path, "worktrees": [by_name.get(name, name) for name in held],
                    "quiet": [by_name.get(name, name) for name in held if by_name.get(name, name) in quiet]}
                   for path, held in shared],
        "keepPorts": keep_rows,
        "queue": queue_rows(place, record),
        "outside": [{"pid": p["pid"], "command": shown(p["command"], 300)} for p in snapshot
                    if p["pid"] in heavy and whose.get(p["pid"]) is None],
        "turn": {"worktree": by_name.get(holder_name(turn, place.trees), holder_name(turn, place.trees)),
                 "since": turn.get("since"), "command": turn.get("command")} if turn else None,
        "turns": turns,
        "slots": max(1, int(slots)) if str(slots or "").isdigit() else 1,
        "memory": dict(machine, sessions=memory_of(below(session_pids_listed, snapshot, children), snapshot)
                       if session_pids_listed else None) if machine else None,
        "peaks": [{"command": entry["command"], "peak": most, "seconds": entry.get("seconds"), "runs": entry.get("runs"),
                   "at": entry.get("at"), "small": bool(entry.get("small"))} for most, entry in peaks[:3]],
        "unreachable": list(place.unreachable),
        "gone": gone_sessions(place.trees, desktop),
        "dropped": [{"key": claim["key"], "holder": holder_name(claim, place.trees), "reason": reason} for claim, reason in dropped],
    }


def look(place, verbose=False, record=None, write=True):
    """Measures what a look needs and returns its model. record is a survey already made, as `crew watch` keeps one;
    write False reads the claims without dropping the ones that no longer hold."""
    now = time.time()
    if write:
        with Lock(state_dir(place.root)):
            claims, dropped = place.settled()
    else:
        claims, dropped = place.settled(write=False)
    spoken = load_said(place.root)
    record = survey(place) if record is None else record
    rows = fetch_sessions(place.root, place.config)
    snapshot = processes()
    ports = listening()
    return gather(place, record, rows, snapshot, ports, claims, dropped, spoken, load_asks(place.root), now, verbose,
                  desktop_sessions(place.config))


def lines_of(text, first="  ", rest=None):
    """A sentence as lines of at most WIDTH columns; the lines after the first are indented by rest."""
    rest = first + "    " if rest is None else rest
    return textwrap.wrap(text, WIDTH, initial_indent=first, subsequent_indent=rest, break_on_hyphens=False) or [first.rstrip()]


def clock(stamp, now):
    """A claim's time as the person reads it: the hour alone today, the date and the hour before."""
    text = str(stamp or "")
    return text[11:] if text[:10] == time.strftime("%Y-%m-%d", time.localtime(now)) else text


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def written_words(stamp, now):
    """When a file was last written, as a person reads it: "written 5 hours ago" within two days, else "from 24
    October", with the year when it is not this year's."""
    if now - stamp < 48 * 3600:
        return "written " + ago(stamp, now)
    day, today = time.localtime(stamp), time.localtime(now)
    return f"from {day.tm_mday} {MONTHS[day.tm_mon - 1]}" + (f" {day.tm_year}" if day.tm_year != today.tm_year else "")


def changed_words(item, now):
    """The files of a worktree not committed, in words, the untracked ones apart with the age of the newest: "2 files
    not committed, 3 untracked files, the newest from 24 October"; empty when there are none."""
    untracked = item.get("untracked") or 0
    parts = []
    if item["uncommitted"] - untracked:
        parts.append(common.count(item["uncommitted"] - untracked, "file", "files") + " not committed")
    if untracked:
        words = common.count(untracked, "untracked file", "untracked files")
        if item.get("untrackedAt"):
            words += (", " if untracked == 1 else ", the newest ") + written_words(item["untrackedAt"], now)
        parts.append(words)
    return ", ".join(parts)


def holds(item, base, short=False, now=None):
    """What a worktree holds that is not on the pushed branch, in words; short leaves out how far behind it is."""
    parts = []
    if item["uncommitted"]:
        parts.append(changed_words(item, time.time() if now is None else now))
    if item["notOnBase"]:
        parts.append(common.count(item["notOnBase"], "commit", "commits") + f" not on {base}")
    elif item["ahead"] and not short:
        parts.append(common.count(item["ahead"], "commit", "commits") + f" ahead, on {base} by content")
    if item["behind"] and not short:
        parts.append(f"{item['behind']} behind")
    return ", ".join(parts) or (f"nothing that is not on {base}" if base else "nothing not committed")


def reason_words(item, model):
    """Why a worktree is in its group, in a few words."""
    reason, sessions, now = item["reason"], item["sessions"], model["at"]
    if reason == "asks":
        return "a session asks you a question"
    if reason == "blocked":
        blocked = sum(1 for session in sessions if session["status"] == "blocked")
        return "a session is blocked" if blocked == 1 else f"{blocked} sessions are blocked"
    idle = "offline" if sessions and all(session["status"] == "offline" for session in sessions) else "idle"
    if reason == "idle-uncommitted":
        return f"{idle}, with work not committed"
    if reason == "idle-unpushed":
        return f"{idle}, with work not on {model['base']}"
    if reason == "busy":
        return common.count(sum(1 for session in sessions if session["status"] == "busy"), "session", "sessions") + " busy"
    if reason == "heavy":
        return "a heavy check runs" + (", its sessions idle" if sessions else "")
    if reason == "command":
        running = sum(len(session.get("commands") or []) for session in sessions)
        live = sum(1 for session in sessions if session["status"] != "offline")
        return ("a background command runs" if running == 1 else f"{running} background commands run") + (
            ", its session idle" if live == 1 else ", its sessions idle")
    if reason == "wrote":
        wrote = max([session.get("wrote") or 0 for session in sessions] or [0])
        return "a session wrote " + ago(wrote, now) if wrote else "a session at work"
    if reason == "sign" and item["lastSign"]:
        return f"a sign of work {ago(item['lastSign']['at'], now)} ({item['lastSign']['what']}), and no session listed here"
    return reason


def head_of(item, model):
    head = item["display"]
    plain = {"claude/" + os.path.basename(item["path"]), "worktree-" + os.path.basename(item["path"]),
             os.path.basename(item["path"]), (model["base"] or "/").split("/", 1)[-1], "main", "master"}
    if item["branch"] not in plain:
        head += f" (branch {item['branch']})"
    return head + (" (this one)" if item["this"] else "")


def block(item, model, verbose=False):
    """One worktree's lines in the printout."""
    now, base = model["at"], model["base"]
    out = lines_of(f"{head_of(item, model)}: {reason_words(item, model)}")
    out += lines_of("holds: " + holds(item, base, now=now), "      ", "        ")
    for session in item["sessions"]:
        held = f", {size(session['memory'])} of memory" if session.get("memory") else ""
        out += lines_of(f"session {session_name(session)}: {session_state(session, now)}{held}", "      ", "        ")
        for command in session.get("commands") or []:
            # The session's turn may have ended long ago: Claude Code calls it idle while its command still runs.
            where = "runs" if session["status"] == "busy" else "runs in the background"
            out += lines_of(f"{where}: {shown(command['command'], 170)}", "        ", "          ")
        if session.get("asks"):
            asked = session["asks"]
            out += lines_of(f"asks, {ago(asked['at'], now) if asked.get('at') else 'lately'}: {quoted(asked['words'])}",
                            "        ", "          ")
    for asked in item["asks"]:
        out += lines_of(f"asks, {ago(asked['at'], now) if asked.get('at') else 'lately'}: {quoted(asked['words'])}",
                        "      ", "        ")
    if sum(1 for session in item["sessions"] if session["status"] == "busy") > 1:
        out += lines_of("warning: more than one session is busy in this one worktree, and they may change the same files",
                        "      ", "        ")
    if not item["sessions"] and item["reason"] != "sign":              # a "sign" worktree's heading names it already
        sign = item["lastSign"]
        out += lines_of("last sign of work: " + (f"{ago(sign['at'], now)}, {sign['what']}" if sign else "none on this machine"),
                        "      ", "        ")
    if not item["sessions"] and item.get("archived"):
        out += lines_of(archived_words(item["archived"]) + " in Claude Desktop, so no session is open here", "      ",
                        "        ")
    for process in item["processes"]:
        marks = (["heavy"] if process["heavy"] else []) + [
            f"listens on {port}" + (", the person's own" if port in process["keep"] else "") for port in process["ports"]]
        out += lines_of(f"pid {process['pid']} {shown(process['shown'], 170)}" + (f" ({', '.join(marks)})" if marks else ""),
                        "      process: ", "        ")
    for turn in model["turns"]:
        if same(turn["path"] or "") == same(item["path"]):
            kind = "a small check" if turn["small"] else "a heavy check"
            out += lines_of(f"holds the turn for {kind} since {clock(turn['since'], now)}, for: {turn['command']}",
                            "      ", "        ")
    for claim in item["claims"]:
        out += lines_of(f"{claim['key']}, since {clock(claim['since'], now)}" + (f": {claim['why']}" if claim["why"] else ""),
                        "      claim: ", "        ")
    if item["said"]:
        # In quotation marks: the words are the session's own, and a status that holds "claim:" or "process:" must
        # not read as one of the look's own lines.
        when = ago(item["said"]["at"], now) if item["said"].get("at") else "lately"
        out += lines_of(f"said, {when}: \"{item['said']['words']}\"", "      ", "        ")
    return out


def idle_line(item, model):
    extra = [f"listens on {port}" for process in item["processes"] for port in process["ports"]]
    if item["claims"]:
        extra.append("still claims " + ", ".join(claim["key"] for claim in item["claims"]))
    names = "; ".join(session_name(session) + (f" ({size(session['memory'])})" if session.get("memory") else "")
                      + ((" (offline in Claude Desktop's sidebar: archive it before this worktree is removed)"
                          if session.get("kind") == "desktop" else " (offline: no process of it runs)")
                         if session["status"] == "offline" else "")
                      for session in item["sessions"])
    if item.get("untrackedOld"):
        extra.append(f"and {changed_words(item, model['at'])}, none written in "
                     f"{common.count(model['oldUntrackedHours'], 'hour', 'hours')}")
    return lines_of(f"{head_of(item, model)}: {names}" + (", " + ", ".join(extra) if extra else ""), "  ", "      ")


def quiet_line(quiet, model):
    base, n = model["base"], len(quiet)
    words = (f"QUIET: {common.count(n, 'worktree', 'worktrees')} with no session and no sign of work in "
             f"{model['activeMinutes']} minutes. ")
    held = [item for item in quiet if item["uncommitted"] or item["notOnBase"]]
    if held:
        words += (f"{len(held)} {'holds' if len(held) == 1 else 'hold'} work that is not on {base or 'a pushed branch'}: "
                  + ", ".join(f"{item['display']} ({holds(item, base, short=True, now=model['at'])})" for item in held) + ". ")
    else:
        words += f"None holds work that is not on {base}. " if base else "None holds files not committed. "
    content = [item for item in quiet if item["ahead"] and not item["notOnBase"]]
    for item in content[:3]:
        words += f"{item['display']}'s {common.count(item['ahead'], 'commit is', 'commits are')} on {base} by content. "
    if len(content) > 3:
        words += f"So are those of {len(content) - 3} more. "
    for item in quiet:
        for process in item["processes"]:
            for port in process["ports"]:
                words += f"A process listens on {port} in {item['display']}. "
    return lines_of(words + "--verbose lists them.", "", "  ")


def link_lines(sessions):
    """The lines that give each session's id in Claude Desktop, for a reply there to link it as [its title](#<id>):
    one line per session, the id first; nothing when no session has one."""
    out, seen = [], set()
    for session in sessions:
        if session.get("desktop") and session["desktop"] not in seen:
            seen.add(session["desktop"])
            out += lines_of(f"#{session['desktop']} {session_name(session)}", "  ", "      ")
    return ["SESSION LINKS: in a reply in Claude Desktop, link a session as [its title](#<its id>)"] + out if out else []


def wants_links():
    """Whether the printout gives the sessions' links: when it runs inside a Claude Code session, which sets CLAUDECODE
    for its tools' shells, because only a reply in Claude Desktop turns them into links; a person's own terminal and
    crew watch go without them."""
    return os.environ.get("CLAUDECODE") == "1"


def render(model, verbose=False, links=False):
    """The printout of a look, as lines: what waits for the person first, then the worktrees at work, the idle ones a
    line each, the quiet ones in one line, and then what concerns more than one worktree. links adds each session's
    id in Claude Desktop at the end."""
    now, base, counts = model["at"], model["base"], model["counts"]
    out = lines_of(f"bowline crew: {model['repository']}, " + (f"measured against {base}" if base else
                   "with no pushed branch to measure against") + time.strftime(", %H:%M", time.localtime(now)), "", "  ")
    offline = f" ({counts['offline']} more listed, offline)" if counts.get("offline") else ""
    out += lines_of(f"{common.count(counts['worktrees'], 'worktree', 'worktrees')} and "
                    f"{common.count(counts['sessions'], 'session', 'sessions')}{offline}: {counts['waits']} wait for you, "
                    f"{counts['work']} at work, {counts['idle']} idle, {counts['quiet']} quiet"
                    + (f", {counts['broken']} broken" if counts["broken"] else "") + "."
                    + (f" A worktree is named by its folder in {model['worktreesFolder']}." if model["worktreesFolder"] else ""))
    if not model["sessionsListed"]:
        out += lines_of(f"Claude Code's list of sessions could not be asked ({' '.join(model['claude'])} agents --json), so "
                        "a session is named from its transcript's title, and whether it is busy is not known.")
    if model["unreachable"]:
        out += lines_of(f"Left out: {common.count(len(model['unreachable']), 'worktree', 'worktrees')} that git lists and "
                        "this system cannot enter (made from another system's view of the disk, or removed by hand): "
                        + common.names([os.path.basename(path) for path in model["unreachable"]], verbose) + ".")
    if not model["processesListed"]:
        out += lines_of("The system would not list its processes, so none are shown.")
    if not model["portsListed"]:
        out += lines_of("The system has no tool that lists listening ports (netstat, ss or lsof), so none are shown.")
    out.append("")
    group = {name: [item for item in model["worktrees"] if item["group"] == name] for name in GROUPS}
    out.append("WAITS FOR YOU" if group["waits"] else "WAITS FOR YOU: nothing.")
    for item in group["waits"]:
        out += block(item, model, verbose) + [""]
    if not group["waits"]:
        out.append("")
    out.append("AT WORK" if group["work"] else "AT WORK: no session is busy, and no heavy check runs.")
    for item in group["work"]:
        out += block(item, model, verbose) + [""]
    if not group["work"]:
        out.append("")
    if group["idle"]:
        old = any(item.get("untrackedOld") for item in group["idle"])
        out += lines_of("IDLE, HOLDING NOTHING: nothing to commit" + (" but untracked files nobody has written in "
                        f"{common.count(model['oldUntrackedHours'], 'hour', 'hours')}" if old else "")
                        + (f", and every commit is on {base}" if base else ""), "", "  ")
        for item in group["idle"]:
            out += idle_line(item, model)
        out.append("")
    if group["quiet"] and verbose:
        out.append(f"QUIET: no session and no sign of work in {model['activeMinutes']} minutes")
        for item in group["quiet"]:
            out += block(item, model, verbose) + [""]
    elif group["quiet"]:
        out += quiet_line(group["quiet"], model) + [""]
    for item in group["broken"]:
        out += lines_of(f"BROKEN OR BEING REMOVED: {head_of(item, model)}. Its folder has no .git file of its own, so git "
                        "asked there answers for the main checkout; it is left out of the counts and of the files "
                        "changed in more than one worktree.", "", "  ") + [""]
    out.append("ACROSS THE WORKTREES")
    if model["overlaps"]:
        out.append("  Changed differently in more than one worktree, so a rebase will meet both changes:")
        for overlap in model["overlaps"] if verbose else model["overlaps"][:20]:
            names = " and ".join(name + (" (quiet)" if name in overlap["quiet"] else "") for name in overlap["worktrees"])
            out += lines_of(names + ":", "      ", "      ")
            out += lines_of(", ".join(overlap["files"]), "          ", "          ")
        if len(model["overlaps"]) > 20 and not verbose:
            out.append(f"      and {len(model['overlaps']) - 20} more (--verbose lists them)")
    if model["shared"]:
        out.append("  Shared records (crew.shared), changed in more than one worktree as they are meant to be:")
        for entry in model["shared"]:
            out += lines_of(f"{entry['file']}: " + ", ".join(name + (" (quiet)" if name in entry["quiet"] else "")
                                                            for name in entry["worktrees"]), "      ", "          ")
    if model["keepPorts"]:
        out.append(f"  The person's own ports ({common.CONFIG_FILE}, crew.keepPorts). Never stop what listens on them:")
        for row in model["keepPorts"]:
            who = ("nothing listens now" if not row["pid"] else f"pid {row['pid']}, in {row['worktree']}" if row["worktree"]
                   else f"pid {row['pid']} {shown(row['command'] or '', 70)}")
            out.append(f"      {row['port']}: {who}")
    if model["queue"]:
        out.append("  The push queue (crew queue): rebase onto the push of a worktree ahead that changes your files")
        out += queue_lines(model["queue"])
    for process in model["outside"]:
        out += lines_of(f"A heavy process in no worktree: pid {process['pid']} {shown(process['command'], 170)}")
    for claim in model["dropped"]:
        out += lines_of(f"Dropped the claim {claim['key']} of {claim['holder']}: {claim['reason']}.")
    if model.get("gone"):
        out += lines_of(f"In Claude Desktop's sidebar, not archived, {common.count(len(model['gone']), 'session', 'sessions')}"
                        " whose worktree is gone or being removed: "
                        + "; ".join(f"{session_name(s)} ({s['folder']})" for s in model["gone"])
                        + ". Reopened, " + ("it" if len(model["gone"]) == 1 else "each") + " finds its folder missing; "
                        "archive " + ("it" if len(model["gone"]) == 1 else "them") + " in the sidebar.")
    for turn in model["turns"]:
        out += lines_of(f"The turn for {'a small check' if turn['small'] else 'a heavy check'} is held since "
                        f"{turn['since']} by {turn['worktree']}, for: {turn['command']}")
    if not model["turns"]:
        out += lines_of("The turn for a heavy check is free." + ("" if model["heavyPatterns"] else
                        f" {common.CONFIG_FILE} names no heavy processes (crew.heavy)."))
    if model["turns"] or model["slots"] > 1:
        out += lines_of(f"crew.slots lets {common.count(model['slots'], 'full check', 'full checks')} run at a time, and "
                        "a small one (crew run --small) beside them.")
    if model["peaks"]:
        out += lines_of("The most memory the checks run through the turn took: " + "; ".join(
            f"{shown(entry['command'], 60)}, {size(entry['peak'])}" + (f" in {how_long(entry['seconds'])}" if entry.get("seconds") else "")
            + (" (small)" if entry["small"] else "") for entry in model["peaks"]) + ".")
    memory = model["memory"]
    if memory:
        words = f"Memory: {size(memory['total'] - memory['available'])} of {size(memory['total'])} in use"
        if memory.get("sessions"):
            words += (f"; the sessions listed and the processes they started hold {size(memory['sessions'])} of it, "
                      "each one's beside its name")
        out += lines_of(words + ".")
    out.append("  To tell a session what you take: SendMessage." if model["sessionsListed"] else
               "  The sessions themselves, and which are busy: ListAgents. To tell one what you take: SendMessage.")
    if links:
        shown_items = [item for item in model["worktrees"] if item["group"] != "quiet" or verbose]
        linked = link_lines([session for item in shown_items for session in item["sessions"]]
                            + [session for item in shown_items if not item["sessions"] for session in item.get("archived", [])]
                            + model.get("gone", []))
        out += [""] + linked if linked else []
    return out


def do_look(options):
    model = look(Place(options.repo), verbose=options.verbose)
    if options.json:
        print(json.dumps(model, indent=2))
    else:
        print("\n".join(render(model, options.verbose, links=wants_links())))
    return 0


def terminal_codes():
    """Whether the terminal reads the codes that clear it. A Windows console is told to; elsewhere a terminal does."""
    if not WINDOWS:
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))     # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:  # noqa: BLE001 - without the codes the printouts follow one another
        return False


def do_watch(options):
    """The printout, drawn again every few seconds until Ctrl+C, for a terminal kept beside Claude Code or Claude
    Desktop. The sessions, the processes and the claims are asked again at every drawing; the worktrees are measured
    in the background, one measuring after another, because a large repository's take minutes."""
    place = Place(options.repo)
    every = options.every if options.every is not None else (settings(place.config).get("watchSeconds") or 10)
    every = max(0.2, float(every))
    latest = {"record": None}
    stop = threading.Event()

    def measure():
        while not stop.is_set():
            try:
                latest["record"] = survey(Place(options.repo))
            except Exception:  # noqa: BLE001 - a measuring that fails is tried again; the last one stays shown
                pass
            stop.wait(every)
    clear = sys.stdout.isatty() and terminal_codes()
    print(f"Measuring the worktrees of {place.trees[0]['path']}; the first drawing follows.", flush=True)
    threading.Thread(target=measure, daemon=True).start()
    drawn = 0
    try:
        while latest["record"] is None:
            time.sleep(0.1)
        while True:
            model = look(Place(options.repo), record=latest["record"], write=False)
            lines = render(model)
            lines += lines_of(f"Redrawn every {every:g} seconds; the worktrees were measured "
                              f"{ago(latest['record'].get('at') or time.time(), time.time())}, the sessions and the "
                              "processes now. Ctrl+C stops it.")
            sys.stdout.write(("\x1b[H\x1b[2J" if clear else "") + "\n".join(lines) + ("\n" if clear else "\n\n"))
            sys.stdout.flush()
            drawn += 1
            if options.times and drawn >= options.times:
                return 0
            time.sleep(every)
    except KeyboardInterrupt:
        print()
        return 0
    finally:
        stop.set()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # What follows two dashes is the command crew run starts, with its own flags; argparse must not read them.
    command = []
    if "--" in argv:
        cut = argv.index("--")
        argv, command = argv[:cut], argv[cut + 1:]
    parser = argparse.ArgumentParser(prog="bowline crew",
                                     description="Working beside other Claude Code sessions in one repository.")
    parser.add_argument("--repo", help="a path inside the repository (default: the current folder)")
    parser.add_argument("--verbose", action="store_true",
                        help="every process of a worktree, every quiet worktree and every file changed twice")
    parser.add_argument("--json", action="store_true", help="the look's model as JSON, which every view draws from")
    sub = parser.add_subparsers(dest="action")
    p = sub.add_parser("queue", help="the push queue: take a place before your full checks, or give it up")
    p.add_argument("step", nargs="?", choices=("join", "leave"), help="join or leave; none lists the queue")
    p.add_argument("--why", help="what this worktree will push, in a few words")
    p = sub.add_parser("prune", help="the worktrees that are safe to remove, and why the others are not")
    p.add_argument("--remove", nargs="+", metavar="NAME", help="remove these, each checked again first; only on the person's yes")
    p = sub.add_parser("watch", help="the look, drawn again every few seconds until Ctrl+C, for a terminal beside the app")
    p.add_argument("--every", type=float, help="seconds between two drawings (default: crew.watchSeconds)")
    p.add_argument("--times", type=int, help="stop after this many drawings")
    p = sub.add_parser("claim", help="take a note, a file or a number, or the next free number of a list with --new")
    p.add_argument("key")
    p.add_argument("--why", help="what it is taken for, in a few words the other sessions read")
    p.add_argument("--new", action="store_true", help="the key is a numbered list's name; take its next free number")
    p = sub.add_parser("release", help="give back what this worktree took")
    p.add_argument("keys", nargs="*")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("run", help="wait for a quiet machine and the turn, then run the command after two dashes")
    p.add_argument("--timeout", type=float, help="minutes to wait before giving up (default: crew.waitMinutes)")
    p.add_argument("--every", type=float, help="seconds between two looks (default: crew.waitEverySeconds)")
    p.add_argument("--small", action="store_true",
                   help="a check of one file or a few: it runs beside the full checks, one small check at a time")
    p.add_argument("--sample", type=float, help=f"seconds between two measures of the command's memory (default: {SAMPLE_SECONDS})")
    for name in ("after-rebase", "after-push", "after-commit"):
        p = sub.add_parser(name)
        p.add_argument("--hook", action="store_true", help="read a PostToolUse hook's JSON on standard input; always exit 0")
    sub.add_parser("refresh", help="measure the worktrees again and keep the result, printing nothing")
    p = sub.add_parser("before-edit", help="whether another worktree holds a file: changed, committed or claimed there")
    p.add_argument("--file", help="the file to ask about")
    p.add_argument("--hook", action="store_true", help="read a PreToolUse hook's JSON on standard input; always exit 0")
    p = sub.add_parser("say", help="a few sentences about this worktree's work, for the other sessions' look")
    p.add_argument("words", nargs="*", help="what is done, what you wait on, what you ask; none prints what was said")
    p.add_argument("--clear", action="store_true", help="take back what this worktree said, or with --asks the question")
    p.add_argument("--asks", action="store_true",
                   help="the words are a question this session waits for the person to answer; shown first until their next prompt")
    for p in sub.choices.values():
        p.add_argument("--repo", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    options = parser.parse_args(argv)
    options.command = command
    if options.action == "before-edit":
        import crew_edit                    # imported here, because crew_edit imports this module
        return crew_edit.do_before_edit(options)
    after = {"after-rebase": do_after_rebase, "after-push": lambda o: do_after_push(o, "push"),
             "after-commit": lambda o: do_after_push(o, "commit")}
    if getattr(options, "hook", False):
        try:
            return after[options.action](options)
        except BaseException:  # noqa: BLE001 - a hook must never fail the command it follows
            return 0
    if options.action in after:
        return after[options.action](options)
    if options.action == "claim":
        return do_claim(options)
    if options.action == "release":
        return do_release(options)
    if options.action == "run":
        return do_run(options)
    if options.action == "refresh":
        return do_refresh(options)
    if options.action == "say":
        return do_say(options)
    if options.action == "watch":
        return do_watch(options)
    if options.action == "queue":
        return do_queue(options)
    if options.action == "prune":
        return do_prune(options)
    if command:
        print("bowline crew: a command after two dashes belongs to crew run: crew run -- <command>", file=sys.stderr)
        return 2
    return do_look(options)


if __name__ == "__main__":
    sys.exit(main())
