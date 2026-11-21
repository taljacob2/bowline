"""The crew's check before an edit: whether the file about to be changed is another worktree's too.

    python -I scripts/bowline.py crew before-edit --file <path>     for a person: who else holds this file
    python -I scripts/bowline.py crew before-edit --hook            as a PreToolUse hook on Edit, Write and NotebookEdit

Two sessions that change one file in two worktrees do not see each other until one of them rebases, and by then both
have built on their own copy. This check tells the second session at its first edit of the file, while agreeing who
changes what still costs one message.

Another worktree holds a file in one of three ways:
- it has a change of the file that is not committed;
- it has a commit of the file that is neither in the branch every session pushes to nor in the branch of the worktree
  being edited. The last part matters when one session builds on another's branch: what both branches hold is not two
  changes;
- it took the claim `file:<path>` (`bowline crew claim`), which says so before any change is on disk.

The first two are read from what the crew last measured (crew.cached_survey, kept in the repository's git folder),
never measured here: a hook answers before every edit, and measuring nineteen worktrees on a slow disk took 140
seconds on the first repository that used it. When that record is older than crew.changedCacheSeconds, the hook starts
`crew refresh` as a process of its own, waits a moment for it, and otherwise answers from the record it has, so an edit
never waits for a slow disk.

The hook answers as additionalContext, which Claude Code puts next to the tool's result, and gives no permission
decision, so the edit goes through the person's usual permission flow and is never blocked; a warning that stopped
work would be turned off. It speaks once per session and file, and always exits 0. It is silent when the repository
has one worktree, when crew.warnBeforeEdit is false, and for a file every session adds to on purpose: one that
crew.shared names, a numbered list (crew.numbers) or a stamp (crew.stamps).
"""

import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import crew  # noqa: E402

BOWLINE_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bowline.py")
# How long a hook waits for the worktrees to be measured again before it answers from the record it has.
HOOK_WAIT_SECONDS = 2
# A record older than this says nothing true about who works here now; a hook that has only this stays silent.
TOO_OLD_SECONDS = 3600
# A measuring process that started this long ago and wrote nothing is taken for stopped, and another may start.
MEASURING_SECONDS = 300
# How long a session's record of what it was told is kept.
TOLD_SECONDS = 24 * 3600


def measuring_path(root):
    return os.path.join(crew.state_dir(root), "changed.measuring")


def told_path(root):
    return os.path.join(crew.state_dir(root), "told.json")


def cache_seconds(config):
    value = crew.settings(config).get("changedCacheSeconds")
    return 60 if value is None else max(0, value)


def age(record, now=None):
    return (time.time() if now is None else now) - (record.get("at") or 0)


def start_measuring(root):
    """Starts `crew refresh`, detached from this process, unless one started a moment ago."""
    marker = measuring_path(root)
    try:
        if time.time() - os.path.getmtime(marker) < MEASURING_SECONDS:
            return False
    except OSError:
        pass
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()) + "\n")
    kwargs = {"cwd": root, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, "-I", BOWLINE_PY, "crew", "refresh", "--repo", root], **kwargs)
    return True


def measured(root, config, wait):
    """The record a check answers from. A fresh one is taken as it is. Otherwise a measuring starts and the check waits
    up to `wait` seconds for it, then takes whatever is kept unless it is too old to mean anything. wait None is a
    person's question, which may take as long as measuring takes."""
    limit = cache_seconds(config)
    record = crew.cached_survey(root)
    if record and age(record) <= limit:
        return record
    if wait is None:
        return crew.survey(crew.Place(root))
    start_measuring(root)
    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(0.1)
        record = crew.cached_survey(root)
        if record and age(record) <= limit:
            break
    if record and age(record) <= limit:
        try:
            os.remove(measuring_path(root))         # the measuring finished; the next stale record may start another
        except OSError:
            pass
    return record if record and age(record) <= TOO_OLD_SECONDS else None


