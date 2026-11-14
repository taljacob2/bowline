---
name: memory-backup
description: Back up Claude Code's memory folder for this repository to a private git remote of the person's, after every reply, or restore it on a new machine, or report its state. Use when the doctor says the memory is not backed up, when the person moves to a new machine, or when they ask what Claude remembers and where it lives.
---

# The memory backup

Claude Code keeps its notes about this repository in a folder outside it, one per person per machine, and loses it with
the machine. bowline makes that folder a git repository tied to a private remote and pushes it after every reply.

## Setting it up

1. Explain in two sentences what the folder is and that the notes are personal (how they work, their machines, their
   links), so the remote must be private. Ask for the remote's address. If they have none, offer to create one:

   ```
   gh repo create <name> --private --description "Claude Code's memory for <repository>"
   ```

   and use `git@github.com:<owner>/<name>.git`. Creating a repository on their account is outward-facing: do it only on
   their word.

2. Run the setup. The bowline plugin's own hook already pushes after every reply once the plugin is installed, so no
   per-machine hook is needed:

   ```
   "${CLAUDE_PLUGIN_ROOT}/bin/bowline" memory setup <remote> --no-hook
   ```

   It clones the remote when the folder is empty (a new machine), initializes and pushes a first backup when the folder
   holds notes and the remote is empty, and refuses when both hold content, saying how to merge by hand. If it says
   Claude Code has made no project folder yet, a session has to run in the repository once first; this one counts, so
   run it again.

3. Show the result of `"${CLAUDE_PLUGIN_ROOT}/bin/bowline" memory status`: the index's size against its cap, the remote,
   the last commit, what is not yet pushed.

If the plugin's hook cannot run on this machine (Windows without Git Bash), run the setup without `--no-hook`: it then
writes a per-machine hook into Claude Code's settings with the absolute path of this Python.

## On a new machine

```
"${CLAUDE_PLUGIN_ROOT}/bin/bowline" memory restore <remote> --no-hook
```

after one session has run in the repository. Then `/memory` in a new session shows the notes read.

## When asked what Claude remembers

`memory status` says where the folder is and how big the index is. The notes themselves are the person's to read; the
index `MEMORY.md` lists them one line each. If the index is near its cap, offer `/bowline:curate-memory`.

Never print the content of a note the person did not ask to see, and never push to a remote that is not private.
