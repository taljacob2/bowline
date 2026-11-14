"""The reminders during a session, on a scratch repository: the brief at a session's start records what it said, the
watch after a reply speaks once when something new crosses a limit and stays quiet as the file keeps growing, the
pending line reaches Claude at the next prompt exactly once, and a fixed finding that comes back is new again."""

import json
import os
import subprocess
import sys
import unittest

from support import SCRIPTS, ScratchRepo, git, write

ROOT = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"


class WatchTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        git(self.repo, "add", "CLAUDE.md")
        git(self.repo, "commit", "-q", "-m", "root")
        self.sub = os.path.join(self.repo, "sub", "CLAUDE.md")

    def hook(self, mode, event):
        """Runs the doctor the way a hook does: the event's JSON on standard input, the cwd named in it."""
        stdin = json.dumps({"cwd": self.repo, "hook_event_name": event})
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "doctor.py"), mode, "--no-memory"], input=stdin,
                                cwd=self.root, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def test_one_reminder_per_new_finding_and_once_for_claude(self):
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")        # a session starts; all is clean
        self.assertEqual((code, out, err), (0, "", ""))
        code, out, err = self.hook("--watch", "Stop")                                # a reply ends; nothing changed
        self.assertEqual((code, out, err), (0, "", ""))
        write(self.sub, "# Sub\n\n" + "A line.\n" * 205)                            # a file crosses the target mid-session
        code, out, err = self.hook("--watch", "Stop")
        self.assertEqual(code, 0, err)
        message = json.loads(out)["systemMessage"]
        self.assertIn("sub/CLAUDE.md has 207 lines", message)
        self.assertIn("/bowline:split-instructions", message)
        write(self.sub, "# Sub\n\n" + "A line.\n" * 230)                            # it keeps growing: the same finding
        code, out, err = self.hook("--watch", "Stop")
        self.assertEqual((code, out), (0, ""))
        code, out, err = self.hook("--pending", "UserPromptSubmit")                  # Claude hears it at the next prompt
        self.assertEqual(code, 0, err)
        self.assertIn("sub/CLAUDE.md has 207 lines", out)
        self.assertIn("tell the person", out)
        self.assertNotIn("{", out)
        code, out, err = self.hook("--pending", "UserPromptSubmit")                  # and only once
        self.assertEqual((code, out), (0, ""))
        write(self.sub, "# Sub\n\nShort.\n")                                         # fixed: quiet
        code, out, _ = self.hook("--watch", "Stop")
        self.assertEqual(out, "")
        write(self.sub, "# Sub\n\n" + "A line.\n" * 205)                            # over again: new again
        code, out, _ = self.hook("--watch", "Stop")
        self.assertIn("systemMessage", out)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".git", "bowline", "watch.json")))

    def test_the_first_watch_without_a_record_says_nothing_and_the_brief_resets_the_record(self):
        write(self.sub, "# Sub\n\n" + "A line.\n" * 205)
        code, out, err = self.hook("--watch", "Stop")                                # no record yet: the start said it
        self.assertEqual((code, out, err), (0, "", ""))
        code, out, _ = self.run_script("doctor", "--brief", "--no-memory")           # a new session: the brief says it
        self.assertIn("sub/CLAUDE.md has 207 lines", out)
        code, out, _ = self.hook("--watch", "Stop")                                  # and the watch does not repeat it
        self.assertEqual(out, "")
        code, out, _ = self.hook("--pending", "UserPromptSubmit")
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
