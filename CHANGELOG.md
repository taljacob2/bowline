# Changelog

Every version names the date its facts were last checked against the Claude Code documentation, because the limits
keel measures against are Claude Code's, not keel's. When a limit moves, `defaults.json` and `docs/facts.md` change
together and the entry here says which.

## Unreleased

Facts checked against the Claude Code documentation on 2026-11-14 (`docs/facts.md`).

- `doctor`: measures a repository's instruction files against what Claude Code reads, the memory folder against its
  index cap and its backup, and the repository against the layout; three lines per finding.
- `gate`: refuses a commit whose staged lines hold a token, a control byte, a carriage return, a byte-order mark, a
  character outside the accepted set when the policy says so, or a word from a private never-commit list.
- `budget`: refuses an instruction file over the sizes Claude Code reads, or one that names a path outside the
  repository.
