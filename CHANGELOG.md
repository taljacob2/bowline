# Changelog

Every version names the date its facts were last checked against the Claude Code documentation, because the limits
bowline measures against are Claude Code's, not bowline's. When a limit moves, `plugin/defaults.json` and
`plugin/docs/facts.md` change together and the entry here says which.

## 0.10.0 (2026-11-21)

The crew: several Claude Code sessions in one repository, each in its own worktree, without colliding. No Claude Code
limit moved. Three rows of `plugin/docs/facts.md` about hooks were read in the documentation on 2026-11-21, and two
were observed that day: the Write tool refuses a file that changed since it was read while the Edit tool keeps the
other changes, and each worktree has its own project folder. The reasoning is in `plugin/docs/decisions.md`, "the
crew".

- A new command, `bowline crew`. Alone it lists every worktree of the repository: its branch, its distance from the
  pushed branch, its uncommitted files, when a session last worked there, its processes that are heavy or listen on a
  port, the person's own ports as never to be stopped, the files changed in more than one worktree, the claims and
  the turn. It reads the machine's process list and its listening ports, and stores nothing of them.
- `crew claim <key>` takes a note, a file or a number for this worktree and refuses one another worktree holds, naming
  it; `crew claim <list> --new` takes one past the highest number of a numbered list in the pushed branch, in every
  worktree's copy of the file and in every claim; a key that starts with `waits:` says this worktree waits on
  another's push, and several may hold it; `crew release` gives claims back. The claims live in the repository's git
  folder, shared by its worktrees, never committed. A claim of a removed worktree, and a number that reached the
  pushed branch, are dropped.
- `crew run -- <command>` waits until no process on the machine matches the repository's heavy patterns and no other
  `crew run` holds the turn, runs the command and passes its exit code through; after `crew.waitMinutes` it names what
  still runs and exits with code 3 without running it. It never stops a process.
- `crew after-rebase` says when a number appears twice in a numbered list, when a number this worktree claimed
  reached the pushed branch, or when a stamp names a commit the branch no longer holds; `crew after-push` says who
  waits on this worktree. New hooks run them after a `git rebase`, `git pull` or `git push` that Claude issues, through
  the Bash or the PowerShell tool, and say nothing when there is nothing to say.
- The doctor warns about a number that appears twice and about a stale stamp, in a repository that names its lists and
  stamps. At a session's start it adds one line when another session worked in the repository in the last
  `crew.activeMinutes` minutes, in another worktree or in the same folder, from the times the transcript files were
  written, never their content.
- The memory backup's commits made by the hook name the session whose reply they follow ("Session: <id>"). The doctor
  warns when one session's commit removed lines that another session's commit had added within
  `crew.memoryLossHours` hours and no note holds them now, without quoting them; `bowline memory losses` lists them,
  and `--meant <commit>` records a removal that was meant.
- A new skill, `crew`, with the procedure and the three rules for a file the sessions share; a rule template for a
  repository where several sessions work, `templates/crew/beside-other-sessions.md`, which the skill offers and `init`
  does not write; a `crew` section in `defaults.json` with each key's reason, all of it empty or off until a
  repository fills it: `heavy`, `keepPorts`, `numbers`, `stamps`, `base`, `activeMinutes`, `waitMinutes`,
  `waitEverySeconds`, `memoryLossDays`, `memoryLossHours`.
- `plugin/PRIVACY.md` says what the crew reads and writes, and that the backup's commits now carry the session's
  identifier to your remote.

Not done in this version: a git `post-rewrite` hook for rebases made outside Claude Code, the commit gate's hook for
the PowerShell tool, claims across machines, and the session-start line from a folder of repositories (the decisions
page has them, numbered).

## 0.9.0 (2026-11-16)

A folder of many repositories: `init` installs the gate where it can and says so where it cannot, describes each
repository on purpose, and keeps its lists short; the doctor takes seconds, not minutes, and says a repeated finding
once. No Claude Code limit moved; the facts stay as checked on 2026-11-14. The reasoning is in
`plugin/docs/decisions.md`, "a folder of many repositories".

