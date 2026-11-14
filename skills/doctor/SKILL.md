---
name: doctor
description: Measure this repository and this machine against what Claude Code actually reads - CLAUDE.md sizes and where a nested one is cut, the rules' and skills' budgets, the memory index and its backup, the compaction section, the commit gate - and read the report with the person. Use when asked whether the instructions are in good shape, when a CLAUDE.md feels ignored, or before init, curate-memory or split-instructions.
---

# The doctor

The doctor changes nothing. It measures and says, for each finding, what it found, why it matters and what to do.

## Run it

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" doctor
```

Add `--no-memory` when the memory folder is not this person's concern (CI, a shared machine). Add `--repo <path>` to
measure another repository.

## Read the report with the person

Go through the findings in order, worst first: PROBLEM, then WARNING, then NOTE. For each, say in one sentence what it
means for this repository, in plain words, and name the skill that fixes it:

- A `CLAUDE.md` over 200 lines, or a nested one cut at a line: `/bowline:split-instructions`. Say which sections are
  never read today; that is the fact that convinces.
- A rules file or an area over its budget: `/bowline:split-instructions` for the move, then shorten the rules.
- A path outside the repository in an instruction file: fix the pointer by hand; a contributor cannot follow it.
- No `Compact Instructions` or `Memory between sessions` section, no `.claude/bowline.json`, no gate: `/bowline:init`.
- The memory index near or over its cap: `/bowline:curate-memory`.
- The memory not backed up, or no hook pushing it: `/bowline:memory-backup`.

Then stop. Do not fix anything from this skill; each fix is its own skill with the person's yes. If the report is clean,
say so in one line and what the numbers were.

## What the numbers mean

The doctor prints which limits it used and the date they were checked against the Claude Code documentation. The
reasons are in `${CLAUDE_PLUGIN_ROOT}/docs/facts.md`; when the person asks why a limit is what it is, read the row
there and answer from it, never from memory.
