"""Autosplit on a scratch repository, with a stand-in for the claude command (fake_claude.py beside this file) that
behaves like a headless session that did the split, did half of it, or did nothing. No real session is started."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from support import SCRIPTS, ScratchRepo, assert_starts_hidden, git, read, wait_for_split, write

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
        # A root file in .claude/ loads whole, like CLAUDE.md: wide is not cut there, only long is too long.
        write(os.path.join(self.repo, ".claude", "CLAUDE.md"), "# Root\n\n## Wide\n\n" + ("words " * 400 + "\n") * 20)
        self.assertEqual(autosplit.oversized(self.repo, config), [])

    def test_the_worker_starts_with_a_console_that_is_never_shown(self):
        import autosplit
        started = []
        real = autosplit.subprocess.Popen
        autosplit.subprocess.Popen = lambda args, **kwargs: started.append((args, kwargs))
        try:
            autosplit.start_worker(self.repo, "sub/CLAUDE.md", 257, 4000, "a test")
        finally:
            autosplit.subprocess.Popen = real
        self.assertEqual(len(started), 1)
        args, kwargs = started[0]
        self.assertEqual(args[3:5], ["autosplit", "worker"], "what is started is the worker")
        assert_starts_hidden(self, kwargs)

    @unittest.skipUnless(os.name == "nt", "only Windows refuses to replace a file that another process has open")
    def test_a_record_is_saved_while_a_reader_has_it_open(self):
        import autosplit
        import common
        autosplit.save_state(self.repo, "sub/CLAUDE.md", {"file": "sub/CLAUDE.md", "state": "starting"})
        # A reader in the middle of its read, as a session's hook, the doctor or this file's own wait is: Windows
        # refuses the replacement until the reader closes the file, here half a second later.
        reader = open(self.state_file(), encoding="utf-8")
        closing = threading.Timer(0.5, reader.close)
        closing.start()
        try:
            autosplit.save_state(self.repo, "sub/CLAUDE.md", {"file": "sub/CLAUDE.md", "state": "running"})
        finally:
            closing.cancel()
            reader.close()
        self.assertEqual(self.state()["state"], "running", "the save waited for the reader, it did not fail")
        # A file that stays open is still an error, raised once the time is up, and the record is left as it was.
        temp = self.state_file() + ".tmp"
        write(temp, "{}")
        reader = open(self.state_file(), encoding="utf-8")
        try:
            started = time.time()
            with self.assertRaises(PermissionError):
                common.replace_file(temp, self.state_file(), seconds=0.3)
            self.assertLess(time.time() - started, 3)
        finally:
            reader.close()
        self.assertEqual(self.state()["state"], "running")

    def test_a_worker_that_fails_after_it_made_its_worktree_removes_it_and_records_why(self):
        import autosplit
        import common
        self.enable()
        real = autosplit.save_state
        refused = []

        def save_state(root, path, state):
            if "worktree" in state and not refused:           # the save that says where the worktree is, once
                refused.append(state["worktree"])
                raise PermissionError(5, "Access is denied")
            real(root, path, state)
        autosplit.save_state = save_state
        try:
            final = autosplit.run_split(self.repo, "sub/CLAUDE.md", common.load_config(self.repo), lambda words: None)
        finally:
            autosplit.save_state = real
        self.assertEqual(len(refused), 1)
        self.assertEqual(final["state"], "failed", json.dumps(final, indent=1))
        self.assertIn("the worker stopped on an error", final["reason"])
        self.assertIn("Access is denied", final["reason"])
        self.assertEqual(self.state()["state"], "failed", "the record says so too, it does not stay at running")
        self.assertFalse(os.path.exists(refused[0]), "the worktree's folder is gone")
        self.assertEqual(len(self.git_out("worktree", "list").strip().splitlines()), 1)
        self.assertEqual(self.calls_made(), [], "no session was started")

    def test_a_worker_that_is_gone_is_told_from_one_at_work_and_discard_clears_what_it_left(self):
        import autosplit
        self.enable()
        branch = "bowline/split/sub-CLAUDE-md"
        # What a worker leaves when it is stopped in the middle, or the machine restarts: the record at "running" with
        # the id of a process that no longer exists, the branch, and the worktree in a temporary folder of its own.
        ended = subprocess.Popen([sys.executable, "-I", "-c", "pass"])
        ended.wait()
        temp = os.path.realpath(tempfile.mkdtemp(prefix="bowline-split-", dir=self.root))
        worktree = os.path.join(temp, "sub-CLAUDE-md")
        git(self.repo, "worktree", "add", "-q", "-b", branch, worktree, "HEAD")
        record = {"file": "sub/CLAUDE.md", "state": "running", "branch": branch, "started": "2026-11-21 10:57",
                  "pid": ended.pid, "log": os.path.join(os.path.dirname(self.state_file()), "sub-CLAUDE-md.log")}
        autosplit.save_state(self.repo, "sub/CLAUDE.md", record)
        gone = f"its process {ended.pid} no longer exists"
        code, out, _ = self.bowline("autosplit", "status")
        self.assertIn("sub/CLAUDE.md: stopped without recording how it ended: " + gone, out)
        self.assertNotIn("being prepared in the background", out)
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("WARN", out)
        self.assertIn("The background split of sub/CLAUDE.md stopped without recording how it ended: " + gone, out)
        self.assertIn("bowline autosplit discard --file sub/CLAUDE.md", out)
        code, out, _ = self.bowline("doctor", "--brief", "--no-memory")
        self.assertIn("stopped without recording how it ended", out)
        # Nothing starts on its own for a file that has a record, and a run in the foreground says how to clear it.
        self.hook()
        time.sleep(1)
        self.assertEqual(self.calls_made(), [])
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("Clear it first: bowline autosplit discard --file sub/CLAUDE.md", err)
        # discard removes the worktree, its temporary folder, the branch and the record.
        code, out, err = self.bowline("autosplit", "discard", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Its worker was gone (" + gone + ")", out)
        self.assertIn("is removed", out)
        self.assertFalse(os.path.exists(temp), "the worktree and the folder made for it are gone")
        self.assertEqual(len(self.git_out("worktree", "list").strip().splitlines()), 1)
        self.assertEqual(self.git_out("branch", "--list", "bowline/split/*").strip(), "")
        self.assertFalse(os.path.exists(self.state_file()))
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("autosplit will start on sub/CLAUDE.md after the next reply", out)
        # A worker whose process exists is at work: the doctor says so, and discard still refuses.
        autosplit.save_state(self.repo, "sub/CLAUDE.md", dict(record, pid=os.getpid()))
        code, out, _ = self.bowline("doctor", "--no-memory")
        self.assertIn("A split of sub/CLAUDE.md is being prepared in the background", out)
        code, out, err = self.bowline("autosplit", "discard", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn(f"still running (process {os.getpid()})", err)
        # A record at "starting" names no process yet. It is young for a second; after two minutes no worker began.
        starting = {key: value for key, value in record.items() if key != "pid"}
        autosplit.save_state(self.repo, "sub/CLAUDE.md", dict(starting, state="starting"))
        code, out, _ = self.bowline("autosplit", "status")
        self.assertIn("being prepared in the background", out)
        long_ago = time.time() - 300
        os.utime(self.state_file(), (long_ago, long_ago))
        code, out, _ = self.bowline("autosplit", "status")
        self.assertIn("stopped without recording how it ended: its worker did not begin within 120 seconds", out)
        code, out, err = self.bowline("autosplit", "discard", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        self.assertIn("it left no worktree", out)
        self.assertFalse(os.path.exists(self.state_file()))

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
        state = wait_for_split(self, self.state_file())
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

    def test_merge_delivers_onto_the_branch_when_the_tree_is_clean_and_waits_otherwise(self):
        self.enable(deliver="merge")
        write(os.path.join(self.repo, "README.md"), "# edited, not committed\n")
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        state = self.state()
        self.assertEqual(state["state"], "ready")
        self.assertIn("uncommitted changes", state["undelivered"])
        self.assertIn("not merged on its own", out)
        self.assertEqual(read(os.path.join(self.repo, "sub", "CLAUDE.md")), LONG)
        self.assertIn("bowline/split/sub-CLAUDE-md", self.git_out("branch", "--list", "bowline/split/*"))
        git(self.repo, "checkout", "--", "README.md")
        self.bowline("autosplit", "discard", "--file", "sub/CLAUDE.md")
        before = self.git_out("rev-parse", "HEAD").strip()
        code, out, err = self.bowline("autosplit", "run", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        state = self.state()
        self.assertEqual(state["state"], "merged", json.dumps(state, indent=1))
        self.assertEqual(state["merged_onto"], "main")
        self.assertEqual(len(state["merged"]), 2)
        self.assertEqual(len(self.git_out("log", "--format=%s", f"{before}..HEAD").strip().splitlines()), 2)
        self.assertLess(len(read(os.path.join(self.repo, "sub", "CLAUDE.md")).splitlines()), 10)
        self.assertEqual(self.git_out("status", "--porcelain"), "")
        self.assertEqual(self.git_out("branch", "--list", "bowline/split/*").strip(), "")
        code, out, _ = self.bowline("doctor", "--brief", "--no-memory")
        self.assertIn("autosplit merged the split of sub/CLAUDE.md", out)
        code, out, _ = self.bowline("autosplit", "show", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out)
        self.assertIn("git revert", out)
        self.assertIn("Proposal:", out)
        code, out, _ = self.bowline("autosplit", "done", "--file", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out)
        self.assertIn("cleared", out)
        self.assertFalse(os.path.exists(self.state_file()))


if __name__ == "__main__":
    unittest.main()
