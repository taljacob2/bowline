"""The Node launcher the plugin's hooks and skills start: it finds Python and passes the arguments, standard output,
standard input and the exit code through, as a hook needs. Skipped on a machine without node."""

import json
import os
import shutil
import subprocess
import unittest

from support import SCRIPTS, ScratchRepo, git, write

NODE = shutil.which("node")
LAUNCHER = os.path.join(SCRIPTS, "run.mjs")
FAKE_TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"   # built at runtime, never a literal token


@unittest.skipUnless(NODE, "node is not installed on this machine")
class LauncherTests(ScratchRepo):
    def launch(self, *args, stdin=""):
        result = subprocess.run([NODE, LAUNCHER, *args], input=stdin, cwd=self.repo, capture_output=True, text=True,
                                encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def test_passes_the_arguments_and_the_output_through(self):
        code, out, err = self.launch("doctor", "--no-memory")
        self.assertEqual(code, 0, out + err)
        self.assertIn("bowline doctor:", out)

    def test_passes_standard_input_and_the_exit_code_through_as_a_hook_needs(self):
        write(os.path.join(self.repo, "new.txt"), "token " + FAKE_TOKEN + "\n")
        git(self.repo, "add", "new.txt")
        commit = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": self.repo})
        code, out, err = self.launch("gate", "--hook", stdin=commit)
        self.assertEqual(code, 2, out + err)
        self.assertIn("new.txt:1: a GitHub token", err)
        self.assertNotIn(FAKE_TOKEN, out + err)
        status = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": self.repo})
        code, out, err = self.launch("gate", "--hook", stdin=status)
        self.assertEqual(code, 0, out + err)


if __name__ == "__main__":
    unittest.main()
