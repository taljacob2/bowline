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
PYTHON_BESIDE_NODE = bool(NODE) and any(shutil.which(name, path=os.path.dirname(NODE)) for name in ("python", "python3", "py"))
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

    def edit(self, path, python=True):
        """The check before an edit, started the way the hook starts it. Without python, the launcher is given a PATH
        that holds only node's folder, so a clean answer proves that Python was never started for it."""
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit", "session_id": "launcher",
                              "cwd": self.root, "tool_input": {"file_path": path}})
        env = dict(os.environ)
        if not python:
            env["PATH"] = os.path.dirname(NODE)
        result = subprocess.run([NODE, LAUNCHER, "crew", "before-edit", "--hook"], input=payload, cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8", env=env)
        return result.returncode, result.stdout, result.stderr

    @unittest.skipIf(PYTHON_BESIDE_NODE, "python sits in node's own folder here, so a PATH without it cannot be made")
    def test_an_edit_in_a_repository_with_one_worktree_never_starts_python(self):
        for path in (os.path.join(self.repo, "README.md"), os.path.join(self.repo, "new", "deep", "file.txt"),
                     os.path.join(self.root, "outside", "any.txt"), "relative.txt"):
            self.assertEqual(self.edit(path, python=False), (0, "", ""), path)
        result = subprocess.run([NODE, LAUNCHER, "crew", "before-edit", "--hook"], input="not json", cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PATH=os.path.dirname(NODE)))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_an_edit_beside_another_worktree_reaches_python_with_its_standard_input(self):
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        other = os.path.join(self.repo, ".claude", "worktrees", "other")
        write(os.path.join(other, "README.md"), "# Changed in the other worktree\n")
        subprocess.run([NODE, LAUNCHER, "crew", "refresh"], cwd=self.repo, check=True, capture_output=True)
        code, out, err = self.edit(os.path.join(self.repo, "README.md"))
        self.assertEqual(code, 0, out + err)
        self.assertIn("README.md is also held by another worktree", json.loads(out)["hookSpecificOutput"]["additionalContext"])
        # From the worktree's side its .git is a file, so the launcher leaves the answer to Python, which is silent here.
        self.assertEqual(self.edit(os.path.join(other, "README.md"))[:2], (0, ""))


if __name__ == "__main__":
    unittest.main()
