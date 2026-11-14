"""keel's one entry point. The launchers in bin/ run it; so can you:

    python -I scripts/keel.py doctor [--repo <path>] [--no-memory]
    python -I scripts/keel.py gate [--all | --hook] [--never-commit <file>]
    python -I scripts/keel.py budget [--repo <path>]

Each command is its own module beside this file and can be run directly with the same arguments.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COMMANDS = {
    "doctor": ("doctor", "measure a repository and this machine against what Claude Code reads"),
    "gate": ("gate", "refuse a commit whose added lines hold what must never be committed"),
    "budget": ("budget", "refuse an instruction file over the sizes Claude Code reads"),
}
LATER = {
    "memory": "round 2 of keel's plan brings the memory backup (setup, status, restore, push)",
    "init": "round 2 brings the scaffolding of the repository side",
    "move": "round 3 brings the move of an oversized CLAUDE.md into pages and rules",
}


def usage():
    print(__doc__.strip())
    print()
    for name, (_, words) in COMMANDS.items():
        print(f"  {name:8} {words}")
    return 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        return usage()
    name, rest = argv[0], argv[1:]
    if name in LATER:
        print(f"keel: '{name}' is not here yet: {LATER[name]}.", file=sys.stderr)
        return 2
    if name not in COMMANDS:
        print(f"keel: unknown command '{name}'.", file=sys.stderr)
        return usage()
    module = __import__(COMMANDS[name][0])
    return module.main(rest)


if __name__ == "__main__":
    sys.exit(main())
