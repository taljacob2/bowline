"""The crew: working beside other Claude Code sessions in one repository, each in its own worktree.

    python -I scripts/bowline.py crew [--repo <path>] [--verbose]          who is here, and what each has taken
    python -I scripts/bowline.py crew claim <key> [--why <words>]          take a note, a file or a number, or refuse
    python -I scripts/bowline.py crew claim <list> --new [--why <words>]   take the next free number of a numbered list
    python -I scripts/bowline.py crew release <key>... | --all             give back what this worktree took
    python -I scripts/bowline.py crew run [--timeout <minutes>] [--every <seconds>] -- <command> [<argument>...]
    python -I scripts/bowline.py crew after-rebase [--hook]                what a rebase changed: numbers and stamps
    python -I scripts/bowline.py crew after-push [--hook]                  who waits on this worktree's push
    python -I scripts/bowline.py crew after-commit [--hook]                who waits on this worktree's commit
    python -I scripts/bowline.py crew refresh                              measure the worktrees again, for the record
    python -I scripts/bowline.py crew before-edit --file <path> | --hook   whether another worktree holds this file
    python -I scripts/bowline.py crew say [<words> | --clear]              what this worktree's session wants the others to know

Several sessions in one repository share more than they see: one machine's processor, one memory folder, one roadmap
whose numbers each of them extends, and the ports a person's own servers listen on. This command gives each session
what the others would otherwise have to say by hand.

With no word after it, crew lists every worktree of the repository: its branch, how far it is from the branch every
session pushes to, its changed files, the last sign of work there, its processes that count as heavy or that listen
on a port, the claims it holds, the files changed in more than one worktree, and who holds the turn for a heavy check.
A sign of work is the newest of three times: when a transcript file in Claude Code's project folder for the worktree
was written (never what the file holds), when the worktree's own git folder was written (a commit, a staged file), and
when it took a claim. The last two matter because a session started in another folder can work in a worktree by its
path, and then leaves no transcript there. Every git question is asked with --no-optional-locks, so that looking at
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

run waits until no process on the machine matches the repository's heavy patterns (crew.heavy, regular expressions
over command lines) and no other `crew run` of the repository holds the turn, takes the turn, runs the command with
its output and its exit code passed through, and gives the turn back. It never stops a process. After the timeout it
names what still runs and exits with code 3 without running the command.

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
time, no longer than crew.sayChars, kept beside the claims and never committed. A message between sessions arrives
when the other one next looks, and may cross the answer on its way; what a session said is there whenever anyone
looks, and it is the session itself that chooses the words, so nothing is read out of a transcript. With no words it
prints what this worktree last said; --clear takes it back. A worktree that is removed takes its words with it.
"""

import argparse
import concurrent.futures
import datetime
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
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
                      "branch": branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else (branch or "no branch")})
    if not found:
        found = [{"path": os.path.normpath(root), "branch": "no branch", "head": None}]
    main = found[0]["path"]
    for index, tree in enumerate(found):
        tree["main"] = index == 0
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


def last_session(tree_path):
    """When a session started in a worktree last worked: the time its newest transcript file was written, or None."""
    return max((stamp for _, stamp in transcripts(tree_path)), default=None)


def git_written(tree_path):
    """When a worktree's own git folder was last written: its index, its HEAD or its log, whichever is newest, or None.
    A commit, a staged file or a checkout writes one of them. Read from the file system, without starting git."""
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


def last_sign(tree_path, claims, said=()):
    """The last sign of work in a worktree, as (time, what it was), or (None, None): a session's transcript, the
    worktree's git folder, a claim, or what its session said of itself. A session started in another folder that
    works here by path leaves no transcript here."""
    spoke = said_by(tree_path, said)
    signs = [(last_session(tree_path), "a session's transcript"), (git_written(tree_path), "its git folder"),
             (claimed_at(tree_path, claims), "a claim"), (said_at(spoke) if spoke else None, "what it said")]
    signs = [sign for sign in signs if sign[0] is not None]
    return max(signs) if signs else (None, None)


