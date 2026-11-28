---
name: doctor
description: Measure this repository and this machine against what Claude Code actually reads - CLAUDE.md sizes and where a nested one is cut, the rules' and skills' budgets, the memory index, its notes and its backup, the compaction section, the commit gate - and read the report with the person. Use when asked whether the instructions are in good shape, when a CLAUDE.md feels ignored, or before init, curate-memory or split-instructions.
---

# The doctor

The doctor changes nothing. It measures and says, for each finding, what it found, why it matters and what to do.
The one line at a session's start, and a reminder during a session when something crosses a limit, are the same
findings in short; this skill is the full report. From a folder of repositories, each finding starts with the
repository's name, and the memory finding is the folder's.

## Run it

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" doctor
```

Add `--no-memory` when the memory folder is not this person's concern (CI, a shared machine). Add `--repo <path>` to
measure another repository.

From a folder of many repositories, the doctor measures eight at a time and prints each repository's sizes as it is
measured, with progress on standard error; let it finish rather than move it to the background. A finding found the
same in several repositories is printed once, with an `in:` line naming them; read it with the person as one finding.
`--verbose` prints every finding, every repository's sizes and every name; `--folder-only` measures the folder itself
and stops, for a quick check.

## Read the report with the person

Go through the findings in order, worst first: PROBLEM, then WARNING, then NOTE. For each, say in one sentence what it
means for this repository, in plain words, and name the skill that fixes it:

- A `CLAUDE.md` over 200 lines, or a nested one cut at a line: `/bowline:split-instructions`. Say which sections are
  never read today; that is the fact that convinces. While autosplit is off, the fix also offers it, with what one
  split may spend. Say the cost when you pass the offer on, and leave the choice to the person: it is their money.
- A rules file or an area over its budget: `/bowline:split-instructions` for the move, then shorten the rules.
- A path outside the repository in an instruction file: fix the pointer by hand; a contributor cannot follow it.
- No `Compact Instructions` or `Memory between sessions` section, no `.claude/bowline.json`, no gate: `/bowline:init`.
- The memory index near or over its cap: `/bowline:curate-memory`.
- A memory note that names many commits, so it keeps finished work like a log: `/bowline:curate-memory`, whose
  TRIM verdict cuts each finished item the repository records down to a pointer and its last commit.
- The memory not backed up, or no hook pushing it: `/bowline:memory-backup`.
- The memory's backup behind: run `bowline memory push` with the person's word, and read what it says. When it pushed,
  look again after the next reply: a change that waits again means that the hook does not back this folder up. When
  the push failed, what git said is the reason, such as a remote that is gone or a sign-in that ended.
- A split that autosplit prepared in the background, ready on its branch: `/bowline:split-instructions review <file>`.
  One that failed: read its log with the person, then `/bowline:split-instructions` by hand, or
  `bowline autosplit discard --file <file>` to let autosplit try again. One that stopped without recording how it
  ended (its worker is gone): the same, and `discard` also removes the worktree it left. One that autosplit merged
  on its own (the repository sets `deliver` to `merge`): read what landed with
  `bowline autosplit show --file <file>`, then `bowline autosplit done --file <file>`.

Then stop. Do not fix anything from this skill; each fix is its own skill with the person's yes. If the report is clean,
say so in one line and what the numbers were.

## What the numbers mean

The doctor prints which limits it used and the date they were checked against the Claude Code documentation. The
reasons are in `${CLAUDE_PLUGIN_ROOT}/docs/facts.md`; when the person asks why a limit is what it is, read the row
there and answer from it, never from memory.
