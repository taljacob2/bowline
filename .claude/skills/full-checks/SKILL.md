---
name: full-checks
description: Run every check bowline requires before a push - the tests on scratch repositories, bowline's own gate over its files, the budget and the doctor. Use before pushing, or when asked whether everything passes.
---

# The full checks

A push comes only after these pass (`.claude/rules/before-a-commit.md`). Run them from the repository's root.

## 1. The tests

```
python -I -m unittest discover -s tests -p "test_*.py"
```

Every test makes a scratch git repository and a scratch Claude Code configuration folder under the system's temp
folder and removes them afterwards. The launcher's tests start `plugin/scripts/run.mjs` with node, and are skipped on a
machine without node. A test that fails only on one system is a real finding: the launcher and the paths are what
differ between Windows, Linux and macOS. CI runs the same command on Linux, Windows and macOS on every push to main.

## 2. bowline's own gate, budget and doctor, and the validation

```
python -I plugin/scripts/bowline.py gate --all
python -I plugin/scripts/bowline.py budget
python -I plugin/scripts/bowline.py doctor --no-memory
claude plugin validate plugin --strict
claude plugin validate .
```

The first validation checks the plugin folder as Anthropic's plugin directory does; the second checks the marketplace
file at the root.

bowline's files are ASCII only (`.claude/bowline.json` makes a character outside ASCII a refusal), so a `\u` escape typed
into a test must be built with `chr()`; the Write tool of Claude Code turns the escape into the character itself.

## 3. What tests cannot show

A change to the launcher, to `plugin/hooks/hooks.json` or to how a hook reads its input is checked in a real Claude
Code session started with `--plugin-dir <this folder>/plugin`: the memory push after a reply, and the gate blocking a
`git commit` with a staged fake token, on Windows and on Linux (WSL).