def others_active(start, config, transcript=None, now=None):
    """The names of the places where another session worked in the last crew.activeMinutes: every other worktree of
    the repository with a sign of work that recent (a transcript, its git folder, a claim), and this worktree itself
    when a transcript other than this session's was written there. For the line at a session's start. transcript is
    this session's own transcript, or a function that gives it, asked only when this folder has a transcript written
    lately; without it, two such transcripts mean one is another session's."""
    minutes = settings(config).get("activeMinutes") or 0
    root = common.repo_root(start)
    if not minutes or not root:
        return []
    now = time.time() if now is None else now
    trees = worktrees(root)
    here = mine(trees, root)
    claims, said = load_claims(root), load_said(root)
    names = []
    for tree in trees:
        if tree is not here:
            stamp, _ = last_sign(tree["path"], claims, said)
            if stamp is not None and now - stamp <= minutes * 60:
                names.append(tree["name"])
            continue
        recent = [path for path, stamp in transcripts(tree["path"]) if now - stamp <= minutes * 60]
        if not recent:
            continue
        own = transcript() if callable(transcript) else transcript
        if any(same(path) != same(own) for path in recent) if own else len(recent) > 1:
            names.append("this same folder")
    return names


# The processes and the ports.

def processes():
    """Every process on the machine as {pid, ppid, name, command}, or [] when the system would not say."""
    try:
        if WINDOWS and shutil.which("wmic"):
            # wmic answers in about a third of the time PowerShell takes to start, which matters on the busy machine
            # this command is for; newer Windows no longer installs it, and PowerShell below is the way there. Its
            # table has the columns in the alphabet's order, the command line first, so a comma inside one is kept.
            result = subprocess.run(["wmic", "process", "get", "CommandLine,Name,ParentProcessId,ProcessId", "/format:csv"],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
            found = []
            for line in result.stdout.decode("oem", "replace").splitlines():
                parts = line.strip().split(",", 1)[-1].rsplit(",", 3)
                if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
                    found.append({"pid": int(parts[3]), "ppid": int(parts[2]), "name": parts[1], "command": parts[0] or parts[1]})
            if found:
                return found
        if WINDOWS:
            script = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-CimInstance Win32_Process | "
                      "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress")
            result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
            rows = json.loads(result.stdout.decode("utf-8", "replace") or "[]")
            rows = [rows] if isinstance(rows, dict) else rows
            return [{"pid": int(row.get("ProcessId") or 0), "ppid": int(row.get("ParentProcessId") or 0),
                     "name": row.get("Name") or "", "command": row.get("CommandLine") or row.get("Name") or ""}
                    for row in rows]
        result = subprocess.run(["ps", "-e", "-ww", "-o", "pid=,ppid=,args="], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
        found = []
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                found.append({"pid": int(parts[0]), "ppid": int(parts[1]),
                              "name": os.path.basename(parts[2].split(" ")[0]), "command": parts[2]})
        return found
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


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


def owner(command, trees):
    """The worktree a process belongs to: the one whose path its command line names, the longest when one path lies
    inside another, as a worktree under the main checkout does. None when it names none."""
    text = same(command) if WINDOWS else command.replace("\\", "/")
    best = None
    for tree in trees:
        path = same(tree["path"])
        if re.search(re.escape(path) + r"(?![A-Za-z0-9._-])", text) and (best is None or len(path) > len(same(best["path"]))):
            best = tree
    return best


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


def crew_chain(snapshot):
    """The processes that are a bowline crew command or one of its parents, this one included. A waiting
    `crew run -- <a heavy command>` names the heavy command in its own command line, and so does the shell that started
    it; neither is the heavy process, and two waiting sessions must not wait for each other."""
    parents = {process["pid"]: process["ppid"] for process in snapshot}
    chain = set()
    starts = [os.getpid()] + [p["pid"] for p in snapshot
                              if CREW_PROCESS.search(p["command"]) and re.search(r"\bcrew\b", p["command"])]
    for pid in starts:
        while pid and pid not in chain:
            chain.add(pid)
            pid = parents.get(pid)
    return chain


def heavy_now(snapshot, patterns):
    """The processes that match a heavy pattern, leaving out the crew commands and their parents."""
    if not patterns:
        return []
    skip = crew_chain(snapshot)
    return [p for p in snapshot if p["pid"] not in skip and any(pattern.search(p["command"]) for pattern in patterns)]


def shown(command, width=100):
    command = " ".join(command.split())
    return command if len(command) <= width else command[:width - 3] + "..."


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
    os.replace(temp, path)


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
                print(f"bowline crew: this worktree said, at {mine_now.get('at')}: {mine_now.get('words')}")
            else:
                print("bowline crew: this worktree has said nothing. Say what you finished, what you wait on and what "
                      "you ask: crew say \"<a few sentences>\"")
            return 0
        if limit and len(words) > limit:
            print(f"bowline crew: that is {len(words)} characters, and what a session says of itself may hold {limit} "
                  f"({common.CONFIG_FILE}, crew.sayChars), so that every session can read every other's in one look. "
                  "Say what is done, what you wait on and what you ask; the rest belongs in a commit message or a "
                  "note. Nothing was changed.", file=sys.stderr)
            return 2
        write_json(said_path(place.root), {"said": others + [
            {"worktree": here, "words": words, "at": now_stamp(), "seconds": time.time()}]})
    print(f"bowline crew: said, for every session that looks with `bowline crew`: {words}")
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
    say(lines, options.hook)
    return 0


# The turn for a heavy check.

def turn_path(root):
    return os.path.join(state_dir(root), "turn.json")


def turn_holder(root, snapshot):
    """Who holds the turn, or None. A turn whose process is gone was left by a command that was stopped, and is removed."""
    path = turn_path(root)
    turn = read_json(path, None)
    if not isinstance(turn, dict):
        if turn is not None or os.path.exists(path):
            try:
                if time.time() - os.path.getmtime(path) > LOCK_STALE_SECONDS:
                    os.remove(path)        # a turn file nobody finished writing
            except OSError:
                pass
        return None
    if snapshot and turn.get("pid") not in {p["pid"] for p in snapshot}:
        try:
            os.remove(path)
        except OSError:
            pass
        return None
    return turn


def take_turn(root, here, command):
    """Takes the turn when nobody holds it; only one of two sessions that try at the same moment succeeds."""
    path = turn_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
        json.dump({"pid": os.getpid(), "worktree": here["path"], "command": shown(" ".join(command)), "since": now_stamp()}, out)
        out.write("\n")
    return True


def give_turn(root):
    turn = read_json(turn_path(root), None)
    if isinstance(turn, dict) and turn.get("pid") == os.getpid():
        try:
            os.remove(turn_path(root))
        except OSError:
            pass


def do_run(options):
    command = [word for word in options.command if word != "--"] if options.command[:1] == ["--"] else list(options.command)
    if not command:
        print("bowline crew: name the command after two dashes: crew run -- <command> [<argument>...]", file=sys.stderr)
        return 2
    place = Place(options.repo)
    patterns = heavy_patterns(place.config)
    crew = settings(place.config)
    minutes = options.timeout if options.timeout is not None else (crew.get("waitMinutes") or 30)
    every = max(1, options.every if options.every is not None else (crew.get("waitEverySeconds") or 15))
    if not patterns:
        print(f"bowline crew: {common.CONFIG_FILE} names no heavy processes (crew.heavy), so only the turn is waited for.",
              file=sys.stderr)
    deadline = time.time() + minutes * 60
    said = None
    while True:
        snapshot = processes()
        busy = heavy_now(snapshot, patterns)
        turn = turn_holder(place.root, snapshot)
        if not busy and not turn and take_turn(place.root, place.here, command):
            break
        waits = []
        for process in busy[:5]:
            whose = owner(process["command"], place.trees)
            waits.append(f"pid {process['pid']} {shown(process['command'], 70)}" + (f" ({whose['name']})" if whose else ""))
        if len(busy) > 5:
            waits.append(f"and {len(busy) - 5} more")
        if turn:
            waits.append(f"the turn, held since {turn.get('since')} by {holder_name(turn, place.trees)} for: {turn.get('command')}")
        words = "; ".join(waits) or "another session that took the turn at the same moment"
        if words != said:
            print(f"bowline crew: waiting for a quiet machine, up to {minutes:g} minute(s), looking every {every:g} "
                  f"second(s). Running now: {words}.", file=sys.stderr, flush=True)
            said = words
        if time.time() >= deadline:
            print(f"bowline crew: the machine was not quiet within {minutes:g} minute(s), so the command did not run. "
                  f"Still running: {words}. Nothing was stopped; ask that session, or try again later.", file=sys.stderr)
            return TIMED_OUT
        time.sleep(min(every, max(0.1, deadline - time.time())))
    try:
        print(f"bowline crew: the machine is quiet and the turn is this worktree's; running: {shown(' '.join(command))}",
              file=sys.stderr, flush=True)
        if len(command) == 1:
            return subprocess.call(command[0], shell=True)
        program = shutil.which(command[0]) or command[0]
        try:
            return subprocess.call([program] + command[1:])
        except OSError as problem:
            print(f"bowline crew: {command[0]} could not be started: {problem}", file=sys.stderr)
            return 2
    finally:
        give_turn(place.root)


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
    ahead = behind = None
    blobs = {}
    if base:
        code, out = git(path, "rev-list", "--left-right", "--count", f"{base}...HEAD")
        if code == 0 and len(out.split()) == 2:
            behind, ahead = (int(n) for n in out.split())
        # Each committed change with the id of the content it ends in, so that two worktrees whose branches hold the
        # same commit are seen to hold the same file, not two changes of it.
        code, out = git(path, "diff", "--raw", "--no-abbrev", "--no-renames", f"{base}...HEAD")
        for line in out.splitlines() if code == 0 else []:
            facts, _, name = line.partition("\t")
            if line.startswith(":") and name and len(facts.split()) >= 4:
                blobs[name.strip('"')] = facts.split()[3]
    code, out = git(path, "status", "--porcelain", "--untracked-files=all")
    dirty = []
    for line in out.splitlines() if code == 0 else []:
        if len(line) > 3:
            dirty.append(line[3:].split(" -> ")[-1].strip('"'))
            blobs.setdefault(dirty[-1], None)                           # changed here, in no commit yet
    return {"path": path, "name": tree["name"], "branch": tree["branch"], "main": tree["main"],
            "head": tree.get("head"), "ahead": ahead,
            "behind": behind, "uncommitted": len(dirty), "files": sorted(blobs), "blobs": blobs, "dirty": sorted(dirty)}


def collisions(trees):
    """The files that more than one worktree changed differently, as {path: [the worktrees' names]}, from the records
    of a survey. Two worktrees whose commits end in the same content of a file, because one branch was cut from the
    other or both took the same commit, did not change it differently, and neither did one of them that goes on from
    there without a commit yet. It is a collision when their commits end in different content, or when two of them
    each hold a change that is not committed."""
    holders = {}
    for tree in trees:
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
    the commit the worktree is at, "ahead", "behind", "uncommitted", "files": every file the worktree changed, committed or not, by its path from the
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


def do_look(options):
    place = Place(options.repo)
    crew = settings(place.config)
    now = time.time()
    with Lock(state_dir(place.root)):
        claims, dropped = place.settled()
    spoken = load_said(place.root)
    record = survey(place)
    snapshot = processes()
    ports = listening()
    patterns = heavy_patterns(place.config)
    heavy = {p["pid"] for p in heavy_now(snapshot, patterns)}
    keep = [int(p) for p in crew.get("keepPorts") or [] if str(p).isdigit()]
    by_pid = {p["pid"]: p for p in snapshot}
    port_owner = {port: pid for pid, found in (ports or {}).items() for port in found}
    whose = {p["pid"]: owner(p["command"], place.trees) for p in snapshot}

    print(f"bowline crew: {place.trees[0]['path']}, {common.count(len(place.trees), 'worktree', 'worktrees')}"
          + (f", measured against {place.base}" if place.base else ", with no pushed branch to measure against"))
    if place.unreachable:
        print(f"  {common.count(len(place.unreachable), 'worktree that git lists is', 'worktrees that git lists are')} left out, "
              "because this system cannot enter the folder (made from another system's view of the disk, or removed "
              f"by hand): {common.names(place.unreachable, options.verbose)}")
    if not snapshot:
        print("  The system would not list its processes, so none are shown.")
    if ports is None:
        print("  The system has no tool that lists listening ports (netstat, ss or lsof), so none are shown.")
    print()
    quiet = {}
    for tree, measured in zip(place.trees, record["trees"]):
        head = f"  {tree['name']}" + (" (this one)" if tree is place.here else "") + f", branch {tree['branch']}"
        if measured["ahead"] is not None:
            head += f": {common.count(measured['ahead'], 'commit', 'commits')} ahead of {place.base}, {measured['behind']} behind"
        head += f", {common.count(measured['uncommitted'], 'file', 'files')} not committed"
        print(head)
        stamp, what = last_sign(tree["path"], claims, spoken)
        if stamp is None or now - stamp > 24 * 3600:
            quiet[tree["name"]] = "no sign of work" if stamp is None else f"quiet for {how_long(now - stamp)}"
        print("      last sign of work: " + (f"{ago(stamp, now)}, {what}" if stamp else "none on this machine"))
        own = [p for p in snapshot if whose[p["pid"]] is tree and p["pid"] != os.getpid()]
        named = [p for p in own if p["pid"] in heavy or (ports or {}).get(p["pid"])]
        for process in named if not options.verbose else own:
            marks = (["heavy"] if process["pid"] in heavy else []) + [f"listens on {port}" for port in sorted((ports or {}).get(process["pid"], []))]
            print(f"      process: pid {process['pid']} {shown(process['command'])}" + (f" ({', '.join(marks)})" if marks else ""))
        rest = len(own) - len(named)
        if rest and not options.verbose:
            print(f"      and {common.count(rest, 'other process', 'other processes')} that neither count as heavy nor listen (--verbose lists them)")
        for claim in claims:
            if same(claim["worktree"]) == same(tree["path"]):
                why = f": {claim['why']}" if claim.get("why") else ""
                print(f"      claim: {claim['key']}, since {claim.get('since')}{why}")
        spoke = said_by(tree["path"], spoken)
        if spoke:
            when = said_at(spoke)
            print(f"      said, {ago(when, now) if when else spoke.get('at')}: {spoke.get('words')}")
        print()
    outside = [p for p in snapshot if p["pid"] in heavy and whose[p["pid"]] is None]
    if outside:
        print("  Heavy processes that belong to no worktree:")
        for process in outside:
            print(f"      pid {process['pid']} {shown(process['command'])}")
        print()
    if keep:
        print("  The person's own ports, named in " + common.CONFIG_FILE + " (crew.keepPorts). Never stop what listens on them:")
        for port in keep:
            pid = port_owner.get(port)
            who = f"pid {pid} {shown(by_pid[pid]['command'], 70)}" if pid in by_pid else (f"pid {pid}" if pid else "nothing listens now")
            print(f"      {port}: {who}")
        print()

    def said(names):
        return ", ".join(name + (f" ({quiet[name]})" if name in quiet else "") for name in names)

    both = sorted(collisions(record["trees"]).items())
    records = [(path, names) for path, names in both if shared_record(path, place.config)]
    both = [pair for pair in both if pair not in records]
    if both:
        print("  Changed differently in more than one worktree, so a rebase will meet both changes:")
        for path, names in both[:20] if not options.verbose else both:
            print(f"      {path}: {said(names)}")
        if len(both) > 20 and not options.verbose:
            print(f"      and {len(both) - 20} more (--verbose lists them)")
        print()
    if records:
        print("  Shared records (crew.shared), which every session adds to, changed in more than one worktree as they are meant to be:")
        for path, names in records:
            print(f"      {path}: {said(names)}")
        print()
    for claim, reason in dropped:
        print(f"  Dropped the claim {claim['key']} of {holder_name(claim, place.trees)}: {reason}.")
    turn = turn_holder(place.root, snapshot)
    if turn:
        print(f"  The turn for a heavy check is held since {turn.get('since')} by {holder_name(turn, place.trees)}, for: {turn.get('command')}")
    else:
        print("  The turn for a heavy check is free." + ("" if patterns else f" {common.CONFIG_FILE} names no heavy processes (crew.heavy)."))
    print("  The sessions themselves, and what each says it is doing: ListAgents. To tell one what you take: SendMessage.")
    return 0


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
    parser.add_argument("--verbose", action="store_true", help="every process of a worktree and every file changed twice")
    sub = parser.add_subparsers(dest="action")
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
    for name in ("after-rebase", "after-push", "after-commit"):
        p = sub.add_parser(name)
        p.add_argument("--hook", action="store_true", help="read a PostToolUse hook's JSON on standard input; always exit 0")
    sub.add_parser("refresh", help="measure the worktrees again and keep the result, printing nothing")
    p = sub.add_parser("before-edit", help="whether another worktree holds a file: changed, committed or claimed there")
    p.add_argument("--file", help="the file to ask about")
    p.add_argument("--hook", action="store_true", help="read a PreToolUse hook's JSON on standard input; always exit 0")
    p = sub.add_parser("say", help="a few sentences about this worktree's work, for the other sessions' look")
    p.add_argument("words", nargs="*", help="what is done, what you wait on, what you ask; none prints what was said")
    p.add_argument("--clear", action="store_true", help="take back what this worktree said")
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
    if command:
        print("bowline crew: a command after two dashes belongs to crew run: crew run -- <command>", file=sys.stderr)
        return 2
    return do_look(options)


if __name__ == "__main__":
    sys.exit(main())
