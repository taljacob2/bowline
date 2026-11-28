"""The doctor: measures a repository and this machine against what Claude Code reads, and says what to do.

    python -I scripts/doctor.py [--repo <path>] [--no-memory]
    python -I scripts/doctor.py --brief [--no-memory]      one line per problem or warning, nothing when clean (the SessionStart hook)
    python -I scripts/doctor.py --watch                    after a reply: one reminder to the person when something new crosses a limit (the Stop hook)
    python -I scripts/doctor.py --pending                  before a prompt: the same reminder, once, for Claude (the UserPromptSubmit hook)
    python -I scripts/doctor.py [--verbose] [--folder-only]  from a folder of repositories: every finding one by one, or the folder alone

For each finding it prints three lines: what it found, why it matters, what to do and which skill does it. It reports:
- every CLAUDE.md against the line target, and for a nested one how much of it is never read on a 200K and on a 1M
  context window, naming the section the cut falls in;
- the rules per area and the unscoped rules against their budgets, skills against theirs, and pointers outside the
  repository (the budget check);
- the memory folder Claude Code keeps for this repository on this machine: its index against the cap, each note
  against the commits it names (a note that keeps finished work like a log), whether the folder is a git repository
  with a remote, whether the push hook is installed, a change that has waited for the backup longer than a day, and
  lines that one session added to a note and another session removed soon after (the memory is one folder for every
  worktree, so a note saved whole from an older copy loses them);
- for a repository that names them in its .claude/bowline.json (crew): a number that appears twice in a numbered list
  such as a roadmap, and a stamp that names a commit the branch no longer holds, both of which a rebase leaves behind;
- as a note, a repository that has several worktrees and no rule about working beside other sessions;
- as a warning, each worktree but the main checkout that holds, in its top level or one level down, a junction, a
  symbolic link or a mount point to a folder outside it: where it points, why it matters (Git for Windows' git
  worktree remove deletes what a junction points to, and Claude Desktop's own clean-up of worktrees never asks
  bowline), and the command that takes it away alone. --brief gives it first, whole, on a line of its own, apart
  from the findings about the instructions and the memory, for up to LINKS_SHOWN worktrees;
- whether the root CLAUDE.md has a compaction section, whether the gate and the budget check are installed, and
  whether the repository has a .claude/bowline.json;
- a split that autosplit prepared in the background, ready on its branch, still running or failed, and why one has
  not started, when the repository turned autosplit on.
From a folder that is not a repository but holds several, as with services cloned side by side, it measures the
folder's own CLAUDE.md and every repository directly under it, names the repository in each finding, and reads the
one memory folder Claude Code keeps for a session started there.
At a session's start, --brief adds one line about working beside other sessions, in every repository, because several
sessions in one repository is taken as the usual case (crew.assumeOthers; false gives the line only when another
session is seen, and crew.activeMinutes 0 gives none). It names the places where another Claude Code session worked in
the last crew.activeMinutes minutes, each on its own with the sessions seen there, saying which one is the session's
own folder, or says that none shows now, and points to /bowline:crew and /bowline:collaborate. It reads when the
transcript files in Claude Code's project folders were written, and of what they hold only the session's title from the
file's end; the names come first from what the last `bowline crew` heard from `claude agents`. In a repository that has no rule about working beside other sessions, the line also
carries the rule's main points and says that /bowline:crew sets the repository up. --pending, before a prompt, names
each place where another session started to work since this one was last told, once.
Exit codes: 0 when nothing is a problem (warnings and notes allowed), 1 when at least one problem was found, 2 when the
script could not run. The three hook modes always exit 0.

The reminders during a session: --brief records what it said at the session's start under <git dir>/bowline/watch.json.
--watch measures again after every reply and, when a finding appears that was not there before (a CLAUDE.md that
crossed the line target, a rules area over its budget, the memory index at its cap), prints it once as a hook
systemMessage, which Claude Code shows to the person, and keeps it pending for Claude. --pending prints what is pending
as plain text, which Claude Code adds to Claude's context at the person's next prompt, and clears it. A finding's
identity is its words with the numbers blanked, so a file that keeps growing is one reminder, not one per reply.
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autosplit  # noqa: E402
import budget  # noqa: E402
import common  # noqa: E402
import crew  # noqa: E402
import crew_edit  # noqa: E402
import memory  # noqa: E402

HEADING = re.compile(r"^#{1,3} (.+)$", re.MULTILINE)


def cut_point(text, cutoff):
    """Where a cutoff falls in a file: (line number, the heading of the section it falls in, the sections never read)."""
    if len(text) <= cutoff:
        return None
    before = text[:cutoff]
    line = before.count("\n") + 1
    headings = [(m.start(), m.group(1).strip()) for m in HEADING.finditer(text)]
    current = None
    never = []
    for start, title in headings:
        if start <= cutoff:
            current = title
        else:
            never.append(title)
    return line, current, never


def claude_md_findings(root, config, facts):
    limits = config["limits"]
    small, large = limits["onDemandCutoffSmallWindow"], limits["onDemandCutoffLargeWindow"]
    findings = []
    for path, lines, chars in facts["claudeMd"]:
        if common.is_root_claude_md(path):
            continue        # a root file loads whole at a session's start; only a nested one is cut
        text = common.read_text(os.path.join(root, path))
        for cutoff, window in ((small, "a 200K context window"), (large, "a 1M context window")):
            cut = cut_point(text, cutoff)
            if not cut:
                continue
            line, section, never = cut
            share = 100 - int(100 * cutoff / max(chars, 1))
            where = f"inside the section \"{section}\"" if section else "before its first heading"
            lost = f"; never read: {', '.join(never[:6])}" + (" and more" if len(never) > 6 else "") if never else ""
            findings.append(common.Finding(
                "problem",
                f"{path} is cut at line {line} on {window}, {where}: about {share}% of the file is never read there{lost}.",
                config["limitsWhy"]["onDemandCutoffSmallWindow" if cutoff == small else "onDemandCutoffLargeWindow"],
                "Move the long form into docs pages and the rules into .claude/rules/ scoped by path, and keep this file an index: /bowline:split-instructions."))
            break
        if chars >= limits["skippedFileBytes"]:
            findings.append(common.Finding("problem", f"{path} is over 4 MiB and is skipped entirely.",
                                           config["limitsWhy"]["skippedFileBytes"], "Split it: /bowline:split-instructions."))
    return findings


def root_claude_md_findings(root, facts):
    findings = []
    measured = {p.replace("\\", "/") for p, _, _ in facts["claudeMd"]}
    roots = [p for p in common.ROOT_CLAUDE_MD if p in measured]        # named in the order Claude Code's docs give
    if not roots:
        findings.append(common.Finding(
            "warning", "The repository has no root CLAUDE.md.",
            "The root CLAUDE.md is the one file every session loads whole and re-reads after a compaction; without it nothing standing survives a summary.",
            "Create one with the writing rules, where decisions are recorded, and a Compact Instructions section: /bowline:init.",
            many="{count} repositories have no root CLAUDE.md."))
        return findings
    # CLAUDE.md and .claude/CLAUDE.md both load whole, so a section in either one counts.
    text = "\n".join(common.read_text(os.path.join(root, path)) for path in roots)
    name = " and ".join(roots)
    has, says = ("has", "does not say") if len(roots) == 1 else ("have", "do not say")
    if not re.search(r"^#+\s*compact instructions", text, re.IGNORECASE | re.MULTILINE):
        findings.append(common.Finding(
            "warning", f"{name} {has} no \"Compact Instructions\" section.",
            "Claude Code replaces a long conversation with a summary, when the context fills and after about an hour of quiet; this section tells every summary what to keep.",
            "Add the section: /bowline:init offers the text, and bowline's docs/conventions.md says what it is for."))
    if not re.search(r"^#+\s*memory between sessions", text, re.IGNORECASE | re.MULTILINE):
        findings.append(common.Finding(
            "note", f"{name} {says} what the memory folder is for.",
            "A session that knows the index loads only to 200 lines keeps it short; one that does not fills it until the newest notes fall off.",
            "Add the section: /bowline:init offers the text."))
    return findings


def memory_findings(root, config):
    limits = config["limits"]
    findings = []
    checkout = common.main_checkout(root)
    folder = common.memory_folder(checkout)
    project = os.path.dirname(folder)
    if not os.path.isdir(project):
        findings.append(common.Finding(
            "note", f"Claude Code has no project folder for {checkout} on this machine (expected {project}).",
            "The folder is made the first time Claude Code runs in the repository; its name is the path with every other character replaced by a dash, as observed, not documented.",
            "Nothing to do until a session has run here."))
        return findings
    index = os.path.join(folder, "MEMORY.md")
    if not os.path.isfile(index):
        findings.append(common.Finding("note", "The memory folder has no MEMORY.md yet.", "Claude writes it at the first memory it keeps.", None))
    else:
        text = common.read_text(index)
        lines, size = common.count_lines(text), len(text.encode("utf-8"))
        if lines >= limits["memoryIndexLines"] or size >= limits["memoryIndexBytes"]:
            findings.append(common.Finding(
                "problem", f"MEMORY.md has {lines} lines and {size:,} bytes; only the first {limits['memoryIndexLines']} lines or {limits['memoryIndexBytes']:,} bytes load.",
                config["limitsWhy"]["memoryIndexLines"],
                "Fold finished items into one line each and promote project knowledge into the repository: /bowline:curate-memory."))
        elif lines >= int(limits["memoryIndexLines"] * 0.8) or size >= int(limits["memoryIndexBytes"] * 0.8):
            findings.append(common.Finding(
                "warning", f"MEMORY.md is at {lines} lines and {size:,} bytes, near the cap of {limits['memoryIndexLines']} lines or {limits['memoryIndexBytes']:,} bytes.",
                config["limitsWhy"]["memoryIndexLines"], "Curate before it passes the cap: /bowline:curate-memory."))
    findings.extend(note_findings(folder, config))
    if not os.path.isdir(os.path.join(folder, ".git")):
        findings.append(common.Finding(
            "warning", f"The memory folder {folder} is not backed up.",
            "Memory is per person and per machine, outside the repository; a lost or reinstalled machine loses every note.",
            "Make it a git repository pushed to a private remote after every reply: /bowline:memory-backup setup <remote>."))
    else:
        remote = common.run_git(["-C", folder, "remote", "get-url", "origin"], check=False).strip()
        if not remote:
            findings.append(common.Finding("warning", "The memory folder is a git repository with no remote.",
                                           "A local repository is lost with the machine like the folder itself.", "/bowline:memory-backup setup <remote>."))
        hooked = hook_installed()
        if not hooked:
            findings.append(common.Finding(
                "warning", "No hook pushes the memory folder after a reply.",
                "Without the hook the backup is only as fresh as the last push someone remembered to make.",
                "/bowline:memory-backup setup <remote> installs it for this machine."))
        if remote:
            findings.extend(waiting_findings(folder, config))
        findings.extend(loss_findings(folder, config))
    return findings


def waiting_findings(folder, config):
    """Notes that have waited for the backup longer than the repository allows. The hook that backs them up prints
    nothing, whatever happens, so this is where a person learns that it stopped or that its push fails. The words hold
    no noun that changes with a number, so a backup that falls further behind is one reminder."""
    hours = config["limits"].get("memoryBackupHours")
    if not hours:
        return []
    notes, commits, since = memory.waiting(folder)
    if since is None or time.time() - since <= hours * 3600:
        return []
    return [common.Finding(
        "warning", f"The memory's backup is behind: the oldest change that waits for it is from {memory.stamp(since)}. "
                   f"Notes not committed: {notes}. Commits not pushed: {commits}.",
        config["limitsWhy"]["memoryBackupHours"],
        "Back the notes up now with: bowline memory push. When the push fails, it says what git said. When a change "
        "still waits after the next reply, the hook does not back this folder up: /bowline:memory-backup.")]


def loss_findings(folder, config):
    """Lines one session added to a note and another session removed soon after, read from the backup's history. The
    finding counts the lines and never quotes one: a note's words are shown only to a person who asks for them, which
    `bowline memory losses` does."""
    hours = (config.get("crew") or {}).get("memoryLossHours")
    findings = []
    for loss in memory.losses(folder, config):
        findings.append(common.Finding(
            "warning", f"The memory note {loss['note']} lost {common.count(len(loss['lines']), 'line', 'lines')} that another "
                       f"session had added less than {hours} hours before, in the backup's commit {loss['commit'][:12]}.",
            "Every worktree of a repository shares one memory folder, so a note written whole from an older copy erases "
            "what another session added in between; the backup's history still holds the lines.",
            "List them with: bowline memory losses. Put back what was lost with the Edit tool, or, for a removal that was "
            f"meant: bowline memory losses --meant {loss['commit'][:12]}. /bowline:crew says how sessions edit a file they share."))
    return findings


def note_findings(folder, config):
    """A note that keeps finished work like a log. The rule that keeps the index short moves the detail into the notes,
    and the index check never sees them, so a careful project's index stays small while one note grows round by round.
    A warning, not a note, because only problems and warnings reach a person at a session's start."""
    limit = config["limits"].get("memoryNoteCommits")
    if not limit or not os.path.isdir(folder):
        return []
    findings = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md") or name == "MEMORY.md":
            continue
        commits = common.commits_named(common.read_text(os.path.join(folder, name)))
        if len(commits) >= limit:
            findings.append(common.Finding(
                "warning", f"The memory note {name} names {len(commits)} commits: it keeps finished work like a log.",
                config["limitsWhy"]["memoryNoteCommits"],
                "Cut each finished item the repository records down to a pointer and its last commit, and keep what is "
                "still open: /bowline:curate-memory."))
    return findings


