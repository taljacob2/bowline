---
name: full-checks
description: Run every check a repository below this folder requires before a push, in the order that keeps them from colliding. Use before pushing, or when asked whether everything passes.
---

# The full checks

Fill in each part with each repository's own commands, under its name; delete the parts no repository has. A push
comes only after these pass (`.claude/rules/before-a-commit.md`). Run a repository's commands in that repository.

## 1. The code

```
<the repository>: <the build command>
<the repository>: <the test command, over the whole project, never one module>
```

Say here what a flaky or long step means and what to do about it, so the next person does not guess.

## 2. The instruction files

{budget}

## 3. What tests cannot show

Name here the kinds of change that need a check against the running program, and how that check is done.
