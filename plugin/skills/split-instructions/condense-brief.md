# The brief for a subagent that condenses one page into rules

Fill in the angle brackets and give the whole text to one subagent per page. The subagent reads the repository but
changes nothing; it writes its drafts into a scratch folder you name.

---

You are condensing one long-form page of a repository's instruction history into a short rule file that Claude Code
can read, as part of a move the person approved. READ-ONLY on the repository: do not edit, move or commit anything in
it. Write your output ONLY under <scratch folder>.

Repository: <path>. The page: <page path>, about <size> characters. Read it completely with the Read tool in ranges.

Why: Claude Code cuts a nested instruction file at a fixed size, so most of this text was never applied; the page now
holds the long form, and your rule file is the short form that loads whenever a file under <area glob> is touched.

Write these files:
1. `<rule file name>.md`, starting with this front matter exactly:
---
paths:
  - "<area glob>"
---
then a heading, one sentence saying what the file covers and that the long form with its history is in <page path>
under the same titles, then the rules. Each rule is a bullet: a bold lead of a few words, the imperative in plain
full sentences, and its one-sentence why. Point to the exact source file, test or lint rule when one enforces a rule,
after checking with grep that it exists.
2. `MAP.md`: a table with one row per top-level entry of the page, in order: its bold title or first six words; what
became of it: RULE (which bullet), PAGE-ONLY (history or reasoning that stays in the long form only), or DROPPED (the
reason: superseded by later text in the same page, enforced by a named test or lint rule you confirmed by grep, or a
one-off state that is over). Then a short list of anything you could not verify, and of entries that contradict each
other (say which one the code follows).

Hard limits: the rule file holds at most <budget> characters and fewer than 200 lines; count before you finish and cut
the least important rules first. Writing rules: full sentences in plain words for a contributor who never met the
person or Claude; refer to the person as "the user"; ASCII only; no dates unless a why needs one; no paths outside the
repository (no memory, scratch, temp or home folders); no private links; no company or third-party names other than
the open-source tools used. When an entry names a file, class, component or test, check with grep that it still
exists; if it is gone, mark the entry DROPPED with that reason. Report back with the character count and the MAP's
counts.
