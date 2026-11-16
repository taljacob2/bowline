## Where the rest of the rules are

This file stays short because Claude Code reads it whole at the start of every session. The rest is split by how it
loads. A rule for one part of the code is a file under `.claude/rules/`, scoped by path in its front matter, so it
loads only when a file it concerns is touched; a rule without a path loads at launch like this file. A procedure, such
as running the checks or pushing a round, is a skill under `.claude/skills/`, whose body loads only when it is used.
The long form of a rule, with its history and reasoning, is a page under `docs/conventions/`, read on demand. A nested
`CLAUDE.md` in a subfolder is an index that says where its part's rules, skills and pages are, under 200 lines, because
Claude Code cuts a nested file at a fixed size and never reads the rest unless asked. `.claude/README.md` explains the
folder and the sizes.

## Compact Instructions

Claude Code replaces a long conversation with a summary when the context nears its limit, and after about an hour of
quiet in a long session. This section tells that summary what it must keep, so that the next reply can carry on where
the work stopped. When you summarize this conversation, keep these, and prefer the exact words over a paraphrase:

- **The work in progress**: what is being built, in three parts: what is committed and pushed, with each commit's
  hash; what is built but not yet checked, naming the checks still to run; and what is only designed or agreed.
- **The user's decisions and open questions**: every decision made in this conversation, in the user's own words where
  they gave a rule, and every question still open to them, including anything that waits on them.
- **Rules about what must never be written**: every rule about what must never be documented, printed, logged or
  committed, word for word, and every check that must stop a commit or a push when it fails.
- **Standing requests about replies**: anything the user asked to see in every reply or at the end of every summary.
- **The files and programs still in use**: the exact path of every scratch script, recipe and plan note still needed,
  and every program, machine, port or background job the session started, saying which must be stopped.
- **The branch and the push recipe**, when they differ from what the memory folder describes.

## Memory between sessions

Claude Code keeps notes between sessions in a folder outside the repository, `~/.claude/projects/<project>/memory/`,
where `<project>` is made from the repository's path. Every worktree of this repository shares that one folder. It
holds one file per fact and an index, `MEMORY.md`, with one line per file. When a session starts, only the index is
loaded, and only its first 200 lines or 25 KB, whichever comes first; the files themselves are read on demand.

- **Keep the index under the cap.** One line per fact, never one per round. When a piece of work is finished, fold its
  rounds into one line that names the final state and the commit hashes, and move the detail into its own file. Past
  the cap, the newest lines are the ones a fresh session never sees.
- **Trim a note once the repository records its work.** A note is read whole whenever it looks relevant, so a note
  that keeps every finished round becomes a log that buries what is still open. When the repository records a
  finished piece of work, the note keeps a pointer to that record and its last commit, nothing more; the doctor
  warns when one note names many commits.
- **Write the state before the closing reply.** The state of the work goes to memory before the reply that closes a
  round, so that a compaction or a fresh session at any moment finds it.
- **The repository is the record; the memory is the working notes.** The memory folder is not part of the repository
  and is not backed up with it. A decision is durable only once it is in the repository's documents; a memory note
  points at that record, it does not replace it. Back the folder up to a private repository of your own (`bowline memory
  setup <remote>`), because the notes are personal: they hold how you work, your machines and your links.
