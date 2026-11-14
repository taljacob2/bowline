---
name: push
description: Commit a finished, verified round of bowline and push it to main, with the gate and the checks. Use when a round is done, or when the user says to push.
---

# Push a finished round

Follow the rules in `.claude/rules/before-a-commit.md`; this is the procedure.

## 1. Run the checks

The `full-checks` skill: the tests, then bowline's own gate, budget and doctor.

## 2. Stage and gate

Stage the files you changed by name. Then:

```
python -I scripts/bowline.py gate
```

Exit code 0 lets you go on. Any hit stops here: fix the line, stage again, run again. Never commit past a hit.

## 3. Commit from a message file

Write the message to a file outside the repository and commit with `git commit -F <file>`. The first line names what
changed in plain words. The body gives the context and the reason, what changed, every deliberate scope cut named as
such, and what a check proved. Add a line to `CHANGELOG.md` under Unreleased when a command changed what it does.

## 4. Push fast-forward

```
git fetch -q origin && (git merge-base --is-ancestor origin/main HEAD || git pull -q --rebase origin main) && git merge-base --is-ancestor origin/main HEAD && git push -q origin HEAD:main
```

Never force. If the rebase changed what you are pushing, run the checks again first.

## 5. Afterwards

Say in the reply what was verified and what was left out, with the commit's hash.