def hook_installed():
    path = os.path.join(common.config_dir(), "settings.json")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            settings = json.load(handle)
    except Exception:
        return False
    for event in ("Stop", "SessionEnd"):
        for group in (settings.get("hooks") or {}).get(event, []) or []:
            for hook in group.get("hooks", []) or []:
                text = str(hook.get("command", "")) + " " + " ".join(str(a) for a in hook.get("args", []) or [])
                if "push-memory" in text or "bowline" in text:
                    return True
    return False


def layout_findings(root):
    findings = []
    if not os.path.isfile(os.path.join(root, common.CONFIG_FILE)):
        findings.append(common.Finding(
            "note", f"The repository has no {common.CONFIG_FILE}; the defaults apply.",
            "The file holds the repository's own limits and gate policy, so every contributor measures against the same numbers.",
            "/bowline:init writes it with the defaults and their reasons.",
            many="{count} repositories have no " + common.CONFIG_FILE + "; the defaults apply."))
    gate_local = os.path.isfile(os.path.join(root, ".claude", "scripts", "gate.py")) or os.path.isfile(os.path.join(root, ".githooks", "pre-commit"))
    hooks_path = common.run_git(["-C", root, "config", "--get", "core.hooksPath"], check=False).strip()
    if not gate_local and not hooks_path:
        findings.append(common.Finding(
            "note", "No commit gate is installed for this repository.",
            "A gate reads the staged lines before every commit and refuses a token, a stray byte or a word that must never be committed; a pushed secret cannot be taken back.",
            "/bowline:init installs a repository-local copy and the pre-commit hook; the bowline plugin's hook runs it from Claude Code too.",
            many="{count} repositories have no commit gate installed."))
    return findings


