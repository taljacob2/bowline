"""The crew's check before an edit, on a scratch repository with two worktrees and a pushed branch: a file another
worktree changed and did not commit, one it committed and did not push, one it only claimed, the cases that are not two
changes (a pushed commit, a branch cut from the other), the files every session adds to, the off switch, one warning
per session and file, a record that is fresh, stale or too old, a repository with one worktree, and the doctor's note."""

import json
import os
import subprocess
import sys
import time
import unittest

from support import SCRIPTS, ScratchRepo, assert_starts_hidden, git, write

import common  # noqa: E402 - support puts the scripts on the path
import crew  # noqa: E402
import crew_edit  # noqa: E402

ROOT = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"


class CrewEditTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        write(os.path.join(self.repo, "src", "a.py"), "a = 1\n")
        write(os.path.join(self.repo, "docs", "ROADMAP.md"), "# Roadmap\n\n1. **One.** First.\n")
        git(self.repo, "add", "CLAUDE.md", "src/a.py", "docs/ROADMAP.md")
        git(self.repo, "commit", "-q", "-m", "a file and a roadmap")
        self.origin = os.path.join(self.root, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        git(self.repo, "remote", "add", "origin", self.origin)
        git(self.repo, "push", "-q", "-u", "origin", "main")
        self.other = None
        self.sessions = 0

    def add_other(self):
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.other = [tree["path"] for tree in crew.worktrees(self.repo) if not tree["main"]][0]
        git(self.other, "config", "user.email", "t@example.invalid")
        git(self.other, "config", "user.name", "Test")

    def configure(self, settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"crew": settings}) + "\n")
        common.forget_layout()

    def crew(self, *args, cwd=None, stdin=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args], input=stdin,
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def measure(self):
        code, out, err = self.crew("refresh")
        self.assertEqual(code, 0, out + err)

    def hook(self, path, session=None, tool="Edit", field="file_path", measure=True):
        """Runs the check the way the PreToolUse hook does, after a fresh measuring unless told otherwise, and returns
        what Claude would be told, or None. A new session each time unless one is named."""
        if measure:
            self.measure()
        if session is None:
            self.sessions += 1
            session = f"session-{self.sessions}"
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "session_id": session,
                              "cwd": self.root, "tool_input": {field: path}})
        code, out, err = self.crew("before-edit", "--hook", cwd=self.root, stdin=payload)
        self.assertEqual(code, 0, out + err)
        if not out.strip():
            return None
        answer = json.loads(out)
        self.assertEqual(sorted(answer), ["hookSpecificOutput"], "a warning, never a decision: nothing blocks the edit")
        self.assertEqual(sorted(answer["hookSpecificOutput"]), ["additionalContext", "hookEventName"])
        self.assertEqual(answer["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        return answer["hookSpecificOutput"]["additionalContext"]

    def mine(self, *parts):
        return os.path.join(self.repo, *parts)

    def test_a_repository_with_one_worktree_is_silent(self):
        write(self.mine("src", "a.py"), "a = 2\n")
        self.assertIsNone(self.hook(self.mine("src", "a.py"), measure=False))
        self.assertFalse(os.path.exists(os.path.join(crew.state_dir(self.repo), "changed.json")), "nothing is measured for one worktree")
        code, out, _ = self.crew("before-edit", "--file", "src/a.py")
        self.assertEqual(code, 0)
        self.assertIn("one worktree", out)

    def test_a_change_another_worktree_did_not_commit_is_named(self):
        self.add_other()
        write(os.path.join(self.other, "src", "a.py"), "a = 3\n")
        said = self.hook(self.mine("src", "a.py"))
        self.assertIn("src/a.py is also held by another worktree", said)
        self.assertIn(".claude/worktrees/other, on the branch other", said)
        self.assertIn("changed there and not committed", said)
        self.assertIn("SendMessage", said)
        self.assertIn("crew.shared", said)
        # The same answer for a notebook, whose tool names the path differently, and from the other side.
        self.assertIn("not committed", self.hook(self.mine("src", "a.py"), tool="NotebookEdit", field="notebook_path"))
        self.assertIsNone(self.hook(os.path.join(self.other, "src", "a.py")), "the main checkout did not change the file")
        self.assertIsNone(self.hook(self.mine("CLAUDE.md")), "a file nobody else changed")
        code, out, _ = self.crew("before-edit", "--file", "src/a.py")
        self.assertIn("is also held by another worktree", out)
        code, out, _ = self.crew("before-edit", "--file", "CLAUDE.md")
        self.assertIn("no other worktree has changed or claimed CLAUDE.md", out)

    def test_a_new_file_under_a_folder_the_other_worktree_made_is_named(self):
        self.add_other()
        write(os.path.join(self.other, "fresh", "deep", "b.py"), "b = 1\n")
        said = self.hook(self.mine("fresh", "deep", "b.py"))        # neither the file nor its folder exists here yet
        self.assertIn("fresh/deep/b.py is also held", said)

    def test_a_commit_is_named_until_it_is_pushed(self):
        self.add_other()
        write(os.path.join(self.other, "src", "a.py"), "a = 4\n")
        git(self.other, "commit", "-q", "-am", "the other changes a")
        said = self.hook(self.mine("src", "a.py"))
        self.assertIn("committed there and not in origin/main", said)
        git(self.other, "push", "-q", "origin", "other:main")
        git(self.repo, "fetch", "-q", "origin")
        self.assertIsNone(self.hook(self.mine("src", "a.py")), "what is pushed is no longer another session's change")

    def test_a_branch_cut_from_the_other_does_not_hold_two_changes(self):
        self.add_other()
        write(os.path.join(self.other, "src", "a.py"), "a = 5\n")
        git(self.other, "commit", "-q", "-am", "the other changes a")
        git(self.repo, "merge", "-q", "--ff-only", "other")
        self.assertIsNone(self.hook(self.mine("src", "a.py")), "both branches hold the same commit")
        write(self.mine("src", "a.py"), "a = 6\n")
        git(self.repo, "commit", "-q", "-am", "this branch goes on from there")
        self.assertIsNone(self.hook(self.mine("src", "a.py")), "this branch holds the other's commit and adds to it")
        write(os.path.join(self.other, "src", "a.py"), "a = 7\n")
        git(self.other, "commit", "-q", "-am", "the other goes on too")
        self.assertIn("committed there", self.hook(self.mine("src", "a.py")))

    def test_a_claim_speaks_before_any_change_is_on_disk(self):
        self.add_other()
        code, out, err = self.crew("claim", "file:src/a.py", "--why", "the parser's lines", cwd=self.other)
        self.assertEqual(code, 0, out + err)
        said = self.hook(self.mine("src", "a.py"))
        self.assertIn("claimed there for: the parser's lines", said)
        self.assertIsNone(self.hook(os.path.join(self.other, "src", "a.py")), "the holder of a claim is not warned about it")

    def test_files_every_session_adds_to_are_never_warned_about(self):
        self.add_other()
        self.configure({"shared": ["docs/DECISIONS.md", "notes/*.md"],
                        "numbers": {"roadmap": {"file": "docs/ROADMAP.md"}},
                        "stamps": [{"file": "web/.source-commit"}]})
        for parts in (("docs", "DECISIONS.md"), ("notes", "queue.md"), ("docs", "ROADMAP.md"), ("web", ".source-commit"), ("src", "a.py")):
            write(os.path.join(self.other, *parts), "theirs\n")
        for parts in (("docs", "DECISIONS.md"), ("notes", "queue.md"), ("docs", "ROADMAP.md"), ("web", ".source-commit")):
            self.assertIsNone(self.hook(self.mine(*parts)), "/".join(parts))
        self.assertIn("src/a.py", self.hook(self.mine("src", "a.py")))
        code, out, _ = self.crew("before-edit", "--file", "docs/ROADMAP.md")
        self.assertIn("a file every session adds to", out)

    def test_the_setting_turns_the_warning_off(self):
        self.add_other()
        write(os.path.join(self.other, "src", "a.py"), "a = 8\n")
        self.configure({"warnBeforeEdit": False})
        self.assertIsNone(self.hook(self.mine("src", "a.py")))
        code, out, _ = self.crew("before-edit", "--file", "src/a.py")
        self.assertIn("turned off", out)

    def test_a_session_is_told_once_per_file(self):
        self.add_other()
        write(os.path.join(self.other, "src", "a.py"), "a = 9\n")
        write(os.path.join(self.other, "CLAUDE.md"), ROOT + "\nMore.\n")
        self.assertIsNotNone(self.hook(self.mine("src", "a.py"), session="one"))
        self.assertIsNone(self.hook(self.mine("src", "a.py"), session="one"), "said once; again at every edit it is read past")
        self.assertIsNotNone(self.hook(self.mine("CLAUDE.md"), session="one"), "another file is another warning")
        self.assertIsNotNone(self.hook(self.mine("src", "a.py"), session="two"), "another session has not heard it")
        git(self.other, "commit", "-q", "-am", "the other commits a")
        self.assertIn("committed there", self.hook(self.mine("src", "a.py"), session="one"), "a new state is said again")

    def test_a_hook_without_a_record_starts_a_measuring_and_does_not_fail(self):
        self.add_other()
        write(os.path.join(self.other, "src", "a.py"), "a = 10\n")
        record = os.path.join(crew.state_dir(self.repo), "changed.json")
        self.assertFalse(os.path.exists(record))
        self.hook(self.mine("src", "a.py"), session="early", measure=False)     # may speak or not; it must not fail
        deadline = time.time() + 60
        while not os.path.exists(record) and time.time() < deadline:
            time.sleep(0.2)
        self.assertTrue(os.path.exists(record), "the hook started `crew refresh` on its own")
        self.assertIn("not committed", self.hook(self.mine("src", "a.py"), session="later", measure=False))

    def test_a_record_is_used_while_fresh_and_dropped_when_too_old(self):
        self.add_other()
        self.measure()
        config = common.load_config(self.repo)
        started = []
        real = crew_edit.start_measuring
        crew_edit.start_measuring = lambda root: started.append(root)
        try:
            fresh = crew_edit.measured(self.repo, config, 0)
            self.assertEqual((len(fresh["trees"]), started), (2, []), "a fresh record starts no measuring")
            path = os.path.join(crew.state_dir(self.repo), "changed.json")
            for minutes, kept in ((5, True), (120, False)):
                old = crew.read_json(path, None)
                old["at"] = time.time() - minutes * 60
                crew.write_json(path, old)
                del started[:]
                record = crew_edit.measured(self.repo, config, 0)
                self.assertEqual(len(started), 1, "a stale record starts a measuring")
                self.assertEqual(record is not None, kept, f"a record {minutes} minutes old")
        finally:
            crew_edit.start_measuring = real

    def test_a_measuring_is_not_started_twice_at_once(self):
        self.add_other()
        marker = crew_edit.measuring_path(self.repo)
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        write(marker, "1\n")
        started = []
        real = crew_edit.subprocess.Popen
        crew_edit.subprocess.Popen = lambda args, **kwargs: started.append((args, kwargs))
        try:
            self.assertFalse(crew_edit.start_measuring(self.repo), "one started a moment ago")
            self.assertEqual(started, [])
            old = time.time() - crew_edit.MEASURING_SECONDS - 5
            os.utime(marker, (old, old))
            self.assertTrue(crew_edit.start_measuring(self.repo), "one that old is taken for stopped")
        finally:
            crew_edit.subprocess.Popen = real
        self.assertEqual(len(started), 1)
        args, kwargs = started[0]
        self.assertEqual(args[-4:], ["crew", "refresh", "--repo", self.repo], "what is started is crew's own measuring")
        assert_starts_hidden(self, kwargs)

    def test_a_file_outside_any_repository_and_a_path_that_is_not_absolute_are_silent(self):
        self.add_other()
        self.assertIsNone(self.hook(os.path.join(self.root, "elsewhere", "x.txt"), measure=False))
        self.assertIsNone(self.hook("src/a.py", measure=False))
        code, out, err = self.crew("before-edit", "--hook", cwd=self.root, stdin="not json")
        self.assertEqual((code, out), (0, ""), err)

    def test_the_doctor_notes_several_worktrees_without_a_rule(self):
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertNotIn("working beside other sessions", out, "one worktree needs no rule")
        self.add_other()
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertEqual(code, 0, out + err)
        self.assertIn("NOTE  The repository has 2 worktrees and no rule about working beside other sessions.", out)
        self.assertIn("/bowline:crew offers the rule", out)
        # A worktree nobody has worked in lately presses nothing at a session's start: the note stays a note. The
        # line for a session that does work beside another one, which names the missing rule, is in test_crew.
        folder = os.path.join(self.repo, ".git", "worktrees", os.path.basename(self.other))
        stamp = time.time() - 120 * 60
        for name in ("index", "HEAD", os.path.join("logs", "HEAD")):
            if os.path.exists(os.path.join(folder, name)):
                os.utime(os.path.join(folder, name), (stamp, stamp))
        code, brief, _ = self.run_script("doctor", "--brief", "--no-memory")
        self.assertNotIn("no rule about working", brief, "a note is not pressed at a session's start")
        write(os.path.join(self.repo, ".claude", "rules", "beside-other-sessions.md"), "# Working beside other sessions\n\nSplit the work by files.\n")
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertNotIn("no rule about working beside other sessions", out)
        self.assertEqual(crew_edit.worktree_count(self.other), 2, "counted from a worktree as from the main checkout")


if __name__ == "__main__":
    unittest.main()
