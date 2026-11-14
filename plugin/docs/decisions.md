# Decisions

Where a design question of bowline settled, with the reasoning, recorded in the round it settled, as the
`recording-decisions` rule asks. The newest entry is last.

## 2026-11-14: autosplit prepares the split on a branch; the merge stays a person's

**The question.** Should bowline notice that a `CLAUDE.md` has outgrown the limits and split it on its own, in the
background, the way Claude Code's autocompact summarizes a conversation when its context fills? The plugin's first user
asked for exactly that: recognize when it is time to reorder, as autocompact does, and just do it in the background of
their work.

**The decision.** Yes to the trigger and to the background work, no to landing the result unasked. With
`autosplit.enabled` set in a repository's `.claude/bowline.json`, the hook that already runs after every reply measures
the `CLAUDE.md` files the way the doctor does, and when one is over the limits and committed clean it starts a worker.
The worker makes a git worktree on a new branch from the committed HEAD, runs a headless Claude Code session there with
the unattended procedure of the split-instructions skill, checks the result, removes the worktree and keeps the branch.
The doctor and the session-start finding say that the split is ready, and the person reviews the proposal and the MAP
from the two commits and cherry-picks them.

**Why the merge is not automatic.** Autocompact can rewrite a conversation's context unasked because that context is
nobody else's input, and a bad summary costs one conversation. A `CLAUDE.md` is every future session's input, and the
condensing step drops lines by judgment. bowline's own guide says that a tool rewriting the rules you work from in the
background is the one thing it exists to prevent, and its skill says that the condensed rule is reviewed against its
page. The branch keeps both true while the work itself happens unattended: nothing on the person's branch changes until
they say so, and what they review is a diff with its reasoning in the commit messages, not a conversation. A person's
uncommitted edits to the same file would also make an automatic merge conflict at a moment they did not choose.

**Why a headless session and not a script.** The move itself is a script (`bowline move run`), but deciding which
section becomes a page, a rule or a skill, condensing a page into rules and sorting the pointers need judgment. The
headless session runs with `--permission-prompts none`, so anything that would ask a person is denied, with an allowlist
of tools, a cost cap (`--max-budget-usd`) and a time limit, in a worktree under the system's temp folder, so that the
person's tree, their uncommitted work and their open session are never touched.

**Why it is off by default.** A background worker spends tokens and makes a branch. Each repository opts in, in a file
every contributor sees, and a contributor who installs the plugin for another repository gets nothing they did not ask
for.

**The two ways to deliver, and the default.** `deliver: branch`, the default, leaves the two commits on their branch
for the person to review and cherry-pick. `deliver: merge` has the worker cherry-pick them onto the person's current
branch itself as soon as they are ready, with three safeguards: only when the working tree is clean, only when the
cherry-pick applies without a conflict (otherwise the split stays on its branch and the doctor says why), and never a
push; the doctor then says what landed until the person acknowledges it with `done`. The default is branch because
the condensing drops lines by judgment, and an unreviewed change to the instructions is the one thing bowline exists to
prevent. merge exists because the first user asked that every option be there for the person to choose, with a
default chosen for them, and a repository that wants the autocompact feel to the end can say so in the open, in a file
every contributor sees. Not chosen: running the worker at a session's start, which would make the person wait, where
the hook after a reply starts it while they work; and keeping the worktree under the repository, which would show up
as an untracked folder in their tree.

Also not chosen, after the first live run: giving the worker's session `bypassPermissions` so that it could write the
rule files itself. The run showed that Claude Code treats an edit under `.claude/` as a sensitive-file edit that only a
person may approve, even with an allow rule for the path, so the session that had moved the pages and drafted the
rules could not place them. The oversight layer of the session that built autosplit refused to start a nested session
with every permission check bypassed, and the refusal was right: an unattended session with no checks at all is a wider
grant than the work needs. Instead the move tool, which already writes the moved rule files from a spec, places the
condensed drafts too (`move place`), and the model never edits under `.claude/` in its own session. What a person
reviews on the branch is the same either way.