# How many repositories of a folder are measured at once. The work is git calls and file reads, which wait on the disk
# rather than the processor, so a few at a time hide most of the waiting; more would only crowd a slow mount.
WORKERS = 8


def measure_one(root):
    """One repository of a folder: its configuration, findings and sizes, ready to be labelled."""
    config = common.load_config(root)
    findings, facts = repository_findings(root, config)
    return config, findings, facts


class Survey:
    """What the doctor finds from a path. `workspace` is the folder of repositories when the path is in one and not in a
    repository, else None; `roots` the repository roots; `parts` (name, root, facts, config) for the sizes, the name
    None for a single repository; `findings` every finding, each prefixed with its repository's name when there are
    several, or None when the path is in no repository and holds none. In a folder, the repositories are measured
    WORKERS at a time; on_part is called with each part in order as soon as it and every one before it are done, and
    on_progress with (done, total) as each completes. folder_only measures the folder itself and no repository."""

    def __init__(self, start, no_memory, folder_only=False, on_part=None, on_progress=None):
        self.workspace, self.roots = common.roots_for(start)
        self.parts, self.findings = [], None
        self.folder_only = folder_only
        if not self.roots:
            return
        if self.workspace is None:
            root = self.roots[0]
            config = common.load_config(root)
            findings, facts = repository_findings(root, config)
            if not no_memory:
                findings += memory_findings(root, config)
            self.findings = findings
            self.parts.append((None, root, facts, config))
            return
        self.findings = []
        shared = common.load_config(self.workspace)
        budget_findings, facts = budget.measure(self.workspace, shared)
        own = claude_md_findings(self.workspace, shared, facts) + workspace_findings(self.workspace, facts) + budget_findings
        if common.is_repository(self.workspace):
            # A folder that is its own git repository: its own files are committed, gated and split like a repository's.
            own += autosplit.findings(self.workspace, shared, facts) + layout_findings(self.workspace)
            autosplit.adjust(own, self.workspace, shared, facts)
        self.findings += label(own, os.path.basename(self.workspace))
        self.parts.append((os.path.basename(self.workspace), self.workspace, facts, shared))
        if on_part:
            on_part(self.parts[-1])
        if not folder_only and self.roots:
            done, lock, total = [0], threading.Lock(), len(self.roots)

            def measured(future):
                with lock:
                    done[0] += 1
                    if on_progress:
                        on_progress(done[0], total)

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(WORKERS, total)) as pool:
                futures = [pool.submit(measure_one, root) for root in self.roots]
                for future in futures:
                    future.add_done_callback(measured)
                for root, future in zip(self.roots, futures):
                    config, findings, facts = future.result()
                    self.findings += label(findings, os.path.basename(root))
                    self.parts.append((os.path.basename(root), root, facts, config))
                    if on_part:
                        on_part(self.parts[-1])
        if not no_memory:
            self.findings += memory_findings(self.workspace, shared)

    def urgent(self):
        return [f for f in self.findings or [] if f.level in ("problem", "warning")]


