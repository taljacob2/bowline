---
name: init
description: Scaffold the repository's side of bowline's layout - the root CLAUDE.md's three sections, .claude/README.md, two starter rules, two starter skills, repository-local copies of the gate and the budget check, the pre-commit hook, .claude/bowline.json - file by file, with the person's yes, never overwriting. Use after the doctor on a repository that has none of it, or to add the parts it lacks.
---

# Scaffold the repository's side

A plugin cannot ship a `CLAUDE.md` or rules, so these files are written into the repository, where every contributor
and CI see them. `init` never overwrites: it creates what is missing and appends the sections a `CLAUDE.md` lacks.

## 1. Measure first

Run `/bowline:doctor` if it has not run in this session, so the person knows what is missing and why.

## 2. Show the plan

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" init --plan
```

It lists every item with its target path and what would happen: create, append sections, or kept. For each item the
person has not seen before, show them the text that would be written, read from `${CLAUDE_PLUGIN_ROOT}/templates/`:

- `claude-md`: `CLAUDE.md.sections.md` (the three sections) and, when the repository has no `CLAUDE.md`, `CLAUDE.md.head.md`.
- `claude-readme`: `claude-readme.md`.
- `rules`: `rules/before-a-commit.md`, `rules/recording-decisions.md`.
- `skills`: `skills/full-checks/SKILL.md`, `skills/push/SKILL.md` (starters with placeholders).
- `scripts`: copies of bowline's `gate.py`, `budget.py`, `common.py` and `defaults.json` into `.claude/scripts/`.
- `githook`: `githooks/pre-commit`.
- `config`: `bowline.json`.
- `gitignore`: the entries for a person's own Claude Code files.

Say in one sentence per item what it is for. Ask which items they want; the default is all of them.

## 3. Write

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" init --write --only <the items they chose, comma-separated>
```

or without `--only` for all. Then show `git status` so they see exactly what appeared.

## 4. Finish with them

- Fill the placeholders in `.claude/skills/full-checks/SKILL.md` and `.claude/skills/push/SKILL.md` with the
  repository's own commands; ask for them rather than guessing.
- Offer `git config core.hooksPath .githooks`, so git runs the gate on every commit, theirs included.
- If the repository's convention is ASCII only, or it accepts a few characters, set `gate.nonAscii` and
  `gate.acceptedCharacters` in `.claude/bowline.json`.
- Run `/bowline:doctor` again and show that the findings it fixed are gone.
- Suggest `/bowline:conventions` when the repository has no decisions section, no roadmap with slots and no notes queue.

Never edit an existing `CLAUDE.md` beyond appending the missing sections; what a repository already says is the
person's.

## From a folder of repositories

When the session runs in a folder that is not a repository but holds several, `init --plan` plans the folder's own
scaffold: `CLAUDE.md` from `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.folder.md`, an index with a table of the
repositories, what applies to every repository, the Compact Instructions and a memory section that says the memory is
one for the whole folder; and the shared `.claude/bowline.json`, the layer every repository's own lies over. Show the
template, write with `--write`, then fill the table with the person: a line for each repository and how they call one
another. `init --each --plan` plans the repository scaffold above in every repository of the folder, and
`init --each --write --only <items>` writes it; show the plan before writing into several repositories at once.
