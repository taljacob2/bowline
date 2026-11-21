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
        self.assertIn("/bowline:split-instructions", out)

    def test_brief_says_nothing_when_clean_and_one_line_per_problem(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n")
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")
        self.assertEqual((code, err), (0, ""))
        # Clean: no finding, and the one line every session's start gets about working beside other sessions.
        self.assertNotIn("bowline found", out)
        self.assertEqual(len(out.splitlines()), 1, out)
        self.assertIn("bowline: no other Claude Code session shows a sign of work in this repository right now.", out)
        write(os.path.join(self.repo, ".claude", "bowline.json"), '{"crew": {"assumeOthers": false}}\n')
        self.assertEqual(self.run_script("doctor", "--brief", "--no-memory"), (0, "", ""))
        os.remove(os.path.join(self.repo, ".claude", "bowline.json"))
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), "# Sub\n\n## First\n\n" + ("words " * 20 + "\n") * 400 + "## Second\n\nx\n")
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")
        self.assertEqual(code, 0, out + err)
        self.assertIn("run /bowline:doctor", out)
        self.assertIn("sub/CLAUDE.md is cut at line", out)
        self.assertLessEqual(len(out.strip().splitlines()), 4)

    def test_a_small_repository_gets_notes_not_problems(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n\nShort.\n")
        code, out, _ = self.run_script("doctor", "--no-memory")
        self.assertEqual(code, 0, out)
        self.assertIn('has no "Compact Instructions" section', out)
        self.assertIn("No commit gate is installed", out)
        self.assertIn("0 problem(s)", out)

    def test_a_root_file_in_the_claude_folder_is_the_root_file(self):
        # Claude Code reads .claude/CLAUDE.md whole, like CLAUDE.md: it is never cut, and its sections count.
        wide = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n\n## Wide\n\n"
        write(os.path.join(self.repo, ".claude", "CLAUDE.md"), wide + ("words " * 400 + "\n") * 20)
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("no root CLAUDE.md", out)
        self.assertNotIn("is cut at line", out)
        self.assertNotIn('"Compact Instructions" section', out)
        self.assertNotIn("what the memory folder is for", out)
        write(os.path.join(self.repo, ".claude", "CLAUDE.md"), "# Root\n\nShort.\n")
        code, out, _ = self.run_script("doctor", "--no-memory")
        self.assertIn('.claude/CLAUDE.md has no "Compact Instructions" section', out)
        write(os.path.join(self.repo, "CLAUDE.md"), "# Also root\n\n## Compact Instructions\n\nKeep.\n")
        code, out, _ = self.run_script("doctor", "--no-memory")
        self.assertNotIn('"Compact Instructions" section', out)
        self.assertIn("CLAUDE.md and .claude/CLAUDE.md do not say what the memory folder is for", out)

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

    def test_a_note_that_keeps_finished_work_like_a_log_is_a_warning_that_reaches_the_session_start(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n")
        folder = self.project_memory()
        write(os.path.join(folder, "MEMORY.md"), "- [Progress](progress.md) - the rounds\n")
        git(folder, "init", "-q", "-b", "main")
        git(folder, "remote", "add", "origin", "git@example.invalid:someone/memory.git")
        write(os.path.join(self.config_dir, "settings.json"), json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python", "args": ["-I", "x/push-memory.py"]}]}]}}))
        # Ids and paths are not commits: the front matter's session id, a UUID in the body, a job folder in a path.
        front = "---\nname: progress\nmetadata:\n  originSessionId: 1f080fe8-8cad-4ee8-a287-31c4d804b64e\n---\n"
        ids = "Session 2b7e1d40-5c3a-4f19-9d2e-8a1b3c4d5e6f, scratch C:\\jobs\\8d8686c0\\tmp, run /tmp/9e9e9e9e/x.\n"
        rounds = "".join(f"- round {i} done in `{i:03d}c0ffee`\n" for i in range(9))
        write(os.path.join(folder, "progress.md"), front + ids + rounds)
        code, out, _ = self.run_script("doctor")
        self.assertNotIn("names 9 commits", out)
        self.assertNotIn("like a log", out)
        write(os.path.join(folder, "progress.md"), front + ids + rounds + "- round 9 done in `009dead1`\n")
        code, out, _ = self.run_script("doctor")
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING  The memory note progress.md names 10 commits: it keeps finished work like a log.", out)
        self.assertIn("/bowline:curate-memory", out)
        code, out, _ = self.run_script("doctor", "--brief")
        self.assertIn("progress.md names 10 commits", out)

    def test_entry_point_dispatches(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n")
        from support import SCRIPTS
        import sys
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "budget"], cwd=self.repo,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("within limits", result.stdout)
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "nonsense"], cwd=self.repo,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown command", result.stderr)


if __name__ == "__main__":
    unittest.main()
