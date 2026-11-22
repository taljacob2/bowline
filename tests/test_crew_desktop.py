"""The crew and Claude Desktop's record of its sessions, on a scratch repository with two worktrees and a scratch
folder of records where the app keeps them: a session the app records is named by its full title and given its id
in the app, by which a reply there links it, and the look, run inside a Claude Code session, ends with those links."""

import json
import os
import subprocess
import sys
import unittest

from support import SCRIPTS, ScratchRepo, git, write

import crew  # noqa: E402 - support puts the scripts on the path

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]
PARSER = "local_11111111-2222-3333-4444-555555555555"


def flat(text):
    return " ".join(text.split())


class DesktopTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        self.configure({})
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.main, self.other = (tree["path"] for tree in crew.worktrees(self.repo))
        # Where the app keeps its records on this system; support points it into the test's own folder.
        if os.name == "nt":
            base = os.environ["APPDATA"]
        elif sys.platform == "darwin":
            base = os.path.join(self.root, "Library", "Application Support")
        else:
            base = os.environ["XDG_CONFIG_HOME"]
        self.desktop = os.path.join(base, "Claude", "claude-code-sessions")
        self.assertTrue(crew.same(self.desktop).startswith(crew.same(self.root) + "/"), self.desktop)

    def configure(self, settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"),
              json.dumps({"crew": dict({"claude": FAKE_CLAUDE}, **settings)}) + "\n")

    def agents(self, *rows):
        write(self.agents_file, json.dumps(list(rows)) + "\n")

    def record(self, local_id, cli, title, folder, archived=False, account="account-1"):
        """A session's record as Claude Desktop writes it, with some of the fields the crew never reads."""
        write(os.path.join(self.desktop, account, "organization-1", local_id + ".json"), json.dumps({
            "sessionId": local_id, "cliSessionId": cli, "cwd": folder, "worktreePath": folder, "title": title,
            "isArchived": archived, "lastActivityAt": 1795313419720, "model": "a model",
            "enabledMcpTools": {"local:a-server:a-tool": True}, "remoteMcpServersConfig": [{"url": "https://example.invalid"}],
        }) + "\n")

    def crew(self, *args, env=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8",
                                env=dict(os.environ, **(env or {})))
        return result.returncode, result.stdout, result.stderr

    def test_a_session_the_app_records_has_its_full_title_and_its_link(self):
        # `claude agents` gives a session's Claude Code id and its title cut at 50 characters; a reply in Claude Desktop
        # links a session by the app's own id, which only the app's record holds.
        self.agents({"sessionId": "cli-parser", "cwd": self.other, "kind": "interactive", "pid": 4242, "status": "busy",
                     "name": "The parser keeps every comment and every blank l"},
                    {"sessionId": "cli-terminal", "cwd": self.main, "kind": "interactive", "pid": 4243, "status": "idle",
                     "name": "a session in a terminal"})
        self.record(PARSER, "cli-parser", "The parser keeps every comment and every blank line it reads", self.other)
        write(os.path.join(self.desktop, "account-1", "organization-1", "local_broken.json"), "not a record\n")
        code, out, err = self.crew(env={"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        self.assertIn('session "The parser keeps every comment and every blank line it reads": busy', text)
        links = text[text.index("SESSION LINKS"):]
        self.assertIn("SESSION LINKS: in a reply in Claude Desktop, link a session as [its title](#<its id>)", links)
        self.assertIn(f'#{PARSER} "The parser keeps every comment and every blank line it reads"', links)
        self.assertNotIn("a session in a terminal", links)                       # the app has no record of it
        self.assertNotIn("enabledMcpTools", out)
        for line in out.splitlines():
            self.assertLessEqual(len(line), 100, line)
        # A person's own terminal, and crew watch, go without the links; --json always has them.
        self.assertNotIn("SESSION LINKS", self.crew()[1])
        model = json.loads(self.crew("--json")[1])
        by = {item["display"]: item for item in model["worktrees"]}
        self.assertEqual(by["other"]["sessions"][0]["desktop"], PARSER)
        self.assertIsNone(by["the main checkout"]["sessions"][0]["desktop"])
        # crew.desktop false reads no record.
        self.configure({"desktop": False})
        model = json.loads(self.crew("--json")[1])
        session = next(item for item in model["worktrees"] if item["display"] == "other")["sessions"][0]
        self.assertEqual((session["name"], session["desktop"]), ("The parser keeps every comment and every blank l", None))


if __name__ == "__main__":
    unittest.main()
