# Changelog

Every version names the date its facts were last checked against the Claude Code documentation, because the limits
bowline measures against are Claude Code's, not bowline's. When a limit moves, `defaults.json` and `docs/facts.md`
change together and the entry here says which.

## Unreleased

- A `release` skill under `.claude/skills/`: the checks, the version in the plugin manifest (the only thing Claude Code
  reads to decide that an update exists), the changelog heading, `claude plugin validate`, one commit, the push to main,
  a plain `X.Y.Z` tag and the proof on this machine. `docs/decisions.md` says why the tag is plain and not the
  `bowline--vX.Y.Z` that `claude plugin tag` makes.

## 0.3.0 (2026-11-14)

`autosplit`: when a repository turns it on, bowline prepares the split of a `CLAUDE.md` that outgrew the limits in the
background, on a branch of its own, and the person reviews and merges.

- Why: the first user asked for the split to happen the way autocompact happens, noticed and done in the background of
  their work. A `CLAUDE.md` is every future session's input, so the result waits on a branch rather than landing
  unasked; `docs/decisions.md` has the reasoning.
- `autosplit --hook` runs from the plugin's Stop and SessionEnd hooks: when `autosplit.enabled` is set in
  `.claude/bowline.json` and a `CLAUDE.md` is over the limits, committed and clean, it starts a detached worker. The
  worker adds a git worktree on the branch `bowline/split/<file>` from the committed HEAD, runs a headless Claude Code
  session there (`-p`, `acceptEdits`, `--permission-prompts none`, an allowlist of tools, `--max-budget-usd`, a time
  limit, the parent session's marks removed from the environment) with the unattended procedure of the
  split-instructions skill, checks the result (a clean tree, the file under the line target, the budget passing),
  removes the worktree, keeps the branch and records the outcome under the repository's `.git/bowline/autosplit/`,
  beside the session's log.
- The doctor, in full and in brief, says when a split is ready, running or failed, and why one has not started (an
  uncommitted file, a missing command, a branch that exists); a ready split points the file's own finding at the review.
- `autosplit run` does the same work now, in the foreground; `status`; `show` prints the commits with the proposal and
  the MAPs and the cherry-pick that takes them; `done` after the merge; `discard` for a split not wanted, or to try
  again.
- The split-instructions skill gains the unattended procedure and the review; `defaults.json` gains the `autosplit`
  settings with their reasons (off by default, `claude` as the command, 20 dollars, 60 minutes); the template
  `.claude/bowline.json` shows the switch; the guide, the comparison, the facts and the migrating page say what changed.
- `move place --spec` copies finished drafts from a scratch folder into instruction files only (a rule, a skill, a page,
  a CLAUDE.md), normalized as `move run` normalizes. The unattended procedure places the condensed rules and the index
  with it, because an unattended session cannot write under `.claude/` itself: Claude Code treats that as a
  sensitive-file edit that only a person may approve, which the first live run found (`docs/facts.md` has the row, and
  `docs/decisions.md` says why the worker was not given `bypassPermissions` instead).
- Reminders during a session. The doctor's `--watch` runs from the Stop hook after every reply: it measures again and,
  when a finding appears that was not there before (a `CLAUDE.md` that crossed the line target, a rules area over its
  budget, the memory index at its cap), shows the person one line in the doctor's words, once, not again as the file
  keeps growing. `--pending` runs from a new UserPromptSubmit hook and hands the same line to Claude at the next
  prompt, so "do it" means something. `--brief` records what it said at the session's start, so nothing is said twice.
  The record is `<git dir>/bowline/watch.json`.
- `autosplit.deliver` chooses how the result arrives: `branch` (the default) leaves the two commits for the person to
  review and cherry-pick; `merge` has the worker cherry-pick them onto the current branch as soon as they are ready,
  only onto a clean tree and only when they apply without a conflict, and the doctor says what landed until `done`.
  `docs/decisions.md` says why branch is the default.
- The tests run the worker against a stand-in for the `claude` command (`scripts/tests/fake_claude.py`), so the suite
  starts no session. That a headless session starts from inside another session's hook environment and returns the JSON
  result was checked by hand on Windows, with a ten-cent cap.
- What that check also found: Claude Code runs a shell-form hook in Git Bash on Windows and falls back to PowerShell
  when it does not find Git Bash, and there bowline's quoted-path hooks are a parse error (`docs/facts.md` has the
  row). The worker therefore hands the session it starts the path of Git for Windows' bash through
  `CLAUDE_CODE_GIT_BASH_PATH` when nothing names one. The hook claims a split by creating its record exclusively, so
  two hooks firing at once cannot start two workers.
