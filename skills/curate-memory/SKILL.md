---
name: curate-memory
description: Sort Claude Code's memory notes for this repository into what belongs in the repository (promote), what stays personal (keep), what is finished history worth five lines (trim) and what is stale or already recorded (delete), with a map the person approves before anything moves. Use when the memory index nears its cap, when notes have piled up over months, or when the person wants to share what was learned with other contributors.
---

# Curate the memory

Memory is personal and per machine by design: a note is never shared by copying it. What a project needs every
contributor to know is promoted into the repository, written for a contributor; what is personal stays; what is done
goes. Nothing moves before the person approves the map.

## 1. Take stock

Run `"${CLAUDE_PLUGIN_ROOT}/bin/bowline" memory status`. Confirm the folder is backed up (the history then keeps every
deleted note); if not, offer `/bowline:memory-backup` first and stop until it is. List the notes with their sizes and
their `description` lines from the front matter.

## 2. Sort, with the rubric

The rubric is `${CLAUDE_PLUGIN_ROOT}/skills/curate-memory/rubric.md`. Read each note in full and give it one verdict:

- **PROMOTE**: a convention, gotcha, procedure or decision anyone working on this repository should know, and the
  repository does not already say it. Check by grep (two or three distinctive phrases over the instruction files and
  the docs). Draft the promoted sentence for a contributor who never met the person or Claude, at most sixty words,
  with the why, and name its home: a scoped rule under `.claude/rules/<area>/`, the root `CLAUDE.md` (rare, whole-repo
  and short), a skill (a procedure), the design document's decisions section, or the roadmap. In a folder of
  repositories, a note about one repository goes into that repository; one that holds for all of them goes into the
  folder's own `CLAUDE.md` or an unscoped rule under the folder's `.claude/rules/`.
- **KEEP**: personal to the person and their Claude: how replies should sound, standing requests, how they coordinate
  sessions, their machines, lab, links and other projects, the state of ongoing conversations.
- **TRIM**: a finished piece of work the repository already records; keep five lines (the final state, the hashes, an
  open follow-up) and drop the history.
- **DELETE**: stale, superseded, or fully duplicated by a repository file (name the file and line).
- **SPLIT**: promote one part, keep or trim the rest.

For more than about twenty notes, split the list among subagents, each with the rubric and the same table columns, and
merge their tables. The table has one row per note: name, gist, in the repository already (file:line or no), verdict,
home of the promoted part, the promoted sentence, flags (a private link, an address, a machine, another project, a
third party's name).

## 3. Show the map and wait

Show the table, the counts per verdict, and the notes that overlap and should merge into one. Ask the person to approve
or change it. Do not touch a file before they do. Say plainly what you will never do: delete a note they did not
approve deleting, or write anything flagged as personal into the repository.

## 4. Carry it out

- Write each promotion into its home, as a bullet in the repository's own style (an imperative with its why). A
  procedure becomes a skill or a section of one. Run the repository's budget check afterwards.
- Trim, merge and delete the notes as approved. A merged note keeps its sources' dates where a date carries meaning.
- Rewrite `MEMORY.md` with one line per remaining note: a link and a hook sentence, nothing else. Keep it far under 200
  lines and 25 KB.
- Run `"${CLAUDE_PLUGIN_ROOT}/bin/bowline" memory push` so the backup records the change, and
  `"${CLAUDE_PLUGIN_ROOT}/bin/bowline" doctor` to show the index's new size.

## 5. Report

Say how many notes went each way, where each promotion landed, and what stayed private and why. Grep once more that
every promoted sentence exists exactly once in the repository.
