# Working beside other sessions

Several Claude Code sessions work in this repository at once, each in its own worktree. They share one machine, one
memory folder and the numbered lists each of them extends. The `/bowline:crew` skill is the procedure these rules
follow; `bowline crew` shows who is here.

- **Look before the first change, and before a push.** `bowline crew` lists the worktrees, their processes, their
  ports and their claims; `ListAgents` names the sessions. Never stop a process, a server or a worktree you did not
  start, and never one that listens on a port `.claude/bowline.json` names as the person's own.
- **Claim before you work.** A new number of <the roadmap> comes from `bowline crew claim <list> --new`, never from
  reading the file, because two sessions that each add one take the same number. Claim a note or a file the same way,
  and tell the sessions it concerns with `SendMessage`.
- **Edit a shared file; never save it over whole.** The memory folder is one for every worktree: change a note with
  the Edit tool, one addition at a time, and never write it from a shell or a script, because the last writer erases
  what another session added since it read the file.
- **Run a heavy check through the turn.** `bowline crew run -- <command>` waits until no other session's <test suite
  or build> runs, because two at once crash or time out and the failure looks real.
- **After a rebase, read again what the others also write.** A rebase can succeed and still leave a number twice or a
  build's stamp that names a commit which no longer exists; `bowline crew after-rebase` says so.
- **After a push, send the commit's hash to whoever waits on it**, and give back the claims the push finished.
