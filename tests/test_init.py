"""The scaffolding on a scratch repository: the plan changes nothing, --write creates what is missing and appends the
missing sections, never overwrites, and a second run keeps everything."""

import json
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

    def test_a_root_file_in_the_claude_folder_gets_the_sections_and_no_second_file(self):
        write(os.path.join(self.repo, ".claude", "CLAUDE.md"), "# My project\n\nIt does things.\n\n## Compact Instructions\n\nKeep.\n")
        code, out, err = self.run_script("init", "--only", "claude-md")
        self.assertEqual(code, 0, out + err)
        self.assertIn(".claude/CLAUDE.md", out)
        self.assertIn("append sections: Where the rest of the rules are, Memory between sessions", out)
        code, out, err = self.run_script("init", "--write", "--only", "claude-md")
        self.assertEqual(code, 0, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "CLAUDE.md")))
        text = read(os.path.join(self.repo, ".claude", "CLAUDE.md"))
        self.assertTrue(text.startswith("# My project"))
        self.assertEqual(text.count("## Compact Instructions"), 1)
        self.assertIn("## Memory between sessions", text)

    def test_the_plan_offers_autosplit_with_its_cost_and_turns_it_on_only_when_asked(self):
        config = os.path.join(self.repo, ".claude", "bowline.json")
        code, out, err = self.run_script("init", "--plan", "--only", "config")
        self.assertEqual(code, 0, out + err)
        self.assertIn("off; --autosplit turns it on in the new file", out)
        self.assertIn("one split may spend up to $20 (autosplit.maxBudgetUsd)", out)
        self.assertIn("off by default because it spends money", out)
        code, out, err = self.run_script("init", "--write", "--only", "config")
        self.assertEqual(code, 0, out + err)
        self.assertFalse(json.loads(read(config))["autosplit"]["enabled"])

        os.remove(config)
        code, out, err = self.run_script("init", "--write", "--only", "config", "--autosplit")
        self.assertEqual(code, 0, out + err)
        self.assertIn("on in the new file (--autosplit)", out)
        self.assertTrue(json.loads(read(config))["autosplit"]["enabled"])
        # Only the one value differs from the template; its comments and its line breaks stay as they are.
        import init
        self.assertEqual(read(config), init.template("bowline.json").replace('"enabled": false', '"enabled": true'))
        code, out, _ = self.run_script("init", "--plan", "--only", "config")
        self.assertIn(".claude/bowline.json                     on\n", out)

        write(config, json.dumps({"autosplit": {"enabled": False}}))
        code, out, err = self.run_script("init", "--write", "--only", "config", "--autosplit")
        self.assertEqual(code, 0, out + err)
        self.assertIn("--autosplit changed nothing, because init never edits a file that exists", out)
        self.assertFalse(json.loads(read(config))["autosplit"]["enabled"])

        code, out, err = self.run_script("init", "--plan", "--only", "rules", "--autosplit")
        self.assertEqual(code, 2)
        self.assertIn("add config to --only", err)
        code, out, err = self.run_script("init", "--plan", "--only", "rules")
        self.assertNotIn("autosplit", out.lower())

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
