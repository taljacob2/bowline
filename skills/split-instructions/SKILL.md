---
name: split-instructions
description: Move an oversized CLAUDE.md into long-form pages, scoped rules and a short index, without losing a line - move first, condense second, every pointer updated. Use when the doctor says a CLAUDE.md is over 200 lines or is cut at a line Claude Code never reads past.
---

# Split an oversized CLAUDE.md

Claude Code cuts a nested `CLAUDE.md` at a fixed size and never reads the rest unless asked, and a file over 200 lines
is applied less even before that. The fix is not to shorten the knowledge but to move each kind of it where the tool
loads it: the long form into pages read on demand, the rules into files scoped by path, the procedures into skills,
and a short index in the file's place. Two steps, two commits: the move is a pure move anyone can diff; the condensing
is reviewed against the page it came from. When a repository turns `autosplit` on, a background worker runs these steps
on a branch of its own and the person's part is the review at the end; the last two sections say how.

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
Trim to the area's budget; a dropped rule stays in the page. Place the approved drafts with
`"${CLAUDE_PLUGIN_ROOT}/bin/bowline" move place --spec <json>` when the Write tool may not write under `.claude/`.

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

## Unattended: the background worker

When a repository sets `autosplit.enabled` in `.claude/bowline.json`, bowline's hook notices after a reply that a
`CLAUDE.md` is over the limits and starts a headless Claude Code session on a git worktree of its own, branched from the
committed HEAD, with this skill as the procedure and no person to ask. That session follows steps 1 to 5 with these
differences:

- **Decide the proposal yourself, by the kind of each section.** A section of dated entries, history or reasoning
  becomes a long-form page under the conventions folder. A section that is a list of imperatives about one part of the
  code becomes a scoped rule whose glob is the folder the file sits in (`<folder>/**`), or, for the root file, the
  folder the section names. A section that is a procedure becomes a skill. The commands, the pointers to where things
  are and what to read first stay in the index. A section that fits two kinds becomes a page, and the rule is condensed
  from it. Write the proposal as the table step 1 describes into the message of the first commit, since there is no
  one to show it to.
- **Scratch stays in the worktree, and the move tool places the drafts.** The condensing subagents write their drafts
  under `.bowline-scratch/` in the working folder. An unattended session cannot write under `.claude/` itself: Claude
  Code treats those files as sensitive and only a person may approve the edit. So place the finished rule files, any
  new skill and the index with `move place --spec <json>`, a list of `{"source": <draft>, "target": <file>}`
  entries, `--check` first; it is the tool that wrote the moved rules in step 2. Remove the scratch folder with
  `git clean -fdx -- .bowline-scratch` before the second commit.
- **The second commit's message holds the review.** For each page, its MAP as the subagent returned it, and the list of
  what could not be verified, so that the person reviews the condensing from the commit.
- **Two commits and nothing else.** The move, then the rules, the index and the pointers. Run bowline's `gate` before
  each commit and `budget` before the second. Finish with a clean tree. Never push, never ask, never touch anything
  outside the working folder. The worker that started the session checks the result, removes the worktree, keeps the
  branch and reports through the doctor.

## Review a split made in the background

The doctor, and the one-line finding at a session's start, say when a split is ready: "A split of <file> is ready on
the branch bowline/split/<name>". Then, with the person:

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" autosplit show --file <the CLAUDE.md>
```

prints the branch, its two commits with their messages (the proposal and the MAPs), the files it adds and changes, and
the file's size before and after. Read the proposal with the person, then the rules against their pages as step 3 says,
from the diff. When they say yes, take the two commits onto the current branch and forget the split:

```
git cherry-pick <base>..bowline/split/<name>
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" autosplit done --file <the CLAUDE.md>
```

`show` prints both commands with the real names. A cherry-pick that conflicts means the file changed since the split
was made: resolve it by hand, or `git cherry-pick --abort` and `autosplit discard --file <the CLAUDE.md>`, after which
autosplit prepares a fresh one after the next reply. When the person does not want the split, `discard` deletes the
branch and the record. A failed split says why in the doctor and keeps its log under the repository's `.git` folder;
read the log with the person, then split by hand with the steps above, or `discard` to let autosplit try again.