- `init` from a folder that is a git repository offers `scripts` and `githook`, installed as for a repository. From a
  plain folder it refuses them, and its plan says what `git init` would add: the gate and the `.gitignore` entries.
- The folder's rules, skills and `.claude/README.md` come from `templates/folder/`, worded for a folder, and name the
  folder's copy of the gate only when there is one; the plan marks the others "without the gate".
- Each row of the folder's table is described from the README, the package's description, or the opening of the
  `CLAUDE.md`, never a warning, a rule or a list item, in whole sentences; the plan says which rows came from where.
  New flag: `--no-describe`.
- The folder's `CLAUDE.md` has one blank line before "Memory between sessions", and its paragraphs that hold a filled
  sentence are re-wrapped.
- The doctor from a folder: the layout worked out once per run, three git processes per repository instead of eleven,
  eight repositories at a time, each printed as it completes, progress on standard error, a repeated finding said once
  with an `in:` line, no all-zero rules line. New flags: `--verbose` (every finding, size and name one by one) and
  `--folder-only`. Exit codes, `--brief` and the reminders are as before.
- Every list of repositories names ten and says how many more; `--verbose` names them all, in init and the doctor.

Not done in this version: the folder's table moving to a page past 200 lines, `budget`'s one line per repository, and a
plan that says which files written without the gate would now read differently (the decisions page has them).

## 0.8.1 (2026-11-16)

- The curate-memory skill's description names the doctor's new warning, a note that keeps finished work like a
  log, among the times to use it. Claude reads the description when it decides whether to offer a skill, and the
  doctor only reports: without the words, the warning pointed at a skill Claude had no reason to offer.

## 0.8.0 (2026-11-16)

The doctor watches the memory's notes, not only its index. No Claude Code limit moved:
`memoryNoteCommits` is bowline's own threshold, and the facts stay as checked on 2026-11-14.

- The doctor warns when a memory note names many commits, so that it keeps finished work like a log
  (`memoryNoteCommits`, 10 by default, a new setting), and points to `/bowline:curate-memory`. Before, it measured only
  the index, and the rule that keeps the index short moves the detail into the notes. `bowline memory status` lists
  every note with its lines, its bytes and the commits it names, the largest first. The memory rule in the templates
  gains one sentence: once the repository records a finished piece of work, the note keeps a pointer to that record
  and its last commit.

## 0.7.0 (2026-11-14)

A folder of repositories can keep bowline's files itself, and can be a git repository of its own.

- A new setting, `writeToRepositories`, read from the folder's `.claude/bowline.json`: `true`, the default and the
  behaviour so far; `false`, so that bowline writes nothing into the repositories under the folder, for repositories a
  person cannot or would rather not write into; or a list of the names it may write into. A repository's own file
  cannot change it. `init --leave-repositories` from the folder writes it as `false`.
- With the repositories left untouched: `init` from the folder writes the README, the starter rules and the skills into
  the folder as well, and its `CLAUDE.md` says that a rule for one repository goes in `.claude/rules/<repository>/`
  with `paths: ["<repository>/**"]`. `init --each` skips those repositories and says why; `init` run inside one refuses
  and points at the folder. `move run`, `pointers` and `place` refuse to write into them and change nothing, while
  `plan` and `--check` still work. Autosplit never starts there, and `autosplit run` refuses. The doctor still measures
  them, but as notes that say why bowline changes nothing and what the person can do: ask the owners, or keep what the
  folder needs in its own rules. So the line at a session's start never repeats a fix the person may not make.
- The folder can be a git repository of its own, which holds what its repositories share without tracking them:
  bowline sees a folder of repositories when a repository's top folder holds other repositories it does not track. A
  submodule is tracked, so it stays part of the repository. `init` there writes the `.gitignore` lines that keep the
  repositories out, the folder's `CLAUDE.md` says what kind of folder it is, the folder's own files get the doctor's
  checks of a repository (the gate, the configuration, autosplit), and the folder's `.claude/bowline.json` is the layer
  its repositories share, as for a plain folder.
