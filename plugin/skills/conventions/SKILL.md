---
name: conventions
description: Offer a repository the working conventions that keep decisions, roadmap items and mid-work notes from getting lost - a decisions section, a roadmap whose scope cuts get numbered slots, a notes queue, the state written before a round closes, a fresh session per finished item, a decision looked up before a question goes to the person - each with its reason and a template the person may edit. Use after init, or when decisions keep getting re-litigated, deferred work keeps vanishing, feedback arrives faster than it is handled, or the doctor notes that the repository's instructions have no section about looking a decision up.
---

# The conventions

These are recommended defaults, not rules bowline enforces. Each one exists because of a specific loss; offer it with its
reason and let the person choose. The reasons and templates are in `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md` and
`${CLAUDE_PLUGIN_ROOT}/templates/conventions/`.

## Offer them one at a time

1. **A decisions section in the design document.** When a design question settles in conversation, it gets an entry
   with its reasoning in the same round, without being asked. Without it the same question is re-argued a month later
   and the reasoning is gone. Template: `decisions-section.md`. Ask where the design document is, or offer to start one.
2. **A roadmap with numbered slots for scope cuts.** The Next list is in the order work should run; a deliberate scope
   cut gets a numbered item in the same round that makes the cut. A gap with a name but no slot is forgotten. Template:
   `roadmap.md`.
3. **A notes queue.** Feedback that arrives mid-work is written down verbatim, with its date, and worked in order once
   the current round is committed; the person keeps sending, the work keeps its thread. Template: `notes-queue.md`.
   Ask whether the queue lives in the repository (shared) or in memory (personal); both work.
4. **The state written before a round closes.** Before the reply that closes a round, the round's state (what is
   pushed with its hashes, what is built but unchecked, what is only agreed) goes where the next session will look:
   the roadmap, a progress note, the memory. A compaction or a fresh session then finds it. This is a habit, not a
   file; it belongs in the root `CLAUDE.md`'s Compact Instructions, which `init` wrote.
5. **A fresh session at a finished item.** A summary of a summary loses more than a fresh start that reads the index
   and the instruction files. Offer the habit; nothing to install.
6. **A decision is looked up before a question goes to the person.** Two bullets in the rule about recording
   decisions: read what was decided and find the nearest case the product already handles before a design question
   goes to the person, and when a record and the program disagree, find which one is the mistake before editing
   either. Without them a session asks a question whose answer is in a record, or picks a side and edits. `init`
   writes them into a new repository's starter rule; a repository whose rule file is older has neither, and the
   doctor notes it. Run `node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" decisions section`. It changes no file. It
   says whether the section is there, and if not: where it goes, how many characters it adds to the rules every
   session loads, the earlier bullet that it replaces, and the section's text. Show the person what it printed.
   With their yes, edit the rule file that exists: add the section at its end, in the repository's own words where
   its other bullets have them, and take out the bullet the command names, which told a session to correct the
   document. Never write a second rule file. When the rules would go over their limit, say so and ask what to move
   or trim before you add anything. Afterwards run the budget check and the doctor: the note is gone when the
   section's heading says "Before a question" or the rule names `/bowline:decide`.

When the person runs several sessions on the repository at once, each in its own worktree, there is one more, with a
skill of its own: `/bowline:crew`, for who is here, claims before work, shared files that are edited and never saved
over, and a quiet machine before a heavy check. Offer it by name; do not repeat its steps here. Its companion,
`/bowline:collaborate`, is for the same sessions working as a team.

In a folder of repositories, each repository keeps its own decisions and roadmap, and the folder's own documents hold
what spans them; ask which the person means before writing. For each one the person wants, write the template into
the repository where they say, adapted to its words (ask for
the design document's name, the roadmap's name, the queue's place), and add a line to `.claude/rules/recording-decisions.md`
if it exists so the rule and the file agree.

## What not to do

Do not write all six unasked, and do not present them as bowline's rules: they are one team's way that worked, offered
with its reasons. A repository that already has an ADR folder, an issue tracker as its roadmap, or another queue keeps
its own; point the rule at the existing thing instead.
