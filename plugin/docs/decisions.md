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

## 2026-11-14: bowline is not submitted to Anthropic's plugin directory, for now

**The question.** bowline 0.7.0 passed the directory's validation with no blocking issue. The last step of the
submission asks the author to agree to the Software Directory Terms and the Directory Policy, and to state that "the
plugin does not exfiltrate credentials or execute code outside its declared MCP servers". Can the author agree?

**What the documents say.** The Directory Policy, section 1, item G, with no exception: "Software must not query or
extract data from Claude's memory, chat history, conversation summaries, or user-generated or uploaded files and must
not persistently store or use conversation content to build user profiles or attempt to make any changes to Claude's
behavior across sessions." bowline's memory backup extracts Claude Code's memory folder and pushes it to a remote, its
curation reads and rewrites the memory, and its purpose is how Claude behaves across sessions. By submitting, the
author warrants that the software's ordinary use complies with the Policy. bowline declares no MCP servers, and its
hooks and skills run Python on the user's machine, so the statement about code is not true of it either. The
validation had already said that the directory will later accept command hooks only from Verified organizations.

**The decision.** The first user's words: "let's don't release for now ... we just use the marketplace and it's
enough for now". bowline reaches people through its own marketplace, which none of these rules govern. Nothing built
for the directory is undone: the plugin's own folder, the hooks in program-and-arguments form, the privacy policy and
the `release` branch stay, because each is right for the marketplace too and keeps a later submission one step away.

**Not chosen.** Cutting bowline down to fit: without the memory features much of its value is gone, and its hooks would
still run code. Agreeing on a generous reading of the statement: an attestation is a promise, and this one would not
be true. Asking Anthropic first remains open to the author, for whether a plugin that manages CLAUDE.md files and backs
up Claude Code's memory at the user's request is acceptable, and how a plugin with command hooks should answer.

## 2026-11-16: a memory note that names many commits is a warning

**The question.** The doctor measured the memory index and the backup, never a note. The first user asked whether
memory notes should be kept to a length, after a search of theirs showed a capped output, and whether bowline's
documentation already covers it. It does not, for three reasons found in 0.7.0. The rule that keeps the index short
moves the detail into the notes ("fold its rounds into one line ... and move the detail into its own file"), so a
project that follows it well has a small index and notes that keep growing. The only thing that shortens a note is
curate-memory's TRIM verdict, which the doctor suggested only when the index neared its cap, so a careful project was
never prompted. And a note is read whole whenever it looks relevant, so one that keeps every finished round spends
context at every read and buries what is still open.

**The decision.** The doctor warns when a note names `memoryNoteCommits` commits or more (10 by default), and points to
curate-memory. `bowline memory status` lists every note with its lines, its bytes and the commits it names, the largest
first. The memory rule in the templates and in bowline's own `CLAUDE.md` gains one sentence: once the repository
records a finished piece of work, the note keeps a pointer to that record and its last commit, nothing more.

**Why commits and not lines.** No Claude Code limit makes a line count meaningful for a note: notes load on demand,
whole, and the Read tool reads up to 2,000 lines by default, far past any note. On the first user's real memory, 18 notes
of 15 to 57 lines, sizes did not tell the log from a long reference note (5.0 KB against 4.6 KB), and the commits did:
the progress note that had become a log named 16, the most of any other was 6, and that was a finished item folded as
the rule asks. Folding names commits, so the count grows exactly with finished work kept in full. A commit is 7 to 40
lowercase hex digits with a letter and a digit, standing alone; front matter, UUIDs and path segments do not count,
because the first run counted a job's scratch folder in a path.

**Why a warning and not a note.** Only problems and warnings reach a person at a session's start and in the reminders;
a note appears only when someone runs the doctor, which is the gap this closes. The reminder's identity is the
finding's words with the numbers blanked, so a note that keeps growing is one reminder, not one per reply.

**Not chosen.** A line or byte limit per note, for the reason above. A note-level finding, for the reason above.
Counting dated entries: a note keeps the dates that carry meaning, so dates do not mark finished work.

## 2026-11-16: a folder of many repositories

**The question.** A person ran `init` and the doctor from a plain folder of well over a hundred repositories on a slow
mount. Four
things went wrong. `init` could not install the gate there, yet wrote a rule and two skills that told Claude to run
`.claude/scripts/gate.py`, which did not exist, and said "this repository" of a folder. Each row of the folder's table
took the first line of the repository's `CLAUDE.md`, which was as often a warning or a rule as a description, cut at a
hundred characters. The doctor ran past Claude Code's two-minute command limit and printed close to two thousand lines, most of them
three findings repeated for every repository, and nothing until the end. And `init` printed every name twice.

