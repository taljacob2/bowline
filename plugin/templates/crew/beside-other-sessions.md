# Working beside other sessions

Several Claude Code sessions often work on this repository at the same time, each usually in a git worktree of its
own: a separate checkout on its own branch. They share one machine, one memory folder and the records each of them
adds to. These rules keep two sessions from changing one thing at once, and they move work into a session of its own
wherever the work allows it. The `/bowline:crew` skill is the procedure they follow; `bowline crew` shows who is here.

## Keeping apart

- **Look who else is working before a round starts, and before a push.** `bowline crew` lists every worktree, the
  files it has changed and not yet pushed, its processes, its ports and its claims; `ListAgents` names the sessions
  you can message. Reading another worktree is fine; writing in it never is. Never stop a process or a server you did
  not start, and never one that listens on a port `.claude/bowline.json` names as the person's own.
- **Split the work by files.** Two sessions never edit the same file at the same time. When your round needs a file
  that another session has changed, message that session before you edit it, agree who changes what, and name the
  agreement in your commit message. When you cannot reach it, wait for its push and rebase onto it. bowline warns
  before an edit of a file another worktree holds.
- **Claim before you work.** A new number of <the roadmap> comes from `bowline crew claim <list> --new`, never from
  reading the file, because two sessions that each add one take the same number. Claim a note or a file the same
  way, and tell the sessions it concerns with `SendMessage`.
- **The shared records are the one exception, and they are edited, never saved over whole.** Every session writes to
  <the roadmap, the design document's decisions, the notes queue in the memory folder>. Add your own entry with the
  Edit tool, never rewrite another session's, and never write such a file from a shell or a script: the memory folder
  is one for every worktree, and the last writer erases what another session added since it read the file.
- **Run a heavy check through the turn.** `bowline crew run -- <command>` waits until no other session's <test suite
  or build> runs, because two at once crash or time out and the failure looks real.
- **After a rebase, read the shared records again**, because their numbers are shared: a rebase can succeed and still
  leave a number twice, or a build's stamp that names a commit which no longer exists. `bowline crew after-rebase`
  says so.
- **After a commit or a push, send its hash to whoever waits on it**, and give back the claims a push finished.

## A session of its own

- **A task of its own gets a session of its own.** A deliberate scope cut, or a problem found in passing, gets its
  numbered slot in the roadmap (`recording-decisions.md`). Where the client can start sessions, it also gets a
  proposed session whose brief names its files and what done looks like. It does not widen the round you are in.
  Where the client cannot start sessions, as in the terminal, the slot and one line in your reply stand in for it.
- **Prefer parallel sessions where the pieces allow it.** When a plan has two or more pieces that touch different
  files and need nothing from each other, propose each one as its own session instead of doing them one after another.
- **A new subject moves the current round first.** When the person asks about something else in the middle of a
  round, hand the round to a session of its own with the plan that is left, and then answer. In a worktree, commit
  first, because the new session starts from your branch and your uncommitted edits stay behind.
- **Reading and checking stay with you.** A search, a review or a test run goes to a subagent, whose answer comes back
  in the same turn. A session is for work that ends in a commit of its own.

How a finished round is pushed beside the others (fetch, rebase, never autostash, stage only your own files) is in
`before-a-commit.md`.
