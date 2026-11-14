"""A folder of repositories that keeps bowline's files itself: writeToRepositories false or a list of names in the
folder's .claude/bowline.json, so that init, move and autosplit write nothing into the repositories it leaves untouched,
and the doctor says why instead of asking for a fix; and a folder that is a git repository of its own, holding what
its repositories share without tracking them."""

import json
import os
import subprocess
import sys
import unittest

from support import SCRIPTS, ScratchRepo, git, read, write

FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")
LONG = "# Sub\n\n## First\n\n" + ("A rule, stated at length.\n" * 150) + "\n## Second\n\n" + ("More.\n" * 100)


class FolderKeepsTheFilesTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.workspace = os.path.join(self.root, "services")
        self.repo1 = self.make_repo("repo1", {"CLAUDE.md": "# repo1\n\nThe first service.\n", "sub/CLAUDE.md": LONG})
        self.repo2 = self.make_repo("repo2", {"CLAUDE.md": "# repo2\n\nThe second service.\n"})
        os.environ["FAKE_CLAUDE_LOG"] = os.path.join(self.root, "fake-claude-calls.log")
        os.environ["FAKE_CLAUDE_MODE"] = "split"

    def make_repo(self, name, files):
        repo = os.path.join(self.workspace, name)
        os.makedirs(repo)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "t@example.invalid")
        git(repo, "config", "user.name", "Test")
        for path, text in files.items():
            write(os.path.join(repo, path), text)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "init")
        return repo

    def bowline(self, *args, stdin=None, cwd=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), *args], input=stdin,
                                cwd=cwd or self.workspace, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def folder_config(self, data):
        write(os.path.join(self.workspace, ".claude", "bowline.json"), json.dumps(data))

    def untouched(self, repo):
        """The repository has no change and no new file, tracked or not, and no branch but main."""
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, capture_output=True,
                                text=True).stdout
        branches = subprocess.run(["git", "branch", "--format=%(refname:short)"], cwd=repo, capture_output=True,
                                  text=True).stdout.split()
        return status == "" and branches == ["main"]

    def test_init_leave_repositories_writes_only_into_the_folder(self):
        code, out, err = self.bowline("init", "--leave-repositories", "--plan")
        self.assertEqual(code, 0, out + err)
        self.assertIn(".claude/rules/before-a-commit.md", out)
        self.assertIn("bowline writes nothing into repo1, repo2", out)
        code, out, err = self.bowline("init", "--leave-repositories", "--write")
        self.assertEqual(code, 0, out + err)
        config = json.loads(read(os.path.join(self.workspace, ".claude", "bowline.json")))
        self.assertIs(config["writeToRepositories"], False)
        for path in ("CLAUDE.md", ".claude/README.md", ".claude/rules/before-a-commit.md", ".claude/skills/push/SKILL.md"):
            self.assertTrue(os.path.isfile(os.path.join(self.workspace, path)), path)
        text = read(os.path.join(self.workspace, "CLAUDE.md"))
        self.assertIn("a rule for one repository goes here too, in `.claude/rules/<repository>/`", text)
        self.assertIn("| `repo1/` | The first service. |", text)
        self.assertTrue(self.untouched(self.repo1) and self.untouched(self.repo2))
        code, out, err = self.bowline("init", "--each", "--write")
        self.assertEqual(code, 0, out + err)
        self.assertIn("bowline leaves repo1 untouched: the folder's .claude/bowline.json sets writeToRepositories to false; skipped.", out)
        self.assertIn("nothing to do", out)
        self.assertTrue(self.untouched(self.repo1) and self.untouched(self.repo2))
        code, out, err = self.bowline("init", "--write", cwd=self.repo1)
        self.assertEqual(code, 1, out + err)
        self.assertIn("Run init from the folder", err)
        self.assertTrue(self.untouched(self.repo1))

    def test_a_list_names_the_repositories_bowline_may_write_into(self):
        self.folder_config({"writeToRepositories": ["repo2"]})
        code, out, err = self.bowline("init", "--each", "--write", "--only", "config")
        self.assertEqual(code, 0, out + err)
        self.assertIn("lists in writeToRepositories the repositories bowline may write to, and repo1 is not one of them", out)
        self.assertTrue(self.untouched(self.repo1))
        self.assertTrue(os.path.isfile(os.path.join(self.repo2, ".claude", "bowline.json")))
        code, out, err = self.bowline("init", "--plan")
        self.assertIn("The folder's repositories repo2 get their own scaffold with --each.", out)
        self.assertIn("bowline writes nothing into repo1", out)

    def test_the_doctor_notes_why_instead_of_asking_for_a_fix(self):
        self.folder_config({"writeToRepositories": False})
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertEqual(code, 0, out + err)                                   # nothing the person could fix is a problem
        self.assertIn("NOTE  repo1: sub/CLAUDE.md has 257 lines", out)
        self.assertIn("bowline leaves repo1 untouched", out)
        self.assertIn("in the folder's .claude/rules/repo1/, with paths: [\"repo1/**\"]", out)
        self.assertNotIn("repo1: No commit gate is installed", out)
        code, out, err = self.bowline("doctor", "--brief", "--no-memory")
        self.assertNotIn("repo1", out)

    def test_move_and_autosplit_write_nothing_into_a_repository_left_untouched(self):
        self.folder_config({"writeToRepositories": False,
                            "autosplit": {"enabled": True, "command": [sys.executable, "-I", FAKE], "maxBudgetUsd": 3}})
        spec = os.path.join(self.root, "spec.json")
        write(spec, json.dumps({"pages": [{"target": "docs/first.md", "sections": ["First"]}]}))
        code, out, err = self.bowline("move", "run", "--file", "repo1/sub/CLAUDE.md", "--spec", spec)
        self.assertEqual(code, 1, out + err)
        self.assertIn("bowline leaves repo1 untouched", err)
        self.assertIn("Nothing was changed", err)
        code, out, err = self.bowline("autosplit", "run", "--file", "repo1/sub/CLAUDE.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("a split is a branch in it", err)
        hook = json.dumps({"cwd": self.workspace, "hook_event_name": "Stop"})
        code, out, err = self.bowline("autosplit", "--hook", stdin=hook)
        self.assertEqual(code, 0, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.repo1, ".git", "bowline")))
        self.assertTrue(self.untouched(self.repo1))
        code, out, err = self.bowline("autosplit", "status")
        self.assertIn("bowline leaves repo1 untouched", out)

    def test_a_folder_that_is_a_git_repository_of_its_own(self):
        git(self.workspace, "init", "-q", "-b", "main")
        git(self.workspace, "config", "user.email", "t@example.invalid")
        git(self.workspace, "config", "user.name", "Test")
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertIn("a folder of 2 repositories: repo1, repo2", out)
        code, out, err = self.bowline("init", "--leave-repositories", "--write")
        self.assertEqual(code, 0, out + err)
        ignore = read(os.path.join(self.workspace, ".gitignore"))
        self.assertIn("/repo1/", ignore)
        self.assertIn("/repo2/", ignore)
        self.assertIn("This folder is a git repository of its own", read(os.path.join(self.workspace, "CLAUDE.md")))
        git(self.workspace, "add", "-A")
        git(self.workspace, "commit", "-q", "-m", "what the services share")
        tracked = subprocess.run(["git", "ls-files"], cwd=self.workspace, capture_output=True, text=True).stdout.split()
        self.assertFalse([p for p in tracked if p.startswith(("repo1/", "repo2/"))], tracked)
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertIn("a folder of 2 repositories: repo1, repo2", out)
        self.assertIn("bowline leaves repo1 untouched", out)                  # the folder's own file applies to its children
        self.assertTrue(self.untouched(self.repo1) and self.untouched(self.repo2))

    def test_a_submodule_is_part_of_the_repository_not_a_repository_beside_it(self):
        git(self.workspace, "init", "-q", "-b", "main")
        git(self.workspace, "config", "user.email", "t@example.invalid")
        git(self.workspace, "config", "user.name", "Test")
        git(self.workspace, "add", "repo2")                                      # tracked: git records it as a gitlink
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertIn("a folder of 1 repository: repo1", out)


if __name__ == "__main__":
    unittest.main()