**The decisions.**

- The gate goes where commits are made. `scripts` and `githook` are folder items when the folder is a git repository,
  installed as for a repository; in a plain folder `init` refuses them and says that `git init` comes first. The
  folder's rules, skills and README have their own templates, `templates/folder/`, worded for a folder, and name the
  folder's copy of the gate only when there is one; otherwise they say that none is installed, why, and that the
  plugin's hook still gates every commit Claude issues in a repository below. The plan marks those files "without the
  gate". A repository's own templates are unchanged.
- A row's description is chosen, not taken. The README's first paragraph that describes, then the package's
  description (package.json, composer.json, pyproject.toml, Cargo.toml, a .csproj), then the first describing
  paragraph at the opening of the `CLAUDE.md`, before its first section. A line that starts with a list marker, a
  bold or quoted mark, a word that instructs (never, always, must, stop, important, and the like), a line in capitals,
  or a line that ends with a colon never describes. Whole sentences only, up to 160 characters; a first sentence over
  240 leaves the row for the person. The plan says which rows came from where, and `--no-describe` fills none.
- The doctor's time was git, not printing. A profile of 139 made-up repositories found 1,534 git processes, eleven per
  repository: three file listings for the size check, each with its own `rev-parse`, and "which folder is this
  repository in?", asked three to six times per repository, rescanning the whole folder every time, with one git call
  per child when the folder is a repository. Now the folder's layout is worked out once per run, the folder's tracked
  children are one git call, the size check lists a repository's files once, and autosplit reads `.git` without git:
  three git processes per repository. Eight repositories are measured at once. On Windows the run went from 21
  seconds to 1.8, and on WSL over `/mnt/c` from 44 to 2, with the report unchanged before the output changes below.
- The report says a repeated finding once. In a folder, a finding found the same in several repositories, the same
  severity, words, why and fix, is one finding with an `in:` line naming them, its why and fix once; a finding about
  the folder itself stands alone, since the folder is not one of its repositories. The totals and the exit code count
  the findings one by one, as before, and `--brief` and the reminders read them one by one, unchanged. Each
  repository's sizes print as it completes, in order, a line on standard error marks every tenth of the way, a
  repository whose rules and skills are all zero gets no line for them, and `--verbose` restores everything one by one.
  `--folder-only` measures the folder alone.
- A list of names shows ten. Every list of repositories init or the doctor prints shows the first ten and how many
  more, and says the count and the reason once; `--verbose` names them all.

**Why the layout may be remembered for a run.** A run of bowline creates no repository, so which folder is a
repository's top, and which repositories a folder holds, stays true until it ends. File listings are never kept: a run
writes files, and the autosplit worker measures a worktree it just made.

**Not chosen.** An ignore line for "every folder that holds a `.git`": git cannot express it, so `.gitignore` keeps one
line per repository, and the README shows the allowlist a person may write instead. Changing `--brief` to show the
problems first: it was asked to stay as it was.

**Left for later**, each a concrete piece of work this round did not do:

1. The folder's `CLAUDE.md` holds one table row per repository, so with about 140 repositories it passes 200 lines and
   the doctor flags the file `init` just wrote. The table could move to a page the `CLAUDE.md` points to once the
   folder holds more repositories than fit.
2. `budget` from a folder still prints one summary line per repository; it could list only those with something in
   them, as the doctor now does.
3. A rule or a skill written without the gate stays as it is after `git init`, because `init` never overwrites; the
   plan could say which files would read differently now that the gate can be installed.

## 2026-11-21: the crew, for sessions that work side by side in one repository

**The question.** The first user runs several Claude Code sessions at once on one repository, each in its own git
worktree, each pushing to the same branch after a rebase. For two days the sessions coordinated by hand: they listed
one another, sent messages saying which files each would touch, read the machine's process list for one another's
test runs, checked the ports the person's own servers listen on, and waited in a loop until nobody else's tests ran.
Three things still went wrong. One session saved an older copy of a shared memory note over the file and erased four
notes another session had added. Two sessions took the same roadmap number. And checks crashed or timed out under
another session's test suite. After a rebase, a build's stamp also named a commit that no longer existed. Should this
way of working be a standard, and should bowline hold it?

**The decision.** Yes, as one skill, `crew`, and one command, `bowline crew`, with checks in the doctor and hooks
after the git commands that matter. bowline lists and records what a script can see; Claude says the rest to the other
sessions with its own tools, `ListAgents` and `SendMessage`, and the skill says when. The pieces, each with the loss
it answers:

