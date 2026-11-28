# Changelog

Every version names the date its facts were last checked against the Claude Code documentation, because the limits
bowline measures against are Claude Code's, not bowline's. When a limit moves, `plugin/defaults.json` and
`plugin/docs/facts.md` change together and the entry here says which.

## 0.19.0 (2026-11-28)

A session looks up what was already decided before a design question goes to the person. New: the command
`bowline decisions` (`find`, `records`, `section`), the skill `/bowline:decide`, a section of settings, `decisions`,
and two findings of the doctor. No Claude Code limit moved, and no hook is new.

- **A decision is looked up before a question goes to the person.** A new command, `bowline decisions find <words>`,
  lists where a subject appears: the records of decisions first, then the other documents, the tests, the code and
  the commit messages, with the commit that last wrote each line of a test or of the code, the record a comment's
  date points to, and a mark on an entry that approves by reference, such as "all three as recommended".
  `decisions records` prints the files taken as records, and a new section of settings, `decisions`, names them. A
  new skill, `/bowline:decide`, is the procedure before a design question goes to the person. The starter rule
  `recording-decisions.md` loses "a line in a document is a claim, not a fact" and gains a section, "Before a question
  goes to the person"; the template of a decisions section asks for the decision's own sentence and the person's own
  words; and the Compact Instructions and the memory section say what an open question keeps. A repository that
  already has these files keeps its own, and takes the new section as the next entry says.
- **A repository that already has its rule file takes the section.** The doctor notes a repository whose
  instructions have no section about looking a decision up. Until it has one, the line at a session's start says
  in one sentence what to do before a question and names `/bowline:decide`; a new setting, `decisions.atStart`,
  turns the sentence off. Tried on live sessions: with the sentence first and the action first in it, 5 of 5
  sessions used the skill; said last and as a description, 2 of 5. `bowline decisions section` prints where the section goes, how many characters it adds
  to the rules every session loads, the earlier bullet it replaces and the text, and changes no file. The
  `conventions` skill has a sixth convention that makes the edit with the person, in the rule file that exists.
- **The doctor warns of an entry that approves by reference.** An entry of the records of decisions that says
  "all three as recommended" keeps the approval and loses what was decided. The doctor names each such line, at
  a session's start and in its report, and when one is written during a session it tells the person once, after
  the reply. A phrase inside quotation marks is not counted, by the doctor or by `decisions find`, and an empty
  `decisions.byReference` turns the mark and the warning off.
- **What was measured.** A replay of the round this answers, on a made-up repository, with Claude Code's own
  `claude plugin eval`: 61 sessions on 2026-11-28. Claude Code alone edited nothing and asked in 6 of 13 runs
  when a record and the program disagreed, and went back to the records in 0 of 6 when asked again after a
  summary. With the rule's two bullets in front of it: 5 of 5 and 5 of 5. With the plugin and no rule: 12 of 13
  and 6 of 6. With both: 5 of 5 and 5 of 5. The sessions were fresh and short, and five runs is a small number;
  `docs/decisions.md` has the limits, and the replay itself is in the repository's `evals/`, which does not ship.

## 0.18.0 (2026-11-28)

Autosplit is offered with its cost, where a person meets it. One option is new, `init --autosplit`. No Claude Code
limit moved, and no hook or setting is new.

- **The doctor offers autosplit while it is off.** A finding about a `CLAUDE.md` that autosplit would split ends
  its fix with how to turn autosplit on, what it does, and what one split may spend (`autosplit.maxBudgetUsd`, $20
  by default). The fix is in the line at a session's start too, so a person who never runs the doctor hears of it.
- **`init` says whether autosplit is on and what it costs.** Wherever it plans the config item, an `autosplit` line
  gives the state and a sentence after the plan says what autosplit does and spends. `--autosplit` turns it on in
  the `.claude/bowline.json` that init creates; where the file exists, init still never edits it and names the key
  to set. The init skill asks once, naming the cost.
- **A repository's new `.claude/bowline.json` keeps the folder's autosplit.** It took the template's `false`, which
  turned autosplit off in each repository that `init --each` set up under a folder that had turned it on.

## 0.17.1 (2026-11-24)

A rule for a decision that reaches the wrong session. No Claude Code limit moved, and no command, hook or setting is
new.

- **A decision goes to the session that holds the work.** The `collaborate` skill now says what a session does when the
  person decides, in it, something about work another session holds: it does not edit that work, it sends that session
  the person's own words with what is still open, it tells the person whether the message was delivered or only
  queued, and it sends a later answer as a correction. This holds above all for a fork that shares its parent's
  worktree. The line at every session's start says the rule itself, as does the line before a prompt when another
  session appears, and the skill's description names it. The `crew` skill and the rule template point to it, and the skill gives the template's size as it is now.

## 0.17.0 (2026-11-24)

The doctor watches whether the memory's backup arrives, not only whether it is set up. One setting is new,
`limits.memoryBackupHours`. No Claude Code limit moved, and no command or hook is new.

- **The doctor says when the memory's backup is behind.** It checked that a backup exists and that a hook is installed,
  never that the notes arrive. The hook prints nothing, so a backup that stopped showed nowhere: the fault that 0.16.3
  put right hid for more than a day. The doctor now warns when a note not committed, or a commit not pushed, has waited
  longer than `memoryBackupHours` (24 by default, 0 turns it off, a new setting): from when the oldest change waits,
  how many notes and commits wait, and what to do. The warning reaches a person at a session's start and as the one
  reminder after a reply. `memory status` says from when the oldest change waits.
- **`memory push` says when a push failed.** Run by hand, it said "nothing to push" for a push that failed, with exit
  code 0. It now says that it failed, how many commits wait and what git said, with exit code 1. As a hook it stays
  silent, with exit code 0.

## 0.16.3 (2026-11-23)

The memory backup, put right for sessions that run in a worktree, where it did nothing in silence. No Claude Code
limit moved, and no command, hook or setting is new.

- **The memory backup works for a session in a worktree.** The hook after a reply looked for the notes beside the
  session's transcript. A session in a worktree has its transcript in the worktree's own project folder, while the
  notes are in the main checkout's, which every worktree shares, so the hook found no backup there and did nothing, in
  silence. Where every session works in a worktree, nothing was backed up: the first user's notes waited more than a
  day, until a person asked. The hook now takes the notes beside the transcript when they are backed up, as before,
  and otherwise those of the main checkout of the folder the session works in, the folder `memory status` names.
  Notes that waited are pushed after the next reply; nothing has to be done by hand. A machine that has the hook of
  its own from `memory setup` without `--no-hook` runs the same code, so it is put right too.

## 0.16.2 (2026-11-22)

A warning about a link inside a worktree, given before anything removes the worktree, where 0.16.1 gave it only when
`crew prune` ran. No Claude Code limit moved, and no command, hook or setting is new.