def repository_findings(root, config):
    """One repository's findings, in the doctor's order, and the sizes measured on the way. In a repository bowline
    leaves untouched, each finding is a note that says so and what the person can do instead, because a fix bowline may
    not make is not theirs to make either, and the line at a session's start should not repeat it every time."""
    budget_findings, facts = budget.measure(root, config)
    if not common.writes_allowed(root):
        findings = claude_md_findings(root, config, facts) + budget_findings + root_claude_md_findings(root, facts)
        for finding in findings:
            finding.level = "note"
            finding.fix = common.left_alone_fix(root)
            finding.fix_many = common.left_alone_fix(root, "<repository>")
        # A link inside a worktree stays a warning: taking it away writes nothing into the repository.
        return findings + crew.link_findings(root), facts
    findings = claude_md_findings(root, config, facts)
    findings += autosplit.findings(root, config, facts)
    findings += budget_findings
    findings += root_claude_md_findings(root, facts)
    findings += layout_findings(root)
    findings += crew.findings(root, config)
    findings += crew.link_findings(root)
    findings += crew_edit.findings(root, config)
    autosplit.adjust(findings, root, config, facts)
    return findings, facts


def workspace_findings(workspace, facts):
    """The folder's own CLAUDE.md, the file that loads whole at the start of a session started in the folder."""
    roots = [p for p, _, _ in facts["claudeMd"] if common.is_root_claude_md(p)]
    if not roots:
        return [common.Finding(
            "note", "The folder itself has no CLAUDE.md.",
            "A session started in the folder loads a CLAUDE.md there whole, at its start; it is the place to say in a few lines what the repositories are and how they relate.",
            "/bowline:init writes one from the folder: a table of the repositories, what applies to all of them, the Compact Instructions and the memory section; --each scaffolds every repository.")]
    return root_claude_md_findings(workspace, facts)


