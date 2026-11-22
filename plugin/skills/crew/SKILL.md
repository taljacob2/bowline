---
name: crew
description: Work beside other Claude Code sessions in one repository without colliding - see who is here and what waits for the person (each worktree's sessions by name, heavy processes and ports), claim a roadmap number, a note or a file before working on it, edit the files the sessions share (the memory above all) and never save one over whole, wait for a quiet machine before a heavy check, take a place in the push queue before full checks, re-read numbers and stamps after a rebase, and list the worktrees that are safe to remove. Use when a session's start says other sessions are at work, before taking a number or a note, before a test suite or a build another session may also be running, after a rebase, after a push someone waits on, or when the person asks who else is working here, what waits for them, or which worktrees can go.
---

# The crew

Several sessions in one repository, each in its own worktree, share more than they see: one machine's processor, one
memory folder, one roadmap whose numbers each of them extends, and the ports the person's own servers listen on.
bowline lists and records what a script can; you say the rest to the other sessions with `SendMessage`. bowline never
stops a process and never sends a message.

The command, in every step below, is `node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew`.

## 1. See who is here

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew
```

It puts what matters first, each worktree once: **WAITS FOR YOU** (a session asks the person a question or is
blocked, or its sessions are idle while it holds files not committed or commits not on the pushed branch; untracked
files that nobody has written for a day, such as a tool's old cache, do not count, and are listed under IDLE with
the date of the newest), **AT
WORK** (a session is busy, a heavy check runs, or a command a session started still runs after its turn ended),
**IDLE** (a line each), and **QUIET** (one line, saying whether any of them holds work). Each worktree shows its
sessions by name, what it holds, its heavy and listening processes, its claims and what its session said; then come
the files changed differently in more than one worktree, grouped by the worktrees that share them, the person's ports
and the turn. The sessions come from `claude agents --json`; when the look says that list could not be asked, call
`ListAgents` for who is busy. Look before the first change of a session that was told at its start that others are
at work, and again before a push. `SendMessage` reaches a session by the name `ListAgents` gives it. `crew --json`
gives the same as data.

- **When you wait for the person's answer**, say so: `crew say --asks "<the question>"`. Claude Code lists a session
  that ended its reply with a question as plain idle, the same as one that is done. The hook after a reply sets it
  for you when your reply ends with a question, and the person's next prompt takes it back.
- **A worktree to watch.** The person can keep the look open in a terminal beside the app, drawn again every ten
  seconds until Ctrl+C: give them the command with this skill's path written out,
  `node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew watch`, run from inside the repository. It does not belong in
  your own shell, where it never ends. In Claude Desktop, where a `!` command does not run, the person asks you for
  `/bowline:crew` instead.

- **Two sessions in one worktree** are both listed, with a warning when both are busy: they may change the same
  files. Ask the person which of them keeps the worktree.
- **Each session's memory** is beside its name: its own process and every process it started.
- **A session's own command.** Claude Code calls a session idle as soon as its turn ends, even while a command it
  started in the background still runs, such as a long push. The look finds each such command below the session's
  process, names it under the session ("runs in the background: ..."), and puts the worktree under AT WORK.
- **An offline session** is a session with no process that can still be taken up again: a background session that
  Claude Code still lists with the state it last recorded, often "blocked", or a Claude Desktop session in the
  person's sidebar, not archived, whose process has ended (`claude agents` does not list it; the app's record of its
  sessions does). The look names it beside its worktree, and never counts it as waiting for the person or as at
  work. It holds no memory; the person can open it to take it up again. Its worktree is not safe to remove, because
  the session reopened after a removal would find its folder gone: the person archives it first.
- **A session whose worktree is gone** is one in the sidebar, not archived, whose worktree was removed or is being
  removed. The look lists it under ACROSS THE WORKTREES; tell the person to archive it.
- **A worktree that is broken or being removed** has lost the `.git` file in its folder, so git there answers for the
  main checkout. It is named and left out of the counts and of the files changed twice; never work in it.

- **A sign of work** is the newest of a session's transcript, the worktree's own git folder being written, and a
  claim. A session that was started in another folder and works here by path leaves no transcript here, so the last
  two are how it is seen; take a claim early when you work that way yourself. A write of HEAD that moves it to no
  other commit is not work: Claude Desktop detaches the HEAD of a session's worktree, at the same commit, when it
  archives the session. Nor is the transcript of an archived session. The look names the archived session of a
  worktree that no other session holds.
- **A file changed differently in more than one worktree** is one a rebase will meet twice. Tell the other session
  which lines you change, or wait for its push. A worktree marked quiet has shown no sign of work for a day or more,
  and its changes may be abandoned; ask the person before counting on that.
- **A shared record** (`crew.shared`: a roadmap, a design document, a changelog) is listed apart, because every
  session adds to it by rule.
- **A worktree this system cannot enter**, such as one made from another system's view of the same disk, is named
  and left out; a session may still be at work in it.

Before you pass the look on to the person, read it as a measurement, not as the answer:

- **Link every session you name.** In Claude Desktop, a reply links a session as `[its title](#<its id>)`, where the
  id is the app's own and starts with `local_`. Run inside a session, the look ends with SESSION LINKS: each listed
  session's id and title, read from the app's record of its sessions. `crew --json` gives the same id as each
  session's `desktop`. The short refs that `ListAgents` gives are not links. For a session the look does not list,
  such as one in another repository, `mcp__ccd_session_mgmt__list_sessions` gives its id, with
  `include_archived: true` for an archived one.

- **Check a session itself before you say "idle, with work ..."**: read its transcript, or ask it with `SendMessage`,
  for a background command or a push still on its way. The look sees only the processes on this machine, and a
  command whose process has lost its parent can escape it.
- **Put the work that is moving first**: a busy session, a background command or a heavy check comes before what is
  idle or quiet, and the session that does the most is never the one you mention least.
- **List a side session under the session it belongs to.** A fork, a "btw" question or a session started from
  another works in that session's folder and often holds nothing of its own. Name it under the session it came from,
  not as one more session working on its own.
- **When the person needs memory back**, go through every idle session that holds nothing of its own, one by one,
  including one in a worktree whose other session holds work. The IDLE, HOLDING NOTHING group is decided per
  worktree, so a side session idle beside work is not in it, and closing it gives its memory back too. Say which
  sessions and how much each holds, and never close one yourself.

Never stop a process you did not start. The ports the repository names as the person's own (`crew.keepPorts`) are
listed with what listens on them and are never to be stopped; a server of your own takes a port nothing listens on.

## 2. Claim before you work

Take the thing before you touch it, so that the second session to want it is told at once:

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew claim roadmap --new --why "the log viewer"
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew claim roadmap:118 --why "working the existing item"
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew claim note:17 --why "the note about the slow start"
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew claim file:src/parser.py --why "lines 120 to 180"
```

- **A new number** of a numbered list the repository names (`crew.numbers` in `.claude/bowline.json`) comes from
  `claim <list> --new`, never from reading the file and adding one. It is one past the highest number in the pushed
  branch, in every worktree's copy of the file, committed or not, and in every claim, so it is free even when another
  session wrote its item an hour ago and has not pushed.
- **A claim another worktree holds is refused**, with that worktree's name. Take another thing, or ask that session.
- **Split the work by files.** Two sessions never edit the same file at the same time. When your round needs a file
  another session has changed, message that session before you edit it, agree who changes what, and name the
  agreement in your commit message; when you cannot reach it, wait for its push and rebase onto it. The files the
  repository names as shared records are the one exception: every session adds its own entry to them.
- **Say it as well as write it.** After each claim, tell the sessions it concerns with `SendMessage`: what you took,
  the files and the lines you will change, and what you will not touch. The claims file is where they look; the
  message is how they hear.
- **Wait on a push in the open.** When you need another worktree's work first:
  `crew claim waits:<its folder's or its branch's name> --why "<what you wait for>"`. That session is told after its
  push.
- **Give it back.** `crew release <key>` when the work is pushed or dropped, `crew release --all` at the end. A number
  that has reached the pushed branch, and every claim of a worktree that was removed, are dropped on their own.

## When bowline warns before an edit

Before an edit with the Edit, Write or NotebookEdit tool, bowline tells you when the file is held by another worktree:
changed there and not committed, committed there and not pushed, or claimed there with `file:<path>`. The message
begins "bowline crew:", names the worktree, its branch and the last sign of work there, and arrives beside the edit's
result. It says so once per session and file and never blocks the edit. Then message that session, agree who changes
what, and name the agreement in your commit message; when the work there is old and no session holds it, say so to
the person and go on. To ask the same question by hand:

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew before-edit --file <path>
```

A file every session adds to belongs in `crew.shared`, and is then never warned about; the files of `crew.numbers`
and `crew.stamps` are skipped on their own. The warning does not see a file changed through a shell command.

## 3. Edit a shared file; never save it over whole

Every worktree of a repository reads and writes the same memory folder, and several sessions add to the same notes
there, such as a notes queue. Outside the repository there are no branches and no merge: the last writer wins.

- **Change a shared file with the Edit tool, one addition or removal at a time.** Edit puts your change into the file
  as it is now, so what another session added since you read it stays.
- **Never write a shared file whole from a shell or a script**: no redirect, no `Set-Content`, no one-off program
  that writes the text it holds. Those do not notice that the file changed.
- **When Write answers "File has been modified since read"**, another session changed the file. Read it again and put
  your change into what is there now. Never read it only to make the tool accept the text you already had.
- **The same holds for the roadmap, the notes queue and any index** in the repository: add your entry with Edit, in
  its place, and let the rebase join it with the others'.

The doctor watches the memory's backup for this: it warns when one session's commit removed lines that another
session had added within the last day. `node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" memory losses` lists the lines
and the commit; put back what was lost with Edit. A line of a note's front matter that a save gave a new value, such
as the `modified:` time Claude Code writes on every save, is not counted as lost. For a removal that was meant, such as a worked note another session
took off the queue, `memory losses --meant <commit>` records it so that it is not reported again. Show the lines to
the person before deciding which it was.

## 4. Wait for a quiet machine before a heavy check

A test suite beside another session's test suite crashes or times out, and the failure looks like a real one. Run
every heavy check through the turn:

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew run -- <the command and its arguments>
```

It waits for a slot of the turn, takes it, runs the command with its output and its exit code passed through, and
gives the slot back. `crew.slots` full checks run at a time, one unless the repository says more; a process that
matches the repository's heavy patterns (`crew.heavy`) and that no `crew run` started takes a slot too. Start it in
the background, because the wait can be longer than a command may take in the foreground. Exit code 3 means no slot
came free within the time allowed (30 minutes unless `--timeout <minutes>` or `crew.waitMinutes` says otherwise) and
the command did not run; the message names what was still running. Then ask that session, or wait; never stop its
process.

- **A check of one file or a few takes the small turn**: `crew run --small -- <command>`. It runs beside the full
  checks, one small check at a time, so that a test of one file does not wait twenty minutes behind a full suite. Use
  it only for a check that is small; the look shows what each check took.
- **Memory decides how many run at once.** `crew run` measures the memory its command and every process below it
  take, and says the most when the command ends; a check that would start beside another waits until its own peak,
  from its last runs, is free. The look shows the largest peaks and the memory in use. When the person asks whether
  two full checks can run at once, read the two numbers to them: two fit when twice the largest peak is less than what
  is free while no check runs. `crew.slots` is theirs to set.

The order of a repository's own checks, and which of them may run together, stay the repository's rules. The turn
adds one thing to them: as many heavy commands at a time as the repository's slots allow, across every session.

**Take a place in the push queue before your full checks.** When two worktrees change one file, the second should
rebase onto the first's push before its full checks, not after: checks that ran on code about to change must run
again, and a full check takes many minutes.

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew queue join --why "<what you will push>"
```

It says which worktrees ahead of you change a file you change. Wait for that push, rebase onto it, and then run the
checks; `crew run` says the same when you start a heavy check behind such a worktree, and runs it all the same. After
your push the hook gives your place up and names who comes next with your files: send it the hash with `SendMessage`
so that it rebases now. `crew queue` lists the queue; `crew queue leave` gives the place up when the work is dropped.

## 5. After a rebase, read again what the others also write

A rebase can succeed and still leave two items with the same number, or a build's stamp that names a commit which no
longer exists. bowline's hook checks after every `git rebase` and `git pull` you issue and speaks only when
something is wrong; by hand:

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew after-rebase
```

- **A number that appears twice**: give your item the next free number with `crew claim <list> --new`, and correct
  every place that names the old one: the commit messages you have not pushed, the notes, the messages you sent.
- **A claimed number that reached the pushed branch**: if that item is not yours, another session took the number
  without a claim; take a new one the same way.
- **A stale stamp**: remake it with the command the repository names (`crew.stamps`), before anything reads it.

Then run the checks again when the rebase changed what you are about to push.

## 6. After a commit or a push, tell whoever waits

bowline's hook says, after a `git commit` or a `git push` you issue, which sessions wait on this worktree and for
what, with the commit's hash. A session on a branch of its own commits long before it pushes, and the session that
waits may need only the commit. Send each of them the hash with `SendMessage`, in one sentence that says what the
commit holds. After a push, release the claims it finished.

Sending a hash is the least two sessions can do for each other. `/bowline:collaborate` is the procedure for the
rest: saying your subject before you design, asking another session to try your work, and keeping a status of your
own with `crew say` that the others read whenever they look.

## 7. Give work a session of its own

Keeping apart is half of working side by side; the other half is moving work into a session of its own wherever the
work allows it, so that a round stays one subject and ends in one commit.

- **A task of its own gets a session of its own.** A deliberate scope cut, or a problem found in passing, gets its
  numbered slot in the roadmap and does not widen the round you are in. Where the client can start sessions, propose
  one whose brief names its files and what done looks like; where it cannot, as in the terminal, the slot and one
  line in your reply stand in for it.
- **Prefer parallel sessions where the pieces allow it.** When a plan has two or more pieces that touch different
  files and need nothing from each other, propose each as its own session instead of doing them one after another.
- **A new subject moves the current round first.** When the person asks about something else in the middle of a
  round, hand the round to a session of its own with the plan that is left, and then answer. In a worktree, commit
  first: the new session starts from your branch, and your uncommitted edits stay behind.
- **Reading and checking stay with you.** A search, a review or a test run goes to a subagent, whose answer comes
  back in the same turn. A session is for work that ends in a commit of its own.

## Remove the worktrees nobody needs

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew prune
```

It names the worktrees that are safe to remove (every file committed, every commit on the pushed branch by content,
no session, process, claim, lock or place in the queue, and no sign of work for `crew.pruneHours`) and why each
other one is not. A session offline in Claude Desktop's sidebar counts as a session until the person archives it,
because reopened after a removal it would find its folder gone; prune names it and says to archive it first. Show the
list to the person, with each session it names linked. Only on their yes, run `crew prune --remove <name>...`: each is checked
again and removed with `git worktree remove`, never with `--force`, and its branch stays. Start it in the background,
because a worktree with its own `node_modules` takes minutes to delete on Windows, and a command stopped at a time
limit leaves git's deletion half done. Never remove a worktree the list calls not safe, and never one by hand.

## Setting a repository up for it

The first time in a repository, ask the person and write the answers into `.claude/bowline.json` under `crew`; the
keys and their reasons are in `${CLAUDE_PLUGIN_ROOT}/defaults.json`:

- `heavy`: the processes that must not run beside one another, as regular expressions over a command line. Ask which
  checks are heavy and how each one's program appears in a process list; `crew --verbose` shows the command lines of
  what runs now. Leave out any server the person keeps running, which would never go quiet.
- `keepPorts`: the ports of the person's own servers.
- `numbers`: each numbered list the sessions extend, with its file and the pattern of an item's number.
- `shared`: the files every session adds to by rule, as paths or patterns.
- `stamps`: each file a build writes with a commit, and the command that remakes it.
- `warnBeforeEdit`: leave it on, unless the repository's worktrees are not sessions; `false` turns the warning before
  an edit off.
- `changedCacheSeconds`: how old the record of what each worktree changed may be before the warning has it measured
  again in the background; 60 unless the person asks for another value.
- `slots`: how many full checks run at once; 1 until the look's largest peaks show that two fit in the memory free
  while no check runs.

Then offer the rule in `${CLAUDE_PLUGIN_ROOT}/templates/crew/beside-other-sessions.md`: show it, adapt its words to
the repository, and with the person's yes write it to `.claude/rules/beside-other-sessions.md`. It holds both halves,
keeping apart and giving work a session of its own, because a repository should have one rule about this and not
two. It has no `paths:`, so every session reads it at its start, and it takes about 4,000 of the 10,000 characters the
unscoped rules may use; drop the rules the repository does not need. Keep its sentence that says `bowline crew` is
the plugin's script: a session that types the name as a command finds no such program. A repository that already has
such a rule keeps its own: fill its names into the template's words, or leave it. Offer the settings and the rule in
every repository: several sessions in one repository is taken as the usual case, and the person may decline.

## What not to do

- Do not stop, restart or "clean up" a process, a server or a worktree that another session or the person started;
  a worktree goes only through `crew prune --remove`, on the person's yes.
- Do not take a number by reading the list, and do not reuse a number that was given back.
- Do not treat silence as agreement: a message is delivered when the other session next looks, and a session in
  another permission mode may hold it for its person.
- Do not release or overwrite another worktree's claim; ask that session, or the person.
