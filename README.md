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

The skills that scaffold a repository, back up the memory, curate it and split an oversized file follow in the next
rounds (see `CHANGELOG.md`). The facts everything rests on, with sources and the date checked, are in
[`docs/facts.md`](docs/facts.md).

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