def label(findings, name):
    """Prefixes each finding with its repository's name, and names the repository in the commands a fix gives."""
    for finding in findings:
        finding.where, finding.bare = name, finding.what
        finding.what = f"{name}: {finding.what}"
        if finding.fix and "--file " in finding.fix:
            finding.fix_many = re.sub(r"(--file \S+)", lambda m: f"{m.group(1)} --repo <repository>", finding.fix)
            finding.fix = re.sub(r"(--file \S+)", lambda m: f"{m.group(1)} --repo {name}", finding.fix)
    return findings


def grouped(findings, verbose=False, folder=None):
    """A folder's findings for a reader: a finding found the same in several repositories, the same severity, words, why
    and fix, is one finding that names them, with its why and fix once; one found in a single place stays as it is.
    In the order each first appears. A finding about the folder itself (named folder) stands alone: the folder is not
    one of its repositories. With verbose, every finding one by one, as before grouping."""
    if verbose:
        return findings
    groups = {}
    for finding in findings:
        mine = finding.where and finding.where != folder
        key = (finding.level, finding.bare, finding.why, finding.fix_many or finding.fix) if mine else id(finding)
        groups.setdefault(key, []).append(finding)
    out = []
    for members in groups.values():
        if len(members) == 1:
            out.append(members[0])
            continue
        first = members[0]
        count = len(members)
        what = first.many.format(count=count) if first.many else f"In {count} repositories: {first.bare}"
        one = common.Finding(first.level, what, first.why, first.fix_many or first.fix)
        one.names = common.names([m.where for m in members]) + (" (--verbose lists each finding)" if count > 10 else "")
        out.append(one)
    return out


def finding_key(finding):
    """A finding's identity across replies: its words with every number blanked, so a file that keeps growing is one."""
    return re.sub(r"\d[\d,.]*", "#", finding.what)


