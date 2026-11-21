---
name: crew
description: Work beside other Claude Code sessions in one repository without colliding - see who is here (each worktree's session, heavy processes and ports), claim a roadmap number, a note or a file before working on it, edit the files the sessions share (the memory above all) and never save one over whole, wait for a quiet machine before a heavy check, and re-read numbers and stamps after a rebase. Use when a session's start says other sessions are at work, before taking a number or a note, before a test suite or a build another session may also be running, after a rebase, after a push someone waits on, or when the person asks who else is working here.
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

It lists every worktree of the repository: its branch, how far it is from the branch every session pushes to, its
files not yet committed, the last sign of work there, its processes that count as heavy or listen on a port, the
claims it holds, the files changed differently in more than one worktree, and who holds the turn for a heavy check.
Then call `ListAgents`: it names the sessions and says which are busy, which the script cannot know. Do both before
the first change of a session that was told at its start that others are at work, and again before a push.

- **A sign of work** is the newest of a session's transcript, the worktree's own git folder being written, and a
  claim. A session that was started in another folder and works here by path leaves no transcript here, so the last
  two are how it is seen; take a claim early when you work that way yourself.
- **A file changed differently in more than one worktree** is one a rebase will meet twice. Tell the other session
  which lines you change, or wait for its push. A worktree marked quiet has shown no sign of work for a day or more,
  and its changes may be abandoned; ask the person before counting on that.
- **A shared record** (`crew.shared`: a roadmap, a design document, a changelog) is listed apart, because every
  session adds to it by rule.
- **A worktree this system cannot enter**, such as one made from another system's view of the same disk, is named
  and left out; a session may still be at work in it.

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
- **Say it as well as write it.** After each claim, tell the sessions it concerns with `SendMessage`: what you took,
  the files and the lines you will change, and what you will not touch. The claims file is where they look; the
  message is how they hear.
- **Wait on a push in the open.** When you need another worktree's work first:
  `crew claim waits:<its folder's or its branch's name> --why "<what you wait for>"`. That session is told after its
  push.
- **Give it back.** `crew release <key>` when the work is pushed or dropped, `crew release --all` at the end. A number
  that has reached the pushed branch, and every claim of a worktree that was removed, are dropped on their own.

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
and the commit; put back what was lost with Edit. For a removal that was meant, such as a worked note another session
took off the queue, `memory losses --meant <commit>` records it so that it is not reported again. Show the lines to
the person before deciding which it was.

## 4. Wait for a quiet machine before a heavy check

A test suite beside another session's test suite crashes or times out, and the failure looks like a real one. Run
every heavy check through the turn:

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" crew run -- <the command and its arguments>
```

It waits until no process on the machine matches the repository's heavy patterns (`crew.heavy`) and no other
`crew run` holds the turn, takes the turn, runs the command with its output and its exit code passed through, and
gives the turn back. Start it in the background, because the wait can be longer than a command may take in the
foreground. Exit code 3 means the machine did not go quiet within the time allowed (30 minutes unless
`--timeout <minutes>` or `crew.waitMinutes` says otherwise) and the command did not run; the message names what was
still running. Then ask that session, or wait; never stop its process.

The order of a repository's own checks, and which of them may run together, stay the repository's rules. The turn
adds one thing to them: one heavy command at a time, across every session.

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

Then offer the rule in `${CLAUDE_PLUGIN_ROOT}/templates/crew/beside-other-sessions.md`: show it, adapt its words to
the repository, and with the person's yes write it to `.claude/rules/beside-other-sessions.md`. It has no `paths:`,
so every session reads it at its start; it is short for that reason. A repository where one session works at a time
needs neither the settings nor the rule.

## What not to do

- Do not stop, restart or "clean up" a process, a server or a worktree that another session or the person started.
- Do not take a number by reading the list, and do not reuse a number that was given back.
- Do not treat silence as agreement: a message is delivered when the other session next looks, and a session in
  another permission mode may hold it for its person.
- Do not release or overwrite another worktree's claim; ask that session, or the person.
