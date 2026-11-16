"""bowline from a folder of many repositories: init's folder scaffold and the gate (whether the folder can hold it), the
table's descriptions chosen on purpose, the doctor grouping what repeats and printing as it goes, and lists of
repository names kept short. Every repository and every line in it is made up here."""

import json
import os
import subprocess
import sys
import unittest

from support import SCRIPTS, ScratchRepo, git, read, write

sys.path.insert(0, SCRIPTS)
import init  # noqa: E402

PLACEHOLDER = "(say in a line what it is)"


class ManyRepositoriesTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.folder = os.path.join(self.root, "workbench")
        self.repos = {}
        self.make_repo("warns", {"CLAUDE.md": "# warns\n\n**WAIT:** Ask before you change a generated file.\n\n"
                                              "The warns service keeps the price lists in step.\n"})
        self.make_repo("orders", {"CLAUDE.md": "# orders\n\nNEVER write code before the plan is agreed. Every task MUST "
                                               "follow these steps:\n\n1. Read the plan.\n"})
        self.make_repo("rules", {".claude/CLAUDE.md": "# rules\n\n- ALWAYS keep the old interface working\n- Run the "
                                                      "tests before a push\n\nRead these first:\n"})
        self.make_repo("invoices", {"CLAUDE.md": "# invoices\n\nThis service turns widget orders into invoices. It runs "
                                                 "every night, and nobody calls it by hand. A third sentence that makes "
                                                 "the paragraph longer than a table cell should ever be allowed to grow.\n"})
        self.make_repo("labels", {"README.md": "# labels\n\n[![build](https://example.invalid/badge.svg)](https://example.invalid)"
                                               "\n\nA made-up library that formats widget labels.\n"})
        self.make_repo("shop", {"package.json": json.dumps({"name": "shop", "description": "A made-up web front end for the widget shop."})})
        for name in ("empty1", "empty2", "empty3", "empty4", "empty5", "empty6"):
            self.make_repo(name, {})

    def make_repo(self, name, files):
        repo = os.path.join(self.folder, name)
        os.makedirs(repo)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "t@example.invalid")
        git(repo, "config", "user.name", "Test")
        for path, text in files.items():
            write(os.path.join(repo, path), text)
        if files:
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "init")
        self.repos[name] = repo
        return repo

    def bowline(self, *args):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), *args], cwd=self.folder,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def git_folder(self):
        git(self.folder, "init", "-q", "-b", "main")
        git(self.folder, "config", "user.email", "t@example.invalid")
        git(self.folder, "config", "user.name", "Test")

    # ---- Problem 1: the gate, and rules and skills that are true for the folder

    def test_a_plain_folder_offers_no_gate_and_its_rules_and_skills_do_not_lean_on_one(self):
        code, out, err = self.bowline("init", "--leave-repositories", "--plan")
        self.assertEqual(code, 0, out + err)
        self.assertIn("rules", out)
        self.assertIn("git init", out)                       # what git init would add: the gate and the .gitignore entries
        self.assertIn(".gitignore entries that keep the repositories out of the folder's history", out)
        code, out, err = self.bowline("init", "--leave-repositories", "--plan", "--only", "scripts,githook")
        self.assertEqual(code, 2)
        self.assertIn("this folder is not a git repository", err)
        self.assertIn("git init", err)
        code, out, err = self.bowline("init", "--leave-repositories", "--write", "--only", "claude-md,claude-readme,rules,skills,config")
        self.assertEqual(code, 0, out + err)
        rule = read(os.path.join(self.folder, ".claude", "rules", "before-a-commit.md"))
        self.assertNotIn(".claude/scripts/gate.py", rule)
        self.assertNotIn("this repository", rule)
        self.assertIn("a repository below this folder", rule)
        self.assertIn("No copy of the gate is installed in this folder", rule)
        for skill in ("full-checks", "push"):
            text = read(os.path.join(self.folder, ".claude", "skills", skill, "SKILL.md"))
            self.assertNotIn(".claude/scripts/", text, skill)
            self.assertNotIn("this repository", text, skill)
        self.assertNotIn("this repository", read(os.path.join(self.folder, ".claude", "README.md")))
        self.assertFalse(os.path.exists(os.path.join(self.folder, ".claude", "scripts")))

    def test_a_folder_that_is_a_git_repository_installs_the_gate_and_its_rule_names_it(self):
        self.git_folder()
        code, out, err = self.bowline("init", "--leave-repositories", "--plan")
        self.assertEqual(code, 0, out + err)
        self.assertIn(".claude/scripts/gate.py", out)
        self.assertIn(".githooks/pre-commit", out)
        code, out, err = self.bowline("init", "--leave-repositories", "--write")
        self.assertEqual(code, 0, out + err)
        for path in (".claude/scripts/gate.py", ".claude/scripts/budget.py", ".claude/scripts/common.py",
                     ".claude/scripts/defaults.json", ".githooks/pre-commit"):
            self.assertTrue(os.path.isfile(os.path.join(self.folder, path)), path)
        rule = read(os.path.join(self.folder, ".claude", "rules", "before-a-commit.md"))
        self.assertIn("python -I .claude/scripts/gate.py --repo <repository>", rule)
        self.assertNotIn("this repository", rule)
        git(self.folder, "add", "CLAUDE.md")
        local = subprocess.run([sys.executable, "-I", os.path.join(self.folder, ".claude", "scripts", "gate.py")],
                               cwd=self.folder, capture_output=True, text=True)
        self.assertEqual(local.returncode, 0, local.stdout + local.stderr)

    def test_rules_without_the_gate_in_a_git_folder_say_so_in_the_plan(self):
        self.git_folder()
        code, out, err = self.bowline("init", "--leave-repositories", "--plan", "--only", "rules,skills")
        self.assertEqual(code, 0, out + err)
        self.assertIn("without the gate: add scripts to install it", out)
        code, out, err = self.bowline("init", "--leave-repositories", "--write", "--only", "rules")
        self.assertEqual(code, 0, out + err)
        self.assertIn("No copy of the gate is installed in this folder",
                      read(os.path.join(self.folder, ".claude", "rules", "before-a-commit.md")))

    def test_a_repository_keeps_its_own_wording(self):
        code, out, err = self.bowline("init", "--repo", self.repos["empty1"], "--write", "--only", "rules")
        self.assertEqual(code, 0, out + err)
        rule = read(os.path.join(self.repos["empty1"], ".claude", "rules", "before-a-commit.md"))
        self.assertIn("These rules apply to every commit in this repository", rule)
        self.assertIn("python -I .claude/scripts/gate.py", rule)

    # ---- Problem 2: each row's description, chosen on purpose

    def test_a_description_is_a_sentence_and_never_a_warning_a_rule_or_a_list(self):
        self.assertEqual(init.describe(self.repos["warns"]), ("The warns service keeps the price lists in step.", "CLAUDE.md"))
        self.assertEqual(init.describe(self.repos["orders"]), (None, None))
        self.assertEqual(init.describe(self.repos["rules"]), (None, None))
        self.assertEqual(init.describe(self.repos["invoices"]),
                         ("This service turns widget orders into invoices. It runs every night, and nobody calls it by hand.", "CLAUDE.md"))
        self.assertEqual(init.describe(self.repos["labels"]), ("A made-up library that formats widget labels.", "README.md"))
        self.assertEqual(init.describe(self.repos["shop"]), ("A made-up web front end for the widget shop.", "package.json"))
        self.assertEqual(init.describe(self.repos["empty1"]), (None, None))

    def test_the_readme_comes_before_the_claude_md_and_a_long_sentence_is_never_cut(self):
        both = self.make_repo("both", {"README.md": "# both\n\nThe both service sends the widget newsletter.\n",
                                       "CLAUDE.md": "# both\n\nThe CLAUDE.md says something else.\n"})
        self.assertEqual(init.describe(both), ("The both service sends the widget newsletter.", "README.md"))
        long_one = self.make_repo("long", {"README.md": "# long\n\n" + "A sentence that goes on " + "and on " * 60 + "without end.\n"})
        self.assertEqual(init.describe(long_one), (None, None))

    def test_the_plan_says_where_each_row_came_from_and_no_describe_fills_none(self):
        code, out, err = self.bowline("init", "--leave-repositories", "--plan")
        self.assertEqual(code, 0, out + err)
        self.assertIn("the table's rows: from CLAUDE.md (2): invoices, warns; from README.md (1): labels; "
                      "from package.json (1): shop; for you to fill (8): empty1, empty2", out)
        code, out, err = self.bowline("init", "--leave-repositories", "--write", "--only", "claude-md")
        self.assertEqual(code, 0, out + err)
        text = read(os.path.join(self.folder, "CLAUDE.md"))
        self.assertIn("| `labels/` | A made-up library that formats widget labels. |", text)
        self.assertIn(f"| `orders/` | {PLACEHOLDER} |", text)
        self.assertNotIn("WAIT", text)
        self.assertNotIn("NEVER", text)
        self.assertNotIn("...", text)
        os.remove(os.path.join(self.folder, "CLAUDE.md"))
        code, out, err = self.bowline("init", "--leave-repositories", "--write", "--only", "claude-md", "--no-describe")
        self.assertEqual(code, 0, out + err)
        text = read(os.path.join(self.folder, "CLAUDE.md"))
        self.assertIn(f"| `labels/` | {PLACEHOLDER} |", text)
        self.assertIn("--no-describe", out)

    # ---- Problem 3: the doctor in a folder of many repositories

    def test_the_doctor_groups_what_repeats_and_verbose_restores_each(self):
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertEqual(code, 0, out + err)
        self.assertIn("WARNING  8 repositories have no root CLAUDE.md.", out)
        self.assertEqual(out.count("The repository has no root CLAUDE.md."), 0)
        self.assertEqual(out.count("Create one with the writing rules"), 1)       # the fix, once
        self.assertIn("in: empty1, empty2, empty3, empty4, empty5, empty6, labels, shop", out)
        self.assertNotIn("empty1: scoped rules per area: none; unscoped: 0; skills: 0", out)
        code, out, err = self.bowline("doctor", "--no-memory", "--verbose")
        self.assertEqual(code, 0, out + err)
        self.assertIn("empty1: The repository has no root CLAUDE.md.", out)
        self.assertIn("empty1: scoped rules per area: none; unscoped: 0; skills: 0", out)

    def test_the_doctor_says_how_far_it_is_and_folder_only_stops_at_the_folder(self):
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertIn("bowline doctor: measuring 12 repositories", err)
        self.assertIn("12 of 12 measured", err)
        code, out, err = self.bowline("doctor", "--no-memory", "--folder-only")
        self.assertEqual(code, 0, out + err)
        self.assertIn("workbench: The folder itself has no CLAUDE.md.", out)
        self.assertNotIn("have no root CLAUDE.md", out)
        self.assertNotIn("empty1: ", out)                    # named in the header, measured nowhere
        self.assertIn("--folder-only", out)

    def test_exit_codes_and_the_session_start_line_are_as_before(self):
        write(os.path.join(self.repos["warns"], "sub", "CLAUDE.md"), "# Sub\n\n## First\n\n" + "A rule.\n" * 60000)
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertEqual(code, 1, out + err)
        self.assertIn("PROBLEM  warns: sub/CLAUDE.md", out)
        code, out, err = self.bowline("doctor", "--brief", "--no-memory")
        self.assertEqual(code, 0, err)
        # As before this round: the count of every problem and warning, one by one, and the first three in the order
        # the doctor finds them.
        self.assertIn("bowline found 14 thing(s)", out)
        self.assertIn("- empty1: The repository has no root CLAUDE.md.", out)
        self.assertLessEqual(len(out.strip().splitlines()), 4)

    # ---- Problem 4: lists of names kept short

    def test_init_names_the_repositories_once_and_caps_the_list(self):
        code, out, err = self.bowline("init", "--leave-repositories", "--plan")
        self.assertEqual(code, 0, out + err)
        line = next(l for l in out.splitlines() if l.startswith("bowline writes nothing into"))
        self.assertIn("bowline writes nothing into its 12 repositories", line)
        self.assertIn("and 2 more", line)
        self.assertNotIn("warns", line)
        code, out, err = self.bowline("init", "--leave-repositories", "--write", "--only", "claude-md,config")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(out.count("bowline writes nothing into"), 1)
        self.assertNotIn("empty1", next(l for l in out.splitlines() if "Next:" in l))
        code, out, err = self.bowline("init", "--leave-repositories", "--plan", "--verbose")
        self.assertIn("warns", next(l for l in out.splitlines() if l.startswith("bowline writes nothing into")))

    # ---- The smaller points

    def test_the_folder_claude_md_reads_well(self):
        code, out, err = self.bowline("init", "--leave-repositories", "--write", "--only", "claude-md")
        self.assertEqual(code, 0, out + err)
        text = read(os.path.join(self.folder, "CLAUDE.md"))
        self.assertNotIn("\n\n\n", text)
        first = text.split("\n\n")[1]
        self.assertTrue(all(len(line) <= 120 for line in first.split("\n")), first)
        self.assertLessEqual(max(len(line) for line in first.split("\n")) - min(len(line) for line in first.split("\n")[:-1]), 30, first)


if __name__ == "__main__":
    unittest.main()
