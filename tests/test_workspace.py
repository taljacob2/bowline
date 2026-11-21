"""bowline from a folder that is not a repository but holds several, as with services cloned side by side: the doctor,
the one-line finding, the budget and the gate over every repository with the repository named in each finding; the
memory keyed on the folder; autosplit started by the hook in the repository that turned it on; the reminders; and the
messages of init and move."""

import json
import os
import re
import subprocess
import sys
import unittest

from support import SCRIPTS, ScratchRepo, git, read, wait_for_split, write

FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")
LONG = "# Sub\n\n## First\n\n" + ("A rule, stated at length.\n" * 150) + "\n## Second\n\n" + ("More.\n" * 100)


class WorkspaceTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.workspace = os.path.join(self.root, "services")
        self.repo1 = self.make_repo("repo1", {"CLAUDE.md": "# repo1\n", "sub/CLAUDE.md": LONG})
        self.repo2 = self.make_repo("repo2", {"CLAUDE.md": "# repo2\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"})
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

    def hook_json(self, event="Stop", command=None):
        facts = {"cwd": self.workspace, "hook_event_name": event}
        if command:
            facts["tool_name"] = "Bash"
            facts["tool_input"] = {"command": command}
        return json.dumps(facts)

    def test_doctor_and_brief_name_the_repository_in_each_finding(self):
        code, out, err = self.bowline("doctor", "--no-memory")
        self.assertEqual(code, 1, out + err)
        self.assertIn("a folder of 2 repositories: repo1, repo2", out)
        self.assertIn("repo1: sub/CLAUDE.md has 257 lines", out)
        self.assertIn("repo1: CLAUDE.md: 1 lines", out)
        self.assertIn("repo2: CLAUDE.md: 9 lines", out)
        self.assertIn("services: The folder itself has no CLAUDE.md.", out)
        self.assertIn('repo1: CLAUDE.md has no "Compact Instructions" section', out)
        self.assertNotIn('repo2: CLAUDE.md has no "Compact Instructions"', out)
        write(os.path.join(self.workspace, "CLAUDE.md"), "# The services\n\nrepo1 and repo2.\n")
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertNotIn("has no CLAUDE.md", out)
        self.assertIn('services: CLAUDE.md has no "Compact Instructions" section', out)
        self.assertIn("services: CLAUDE.md: 3 lines", out)
        code, out, err = self.bowline("doctor", "--brief", "--no-memory")
        self.assertEqual(code, 0, err)
        self.assertIn("this folder's repositories", out)
        self.assertIn("- repo1: sub/CLAUDE.md has 257 lines", out)

    def test_budget_and_gate_cover_every_repository(self):
        code, out, _ = self.bowline("budget")
        self.assertEqual(code, 1, out)
        self.assertIn("repo1: sub/CLAUDE.md has 257 lines", out)
        write(os.path.join(self.repo1, "sub", "CLAUDE.md"), "# Sub\n\nShort.\n")
        code, out, _ = self.bowline("budget")
        self.assertEqual(code, 0, out)
        self.assertIn("across the folder and its 2 repositories", out)
        self.assertIn("  repo2: 1 CLAUDE.md file(s)", out)
        code, out, _ = self.bowline("gate", "--all")
        self.assertEqual(code, 0, out)
        self.assertIn("repo1:", out)
        self.assertIn("repo2:", out)
        self.assertIn("nothing found across 2 repositories", out)
        write(os.path.join(self.repo2, "bad.txt"), "a key AKIA" + "ABCDEFGHIJKLMNOP\n")
        git(self.repo2, "add", "bad.txt")
        code, out, _ = self.bowline("gate")
        self.assertEqual(code, 1, out)
        self.assertIn("repo2: bad.txt:1: an AWS access key id", out)
        self.assertNotIn("repo1: bad.txt", out)

    def test_memory_is_the_folders_and_init_and_move_say_where_to_go(self):
        code, out, _ = self.bowline("memory", "status")
        self.assertEqual(code, 0, out)                       # no memory folder yet: nothing to back up, nothing wrong
        self.assertIn("folder: " + self.workspace, out)
        self.assertIn("does not exist yet", out)
        name = re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(self.workspace))
        self.assertIn(os.path.join(self.config_dir, "projects", name, "memory"), out)
        code, out, err = self.bowline("init", "--plan")                                 # the folder's own scaffold
        self.assertEqual(code, 0, out + err)
        self.assertIn("get their own scaffold with --each", out)
        code, out, err = self.bowline("move", "plan", "--file", "repo1/sub/CLAUDE.md")      # the file's own repository
        self.assertEqual(code, 0, out + err)
        self.assertIn("First", out)
        code, out, err = self.bowline("move", "find-pointers", "--name", "sub/CLAUDE.md")
        self.assertEqual(code, 2)
        self.assertIn("pass --repo", err)
        code, out, err = self.bowline("move", "find-pointers", "--name", "sub/CLAUDE.md", "--repo", "repo1")
        self.assertEqual(code, 0, out + err)
        write(os.path.join(self.repo1, "new-index.md"), "# Sub, the index\n\nShort.\n")                       # the spec's index, from the repository
        write(os.path.join(self.root, "spec.json"), json.dumps({"pages": [{"target": "docs/conventions/sub.md", "sections": ["First", "Second"]}], "index": "new-index.md"}))
        code, out, err = self.bowline("move", "run", "--file", "repo1/sub/CLAUDE.md", "--spec", os.path.join(self.root, "spec.json"))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(read(os.path.join(self.repo1, "sub", "CLAUDE.md")), "# Sub, the index\n\nShort.\n")
        self.assertTrue(os.path.isfile(os.path.join(self.repo1, "docs", "conventions", "sub.md")))

    def test_the_hook_starts_autosplit_in_the_repository_that_turned_it_on(self):
        write(os.path.join(self.repo1, ".claude", "bowline.json"),
              json.dumps({"autosplit": {"enabled": True, "command": [sys.executable, "-I", FAKE], "maxBudgetUsd": 2}}))
        git(self.repo1, "add", ".claude/bowline.json")
        git(self.repo1, "commit", "-q", "-m", "autosplit on in repo1")
        code, out, err = self.bowline("autosplit", "--hook", stdin=self.hook_json())
        self.assertEqual((code, out, err), (0, "", ""))
        state_file = os.path.join(self.repo1, ".git", "bowline", "autosplit", "sub-CLAUDE-md.json")
        state = wait_for_split(self, state_file)
        self.assertEqual(state["state"], "ready", json.dumps(state, indent=1))
        self.assertFalse(os.path.exists(os.path.join(self.repo2, ".git", "bowline")))
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("repo1: A split of sub/CLAUDE.md is ready on the branch bowline/split/sub-CLAUDE-md", out)
        code, out, _ = self.bowline("autosplit", "status")
        self.assertIn("ready on the branch", out)
        code, out, _ = self.bowline("autosplit", "show", "--file", "sub/CLAUDE.md", "--repo", "repo1")
        self.assertEqual(code, 0, out)
        self.assertIn("git cherry-pick", out)
        code, out, err = self.bowline("autosplit", "show", "--file", "repo1/sub/CLAUDE.md")       # the file's path names the repository
        self.assertEqual(code, 0, out + err)
        self.assertIn("git cherry-pick", out)
        code, out, err = self.bowline("autosplit", "show", "--file", "sub/CLAUDE.md")             # a bare name from the folder
        self.assertEqual(code, 2)
        self.assertIn("give the file as a path from here", err)
        code, out, err = self.bowline("autosplit", "discard", "--file", "repo1/sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        self.assertFalse(os.path.exists(state_file))

    def test_a_shared_config_in_the_folder_applies_to_its_repositories(self):
        write(os.path.join(self.workspace, ".claude", "bowline.json"), json.dumps({"limits": {"claudeMdLines": 5}}))
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("repo2: CLAUDE.md has 9 lines; the target is under 5", out)
        write(os.path.join(self.repo2, ".claude", "bowline.json"), json.dumps({"limits": {"claudeMdLines": 50}}))
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertNotIn("repo2: CLAUDE.md has 9 lines", out)
        self.assertIn("with .claude/bowline.json in services, repo2", out)

    def test_reminders_from_the_folder_name_the_repository(self):
        code, out, err = self.bowline("doctor", "--brief", "--no-memory")           # a session starts in the folder
        self.assertEqual(code, 0, err)
        write(os.path.join(self.repo2, "CLAUDE.md"), "# repo2\n\n" + "A line.\n" * 205)   # repo2's file crosses the target
        code, out, err = self.bowline("doctor", "--watch", "--no-memory", stdin=self.hook_json("Stop"))
        self.assertEqual(code, 0, err)
        message = json.loads(out)["systemMessage"]
        self.assertIn("repo2: CLAUDE.md has 207 lines", message)
        self.assertNotIn("repo1: sub/CLAUDE.md", message)                             # that one was said at the start
        code, out, _ = self.bowline("doctor", "--pending", stdin=self.hook_json("UserPromptSubmit"))
        self.assertIn("repo2: CLAUDE.md has 207 lines", out)
        name = re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(self.workspace))
        self.assertTrue(os.path.isfile(os.path.join(self.config_dir, "projects", name, "bowline", "watch.json")))

    def test_init_scaffolds_the_folder_itself_and_each_repository_on_request(self):
        code, out, err = self.bowline("init", "--plan")
        self.assertEqual(code, 0, out + err)
        self.assertIn("bowline init: " + self.workspace, out)
        self.assertIn("CLAUDE.md", out)
        self.assertIn(".claude/bowline.json", out)
        self.assertIn("Its 2 repositories (repo1, repo2) get their own scaffold with --each.", out)
        self.assertFalse(os.path.exists(os.path.join(self.workspace, "CLAUDE.md")))
        code, out, err = self.bowline("init", "--write")
        self.assertEqual(code, 0, out + err)
        text = read(os.path.join(self.workspace, "CLAUDE.md"))
        self.assertIn("It holds 2 repositories side by side", text)
        self.assertIn("| `repo1/` | (say in a line what it is) |", text)            # repo1's CLAUDE.md is a heading only
        self.assertIn("| `repo2/` | (say in a line what it is) |", text)            # "Keep." is in a section, not a description
        self.assertIn("## Compact Instructions", text)
        self.assertIn("one memory for the whole folder", text)
        self.assertLess(len(text.splitlines()), 200)
        self.assertTrue(os.path.isfile(os.path.join(self.workspace, ".claude", "bowline.json")))
        code, out, _ = self.bowline("init", "--plan")
        self.assertIn("kept (has every section)", out)
        self.assertIn("kept (exists)", out)
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertNotIn("has no CLAUDE.md", out)
        self.assertNotIn('services: CLAUDE.md has no "Compact Instructions"', out)
        code, out, err = self.bowline("init", "--each", "--plan")
        self.assertEqual(code, 0, out + err)
        self.assertIn("bowline init: " + self.repo1, out)
        self.assertIn("bowline init: " + self.repo2, out)
        self.assertFalse(os.path.exists(os.path.join(self.repo1, ".claude", "bowline.json")))
        code, out, err = self.bowline("init", "--each", "--write", "--only", "config,rules")
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(os.path.join(self.repo1, ".claude", "bowline.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.repo2, ".claude", "rules", "before-a-commit.md")))
        code, out, err = self.bowline("init", "--only", "githook")                   # needs the folder to be a repository
        self.assertEqual(code, 2)
        self.assertIn("this folder is not a git repository", err)
        self.assertIn("git init", err)


if __name__ == "__main__":
    unittest.main()