- **Who is here.** `bowline crew` lists every worktree with its branch, its distance from the pushed branch, its
  uncommitted files, when a session last worked there, its processes that are heavy or listen on a port, the files
  changed in more than one worktree, the claims and the turn. A session's start gets one line when another session
  worked in the repository in the last half hour, and nothing when it is alone, so a session alone pays nothing.
- **Claims.** A session takes a name, such as `roadmap:124`, before it works on the thing, and a second session is
  refused with the holder's name. `claim <list> --new` takes one past the highest number in the pushed branch, in
  every worktree's copy of the file, committed or not, and in every claim. Reading the other worktrees' copies is what
  makes it hold even when a session forgot to claim: the two sessions that took the same number had each written it
  into a file the other could have read.
- **Shared files are edited.** What was measured on 2026-11-21: Claude Code's Write tool refuses a file that changed
  since it was read, and its Edit tool puts its replacement into the file as it is now. So a note is lost in two ways
  only: a whole-file write from a shell or a script, or a session that is refused, reads the file again, and sends the
  text it already had. The skill's rule closes both. For what slips through, each commit of the memory backup now
  names the session whose reply it follows, and the doctor warns when one session's commit removed lines another
  session's commit had added within a day and no note holds them now.
- **The turn.** `crew run -- <command>` waits until no process matches the repository's heavy patterns and no other
  `crew run` holds the turn, takes it, and runs the command. The turn exists because watching processes alone has a
  gap: two sessions that wait both see the machine go quiet at the same look and both start.
- **After a rebase and a push.** A hook after `git rebase` and `git pull` says when a number appears twice or a stamp
  names a commit the branch lost; a hook after `git push` says who waits on it. Both are silent otherwise.

**Where the claims live.** In the repository's git folder, under `bowline/crew/`, beside the autosplit records: every
worktree of a repository shares that folder, nothing in it is ever committed, and it needs no service. Not chosen: the
memory folder, which every worktree also shares, because the backup would commit each claim after every reply and the
notes are for what should outlast a session; a file in the repository, because a claim must be seen before a push,
not after one.

**Why a session is recognized by three signs.** A script cannot ask Claude Code which sessions are open. What it can
see is that each worktree has its own project folder in Claude Code's configuration, and that a session started there
writes its transcript there as it works. Only the folder's listing is read, never a transcript. That sign alone
missed the first session that worked beside the one building this: it had been started in another repository and
worked in a worktree of this one by path, so its transcript was in the other repository's project folder, and the
look said nobody had worked there while that session held three claims. So the last sign of work is the newest of
three: a transcript, the worktree's own git folder being written (a commit, a staged file), and a claim. All three are
observed, not documented; the line at a session's start is a hint that points to the skill, and `ListAgents` is the
list.

**What a second session found by using it.** Before the release, a session with a related task ran the uncommitted
command from its own worktree and on the first user's repository, and sent eight findings; each changed the command.
A look ran `git status` in every worktree, which refreshes that worktree's index and can make the other session's own
git command fail on the index lock: every git question is now asked with `--no-optional-locks`. A session that waits
on another's work heard nothing until a push, though a session on a branch of its own commits long before it pushes:
the hook now speaks after a commit too. A claim's key was shown with its case folded: keys are compared folded and
kept as typed. On the real repository the list of files changed in two worktrees named twelve files, one of them in
two running sessions' worktrees, which nobody had noticed, and it also named the roadmap and the design document,
which every session changes by rule, and four files of a worktree nobody had touched for three weeks: so the
repository names its shared records (`crew.shared`), which are listed apart, and a worktree with no sign of work for a
day is marked quiet. A branch cut from another's commit made every file of that commit look changed twice: a file now
counts only when two worktrees hold different content of it, compared by the content's id. Two worktrees made from
another system's view of the disk were left out without a word: they are named. The person's git showed a signature
line before every commit in `git log`: the memory's history is read with `--no-show-signature`. And reading every
worktree of that repository cold took over two minutes, far too long for a hook that runs before an edit: the look
keeps what it measured in the repository's git folder, `crew refresh` measures again and prints nothing, and such a
hook reads the record.

**Why the doctor never quotes a lost line.** The memory-backup skill says that a note's content is shown only to a
person who asked for it. The finding counts the lines and names the note and the commit; `bowline memory losses`,
which a person or Claude runs on purpose, lists them.