def watch_file(workspace, roots):
    """Where the reminders' record lives: beside the autosplit records in the repository's git folder, or, for a folder
    of repositories, in Claude Code's project folder for it, the same place its memory lives."""
    if workspace:
        return os.path.join(common.project_folder(workspace), "bowline", "watch.json")
    return os.path.join(os.path.dirname(autosplit.state_dir(roots[0])), "watch.json")


def load_watch(path):
    data = autosplit.read_json(path)
    if data is None:
        return None
    return {"told": list(data.get("told") or []), "pending": list(data.get("pending") or []),
            "others": list(data.get("others") or [])}


def save_watch(path, watch):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(watch, handle, indent=2)
        handle.write("\n")
    common.replace_file(temp, path)


def hook_input():
    """What a hook's JSON on standard input says, or {} when there is none to read."""
    try:
        if sys.stdin is not None and not sys.stdin.isatty():
            facts = json.load(sys.stdin)
            return facts if isinstance(facts, dict) else {}
    except Exception:
        pass
    return {}


def hook_facts(wait=0.5):
    """What a hook's JSON on standard input says, or {} when there is none within a moment. Read from the descriptor in
    a thread of its own, so that a standard input nobody closes cannot hold a session's start."""
    box = []

    def read():
        try:
            data = b""
            while True:
                piece = os.read(0, 65536)
                if not piece:
                    break
                data += piece
            box.append(json.loads(data.decode("utf-8", "replace")))
        except Exception:  # noqa: BLE001 - no JSON, no facts
            pass

    try:
        if sys.stdin is None or sys.stdin.isatty():
            return {}
    except Exception:  # noqa: BLE001
        return {}
    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    thread.join(wait)
    return box[0] if box and isinstance(box[0], dict) else {}


# How many worktrees with a link a session's start names one by one; the report names every one.
LINKS_SHOWN = 3


WITHOUT_A_RULE = (
    " This repository has no rule about working beside other sessions, so these hold until it has one: two sessions "
    "never edit one file at once, so message a session before you edit a file it has changed; claim a number, a note or "
    "a file before you work on it; and run a heavy check through the turn, never beside another session's. The last "
    "section of /bowline:crew sets the repository up, its settings and the rule; offer that to the person.")


# In the line itself, because a session that does not know the rule has no reason to open the skill that holds it.
DECIDED_HERE = (
    "When the person decides something here about work another session holds, do not edit that work: send that session "
    "the person's words with SendMessage, as /bowline:collaborate says, and tell the person whether the message was "
    "delivered or only queued.")


BESIDE_OTHERS = (
    "Before you take a roadmap number or a note, edit a file the sessions share such as the memory, run a heavy check, "
    "rebase or push, follow /bowline:crew. When another session has your subject or your files, work with it as a team: "
    "/bowline:collaborate. " + DECIDED_HERE)


def others_line(root, places=None):
    """The line every session's start gets in a repository, with the places where another session worked lately, or
    None. The places are the worktrees with a sign of work in the last crew.activeMinutes minutes, each named on its
    own with the sessions seen there, and this session's own folder said as such; this session's own transcript is the
    one the hook names. Several sessions in one repository is taken as the usual case (crew.assumeOthers), so a session
    that sees nobody still gets the line: another may start a minute later, and a session's start is the one moment
    every session reads. A repository without a rule about working beside other sessions gets the rule's main points
    with it, and where the repository is set up. Returns the line and the names of the places."""
    config = common.load_config(root)
    settings = config.get("crew") or {}
    minutes = settings.get("activeMinutes")
    if places is None:
        places = crew.others_active(root, config, transcript=lambda: hook_facts().get("transcript_path"))
    names = [place["name"] for place in places]
    if not minutes or not (places or settings.get("assumeOthers")):
        return None, names
    if places:
        count, where = crew.places_words(places)
        seen = (f"{common.count(count, 'other Claude Code session has', 'other Claude Code sessions have')} worked in this "
                f"repository in the last {minutes} minutes: {where}.")
    else:
        seen = ("no other Claude Code session shows a sign of work in this repository right now. Work as if one may start "
                "at any moment, because several sessions in one repository is the usual case; bowline tells you before a "
                "prompt when one appears.")
    return f"bowline: {seen} {BESIDE_OTHERS}" + ("" if crew_edit.has_rule(root, config) else WITHOUT_A_RULE), names


