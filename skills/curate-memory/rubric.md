# The rubric for sorting memory notes

A memory note gets one of five verdicts. The question behind every verdict is the same: who needs this, and where would
they look for it?

| Verdict | It is | Where it goes |
|---|---|---|
| PROMOTE | A convention, gotcha, procedure or decision anyone working on the repository should follow or know, that the repository does not already say | A scoped rule, the root CLAUDE.md, a skill, the decisions section or the roadmap, rewritten for a contributor |
| KEEP | Personal to the person and their Claude: reply style, standing requests, session coordination, machines, lab, links, other projects, ongoing conversations | Stays in the memory, maybe merged with its kin |
| TRIM | A finished piece of work the repository already records | Five lines: the final state, the hashes, an open follow-up |
| DELETE | Stale, superseded, or fully duplicated by a repository file | Gone (the backup's history keeps it) |
| SPLIT | A project rule carrying a personal story | The rule promoted, the story kept or dropped |

## Tests that decide the hard cases

- **Would a new contributor on another machine need it to do the work right?** Then it is project knowledge, however
  personal its origin. A rule the person stated in anger is still a rule.
- **Is it already in the repository?** Grep two or three distinctive phrases over the instruction files and the docs.
  If a file says it, the note is DELETE or TRIM, however well written.
- **Does a test or a lint rule already enforce it?** Then the repository does not need the sentence either; name the
  test in the map and drop the note.
- **Is it about how the tools behaved on this machine** (a shell quirk, a failing drive, a sandbox refusal)? KEEP; a
  contributor's machine differs.
- **Is it the state of something in progress?** KEEP, trimmed to the open part; the finished part is in the repository
  or belongs there.
- **Does it name a third party, a private link, an address, an account or a path on this machine?** Flag it. Nothing
  flagged goes into the repository; a promoted sentence is written without it.

## Writing the promoted sentence

For a contributor who never met the person or Claude: plain full sentences, the imperative and its one-sentence why,
at most sixty words, no dates unless the why needs one, no names of people, no paths outside the repository, no
company or third-party names beyond the open-source tools used. Name the file, class or test that enforces it when one
exists, after checking it still does.

## Merging kept notes

Notes about one subject merge into one: the person's git workflow, their test machines, their links and the brand's
history, their other projects, how decisions are brought to them. Each merged note keeps the dates that carry meaning
and the user's own words where they gave a rule.