**Why a loss is a warning that can be wrong.** A commit cannot say whether a removal was a mistake. A session that
works a note another session queued an hour ago and takes it off the queue looks the same in the history as a session
that saved an older copy over the file. The check takes the side that loses nothing: it warns, shows where the lines
are, and `memory losses --meant <commit>` records that a removal was meant. Lines that are moved to another note, or
put back, are never reported, because the check asks whether any note holds the line today.

**What stays the repository's.** Which processes are heavy, which ports are the person's own, which lists are
numbered and by which pattern, which files are stamps and how each is remade: all in the repository's
`.claude/bowline.json`, under `crew`, empty by default. The order of a repository's checks, and which may run
together, stay its own rules; the turn adds only that one heavy command runs at a time across every session. A short
unscoped rule for such a repository is a template the skill offers, not something `init` writes, because a repository
where one session works at a time should not pay for it at every session's start.

**What bowline does not do.** It never stops a process: the wait ends by itself or times out and names what runs. It
never sends a message. It never writes into another worktree. A heavy pattern that matches a server a person keeps
running would make every wait time out, which is why the patterns are each repository's to write.

**Not chosen.** A hook that refuses a write to a memory note: the Write tool already refuses the stale ones, and a
shell command's target cannot be read reliably from its text. A default list of heavy programs: a person's own
watcher would match it and never go quiet. Measuring the processor's load instead of naming processes: a load number
does not say whose work it is, or when it will end. Dropping a waiting claim after the push it waited for: the push
may hold something else, so the claim stays until the session that waits gives it back.

**One rule, with both halves (added the same day, after the release).** While 0.10.0 was being built, the first
user's repository wrote its own rule about working beside other sessions. Half of it was what the crew's template
already said. The other half was new: a task of its own gets a session of its own, parallel sessions where the pieces
allow it, a new subject moves the round first, and reading and checking stay in subagents; and one rule of the first
half, split the work by files and agree before editing a file another session changed. The user asked, through the
session that works there, that bowline ship one rule holding both, because two rule files with one title would make
a reader wonder how they differ. So the template has two sections, the skill has a seventh step, and the conventions
page names each habit with its loss. The cost is size: about 4,000 characters of the 10,000 the unscoped rules may
use, where the first template took 1,700, which is why the skill tells a repository to drop the rules it does not
need.

**Left for later**, each a concrete piece of work this round did not do:

1. A git `post-rewrite` hook in the repository, installed by `init` beside the pre-commit hook, so that a rebase a
   person makes outside Claude Code is checked at once; today the doctor finds its traces at the next session's start
   or after the next reply.
2. The commit gate's hook matches only the Bash tool (`"matcher": "Bash"`, `Bash(git commit*)`), so a `git commit`
   that Claude issues through the PowerShell tool is not gated by the plugin; the crew's hooks match both tools, and
   the gate's should.
3. Claims across machines. The claims live in one machine's git folder; two people's sessions on two machines meet
   only at the remote.
4. From a folder of repositories, the line at a session's start says nothing about other sessions; it could look at
   each repository's worktrees.

## 2026-11-21: a warning before an edit of a file another worktree holds

**The question.** After a round in which three sessions worked on one repository without a collision, the first user
asked to keep how they did it as a standard, "where possible", in bowline. Most of that behaviour had come from the
instructions the Claude desktop app gives Claude, which another client and another contributor never see. A rule in
the repository makes it the repository's own; what makes it hold without anyone remembering is a hook. The crew, built
the same day by another session, covers who is here, claims, shared files, heavy checks and rebases. What it did not
have is the moment that matters most for a file: the edit.

**The decision.** A PreToolUse hook on Edit, Write and NotebookEdit, `crew before-edit --hook`. When another worktree
holds the file about to be edited, Claude is told which worktree and branch hold it, how, and the last sign of work
there, and is asked to agree with that session who changes what and to name the agreement in the commit message. It
is part of the crew: one feature has one name, one settings section and one rule template, so this version adds no
second word for it.

**Why a warning and never a block.** The hook answers with `hookSpecificOutput.additionalContext` and no
`permissionDecision`. The documentation says a hook that reports no decision lets the tool call continue "through the
normal permission flow", so the person's own approvals are untouched and nothing is auto-approved. A block would be
wrong more often than right: bowline cannot know whether a session still works in the other worktree, whether the two
sessions already agreed, or whether the file is one both are meant to add to. A check that stops work on a guess gets
turned off; one that says what it sees and what to do is read.

**What counts as held.** A change there that is not committed; a commit there that is in neither the pushed branch
nor the branch being edited; or a claim `file:<path>`. The second was learned by building it: this feature's branch
was cut from the crew's branch before that was pushed, so every file the crew's commit touched looked changed in both
worktrees. The hook therefore asks git, for the one file, what the other branch holds from where the two branches
part; nothing means this branch already has the change. The claim was learned the same way: the session that built
this held claims on three files and the other session edited them all the same, because nothing read a claim at the
moment of an edit.

