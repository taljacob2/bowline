# keel

Claude Code reads less of your `CLAUDE.md` than you think. A nested one is cut at a fixed size and the rest is never
applied; the documentation's target is 200 lines, and real files grow to thousands. The memory Claude keeps about your
project lives on one machine, loads only its index at the start of a session, and is lost with the machine. A long
conversation is summarized while you are away, and nothing tells the summary what to keep.

keel is a small set of tools and one explanation. It measures a repository and a machine against what Claude Code
actually reads and says what to do; it scaffolds a layout where each kind of knowledge lives where the tool loads it;
it backs up and curates the personal memory; it moves an oversized instruction file into that layout without losing a
line; and it refuses a commit that carries what must never be committed. Every number it uses is a visible, dated
setting with its source. The name is the beam a ship is built on, the one that keeps it steady on every voyage.

## Try it in one minute

```
git clone https://github.com/taljacob2/keel
python -I keel/scripts/keel.py doctor --repo <your repository>
```

The doctor prints three lines per finding: what it found, why it matters, and what to do. Nothing is changed.

## What is here today

| Command | What it does |
|---|---|
| `doctor` | Measures every `CLAUDE.md` against the loading limits (naming the section where a nested file is cut), the rules and skills against their budgets, the memory folder against its index cap and its backup, and the repository against the layout. |
| `gate` | Refuses a commit whose staged lines hold a token, a control byte, a carriage return, a byte-order mark, a character outside the accepted set when the repository says so, or a word from a private never-commit list kept outside every repository. Also runs as a Claude Code hook on `git commit`. |
| `budget` | Refuses an instruction file over the sizes Claude Code reads, or one that names a path no other machine can see. |
| `memory setup <remote>` | Makes Claude Code's memory folder for the repository a git repository tied to a private remote of yours, and installs the hook that pushes it after every reply. `memory status`, `memory restore <remote>` on a new machine, `memory push`. |
| `init` | Scaffolds the repository's side: three sections for the root CLAUDE.md, `.claude/README.md`, two starter rules, two starter skills, repository-local copies of the gate and the budget check, a pre-commit hook, `.claude/keel.json`. `--plan` shows, `--write` does; nothing that exists is overwritten. |

```
python -I keel/scripts/keel.py init --repo <your repository> --plan
python -I keel/scripts/keel.py init --repo <your repository> --write
python -I keel/scripts/keel.py memory setup git@github.com:<you>/<private memory repo>.git --repo <your repository>
```

| `move` | Moves an oversized CLAUDE.md into long-form pages, scoped rules and an index without losing a line: `plan` shows the sections and where the cutoffs fall, `run --spec` moves them verbatim, `find-pointers` and `pointers` update every mention. |

## The skills, for Claude Code

`skills/` holds the six procedures Claude runs these tools through, with the person in the loop: `doctor`, `init`,
`memory-backup`, `curate-memory` (sort the memory with a map you approve), `split-instructions` (move first, condense
second) and `conventions` (a decisions section, a roadmap with slots, a notes queue, offered one at a time). The plugin
packaging that installs them with one command is the next round; until then, start a session with
`claude --plugin-dir <this folder>` once the manifest lands.

The guide: [`docs/facts.md`](docs/facts.md) (what keel measures against, with sources and the date checked),
[`docs/conventions.md`](docs/conventions.md) (the conventions and the loss each prevents) and
[`docs/migrating.md`](docs/migrating.md) (move first, condense second; sorting a memory).

## Requirements

Python 3.8 or later (standard library only) and git. Windows, Linux and macOS.

## Configuration

`defaults.json` holds every limit and policy with its reason. A repository lays its own values over them in
`.claude/keel.json`, for example to make characters outside ASCII a refusal rather than a warning, or to name the
characters it accepts.

## Tests

```
python -I -m unittest discover -s scripts/tests -p "test_*.py"
```

Every test runs on a scratch repository under the system's temp folder and removes it afterwards.

## License

MIT.
