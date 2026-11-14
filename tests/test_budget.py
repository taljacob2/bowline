"""The budget check on a scratch repository: every limit, the areas, the unscoped rules, the outside pointers."""

import json
import os
import unittest

from support import ScratchRepo, write


def rule(paths, body_lines, line="- **A rule.** It says why.\n"):
    front = "---\npaths:\n" + "".join(f'  - "{p}"\n' for p in paths) + "---\n\n" if paths else ""
    return front + "# A rule file\n\n" + line * body_lines


class BudgetTests(ScratchRepo):
    def test_within_limits_reports_areas(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n\nShort.\n")
        write(os.path.join(self.repo, ".claude", "rules", "webui", "a.md"), rule(["webui/**"], 10))
        write(os.path.join(self.repo, ".claude", "rules", "ps.md"), rule(["**/*.ps1"], 5))
        write(os.path.join(self.repo, ".claude", "rules", "always.md"), rule([], 5))
        write(os.path.join(self.repo, ".claude", "skills", "x", "SKILL.md"), "---\nname: x\n---\n# x\n")
        code, out, err = self.run_script("budget")
        self.assertEqual(code, 0, out + err)
        self.assertIn("within limits", out)
        self.assertIn("webui", out)
        self.assertIn("*.ps1", out)
        self.assertIn("unscoped, every session:", out)

    def test_each_limit_is_refused(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n" + "a line\n" * 205)
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), "# Sub\n\nSee C:\\Users\\someone\\notes.md for the rest.\n")
        big = rule(["webui/**"], 10, line="- **A long rule.** " + "x" * 4000 + "\n")        # about 40 KB
        write(os.path.join(self.repo, ".claude", "rules", "webui", "big.md"), big)
        write(os.path.join(self.repo, ".claude", "rules", "always.md"), rule([], 12, line="- **Everywhere.** " + "y" * 900 + "\n"))
        write(os.path.join(self.repo, ".claude", "skills", "x", "SKILL.md"), "---\nname: x\n---\n" + "step\n" * 505)
        code, out, _ = self.run_script("budget")
        self.assertEqual(code, 1, out)
        self.assertIn("CLAUDE.md has 206 lines", out)
        self.assertIn("sub/CLAUDE.md names a path outside the repository", out)
        self.assertIn("big.md has 40,", out)
        self.assertIn("scoped rules for webui load", out)
        self.assertIn("unscoped rules load", out)
        self.assertIn("SKILL.md has 508 lines", out)

    def test_repository_config_overrides_a_limit(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n" + "a line\n" * 150)
        code, out, _ = self.run_script("budget")
        self.assertEqual(code, 0, out)
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"limits": {"claudeMdLines": 100}}))
        code, out, _ = self.run_script("budget")
        self.assertEqual(code, 1, out)
        self.assertIn("the target is under 100", out)

    def test_untracked_files_count_too(self):
        write(os.path.join(self.repo, ".claude", "rules", "new.md"), rule([], 12, line="- **Everywhere.** " + "y" * 900 + "\n"))
        code, out, _ = self.run_script("budget")
        self.assertEqual(code, 1, out)
        self.assertIn("unscoped rules load", out)

    def test_only_files_named_exactly_claude_md_count(self):
        write(os.path.join(self.repo, "CLAUDE.md"), "# Root\n")
        write(os.path.join(self.repo, "notes", "old-CLAUDE.md"), "# Not loaded by Claude Code\n" + "line\n" * 300)
        code, out, err = self.run_script("budget")
        self.assertEqual(code, 0, out + err)
        self.assertIn("1 CLAUDE.md file(s)", out)


if __name__ == "__main__":
    unittest.main()