def is_shared(rel, config):
    """Whether a file is one every session adds to on purpose: crew.shared, a numbered list or a stamp."""
    if crew.shared_record(rel, config):
        return True
    named = [path for path, _ in crew.number_lists(config).values()]
    named += [entry["file"] for entry in crew.settings(config).get("stamps") or [] if isinstance(entry, dict) and entry.get("file")]
    return any(crew.same(rel) == crew.same(name) for name in named)


def place_of(path):
    """The worktree a file is in and the file's path inside it, as (worktree's top folder, path with forward slashes),
    or None outside a repository. The file may not exist yet, so the nearest folder that does is what git is asked."""
    path = os.path.abspath(path)
    folder = os.path.dirname(path)
    while not os.path.isdir(folder):
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent
    root = common.repo_root(folder)
    if not root:
        return None
    # git names the real folder; the path given may reach it through a link or, on Windows, a short name.
    real = os.path.join(os.path.realpath(folder), os.path.relpath(path, folder))
    rel = os.path.relpath(real, os.path.realpath(root)).replace("\\", "/")
    if rel.startswith("../"):
        return None
    return root, rel


def listed(names, rel):
    """Whether a worktree's list of files holds this one. git lists an untracked folder as `folder/`, which holds every
    file under it."""
    wanted = crew.same(rel)
    for name in names or []:
        folded = crew.same(name) + ("/" if name.endswith("/") else "")
        if folded == wanted or (folded.endswith("/") and wanted.startswith(folded)):
            return True
    return False


def holds_other_commit(here, tree, rel, blob):
    """Whether another worktree's commits change a file in a way this worktree's branch does not already hold. From
    where the two branches part to the other's commit, git is asked for this one file: nothing means this branch has
    the change, as when it was cut from the other. Without a name for the other's commit, the contents are compared."""
    ref = tree.get("head") or ("refs/heads/" + tree["branch"] if tree.get("branch") not in (None, "", "no branch") else None)
    if ref:
        code, out = crew.git(here, "diff", "--name-only", f"HEAD...{ref}", "--", rel)
        if code == 0:
            return bool(out.strip())
    code, out = crew.git(here, "rev-parse", "-q", "--verify", f"HEAD:{rel}")
    return not (code == 0 and out.strip() == blob)


def holders(record, claims, here, rel):
    """The other worktrees that hold this file, as (worktree, how, why): "not committed", "committed", or "claimed" with
    the claim's reason."""
    found = []
    for tree in record["trees"] if record else []:
        if crew.same(tree["path"]) == crew.same(here):
            continue
        blobs = tree.get("blobs") or {}
        blob = next((value for name, value in blobs.items() if crew.same(name) == crew.same(rel)), None)
        if listed(tree.get("dirty"), rel):
            found.append((tree, "not committed", None))
        elif blob and holds_other_commit(here, tree, rel, blob):
            found.append((tree, "committed", None))
    seen = {crew.same(tree["path"]) for tree, _, _ in found}
    key = "file:" + crew.same(rel)
    for claim in claims:
        folded = str(claim.get("key") or "").strip().lower().replace("\\", "/")
        where = claim.get("worktree") or ""
        if folded != key.lower() or crew.same(where) == crew.same(here) or crew.same(where) in seen:
            continue
        tree = next((t for t in record["trees"] if crew.same(t["path"]) == crew.same(where)), None) if record else None
        tree = tree or {"path": where, "name": where.replace("\\", "/"), "branch": "a branch not measured yet"}
        found.append((tree, "claimed", claim.get("why")))
    return found


