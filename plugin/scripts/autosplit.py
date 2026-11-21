"""Autosplit: when a CLAUDE.md outgrows what Claude Code reads, bowline prepares its split in the background, on a
branch of its own, and the next session hears that the split is ready to review.

    python -I scripts/bowline.py autosplit --hook                                    what the Stop and SessionEnd hooks run
    python -I scripts/bowline.py autosplit run --file <CLAUDE.md> [--repo <path>]  the same work now, in the foreground
    python -I scripts/bowline.py autosplit status [--repo <path>]
    python -I scripts/bowline.py autosplit show --file <CLAUDE.md> [--repo <path>]
    python -I scripts/bowline.py autosplit done --file <CLAUDE.md> [--repo <path>]     after the merge: forget the split, delete its branch
    python -I scripts/bowline.py autosplit discard --file <CLAUDE.md> [--repo <path>]  the same for a split that is not wanted, or to try again

Claude Code's autocompact summarizes a conversation when its context fills, without asking, and it can, because that
context is nobody else's input. A CLAUDE.md is every future session's input, so bowline never rewrites one on the
person's branch unasked. With `autosplit.enabled` set in .claude/bowline.json, the hook that runs after every reply
measures the CLAUDE.md files the way the doctor does and, when one is over the limits and committed clean, starts a
worker in the background. The worker adds a git worktree on a new branch from the committed HEAD, runs a headless
Claude Code session there with the unattended procedure of the split-instructions skill, checks the result (a clean
tree, the file under the line target, the budget passing), removes the worktree and keeps the branch. The doctor, and
the one-line finding at a session's start, then say that the split is ready and how to review and merge it. Each
split's state is a small JSON file under <git dir>/bowline/autosplit/, beside its log.
"""

import argparse
import datetime
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import budget  # noqa: E402
import common  # noqa: E402

