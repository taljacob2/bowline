# bowline

Claude Code reads less of your `CLAUDE.md` than you think. A nested one is cut at a fixed size and the rest is never
applied; the documentation's target is 200 lines, and real files grow to thousands. The memory Claude keeps about your
project lives on one machine, loads only its index at the start of a session, and is lost with the machine. A long
conversation is summarized while you are away, and nothing tells the summary what to keep.

bowline is a small set of tools and one explanation. It measures a repository and a machine against what Claude Code
actually reads and says what to do; it scaffolds a layout where each kind of knowledge lives where the tool loads it;
it backs up and curates the personal memory; it moves an oversized instruction file into that layout without losing a
line; and it refuses a commit that carries what must never be committed. Every number it uses is a visible, dated
setting with its source. The name is the sailor's knot that holds fast under load and still comes undone by hand:
knowledge tied down so that it holds, with nothing locked.

## Install

As a Claude Code plugin, so its skills and hooks are there in every session:

```
claude plugin marketplace add taljacob2/bowline
claude plugin install bowline@bowline
```

Then, in any repository, `/bowline:doctor`. The plugin's hooks run on their own: at a session's start the doctor puts a
one-line finding into Claude's context when something is over budget or unbacked, and nothing when all is well; after
every reply the memory folder is pushed to its backup once `/bowline:memory-backup` has tied it to a private remote; and
before every `git commit` Claude issues, the gate checks the staged lines. During a session, when a `CLAUDE.md`, the
memory index or one of its notes crosses a limit, you get one reminder in the doctor's words, and Claude gets the same line at your next
message. A repository that turns `autosplit` on in `.claude/bowline.json` gets one more: when a `CLAUDE.md` outgrows
the limits, the hook after a reply starts a worker that prepares its split in the background, on a branch of its own,
for you to review and merge. Everything else is a skill you or Claude invoke, with you approving before anything moves
on your branch.

The doctor prints three lines per finding: what it found, why it matters, and what to do. Nothing is changed.

## What is here today

| Command | What it does |
|---|---|
| `doctor` | Measures every `CLAUDE.md` against the loading limits (naming the section where a nested file is cut), the rules and skills against their budgets, the memory folder against its index cap, its notes against the commits each one names (a note that keeps finished work like a log) and its backup, and the repository against the layout. As hooks: `--brief` at a session's start, `--watch` after every reply (one reminder when something new crosses a limit), `--pending` before a prompt (the same line for Claude). |
| `gate` | Refuses a commit whose staged lines hold a token, a control byte, a carriage return, a byte-order mark, a character outside the accepted set when the repository says so, or a word from a private never-commit list kept outside every repository. Also runs as a Claude Code hook on `git commit`. |
| `budget` | Refuses an instruction file over the sizes Claude Code reads, or one that names a path no other machine can see. |
| `memory setup <remote>` | Makes Claude Code's memory folder for the repository a git repository tied to a private remote of yours, and installs the hook that pushes it after every reply. `memory status`, `memory restore <remote>` on a new machine, `memory push`. |
| `init` | Scaffolds the repository's side: three sections for the root CLAUDE.md, `.claude/README.md`, two starter rules, two starter skills, repository-local copies of the gate and the budget check, a pre-commit hook, `.claude/bowline.json`. `--plan` shows, `--write` does; nothing that exists is overwritten. |
| `move` | Moves an oversized CLAUDE.md into long-form pages, scoped rules and an index without losing a line: `plan` shows the sections and where the cutoffs fall, `run --spec` moves them verbatim, `find-pointers` and `pointers` update every mention, `place --spec` copies finished drafts into rules, skills, pages or an index. |
| `autosplit` | With `autosplit.enabled` in `.claude/bowline.json`, prepares the split of a CLAUDE.md that outgrew the limits in the background: the hook after a reply starts a headless Claude Code session on a branch of its own, the worker checks the result, and the doctor says when it is ready for you to review and merge. `deliver` chooses between that branch (the default) and merging onto your branch on its own when your tree is clean. `run` does it now in the foreground; `status`, `show`, `done` after the merge, `discard`. |

## A folder of repositories