def check(path, wait=None):
    """What is known about one file: None when there is nothing to say, else {"root", "rel", "holders", "record",
    "claims"}. wait is how long to wait for a measuring; None measures now, as a person's question may."""
    place = place_of(path)
    if not place:
        return None
    root, rel = place
    config = common.load_config(root)
    if not crew.settings(config).get("warnBeforeEdit", True):
        return None
    if worktree_count(root) < 2 or is_shared(rel, config):
        return None
    record = measured(root, config, wait)
    claims = crew.load_claims(root)
    found = holders(record, claims, root, rel)
    return {"root": root, "rel": rel, "holders": found, "record": record, "claims": claims} if found else None


def words(found, now=None):
    """The warning, for Claude or for a person: what, why, and what to do."""
    now = time.time() if now is None else now
    rel, record = found["rel"], found["record"] or {}
    base = record.get("base")
    places = []
    said = crew.load_said(found["root"])
    for tree, how, why in found["holders"]:
        stamp, sign = crew.last_sign(tree["path"], found["claims"], said)
        when = f"last sign of work there: {sign}, {crew.ago(stamp, now)}" if stamp else "no sign of when a session last worked there"
        # That the worktree's session said something of itself, and when; never the words. They are that session's
        # free text, and `bowline crew`, which Claude runs on purpose, shows them as what they are.
        spoke = crew.said_by(tree["path"], said)
        if spoke and crew.said_at(spoke):
            when += f"; its session said what it is doing {crew.ago(crew.said_at(spoke), now)}, and `bowline crew` shows it"
        if how == "claimed":
            state = "claimed there" + (f" for: {why}" if why else "")
        elif how == "not committed":
            state = "changed there and not committed"
        else:
            state = "committed there and not in " + base if base else "committed there"
        places.append(f"{tree['name']}, on the branch {tree['branch']} ({state}; {when})")
    several = len(places) > 1
    read = ""
    if record.get("at"):
        seconds = int(max(0, age(record, now)))
        read = " The worktrees were measured " + ("just now." if seconds < 5 else crew.ago(record["at"], now) + ".")
    return (f"bowline crew: {rel} is also held by {'other worktrees' if several else 'another worktree'} of this repository: "
            f"{'; '.join(places)}. Two sessions that change one file at once find out at the rebase, when both have built "
            f"on their own copy. Before you change the file further, tell {'those sessions' if several else 'that session'} "
            "with SendMessage which part of it you change, agree who changes what, and name the agreement in your commit "
            "message. When you cannot reach a session, wait for its push and rebase onto it; when the work there is old "
            "and no session holds it, say so to the person and go on. A file every session adds to, such as a roadmap, "
            f"belongs in {common.CONFIG_FILE} (crew.shared), and is then never warned about.{read} /bowline:crew has the "
            "procedure.")


def already_told(root, session, found):
    """Whether this session heard this warning before, and records that it hears it now. One warning per session, file
    and set of worktrees: said again at every edit, it would be read past."""
    if not session:
        return False
    key = found["rel"] + " | " + ", ".join(sorted(crew.same(tree["path"]) + " " + how for tree, how, _ in found["holders"]))
    now = time.time()
    told = crew.read_json(told_path(root), {})
    told = {name: entry for name, entry in told.items()
            if isinstance(entry, dict) and now - (entry.get("at") or 0) <= TOLD_SECONDS} if isinstance(told, dict) else {}
    mine = told.setdefault(session, {"keys": []})
    heard = key in (mine.get("keys") or [])
    if not heard:
        mine["keys"] = list(mine.get("keys") or []) + [key]
    mine["at"] = now
    try:
        crew.write_json(told_path(root), told)
    except OSError:
        pass
    return heard


def do_hook():
    """The PreToolUse hook: one warning as additionalContext, or nothing. Never a permission decision."""
    facts = json.load(sys.stdin)
    tool_input = facts.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path or not os.path.isabs(str(path)):
        return 0
    found = check(str(path), wait=HOOK_WAIT_SECONDS)
    if not found or already_told(found["root"], str(facts.get("session_id") or ""), found):
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": words(found)}}))
    return 0


