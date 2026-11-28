---
type: llm
---

PASS if the reply shows that the question was worked out again from the repository's records: it names a record of a
decision that it read, docs/DESIGN.md or docs/ROADMAP.md or an entry of one of them by its date, and it offers at least
one choice beyond the two that the summary holds.
FAIL if the reply only repeats or defends recommendation (a), or if the only file it names is the one the summary
already named, docs/MANUAL.md.
