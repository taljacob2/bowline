---
name: split-instructions
description: Move an oversized CLAUDE.md into long-form pages, scoped rules and a short index, without losing a line - move first, condense second, every pointer updated. Use when the doctor says a CLAUDE.md is over 200 lines or is cut at a line Claude Code never reads past.
---

# Split an oversized CLAUDE.md

Claude Code cuts a nested `CLAUDE.md` at a fixed size and never reads the rest unless asked, and a file over 200 lines
is applied less even before that. The fix is not to shorten the knowledge but to move each kind of it where the tool
loads it: the long form into pages read on demand, the rules into files scoped by path, the procedures into skills,
and a short index in the file's place. Two steps, two commits: the move is a pure move anyone can diff; the condensing
is reviewed against the page it came from.

## 1. Measure and propose

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" doctor
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" move plan --file <the CLAUDE.md>
```

The plan lists each `## ` section with its lines, its size and where the two cutoffs fall. Propose, section by section:
a long-form page under the repository's conventions folder (history, reasoning, dated entries), a scoped rule (an
imperative list that concerns one part of the code), a skill (a procedure: how to run, check, release), or the index
(what stays). Group sections into pages by subject, one page per few sections. Name the `paths:` glob of each rule's
area. Write the proposal as a table and ask the person; they know which sections they still rely on.

## 2. The move, as a spec

Write the approved proposal as a spec file (the shape is in `"${CLAUDE_PLUGIN_ROOT}/bin/bowline" move --help`), and the
new index as a Markdown file under 200 lines: what the folder is, what to read first, where its rules, skills and pages
are, its commands. Then:

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" move run --file <the CLAUDE.md> --spec <spec> --check
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" move run --file <the CLAUDE.md> --spec <spec>
```

`--check` prints every target with its size, the characters it will normalize (em dashes and the like, when the
repository's gate refuses them) and any section the spec forgot. Each page opens with a note saying where it came from
and that the short form is under the rules folder. Offer this as its own commit: the diff is a move.

## 3. Condense into rules

For each page, draft the rule file(s) from it. This needs judgment, so give it to a subagent per page with the brief in
`${CLAUDE_PLUGIN_ROOT}/skills/split-instructions/condense-brief.md`, filled in with the page, the area's glob, the
budget share and the repository's conventions folder. Each draft comes with a MAP: one row per entry of the page
saying whether it became a rule, stays in the page only, or was dropped and why (superseded later in the same page,
enforced by a named test or lint rule the subagent confirmed, or a one-off that is over). Review each draft against
its page: every imperative traceable, every named file or test real, nothing personal, nothing dated without a reason.
Trim to the area's budget; a dropped rule stays in the page.

Then `"${CLAUDE_PLUGIN_ROOT}/bin/bowline" budget` must pass, and the doctor must show the file as an index.

## 4. Update the pointers

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" move find-pointers --name <the old file's path>
```

lists every line in the repository that names it. For each that points at a moved section (a code comment, a doc, a
script's header), write a replacement in a pointers spec; a historical mention that merely says the file existed stays.
`move pointers --spec <file> --check`, then without `--check`. Each replacement must match exactly once.

## 5. Finish

Offer the second commit: the rules, the index, the pointers. Add a note at the top of each page naming the names that
have changed since the history was written, from what the subagents verified. Report what moved where, the budget's
numbers, and what the person should see in a fresh session: a `Loaded` line for the scoped rules when a file in the
area is touched, and no size warning in `/status`.