- The messages that count repositories say "1 repository" rather than "1 repositories".
- `plugin/docs/facts.md` has two rows on how Claude Code loads a folder's rules and skills, with the documentation's
  words; `plugin/docs/decisions.md` says why the setting is the folder's and why a folder may be a repository.

## 0.6.2 (2026-11-14)

- bowline has a privacy policy, `plugin/PRIVACY.md`, and the manifest names it in `privacyPolicyUrl`, the field
  Anthropic's plugin directory reads; the directory warned that none was found. The page says who is behind bowline and
  that they receive nothing, what leaves the machine and only when the person turns it on (the memory backup to a git
  remote they name, autosplit's Claude Code session to Anthropic), what bowline reads and writes, the personal data the
  memory can hold, how long anything is kept, that it is not intended for anyone under 18, and where to ask. The URL
  follows the `release` branch, so it always shows the policy of the version the directory serves.
- The README's data section becomes "Privacy": a short summary of the two features and a link to the policy, so the
  full text lives in one place. The code is unchanged.

## 0.6.1 (2026-11-14)

- The plugin's README has a section, "What bowline reads, writes and sends", for the data-handling questions of
  Anthropic's plugin directory. It names the two features that send data off the machine, both off until a person turns
  them on: the memory backup, which pushes Claude Code's memory folder with git to a remote the person names, and
  autosplit, whose headless Claude Code session talks to Anthropic as any session does. It lists what bowline reads and
  writes, and says that nothing else is read, written or sent. The code is unchanged.

## 0.6.0 (2026-11-14)

What Anthropic's plugin directory asked when it validated 0.5.3: the validation passed, with three holds for a
reviewer, two warnings and several notes. This version answers the ones bowline can answer.

- The plugin is its own folder, `plugin/`, and the marketplace names it as the source (`"./plugin"`). The directory now
  sees only what ships. The instructions, rules and skills for working on bowline stay in `.claude/` at the
  repository's root, and the tests move to `tests/`; neither ships. This clears the note about files in a
  `.claude/skills` folder and the half of a hold that read the contributors' `CLAUDE.md` as code.
- The hooks name their program and arguments, as the directory asks: `node` with `scripts/run.mjs`, a small launcher
  that finds Python by the name the machine gives it (`python3`, `python` or `py -3`) and runs `scripts/bowline.py`,
  passing standard input, output and the exit code through. Claude Code's hooks documentation gives node with a script
  as the form that works on every system, because a hook given this way runs with no shell, and on Windows its program
  must be a real executable. The skills use the same launcher. This clears the eight notes that a hook named a plugin
  file as its program.
- The shell launchers in `bin/` are gone, which clears the note about files in `bin/`, which Claude Code adds to the
  PATH. Node.js is now a requirement beside Python and git, and the README says so.
- The changelog no longer names the icon's image file in code formatting, which held the plugin for review as if a
  text pointed a program at an image.
- The plugin's README, which the directory shows on the listing, no longer carries the clone-and-run lines it warned
  about. They are in the repository's new front page, `README.md` at the root, with the layout of the repository and
  the tests.
- For a person who installed 0.5.x: nothing to do. `claude plugin update bowline@bowline` installs the plugin from its
  new folder. In Anthropic's portal, the plugin's path is now `plugin`.

## 0.5.3 (2026-11-14)

- Anthropic's plugin directory can validate the repository. It refused with "Couldn't validate that repository",
  naming `.gitattributes` rules among the causes: the rule `*.cmd text eol=crlf` stored `bin/bowline.cmd` with LF and
  turned it into CRLF on every checkout and archive, so the files the directory received differed from what git
  stores. The launcher is now stored with CRLF and the rule is `*.cmd -text`, so git never converts it. What a person
  gets on disk is the same 629 bytes as before; every file of the repository now archives byte for byte as stored.

## 0.5.2 (2026-11-14)

- `claude plugin validate . --strict` passes, which Anthropic's plugin directory asks of a submission. It failed on one
  warning, "CLAUDE.md at the plugin root is not loaded as project context": the file is bowline's own instructions for
  people working on bowline, not context the plugin ships. It moved to `.claude/CLAUDE.md`, the other place Claude Code
  documents for a project's instructions, so contributors' sessions read it as before.
- The doctor, autosplit and init treat `.claude/CLAUDE.md` as a root file, like `CLAUDE.md`, in every repository they
  measure. The doctor no longer says such a repository has no root `CLAUDE.md`, checks the Compact Instructions and
  memory sections there, and never reports it as cut on demand. Autosplit never counts it as cut either. init appends
  the missing sections to it instead of creating a second file beside it, and a folder's table takes a repository's
  line from it. When both files exist, a section in either one counts. `docs/facts.md` has the row, with the
  documentation's words.

## 0.5.1 (2026-11-14)

- bowline has an icon: a bowline knot in off-white on a navy tile, made by the author with recraft.ai. A vector file is
  its source, and a 1024-pixel image with transparent corners is the file the manifest's `icon` field names for
  Anthropic's plugin directory. Claude Code itself does not show it.
- The README shows the icon at its top. On a page in dark mode GitHub shows a second vector file instead, the same knot
  with the two colours swapped, because the navy tile's edge fades into a dark page.

## 0.5.0 (2026-11-14)

- `init` from a folder of repositories scaffolds the folder itself: its own `CLAUDE.md` from `templates/CLAUDE.md.folder.md`,
  an index with a table of the repositories (a line for each, taken from its own `CLAUDE.md`), what applies to every
  repository, the Compact Instructions and a memory section that says the memory is one for the whole folder; and the
  shared `.claude/bowline.json`. `init --each` plans or writes the repository scaffold in every repository of the folder.
  Nothing that exists is overwritten, as before. The doctor's note for a folder without a `CLAUDE.md` points at it.
- The sweep after it, so that every capability works from the folder without a thought: `autosplit run`, `show`, `done`
  and `discard` take the repository from the file's path, as `move` does (`--file repo1/sub/CLAUDE.md`), and say so when
  a bare name is given from the folder; a move spec's index path is read from the repository when it is not found from
  the current folder; the doctor's header names the folder's shared config a repository lies over; the folder's
  CLAUDE.md template says how a rule for a few of the repositories is scoped; and the split-instructions, memory-backup,
  curate-memory (and its rubric) and conventions skills say what changes in a folder: paths from the folder and
  `--repo` where no file is given, one memory for the whole folder, promotions to the repository a note concerns or to
  the folder's own files for what spans them, conventions per repository or for the folder.

## 0.4.0 (2026-11-14)

- The gate hook finds the repository a commit names, from `git -C <path>` or `cd <path> &&` in the command, resolved
  from the hook's folder, so that a session started in a folder of several repositories is gated too. Before, from such
  a folder it exited with code 2, "not inside a git repository", and for a PreToolUse hook that code means block: every
  commit Claude issued there was refused. When the gate cannot tell which repository is meant, it now lets the command
  through and says nothing; it never blocks on its own confusion.
- A folder of repositories, as with services cloned side by side, is a place bowline works from. The doctor, the
  one-line finding at a session's start, the budget and the gate's plain mode measure the folder's own `CLAUDE.md` and
  every repository directly under it and name the repository in each finding; the memory is the folder's, keyed as
  Claude Code keys it; autosplit and the reminders run across the repositories, each split on a branch of its own
  repository; a `.claude/bowline.json` in the folder is the layer every repository shares, under its own. `move` takes
  the repository from the file it is given; `init` says to run it inside each repository. `docs/decisions.md` has the
  shape and what was left out: depths beyond one level, and a scaffold for the folder itself.
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
