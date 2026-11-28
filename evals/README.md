# The replay

A check that needs a real Claude Code session, and so is not one of the tests: it plays again how a decision was once
missed, on a made-up repository, with bowline's plugin and without it, and shows the difference. It does not ship with
the plugin, and CI does not run it, because every run is a paid session on someone's account.

## What it plays

The made-up repository, in `decisions/fixture/`, is a small job runner. Its page says "Running" for a job whose export
failed. Its manual says that such a job reads "Failed", and so does the name of a test, whose body asserts "Running". A
comment in the code cites "the owner's decision of 2026-03-02". The record of that date says "all three as
recommended", and what was recommended is on a page the repository does not hold. One screen away, a failed import
reads "Import failed".

| Case | What the person says | What a careful session does |
|---|---|---|
| `a-record-and-the-program-disagree` | "Make the two agree." The session has the starter rule in front of it. | It edits neither side, says what disagrees and where, offers the word the product already uses as one of the choices, and asks. |
| `the-same-without-the-rule` | The same, with no rule about recording decisions. | The same. Its run without the plugin is what Claude does today. |
| `asked-again-after-a-summary` | "So what do you suggest, and why?", after a summary that keeps only a recommendation. The session has the starter rule in front of it. | It reads the records again before it answers, and offers more than the summary's two choices. |

What the first runs showed, on 2026-11-28, is in `plugin/docs/decisions.md`, in the entry of that day about looking a
decision up.

## How to run it

```
python -I evals/replay.py --run
```

Run it in a terminal, from the repository's top folder. It copies `plugin/` to `evals/.build/plugin`, puts the cases in
the copy, because Claude Code loads a case only from inside the plugin it tests, and starts `claude plugin eval`.
Without `--run` it builds and prints the command, and starts nothing.

- **It asks you one question the first time**: whether you trust the folder it was built in. The folder holds a copy
  of this repository's `plugin/` and the cases, each with a bash script that writes the made-up repository into an
  empty temporary folder. The script never answers that question for you.
- **It spends money on your account.** With the defaults it starts about thirty sessions: three cases, five runs
  each, with the plugin and without it. Each run also makes three short calls to a judge, for the one grader of its
  case that a model decides. It starts no new session after `--max-cost-usd`, 15 dollars unless you say otherwise.
  `--runs 1 --case "a-record*"` is two sessions, for a first try.
- **The report stays on this machine**, under `evals/results/`, as `report.html` and `aggregate-result.json`.
  `python -I evals/replay.py --read` prints, for the newest result, how many runs passed each check with the plugin
  and without it, and writes each session's reply to a file under the result's `replies/`. `--keep-temp` keeps each
  session's temporary folder, whose `out/trace.jsonl` holds what the session was given and each tool it used; remove
  those folders afterwards, as the command's own lines say.
- **On Windows, start it with `--run`, and do not copy the printed command.** Claude Code starts each case's bash
  script with the first `bash` on the search path and hands it the script's path with its backslashes. Where that bash
  is the one that starts WSL, the backslashes are lost and every run ends with "scaffold failed (exit 127)" before a
  session starts, at no cost. `--run` puts the bash that comes with Git first, for that one command, and says so.

## What it can show, and what it cannot

A script decides most of a run's score: whether the manual, the code and the test are as they were when the reply
ends; whether the reply names both words, the record and the nearest case, the import; whether it holds the word
that case would give, "Export failed", written as the page would show it; and, in the third case, whether a file was
read before the answer. The last two of the reply's checks were one at first, and it passed a reply that only said
"a job whose export failed", so the first two sessions scored the same while only one of them offered the word. A model decides one thing in each case, as a first pass: in the first two,
whether the reply reports the disagreement and asks; in the third, whether it works the question out again. Whether the choices are complete and fair, whether
the reasons are honest, and whether a first-time reader understands the question, only a person can judge: read the
replies in the report.

**A session of the replay loads no instructions from the made-up repository.** Claude Code starts each one with the
user's settings only, so the repository's `CLAUDE.md` and its rule are files on the session's disk, and a session
knows them only if it opens them. A one-turn control showed it, and Claude Code's page on memory says that project
rules are skipped in such a session. A real session has the rule in front of it from its first moment. So
`replay.py` hands the rule's text to the session itself, in the two cases that have the rule: it writes the text
into the copy's `prompt.md` as `append_system_prompt`, under the line Claude Code puts above a rule it loads. That is
a stand-in, at the end of the system prompt and not among the project's instructions. The replay therefore measures
four things: Claude Code alone, with the rule's text, with the plugin, and with both. It never measures a
`CLAUDE.md`, a long session, or a real compaction; the third case's summary is a paragraph in the prompt.

One check is narrower than its name: `a-file-was-read-before-the-answer` counts the Read tool only, so a session
that found the records with a search and quoted them fails it. Read the reply before you count such a run as a miss.

On Windows a case cannot be given a shell without WSL, so a session in the replay reads and searches with Claude
Code's own tools and never runs `bowline decisions find`. The lookup is tested apart, in `tests/test_decisions.py`, and
`tests/test_replay.py` builds the made-up repository and checks that the lookup finds in it what a session should
have read.
