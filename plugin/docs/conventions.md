# The conventions bowline recommends, and why each exists

bowline enforces sizes. It does not enforce these. They are one team's way of working with Claude Code across months,
offered because each one grew out of a specific loss; take the ones whose loss you recognize. The `conventions` skill
offers them one at a time with their templates (`templates/conventions/`).

## Three homes, by kind

The one firm convention, because bowline's checks assume it. A **rule** is an imperative with its one-sentence why, in a
file under `.claude/rules/` scoped by path, so it loads only when a file it concerns is touched and loads whole. A
**procedure** is a skill under `.claude/skills/`, whose body loads only when used. A **decision or a story** is a
document, read on demand: a decisions section for the why, the roadmap for the when, a conventions folder for the long
form of the rules. The root `CLAUDE.md` stays under 200 lines because every session pays for it, and a nested one
becomes an index because Claude Code cuts it.

The loss it prevents: a single growing `CLAUDE.md` that the tool reads less of every month, with no sign that it does.

## A decisions section

When a design question settles in conversation, it gets an entry with its reasoning in the same round, without being
asked. The loss: the same question re-argued later, and the reasoning gone with the conversation that held it. The
entry's shape is the decision, the why in the words the question was asked in, and what was not chosen when that helps.

## A roadmap with numbered slots for scope cuts

The Next list is in the order the work should run. When a round deliberately leaves out a concrete, understood piece
of work, it gets a numbered item in the same round, placed where it should run. The loss: a gap with a name but no
slot, forgotten by everyone, found by a customer.

## A notes queue

Feedback that arrives mid-work is written down verbatim with its date and worked in order once the current round is
committed. The person can keep sending; the work keeps its thread. The loss: a note answered at once that fragments the
round, or a note not written down that is never answered. Whether the queue lives in the repository or in a personal
memory depends on who sends the notes.

## The state written before a round closes

Before the reply that closes a round, its state goes where the next session will look: what is pushed with its
hashes, what is built but not yet checked, what is only agreed. The loss: a compaction or a new session that starts
from a summary's guess. Claude Code's Compact Instructions section, which `init` writes, tells every summary to keep
exactly this.

## A fresh session at a finished item

A long session is summarized again and again; a fresh one reads the index, the root `CLAUDE.md` and the rules whole.
When a piece of work is finished and pushed, that is the clean point to start again. The loss: a summary of a summary
of a summary, each one a little further from what was said.

## Working beside other sessions

Several Claude Code sessions can work in one repository at once, each in its own worktree, and they share more than
they see: one machine's processor, one memory folder, one roadmap whose numbers each of them extends, and the ports a
person's own servers listen on. The convention has two halves, and the `crew` skill is their procedure.

The first half keeps the sessions apart: look at who is here before the first change; split the work by files, and
agree with the other session before editing a file it has changed; claim a number, a note or a file before working on
it, in a place the others read, and say it to them; change a file the sessions share with an edit, never by saving it
over whole; run a heavy check only when no other one runs; and after a rebase, read again what the others also write.
Each habit has its loss. Two sessions that edit one file meet at the rebase, and the second one's work is redone by
hand. Two sessions that each add an item to the roadmap take the same number, and a rebase joins both without a
conflict. A note saved whole from an older copy erases what another session added since, because the memory folder
has no branches and the last writer wins. Two test suites at once crash or time out, and the failure looks real. A
build's stamp names a commit the rebase renamed.

The second half moves work into a session of its own wherever the work allows it. A task of its own, such as a scope
cut or a problem found in passing, gets its numbered slot and a session of its own instead of widening the round; the
loss is a round that never closes and a commit that holds three subjects. Pieces of a plan that touch different files
and need nothing from each other are proposed as sessions side by side; the loss is the sum of their times, spent one
after another. A new subject in the middle of a round moves the round to a session of its own first; the loss is a
round left half done in a conversation that has moved on. And reading and checking stay in the session, in a subagent
whose answer comes back in the same turn; the loss is a session nobody needed to open, for work that ends in no
commit.

Unlike the conventions above, part of this one is checked: `bowline crew`
keeps the claims and the turn, and the doctor warns about a number that appears twice, a stale stamp, and memory
lines one session added and another removed. What stays the repository's own is in its `.claude/bowline.json`: which
processes are heavy, which ports are the person's, which lists are numbered, which files are stamps.

## Writing for a person

Everything a person reads, in the code's messages, the documents and the rules, is written in full sentences, in plain
words, one idea per sentence, a term explained before it is used, so that a first-time reader understands it without
guessing. A rule written in shorthand is a rule the next contributor, and the next session, reads wrong. This is the
convention the others are written in; bowline's own files follow it.
