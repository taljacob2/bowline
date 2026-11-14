<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/icon-for-dark-pages.svg">
    <img src="assets/icon.svg" width="128" height="128" alt="The bowline icon: a bowline knot in off-white on a navy tile">
  </picture>
</p>

# bowline

bowline is a Claude Code plugin and a guide that keep a project's knowledge within what Claude Code actually reads. It
measures your `CLAUDE.md` files, rules, skills and memory against the limits Claude Code loads them by, and says what to
do; it scaffolds a layout where each kind of knowledge lives where the tool loads it, backs up and curates the memory,
moves an oversized instruction file into that layout without losing a line, and refuses a commit that carries what must
never be committed.

The plugin's own README, [`plugin/README.md`](plugin/README.md), says what it does and how to use it, and its guide
starts at [`plugin/docs/guide.md`](plugin/docs/guide.md).

## Install

```
claude plugin marketplace add taljacob2/bowline
claude plugin install bowline@bowline
```

## Without installing

Start a Claude Code session with the plugin folder of a clone, `claude --plugin-dir <the clone>/plugin`, or run the
scripts directly with Python:

```
git clone https://github.com/taljacob2/bowline
python -I bowline/plugin/scripts/bowline.py doctor --repo <your repository>
python -I bowline/plugin/scripts/bowline.py init --repo <your repository> --plan
python -I bowline/plugin/scripts/bowline.py init --repo <your repository> --write
python -I bowline/plugin/scripts/bowline.py memory setup git@github.com:<you>/<private memory repo>.git --repo <your repository>
```

## What is in this repository

| Path | What it holds |
|---|---|
| `plugin/` | The plugin exactly as it ships: its manifest, hooks, skills, scripts, templates, defaults and guide. |
| `.claude-plugin/marketplace.json` | This repository as a marketplace with one plugin, the one in `plugin/`. |
| `tests/` | The tests, each on a scratch repository. They do not ship. |
| `.claude/` | The instructions, rules and skills for working on bowline itself. They do not ship. |
| `assets/` | The icon's vector sources, for this page. The image the plugin ships is in `plugin/assets/`. |
| `CHANGELOG.md` | Every version, with what changed and why. |

A version reaches people in two ways. bowline's own marketplace serves `plugin/` from the main branch, and Claude Code
installs it when its version changes. Anthropic's plugin directory follows the `release` branch, which moves only when
a version is released. The `release` skill under `.claude/skills/` is the procedure, and `plugin/docs/decisions.md`
says why.

## Tests

```
python -I -m unittest discover -s tests -p "test_*.py"
```

Every test runs on a scratch repository under the system's temp folder and removes it afterwards. The tests of the
Node launcher need `node`, and are skipped on a machine without it.

## License

MIT.
