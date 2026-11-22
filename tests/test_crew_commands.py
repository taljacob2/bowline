"""A session's own command, on a scratch repository with two worktrees and a made-up table of processes: a session that
Claude Code calls idle while a command of its Bash or PowerShell tool still runs is at work, and the command is named
under it; a session with only its MCP servers, its console host and its shell's startup below it is not; the shell that
runs the look itself is never reported; and a background session that Claude Code lists with no process of its own is
offline, so it neither waits for the person nor counts among the sessions."""

import json
import os
import sys
import time
from unittest import mock

from support import ScratchRepo, assert_lines_fit, git, write

import crew  # noqa: E402 - support puts the scripts on the path

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]

# The shell Claude Code starts for a command of its Bash tool, as Git Bash shows it on Windows.
BASH_TOOL = ('bash.exe -c "source /c/Users/x/.claude/shell-snapshots/snapshot-bash-1.sh 2>/dev/null || true && '
             "eval '{}' < /dev/null && pwd -P >| /c/Users/x/AppData/Local/Temp/claude-a4d7-cwd\"")
# The one it starts for its PowerShell tool, whose script is in a variable and never on the command line.
POWERSHELL_TOOL = ('cmd.exe /d /s /c ""chcp.com" 65001 >nul & "powershell.exe" -NoProfile -NonInteractive -Command '
                   '"$s = $env:CLAUDE_CODE_SHELL_LAUNCHER_SCRIPT; Invoke-Expression -Command $s" > "tasks\\b1.output" 2>&1"')


class CommandTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"crew": {"claude": FAKE_CLAUDE}}) + "\n")
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.main, self.other = crew.worktrees(self.repo)
        write(os.path.join(self.other["path"], "src", "parser.py"), "half = 1\n")     # work the worktree holds
        self.session(500)

    def session(self, pid, **row):
        """The one session Claude Code lists: idle, in the other worktree, with its claude process at pid."""
        listed = dict({"sessionId": "sess-push", "cwd": self.other["path"], "kind": "interactive", "name": "the push",
                       "status": "idle", "startedAt": int(time.time() * 1000)}, pid=pid, **row)
        write(self.agents_file, json.dumps([{key: value for key, value in listed.items() if value is not None}]) + "\n")

    def look(self, *below):
        """The model and the printout of a look, with the processes below the session's claude process given."""
        claude = {"pid": 500, "ppid": 1, "name": "claude.exe", "command": "claude.exe --output-format stream-json"}
        snapshot = [claude, {"pid": 501, "ppid": 500, "name": "conhost.exe", "command": r"\??\C:\WINDOWS\system32\conhost.exe 0x4"}]
        snapshot += [dict({"name": "bash.exe", "memory": None}, **process) for process in below]
        with mock.patch.object(crew, "processes", return_value=snapshot), \
                mock.patch.object(crew, "listening", return_value={}):
            model = crew.look(crew.Place(self.repo))
        out = "\n".join(crew.render(model))
        assert_lines_fit(self, out)
        tree = next(item for item in model["worktrees"] if item["display"] == "other")
        return tree, " ".join(out.split())

    def test_an_idle_session_whose_background_command_runs_is_at_work(self):
        tree, out = self.look(
            {"pid": 510, "ppid": 500, "command": BASH_TOOL.format(f'cd \\"{self.other["path"]}\\" && git push origin main')},
            # Git Bash starts a second bash below the first, and its programs name a parent that has already exited.
            {"pid": 511, "ppid": 510, "command": BASH_TOOL.format("git push origin main")},
            {"pid": 512, "ppid": 9999, "name": "git.exe", "command": "git push origin main"})
        self.assertEqual((tree["group"], tree["reason"]), ("work", "command"))
        self.assertEqual(tree["sessions"][0]["commands"], [{"pid": 510, "command": "git push origin main"}])
        self.assertIn("AT WORK other: a background command runs, its session idle", out)
        self.assertIn('session "the push": idle', out)
        self.assertIn("runs in the background: git push origin main", out)
        self.assertIn("holds: 1 untracked file, written less than a minute ago", out)  # what it holds is still said
        self.assertIn("WAITS FOR YOU: nothing.", out)

    def test_a_command_of_the_powershell_tool_is_named_by_what_runs_below_it(self):
        tree, out = self.look(
            {"pid": 520, "ppid": 500, "name": "cmd.exe", "command": POWERSHELL_TOOL},
            {"pid": 521, "ppid": 520, "name": "conhost.exe", "command": "conhost.exe 0x4"},
            {"pid": 522, "ppid": 520, "name": "powershell.exe", "command": "powershell.exe -NoProfile -Command $s"},
            {"pid": 523, "ppid": 522, "name": "dotnet.exe", "command": "dotnet test morgana.sln"},
            {"pid": 530, "ppid": 500, "name": "cmd.exe", "command": POWERSHELL_TOOL})       # Start-Sleep runs no program
        self.assertEqual((tree["group"], tree["reason"]), ("work", "command"))
        self.assertEqual([command["command"] for command in tree["sessions"][0]["commands"]],
                         ["dotnet test morgana.sln", "a PowerShell command"])
        self.assertIn("other: 2 background commands run, its session idle", out)

    def test_a_session_with_only_its_mcp_servers_and_its_shells_startup_is_not_at_work(self):
        tree, out = self.look(
            {"pid": 540, "ppid": 500, "name": "node.exe", "command": "node C:/tools/mcp/server.js --stdio"},
            {"pid": 541, "ppid": 540, "name": "cmd.exe", "command": "cmd.exe /c npx -y @scope/mcp-files"},
            {"pid": 542, "ppid": 500, "name": "ace-mcp-server.exe", "command": "ace-mcp-server.exe"},
            # The shell's startup sources the person's profile and writes the snapshot; it evaluates no command.
            {"pid": 543, "ppid": 500, "command": 'bash.exe -c -l "source ~/.bashrc && declare -f > '
                                                 '/c/Users/x/.claude/shell-snapshots/snapshot-bash-2.sh"'})
        self.assertEqual(tree["sessions"][0]["commands"], [])
        self.assertEqual((tree["group"], tree["reason"]), ("waits", "idle-uncommitted"))
        self.assertIn("WAITS FOR YOU other: idle, with work not committed", out)
        self.assertNotIn("runs in the background", out)
        os.remove(os.path.join(self.other["path"], "src", "parser.py"))
        tree, out = self.look({"pid": 540, "ppid": 500, "name": "node.exe", "command": "node C:/tools/mcp/server.js"})
        self.assertEqual((tree["group"], tree["reason"]), ("idle", "idle"))
        self.assertIn('IDLE, HOLDING NOTHING: nothing to commit other: "the push"', out)

    def test_the_shell_that_runs_the_look_is_not_a_command_of_its_session(self):
        tree, _ = self.look({"pid": 550, "ppid": 500, "command": BASH_TOOL.format("python -I bowline.py crew")},
                            {"pid": os.getpid(), "ppid": 550, "name": "python.exe", "command": "python -I bowline.py crew"})
        self.assertEqual(tree["sessions"][0]["commands"], [])
        self.assertEqual(tree["reason"], "idle-uncommitted")

    def test_a_background_session_listed_with_no_process_is_offline_and_waits_for_nobody(self):
        # As Claude Code lists a background job whose last record says blocked when no process of it runs.
        self.session(None, kind="background", status=None, state="blocked", name="the nightly")
        tree, out = self.look()
        self.assertEqual((tree["sessions"][0]["status"], tree["sessions"][0]["was"]), ("offline", "blocked"))
        self.assertEqual((tree["group"], tree["reason"]), ("waits", "idle-uncommitted"))
        self.assertIn("WAITS FOR YOU other: offline, with work not committed", out)
        self.assertIn('session "the nightly": offline: Claude Code lists it as blocked from when it last ran, and no '
                      "process of it runs now", out)
        self.assertNotIn("is blocked", out)
        self.assertIn("2 worktrees and 0 sessions (1 more listed, offline):", out)
        # With its process listed, a blocked background session waits for the person as before.
        self.session(500, kind="background", status=None, state="blocked", name="the nightly")
        tree, out = self.look()
        self.assertEqual((tree["group"], tree["reason"]), ("waits", "blocked"))
        self.assertIn('session "the nightly": blocked in the background', out)
