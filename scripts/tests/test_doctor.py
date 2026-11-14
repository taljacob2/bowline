"""The doctor on a scratch repository and a scratch Claude Code configuration folder."""

import json
import os
import re
import subprocess
import unittest

from support import ScratchRepo, git, write

sys_path_marker = None


class DoctorTests(ScratchRepo):
    def project_memory(self):
        """The memory folder the doctor expects for the scratch repository, made the way Claude Code names it."""
        name = re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(self.repo))
        folder = os.path.join(self.config_dir, "projects", name, "memory")
        os.makedirs(folder, exist_ok=True)
        return folder

    def test_cut_point_names_the_section_and_what_is_never_read(self):
        head = "# Nested\n\n## First\n\n" + ("words " * 20 + "\n") * 400          # about 48 KB before the second heading
        text = head + "## Second\n\n" + "more\n" * 50 + "## Third\n\nlast\n"
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), text)
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n\n## Compact Instructions\n\nKeep the state.\n\n## Memory between sessions\n\nShort.\n")
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertEqual(code, 1, out + err)
        self.assertIn("sub/CLAUDE.md is cut at line", out)
        self.assertIn("on a 200K context window", out)
        self.assertIn('inside the section "First"', out)
        self.assertIn("never read: Second, Third", out)
        self.assertIn("/keel:split-instructions", out)

    def test_a_small_repository_gets_notes_not_problems(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n\nShort.\n")
        code, out, _ = self.run_script("doctor", "--no-memory")
        self.assertEqual(code, 0, out)
        self.assertIn('has no "Compact Instructions" section', out)
        self.assertIn("No commit gate is installed", out)
        self.assertIn("0 problem(s)", out)

    def test_memory_checks(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n")
        code, out, _ = self.run_script("doctor")
        self.assertIn("has no project folder", out)
        folder = self.project_memory()
        write(os.path.join(folder, "MEMORY.md"), "".join(f"- [note {i}](n{i}.md) - a hook\n" for i in range(190)))
        code, out, _ = self.run_script("doctor")
        self.assertIn("near the cap", out)
        self.assertIn("is not backed up", out)
        write(os.path.join(folder, "MEMORY.md"), "".join(f"- [note {i}](n{i}.md) - a hook\n" for i in range(205)))
        code, out, _ = self.run_script("doctor")
        self.assertEqual(code, 1, out)
        self.assertIn("MEMORY.md has 205 lines", out)
        git(folder, "init", "-q", "-b", "main")
        code, out, _ = self.run_script("doctor")
        self.assertIn("git repository with no remote", out)
        git(folder, "remote", "add", "origin", "git@example.invalid:someone/memory.git")
        code, out, _ = self.run_script("doctor")
        self.assertIn("No hook pushes the memory folder", out)
        write(os.path.join(self.config_dir, "settings.json"), json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python", "args": ["-I", "x/push-memory.py"]}]}]}}))
        code, out, _ = self.run_script("doctor")
        self.assertNotIn("No hook pushes", out)

    def test_entry_point_dispatches(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n")
        from support import SCRIPTS
        import sys
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "keel.py"), "budget"], cwd=self.repo,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("within limits", result.stdout)
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "keel.py"), "move"], cwd=self.repo,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not here yet", result.stderr)
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "keel.py"), "nonsense"], cwd=self.repo,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown command", result.stderr)


if __name__ == "__main__":
    unittest.main()
