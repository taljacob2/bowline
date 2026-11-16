# The `.claude` folder

This folder holds what Claude Code reads about the repositories below it, beyond their own `CLAUDE.md` files: what
applies to all of them, and what this folder needs about each one that bowline leaves untouched. Everything in it is
for every contributor; nothing in it is personal.

| Folder | What is in it | When Claude Code reads it |
|---|---|---|
| `rules/` | One rule per topic: an imperative with its one-sentence why. A file with a `paths:` list in its front matter is scoped and loads only when Claude touches a file that matches, such as `repo1/**` for one repository. A file without one loads at the start of every session started in this folder. | By path, or at launch |
| `skills/` | One procedure per folder, `SKILL.md` with reference files beside it: how to run the checks, how to push, how to do the recurring tasks. A session started inside one repository does not see them. | When you type `/name`, or when Claude judges it relevant |
{scripts_row}| `bowline.json` | The limits and gate policy every repository below shares, laid over bowline's defaults; a repository's own `.claude/bowline.json` lies over it. | By the checks |

Long explanations do not live here. A rule points to the page that holds its history and its reasoning, and a decision
is recorded in the design document of the repository it concerns.

## Sizes, and why they matter

Claude Code loads a nested `CLAUDE.md`, and a scoped rule, when a matching file is touched, and reads only the first
40,000 characters of it on a 200K context window (150,000 on a 1M window). Past that, Claude gets a note that it may
read the rest, and usually does not. So every `CLAUDE.md` stays under 200 lines, every rules file under 200 lines and
40,000 characters, the scoped rules that load together for one area under 40,000 characters in all, and the unscoped
rules, which every session loads, under 10,000 together. {budget}

## The commit gate

{gate}
