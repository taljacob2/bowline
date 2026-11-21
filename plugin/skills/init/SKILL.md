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
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" init --plan
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
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" init --write --only <the items they chose, comma-separated>
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
- Ask whether several Claude Code sessions work in the repository at the same time. If they do, suggest
  `/bowline:crew`: its last section writes the repository's settings and offers the rule about working beside other
  sessions. `init` writes neither, because only the person knows the repository's heavy checks, ports and lists.

Never edit an existing `CLAUDE.md` beyond appending the missing sections; what a repository already says is the
person's.

## From a folder of repositories

When the session runs in a folder that holds several repositories side by side, `init --plan` plans the folder's own
scaffold. What it offers depends on two things: whether bowline may write into the repositories, and whether the folder
is a git repository of its own.

Before the first plan, unless the folder's `.claude/bowline.json` already sets `writeToRepositories`, ask the person
once: may bowline write into the repositories, or should its files stay in this folder? They may have no write access,
or not want the repositories touched. If the files should stay here, plan and write with `init --leave-repositories`:
the folder's `.claude/bowline.json` gets `"writeToRepositories": false`, and a rule for one repository goes in
`.claude/rules/<repository>/` with `paths: ["<repository>/**"]`. A list of names in `writeToRepositories` lets bowline
write into those repositories only; `--each` skips the others and says so.

The items for the folder, each with the template to show from `${CLAUDE_PLUGIN_ROOT}/templates/`:

- `claude-md`: `CLAUDE.md.folder.md`, an index with a table of the repositories, what applies to every repository, the
  Compact Instructions and a memory section that says the memory is one for the whole folder. Each row of the table is
  filled from the repository's README, its package description, or the first sentence of its `CLAUDE.md` that
  describes it, never a warning, a rule or a list item; the plan says which rows came from where, and the rest wait
  for the person. `--no-describe` leaves every row for the person.
- `config`: the shared `.claude/bowline.json`, the layer every repository's own lies over.
- `claude-readme`, `rules`, `skills`: the folder's versions, `folder/claude-readme.md`, `folder/rules/` and
  `folder/skills/`, worded for a folder: a commit is made in a repository below it. Planned by default when the folder
  keeps the files of repositories bowline leaves untouched.
- `scripts` and `githook`: the copy of the gate and the budget check in `.claude/scripts/`, and `.githooks/pre-commit`,
  as for a repository. They need the folder to be a git repository, because a gate checks the commits made where it is
  installed; in a plain folder init refuses them and says so.
- `gitignore`: the entries for a person's own Claude Code files and one line per repository, so that the folder's own
  history never takes in a repository below it. Planned when the folder is a git repository.

Without the gate in the folder, the rules, skills and README say so in place of naming it: the bowline plugin's hook
still gates every commit Claude issues in a repository below, and a commit made outside Claude Code is not checked. The
plan marks those files "without the gate".

When the folder is not a git repository, the plan says what `git init` would add: the gate items and the `.gitignore`
entries. Offer it, so that the folder's files are versioned like any repository's: `git init` in the folder, then
`init --plan` again, and write the new items. A rule or a skill already written without the gate stays as it is; tell
the person to delete those files first if they want the version that names the gate, because init never overwrites.

Write with `--write --only <items>`, then fill the table with the person: a line for each repository still waiting,
and how the repositories call one another. `init --each --plan` plans the repository scaffold above in every repository
bowline may write into, and `init --each --write --only <items>` writes it; show the plan before writing into several
repositories at once. Tell the person the one limit: a session started inside a repository reads the folder's
`CLAUDE.md`, but not its skills.

The plan names at most ten repositories in a list and says how many more there are; `--verbose` lists them all.
