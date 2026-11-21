# Working beside other sessions

Several Claude Code sessions often work on this repository at once, each usually in its own git worktree, a
separate checkout on its own branch. They share one machine, one memory folder and the records each adds to. These
rules keep two sessions from changing one thing at once, and give separate work a session of its own.
`/bowline:crew` is the procedure they follow; `bowline crew` is the plugin's script, not a program on the PATH, and
the skill gives its full command.

## Keeping apart

- **Look who else is working before a round and before a push.** `bowline crew` lists every worktree with its
  unpushed files, processes, ports and claims; `ListAgents` names the sessions you can message. Read another worktree
  freely; never write in it. Never stop a process or a server you did not start, nor one on a port
  `.claude/bowline.json` names as the person's own.
- **Split the work by files.** Two sessions never edit one file at once. When your round needs a file another
  session has changed, message it before you edit, agree who changes what, and name the agreement in your commit
  message. If you cannot reach it, wait for its push and rebase onto it. bowline warns before an edit of a file
  another worktree holds.
- **On one subject, work as a team.** When another session has your subject or your files, follow
  `/bowline:collaborate`: say your subject before you design, and exchange file lists before either of you edits.
  Keep a short status with `bowline crew say`, which every session sees in `bowline crew`.
- **Claim before you work.** A new number of <the roadmap> comes from `bowline crew claim <list> --new`, never from
  reading the file: two sessions that each add one take the same number. Claim a note or a file the same way, and
  tell the sessions concerned with `SendMessage`.
- **The shared records are the exception: edited by all, never saved over whole.** Every session writes to <the
  roadmap, the design document's decisions, the notes queue in the memory folder>. Add your own entry with the Edit
  tool, never rewrite another session's, and never write such a file from a shell or a script: every worktree shares
  the one memory folder, and the last writer erases what another added since it read the file.
- **Run a heavy check through the turn.** `bowline crew run -- <command>` waits until no other session's <test suite
  or build> runs, because two at once crash or time out and the failure looks real.
- **After a rebase, read the shared records again**: a rebase can succeed and still leave a number twice, or a
  build's stamp naming a commit that is gone. `bowline crew after-rebase` says so.
- **After a commit or a push, send its hash to whoever waits on it**, and give back the claims a push finished.

## A session of its own

- **A task of its own gets a session of its own.** A deliberate scope cut, or a problem found in passing, gets its
  numbered slot in the roadmap (`recording-decisions.md`) and never widens the round you are in. Where the client can
  start sessions, it also gets a proposed session whose brief names its files and what done looks like; where it
  cannot, as in the terminal, the slot and one line in your reply stand in.
- **Prefer parallel sessions.** When a plan has pieces that touch different files and need nothing from
  each other, propose each as its own session, not one after another.
- **A new subject moves the current round first.** When the person asks about something else in the middle of a
  round, hand the round, with the plan that is left, to its own session, then answer. In a worktree, commit
  first: the new session starts from your branch, without your uncommitted edits.
- **Reading and checking stay with you.** A search, a review or a test run goes to a subagent, whose answer comes back
  in the same turn. A session is for work that ends in a commit of its own.

`before-a-commit.md` says how a finished round is pushed: fetch, rebase, never autostash, stage only your own files.
