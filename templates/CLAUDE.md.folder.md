# This folder, for every Claude Code session started in it

This folder is not a repository. It holds {count} repositories side by side, each with its own `CLAUDE.md`, rules and
skills, which Claude Code loads when a file under that repository is read or edited. This file is read whole at the
start of every session started here and again after every compaction, so it stays short: what the repositories are,
how they relate, and what applies to all of them. Write everything a person reads in full sentences and plain words,
so that a first-time reader understands it without guessing.

## The repositories

| Repository | What it is |
|---|---|
{rows}

Say in a line what each one is and how they call one another; a reader who opens this folder for the first time should
know where to start. Each repository's own `CLAUDE.md` says the rest.

## What applies to every repository

A rule that holds in every repository goes in `.claude/rules/` here, without a `paths:` list, so that it loads at the
start of a session started in this folder; one for a few of them names them in a `paths:` list (`repo1/**`); a rule
for one repository goes in that repository's own `.claude/rules/`.
The `.claude/bowline.json` here is the layer every repository's own lies over: the limits and the gate policy they
share.

{compact}
## Memory between sessions

Claude Code keeps notes between sessions in a folder outside this one, `~/.claude/projects/<project>/memory/`, where
`<project>` is made from this folder's path: a session started here keeps one memory for the whole folder, not one per
repository. It holds one file per fact and an index, `MEMORY.md`, with one line per file. When a session starts, only
the index is loaded, and only its first 200 lines or 25 KB, whichever comes first; the files themselves are read on
demand.

- **Keep the index under the cap.** One line per fact, never one per round. When a piece of work is finished, fold its
  rounds into one line that names the final state and the commit hashes, and move the detail into its own file. Past
  the cap, the newest lines are the ones a fresh session never sees.
- **Write the state before the closing reply.** The state of the work goes to memory before the reply that closes a
  round, so that a compaction or a fresh session at any moment finds it.
- **The repositories are the record; the memory is the working notes.** The memory folder is not part of any repository
  and is not backed up with them. A decision is durable only once it is in a repository's documents; a memory note
  points at that record, it does not replace it. Back the folder up to a private repository of your own (`bowline memory
  setup <remote>`), because the notes are personal: they hold how you work, your machines and your links.
