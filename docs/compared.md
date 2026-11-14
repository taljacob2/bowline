# How keel compares

## With doing it by hand

Everything keel does can be done by hand, and the first repository did it by hand: reading six documentation pages
to learn the limits, measuring two files to find that two thirds of one and half of the other were never read, moving
hundreds of kilobytes in a pure-move commit and condensing them in a second one, sorting 89 memory notes into a table
and promoting a third of them, writing a hook to push the memory and a gate to stop a token. It took two days of a
long session, and the knowledge of how to do it lived in that session. keel is that knowledge as a tool: the limits as
settings with sources, the measuring as a doctor, the move as a script with a spec, the sorting as a rubric a subagent
can follow, the hooks as a plugin. The second repository took an hour.

## With `claude-md-management`

The official marketplace's `claude-md-management` plugin audits a `CLAUDE.md`'s quality against the code it describes
and captures a session's learnings into it. It answers "is this file accurate and well written?". keel answers "is this
file read at all, and is the knowledge where the tool loads it?". They meet in the middle: keel's doctor will tell you a
file is cut at line 1,200, and `claude-md-management` will tell you what in it has gone stale. Use both; keel's
`split-instructions` leaves a short index behind, which is the file the other plugin then keeps honest.

## With Claude Code's own features

Claude Code already has the mechanisms keel organizes around: `.claude/rules/` with `paths:`, skills, the memory
folder, Compact Instructions, hooks. keel adds no mechanism. It adds the measurement (what is over the limits today),
the layout that follows the mechanisms (three homes by kind, with budgets), the migration into that layout without
losing a line, the backup and curation of the memory that Claude Code leaves to you, and the conventions one team found
necessary around them, offered with their reasons. When Claude Code changes a limit, one file in keel changes and the
changelog says so.

## What keel deliberately is not

- Not a background optimizer. It measures and nudges on its own; it changes nothing without a plan you approve.
- Not a framework. Six skills, three hooks, five scripts, standard library Python, no server, no dependency.
- Not an opinion about your rules' content. It cares where a rule lives and how big the file is, not what it says.
- Not a way to share memory. Memory is personal by design; keel promotes what a project needs into the repository and
  keeps the rest where it was, backed up.
