"""Autosplit on a scratch repository, with a stand-in for the claude command (fake_claude.py beside this file) that
behaves like a headless session that did the split, did half of it, or did nothing. No real session is started."""

import json
import os
import subprocess
import sys
import time
import unittest

from support import SCRIPTS, ScratchRepo, git, read, write

FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")
LONG = "# Sub\n\n## First\n\n" + ("A rule, stated at length.\n" * 150) + "\n## Second\n\n" + ("More.\n" * 100)
ROOT = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"


class AutosplitTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.calls = os.path.join(self.root, "fake-claude-calls.log")
        os.environ["FAKE_CLAUDE_LOG"] = self.calls
        os.environ["FAKE_CLAUDE_MODE"] = "split"
        os.environ["CLAUDECODE"] = "1"                        # as in the environment of a real session's hook
        os.environ["CLAUDE_CODE_SESSION_ID"] = "the-parent"
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), LONG)
        git(self.repo, "add", "CLAUDE.md", "sub/CLAUDE.md")
        git(self.repo, "commit", "-q", "-m", "a long nested file")

    def enable(self, **extra):
        config = {"autosplit": dict({"enabled": True, "command": [sys.executable, "-I", FAKE], "maxBudgetUsd": 3}, **extra)}
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps(config))
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "autosplit on")

    def bowline(self, *args, stdin=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), *args], input=stdin,
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def hook(self):
        return self.bowline("autosplit", "--hook", stdin=json.dumps({"cwd": self.repo, "hook_event_name": "Stop"}))

    def git_out(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, encoding="utf-8").stdout

    def state_file(self):
        return os.path.join(self.repo, ".git", "bowline", "autosplit", "sub-CLAUDE-md.json")

    def state(self):
        with open(self.state_file(), encoding="utf-8") as handle:
            return json.load(handle)

    def wait_for_state(self, *kinds, seconds=120):
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                state = self.state()
                if state.get("state") in kinds:
                    return state
            except (OSError, ValueError):
                pass
            time.sleep(0.2)
        self.fail(f"no state in {kinds} within {seconds} seconds")

    def calls_made(self):
        if not os.path.isfile(self.calls):
            return []
        return [json.loads(line) for line in read(self.calls).splitlines() if line.strip()]

    def test_oversized_measures_as_the_doctor_does(self):
        import autosplit
        import common
        config = common.load_config(self.repo)
        over = autosplit.oversized(self.repo, config)
        self.assertEqual([(p, l) for p, l, _, _ in over], [("sub/CLAUDE.md", 257)])
        self.assertIn("over the target of 200", over[0][3])
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), "# Sub\n\n## Wide\n\n" + ("words " * 400 + "\n") * 20)
        over = autosplit.oversized(self.repo, config)
        self.assertEqual(len(over), 1)
        self.assertIn("cut at 40,000", over[0][3])
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), "# Sub\n\nShort.\n")
        self.assertEqual(autosplit.oversized(self.repo, config), [])

    def test_hook_does_nothing_when_off_when_the_file_is_dirty_or_inside_the_worker(self):
        code, out, err = self.hook()
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertFalse(os.path.exists(os.path.dirname(self.state_file())))
        self.enable()
        write(os.path.join(self.repo, "sub", "CLAUDE.md"), LONG + "edited\n")
        code, out, err = self.hook()
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertFalse(os.path.exists(self.state_file()))
        code, out, _ = self.bowline("autosplit", "status")
        self.assertEqual(code, 0, out)
        self.assertIn("autosplit: on", out)
        self.assertIn("has uncommitted changes", out)
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("autosplit has not started on sub/CLAUDE.md", out)
        git(self.repo, "checkout", "--", "sub/CLAUDE.md")
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("autosplit will start on sub/CLAUDE.md after the next reply", out)
        os.environ["BOWLINE_AUTOSPLIT_WORKER"] = "1"
        code, out, err = self.hook()
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertFalse(os.path.exists(self.state_file()))
        del os.environ["BOWLINE_AUTOSPLIT_WORKER"]
        self.assertEqual(self.calls_made(), [])

    def test_hook_prepares_the_split_on_a_branch_and_the_doctor_reports_it(self):
        self.enable()
        code, out, err = self.hook()
        self.assertEqual((code, out, err), (0, "", ""))
        state = self.wait_for_state("ready", "failed")
        self.assertEqual(state["state"], "ready", json.dumps(state, indent=1))
        # The person's checkout is untouched, and the worktree is gone.
        self.assertEqual(read(os.path.join(self.repo, "sub", "CLAUDE.md")), LONG)
        self.assertEqual(self.git_out("status", "--porcelain"), "")
        self.assertEqual(len(self.git_out("worktree", "list").strip().splitlines()), 1)
        # The branch holds the two commits and the short file.
        self.assertEqual(len(self.git_out("log", "--format=%s", "main..bowline/split/sub-CLAUDE-md").strip().splitlines()), 2)
        self.assertEqual(len(state["commits"]), 2)
        self.assertEqual(state["before"]["lines"], 257)
        self.assertLess(state["after"]["lines"], 10)
        self.assertEqual(state["files"]["pages"], 1)
        self.assertEqual(state["files"]["rules"], 1)
        self.assertEqual(state["cost_usd"], 0.42)
        self.assertEqual(state["session_id"], "fake-session")
        # The session was started unattended, in the worktree, with the cost cap and the worker's mark.
        calls = self.calls_made()
        self.assertEqual(len(calls), 1)
        argv = calls[0]["argv"]
        self.assertEqual(argv[argv.index("--permission-prompts") + 1], "none")
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "3")
        self.assertIn("Bash(git *)", argv[argv.index("--allowedTools") + 1])
        self.assertNotEqual(os.path.normcase(os.path.realpath(calls[0]["cwd"])), os.path.normcase(self.repo))
        self.assertEqual(calls[0]["worker"], "1")
        self.assertIsNone(calls[0]["claudecode"])
        self.assertIsNone(calls[0]["parent_session"])
        self.assertIn("Unattended: the background worker", argv[-1])
        self.assertIn("sub/CLAUDE.md", argv[-1])
        # A second reply starts no second worker.
        self.hook()
        time.sleep(1)
        self.assertEqual(len(self.calls_made()), 1)
        # The doctor says so, in full and in brief, and points the split finding at the review.
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("A split of sub/CLAUDE.md is ready on the branch bowline/split/sub-CLAUDE-md", out)
        self.assertIn("/bowline:split-instructions review sub/CLAUDE.md", out)
        self.assertNotIn("history into docs: /bowline:split-instructions.", out)
        code, out, _ = self.bowline("doctor", "--brief", "--no-memory")
        self.assertIn("ready on the branch", out)
        # show names the commands; done deletes the branch and the record.
        code, out, _ = self.bowline("autosplit", "show", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out)
        self.assertIn("git cherry-pick " + state["base"] + "..bowline/split/sub-CLAUDE-md", out)
        self.assertIn("Proposal:", out)
        self.assertIn("MAP:", out)
        code, out, _ = self.bowline("autosplit", "done", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out)
        self.assertIn("deleted", out)
        self.assertFalse(os.path.exists(self.state_file()))
        self.assertEqual(self.git_out("branch", "--list", "bowline/split/*").strip(), "")

    def test_run_reports_a_session_that_did_nothing_and_keeps_the_branch_of_a_half_done_one(self):
        self.enable()
        os.environ["FAKE_CLAUDE_MODE"] = "nothing"
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("made no commit", out)
        self.assertEqual(self.state()["state"], "failed")
        self.assertEqual(self.git_out("branch", "--list", "bowline/split/*").strip(), "")
        self.assertEqual(len(self.git_out("worktree", "list").strip().splitlines()), 1)
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("The background split of sub/CLAUDE.md failed", out)
        self.assertIn("does not try again on its own", out)
        self.hook()
        time.sleep(1)
        self.assertEqual(len(self.calls_made()), 1)
        code, out, _ = self.bowline("autosplit", "discard", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.state_file()))
        os.environ["FAKE_CLAUDE_MODE"] = "half"
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("left uncommitted changes", out)
        self.assertIn("bowline/split/sub-CLAUDE-md", self.git_out("branch", "--list", "bowline/split/*"))
        code, out, _ = self.bowline("autosplit", "status")
        self.assertIn("keeps what was done", out)
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)
        code, out, _ = self.bowline("autosplit", "show", "--file", "sub/CLAUDE.md")
        self.assertIn("Move the sections of sub/CLAUDE.md", out)
        code, out, _ = self.bowline("autosplit", "discard", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git_out("branch", "--list", "bowline/split/*").strip(), "")
        os.environ["FAKE_CLAUDE_MODE"] = "split"
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        self.assertIn("ready on the branch", out)


if __name__ == "__main__":
    unittest.main()