Claude Code can be started in a folder that is not a repository but holds several, as with services cloned side by
side. bowline works there too. The doctor, the budget, the one-line finding at a session's start and the reminders
measure the folder's own `CLAUDE.md` and every repository directly under it, and name the repository in each finding.
The gate finds the repository a commit names (`git -C repo1 commit`, `cd repo1 && git commit`). The memory is the
folder's one memory, as Claude Code keeps it. Autosplit works per repository, each split on a branch of its own
repository, and a `.claude/bowline.json` in the folder is the layer every repository shares, under its own. From the
folder, `init` writes the folder's own `CLAUDE.md`, an index of the repositories with the sections every root file
needs, and the shared `.claude/bowline.json`; `init --each` scaffolds every repository. `move` and `autosplit` take the
repository from the file they are given, as a path from the folder (`repo1/sub/CLAUDE.md`); the few commands that take
no file want `--repo`.

**Keeping bowline's files in the folder.** When you cannot write into the repositories, or would rather not touch them,
set `"writeToRepositories": false` in the folder's `.claude/bowline.json`, or run `init --leave-repositories` from the
folder, which writes it. `init` then puts the README, the rules and the skills in the folder itself, and a rule for one
repository goes in `.claude/rules/<repository>/` with `paths: ["<repository>/**"]`, which Claude Code applies to that
repository's files in a session started in the folder. `init --each`, `move` and autosplit write nothing into the
repositories; the doctor still measures them, in notes that say why it changes nothing and what you can do instead. A
list of names, `["repo2"]`, lets bowline write into those repositories only. One limit is Claude Code's: a session
started inside one of the repositories reads the folder's `CLAUDE.md`, but not the folder's skills, and the
documentation does not say that it reads the folder's rules, so the folder's files serve sessions started in the folder.

**The folder as a git repository of its own.** The folder can itself be a git repository that holds only what its
repositories share, so that its files are versioned and backed up like any repository's. bowline still sees a folder
of repositories, as long as the folder does not track them: `init` writes the `.gitignore` lines that keep them out,
and a submodule, which the folder does track, counts as part of it. The folder's own files are then committed, gated and
split like a repository's.

## The skills, for Claude Code

`skills/` holds the six procedures Claude runs these tools through, with the person in the loop: `doctor`, `init`,
`memory-backup`, `curate-memory` (sort the memory with a map you approve), `split-instructions` (move first, condense
second) and `conventions` (a decisions section, a roadmap with slots, a notes queue, offered one at a time). You start
one by its name, `/bowline:doctor` and the like, or Claude does when one fits the work. The commands they run, and the
hooks, go through `scripts/run.mjs`, which finds Python on the machine and runs bowline.

The guide: [`docs/guide.md`](docs/guide.md) (the problem in a page, the three homes, the budgets, the five flows
drawn), [`docs/facts.md`](docs/facts.md) (what bowline measures against, with sources and the date checked),
[`docs/conventions.md`](docs/conventions.md) (the conventions and the loss each prevents),
[`docs/migrating.md`](docs/migrating.md) (move first, condense second; sorting a memory),
[`docs/compared.md`](docs/compared.md) (how it differs from doing it by hand, from `claude-md-management`, and from
Claude Code's own features) and [`docs/decisions.md`](docs/decisions.md) (the design questions that settled, and why).

## Privacy

bowline runs no service, collects no telemetry, and its author receives nothing from your use of it. Two features
send data off your machine, and each one is off until you turn it on:

- **The memory backup** pushes Claude Code's memory folder for the repository, which can hold personal data, to a git
  remote you name, after every reply.
- **Autosplit** starts a headless Claude Code session on your machine, which talks to Anthropic as any session does.

The [privacy policy](PRIVACY.md) says in full what bowline reads, writes and sends, what personal data it touches and
how long anything is kept.

## Requirements

Python 3.8 or later (standard library only), git, and Node.js on the PATH: Claude Code starts the plugin's hooks with
`node`, and the skills use the same launcher. Windows, Linux and macOS.

## Configuration

`defaults.json` holds every limit and policy with its reason. A repository lays its own values over them in
`.claude/bowline.json`, for example to make characters outside ASCII a refusal rather than a warning, to name the
characters it accepts, or to turn `autosplit` on.

## License

MIT.
