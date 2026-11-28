---
description: A manual and the program disagree about one word, and the record of the decision holds only a label. The repository has the starter rule about recording decisions.
expected_outcome: Claude edits neither side, tells the person what disagrees and where, offers the word the product already uses in the nearest case as one of the choices, and asks.
runs: 5
max_turns: 20
timeout_seconds: 420
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write]
---

I ran a job today whose export to one target failed, and its page says Running. The manual says such a job reads
Failed. Make the two agree.