- **A link inside a worktree is named at every session's start, before anything removes the worktree.** 0.16.0 made
  `crew prune --remove` take such a link away first, but that protects only a removal that goes through bowline. A
  worktree can also be removed by Claude Desktop's own clean-up of worktrees, by git run by hand, or by a delete in a
  file manager, none of which asks bowline. The doctor's line at a session's start now names each worktree that holds
  a junction, a symbolic link or a mount point to a folder outside it: the link, where it points, why it matters
  (Git for Windows' `git worktree remove` deletes what a junction points to) and the command that takes it away alone,
  `cmd /c rmdir "<the link>"` with no `/s` on Windows or `rm "<the link>"` with no `-r` elsewhere. That line comes
  first and whole, apart from the findings about the instructions and the memory, so it never waits behind three of
  those. The full report gives the same warning, and the reminder after a reply names a link made during the session.
- **The look names the same links**, under the worktree they are in, a quiet worktree and one being removed too, with
  the same command; `crew --json` gives them as each worktree's `links`. 0.16.0 left this out because a walk of every
  worktree on every look was too slow for `crew watch`, which draws the look every ten seconds. The warnings look only
  at a worktree's top level and one level down, where such a link stands (`node_modules`, `webui/node_modules`): on the
  first user's machine that took 3.4 milliseconds for ten worktrees, against 230 milliseconds for a full walk of one
  scratch worktree with 3,000 packages. prune still walks a worktree whole before it removes it.
- The crew skill, the rule template `beside-other-sessions.md` and the conventions page now say: never link a
  worktree's `node_modules`, or any other folder, to another checkout's; give the worktree packages of its own, for
  example with `npm ci`.
- `plugin/docs/facts.md` records what is known of Claude Desktop's own removal of a worktree and a link: not tested,
  because neither of its removals can be run on a scratch folder alone; its code, read in version 5.11492.5, takes
  every link away alone before it removes a worktree.

## 0.16.1 (2026-11-22)

The release of the seven fixes listed under 0.16.0, with one more. 0.16.0 reached the default branch, but its tests
failed on GitHub's Windows and macOS machines, so it was never tagged; this version carries all of it. No Claude Code
limit moved.

- The crew no longer breaks a long path in the middle when it wraps a line. Its lines wrap at 100 columns, and a word
  longer than a line was cut with a space, so a path such as a link's target came out as two pieces, and a person who
  copied it got a path that does not exist. A word longer than a line now stays whole, on a line of its own. The tests
  on GitHub's Windows and macOS machines, whose temporary folders have long paths, found it in 0.16.0.

## 0.16.0 (2026-11-22)

Seven fixes from a crew report in the first user's repository on 2026-11-22, where the look and `crew prune` misled
the person, and where `crew prune --remove` deleted the main checkout's packages through a junction; that fix comes
first. No Claude Code limit moved. Two settings are new, `crew.oldUntrackedHours` and `crew.desktop`, and the crew now
reads Claude Desktop's own record of its sessions and Claude Code's own record of its running processes, which
`PRIVACY.md` describes. The reasoning is in `plugin/docs/decisions.md`, "prune never deletes through a link" and "the
crew reads Claude Desktop's record of its sessions".

- **`crew prune --remove` no longer deletes through a link.** Git for Windows' `git worktree remove` follows a
  directory junction inside the worktree and deletes what it points to. On 2026-11-22 a worktree held
  `webui/node_modules` and `docs-site/node_modules` as junctions to the main checkout's real folders; prune called it
  safe, because git ignores both, and its removal deleted 97 of the main checkout's packages and all of the second
  folder. prune now walks a worktree that could go, without following any link, for every junction, symbolic link and
  mount point that points outside it, and lists each with its target under "Not safe while its links stand".
  `--remove` takes each such link away first, the link alone, checks that what it pointed to keeps every entry, and
  runs git only on a worktree that holds none; if a link cannot be taken away, git is not run. A message about a
  folder a removal left behind never advises deleting it while it still holds a link, and says how to take a link
  away alone.
- `memory losses`, and the doctor's warning that reads it, no longer count a line of a note's front matter that a
  commit gave a new value in place. Claude Code writes the front matter again on every save, with a new `modified:`
  time under `metadata:`, so the old time was reported as a line that one session had added and another had lost. A
  field removed with no new value, and a line of the note's body, are still losses.
- The look and `crew prune` tell untracked files apart from changes to tracked files, and give the age of the newest:
  "1 file not committed, 3 untracked files, the newest from 24 October". Untracked files that nobody has written for
  a day (the new setting `crew.oldUntrackedHours`, 24) no longer put a worktree whose sessions are idle under WAITS
  FOR YOU; it is listed under IDLE with those files and their age. Until now a Vite cache and an editor's settings
  from October put a main checkout first in the look, as "idle, with work not committed". `crew prune` still calls
  such a worktree not safe, because `git worktree remove` refuses untracked files, and says so. `crew --json` gains
  each worktree's `untracked`, `untrackedAt` and `untrackedOld`.
- The crew reads Claude Desktop's own record of each of its Code sessions (the new setting `crew.desktop`; `false`
  turns it off), of which it reads only the ids, the title, whether it is archived, its folders and its last
  activity; `PRIVACY.md` says so. A session the app records is named by its full title, where `claude agents` cuts it
  at 50 characters, and comes with the app's id, `local_<uuid>`, by which a reply in the app links it. Run inside a
  Claude Code session, the look ends with SESSION LINKS, each listed session's id and title; `crew --json` gives the
  id as each session's `desktop`. The crew skill tells the session that reads the look to link every session it
  names as `[its title](#<its id>)`.
- A Claude Desktop session in the person's sidebar, not archived, whose process has ended is now an offline session
  of its worktree. `claude agents` does not list such a session, so until now the look put its worktree under QUIET
  with no session, and `crew prune` called it safe to remove: on 2026-11-22 four worktrees were removed whose
  sessions were still in the sidebar. The look names the session beside its worktree and says to archive it before
  the worktree is removed, and `crew prune` keeps the worktree, saying "its session ... is offline in Claude
  Desktop's sidebar, not archived: reopened after a removal, it would find its folder gone, so archive it first".
  Once the session is archived, the worktree is safe. An offline background session is no longer worded as "open" in
  `crew prune`. The look lists, under ACROSS THE WORKTREES, the sidebar sessions whose worktree is gone or being
  removed, for the person to archive; `crew --json` gives them as `gone`.
