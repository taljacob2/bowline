# Before a commit, and before a push

These rules apply to every commit in a repository below this folder{and_folder}, whichever part it touches. The
`push` skill is the procedure that follows them.

{gate}
- **Keep the line endings and the encoding each repository uses** (LF, no byte-order mark, unless its
  `.claude/bowline.json`, or this folder's, says otherwise). A script that edits files keeps them; on Windows, Python
  opens files with `newline=''`, and PowerShell's `Set-Content` and `Out-File` are not used for files in a repository
  because they add a byte-order mark.
- **Fetch and rebase before every push**, with a clean tree, when more than one person or session pushes to the same
  branch. Never force-push a shared branch. Never `--autostash` where worktrees share one stash stack. After a rebase,
  re-read what the rebase merged: a rebase can succeed and still put two people's entries in the wrong order.
- **A commit message says why, what, and what was left out.** The context and the reason, what changed, every
  deliberate scope cut named as such, and what a check proved. A new runtime-state folder gets its `.gitignore` entry in
  the same commit.
- **Stage your own files by name.** Never `git add -A` in a tree another session may also be writing.
- **Run the checks that fit what changed before a push** (the `full-checks` skill names them), because a push that
  breaks the build costs everyone who pulls it.
