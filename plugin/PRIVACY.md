# Privacy

This page says what the bowline plugin reads, writes and sends, for anyone who installs it. It applies from bowline
0.6.2 on; what the crew reads and writes was added in 0.10.0, and its check before an edit in 0.11.0.

## Who is behind bowline, and what they receive

bowline is an open-source Claude Code plugin by Tal Jacob, under the MIT licence. It runs no service, has no server and
collects no telemetry. Its author receives nothing from your use of it: no data, no usage counts and no error reports.

## What leaves your machine

Two features send data off your machine. Each one is off until you turn it on.

- **The memory backup.** Once you run `/bowline:memory-backup` with a git remote of your choosing, the plugin's hooks
  push Claude Code's memory folder for the repository to that remote with git, after every reply and when a session
  ends. Nothing is pushed before you set it up, and `memory status` shows where the backup goes. Use a private
  repository, because the memory can hold personal data (see below).
- **Autosplit.** When a repository turns `autosplit` on in its `.claude/bowline.json`, bowline starts a headless Claude
  Code session on your machine to prepare the split of a `CLAUDE.md` that outgrew the limits. That session works like
  any Claude Code session: it signs in as you, and what it reads of the repository goes to Anthropic. It never starts
  in a repository that has not turned it on.

Nothing else bowline does reaches the network.

## What bowline reads

- The repository's instruction files: its `CLAUDE.md` files, rules and skills.
- The staged lines of a commit, when the commit gate runs.
- Claude Code's memory folder for the repository.
- A private list of words never to commit, at `~/.claude/private/never-commit.txt`, when that file exists.
- For the crew, which helps several sessions work in one repository: the list of the processes on your machine with
  their command lines, the memory each one holds and the TCP ports they listen on, and how much of the machine's
  memory is free, when you or Claude run `bowline crew` or `bowline crew run`;
  the files of the repository's other worktrees that the repository names as numbered lists, and the names of the
  files each worktree changed; the list of Claude Code's sessions on your machine that `claude agents --json` gives,
  with each session's name, folder, process id and whether it is busy, when you or Claude run `bowline crew`; and,
  at a session's start and before each prompt, when the transcript files in Claude Code's project folders for the
  repository's worktrees, and each worktree's own git folder, were last written. Of a transcript bowline reads only
  the session's title, from the last 256 KB of the file, to name a session when that list cannot be had; never the
  conversation. It keeps the names of the worktrees it has named to a session, in the repository's git folder, so
  that it names each one once; nothing of this is sent.
- From 0.16.0, when you or Claude run `bowline crew`, Claude Desktop's record of each of its Code sessions on your
  machine, every account's. Of each record bowline reads only the session's id in the app and in Claude Code, its
  title, whether it is archived, its folder, its worktree and when it was last active; never its settings, its
  tools or its conversation. It keeps none of it, and `crew.desktop: false` turns this off.
- From 0.16.0, when you or Claude run `bowline crew`, Claude Code's own record of each process it runs, the files
  `sessions/<process id>.json` in Claude Code's configuration folder, of which bowline reads only the session's id,
  title, folder, kind, state and start; the files beside them whose names end in `.key` are never opened. For a
  Claude Code process that no listed session owns, it also asks Windows for the path of its program, when it started
  and whether it runs as administrator, which Windows gives to any program of the same user. It keeps none of it.
- After each reply, the reply's text that Claude Code gives the hook, to see whether it ends with a question to you;
  only that last question is kept, and `crew.asksFromReply: false` turns this off. Before each prompt, which session
  it is, to take that question back.
- Before an edit that Claude makes with the Edit, Write or NotebookEdit tool: the path of the file, from the hook's
  input, to say whether another worktree of the repository holds that file. Never the file's content or the edit.

## What bowline writes

- The files `init` creates in a repository, when you ask it to.
- The state of autosplit and its log, and a small record of the reminders already shown, in the repository's own git
  folder; for a folder of repositories, the record of the reminders is in Claude Code's project folder for it.
- The commits of the memory backup, in the memory folder, once the backup is set up. From 0.10.0 each commit's message
  also names the session whose reply it follows, by the random identifier Claude Code gives it, so that bowline can
  tell when one session removed lines another had added; the identifier goes to your remote with the commit.
- The crew's claims, its turn for a heavy check, the list of the files each worktree changed, as last measured, the
  list of sessions `claude agents --json` last gave, the few sentences a session writes about its own work with
  `crew say`, and the question a session waits for you to answer (said with `crew say --asks`, or the last sentence
  of a reply that ends with a question, which Claude Code gives the hook after each reply), the order of the
  push queue, and the most memory each check run through `crew run` took, with its command line and how long it
  ran, in the repository's own git folder, on your machine only and never committed; and the list of memory removals you said were meant, in Claude Code's project
  folder for the repository.
- For the check before an edit, in the repository's own git folder: which warnings each session has already heard
  (the session's random identifier, the file's path and the worktrees named), kept for a day, and a marker while
  the worktrees are being measured.
- A hook entry in Claude Code's settings file, only when you run `memory setup` without the plugin.

## Personal data

The memory folder can hold personal details: Claude Code writes notes there about you and your work, such as your
role, your preferences and your links. bowline reads those notes to measure and sort the memory, and, once you set up
the backup, stores them as git commits in the memory folder and pushes them to your remote. bowline does not look for
names, email addresses or postal addresses, and it reads no one else's data.

## How long data is kept

bowline keeps nothing of its own. The memory backup's commits stay in the memory folder and in your remote for as long
as you keep them, and you delete them as you would any git repository. Autosplit's state and log stay in the
repository's git folder until `autosplit done` or `autosplit discard` removes them. What Anthropic keeps of a Claude
Code session is governed by your own agreement with Anthropic.

## Children

bowline is a developer tool and is not intended for anyone under 18.

## Questions and changes

Ask in the repository's issues: https://github.com/taljacob2/bowline/issues. A version of bowline that changes what it
reads, writes or sends says so in its changelog, and this page changes in the same version.