**Why the hook measures nothing.** It runs before every edit, and measuring nineteen worktrees one after another took
140 seconds on the first user's repository, on a slow disk with stale indexes. So the hook reads the record the crew
keeps (`changed.json`), starts `crew refresh` detached when the record is older than `crew.changedCacheSeconds`, waits
two seconds, and answers from what it has. A file another session changed in the last minute may be missed at one
edit and is caught at the next; an edit never waits for a disk. A record over an hour old says nothing true about who
works here now and is not used.

**Why the launcher answers when it can.** Starting Python took 1.3 seconds on a machine where other sessions ran test
suites, and this hook runs before every edit of every session in every repository that has bowline. Most repositories
have one worktree. `run.mjs` reads the hook's JSON, walks up from the edited file to its `.git`, and exits when that
is a folder with no worktrees under it. A worktree's own `.git` is a file, which already means there are two.

**Why once per session and file.** A warning repeated at every edit of one file is read past by the tenth. It is said
again when the state changes: another worktree joins, or an uncommitted change becomes a commit.

**Why the doctor's finding is a note.** A repository can have several worktrees with no parallel session: Claude Code
makes one for a subagent, and a person keeps a second checkout. A convention is offered, not pressed, and only
problems and warnings are said at a session's start. The hook does the telling when there is something to tell.

**How it was built.** Beside the session that built the crew, in a worktree of its own, each telling the other which
files it took. The two collided once in three files while messages were queued; neither lost work, and the claim check
above came out of it. The second session's findings from using the crew for real are in the crew's entry.

**Not chosen.** A settings section and a rule template of its own, as first asked: the first user agreed that bowline
ships one rule for working beside other sessions, and the crew's template has it. A list of every other worktree's
changed files at a session's start: the crew's one line says that others are at work, and the list is `bowline crew`.
A cache of its own: two records of one thing in one folder disagreed within minutes.

**Left for later**, each a concrete piece of work this round did not do:

1. An edit made through a shell command (a redirect, `sed -i`, a script that writes the file) is not seen: the hook
   matches the three editing tools. The Bash and PowerShell tools name no file, so this needs the changed paths that
   Claude Code reports after a shell command.
2. A session that edits and stages nothing leaves no sign of work for the others until its files are measured. The
   hook could record "a session edited here" in the repository's git folder, and the crew's last sign of work could
   read it, which would also name sessions started in another folder.
3. The warning names each worktree in full. With many holders of one file it grows long; it could name the two with
   the newest sign of work and count the rest.

## 2026-11-21: sessions that collaborate

**The question.** The crew keeps sessions out of each other's way. While it was being built, two sessions with
related tasks worked on it side by side. The first user's words, as one of the two sessions passed them on: "i would
potentially want that as a skill within itself - 'to collaborate between the sessions' - so they would enrich the
experience of each session - since they can check things together and work together as a team to make sure things or
think better together, and sync together." To the session that built it they said: "yes the 'collaboration' sounds
good in my opinion, but plan it first", and, after the plan, "Yes, build it". What does such a skill hold, and does it
need anything a script can give?

**The decision.** A skill of its own, `collaborate`, and one command, `crew say`. The skill is the moves that
worked in that round, each with what it answered. Say your subject before you design: two sessions had been started
on the same feature by two different sessions, and neither knew until one saw the other's branch. Exchange file lists
before either edits: both sessions did, and it is what let them split one feature. Ask for a trial: the second
session ran the first one's uncommitted command from its own worktree and on a large repository, and sent eight
findings, each of which changed the command before its release. Ask what the other sees: one session had measured
the real repository and the other held the approved plan. And sync, with a look before any step that cannot be taken
back.

**Why a status each session writes.** Three things went wrong with messages alone. They arrive when the other
session next looks, so several times in one round two messages crossed and each session acted on an order the other
had already changed. A report that the desktop app passes on to another session is cut at 400 characters. And a
session that needed a neighbour's last report said it read about 240 messages of that conversation to find it.
`crew say` keeps a few sentences per worktree beside the claims, and the look shows them: the state is there, whole,
whenever anyone looks, and a message only says that it changed. The session chooses the words, so bowline still opens
no transcript, and it works where a client has no tools for messages between sessions.

**Why it is refused over its limit, not cut.** A cut report is the loss this exists to prevent. Six hundred
characters hold what is done, what is waited on and what is asked, and a look at ten worktrees can still be read at
once.