WORKER_MARK = "BOWLINE_AUTOSPLIT_WORKER"
# What a running Claude Code session puts into the environment of its hooks; the worker's session must not inherit it,
# or it would take itself for a child of the session that started it.
INHERITED_MARKS = ("CLAUDECODE", "CLAUDE_PID")
INHERITED_PREFIXES = ("CLAUDE_CODE_SESSION", "CLAUDE_CODE_CHILD", "CLAUDE_CODE_MESSAGING", "CLAUDE_CODE_BRIDGE",
                      "CLAUDE_CODE_WORKER", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_ENVIRONMENT")
BRANCH_PREFIX = "bowline/split/"
ALLOWED_TOOLS = "Read Edit Write Glob Grep Agent Skill Bash(git *) Bash(python *) Bash(python3 *)"
SKILL = os.path.join(common.PLUGIN_ROOT, "skills", "split-instructions", "SKILL.md")
BOWLINE_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bowline.py")


def git(cwd, *args, timeout=300):
    """Runs git and returns (exit code, its output as text); a non-zero exit is returned, never raised."""
    result = subprocess.run(["git", "-C", cwd, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, timeout=timeout)
    return result.returncode, result.stdout.decode("utf-8", "replace")


def slug_of(path):
    """The file's path as a name git and a file system accept: sub/CLAUDE.md becomes sub-CLAUDE-md."""
    return re.sub(r"[^A-Za-z0-9]+", "-", path.replace("\\", "/")).strip("-")


def branch_of(path):
    return BRANCH_PREFIX + slug_of(path)


def state_dir(root):
    """Where the splits' records live: inside the repository's git folder, shared by its worktrees, never committed.
    A main checkout's .git folder is its common folder, read without starting git; a worktree's .git file asks git."""
    dot = os.path.join(root, ".git")
    if os.path.isdir(dot):
        return os.path.join(os.path.normpath(dot), "bowline", "autosplit")
    code, out = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    folder = os.path.normpath(out.strip()) if code == 0 and out.strip() else os.path.join(root, ".git")
    return os.path.join(folder, "bowline", "autosplit")


def state_path(root, path):
    return os.path.join(state_dir(root), slug_of(path) + ".json")


def log_path(root, path):
    return os.path.join(state_dir(root), slug_of(path) + ".log")


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def load_state(root, path):
    return read_json(state_path(root, path))


def save_state(root, path, state):
    """Writes the record whole, through a temporary file, so that a reader never sees half of it."""
    folder = state_dir(root)
    os.makedirs(folder, exist_ok=True)
    target = state_path(root, path)
    temp = target + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")
    common.replace_file(temp, target)


def all_states(root):
    folder = state_dir(root)
    if not os.path.isdir(folder):
        return []
    states = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            state = read_json(os.path.join(folder, name))
            if state and state.get("file"):
                states.append(state)
    return states


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def settings(config):
    return config.get("autosplit") or {}


def command_of(config):
    """The command that starts a headless Claude Code session: a string names one program, a list a program with its
    arguments."""
    command = settings(config).get("command") or "claude"
    if isinstance(command, str):
        return [command]
    return [str(part) for part in command]


def oversized(root, config, facts=None):
    """The CLAUDE.md files the doctor tells to split, as (path, lines, chars, why), measured as the doctor measures."""
    limits = config["limits"]
    if facts is None:
        _, facts = budget.measure(root, config)
    out = []
    for path, lines, chars in facts["claudeMd"]:
        nested = not common.is_root_claude_md(path)
        if lines >= limits["claudeMdLines"]:
            out.append((path, lines, chars, f"{lines} lines, over the target of {limits['claudeMdLines']}"))
        elif nested and chars > limits["onDemandCutoffSmallWindow"]:
            out.append((path, lines, chars,
                        f"{chars:,} characters, cut at {limits['onDemandCutoffSmallWindow']:,} on a 200K context window"))
    return out


def measure_file(root, config, path):
    """(lines, chars) of one tracked CLAUDE.md as the budget check sees it, or (None, None) when it is not one."""
    _, facts = budget.measure(root, config)
    for found, lines, chars in facts["claudeMd"]:
        if found == path:
            return lines, chars
    return None, None


def waiting_reason(root, config, path):
    """Why a split of this file cannot start now, in a sentence, or None when nothing stands in the way."""
    code, _ = git(root, "ls-files", "--error-unmatch", "--", path)
    if code != 0:
        return f"{path} is not tracked by git yet; the split starts once it is committed"
    _, out = git(root, "status", "--porcelain", "--", path)
    if out.strip():
        return f"{path} has uncommitted changes; the split starts after they are committed"
    command = command_of(config)
    if not shutil.which(command[0]):
        return f"the command '{command[0]}' that starts a headless Claude Code session was not found on this machine's path"
    if not os.path.isfile(SKILL):
        return "the split-instructions skill was not found beside these scripts; autosplit runs from the installed plugin"
    code, _ = git(root, "rev-parse", "--verify", "-q", "refs/heads/" + branch_of(path))
    if code == 0:
        return (f"the branch {branch_of(path)} already exists; after merging it run 'bowline autosplit done --file {path}', "
                f"or 'bowline autosplit discard --file {path}' to start over")
    return None


# The hook


def repositories_to_split(start):
    """The repositories autosplit may work in from a path: the folder itself when it is a folder of repositories with a
    git repository of its own, and every repository bowline may write into. A split is a branch in the repository, so
    a repository the folder leaves untouched never gets one."""
    workspace, roots = common.roots_for(start)
    own = [workspace] if workspace and common.is_repository(workspace) else []
    return own + [root for root in roots if common.writes_allowed(root)]


def do_hook(options):
    """What the Stop and SessionEnd hooks run: prints nothing, exits 0, starts at most one worker per oversized file."""
    if os.environ.get(WORKER_MARK):
        return 0
    cwd = None
    try:
        if sys.stdin is not None and not sys.stdin.isatty():
            facts = json.load(sys.stdin)
            cwd = facts.get("cwd") or None
    except Exception:
        cwd = None
    for root in repositories_to_split(cwd or options.repo or os.getcwd()):
        config = common.load_config(root)
        if not settings(config).get("enabled"):
            continue
        for path, lines, chars, why in oversized(root, config):
            if load_state(root, path) is not None or waiting_reason(root, config, path):
                continue
            if claim(root, path):
                start_worker(root, path, lines, chars, why)
    return 0


def claim(root, path):
    """Creates the split's record exclusively, so that two hooks firing at once cannot both start a worker."""
    os.makedirs(state_dir(root), exist_ok=True)
    try:
        handle = os.open(state_path(root, path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.close(handle)
    return True


def git_bash():
    """Git for Windows' bash, found from git itself, so that the WSL bash on the path is never mistaken for it."""
    git_exe = shutil.which("git")
    if not git_exe:
        return None
    folder = os.path.dirname(os.path.realpath(git_exe))
    for _ in range(3):                      # git.exe sits in bin/, cmd/ or mingw64/bin/ under the installation
        folder = os.path.dirname(folder)
        for candidate in (os.path.join(folder, "bin", "bash.exe"), os.path.join(folder, "usr", "bin", "bash.exe")):
            if os.path.isfile(candidate):
                return candidate
    return None


def start_worker(root, path, lines, chars, why):
    """Starts the worker for one file, detached from this process, so that the hook returns at once."""
    log = log_path(root, path)
    save_state(root, path, {"file": path, "state": "starting", "branch": branch_of(path), "started": now(),
                            "before": {"lines": lines, "chars": chars}, "why": why, "log": log})
    args = [sys.executable, "-I", BOWLINE_PY, "autosplit", "worker", "--repo", root, "--file", path]
    kwargs = {"cwd": root, "stdin": subprocess.DEVNULL, "stderr": subprocess.STDOUT, **common.background_start()}
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(f"\n== {now()}: autosplit starts on {path} ({why}) ==\n")
        handle.flush()
        subprocess.Popen(args, stdout=handle, **kwargs)


# The worker


class Outcome:
    def __init__(self, ok, reason=None, keep_branch=False, details=None):
        self.ok = ok
        self.reason = reason
        self.keep_branch = keep_branch
        self.details = details or {}


def worker_prompt(path, branch, config):
    bowline_py = BOWLINE_PY.replace("\\", "/")
    skill = SKILL.replace("\\", "/")
    target = config["limits"]["claudeMdLines"]
    return (
        f"You are bowline's background worker, and no person is at the keyboard. Split the instruction file {path} of "
        f"this repository into long-form pages, scoped rules and a short index, without losing a line. The procedure is "
        f"the split-instructions skill: read {skill} completely first, then follow its steps with the differences that "
        f"its section 'Unattended: the background worker' gives. This working folder is a git worktree on the branch "
        f"{branch}, made for this work alone: commit here, in the two commits the skill names, and push nothing. Run "
        f"bowline as: python -I \"{bowline_py}\" followed by the command, for example "
        f"python -I \"{bowline_py}\" move plan --file {path}. Never ask a question; where the skill leaves a choice open, "
        f"take the default it names and say so in the commit message. When you finish, {path} must be under {target} "
        f"lines, python -I \"{bowline_py}\" budget must pass, git status must show a clean tree, and the branch must be "
        f"ahead of its base by exactly two commits."
    )


def session_facts(stdout):
    """What a headless session's JSON result says: its cost, its turns, its session id, whether it reports an error."""
    out = {}
    text = stdout.strip()
    start = text.rfind("\n{")
    candidate = text[start + 1:] if start >= 0 else text
    try:
        data = json.loads(candidate)
    except ValueError:
        return out
    if isinstance(data, dict):
        for key, name in (("total_cost_usd", "cost_usd"), ("num_turns", "turns"), ("session_id", "session_id"),
                          ("is_error", "is_error"), ("subtype", "subtype"), ("errors", "errors"), ("result", "result")):
            if key in data:
                out[name] = data[key]
        if isinstance(data.get("permission_denials"), list):
            out["denied"] = len(data["permission_denials"])
    return out


def count_files(name_status, config):
    """How many files the branch adds, by home: pages under the conventions folder, rules, skills, and the rest."""
    def folder(key, default):
        value = config.get(key) or default
        if isinstance(value, list):
            value = value[0] if value else default
        return value.replace("\\", "/").rstrip("/") + "/"
    pages_dir = folder("conventionsDir", "docs/conventions")
    rules_dir = folder("rulesDir", ".claude/rules")
    skills_dir = folder("skillsDir", ".claude/skills")
    counts = {"pages": 0, "rules": 0, "skills": 0, "other": 0}
    for line in name_status.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].startswith("A"):
            continue
        name = parts[-1]
        if name.startswith(pages_dir):
            counts["pages"] += 1
        elif name.startswith(rules_dir):
            counts["rules"] += 1
        elif name.startswith(skills_dir):
            counts["skills"] += 1
        else:
            counts["other"] += 1
    return counts


def run_session(worktree, path, branch, base, config, say):
    """Runs the headless session in the worktree and checks what it left there. Removes nothing."""
    conf = settings(config)
    command = command_of(config)
    program = shutil.which(command[0])
    if not program:
        return Outcome(False, f"the command '{command[0]}' was not found on this machine's path")
    args = [program, *command[1:], "-p", "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--allowedTools", ALLOWED_TOOLS, "--output-format", "json"]
    if conf.get("maxBudgetUsd"):
        args += ["--max-budget-usd", str(conf["maxBudgetUsd"])]
    if conf.get("model"):
        args += ["--model", str(conf["model"])]
    args += [str(part) for part in conf.get("args") or []]
    args.append(worker_prompt(path, branch, config))
    minutes = float(conf.get("timeoutMinutes") or 60)
    say(f"autosplit: running {' '.join(args[:-1])} in {worktree}, for up to {minutes:g} minutes")
    env = {name: value for name, value in os.environ.items()
           if name not in INHERITED_MARKS and not name.startswith(INHERITED_PREFIXES)}
    env[WORKER_MARK] = "1"
    if os.name == "nt" and not env.get("CLAUDE_CODE_GIT_BASH_PATH"):
        # Claude Code runs a hook's command in Git Bash when it finds it, and in PowerShell otherwise, where the
        # plugin's quoted-path hooks are a parse error; the session this worker starts gets the path spelled out.
        bash = git_bash()
        if bash:
            env["CLAUDE_CODE_GIT_BASH_PATH"] = bash
    try:
        result = subprocess.run(args, cwd=worktree, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=minutes * 60)
    except subprocess.TimeoutExpired:
        return Outcome(False, f"the session ran longer than {minutes:g} minutes and was stopped", keep_branch=True)
    except OSError as problem:
        return Outcome(False, f"the command could not be started: {problem}")
    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    details = session_facts(stdout)
    say("autosplit: the session's output follows")
    say(stdout.strip())
    if stderr.strip():
        say(stderr.strip())
    _, dirty = git(worktree, "status", "--porcelain")
    _, log = git(worktree, "log", "--format=%H%x09%s", f"{base}..HEAD")
    commits = []
    for line in log.strip().splitlines():
        parts = line.split("\t", 1)
        commits.append({"hash": parts[0], "subject": parts[1] if len(parts) > 1 else ""})
    details["commits"] = commits
    if result.returncode != 0:
        return Outcome(False, f"the session exited with code {result.returncode}; its output is in the log",
                       keep_branch=bool(commits), details=details)
    if details.get("is_error"):
        said = details.get("errors") or details.get("result") or details.get("subtype") or "no detail given"
        if isinstance(said, list):
            said = "; ".join(str(part) for part in said)
        return Outcome(False, f"the session reported an error ({details.get('subtype') or 'error'}): {str(said)[:200]}",
                       keep_branch=bool(commits), details=details)
    if not commits:
        return Outcome(False, "the session made no commit", details=details)
    if dirty.strip():
        return Outcome(False, "the session left uncommitted changes in the worktree", keep_branch=True, details=details)
    findings, facts = budget.measure(worktree, config)
    lines, chars = None, None
    for found, found_lines, found_chars in facts["claudeMd"]:
        if found == path:
            lines, chars = found_lines, found_chars
    if lines is None:
        return Outcome(False, f"{path} is no longer a tracked file on the branch", keep_branch=True, details=details)
    details["after"] = {"lines": lines, "chars": chars}
    still = [why for found, _, _, why in oversized(worktree, config, facts) if found == path]
    if still:
        return Outcome(False, f"on the branch {path} is still over the limits: {still[0]}", keep_branch=True, details=details)
    problems = [f.what for f in findings if f.level == "problem"]
    if problems:
        return Outcome(False, "on the branch the budget check fails: " + problems[0], keep_branch=True, details=details)
    _, names = git(worktree, "diff", "--name-status", f"{base}..HEAD")
    details["files"] = count_files(names, config)
    return Outcome(True, details=details)


def run_split(root, path, config, say):
    """One split from start to end: the record, the worktree, the session, the checks, the record again."""
    branch = branch_of(path)
    state = load_state(root, path) or {}
    if "before" not in state:
        lines, chars = measure_file(root, config, path)
        state["before"] = {"lines": lines, "chars": chars}
    state.update({"file": path, "state": "running", "branch": branch, "pid": os.getpid(), "log": log_path(root, path),
                  "started": state.get("started") or now()})
    for key in ("reason", "finished", "branch_kept"):
        state.pop(key, None)
    save_state(root, path, state)
    _, out = git(root, "rev-parse", "HEAD")
    base = out.strip()
    state["base"] = base
    code, _ = git(root, "rev-parse", "--verify", "-q", "refs/heads/" + branch)
    if code == 0:
        return finish(root, path, state, Outcome(False, f"the branch {branch} already exists", keep_branch=True), config, say)
    temp = tempfile.mkdtemp(prefix="bowline-split-")
    worktree = os.path.join(temp, slug_of(path))
    code, out = git(root, "worktree", "add", "-q", "-b", branch, worktree, "HEAD")
    if code != 0:
        shutil.rmtree(temp, ignore_errors=True)
        return finish(root, path, state, Outcome(False, "git worktree add failed: " + out.strip()), config, say)
    state["worktree"] = worktree
    try:
        # From here the worktree and the branch exist, so whatever goes wrong, the worktree is removed and the record
        # says how the worker ended. The record is saved inside for that reason: the save was once refused here.
        save_state(root, path, state)
        say(f"autosplit: the branch {branch} from {base[:12]}, in the worktree {worktree}")
        outcome = run_session(worktree, path, branch, base, config, say)
    except Exception as problem:  # noqa: BLE001 - the worker must always record how it ended
        outcome = Outcome(False, f"the worker stopped on an error: {problem}", keep_branch=True)
    finally:
        git(root, "worktree", "remove", "--force", worktree)
        git(root, "worktree", "prune")
        shutil.rmtree(temp, ignore_errors=True)
    state.pop("worktree", None)
    return finish(root, path, state, outcome, config, say)


def finish(root, path, state, outcome, config, say):
    state.update(outcome.details)
    state["finished"] = now()
    if outcome.ok:
        state["state"] = "ready"
        state.pop("reason", None)
        if settings(config).get("deliver") == "merge":
            deliver(root, state)
        save_state(root, path, state)
        say(f"autosplit: {describe(state)}")
        return state
    state["state"] = "failed"
    state["reason"] = outcome.reason
    if not outcome.keep_branch:
        git(root, "branch", "-D", state["branch"])
    state["branch_kept"] = bool(outcome.keep_branch)
    save_state(root, path, state)
    say(f"autosplit: {describe(state)}")
    return state


def deliver(root, state):
    """With deliver set to merge: takes the split's commits onto the person's current branch, when nothing stands in
    the way. Otherwise the split stays on its branch and the record says why."""
    branch, base = state["branch"], state["base"]
    _, dirty = git(root, "status", "--porcelain")
    if dirty.strip():
        state["undelivered"] = "the working tree had uncommitted changes when the split was ready"
        return
    _, head = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    head = head.strip()
    if not head or head == "HEAD":
        state["undelivered"] = "HEAD was not on a branch when the split was ready"
        return
    count = len(state.get("commits") or [])
    code, out = git(root, "cherry-pick", f"{base}..{branch}")
    if code != 0:
        git(root, "cherry-pick", "--abort")
        state["undelivered"] = f"the cherry-pick onto {head} did not apply cleanly: " + " ".join(out.split())[:200]
        return
    _, log = git(root, "log", "--format=%H%x09%s", f"-{count}")
    merged = []
    for line in log.strip().splitlines():
        parts = line.split("\t", 1)
        merged.append({"hash": parts[0], "subject": parts[1] if len(parts) > 1 else ""})
    state["merged"] = list(reversed(merged))
    state["merged_onto"] = head
    state["state"] = "merged"
    state.pop("undelivered", None)
    git(root, "branch", "-D", branch)


def describe(state):
    """One sentence on where a split stands, for the doctor, the status and the log."""
    kind = state.get("state")
    before = (state.get("before") or {}).get("lines")
    after = (state.get("after") or {}).get("lines")
    if kind in ("starting", "running"):
        return f"being prepared in the background since {state.get('started')}; the log is {state.get('log')}"
    if kind == "merged":
        hashes = ", ".join(c["hash"][:8] for c in state.get("merged") or [])
        return (f"merged onto {state.get('merged_onto')} at {state.get('finished')}: commits {hashes}, from {before} lines "
                f"to {after}; the branch {state.get('branch')} is deleted")
    if kind == "ready":
        files = state.get("files") or {}
        words = (f"ready on the branch {state.get('branch')}: {len(state.get('commits') or [])} commit(s), "
                 f"from {before} lines to {after}, {files.get('pages', 0)} page(s) and {files.get('rules', 0)} rule file(s) added")
        if state.get("cost_usd") is not None:
            words += f"; the session cost about ${float(state['cost_usd']):.2f}"
        if state.get("undelivered"):
            words += f"; not merged on its own because {state['undelivered']}"
        return words
    if kind == "failed":
        kept = f"; the branch {state.get('branch')} keeps what was done" if state.get("branch_kept") else ""
        denied = f"; {state['denied']} tool use(s) were denied in the session" if state.get("denied") else ""
        return f"failed at {state.get('finished')}: {state.get('reason')}{kept}{denied}; the log is {state.get('log')}"
    return str(kind)


# What the doctor says


def findings(root, config, facts):
    """The doctor's findings about autosplit: a split ready, running or failed, and why one has not started."""
    out = []
    if not common.writes_allowed(root):
        return out
    enabled = bool(settings(config).get("enabled"))
    states = {s["file"]: s for s in all_states(root)}
    for path, lines, chars, why in oversized(root, config, facts):
        state = states.pop(path, None)
        if state is not None:
            out.append(state_finding(state))
            continue
        if not enabled:
            continue
        reason = waiting_reason(root, config, path)
        if reason:
            out.append(common.Finding(
                "note", f"autosplit has not started on {path}: {reason}.",
                "autosplit is on for this repository, and it starts only from a committed, clean file, with the headless command at hand, on a branch that does not exist yet.",
                "Clear what stands in the way, or split by hand: /bowline:split-instructions."))
        else:
            out.append(common.Finding(
                "note", f"autosplit will start on {path} after the next reply.",
                "The hook that runs after every reply starts the worker; a run of the doctor does not.",
                f"Or start it now, in the foreground: bowline autosplit run --file {path}."))
    for state in states.values():
        if state.get("state") == "ready":
            out.append(common.Finding(
                "note", f"A split of {state['file']} waits on the branch {state['branch']}, but the file is already within the limits.",
                "Either the split was merged by hand, or the file was shortened another way.",
                f"If it was merged: bowline autosplit done --file {state['file']}. Otherwise: bowline autosplit discard --file {state['file']}."))
        elif state.get("state") in ("starting", "running", "failed", "merged"):
            out.append(state_finding(state))
    return out


def state_finding(state):
    path, kind = state["file"], state.get("state")
    if kind == "merged":
        return common.Finding(
            "warning", f"autosplit merged the split of {path}: {describe(state)}.",
            "This repository sets autosplit.deliver to merge, so the result landed on the current branch as soon as it was ready and the tree was clean; the instruction files changed without a review.",
            f"Read what landed: bowline autosplit show --file {path}. Keep it, or revert the commits as show says; then bowline autosplit done --file {path} to clear this notice.")
    if kind == "ready":
        return common.Finding(
            "warning", f"A split of {path} is {describe(state)}.",
            "bowline prepared it in the background from the committed HEAD; nothing on your branch changed, and the branch waits for your review.",
            f"Review and merge it: /bowline:split-instructions review {path}.")
    if kind in ("starting", "running"):
        return common.Finding(
            "note", f"A split of {path} is {describe(state)}.",
            "autosplit is on and the file is over the limits, so a headless Claude Code session works on a branch of its own.",
            "Nothing to do; the result shows here when it is done.")
    return common.Finding(
        "warning", f"The background split of {path} {describe(state)}.",
        "The file is still over the limits, and autosplit does not try again on its own after a failure.",
        f"Read the log, then split by hand with /bowline:split-instructions, or run 'bowline autosplit discard --file {path}' to let autosplit try again after the next reply.")


def adjust(findings_list, root):
    """Points the doctor's own split findings at the review once a split is ready."""
    ready = {s["file"]: s for s in all_states(root) if s.get("state") == "ready"}
    for finding in findings_list:
        for path, state in ready.items():
            if finding.what.startswith(path + " ") and finding.fix and "split-instructions" in finding.fix and "review" not in finding.fix:
                finding.fix = f"A split is ready on the branch {state['branch']}; review and merge it: /bowline:split-instructions review {path}."


# The commands a person runs


def locate(file, repo):
    """(repository root, the file's path from that root) for a --file: the repository is --repo's, or the current one, or
    the one the file's own folder is in, so that from a folder of repositories `--file repo1/sub/CLAUDE.md` works."""
    root = common.repo_root(repo or os.getcwd())
    given = file.replace("\\", "/")
    under_root = root is not None and os.path.exists(os.path.join(root, given))
    if os.path.isabs(given) or (os.path.exists(given) and not under_root) or root is None:
        candidate = common.repo_root(os.path.dirname(os.path.abspath(given)))
        if candidate:
            root = candidate
            given = os.path.relpath(os.path.realpath(os.path.abspath(given)), os.path.realpath(candidate)).replace("\\", "/")
    return root, given.strip("/")


def do_run(root, config, path, foreground):
    state = load_state(root, path)
    if foreground and state and state.get("state") in ("starting", "running"):
        print(f"bowline autosplit: a split of {path} is already {describe(state)}.", file=sys.stderr)
        return 1
    if foreground and state and state.get("state") == "ready":
        print(f"bowline autosplit: a split of {path} is already {describe(state)}. Review it, or discard it first.", file=sys.stderr)
        return 1
    lines, _ = measure_file(root, config, path)
    if lines is None:
        print(f"bowline autosplit: {path} is not a tracked CLAUDE.md of this repository.", file=sys.stderr)
        return 2
    if foreground:
        reason = waiting_reason(root, config, path)
        if reason:
            print(f"bowline autosplit: cannot start: {reason}.", file=sys.stderr)
            return 1
    final = run_split(root, path, config, functools.partial(print, flush=True))
    return 0 if final.get("state") in ("ready", "merged") else 1


def do_status(root, config):
    enabled = bool(settings(config).get("enabled"))
    print(f"repository: {root}")
    print(f"autosplit: {'on' if enabled else 'off'} (autosplit.enabled in {common.CONFIG_FILE}); command: {' '.join(command_of(config))}")
    states = {s["file"]: s for s in all_states(root)}
    _, facts = budget.measure(root, config)
    over = oversized(root, config, facts)
    if not states and not over:
        print("splits: none; every CLAUDE.md is within the limits.")
        return 0
    for path, lines, chars, why in over:
        state = states.pop(path, None)
        if state:
            print(f"  {path}: {describe(state)}")
            continue
        if not common.writes_allowed(root):
            reason = common.left_alone(root)
        else:
            reason = waiting_reason(root, config, path) if enabled else "autosplit is off"
        print(f"  {path}: over the limits ({why}); " + (f"waiting: {reason}" if reason else "starts after the next reply"))
    for path, state in states.items():
        print(f"  {path}: {describe(state)} (the file is within the limits now)")
    return 0


def do_show(root, path):
    state = load_state(root, path)
    if not state:
        print(f"bowline autosplit: no split of {path} is known; 'bowline autosplit status' lists them.", file=sys.stderr)
        return 1
    print(f"file: {path}")
    print(f"state: {describe(state)}")
    branch, base = state.get("branch"), state.get("base")
    if base and (state.get("state") == "ready" or state.get("branch_kept")):
        print(f"branch: {branch}, from {base}")
        print()
        _, log = git(root, "log", "--format=commit %h%n%B", f"{base}..{branch}")
        print(log.strip())
        print()
        _, stat = git(root, "diff", "--stat", f"{base}..{branch}")
        print(stat.rstrip())
        print()
    if state.get("state") == "merged":
        hashes = [c["hash"] for c in state.get("merged") or []]
        for commit in hashes:
            _, log = git(root, "show", "-s", "--format=commit %h%n%B", commit)
            print(log.strip())
            print()
        if hashes:
            _, stat = git(root, "diff", "--stat", f"{hashes[0]}^..{hashes[-1]}")
            print(stat.rstrip())
            print()
            print(f"The commits are on {state.get('merged_onto')}. To undo them:")
            print(f"  git revert {hashes[0]}^..{hashes[-1]}")
        print(f"Then clear this record: bowline autosplit done --file {path}")
    elif state.get("state") == "ready":
        print("To take the split onto the current branch, with its two commits as they are:")
        print(f"  git cherry-pick {base}..{branch}")
        print("then forget the split and delete its branch:")
        print(f"  bowline autosplit done --file {path}")
        print(f"To drop it instead: bowline autosplit discard --file {path}")
    elif state.get("state") == "failed":
        if state.get("result"):
            print("The session's own closing words, which usually name the cause:")
            print()
            print(str(state["result"]).strip())
            print()
        print(f"log: {state.get('log')}")
    return 0


def do_forget(root, path, merged):
    state = load_state(root, path)
    if not state:
        print(f"bowline autosplit: no split of {path} is known; 'bowline autosplit status' lists them.", file=sys.stderr)
        return 1
    if state.get("state") in ("starting", "running"):
        print(f"bowline autosplit: the split of {path} is still running (process {state.get('pid')}); wait for it, or stop that process first.", file=sys.stderr)
        return 1
    branch = state.get("branch") or branch_of(path)
    exists = git(root, "rev-parse", "--verify", "-q", "refs/heads/" + branch)[0] == 0
    code, out = git(root, "branch", "-D", branch) if exists else (1, "")
    for ext in (".json", ".log"):
        try:
            os.remove(os.path.join(state_dir(root), slug_of(path) + ext))
        except OSError:
            pass
    words = "merged and forgotten" if merged else "dropped"
    if exists and code != 0:
        print(f"bowline autosplit: the split of {path} is {words}, but git could not delete the branch {branch}: {out.strip()}")
        return 1
    if state.get("state") == "merged":
        print(f"bowline autosplit: the record of the split of {path} is cleared; its commits stay on {state.get('merged_onto')}.")
        return 0
    print(f"bowline autosplit: the split of {path} is {words}; " + (f"the branch {branch} is deleted." if exists else f"there was no branch {branch} to delete."))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepares the split of an oversized CLAUDE.md in the background, on a branch of its own.")
    parser.add_argument("--hook", action="store_true", help="what the Stop and SessionEnd hooks run: prints nothing and exits 0")
    parser.add_argument("--repo", help="a path inside the repository (default: the current folder)")
    sub = parser.add_subparsers(dest="command")
    for name in ("run", "worker", "show", "done", "discard"):
        p = sub.add_parser(name)
        p.add_argument("--file", required=True, help="the CLAUDE.md, as a path from the repository's root")
        p.add_argument("--repo", default=argparse.SUPPRESS)
    p = sub.add_parser("status")
    p.add_argument("--repo", default=argparse.SUPPRESS)
    options = parser.parse_args(argv)
    if options.hook:
        try:
            return do_hook(options)
        except BaseException:  # noqa: BLE001 - a hook must never fail a reply
            return 0
    if not options.command:
        parser.print_help()
        return 2
    if options.command == "status":
        workspace, roots = common.roots_for(options.repo or os.getcwd())
        if not roots:
            print("bowline autosplit: not inside a git repository, and this folder holds none.", file=sys.stderr)
            return 2
        targets = ([workspace] if workspace and common.is_repository(workspace) else []) + roots
        for index, root in enumerate(targets):
            if index:
                print()
            do_status(root, common.load_config(root))
        return 0
    root, path = locate(options.file, options.repo)
    if not root:
        _, roots = common.roots_for(options.repo or os.getcwd())
        hint = " From a folder of repositories, give the file as a path from here (repo1/sub/CLAUDE.md) or pass --repo." if roots else ", and this folder holds none."
        print("bowline autosplit: not inside a git repository" + hint, file=sys.stderr)
        return 2
    config = common.load_config(root)
    if options.command in ("run", "worker"):
        if not common.writes_allowed(root):
            print(f"bowline autosplit: {common.left_alone(root)}, and a split is a branch in it. "
                  f"Split {path} by hand in a clone of your own, or ask the repository's owners.", file=sys.stderr)
            return 1
        return do_run(root, config, path, foreground=options.command == "run")
    if options.command == "show":
        return do_show(root, path)
    return do_forget(root, path, merged=options.command == "done")


if __name__ == "__main__":
    sys.exit(main())
