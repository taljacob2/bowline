# The facts bowline rests on

bowline measures a repository against limits that are Claude Code's, not bowline's. Every number below is also a setting in
`defaults.json`, with its reason beside it, and the doctor prints which it used. When Claude Code changes one, the two
files change together and the changelog says so.

Checked against the Claude Code documentation on **2026-11-14**. Each row says whether the documentation states it or
whether it was observed on a machine.

| Fact | Value | Documented or observed | Source |
|---|---|---|---|
| The root `CLAUDE.md`, and every `CLAUDE.md` in a folder above the working directory, load whole at the start of a session, up to a ceiling | 4 MiB per file; a file over it is skipped entirely | Documented | memory.md |
| A `CLAUDE.md` in a subfolder loads on demand, when a file under that folder is read or edited | | Documented ("a `Loaded` line appears") | memory.md |
| A nested `CLAUDE.md` or a scoped rule that loads on demand is cut | 40,000 characters on a 200K context window; 150,000 characters on a 1M window with current models (200,000 on some older ones) | Documented; the text past the cut is not dropped silently: Claude gets a note that it may read the rest with the Read tool, "and until Claude chooses to, the later instructions aren't in its context" | memory.md |
| The size the documentation recommends for any `CLAUDE.md` | under 200 lines; "files over 200 lines consume more context and may reduce adherence" | Documented; a startup warning and `/status` warn above it | memory.md |
| Where part-of-the-codebase instructions should go | `.claude/rules/*.md`, scoped with a `paths:` list in the front matter; an unscoped rule loads at launch like the root file | Documented | memory.md |
| A rule's `paths:` budget | 1,000 patterns and 4 MiB per rule; globs are relative to the folder holding `.claude` | Documented | memory.md |
| Where procedures should go | a skill, `.claude/skills/<name>/SKILL.md`, whose body loads only when invoked or judged relevant; its description and `when_to_use` are listed to every session, truncated at 1,536 characters; keep the body under 500 lines | Documented | skills.md |
| Claude Code's memory | a folder per person per machine, `<config>/projects/<project>/memory/`, with `MEMORY.md` as its index and one file per note; every worktree of one repository shares it | Documented | memory.md |
| How much of the memory loads at a session's start | only `MEMORY.md`, and only its first 200 lines or 25 KB, whichever comes first; the notes are read on demand | Documented | memory.md |
| The project folder's name | the repository's path with every character other than a letter or a digit replaced by `-` | Observed on Windows (`I:\Tal\Code\other\repo` became `I--Tal-Code-other-repo`); the documentation describes transcripts this way but does not state the rule for memory | sessions.md |
| Memory is not backed up and cannot be shared by a checked-in setting | `autoMemoryDirectory` is ignored in a checked-in `.claude/settings.json` "for security" | Documented | settings-reference.md |
| Compaction when the context fills | the conversation is replaced by a structured summary as the context nears the model's limit; `/compact [focus]` does it by hand; a "Compact Instructions" section in `CLAUDE.md` tells the summary what to keep | Documented | context-window.md, how-claude-code-works.md |
| Compaction while idle | on by default (`idleCompaction`): a conversation that has reached 200,000 tokens and has been quiet for about an hour is summarized before the next message | Documented | settings-reference.md |
| What survives a compaction from disk | the root `CLAUDE.md`, unscoped rules, the memory index and skill bodies (to a cap) are re-injected; nested `CLAUDE.md` files and scoped rules only when their trigger file is read again | Documented | context-window.md |
| A plugin can ship skills, hooks, agents and scripts, but not a `CLAUDE.md` or rules | "A `CLAUDE.md` at the plugin root isn't loaded as context" | Documented | plugins-reference.md |
| A headless session, which autosplit's worker starts | `claude -p` prints the answer and exits; `--permission-mode acceptEdits` accepts file edits in the working folder; `--permission-prompts none` denies anything that would ask a person; `--allowedTools` lists what may run without asking; `--max-budget-usd` caps the spend; `--output-format json` ends with one object carrying `total_cost_usd`, `num_turns`, `session_id`, `is_error` and, on an error, `subtype` and `errors` | Documented; the flags and the result observed with Claude Code 2.1.319, and a session started from inside another session's hook environment | headless.md |
| What a Stop or SessionEnd hook receives on its standard input | JSON with `session_id`, `transcript_path`, `cwd` and `hook_event_name` | Documented | hooks.md |
| Edits under `.claude/` by the Edit and Write tools | are sensitive-file edits that need a person's approval even in `acceptEdits` mode and even with an allow rule for the path; with `--permission-prompts none` they are denied, while a script run through an allowed Bash command writes there (which is how `move run` and `move place` write rule files) | Observed with Claude Code 2.1.319; the refusal reads "Claude requested permissions to edit `.claude/rules/probe.md` which is a sensitive file"; not found in the documentation | (observed) |
| Which shell runs a hook's `command` | `sh -c` on macOS and Linux; Git Bash on Windows, or PowerShell when Git Bash is not found (a hook may name its shell with a `shell` field; `CLAUDE_CODE_GIT_BASH_PATH` names the bash to use). In PowerShell a quoted script path followed by arguments is a parse error, so bowline's shell-form hooks need Git Bash on Windows; a headless session started from an environment that hides Git Bash fell back to PowerShell and its hooks failed | Documented; the fallback observed on Windows with Claude Code 2.1.319 | hooks.md |

## What follows from these facts

- **A `CLAUDE.md` that grows is read less, not more.** Past 200 lines adherence drops; past the cutoff the rest is not
  read at all unless Claude decides to look. A repository whose conventions live in one growing file is applying a
  shrinking share of them, and nothing tells it so. bowline's doctor tells it so, naming the line and the section where
  the cut falls.
- **The home of a piece of knowledge follows how Claude Code loads it.** A rule that concerns one part of the code
  belongs in a scoped rules file, so it loads only then and loads whole. A procedure belongs in a skill, so its body
  costs nothing until it is used. A decision or a history belongs in a document, read when someone asks why. The root
  `CLAUDE.md` stays short because it is the one file every session pays for.
- **Memory is a working notebook, not a record.** It is personal by design, loads only its index at start, and is lost
  with the machine. What a project needs every contributor to know is promoted into the repository; what is personal
  stays, backed up to a private remote by a hook, and the index is kept short so the newest notes are not the ones
  that fall off.
- **A summary needs instructions.** Without a "Compact Instructions" section, a long session's state is kept or lost
  at the summary's discretion.

## Sources

- https://code.claude.com/docs/en/memory.md
- https://code.claude.com/docs/en/context-window.md
- https://code.claude.com/docs/en/settings-reference.md
- https://code.claude.com/docs/en/skills.md
- https://code.claude.com/docs/en/sessions.md
- https://code.claude.com/docs/en/how-claude-code-works.md
- https://code.claude.com/docs/en/large-codebases.md
- https://code.claude.com/docs/en/plugins-reference.md
- https://code.claude.com/docs/en/headless.md
- https://code.claude.com/docs/en/hooks.md
