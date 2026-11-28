"""bowline's one entry point. The plugin's hooks and skills run it through run.mjs beside it; so can you:

    python -I scripts/bowline.py doctor [--repo <path>] [--no-memory]
    python -I scripts/bowline.py gate [--all | --hook] [--never-commit <file>]
    python -I scripts/bowline.py budget [--repo <path>]
    python -I scripts/bowline.py memory setup|restore <remote> [--no-hook] | status | push [--hook] | losses [--meant <commit>]
    python -I scripts/bowline.py init [--plan | --write] [--only item,item]
    python -I scripts/bowline.py move plan --file <CLAUDE.md> | run --file <CLAUDE.md> --spec <json> [--check] | find-pointers --name <words> | pointers --spec <json> [--check] | place --spec <json> [--check]
    python -I scripts/bowline.py autosplit --hook | run --file <CLAUDE.md> | status | show --file <CLAUDE.md> | done --file <CLAUDE.md> | discard --file <CLAUDE.md>
    python -I scripts/bowline.py crew | claim <key> [--why <words>] [--new] | release <key>... | run -- <command> | after-rebase | after-push | before-edit --file <path>
    python -I scripts/bowline.py decisions find <word>... [--verbose] | records

Each command is its own module beside this file and can be run directly with the same arguments.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COMMANDS = {
    "doctor": ("doctor", "measure a repository and this machine against what Claude Code reads"),
    "gate": ("gate", "refuse a commit whose added lines hold what must never be committed"),
    "budget": ("budget", "refuse an instruction file over the sizes Claude Code reads"),
    "memory": ("memory", "back up the memory folder: setup <remote>, restore <remote>, status, push, losses"),
    "init": ("init", "scaffold the repository side: --plan to see, --write to do"),
    "move": ("move", "move an oversized CLAUDE.md into pages, rules and an index: plan, run --spec, find-pointers, pointers"),
    "autosplit": ("autosplit", "prepare the split of an oversized CLAUDE.md in the background, on a branch: --hook, run, status, show, done, discard"),
    "crew": ("crew", "work beside other sessions in one repository: who is here, claim, release, say, run -- <command>, after-rebase, after-push, before-edit"),
    "decisions": ("decisions", "where a subject was decided, before a question goes to the person: find <word>..., records"),
}
LATER = {}


def usage():
    print(__doc__.strip())
    print()
    for name, (_, words) in COMMANDS.items():
        print(f"  {name:9} {words}")
    return 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        return usage()
    name, rest = argv[0], argv[1:]
    if name in LATER:
        print(f"bowline: '{name}' is not here yet: {LATER[name]}.", file=sys.stderr)
        return 2
    if name not in COMMANDS:
        print(f"bowline: unknown command '{name}'.", file=sys.stderr)
        return usage()
    module = __import__(COMMANDS[name][0])
    return module.main(rest)


if __name__ == "__main__":
    sys.exit(main())