def arrived_line(root, watch, transcript):
    """Before a prompt: the line for a session that is already running when another one appears, or None. A session's
    start names who is there at that moment; this names each place once when a sign of work shows there afterwards, and
    again when it comes back after going quiet. Changes the record's list of the places named."""
    places = crew.others_active(root, common.load_config(root), transcript=transcript)
    names = [place["name"] for place in places]
    new = [place for place in places if place["name"] not in watch["others"]]
    changed = sorted(names) != sorted(watch["others"])
    watch["others"] = names
    if not new:
        return None, changed
    count, where = crew.places_words(new)
    return (f"bowline: {common.count(count, 'other Claude Code session has', 'other Claude Code sessions have')} started "
            f"to work in this repository since you were last told: {where}. Look who holds what with "
            "/bowline:crew before your next edit, and before you take a number, run a heavy check, rebase or push; when it "
            f"has your subject or your files, work with it as a team: /bowline:collaborate. {DECIDED_HERE}"), True


def do_watch(options):
    """The Stop hook (--watch) and the UserPromptSubmit hook (--pending). Prints nothing when there is nothing new.
    After a reply that ends with a question to the person, the crew records that the session waits for them; before
    the person's next prompt in that session it takes that back."""
    facts = hook_input()
    try:
        crew.clear_asks(facts) if options.pending else crew.note_reply(facts)
    except Exception:  # noqa: BLE001 - the crew's record is a convenience; the reminders go on without it
        pass
    start = facts.get("cwd") or options.repo or os.getcwd()
    workspace, roots = common.roots_for(start)
    if not roots:
        return 0
    path = watch_file(workspace, roots)
    watch = load_watch(path)
    if options.pending:
        if watch and watch["pending"]:
            print("bowline found this during the session, after the last reply; tell the person in a sentence and name the skill that fixes it:")
            for line in watch["pending"]:
                print(f"- {line}")
            watch["pending"] = []
            save_watch(path, watch)
        if watch is not None and not workspace:
            line, changed = arrived_line(roots[0], watch, facts.get("transcript_path"))
            if line:
                print(line)
            if changed:
                save_watch(path, watch)
        return 0
    urgent = Survey(start, options.no_memory).urgent()
    keys = [finding_key(f) for f in urgent]
    if watch is None:
        # No record yet: the session's start said whatever was there, so nothing counts as new this time.
        save_watch(path, {"told": keys, "pending": [], "others": []})
        return 0
    told = set(watch["told"])
    new = [f for f, key in zip(urgent, keys) if key not in told]
    watch["told"] = keys
    if new:
        lines = [f"{f.what} Fix: {f.fix or 'run /bowline:doctor'}" for f in new]
        watch["pending"] = (watch["pending"] + lines)[-10:]
        print(json.dumps({"systemMessage": "bowline: " + "\n".join(lines)}))
    save_watch(path, watch)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measures a repository and this machine against what Claude Code reads.")
    parser.add_argument("--repo", help="a path inside the repository, or a folder of repositories (default: the current folder)")
    parser.add_argument("--no-memory", action="store_true", help="skip the memory folder checks (for CI)")
    parser.add_argument("--brief", action="store_true",
                        help="one line per problem or warning and nothing when clean; always exit 0 (for a SessionStart hook)")
    parser.add_argument("--watch", action="store_true", help="after a reply: one reminder when something new crosses a limit (the Stop hook)")
    parser.add_argument("--pending", action="store_true", help="before a prompt: the pending reminder for Claude, once (the UserPromptSubmit hook)")
    parser.add_argument("--verbose", action="store_true",
                        help="in a folder of repositories: every finding one by one, every repository's sizes, every name")
    parser.add_argument("--folder-only", action="store_true",
                        help="in a folder of repositories: measure the folder itself and its memory, no repository, for a quick check")
    options = parser.parse_args(argv)
    if options.watch or options.pending:
        try:
            return do_watch(options)
        except BaseException:  # noqa: BLE001 - a hook must never fail a reply or a prompt
            return 0
    if options.brief:
        try:
            survey = Survey(options.repo, options.no_memory)
            if survey.findings is None:
                return 0
            urgent = survey.urgent()
        except Exception:
            return 0
        try:
            line, names = others_line(survey.roots[0]) if not survey.workspace else (None, [])
        except Exception:  # noqa: BLE001 - a hook must never fail a session's start
            line, names = None, []
        try:
            save_watch(watch_file(survey.workspace, survey.roots),
                       {"told": [finding_key(f) for f in urgent], "pending": [], "others": names})
        except Exception:
            return 0
        # A link inside a worktree comes first and whole, why included, on a line of its own: a removal that follows it
        # deletes files, and it is not about the instructions or the memory, so it must never wait behind three of those.
        links = [f for f in urgent if f.topic == "links"]
        rest = [f for f in urgent if f.topic != "links"]
        for finding in links[:LINKS_SHOWN]:
            print(f"bowline: {finding.what} {finding.why} Fix: {finding.fix}")
        if len(links) > LINKS_SHOWN:
            print(f"bowline: {common.count(len(links) - LINKS_SHOWN, 'more worktree holds', 'more worktrees hold')} such "
                  "a link; /bowline:doctor lists each.")
        if rest:
            whose = "the instructions or the memory of this folder's repositories" if survey.workspace else "this repository's instructions or memory"
            print(f"bowline found {len(rest)} thing(s) worth a look about {whose}; run /bowline:doctor for the report. The first:")
            for finding in rest[:3]:
                print(f"- {finding.what} Fix: {finding.fix or 'see the doctor'}")
        if line:
            print(line)
        return 0

    workspace, roots = common.roots_for(options.repo)
    if not roots:
        print("bowline doctor: not inside a git repository, and this folder holds none.", file=sys.stderr)
        return 2
    if workspace:
        whole = common.count(len(roots), "repository", "repositories")
        print(f"bowline doctor: {workspace}, a folder of {whole}: {common.names([os.path.basename(r) for r in roots], options.verbose)}")
        with_config = [os.path.basename(r) for r in [workspace] + roots if os.path.isfile(os.path.join(r, common.CONFIG_FILE))]
        suffix = f", with {common.CONFIG_FILE} in {common.names(with_config, options.verbose)}" if with_config else ""
        config = common.load_config(workspace)
    else:
        print(f"bowline doctor: {roots[0]}")
        suffix = f", with {common.CONFIG_FILE}" if os.path.isfile(os.path.join(roots[0], common.CONFIG_FILE)) else ""
        parent = os.path.dirname(roots[0])
        if os.path.isfile(os.path.join(parent, common.CONFIG_FILE)) and common.repo_root(parent) is None:
            suffix += f", over the folder's shared {os.path.join(parent, common.CONFIG_FILE)}"
        config = common.load_config(roots[0])
        if options.folder_only:
            print("bowline doctor: --folder-only is for a folder of repositories; this is one repository, measured whole.",
                  file=sys.stderr)
    print(f"limits from defaults.json (facts checked against the Claude Code docs on {config.get('checkedAgainstDocs')})" + suffix)
    print()
    sys.stdout.flush()

    def sizes(part):
        """A part's sizes, printed as soon as it is measured: each CLAUDE.md, and the rules and skills unless all zero."""
        name, root, facts, _ = part
        head = f"{name}: " if name else ""
        for path, lines, chars in facts["claudeMd"]:
            print(f"  {head}{path}: {lines} lines, {chars:,} characters")
        if facts["areas"] or facts["unscoped"] or facts["skills"] or options.verbose or not workspace:
            areas = ", ".join(f"{area} {chars:,}" for area, chars in sorted(facts["areas"].items())) or "none"
            print(f"  {head}scoped rules per area: {areas}; unscoped: {facts['unscoped']:,}; skills: {len(facts['skills'])}")
        sys.stdout.flush()

    measuring = workspace and not options.folder_only
    if measuring:
        print(f"bowline doctor: measuring {common.count(len(roots), 'repository', 'repositories')}, up to {WORKERS} at a time.",
              file=sys.stderr, flush=True)
    step = max(1, len(roots) // 10)

    def progress(done, total):
        if done % step == 0 or done == total:
            print(f"bowline doctor: {done} of {total} measured.", file=sys.stderr, flush=True)

    survey = Survey(options.repo, options.no_memory, folder_only=options.folder_only, on_part=sizes,
                    on_progress=progress if measuring else None)
    if not survey.workspace:
        for part in survey.parts:
            sizes(part)
    print()
    shown = grouped(survey.findings, options.verbose, os.path.basename(survey.workspace)) if survey.workspace else survey.findings
    problems = common.print_findings(shown, "bowline doctor", counted=survey.findings)
    if survey.workspace and options.folder_only:
        print(f"The folder's {common.count(len(roots), 'repository', 'repositories')} were not measured (--folder-only); "
              "run the doctor without it to measure them.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
