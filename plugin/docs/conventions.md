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

## Writing for a person

Everything a person reads, in the code's messages, the documents and the rules, is written in full sentences, in plain
words, one idea per sentence, a term explained before it is used, so that a first-time reader understands it without
guessing. A rule written in shorthand is a rule the next contributor, and the next session, reads wrong. This is the
convention the others are written in; bowline's own files follow it.
