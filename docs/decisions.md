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
