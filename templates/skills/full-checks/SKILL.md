---
name: full-checks
description: Run every check this repository requires before a push, in the order that keeps them from colliding. Use before pushing, or when asked whether everything passes.
---

# The full checks

Fill in each part with the repository's own commands; delete the parts the repository does not have. A push comes only
after these pass (`.claude/rules/before-a-commit.md`).

## 1. The code

```
<the build command>
<the test command, over the whole project, never one module>
```

Say here what a flaky or long step means and what to do about it, so the next person does not guess.

## 2. The instruction files

```
python -I .claude/scripts/budget.py
```

Refuses when a `CLAUDE.md` has 200 lines or more, a rules file is over its size, an area's rules load more than their
budget together, a `SKILL.md` has 500 lines or more, or an instruction file names a path outside the repository.
`.claude/README.md` says why these sizes.

## 3. What tests cannot show

Name here the kinds of change that need a check against the running program, and how that check is done.
