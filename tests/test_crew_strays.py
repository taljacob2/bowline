"""The Claude Code processes that no listed session owns, on a scratch repository with two worktrees and a made-up
table of processes: a process with Claude Code's own record of a session in a worktree is that worktree's session,
or gives a listed background session its process; one below a listed session, below Claude Desktop, resumed for a
listed session or asking for the list is owned; every other one is named with its start, its memory and its program,
says whether its owner could be found and that it runs as administrator, and is added to the memory line; and bowline
says how the person ends one, never ending one itself."""

import json
import os
import sys
import time
from unittest import mock

from support import ScratchRepo, assert_lines_fit, git, write

import common  # noqa: E402 - support puts the scripts on the path
import crew  # noqa: E402

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]
MB = 1024 * 1024


def flat(text):
    return " ".join(text.split())


class StrayTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"crew": {"claude": FAKE_CLAUDE}}) + "\n")
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.main, self.other = (tree["path"] for tree in crew.worktrees(self.repo))
        write(os.path.join(self.other, "src", "parser.py"), "half = 1\n")         # work, so its lines are written out
        # A folder among the worktrees that is no longer one: its worktree was removed while a session still ran there.
        self.removed = os.path.join(self.repo, ".claude", "worktrees", "removed")
        os.makedirs(self.removed)
        now = int(time.time() * 1000)
        write(self.agents_file, json.dumps([
            {"sessionId": "sess-push", "cwd": self.other, "kind": "interactive", "name": "the push", "status": "idle",
             "startedAt": now, "pid": 500},
            {"sessionId": "sess-nightly", "cwd": self.main, "kind": "background", "name": "nightly", "state": "blocked",
             "startedAt": now}]) + "\n")
        # Claude Code's own record of each process it runs, and the key file beside each, which is never read.
        sessions = os.path.join(common.config_dir(), "sessions")
        for pid, sid, name, cwd in ((700, "sess-admin", "the admin session", self.other),
                                    (710, "sess-nightly", "nightly", self.main),
                                    (720, "sess-left", "the session left behind", self.removed)):
            write(os.path.join(sessions, f"{pid}.json"), json.dumps({
                "pid": pid, "sessionId": sid, "cwd": cwd, "name": name, "kind": "interactive", "status": "idle",
                "startedAt": now - 3600 * 1000}) + "\n")
            write(os.path.join(sessions, f"{pid}.0123456789abcdef.key"), "not a record\n")
        self.started = time.time() - 6 * 24 * 3600

    def look(self):
        hidden = "claude.exe"                          # what WMI gives for the command line of an elevated process
        snapshot = [
            {"pid": 500, "ppid": 1, "name": "claude.exe", "command": "claude.exe --output-format stream-json", "memory": 100 * MB},
            {"pid": 501, "ppid": 500, "name": "claude.exe", "command": "claude.exe -p a question", "memory": 10 * MB},
            {"pid": 600, "ppid": 9999, "name": "claude.exe", "command": hidden, "memory": 300 * MB},
            {"pid": 601, "ppid": 600, "name": "claude.exe", "command": hidden, "memory": 50 * MB},
            {"pid": 602, "ppid": 601, "name": "node.exe", "command": "node server.js", "memory": 20 * MB},
            {"pid": 700, "ppid": 9999, "name": "claude.exe", "command": hidden, "memory": 200 * MB},
            {"pid": 710, "ppid": 9999, "name": "claude.exe", "command": hidden, "memory": 40 * MB},
            {"pid": 720, "ppid": 9999, "name": "claude.exe", "command": hidden, "memory": 70 * MB},
            {"pid": 800, "ppid": 1, "name": "Claude.exe",
             "command": r'"C:\Program Files\WindowsApps\Claude_5.1.0_x64__x\app\Claude.exe"', "memory": 400 * MB},
            {"pid": 801, "ppid": 800, "name": "claude.exe", "command": "claude.exe --output-format stream-json", "memory": 90 * MB},
            {"pid": 950, "ppid": 9999, "name": "claude.exe", "command": "claude agents --json", "memory": 30 * MB},
            {"pid": 960, "ppid": 9999, "name": "claude.exe", "command": "claude.exe --resume=sess-push", "memory": 30 * MB},
        ]
        details = {pid: {"started": self.started, "image": rf"C:\Users\x\.local\bin\claude.exe.old.1.{pid}",
                         "elevated": True} for pid in (600, 601, 700, 710, 720)}
        with mock.patch.object(crew, "processes", return_value=snapshot), \
                mock.patch.object(crew, "listening", return_value={}), \
                mock.patch.object(crew, "machine_memory", return_value={"total": 32 * 1024 * MB, "available": 8 * 1024 * MB}), \
                mock.patch.object(crew, "process_details", create=True,
                                  side_effect=lambda pids: {pid: details.get(pid, {"started": None, "image": None,
                                                                                   "elevated": None}) for pid in pids}):
            model = crew.look(crew.Place(self.repo))
        out = "\n".join(crew.render(model))
        assert_lines_fit(self, out)
        return model, out

    def test_a_claude_process_no_listed_session_owns_is_named_and_counted(self):
        model, out = self.look()
        text = flat(out)
        self.assertEqual([stray["pid"] for stray in model.get("strays", [])], [600, 601, 720])
        day = time.localtime(self.started)
        months = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December")
        when = f"{day.tm_mday} {months[day.tm_mon - 1]}" + (
            f" {day.tm_year}" if day.tm_year != time.localtime().tm_year else "") + time.strftime(" %H:%M", day)
        self.assertIn("Claude processes that no listed session owns: 3. No session that Claude Code or Claude Desktop "
                      "lists is one of them or started them. bowline never stops them; if you do not recognize one, "
                      "end it ", text)
        self.assertIn(f"pid 600, started {when}, 300 MB: C:\\Users\\x\\.local\\bin\\claude.exe.old.1.600. Its owner could "
                      "not be found. It runs as administrator, so its command line cannot be read from here.", text)
        self.assertIn(f"pid 601, started {when}, 50 MB: C:\\Users\\x\\.local\\bin\\claude.exe.old.1.601. It was started "
                      "by pid 600, above.", text)
        self.assertIn(f"Claude Code's own record names it \"the session left behind\", in {self.removed}, though its list "
                      "of sessions leaves it out. That folder's worktree was removed while this session still ran in it, "
                      "so git left the folder behind.", text)
        # The three, with the process they started: 300 + 50 + 20 + 70 MB.
        self.assertIn("the Claude processes that no listed session owns, above, hold 440 MB more.", text)
        # A process with Claude Code's record of a session in a worktree is that worktree's session.
        theirs = next(item for item in model["worktrees"] if item["display"] == "other")
        admin = next(s for s in theirs["sessions"] if s["id"] == "sess-admin")
        self.assertEqual((admin["pid"], admin["kind"], admin["status"], admin["elevated"]), (700, "unlisted", "idle", True))
        self.assertIn('session "the admin session": idle', text)
        self.assertIn("Claude Code's list of sessions leaves it out, and its own record of the running process names "
                      "it; it runs as administrator", text)
        # A background session Claude Code lists with no process gets the one its record names, and is not offline.
        mine = next(item for item in model["worktrees"] if item["main"])
        nightly = next(s for s in mine["sessions"] if s["id"] == "sess-nightly")
        self.assertEqual((nightly["pid"], nightly["status"]), (710, "idle"))
        self.assertIn('"nightly" (40 MB) (listed with no process, found by its record; runs as administrator)', text)
        self.assertEqual(model["counts"]["offline"], 0)
        # Owned: below a session (501), the app (800) and below it (801), a list asked now (950), a resumed session (960).
        for pid in (500, 501, 800, 801, 950, 960):
            self.assertNotIn(f"pid {pid},", text)

    def test_nothing_is_said_of_strays_when_the_sessions_cannot_be_listed(self):
        os.environ["FAKE_CLAUDE_AGENTS_FAIL"] = "1"
        model, out = self.look()
        self.assertEqual(model.get("strays", []), [])
        self.assertNotIn("no listed session owns", out)
