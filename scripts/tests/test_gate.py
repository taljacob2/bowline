"""The gate on a scratch repository: six kinds of bad line, the policies, the hook mode, the sweep."""

import json
import os
import unittest

from support import ScratchRepo, git, write

FAKE_TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"   # built at runtime, never a literal token


class GateTests(ScratchRepo):
    def stage(self, name, lines):
        write(os.path.join(self.repo, name), "\n".join(lines) + "\n")
        git(self.repo, "add", name)

    def test_refuses_each_kind_and_names_only_file_and_line(self):
        never = os.path.join(self.root, "never.txt")
        write(never, "# a test list\nsecret-partner\n")
        self.stage("new.txt", [
            "a good line",                      # 1
            "token " + FAKE_TOKEN,              # 2 a token
            "ends with a return\r",             # 3 a carriage return
            "an em dash " + chr(0x2014) + " here",           # 4 outside ASCII: a warning under the default policy
            "the Secret-Partner name",          # 5 the never-commit list, case ignored
            "bell \x07 byte",                   # 6 a control character
            "a key AKIA" + "ABCDEFGHIJKLMNOP",  # 7 an AWS key id
            "middle dot " + chr(0xB7) + " is accepted",    # 8 accepted below through the configuration
        ])
        write(os.path.join(self.repo, ".claude", "keel.json"), json.dumps({"gate": {"acceptedCharacters": ["U+00B7"]}}))
        code, out, err = self.run_script("gate", "--never-commit", never)
        self.assertEqual(code, 1, out + err)
        hits = [l for l in out.splitlines() if l.startswith("new.txt:")]
        self.assertEqual(len(hits), 5, out)
        for prefix, word in {"new.txt:2": "GitHub token", "new.txt:3": "carriage return", "new.txt:5": "never-commit",
                             "new.txt:6": "control character", "new.txt:7": "AWS"}.items():
            self.assertTrue(any(h.startswith(prefix + ":") and word in h for h in hits), f"{prefix} {word}: {out}")
        self.assertIn("warning: new.txt:4: a character outside ASCII (U+2014)", out)
        self.assertNotIn("new.txt:8", out)
        self.assertNotIn(FAKE_TOKEN, out + err)
        self.assertNotIn("Secret-Partner", out + err)

    def test_refuse_policy_makes_non_ascii_a_problem(self):
        write(os.path.join(self.repo, ".claude", "keel.json"), json.dumps({"gate": {"nonAscii": "refuse"}}))
        self.stage("a.txt", ["caf" + chr(0xE9)])
        code, out, _ = self.run_script("gate")
        self.assertEqual(code, 1)
        self.assertIn("a.txt:1: a character outside ASCII (U+00E9)", out)

    def test_ignore_policy_and_any_line_endings(self):
        write(os.path.join(self.repo, ".claude", "keel.json"), json.dumps({"gate": {"nonAscii": "ignore", "lineEndings": "any"}}))
        self.stage("a.txt", ["caf" + chr(0xE9) + "\r"])
        code, out, _ = self.run_script("gate")
        self.assertEqual(code, 0, out)
        self.assertIn("nothing found", out)

    def test_a_batch_file_may_carry_carriage_returns(self):
        self.stage("tool.cmd", ["@echo off\r", "echo hi\r"])
        self.stage("notes.txt", ["a line\r"])
        code, out, _ = self.run_script("gate")
        self.assertEqual(code, 1, out)
        self.assertIn("notes.txt:1: a carriage return", out)
        self.assertNotIn("tool.cmd", out)

    def test_nothing_staged(self):
        code, out, _ = self.run_script("gate")
        self.assertEqual(code, 0)
        self.assertIn("nothing is staged", out)

    def test_sweep_reads_tracked_files(self):
        write(os.path.join(self.repo, "old.txt"), "a key AKIA" + "ABCDEFGHIJKLMNOP\n")
        git(self.repo, "add", "old.txt")
        git(self.repo, "commit", "-q", "-m", "old")
        code, out, _ = self.run_script("gate")
        self.assertEqual(code, 0, out)                       # nothing staged: the old line does not stop a commit
        code, out, _ = self.run_script("gate", "--all")
        self.assertEqual(code, 1, out)
        self.assertIn("old.txt:1: an AWS access key id", out)

    def test_hook_mode_blocks_only_a_commit_command(self):
        self.stage("new.txt", ["token " + FAKE_TOKEN])
        import subprocess, sys
        from support import SCRIPTS
        for command, expected in (("git commit -m x", 2), ("git status", 0), ("npm test", 0)):
            payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
            result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "gate.py"), "--hook"], input=payload,
                                    cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
            self.assertEqual(result.returncode, expected, f"{command}: {result.stdout} {result.stderr}")
            if expected == 2:
                self.assertIn("new.txt:1: a GitHub token", result.stderr)
                self.assertNotIn(FAKE_TOKEN, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