**Why its own skill.** The crew skill is read by a session that must not collide, at the moment it is about to take
a number or run a check. This one is read at another moment and for another reason: when a session could use
another's help. Claude decides which skill to load from its description, and one description cannot say both. The
crew skill points to it in one sentence.

**What another session's word is worth.** In that round, sessions wrote to one another "the user confirmed" and "the
user asks" several times, each time truthfully. The skill still says that such a sentence is a report: it cannot
approve a push, a release or a deletion, and a session acts on it only for work that is already its own to do. A
skill that made sessions trust each other's reports of approval would turn any one session's mistake into every
session's.

**Not chosen.** A hook that puts another session's words into Claude's context on its own, such as a question
waiting for this worktree: text that arrives unasked from another session reads like an instruction, and the look,
which Claude runs on purpose, shows the same words as data. A shared notes file that every session writes: that is
how one session erased another's notes, and the reason each session has a status of its own instead. A history of
what each session said: the commits are the history, and a status is the present. Sending messages from bowline: a
plugin has no tool for it, and Claude does.

**What a trial of it found.** The session that had tried the crew tried this too, from its own worktree, before any
release. It asked that the look set a session's words apart from its own lines, since a status may hold a sentence
that starts like one of them: they are in quotation marks now. It reported that a refused status exited with 0;
that did not happen again here, where it exited with 2, and the session then found its own cause: it had piped the
command into another, and read that one's exit code. The code is 1 now all the same, as for a claim another worktree
holds. And it proposed that the warning before an edit repeat what the holding worktree said. The warning says only
that it said something, when, and that the look shows it: a hook's text arrives unasked, and the reason above for
keeping another session's words out of it holds there too. The session that proposed it agreed.

**Left for later**, each a concrete piece of work this round did not do:

1. A question to one worktree that stays visible until it is answered, beside what a session says of itself, for a
   client with no messages between sessions; today the status holds the question in its words.
2. The look could mark a status older than its worktree's last commit, since it then describes work that has moved
   on.

## 2026-11-21: a background process on Windows gets a console that is never shown

**The question.** How does bowline start a process that keeps running after the hook that starts it returns? Two do:
the autosplit worker and `crew refresh`. On Windows both were started with `DETACHED_PROCESS`.

**What went wrong.** A process started with `DETACHED_PROCESS` has no console. When it starts a console program, such
as git or Python, Windows gives that program a new console, and the new console is visible; on Windows 11 it opens as
a Windows Terminal window. The first user saw several windows open and close within about five seconds, roughly once a
minute, and each one took the focus from the game they were playing. A process watcher found seven windows in 5.5
seconds, one for each git and Python that a single autosplit worker started while bowline's tests ran. The starts the
hooks make behave the same way.

**The decision.** `common.background_start()` gives the arguments for every such start. On Windows they are
`CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`: the process gets a console of its own that is never shown, every console
program it starts shares that console, and its own process group keeps a Ctrl+C meant for the session away from it.
Windows ignores `CREATE_NO_WINDOW` when `DETACHED_PROCESS` is also given, so the old flag is removed, not added to. On
Linux and macOS the process gets a session of its own, as before.

**Not chosen.** Starting the worker with `pythonw.exe`: it has no console either, so the programs it starts would still
open windows. Passing `CREATE_NO_WINDOW` to each git call inside the worker: it works, but every later call would have to
remember it, and one that forgot would bring the windows back.

## 2026-11-21: several sessions in one repository is the usual case

**The question.** A session set the crew up in a second repository, the day the crew was released, and sent three
gaps. Nothing points a repository to the setup: `init` does not mention it, and it is the last section of a skill
that a session opens only by choice. The rule template writes `bowline crew` as if it were a command, and a session
that types it finds no such program. And the template never names `/bowline:collaborate`, which came after it. All
three were checked against the code and hold, and the first user said: "Yes, build them". The first build gave the
line at a session's start only when another session had worked in the repository in the last half hour. The first
user then asked: "why wait 30 minutes and not 1 minute or even better - immediately once a new session is created?",
and said: "you should assume always that several sessions work in the repository as the default".

**What the 30 minutes are.** Not a wait. The look happens the moment a session starts, and `crew.activeMinutes` says
how long a sign of work counts, so that a session which is thinking, or waiting for a check, still counts as there.
But the question found a real gap: the first session of the day looked, saw nobody and was told nothing, and the
second one started a minute later. The first was never told, unless it happened to edit a file the second held.

