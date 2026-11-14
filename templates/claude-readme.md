# The `.claude` folder

This folder holds what Claude Code reads about the repository beyond the `CLAUDE.md` files, and the small checks the
project's working rules depend on. Everything in it is for every contributor; nothing in it is personal.

| Folder | What is in it | When Claude Code reads it |
|---|---|---|
| `rules/` | One rule per topic: an imperative with its one-sentence why. A file with a `paths:` list in its front matter is scoped and loads only when Claude touches a file that matches. A file without one loads at the start of every session, like the root `CLAUDE.md`. | By path, or at launch |
| `skills/` | One procedure per folder, `SKILL.md` with reference files beside it: how to run the checks, how to push, how to do the project's own recurring tasks. | When you type `/name`, or when Claude judges it relevant |
| `scripts/` | The checks the rules name: the commit gate (`gate.py`) and the size budget of the instruction files (`budget.py`), repository-local copies of keel's, so CI and a contributor without the plugin run the same checks. | Run by the skills, the pre-commit hook and CI |
| `keel.json` | The repository's own limits and gate policy, laid over keel's defaults, so every contributor measures against the same numbers. | By the checks |

Long explanations do not live here. A rule points to the page under `docs/conventions/` that holds its history and its
reasoning, and a decision is recorded in the project's design document.

## Sizes, and why they matter

Claude Code loads a nested `CLAUDE.md`, and a scoped rule, when a matching file is touched, and reads only the first
40,000 characters of it on a 200K context window (150,000 on a 1M window). Past that, Claude gets a note that it may
read the rest, and usually does not. So every `CLAUDE.md` stays under 200 lines, every rules file under 200 lines and
40,000 characters, the scoped rules that load together for one area under 40,000 characters in all, and the unscoped
rules, which every session loads, under 10,000 together. `scripts/budget.py` checks these; `keel doctor` explains
each finding.

## The commit gate

`scripts/gate.py` reads the staged diff and refuses a commit whose added lines hold a token, a control byte, a
carriage return, a byte-order mark, a character outside the accepted set when `keel.json` says so, or a word from a
private list at `~/.claude/private/never-commit.txt` when that file exists. To have git run it on its own, once:

```
git config core.hooksPath .githooks
```
