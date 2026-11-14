"""The scaffolding on a scratch repository: the plan changes nothing, --write creates what is missing and appends the
missing sections, never overwrites, and a second run keeps everything."""

import os
import unittest

from support import ScratchRepo, read, write


class InitTests(ScratchRepo):
    def test_plan_then_write_then_keep(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# My project\n\nIt does things.\n\n## Compact Instructions\n\nKeep the hashes.\n")
        write(os.path.join(self.repo, ".gitignore"), "bin/\n")
        code, out, err = self.run_script("init")
        self.assertEqual(code, 0, out + err)
        self.assertIn("append sections: Where the rest of the rules are, Memory between sessions", out)
        self.assertIn("would be made", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".claude", "README.md")))

        code, out, err = self.run_script("init", "--write")
        self.assertEqual(code, 0, out + err)
        text = read(os.path.join(self.repo, "CLAUDE.md"))
        self.assertTrue(text.startswith("# My project"))
        self.assertEqual(text.count("## Compact Instructions"), 1)
        self.assertIn("## Where the rest of the rules are", text)
        self.assertIn("## Memory between sessions", text)
        self.assertIn("Keep the hashes.", text)
        for path in (".claude/README.md", ".claude/rules/before-a-commit.md", ".claude/rules/recording-decisions.md",
                     ".claude/skills/full-checks/SKILL.md", ".claude/skills/push/SKILL.md", ".claude/scripts/gate.py",
                     ".claude/scripts/budget.py", ".claude/scripts/common.py", ".claude/scripts/defaults.json",
                     ".githooks/pre-commit", ".claude/bowline.json"):
            self.assertTrue(os.path.isfile(os.path.join(self.repo, path)), path)
        ignore = read(os.path.join(self.repo, ".gitignore"))
        self.assertTrue(ignore.startswith("bin/\n"))
        self.assertIn(".claude/settings.local.json", ignore)

        write(os.path.join(self.repo, ".claude", "rules", "before-a-commit.md"), "# Mine\n")
        code, out, err = self.run_script("init", "--write")
        self.assertEqual(code, 0, out + err)
        self.assertIn("0 change(s) made", out)
        self.assertEqual(read(os.path.join(self.repo, ".claude", "rules", "before-a-commit.md")), "# Mine\n")

    def test_no_claude_md_gets_one_with_the_head(self):
        code, out, err = self.run_script("init", "--write", "--only", "claude-md,config")
        self.assertEqual(code, 0, out + err)
        text = read(os.path.join(self.repo, "CLAUDE.md"))
        self.assertTrue(text.startswith("# This repository, for every Claude Code session"))
        self.assertIn("## Compact Instructions", text)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".claude", "bowline.json")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".claude", "README.md")))

    def test_local_copies_run_on_their_own(self):
        self.run_script("init", "--write", "--only", "scripts")
        # The copy lives in the scratch repository; run it directly to check it finds its defaults beside itself.
        import subprocess, sys
        result = subprocess.run([sys.executable, "-I", os.path.join(self.repo, ".claude", "scripts", "budget.py")], cwd=self.repo,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("within limits", result.stdout)


if __name__ == "__main__":
    unittest.main()