**The decision.** Two parts. First, every session's start in a repository gets the line, whether or not another
session is seen (`crew.assumeOthers`, true by default). It names the places where another session worked lately, or
says that none shows now and that one may start at any moment, and it names `/bowline:crew` and
`/bowline:collaborate`. When the repository has no rule about working beside other sessions (the test the doctor's
note already uses: a heading that names other, parallel or several sessions), the line also carries the rule's main
points and says that the last section of `/bowline:crew` sets the repository up. Second, a session that is already
running is told when another one appears: the hook before a prompt looks again and names each place where a sign of
work has shown since the session was last told, once. The names it has given are kept beside the reminders' record,
in the repository's git folder.

**What it costs.** Every session's start in every repository now carries the line: about 500 characters with a rule
and about 930 without one, of the 10,000 a hook's output may hold. The hook before a prompt now asks git for the
worktrees and reads when a few folders were written, on every prompt, where it only read one small file before. This
reverses a choice made a day earlier, that a convention is offered and never pressed at every session's start; the
first user's words above are the reason, and the doctor's note about a repository with several worktrees and no rule
stays as the long form for a person who reads the report.

**The decision, for the template.** It says in one sentence that `bowline crew` is the plugin's script and that the
skill gives the full command, and it has a point about working as a team. Every session reads the template at its
start, and the second repository's unscoped rules already took 9,504 of their 10,000 characters, as that session
reported, so the other points were worded shorter until the template was the size it had been, 4,036 characters.

**Not chosen.** A shorter `crew.activeMinutes`, such as one minute: it would not have told the first session
anything, and it would forget a session in the middle of a long check. A question in `init` about several sessions:
with several sessions taken as the usual case there is nothing to ask, and the init skill offers the setup. Writing
the crew's settings from `init`: only the person knows which checks are heavy, which ports are theirs and which
lists the sessions extend. Making `bowline` a real command: Claude Code's plugin reference, read on 2026-11-21, says
that files in a plugin's `bin/` folder "are on the Bash tool's `PATH` while the plugin is enabled", says nothing of
the PowerShell tool, and says that claude.ai and Cowork do not install a plugin that has this folder. The first
user's sessions type their commands in PowerShell, so the name would work in one tool and fail in the other, and the
plugin would install in fewer places. This was read, not tried.

**Not decided here: autosplit on by default.** Another session passed on the first user's words: "I feel like
autosplit should be default to true 'branch' and crew and collaboration should be default true too". The second half
is what this entry does. The first half is not done: `autosplit.enabled` is false in `defaults.json` because its
worker spends money, up to `autosplit.maxBudgetUsd` for a split, and makes a branch; a plugin installed for a
person's whole account would then start paid runs in every repository they open, their own or not. The session that
passed the words on proposed that `init` write `"autosplit": {"enabled": true}` into the repository's own
`.claude/bowline.json` and name the cost in its plan. That is a decision about the person's money, so it waits for
their word in the session that would build it, not for a word passed on.

**Left for later**, each a concrete piece of work this round did not do:

1. `init` offers autosplit for the repository it sets up, naming the cost, once the person has decided the default.
2. The setup could propose settings it can see: a roadmap file with numbered items, a test runner the repository's
   own files name. A runner in watch mode never goes quiet and must not be proposed as a heavy process.
3. After a commit, when other sessions are at work and this worktree's status is older than the commit, the hook
   could remind the session to write a new one with `crew say`.
4. A session in the middle of a long turn is told of a new session only at its next prompt; until then the warning
   before an edit covers the file both would change. A hook after a tool call could tell it sooner, at the price of
   a look after every tool call.

## 2026-11-21: a message that stops being true is corrected

**What happened.** The day the collaborate skill was released, a session that works on bowline changed one file in
a second repository, for a session that works there. It wrote to that session that the commit was not pushed and
that the push was for the first user or for a session of that repository. Minutes later the first user told the
first session to push, and it pushed and removed its worktree. It sent nothing more. The second session then asked
the first user to approve a push that had already happened, and the first user asked why it had not been told.

**Why the skill did not prevent it.** Three reasons, as the second session named them. The skill said to keep the
state where anyone can read it and to use messages to say that it changed, but never that a message of your own
which stops being true needs a correction. The session that waited had not written its wait down, so the check
after the push told the pusher that nobody waited. And the crew's records are one repository's: the two sessions
work in different repositories, so in each one the other is no neighbour at all.

**The decision.** The skill gets three additions, and no code. A message that stops being true needs a correction,
one line in the same turn that names the message it corrects; the examples are the ones that happened. A session
that needs another's branch or commit first records it with `crew claim waits:`, in the step about exchanging file
lists, where a session that splits work reads it. And the skill says that the record is one repository's, so that
between repositories the messages carry everything.