## 2026-11-14: a release is the version field; the tag is a plain version number

**The question.** How does a version of bowline reach the people who installed it, and what should its git tag be
called? `claude plugin tag` makes tags of the form `bowline--v0.4.0`; the four tags so far are `0.1.0` to `0.3.0`.

**The decision.** The release is the `version` field in `.claude-plugin/plugin.json`: Claude Code computes a plugin's
version from it and replaces an installed copy only when it differs, so a commit pushed without changing it reaches
nobody, and no tag or GitHub release is read at all. The tag stays a plain `X.Y.Z`. The first user's words: the
prefixed form "feels dirty"; "why not 0.4.0". The reasoning behind the feeling: one plugin lives in this repository, and
the repository's name already says which, so the prefix would repeat it; the tag is read by people, not by Claude Code;
and the four tags that exist are plain. The procedure is the `release` skill under `.claude/skills/`.

**Not chosen.** `claude plugin tag`, which also validates the manifests, because its tag name cannot be changed;
`claude plugin validate .` gives the same check inside the skill. Pinning the marketplace entry to a tag with `ref`,
which would make a stable channel: not wanted while every version is meant to be the one people run.

## 2026-11-14: a folder of repositories is one place with several repositories in it

**The question.** The first user keeps services as repositories cloned side by side under one folder and starts
Claude Code in that folder. bowline assumed a single repository: from such a folder every command stopped at "not
inside a git repository", and the gate's hook, exiting with code 2 there, blocked every commit Claude issued.

**The decision.** The folder is a place bowline works from, with the shape Claude Code's own loading gives it: the
folder's own CLAUDE.md is the root that loads whole, each repository directly under it is measured on its own and named
in every finding, the memory is the folder's one memory as Claude Code keeps it, and a .claude/bowline.json in the
folder is the layer every repository shares, under its own. Autosplit runs per repository, on a branch of that
repository. The gate's hook works out which repository a commit names and, when it cannot, lets the command through: a
hook that blocks on its own confusion costs more than the check it skips, and git refuses a commit outside a repository
anyway.

**Not chosen.** Looking deeper than one level: a repository inside a repository is that repository's business, and a
folder of folders of repositories is rare enough to wait for someone who has one. Scaffolding the folder itself with
init was left out at first and asked for the same day: `init` from the folder now writes the folder's own CLAUDE.md,
an index of the repositories with a table (a line for each, taken from its own CLAUDE.md), what applies to every
repository, the Compact Instructions and a memory section that says the memory is one for the whole folder, plus the
shared .claude/bowline.json; `init --each` scaffolds every repository. The depth stays at one level.

## 2026-11-14: Anthropic's plugin directory follows a release branch, not main

**The question.** The first user is submitting bowline to Anthropic's plugin directory. After the first submission, the
directory follows one branch or tag of the repository, by default the default branch, and takes every new commit there
as a candidate version: it checks and scans each one and, by default, has an Anthropic reviewer publish it. Which ref
should it follow?

**The decision.** A branch named `release`, which moves only at the end of a release, to the commit the version's tag
names (step 5 of the `release` skill). The directory then sees exactly the released versions. bowline's own marketplace
keeps following main, as before, because Claude Code installs only when the `version` field changes, so a commit
between releases reaches nobody there. The first user agreed to the release branch when it was proposed.

**Why not main.** Several sessions push work to main between releases, a commit per finished round, and the release is
a separate commit that changes the version. Followed on main, every one of those commits would queue the directory's
checks and, under the default setting, a reviewer, and a version could go live in the directory before its release.

**Why not a tag.** The tags are one per version and never move. A directory that followed a tag would need its setting
changed in the portal at every release, or a moving tag such as `stable`, which reads like a version and confuses the
plain version tags. A branch that only moves forward says what it is, and git itself refuses a push that would move it
backward.

## 2026-11-14: the plugin is its own folder, and its hooks start node

