# Migrating: move first, condense second

This is how an oversized `CLAUDE.md` becomes pages, rules and an index without losing a line, and how a memory that
grew for months is sorted into what the project needs and what stays personal. Both were done once by hand, on a
repository whose two nested `CLAUDE.md` files had reached 278 KB and 465 KB and whose memory had 89 notes; the
procedure below is what that taught, and the `split-instructions` and `curate-memory` skills run it.

## Why two steps

Condensing is editorial: someone decides which sentence survives. Done in one step with the move, a reviewer cannot
tell what was moved from what was cut, and a lost rule is found months later, if ever. So the move comes first and is
pure: every section goes whole into its page, byte for byte except for the normalization of characters a commit gate
refuses (an em dash becomes a dash, an arrow becomes `->`; the count is printed). The index takes the file's place.
That commit is a move anyone can diff. The condensing comes second, in its own commit, and is reviewed against the page
it came from.

## The move

1. `keel doctor` says which file is cut, at which line, inside which section, and what is never read. That is the fact
   to show whoever decides.
2. `keel move plan --file <file>` lists the sections with their sizes and where the cutoffs fall.
3. Decide per section: a long-form page (history, reasoning, dated entries), a scoped rule (an imperative list for one
   area), a skill (a procedure), or the index. Group sections into pages by subject.
4. Write the spec and the new index (under 200 lines: what the folder is, what to read first, where the rules, skills
   and pages are, the commands). `keel move run --check`, then `run`.
5. Commit: "the move".

## The condensing

For each page, a draft rule file with a MAP: one row per entry saying RULE (which bullet), PAGE-ONLY (history that
stays in the long form) or DROPPED (superseded by later text in the same page; enforced by a named test or lint rule,
confirmed by grep; a one-off state that is over). A subagent per page with the brief in
`skills/split-instructions/condense-brief.md` does the drafting; the review checks every imperative against the page,
every named file and test against the code, and the budget: the scoped rules of one area under 40,000 characters
together, each file under 200 lines. Where two entries of the old file disagree, the rule follows the code, and the
page gets a note at its top naming the names that have changed since its history was written.

Then the pointers: `keel move find-pointers --name <old path>` lists every line that names the old file; a code
comment or a document that points at a moved section gets a replacement in a pointers spec, each matched exactly once
(`keel move pointers --spec <file>`); a historical mention that merely says the file existed stays.

Commit: "the short form".

What the first repository measured after both steps: the two files became indexes of 50 and 54 lines; the rules that
load for each area 39 KB; the rules every session loads 5 KB; nothing deleted, every entry in a page.

## Sorting a memory

The rubric is `skills/curate-memory/rubric.md`: promote, keep, trim, delete, split, with the tests for the hard cases.
The order that worked: back the memory up first, so the history keeps every deleted note; sort every note into a table,
in parallel for a large memory; show the table and wait for the person's approval; then write the promotions into the
repository as sentences for a contributor, merge the kept notes by subject, trim the finished ones to five lines,
delete the rest, and rewrite the index with one line per note.

What the first memory measured: 89 notes and 1.4 MB became 20 notes and 137 KB; 35 "how Claude should work" notes
turned out to be mostly project standards and went into the repository's rules; 51 "state of an item" notes were
mostly history the roadmap already held; 3 references stayed personal.

## What to watch for

- A pointer from an instruction file to a memory note, a scratch folder or a temp path: a contributor cannot follow
  it. The budget check refuses them.
- Scripts the instructions rely on that exist only in a session's scratch folder: bring them into the repository or
  drop the reference.
- Stale names: a class renamed since the history was written. The subagents' MAPs find them; the page's top note says
  them.
- The user's own words: when a rule came from a decision the person stated, keep their sentence in the page and write
  the contributor's sentence in the rule.