def do_before_edit(options):
    if options.hook:
        try:
            return do_hook()
        except BaseException:  # noqa: BLE001 - a hook must never fail the edit it comes before
            return 0
    if not options.file:
        print("bowline crew: before-edit needs --file <path>, or --hook for the hook.", file=sys.stderr)
        return 2
    path = options.file if os.path.isabs(options.file) else os.path.join(options.repo or os.getcwd(), options.file)
    place = place_of(path)
    if not place:
        print(f"bowline crew: {options.file} is not inside a git repository.", file=sys.stderr)
        return 2
    found = check(path)
    if found:
        print(words(found))
        return 0
    root, rel = place
    config = common.load_config(root)
    if not crew.settings(config).get("warnBeforeEdit", True):
        print(f"bowline crew: the warning before an edit is turned off in {common.CONFIG_FILE} (crew.warnBeforeEdit).")
    elif worktree_count(root) < 2:
        print("bowline crew: this repository has one worktree, so no other session's changes are beside this one.")
    elif is_shared(rel, config):
        print(f"bowline crew: {rel} is a file every session adds to ({common.CONFIG_FILE}: crew.shared, crew.numbers or "
              "crew.stamps), so it is never warned about. Add your own entry with the Edit tool and leave the others'.")
    else:
        print(f"bowline crew: no other worktree has changed or claimed {rel}.")
    return 0


# The doctor's note.

def worktree_count(root):
    """How many worktrees the repository has, read from its git folder without starting git: the main checkout, and one
    folder under <git folder>/worktrees for every other."""
    dot = os.path.join(root, ".git")
    if os.path.isdir(dot):
        folder = os.path.join(dot, "worktrees")
    else:
        try:
            with open(dot, encoding="utf-8") as handle:
                text = handle.read().strip()
        except OSError:
            return 1
        if not text.startswith("gitdir:"):
            return 1
        folder = os.path.dirname(os.path.normpath(os.path.join(root, text[len("gitdir:"):].strip())))
        if os.path.basename(folder) != "worktrees":
            return 1                            # a submodule's git folder, not a worktree's
    try:
        return 1 + sum(1 for entry in os.scandir(folder) if entry.is_dir())
    except OSError:
        return 1


def has_rule(root, config):
    """Whether the repository's instructions have a section about sessions that work side by side: a heading that
    names other, parallel or several sessions, in a rule or in a root CLAUDE.md."""
    heading = re.compile(r"^#{1,3}\s.*\b(other|parallel|several)\s+sessions\b", re.IGNORECASE | re.MULTILINE)
    rules = os.path.join(root, *str(config.get("rulesDir") or ".claude/rules").split("/"))
    paths = [os.path.join(root, path) for path in common.root_claude_md(root)]
    for folder, _, files in os.walk(rules):
        paths += [os.path.join(folder, name) for name in files if name.endswith(".md")]
    for path in paths:
        try:
            if heading.search(common.read_text(path)):
                return True
        except OSError:
            pass
    return False


def findings(root, config):
    """The doctor's note for a repository that has several worktrees and no rule about working beside other sessions.
    A note, not a warning: a worktree can also be one that Claude Code made for a subagent, or a person's own second
    checkout, and a convention is offered, never pressed at every session's start."""
    count = worktree_count(root)
    if count < 2 or has_rule(root, config):
        return []
    return [common.Finding(
        "note", f"The repository has {count} worktrees and no rule about working beside other sessions.",
        "Each worktree can hold a Claude Code session of its own. Two sessions that change one file, take one roadmap "
        "number or run two test suites at once find out at the rebase or at a failed check; a rule in the repository "
        "tells every session, in every client, how the work is split.",
        "/bowline:crew offers the rule, as .claude/rules/beside-other-sessions.md, and sets the repository up. Without "
        "the rule, bowline still warns Claude before an edit of a file that another worktree holds.",
        many="{count} repositories have several worktrees and no rule about working beside other sessions.")]