- Archiving a session is no longer a sign of work. When Claude Desktop archives a session, it detaches the HEAD of the
  session's worktree at the commit it was on, rewrites the index and writes to the session's transcript; the look then
  put the worktree under AT WORK, "a sign of work less than a minute ago (its git folder), and no session listed
  here", and `crew prune` called it not safe for six hours. A write of HEAD that moves it to no other commit, with
  the index written beside it, and the transcript of an archived session no longer count. The look names the archived
  session of a worktree that no other session holds ("its session ... is archived in Claude Desktop, so no session is
  open here"), and `crew prune` names it beside a worktree that is safe to remove; `crew --json` gives each
  worktree's `archived`.
- The look names the Claude Code processes that no listed session owns. On 2026-11-22 ten `claude.exe` processes,
  2.3 GB together, ran as administrator; `claude agents` listed none of them, Windows hid their command lines from
  the look, and the look never mentioned them. Now, where Claude Code's own record of a running process names a
  session in a worktree, that session is shown there ("not in Claude Code's list"), and prune keeps the worktree; a
  background session listed with no process gets the process its record names. Every other one is listed under
  ACROSS THE WORKTREES with its process id, when it started, its memory and its program, what is known of its owner,
  and whether it runs as administrator; their memory is added to the memory line. bowline never stops them, and says
  that the person can end one in Task Manager's Details tab. `crew --json` gives them as `strays`. `PRIVACY.md` says
  what is read.

## 0.15.1 (2026-11-22)

The crew sees a session's background command, and says when a session it lists is not running. No Claude Code limit
moved. The reasoning is in `plugin/docs/decisions.md`, "a session's own command is work, and a session with no process
is offline".

- A session that Claude Code calls idle, because its turn has ended, while a command it started still runs puts its
  worktree under AT WORK: "a background command runs, its session idle". The command is named under the session, in
  one line ("runs in the background: git push origin main"). A command is a shell that Claude Code started for its
  Bash or PowerShell tool, found below the session's own process; its MCP servers, hooks and the shell's startup are
  not commands. Until now such a worktree with commits not pushed was shown under WAITS FOR YOU as "idle, with work not
  on origin/main", while a 21 MB push ran there for 45 minutes.
- A background session that `claude agents --json` lists with no process is offline. Claude Code keeps such a session
  in its list with the state it last recorded, often "blocked", and the look showed it as blocked and waiting for the
  person; on this machine five were listed, started between 6 and 112 days ago. The look now says that no process of it
  runs, never puts its worktree under WAITS FOR YOU for it, and counts it apart in the first line. `crew --json` gains
  each session's `commands` and `was`, the status `offline`, and `counts.offline`.
- The crew skill tells the session that reads the look to check a session itself before passing "idle, with work" on,
  to put the work that is moving first, to list a side session under the session it belongs to, and, when the person
  needs memory back, to go through every idle session that holds nothing of its own, including one beside a session
  that holds work.

## 0.15.0 (2026-11-21)

The turn makes room by memory, and a removal of a worktree is never stopped halfway. It comes in two parts,
below.

`crew prune --remove` lets git finish. No Claude Code limit moved. The reasoning is in `plugin/docs/decisions.md`,
"which worktrees may go, and an order for pushes", corrected the same day.

- `git worktree remove` runs with no time limit. On Windows, git took more than the two minutes allowed to delete a
  worktree with its own `node_modules`, and was stopped partway, which left the folder with no `.git` file and part
  of its files. Nothing in such a folder is lost, since only a worktree whose work is all on the pushed branch is
  removed, but the folder had to be deleted by hand.
- What git says when it does not remove a worktree is shown; until now the message said only that git "said
  nothing". A removal git stops partway says that the folder is left without its `.git` file.
- Before each removal after the first, the sessions, the processes and the claims are measured again, since each
  removal can take minutes. Each removal is announced as it starts.

The turn makes room by memory, and each session shows what it holds. The reasoning is in `plugin/docs/decisions.md`,
"the turn makes room by memory, and each session shows what it holds".

- `bowline crew run --small -- <command>` is for a check of one file or a few: it runs beside the full checks, one
  small check at a time, so that a test of one file no longer waits behind another session's full suite.
- The new setting `crew.slots` (1) is how many full checks run at once. A heavy process that no `crew run` started
  takes a slot too, so with one slot a full check waits as before.
- `crew run` measures the memory its command and every process below it take, says the most when the command ends,
  and keeps the most of each command's last three runs in the repository's git folder (`peaks.json`). A check that
  would start beside another waits until that much, and a tenth more, is free. `--sample <seconds>` sets how often
  it measures (five).
- The look shows each session's memory beside its name (its own process and every process it started), the machine's
  memory in use, the largest peaks measured, and every turn held, the small one's too. `crew --json` gives them as
  `memory`, `slots`, `turns` and `peaks`, and each session's `memory`.
- On Windows, a process whose command line holds a line break, as `python -c` with a script of several lines does, was
  missing from the list of processes; it is read whole now.

## 0.14.0 (2026-11-21)

The crew for a day of many sessions in one repository: it names who works where, puts what waits for the person
first, says which worktrees may go, and keeps an order for pushes. It comes in three parts, below.

The crew names the sessions, and gives each process to the right worktree. No Claude Code limit moved; one observed
fact was added to `plugin/docs/facts.md`: what `claude agents --json` lists, as Claude Code 2.1.330 prints it. The
reasoning is in `plugin/docs/decisions.md`, "the crew names the sessions, and a process goes by its session".

- `bowline crew` lists the sessions of each worktree by name, with whether each is busy, idle or blocked, from
  `claude agents --json`, Claude Desktop's sessions included. Two sessions in one worktree are both listed, with a
  warning when both are busy. The list is kept in the repository's git folder (`sessions.json`) for the hooks, which
  never start claude. Where claude cannot be asked, a transcript written lately stands for a session, named by the
  title line at its end, and the look says so. The new setting `crew.claude` names the program.
- A worktree whose folder has lost its `.git` file, as while it is being removed, is named "broken or being removed"
  and left out of the counts and of the files changed in more than one worktree. Until now git asked there answered
  for the main checkout, and the look showed the main checkout's changes as that worktree's.
- A process goes to the worktree of the session it descends from, then to the one its command line names, then to
  that of its children when all of them agree, then to that of its nearest parent with one. A build such as
  `cmd.exe /d /s /c tsc -b && vite build` is no longer listed as belonging to no worktree. The main checkout path that
  Claude Desktop passes to every session as `--project-config-root` no longer puts every Desktop session's process
  in the main checkout.
- On Windows, the `&`, `<` and `>` that wmic writes as `&amp;`, `&lt;` and `&gt;` are read back, so a command shows
  as it is and the heavy patterns match what really runs.
- The line at a session's start and the line before a prompt name each place where another session works on its
  own, say which one is the session's own folder, and name the sessions there:
  `in .claude/worktrees/other, "the parser"; in your own folder, the main checkout, "the docs"`. They count
  sessions, not places.

The look puts what waits for the person first, and gives the same as data. The reasoning is in
`plugin/docs/decisions.md`, "the look puts what waits for the person first, and is plain text".

- `bowline crew` shows each worktree once, in the first group that fits: WAITS FOR YOU (a session asks a question or
  is blocked, or its sessions are idle while the worktree holds files not committed or commits not on the pushed
  branch), AT WORK (a session is busy or a heavy check runs), IDLE (a line each) and QUIET (one line for all, saying
  whether any holds work). Then the files changed in more than one worktree, grouped by the worktrees that share
  them, the person's ports and the turn. A worktree goes by its folder's name. Every line is plain ASCII within 100
  columns, for Claude Desktop's narrow pane. `--verbose` shows the quiet worktrees one by one.
- `bowline crew --json` prints the model the printout is drawn from.
- `bowline crew watch` draws the printout again every ten seconds (`crew.watchSeconds`) until Ctrl+C, for a terminal
  kept beside the app; it measures the worktrees in the background.
- `bowline crew say --asks "<question>"` says that the session waits for the person's answer; every look shows it
  first. The hook after a reply sets it when the reply ends with a question (`crew.asksFromReply`, on by default),
  from the reply's text Claude Code gives that hook, and the hook before the person's next prompt takes it back.
- A commit counts as not on the pushed branch only when its change is not there (`git cherry`), so a worktree whose
  commits were rebased onto main no longer reads as holding them.
- A chain of processes that name no path, as Git Bash starts them, takes the worktree its last one names, and a
  worker that a worktree's test runner starts from the main checkout's shared `node_modules` stays with that
  worktree. A Claude Code shell is shown by the command it runs.
- Not built: `crew line` for Claude Code's status line, since Claude Desktop sessions do not show one.

Which worktrees may go, and an order for pushes. The reasoning is in `plugin/docs/decisions.md`, "which worktrees
may go, and an order for pushes".

- `bowline crew prune` names the worktrees that are safe to remove: every file committed, every commit's change on
  the pushed branch (by content, so rebased commits count as pushed), no session, process, claim, lock or place in
  the push queue, and no sign of work for `crew.pruneHours` (six). It says why each other one is not. `crew prune
  --remove <name>...` removes the ones named, each checked again first, with plain `git worktree remove`, which
  takes ignored files such as `node_modules` and refuses a change, so nothing is ever forced; the branch stays. The
  skill runs it only on the person's yes.
- `bowline crew queue join` takes a place in the push queue before the full checks and says which worktrees ahead
  change a file this one changes, so that the session rebases onto their push first; `crew queue` lists it and
  `crew queue leave` gives the place up. `crew run` says the same before a heavy check, and runs it all the same.
  After a push that the pushed branch holds, the hook gives the place up and names who comes next with the same
  files. The look shows the queue.

## 0.13.4 (2026-11-21)

A split whose worker is gone no longer has to be cleared by hand. No Claude Code limit moved. The reasoning is in
`plugin/docs/decisions.md`, "a worker that is gone is told from one at work".

- A worker that is stopped, or whose machine restarts, leaves its record at "running", and until now the doctor and
  `bowline autosplit status` said "being prepared in the background" for good. They now say that the split
  "stopped without recording how it ended", with the reason: the process the record names no longer exists, or, for
  a record still at "starting", no worker began within two minutes. The doctor reports it as a warning.
- `bowline autosplit discard` accepts such a record. It removes the worktree the worker left and the temporary
  folder made for it, deletes the branch and clears the record, and autosplit starts again after the next reply.
  The steps by hand that 0.13.3 named are no longer needed. A worker that is at work is still refused, as before.
- `bowline autosplit run` on such a file says to discard the record first. The hook still starts nothing on its
  own for a file that has a record: a headless session costs money, so a second try is the person's decision.
- `common.process_alive()` says whether a process exists, without starting a program: through kernel32 on Windows,
  with signal 0 elsewhere.

The tests also remove their scratch folders now, which they did not do on Windows. This part changes only `tests/`,
nothing in the plugin.

- On Windows every test left its scratch folder, `bowline-test-*`, in the system's temp folder. git writes its
  object files read-only, Windows does not remove a read-only file, and the removal ignored every error, so nothing
  said so: the machine where it was noticed held about six thousand such folders after a week. The removal
  (`remove_tree()` in `tests/support.py`) now makes a file or a folder that is refused writable and removes it
  again, and tries for up to ten seconds when a process the test started still holds a file. Linux and macOS
  already removed the folders.
- On every system a test whose own `setUp` failed left its folder too, because unittest runs no `tearDown` after
  a `setUp` that failed. The removal, and putting the environment back, are now cleanups, which run in that case
  as well.
- A test whose scratch folder cannot be removed now fails and names what refused, so the folders cannot pile up
  unseen again. `tests/test_support.py` checks it: a scratch repository is gone after its test, with its read-only
  object files, and after a test whose `setUp` failed, and a folder that stays fails the test.
- The folders left by earlier runs are not removed by this change. They are safe to delete when no test is
  running: in PowerShell, `Get-ChildItem $env:TEMP -Directory -Filter 'bowline-test-*' | Remove-Item -Recurse
  -Force`.
- Not changed: how a worker removes its own temporary folder, `bowline-split-*`, when its split ends. git removes
  that worktree itself, with read-only files in it, and the folder stays only while another process still has a
  file open in the worktree or works in it, which clearing the read-only mark does not cure.

## 0.13.3 (2026-11-21)

A fix for Windows: an autosplit worker could stop for good at the moment something else read its record. No Claude
Code limit moved. The reasoning is in `plugin/docs/decisions.md`, "a record that Windows refuses to replace is tried
again".

- On Windows a file cannot be replaced while another process has it open. bowline saves a record (a split's state,
  the crew's claims, statuses and survey, the doctor's watch file) by writing a file beside it and putting that file
  in the record's place, and Windows refused that step with "Access is denied" whenever a session's hook, the
  doctor, a test or a virus scanner had the record open at that moment. The step is now tried again for up to five
  seconds (`common.replace_file()`); a reader is done within milliseconds. Linux and macOS never refused it, and
  nothing changes there.
- An autosplit worker that met the refusal stopped with a traceback in its log. It left its record at "running", and
  its branch and its worktree behind, and autosplit never started on that file again. If `bowline autosplit status`
  says that a split is "being prepared in the background" since a time long past, that worker is gone. `bowline
  autosplit discard` refuses such a record, so clear it by hand: `git worktree list` shows the worktree the worker
  left, then `git worktree remove --force <that folder>`, `git branch -D bowline/split/<the name>`, and delete
  `.git/bowline/autosplit/<the name>.json`. The next reply starts a new worker.
- A worker that fails after it made its worktree now removes the worktree and records "failed" with the reason,
  whatever the failure was. Before, only a failure inside the headless session was recorded.
- The two tests that wait for the worker failed in about half of the full runs on one Windows machine, for this
  reason and not because the machine was busy. They now share one wait, `wait_for_split()` in `tests/support.py`;
  when it runs out, the test fails with the record as it stands and the end of the worker's log.

## 0.13.2 (2026-11-21)

What the collaborate skill left out, found the day it was used between two repositories. No Claude Code limit
moved. The reasoning is in `plugin/docs/decisions.md`, "a message that stops being true is corrected".

- The collaborate skill says that a message which stops being true needs a correction: when a session told
  another one that it would not push, or that something waits for the person, and that changed, it sends one line
  in the same turn that names the message it corrects. After a commit or a push, the hash also goes to every
  session that was told the work was not committed or not pushed.
- A session that needs another session's branch or commit first writes that down with `crew claim waits:<its
  folder or its branch>`, in the step about exchanging file lists and not only in the crew skill, so that
  bowline's check after that session's commit or push names it.
- The skill says that the record is one repository's: a session that works in another repository is no
  neighbour there, so the messages carry everything the record would.

## 0.13.1 (2026-11-21)

A wording fix in the rule template. No Claude Code limit moved.

- `templates/crew/beside-other-sessions.md` says where a status is seen: `bowline crew say` writes it, and every
  session sees it in `bowline crew`. 0.13.0 said only that every session sees it, which names no command to run.
  Four other sentences lost a few words to pay for it, with their meaning unchanged, so the template is 4,034
  characters, two fewer than it was. A repository that copied the template adds the three words to its own copy.

## 0.13.0 (2026-11-21)

Several sessions in one repository is the usual case, with no setup. No Claude Code limit moved. The reasoning is in
`plugin/docs/decisions.md`, "several sessions in one repository is the usual case".

- Every session's start in a repository gets the line about working beside other sessions, whether or not another
  one is seen: the second session may start a minute after the first one looked. The line names the places where
  another session worked in the last `crew.activeMinutes` minutes, or says that none shows now, and names
  `/bowline:crew` and, new, `/bowline:collaborate`. A new setting, `crew.assumeOthers`, is true by default; false
  gives the line only when another session is seen, as before, and `crew.activeMinutes` 0 still gives none.
- A session that is already running is told when another one appears: before a prompt, the hook names each place
  where a sign of work has shown since the session was last told, once, and again when it comes back after going
  quiet. The 30 minutes of `crew.activeMinutes` were never a wait: the look happens at once, and the number only says
  how long a sign of work counts.
- In a repository that has no rule about working beside other sessions, the line at a session's start carries the
  rule's main points (split the work by files, claim before you work, run a heavy check through the turn) and says
  that the last section of `/bowline:crew` sets the repository up. Before, nothing told a session that the setup
  exists: it is in a skill the session opens only by choice.
- The rule template, `templates/crew/beside-other-sessions.md`, says that `bowline crew` is the plugin's script and
  not a program on the PATH, and has a new point: on one subject, work as a team, following `/bowline:collaborate`,
  with a status written by `bowline crew say`. Its other points are worded shorter to pay for both, so the template
  is the size it was, 4,036 characters; every session reads it at its start. A repository that already copied the
  template keeps its copy: compare the two and take what it lacks.
- The init skill offers the crew's setup at its end, and the crew skill offers the settings and the rule in every
  repository, without asking first whether several sessions work there.

## 0.12.0 (2026-11-21)

Sessions that work as a team, not only beside one another. No Claude Code limit moved. The reasoning is in
`plugin/docs/decisions.md`, "sessions that collaborate".

- A new skill, `collaborate`: say your subject before you design (`crew claim subject:<name>`), exchange file lists
  before either session edits, keep a status of your own, ask another session to try your uncommitted work from its
  own worktree, ask what it sees from where it stands when a decision is open, and look once more before a step that
  cannot be taken back. It says what a message is (a notice that may arrive late or cross the answer) and what the
  record is (the claims, the changed files and what each session said, true whenever anyone looks), and what another
  session's word is worth: information, never the person's approval.
- `crew say "<words>"` keeps a few sentences a session writes about its own work: what is done, with the commits,
  what it waits on, what it asks. One per worktree, replaced each time, in the repository's git folder, never
  committed. `bowline crew` shows each worktree's with its age; `crew say` alone prints this worktree's, and
  `--clear` takes it back. A status longer than `crew.sayChars` (600 characters, a new setting) is refused, not cut.
  Saying something counts as a sign of work, and a worktree that is removed takes its words with it. The look shows
  the words in quotation marks, so that a session's free text never reads as one of the look's own lines. The warning
  before an edit says when the worktree that holds the file has said what it is doing, and where to read it; it never
  repeats the words.
- The crew skill, the conventions skill, the conventions page, the guide, the README and `plugin/PRIVACY.md` name the
  new skill and the command.

A fix: on Windows, bowline's background work opened console windows that took the focus. No Claude Code limit moved.
The reasoning is in `plugin/docs/decisions.md`, "a background process on Windows gets a console that is never shown".

- The autosplit worker and `crew refresh` were started with no console at all (`DETACHED_PROCESS`). Windows therefore
  opened a new, visible console window for every git and Python they started, and a burst of windows took the focus
  for a few seconds from whatever the person was doing. Both now start with a console of their own that is never shown
  (`CREATE_NO_WINDOW`), and every program they start shares it. They still keep running after the hook returns, in a
  process group of their own. Linux and macOS are unchanged.
- `common.background_start()` now holds how bowline starts a process in the background, so both starts use the same
  arguments, and a test checks each of them.

## 0.11.0 (2026-11-21)

A warning before an edit of a file that another worktree holds, and one rule template for working beside other
sessions. No Claude Code limit moved. One row of `plugin/docs/facts.md`, what a PreToolUse hook can tell Claude, was
read in the documentation on 2026-11-21. The reasoning is in `plugin/docs/decisions.md`, "a warning before an edit"
and, inside the crew's entry, "One rule, with both halves".

- A new hook before every Edit, Write and NotebookEdit that Claude makes. When another worktree of the repository
  holds the file, Claude is told which worktree and branch, how (changed there and not committed, committed there and
  in neither the pushed branch nor this one, or claimed there as `file:<path>` with the claim's reason), and the last
  sign of work there. It says so once per session and file, as the hook's `additionalContext` with no permission
  decision, so the edit is never blocked and the person's permission flow is unchanged. It goes by the edited file's
  path, not by the folder the session started in, so a session that works in another repository by path is covered.
- `crew before-edit --file <path>` asks the same question by hand and answers in a sentence either way.
- The hook measures nothing. It reads the record `bowline crew` and `crew refresh` keep (`changed.json` in the
  repository's git folder); when the record is older than `crew.changedCacheSeconds` (60, a new setting) it starts
  `crew refresh` in the background, waits two seconds for it, and otherwise answers from the record it has. A record
  over an hour old is not used.
- Silent for the files every session adds to (`crew.shared`, and the files of `crew.numbers` and `crew.stamps`), in a
  repository with one worktree, and when `crew.warnBeforeEdit` (a new setting, on by default) is false.
- The launcher, `run.mjs`, answers this one hook itself when the edited file's repository has no other worktree, and
  starts no Python for it: the hook runs before every edit of every session, and most repositories have one worktree.
- The doctor notes a repository that has several worktrees and no rule about working beside other sessions, and
  points to `/bowline:crew`. It is a note, so it is not said at a session's start.
- The crew's rule template, `templates/crew/beside-other-sessions.md`, holds both halves of working side by side:
  keeping apart (look, split the work by files, claim, edit the shared records, the turn, read again after a rebase,
  send the hash) and giving work a session of its own (a task of its own gets one, parallel sessions where the pieces
  allow it, a new subject moves the round first, reading and checking stay in subagents). The second half comes from
  the rule the first user's repository wrote for itself, so that a repository gets one rule about this and not two.
  The crew skill gains the rule about splitting by files, a section that names the warning before an edit and a
  seventh step for the second half, and the conventions page names each habit with its loss.
- The record a look keeps (`crew.cached_survey`) holds each worktree's commit as `head`.

Not done in this version: an edit made through a shell command is not seen, a session that only edits leaves no sign
of work for the others, and a file with many holders gets a long warning (the decisions page has them, numbered).

## 0.10.0 (2026-11-21)

The crew: several Claude Code sessions in one repository, each in its own worktree, without colliding. No Claude Code
limit moved. Three rows of `plugin/docs/facts.md` about hooks were read in the documentation on 2026-11-21, and two
were observed that day: the Write tool refuses a file that changed since it was read while the Edit tool keeps the
other changes, and each worktree has its own project folder. The reasoning is in `plugin/docs/decisions.md`, "the
crew".

- A new command, `bowline crew`. Alone it lists every worktree of the repository: its branch, its distance from the
  pushed branch, its uncommitted files, when a session last worked there, its processes that are heavy or listen on a
  port, the person's own ports as never to be stopped, the files changed in more than one worktree, the claims and
  the turn. It reads the machine's process list and its listening ports, and stores nothing of them. The last sign
  of work in a worktree is the newest of a session's transcript, the worktree's own git folder being written, and a
  claim, so a session started in another folder that works there by path is seen. A file counts as changed in two
  worktrees only when they hold different content of it, so a branch cut from another's commit shows none; the files
  a repository names as shared records (`crew.shared`) are listed apart; a worktree with no sign of work for a day is
  marked quiet; and a worktree git lists but this system cannot enter is named. Every git question is asked with
  `--no-optional-locks`, so a look never takes the lock another session's git command needs. What the look measured
  is kept in the repository's git folder for a hook to read, and `crew refresh` measures again.
- `crew claim <key>` takes a note, a file or a number for this worktree and refuses one another worktree holds, naming
  it; `crew claim <list> --new` takes one past the highest number of a numbered list in the pushed branch, in every
  worktree's copy of the file and in every claim; a key that starts with `waits:` says this worktree waits on
  another's push, and several may hold it; `crew release` gives claims back. The claims live in the repository's git
  folder, shared by its worktrees, never committed. A claim of a removed worktree, and a number that reached the
  pushed branch, are dropped.
- `crew run -- <command>` waits until no process on the machine matches the repository's heavy patterns and no other
  `crew run` holds the turn, runs the command and passes its exit code through; after `crew.waitMinutes` it names what
  still runs and exits with code 3 without running it. It never stops a process.
- `crew after-rebase` says when a number appears twice in a numbered list, when a number this worktree claimed
  reached the pushed branch, or when a stamp names a commit the branch no longer holds; `crew after-push` and
  `crew after-commit` say who waits on this worktree. New hooks run them after a `git rebase`, `git pull`, `git push`
  or `git commit` that Claude issues, through the Bash or the PowerShell tool, and say nothing when there is nothing
  to say.
- The doctor warns about a number that appears twice and about a stale stamp, in a repository that names its lists and
  stamps. At a session's start it adds one line when another session worked in the repository in the last
  `crew.activeMinutes` minutes, in another worktree or in the same folder, from the times the transcript files were
  written, never their content.
- The memory backup's commits made by the hook name the session whose reply they follow ("Session: <id>"). The doctor
  warns when one session's commit removed lines that another session's commit had added within
  `crew.memoryLossHours` hours and no note holds them now, without quoting them; `bowline memory losses` lists them,
  and `--meant <commit>` records a removal that was meant. The memory's history is read with `--no-show-signature`,
  so a person whose git shows signatures on every commit gets neither their lines in the text nor a check of each.
- A new skill, `crew`, with the procedure and the three rules for a file the sessions share; a rule template for a
  repository where several sessions work, `templates/crew/beside-other-sessions.md`, which the skill offers and `init`
  does not write; a `crew` section in `defaults.json` with each key's reason, all of it empty or off until a
  repository fills it: `heavy`, `keepPorts`, `numbers`, `shared`, `stamps`, `base`, `activeMinutes`, `waitMinutes`,
  `waitEverySeconds`, `memoryLossDays`, `memoryLossHours`.
- `plugin/PRIVACY.md` says what the crew reads and writes, and that the backup's commits now carry the session's
  identifier to your remote.

Not done in this version: a git `post-rewrite` hook for rebases made outside Claude Code, the commit gate's hook for
the PowerShell tool, claims across machines, and the session-start line from a folder of repositories (the decisions
page has them, numbered).

## 0.9.0 (2026-11-16)

A folder of many repositories: `init` installs the gate where it can and says so where it cannot, describes each
repository on purpose, and keeps its lists short; the doctor takes seconds, not minutes, and says a repeated finding
once. No Claude Code limit moved; the facts stay as checked on 2026-11-14. The reasoning is in
`plugin/docs/decisions.md`, "a folder of many repositories".

- `init` from a folder that is a git repository offers `scripts` and `githook`, installed as for a repository. From a
  plain folder it refuses them, and its plan says what `git init` would add: the gate and the `.gitignore` entries.
- The folder's rules, skills and `.claude/README.md` come from `templates/folder/`, worded for a folder, and name the
  folder's copy of the gate only when there is one; the plan marks the others "without the gate".
- Each row of the folder's table is described from the README, the package's description, or the opening of the
  `CLAUDE.md`, never a warning, a rule or a list item, in whole sentences; the plan says which rows came from where.
  New flag: `--no-describe`.
- The folder's `CLAUDE.md` has one blank line before "Memory between sessions", and its paragraphs that hold a filled
  sentence are re-wrapped.
- The doctor from a folder: the layout worked out once per run, three git processes per repository instead of eleven,
  eight repositories at a time, each printed as it completes, progress on standard error, a repeated finding said once
  with an `in:` line, no all-zero rules line. New flags: `--verbose` (every finding, size and name one by one) and
  `--folder-only`. Exit codes, `--brief` and the reminders are as before.
- Every list of repositories names ten and says how many more; `--verbose` names them all, in init and the doctor.

Not done in this version: the folder's table moving to a page past 200 lines, `budget`'s one line per repository, and a
plan that says which files written without the gate would now read differently (the decisions page has them).

## 0.8.1 (2026-11-16)

- The curate-memory skill's description names the doctor's new warning, a note that keeps finished work like a
  log, among the times to use it. Claude reads the description when it decides whether to offer a skill, and the
  doctor only reports: without the words, the warning pointed at a skill Claude had no reason to offer.

## 0.8.0 (2026-11-16)

The doctor watches the memory's notes, not only its index. No Claude Code limit moved:
`memoryNoteCommits` is bowline's own threshold, and the facts stay as checked on 2026-11-14.

- The doctor warns when a memory note names many commits, so that it keeps finished work like a log
  (`memoryNoteCommits`, 10 by default, a new setting), and points to `/bowline:curate-memory`. Before, it measured only
  the index, and the rule that keeps the index short moves the detail into the notes. `bowline memory status` lists
  every note with its lines, its bytes and the commits it names, the largest first. The memory rule in the templates
  gains one sentence: once the repository records a finished piece of work, the note keeps a pointer to that record
  and its last commit.

## 0.7.0 (2026-11-14)

A folder of repositories can keep bowline's files itself, and can be a git repository of its own.

- A new setting, `writeToRepositories`, read from the folder's `.claude/bowline.json`: `true`, the default and the
  behaviour so far; `false`, so that bowline writes nothing into the repositories under the folder, for repositories a
  person cannot or would rather not write into; or a list of the names it may write into. A repository's own file
  cannot change it. `init --leave-repositories` from the folder writes it as `false`.
- With the repositories left untouched: `init` from the folder writes the README, the starter rules and the skills into
  the folder as well, and its `CLAUDE.md` says that a rule for one repository goes in `.claude/rules/<repository>/`
  with `paths: ["<repository>/**"]`. `init --each` skips those repositories and says why; `init` run inside one refuses
  and points at the folder. `move run`, `pointers` and `place` refuse to write into them and change nothing, while
  `plan` and `--check` still work. Autosplit never starts there, and `autosplit run` refuses. The doctor still measures
  them, but as notes that say why bowline changes nothing and what the person can do: ask the owners, or keep what the
  folder needs in its own rules. So the line at a session's start never repeats a fix the person may not make.
- The folder can be a git repository of its own, which holds what its repositories share without tracking them:
  bowline sees a folder of repositories when a repository's top folder holds other repositories it does not track. A
  submodule is tracked, so it stays part of the repository. `init` there writes the `.gitignore` lines that keep the
  repositories out, the folder's `CLAUDE.md` says what kind of folder it is, the folder's own files get the doctor's
  checks of a repository (the gate, the configuration, autosplit), and the folder's `.claude/bowline.json` is the layer
  its repositories share, as for a plain folder.
- The messages that count repositories say "1 repository" rather than "1 repositories".
- `plugin/docs/facts.md` has two rows on how Claude Code loads a folder's rules and skills, with the documentation's
  words; `plugin/docs/decisions.md` says why the setting is the folder's and why a folder may be a repository.

## 0.6.2 (2026-11-14)

- bowline has a privacy policy, `plugin/PRIVACY.md`, and the manifest names it in `privacyPolicyUrl`, the field
  Anthropic's plugin directory reads; the directory warned that none was found. The page says who is behind bowline and
  that they receive nothing, what leaves the machine and only when the person turns it on (the memory backup to a git
  remote they name, autosplit's Claude Code session to Anthropic), what bowline reads and writes, the personal data the
  memory can hold, how long anything is kept, that it is not intended for anyone under 18, and where to ask. The URL
  follows the `release` branch, so it always shows the policy of the version the directory serves.
- The README's data section becomes "Privacy": a short summary of the two features and a link to the policy, so the
  full text lives in one place. The code is unchanged.

## 0.6.1 (2026-11-14)

- The plugin's README has a section, "What bowline reads, writes and sends", for the data-handling questions of
  Anthropic's plugin directory. It names the two features that send data off the machine, both off until a person turns
  them on: the memory backup, which pushes Claude Code's memory folder with git to a remote the person names, and
  autosplit, whose headless Claude Code session talks to Anthropic as any session does. It lists what bowline reads and
  writes, and says that nothing else is read, written or sent. The code is unchanged.

## 0.6.0 (2026-11-14)

What Anthropic's plugin directory asked when it validated 0.5.3: the validation passed, with three holds for a
reviewer, two warnings and several notes. This version answers the ones bowline can answer.

- The plugin is its own folder, `plugin/`, and the marketplace names it as the source (`"./plugin"`). The directory now
  sees only what ships. The instructions, rules and skills for working on bowline stay in `.claude/` at the
  repository's root, and the tests move to `tests/`; neither ships. This clears the note about files in a
  `.claude/skills` folder and the half of a hold that read the contributors' `CLAUDE.md` as code.
- The hooks name their program and arguments, as the directory asks: `node` with `scripts/run.mjs`, a small launcher
  that finds Python by the name the machine gives it (`python3`, `python` or `py -3`) and runs `scripts/bowline.py`,
  passing standard input, output and the exit code through. Claude Code's hooks documentation gives node with a script
  as the form that works on every system, because a hook given this way runs with no shell, and on Windows its program
  must be a real executable. The skills use the same launcher. This clears the eight notes that a hook named a plugin
  file as its program.
- The shell launchers in `bin/` are gone, which clears the note about files in `bin/`, which Claude Code adds to the
  PATH. Node.js is now a requirement beside Python and git, and the README says so.
- The changelog no longer names the icon's image file in code formatting, which held the plugin for review as if a
  text pointed a program at an image.
- The plugin's README, which the directory shows on the listing, no longer carries the clone-and-run lines it warned
  about. They are in the repository's new front page, `README.md` at the root, with the layout of the repository and
  the tests.
- For a person who installed 0.5.x: nothing to do. `claude plugin update bowline@bowline` installs the plugin from its
  new folder. In Anthropic's portal, the plugin's path is now `plugin`.

## 0.5.3 (2026-11-14)

- Anthropic's plugin directory can validate the repository. It refused with "Couldn't validate that repository",
  naming `.gitattributes` rules among the causes: the rule `*.cmd text eol=crlf` stored `bin/bowline.cmd` with LF and
  turned it into CRLF on every checkout and archive, so the files the directory received differed from what git
  stores. The launcher is now stored with CRLF and the rule is `*.cmd -text`, so git never converts it. What a person
  gets on disk is the same 629 bytes as before; every file of the repository now archives byte for byte as stored.

## 0.5.2 (2026-11-14)

- `claude plugin validate . --strict` passes, which Anthropic's plugin directory asks of a submission. It failed on one
  warning, "CLAUDE.md at the plugin root is not loaded as project context": the file is bowline's own instructions for
  people working on bowline, not context the plugin ships. It moved to `.claude/CLAUDE.md`, the other place Claude Code
  documents for a project's instructions, so contributors' sessions read it as before.
- The doctor, autosplit and init treat `.claude/CLAUDE.md` as a root file, like `CLAUDE.md`, in every repository they
  measure. The doctor no longer says such a repository has no root `CLAUDE.md`, checks the Compact Instructions and
  memory sections there, and never reports it as cut on demand. Autosplit never counts it as cut either. init appends
  the missing sections to it instead of creating a second file beside it, and a folder's table takes a repository's
  line from it. When both files exist, a section in either one counts. `docs/facts.md` has the row, with the
  documentation's words.

## 0.5.1 (2026-11-14)

- bowline has an icon: a bowline knot in off-white on a navy tile, made by the author with recraft.ai. A vector file is
  its source, and a 1024-pixel image with transparent corners is the file the manifest's `icon` field names for
  Anthropic's plugin directory. Claude Code itself does not show it.
- The README shows the icon at its top. On a page in dark mode GitHub shows a second vector file instead, the same knot
  with the two colours swapped, because the navy tile's edge fades into a dark page.

## 0.5.0 (2026-11-14)

- `init` from a folder of repositories scaffolds the folder itself: its own `CLAUDE.md` from `templates/CLAUDE.md.folder.md`,
  an index with a table of the repositories (a line for each, taken from its own `CLAUDE.md`), what applies to every
  repository, the Compact Instructions and a memory section that says the memory is one for the whole folder; and the
  shared `.claude/bowline.json`. `init --each` plans or writes the repository scaffold in every repository of the folder.
  Nothing that exists is overwritten, as before. The doctor's note for a folder without a `CLAUDE.md` points at it.
- The sweep after it, so that every capability works from the folder without a thought: `autosplit run`, `show`, `done`
  and `discard` take the repository from the file's path, as `move` does (`--file repo1/sub/CLAUDE.md`), and say so when
  a bare name is given from the folder; a move spec's index path is read from the repository when it is not found from
  the current folder; the doctor's header names the folder's shared config a repository lies over; the folder's
  CLAUDE.md template says how a rule for a few of the repositories is scoped; and the split-instructions, memory-backup,
  curate-memory (and its rubric) and conventions skills say what changes in a folder: paths from the folder and
  `--repo` where no file is given, one memory for the whole folder, promotions to the repository a note concerns or to
  the folder's own files for what spans them, conventions per repository or for the folder.

## 0.4.0 (2026-11-14)

- The gate hook finds the repository a commit names, from `git -C <path>` or `cd <path> &&` in the command, resolved
  from the hook's folder, so that a session started in a folder of several repositories is gated too. Before, from such
  a folder it exited with code 2, "not inside a git repository", and for a PreToolUse hook that code means block: every
  commit Claude issued there was refused. When the gate cannot tell which repository is meant, it now lets the command
  through and says nothing; it never blocks on its own confusion.
- A folder of repositories, as with services cloned side by side, is a place bowline works from. The doctor, the
  one-line finding at a session's start, the budget and the gate's plain mode measure the folder's own `CLAUDE.md` and
  every repository directly under it and name the repository in each finding; the memory is the folder's, keyed as
  Claude Code keys it; autosplit and the reminders run across the repositories, each split on a branch of its own
  repository; a `.claude/bowline.json` in the folder is the layer every repository shares, under its own. `move` takes
  the repository from the file it is given; `init` says to run it inside each repository. `docs/decisions.md` has the
  shape and what was left out: depths beyond one level, and a scaffold for the folder itself.
- A `release` skill under `.claude/skills/`: the checks, the version in the plugin manifest (the only thing Claude Code
  reads to decide that an update exists), the changelog heading, `claude plugin validate`, one commit, the push to main,
  a plain `X.Y.Z` tag and the proof on this machine. `docs/decisions.md` says why the tag is plain and not the
  `bowline--vX.Y.Z` that `claude plugin tag` makes.

## 0.3.0 (2026-11-14)

`autosplit`: when a repository turns it on, bowline prepares the split of a `CLAUDE.md` that outgrew the limits in the
background, on a branch of its own, and the person reviews and merges.

- Why: the first user asked for the split to happen the way autocompact happens, noticed and done in the background of
  their work. A `CLAUDE.md` is every future session's input, so the result waits on a branch rather than landing
  unasked; `docs/decisions.md` has the reasoning.
- `autosplit --hook` runs from the plugin's Stop and SessionEnd hooks: when `autosplit.enabled` is set in
  `.claude/bowline.json` and a `CLAUDE.md` is over the limits, committed and clean, it starts a detached worker. The
  worker adds a git worktree on the branch `bowline/split/<file>` from the committed HEAD, runs a headless Claude Code
  session there (`-p`, `acceptEdits`, `--permission-prompts none`, an allowlist of tools, `--max-budget-usd`, a time
  limit, the parent session's marks removed from the environment) with the unattended procedure of the
  split-instructions skill, checks the result (a clean tree, the file under the line target, the budget passing),
  removes the worktree, keeps the branch and records the outcome under the repository's `.git/bowline/autosplit/`,
  beside the session's log.
- The doctor, in full and in brief, says when a split is ready, running or failed, and why one has not started (an
  uncommitted file, a missing command, a branch that exists); a ready split points the file's own finding at the review.
- `autosplit run` does the same work now, in the foreground; `status`; `show` prints the commits with the proposal and
  the MAPs and the cherry-pick that takes them; `done` after the merge; `discard` for a split not wanted, or to try
  again.
- The split-instructions skill gains the unattended procedure and the review; `defaults.json` gains the `autosplit`
  settings with their reasons (off by default, `claude` as the command, 20 dollars, 60 minutes); the template
  `.claude/bowline.json` shows the switch; the guide, the comparison, the facts and the migrating page say what changed.
- `move place --spec` copies finished drafts from a scratch folder into instruction files only (a rule, a skill, a page,
  a CLAUDE.md), normalized as `move run` normalizes. The unattended procedure places the condensed rules and the index
  with it, because an unattended session cannot write under `.claude/` itself: Claude Code treats that as a
  sensitive-file edit that only a person may approve, which the first live run found (`docs/facts.md` has the row, and
  `docs/decisions.md` says why the worker was not given `bypassPermissions` instead).
- Reminders during a session. The doctor's `--watch` runs from the Stop hook after every reply: it measures again and,
  when a finding appears that was not there before (a `CLAUDE.md` that crossed the line target, a rules area over its
  budget, the memory index at its cap), shows the person one line in the doctor's words, once, not again as the file
  keeps growing. `--pending` runs from a new UserPromptSubmit hook and hands the same line to Claude at the next
  prompt, so "do it" means something. `--brief` records what it said at the session's start, so nothing is said twice.
  The record is `<git dir>/bowline/watch.json`.
- `autosplit.deliver` chooses how the result arrives: `branch` (the default) leaves the two commits for the person to
  review and cherry-pick; `merge` has the worker cherry-pick them onto the current branch as soon as they are ready,
  only onto a clean tree and only when they apply without a conflict, and the doctor says what landed until `done`.
  `docs/decisions.md` says why branch is the default.
- The tests run the worker against a stand-in for the `claude` command (`scripts/tests/fake_claude.py`), so the suite
  starts no session. That a headless session starts from inside another session's hook environment and returns the JSON
  result was checked by hand on Windows, with a ten-cent cap.
- What that check also found: Claude Code runs a shell-form hook in Git Bash on Windows and falls back to PowerShell
  when it does not find Git Bash, and there bowline's quoted-path hooks are a parse error (`docs/facts.md` has the
  row). The worker therefore hands the session it starts the path of Git for Windows' bash through
  `CLAUDE_CODE_GIT_BASH_PATH` when nothing names one. The hook claims a split by creating its record exclusively, so
  two hooks firing at once cannot start two workers.
- The live check, on a clone of the first user's repository with the line target lowered so that the docs site's
  `CLAUDE.md` (199 lines) counted as oversized, with Sonnet and a ten-dollar cap: the first run stopped at the
  sensitive-file refusal and was reported as failed with its branch and first commit kept; after `move place`, the
  second run finished in four minutes for 1.84 dollars: two commits, 199 lines to 52, four pages, four scoped rules,
  one pointer updated, the proposal and the MAPs in the commit messages, the budget passing, the worktree gone, and
  the doctor's one line saying the split was ready.

## 0.2.0 (2026-11-14)

The plugin is renamed from keel to bowline, hours after 0.1.1. Nothing else changes.

- Why: "keel" turned out to be the name of an official Claude connector (a trading-strategy backtester on claude.com's
  marketplace) and of at least five other Claude Code plugins, one of which already answers to `/keel:` commands.
  Anthropic's directory needs a unique plugin name and makes it permanent, so the name changed before anyone depended
  on it. A bowline is the sailor's knot that holds fast under load and still comes undone by hand.
- What changes for a person who installed 0.1.x: remove the old plugin and its marketplace, then add the new one:
  `claude plugin uninstall keel@keel`, `claude plugin marketplace remove keel`,
  `claude plugin marketplace add taljacob2/bowline`, `claude plugin install bowline@bowline`. The skills are
  `/bowline:doctor` and so on. A repository's configuration file is `.claude/bowline.json` (rename `.claude/keel.json`),
  the launchers are `bin/bowline` and `bin/bowline.cmd`, and the entry point is `scripts/bowline.py`. The repository
  `taljacob2/keel` redirects to `taljacob2/bowline`.
- The entries below keep the old name, because those versions carried it.

## 0.1.1 (2026-11-14)

What the first run of the tests on three systems found, hours after 0.1.0:

- `move` built the "moved from" path from the file's path as given; on macOS the temp folder sits behind a symlink and
  on a Windows runner behind a short name, so the relative path was wrong. Both sides are real paths now.
- The tests named the memory folder from the scratch folder's path as given, while the scripts name it from what git
  reports; the scratch folder is a real path now, as git sees it.
- `.gitattributes` checks every text file out with LF on every system, so the gate's carriage-return rule means the same
  thing everywhere; `*.cmd` keeps CRLF, as cmd expects.
- That CRLF checkout made the gate's own sweep refuse every line of the Windows launcher on the three runners, while
  the LF copy on the development machine passed. The carriage-return rule now skips the files `gate.crlfFiles` names,
  by default `*.cmd` and `*.bat`, and a test stages one file of each kind.
- CI runs Python 3.8 on the Windows and macOS runners and 3.11 on Linux, whose image no longer offers 3.8.

## 0.1.0 (2026-11-14)

The first version, extracted from the knowledge work done in one repository over two days and proven on a second.
Facts checked against the Claude Code documentation on 2026-11-14 (`docs/facts.md`).

- `doctor`: measures a repository's instruction files against what Claude Code reads, the memory folder against its
  index cap and its backup, and the repository against the layout; three lines per finding.
- `gate`: refuses a commit whose staged lines hold a token, a control byte, a carriage return, a byte-order mark, a
  character outside the accepted set when the policy says so, or a word from a private never-commit list.
- `budget`: refuses an instruction file over the sizes Claude Code reads, or one that names a path outside the
  repository.
- `memory`: `setup <remote>` makes the memory folder a git repository tied to a private remote (clones on a new
  machine, pushes a first backup when the remote is empty, refuses when both hold content) and installs the push hook
  for this machine; `status`, `restore`, `push`.
- `init`: scaffolds the repository's side, file by file, never overwriting: the root CLAUDE.md's three sections,
  `.claude/README.md`, two starter rules, two starter skills, repository-local copies of the gate and the budget check,
  the pre-commit hook, `.claude/keel.json` and the `.gitignore` entries.
- The `bin/keel` and `bin/keel.cmd` launchers, the plugin's `hooks/hooks.json` (the memory push after every reply, the
  gate before a `git commit`), and tests on Windows and Linux in CI (macOS by hand while the repository is private).
- `move`: `plan` lists a CLAUDE.md's sections with where Claude Code's cutoffs fall; `run --spec` moves named sections
  verbatim into pages and rules (normalizing only the characters a gate refuses, counted) and writes the index;
  `find-pointers` and `pointers --spec` update every mention, each matched exactly once.
- The six skills the plugin ships: `doctor`, `init`, `memory-backup`, `curate-memory` (with its rubric),
  `split-instructions` (with the brief for the condensing subagents) and `conventions` (with its templates); the guide's
  `docs/conventions.md` and `docs/migrating.md`.
- The plugin manifest and a one-plugin marketplace, so `claude plugin marketplace add taljacob2/keel` and
  `claude plugin install keel@keel` work; `doctor --brief` and the SessionStart hook that runs it, so a session learns
  in one line when something is over budget or unbacked, and hears nothing when all is well.
- The guide (`docs/guide.md`: the problem in a page, the three homes, the budgets, the four flows drawn) and the
  comparison (`docs/compared.md`).
