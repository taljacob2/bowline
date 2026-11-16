---
name: push
description: Commit a finished, verified piece of work in a repository below this folder and push it, with the gate and the checks it requires. Use when a round is done, or when the user says to push.
---

# Push a finished round

Follow the rules in `.claude/rules/before-a-commit.md`; this is the procedure. Every command below runs in the
repository you commit to: `cd <repository>` first. Replace `<branch>` with the branch that repository pushes to.

## 1. Run the checks that fit the change

The `full-checks` skill names them. Run the parts that cover what changed; when in doubt, run everything.

## 2. Stage and gate

Stage the files you changed by name. Then:

{gate}

## 3. Commit from a message file

Write the message to a file outside the repository and commit with `git commit -F <file>`, so quotes and backslashes
in the message survive the shell. The first line names what changed in plain words. The body gives the context and the
reason, what changed, every deliberate scope cut named as such, and what a check proved.

## 4. Push fast-forward

```
git fetch -q origin && (git merge-base --is-ancestor origin/<branch> HEAD || git pull -q --rebase origin <branch>) && git merge-base --is-ancestor origin/<branch> HEAD && git push -q origin HEAD:<branch>
```

The command refuses to push anything that is not a fast-forward of the remote branch. If the rebase changed what you
are pushing, run the checks again first. Never force.

## 5. Afterwards

Record the commit's hash where the work is tracked, and say in the reply what was verified and what was left out.