- The live check, on a clone of the first user's repository with the line target lowered so that the docs site's
  `CLAUDE.md` (199 lines) counted as oversized, with Sonnet and a ten-dollar cap: the first run stopped at the
  sensitive-file refusal and was reported as failed with its branch and first commit kept; after `move place`, the
  second run finished in four minutes for 1.84 dollars: two commits, 199 lines to 52, four pages, four scoped rules,
  one pointer updated, the proposal and the MAPs in the commit messages, the budget passing, the worktree gone, and
  the doctor's one line saying the split was ready.

## 0.2.0 (2026-11-14)

The plugin is renamed from keel to bowline, hours after 0.1.1. Nothing else changes.

- Why: "keel" turned out to be the name of an official Claude connector (a trading-strategy backtester on claude.com's
  marketplace) and of at least five other Claude Code plugins, one of which already answers to `/keel:` commands.
  Anthropic's directory needs a unique plugin name and makes it permanent, so the name changed before anyone depended
  on it. A bowline is the sailor's knot that holds fast under load and still comes undone by hand.
- What changes for a person who installed 0.1.x: remove the old plugin and its marketplace, then add the new one:
  `claude plugin uninstall keel@keel`, `claude plugin marketplace remove keel`,
  `claude plugin marketplace add taljacob2/bowline`, `claude plugin install bowline@bowline`. The skills are
  `/bowline:doctor` and so on. A repository's configuration file is `.claude/bowline.json` (rename `.claude/keel.json`),
  the launchers are `bin/bowline` and `bin/bowline.cmd`, and the entry point is `scripts/bowline.py`. The repository
  `taljacob2/keel` redirects to `taljacob2/bowline`.
- The entries below keep the old name, because those versions carried it.

## 0.1.1 (2026-11-14)

What the first run of the tests on three systems found, hours after 0.1.0:

- `move` built the "moved from" path from the file's path as given; on macOS the temp folder sits behind a symlink and
  on a Windows runner behind a short name, so the relative path was wrong. Both sides are real paths now.
- The tests named the memory folder from the scratch folder's path as given, while the scripts name it from what git
  reports; the scratch folder is a real path now, as git sees it.
- `.gitattributes` checks every text file out with LF on every system, so the gate's carriage-return rule means the same
  thing everywhere; `*.cmd` keeps CRLF, as cmd expects.
- That CRLF checkout made the gate's own sweep refuse every line of the Windows launcher on the three runners, while
  the LF copy on the development machine passed. The carriage-return rule now skips the files `gate.crlfFiles` names,
  by default `*.cmd` and `*.bat`, and a test stages one file of each kind.
- CI runs Python 3.8 on the Windows and macOS runners and 3.11 on Linux, whose image no longer offers 3.8.

## 0.1.0 (2026-11-14)

The first version, extracted from the knowledge work done in one repository over two days and proven on a second.
Facts checked against the Claude Code documentation on 2026-11-14 (`docs/facts.md`).

- `doctor`: measures a repository's instruction files against what Claude Code reads, the memory folder against its
  index cap and its backup, and the repository against the layout; three lines per finding.
- `gate`: refuses a commit whose staged lines hold a token, a control byte, a carriage return, a byte-order mark, a
  character outside the accepted set when the policy says so, or a word from a private never-commit list.
- `budget`: refuses an instruction file over the sizes Claude Code reads, or one that names a path outside the
  repository.
- `memory`: `setup <remote>` makes the memory folder a git repository tied to a private remote (clones on a new
  machine, pushes a first backup when the remote is empty, refuses when both hold content) and installs the push hook
  for this machine; `status`, `restore`, `push`.
- `init`: scaffolds the repository's side, file by file, never overwriting: the root CLAUDE.md's three sections,
  `.claude/README.md`, two starter rules, two starter skills, repository-local copies of the gate and the budget check,
  the pre-commit hook, `.claude/keel.json` and the `.gitignore` entries.
- The `bin/keel` and `bin/keel.cmd` launchers, the plugin's `hooks/hooks.json` (the memory push after every reply, the
  gate before a `git commit`), and tests on Windows and Linux in CI (macOS by hand while the repository is private).
- `move`: `plan` lists a CLAUDE.md's sections with where Claude Code's cutoffs fall; `run --spec` moves named sections
  verbatim into pages and rules (normalizing only the characters a gate refuses, counted) and writes the index;
  `find-pointers` and `pointers --spec` update every mention, each matched exactly once.
- The six skills the plugin ships: `doctor`, `init`, `memory-backup`, `curate-memory` (with its rubric),
  `split-instructions` (with the brief for the condensing subagents) and `conventions` (with its templates); the guide's
  `docs/conventions.md` and `docs/migrating.md`.
- The plugin manifest and a one-plugin marketplace, so `claude plugin marketplace add taljacob2/keel` and
  `claude plugin install keel@keel` work; `doctor --brief` and the SessionStart hook that runs it, so a session learns
  in one line when something is over budget or unbacked, and hears nothing when all is well.
- The guide (`docs/guide.md`: the problem in a page, the three homes, the budgets, the four flows drawn) and the
  comparison (`docs/compared.md`).