**Not chosen.** A reminder from the hook after every push to correct what was said: the hook cannot know what a
session said to whom, and a line after every push that is usually about nothing teaches a session to skip it.

**Left for later**, each a concrete piece of work this round did not do:

1. The check after a push looks at the repository of the session's own folder. A push made in another repository,
   by changing folder inside one command, is checked against the wrong one; the check could read the folder the
   command names.
2. A wait across repositories: a session could record that it waits on a branch of another repository on the same
   machine, and that repository's check after a push could name it.

## 2026-11-21: a record that Windows refuses to replace is tried again

**What happened.** Two tests that wait for the autosplit worker failed in about half of the full test runs on one
Windows machine, and never on GitHub's machines: the split's record stayed at "running" for the whole 120 seconds.
A busy machine was the first guess. It was wrong. With the stand-in for claude the worker needs about one second,
and repeated outside the suite, 2 of 40 workers and then 3 of 60 stayed at "running" while the others were ready
within two seconds. Each one that stayed had ended with the same traceback in its log: `PermissionError: [WinError
5] Access is denied`, from `os.replace()` in `save_state()`, at the save that follows `git worktree add`. One run
of the two test modules failed the same way, with the same traceback.

**The cause.** bowline saves a record by writing a file beside it and putting that file in the record's place, so
that a reader never sees half a record. On Linux and macOS that step always works. On Windows it is refused for as
long as any other process has the record open, unless that process opened it in a way Python's `open()` does not.
The test reads the record every 0.2 seconds, and the worker's second save falls about 0.2 seconds after the hook
returns, which is when the test reads for the second time; that is why it happened far more often than two short
moments would meet by chance. A reader is not even needed: of 300 saves made one after another with no reader at
all, 10 were refused at first, by something else on the machine. Every refusal was over within 17 milliseconds.
The worker did not wait: the error ended it, the record stayed at "running", the branch and the worktree stayed,
and the hook starts nothing for a file that has a record.

**Did the hidden console cause it.** No, and it is likely what made it frequent. The save, the reader and the
refusal are the same before and after the start flags changed, so the fault was there from the first version of
autosplit. With `DETACHED_PROCESS` every git and Python the worker started opened a console window, and a process
watcher counted seven of them in 5.5 seconds; since the change the same worker is done in one second, and its saves
fall in the first moments after the hook returns, when the test reads most closely behind it. This part is reasoned
from the timing and was not measured: running the old flags many times would have opened hundreds of windows on
the first user's screen, which is what the change was made to stop.

**The decision.** `common.replace_file()` puts a file in its target's place, and on Windows tries again when the
step is refused, with a short pause that doubles, until five seconds have passed; then it raises the error. The
three places that save a record this way use it: `autosplit.save_state()`, `crew.write_json()` and
`doctor.save_watch()`. Five seconds is about 300 times the longest refusal measured and still short for a hook
that a reply waits on. On Linux and macOS an error from that step is a real one and is raised at once. In the
worker, the save that names the worktree moved inside the block that always removes the worktree and records how
the worker ended, so that a failure there, of any kind, is recorded as "failed" with its reason. With the change,
none of 60 workers stayed at "running", and none of 200 in a second sample.

**The tests.** The wait of 120 seconds stays: it was never too short, and a longer one would only have hidden a
worker that died. Both tests now use one wait, `wait_for_split()`, which fails with the record as it stands and the
end of the worker's log, so the next stall says what the worker last did. Two new tests fail without the fix: one
holds the record open as a reader does while it is saved, and one refuses the save after the worktree was made and
checks that the worktree is gone and the record says "failed".

**Not chosen.** Opening the record for reading in the way that lets Windows replace it: Python's standard library
has no public call for it, and it would do nothing about a virus scanner or any reader that is not bowline. A lock
file around every read and write: it makes every reader wait on every other one to solve a refusal that lasts
milliseconds. A longer wait in the two tests: the worker was dead, not slow.

**Left for later**, each a concrete piece of work this round did not do:

1. A record at "starting" or "running" whose process is gone. A worker can still die without a word: the machine
   restarts, the process is stopped, or a save is refused for longer than five seconds. `bowline autosplit status`
   and the doctor then say "being prepared in the background" for good, `discard` refuses the record because it
   takes the worker to be running, and the person clears it by hand. The doctor could say that the process named in
   the record is gone, and `discard` could accept such a record and remove the worktree it left.
2. The old start flags were not run again, for the reason above, so how often the refusal happened before the
   change is not known.