**The question.** Anthropic's plugin directory validated bowline 0.5.3 and passed it, with holds for a reviewer and
notes about what a later release of the directory may refuse. Some came from files that do not ship to anyone: the
contributors' instructions under .claude/ and the tests. Others came from how the hooks were written: one line of text
whose program was a shell script of the plugin, which the directory asks to see as a named program with its arguments.

**The decision.** The plugin is the folder plugin/, and the marketplace entry names it as the source. What is for
working on bowline, the .claude/ folder, the tests, CI and the marketplace file, stays outside it, so the directory
reads only what a person installs. The hooks are written as a program and its arguments: node, with scripts/run.mjs,
which finds Python and runs scripts/bowline.py. The skills use the same launcher, and the shell launchers in bin/ are
gone, so there is one way in.

**Why node.** A hook written as a program and arguments runs with no shell, and on Windows its program must be a real
executable. Python has no name that works on every system: Windows usually has python and the py launcher, macOS and
Linux have python3, and on Windows a missing Python can still answer to python3 as the Microsoft Store's placeholder.
Claude Code's hooks documentation gives node with a script as the form that works on every system, and the directory
names it too. The cost is a second requirement, Node.js, beside Python; the README says so, and a machine without node
gets hooks that fail to start rather than ones that block anything.

**Not chosen.** Keeping one-line hooks through a shell: they work today, in Git Bash on Windows, but the directory
notes them and may refuse them later, and without Git Bash Claude Code runs them in PowerShell, which cannot start the
shell launcher. Naming python3 or python as the program: each fails on one family of systems. Rewriting bowline in
JavaScript so that node alone would do: a larger change than the problem.

**What it does not change.** The directory says that later it will accept command hooks, scripts and files outside a
short list of types only from Verified organizations, which Anthropic chooses, with no way to apply yet. bowline is
hooks that run scripts, so that rule, when it comes, applies to it whatever its layout. bowline's own marketplace is
not affected by any of the directory's rules.

## 2026-11-14: a folder may keep bowline's files itself, and may be a git repository of its own

**The question.** The first user works from a folder that holds several repositories side by side, and asked for a
second way to use bowline there: with every file bowline writes kept in the folder, because a person may have no write
access to the repositories, or may not want them touched. How is that chosen, and where are the folder's files kept?

**The decision.** A setting, `writeToRepositories`, in the folder's own `.claude/bowline.json`: true by default, which
is how bowline worked until now; false, so that nothing is written into the repositories; or a list of the names
bowline may write into, for a person who owns some of them. Only the folder's file counts, because the choice belongs
to the person who works from the folder, and a repository someone else owns must not be able to grant itself writes.
Where it is false, everything that writes into a repository refuses and says why: init with --each, move, and
autosplit, whose split is a branch in the repository. The doctor still measures those repositories, but every finding
about them is a note that says why bowline changes nothing and what the person can do instead, because a fix the person
may not make should not repeat at the start of every session. What the folder needs about a repository lives in the
folder's own rules, scoped to that repository's files: Claude Code documents a rule's patterns as relative to the
folder that holds its .claude folder, so a rule there with paths repo1/** applies to repo1's files.

**The folder as a repository.** The first user agreed that the folder may be a git repository of its own, because a
folder that keeps instructions but is not versioned keeps them on one machine, which is the loss bowline exists to
prevent. bowline sees a folder of repositories when a repository's top folder holds other repositories that it does
not track; init writes the .gitignore lines that keep them out. A submodule is tracked, so it stays part of the
repository that holds it. The memory is unchanged: Claude Code keys it on the repository's top folder, which is the
same folder.

**Not chosen, for now.** Making an oversized CLAUDE.md in a repository bowline may not write into fully read, by copying
it into the folder's rules and hiding the original through Claude Code's claudeMdExcludes setting: the copy would drift
from the repository's own file as its owners change it. The first user accepted leaving such a file to its owners for
now. Also known and left as it is: a session started inside one of the repositories reads the folder's CLAUDE.md, but
Claude Code looks for skills only up to the repository's root, and does not document whether it reads the folder's
rules, so the folder's files serve sessions started in the folder.
