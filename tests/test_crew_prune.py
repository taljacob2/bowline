"""crew prune and the push queue, on scratch repositories with an origin. prune names the worktrees that are safe to
remove (nothing not committed, every commit on the pushed branch by content, no process, no session, no claim, no
place in the queue, not locked, and no sign of work for hours) and why each other one is not, and removes only the
ones it is told to, checked again first, with plain `git worktree remove`. The queue says in which order the
worktrees push, and tells one behind another that changes the same file to rebase before its full checks."""

import json
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

from support import SCRIPTS, ScratchRepo, git, write

import crew  # noqa: E402 - support puts the scripts on the path

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]


def flat(text):
    return " ".join(text.split())


class CrewCase(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"crew": {"claude": FAKE_CLAUDE}}) + "\n")
        write(os.path.join(self.repo, ".gitignore"), "build/\n")
        git(self.repo, "add", ".claude/bowline.json", ".gitignore")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        bare = os.path.join(self.root, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        git(self.repo, "remote", "add", "origin", bare)
        git(self.repo, "push", "-q", "-u", "origin", "main")
        self.trees = {}

    def worktree(self, name):
        git(self.repo, "worktree", "add", "-q", "-b", name, os.path.join(".claude", "worktrees", name))
        self.trees[name] = os.path.join(self.repo, ".claude", "worktrees", name)
        return self.trees[name]

    def commit(self, tree, path, text, message):
        write(os.path.join(tree, path), text)
        git(tree, "add", path)
        git(tree, "commit", "-q", "-m", message)

    def age(self, tree, hours):
        folder = os.path.join(self.repo, ".git") if tree == self.repo else \
            os.path.join(self.repo, ".git", "worktrees", os.path.basename(tree))
        stamp = time.time() - hours * 3600
        for name in ("index", "HEAD", os.path.join("logs", "HEAD")):
            if os.path.exists(os.path.join(folder, name)):
                os.utime(os.path.join(folder, name), (stamp, stamp))

    def crew(self, *args, cwd=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr


class PruneTests(CrewCase):
    def setUp(self):
        super().setUp()
        done = self.worktree("done")
        self.commit(done, "src/fix.py", "fixed = 1\n", "a fix")
        git(self.repo, "cherry-pick", "-x", "done")                              # main has it under another hash
        git(self.repo, "push", "-q", "origin", "main")
        ignored = self.worktree("ignored")
        write(os.path.join(ignored, "build", "out.txt"), "built\n")             # ignored files never block a removal
        write(os.path.join(self.worktree("dirty"), "notes.txt"), "not committed\n")
        self.commit(self.worktree("ahead"), "src/new.py", "new = 1\n", "not pushed")
        self.worktree("claimed")
        self.crew("claim", "file:src/x.py", "--why", "later", cwd=self.trees["claimed"])
        self.worktree("locked")
        git(self.repo, "worktree", "lock", "--reason", "kept on purpose", self.trees["locked"])
        self.worktree("open")
        write(self.agents_file, json.dumps([{"sessionId": "s1", "cwd": os.path.realpath(self.trees["open"]),
                                             "kind": "interactive", "name": "the open session", "status": "idle"}]) + "\n")
        self.worktree("fresh")
        for name, tree in self.trees.items():
            if name != "fresh":
                self.age(tree, 8)
        self.age(self.repo, 8)

    def test_prune_names_what_is_safe_to_remove_and_why_the_rest_is_not(self):
        code, out, err = self.crew("prune")
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        safe, _, rest = text.partition("Not safe")
        self.assertIn("Safe to remove: 2 worktrees", safe)
        self.assertIn("done: quiet for 8 hours; its 1 commit is on origin/main by content", safe)
        self.assertIn("ignored: quiet for 8 hours", safe)
        for words in ("dirty: 1 file not committed", "ahead: 1 commit not on origin/main",
                      "claimed: it holds the claim file:src/x.py", "locked: git keeps it locked (kept on purpose)",
                      'open: a session is open in it, "the open session"', "fresh: a sign of work less than a minute ago"):
            self.assertIn(words, rest)
        self.assertNotIn("the main checkout:", text)
        self.assertIn("crew prune --remove", text)
        for line in out.splitlines():
            self.assertLessEqual(len(line), 100, line)

    def test_prune_removes_only_what_it_is_told_and_only_what_is_still_safe(self):
        code, out, err = self.crew("prune", "--remove", "dirty")
        self.assertEqual(code, 1, out + err)
        self.assertIn("dirty is not removed: 1 file not committed", flat(out))
        self.assertTrue(os.path.isdir(self.trees["dirty"]))
        code, out, err = self.crew("prune", "--remove", "nothing-of-that-name")
        self.assertEqual(code, 2, out + err)
        self.assertIn("no worktree of this repository is called nothing-of-that-name", flat(err))
        code, out, err = self.crew("prune", "--remove", "done", "ignored")
        self.assertEqual(code, 0, out + err)
        self.assertIn("removed done", out)
        self.assertIn("removed ignored", out)
        self.assertFalse(os.path.exists(self.trees["done"]))
        self.assertFalse(os.path.exists(self.trees["ignored"]))
        listed = subprocess.run(["git", "-C", self.repo, "worktree", "list"], capture_output=True, text=True).stdout
        self.assertNotIn("done", listed)
        self.assertEqual(subprocess.run(["git", "-C", self.repo, "rev-parse", "--verify", "-q", "done"],
                                        capture_output=True).returncode, 0, "its branch stays")

    def test_git_removes_with_no_time_limit_and_its_refusal_is_shown(self):
        # On Windows git took more than two minutes to delete a worktree with its own node_modules; stopped at a time
        # limit, it left a folder with no .git file and part of its files, and said nothing that was shown.
        answer = subprocess.CompletedProcess([], 0, stdout=b"")
        with mock.patch.object(crew.subprocess, "run", return_value=answer) as run:
            crew.remove_worktree(self.repo, self.trees["done"])
        self.assertNotIn("timeout", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs.get("stderr"), subprocess.STDOUT)
        git(self.repo, "worktree", "lock", "--reason", "a test", self.trees["done"])
        code, said = crew.remove_worktree(self.repo, self.trees["done"])
        self.assertNotEqual(code, 0)
        self.assertIn("locked", said)                                            # git's own words, from its errors
        self.assertTrue(os.path.isdir(self.trees["done"]))


class QueueTests(CrewCase):
    def setUp(self):
        super().setUp()
        self.commit(self.worktree("first"), "src/shared.py", "first = 1\n", "first's change")
        self.commit(self.worktree("second"), "src/shared.py", "second = 1\n", "second's change")
        self.commit(self.worktree("third"), "src/other.py", "third = 1\n", "third's change")

    def hook(self, action, command, cwd):
        payload = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", action, "--hook"],
                                input=payload, cwd=self.root, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout

    def test_the_queue_tells_the_second_to_rebase_before_its_checks(self):
        code, out, _ = self.crew("queue", "join", "--why", "the parser", cwd=self.trees["first"])
        self.assertEqual(code, 0, out)
        self.assertIn("place 1 in the push queue", out)
        code, out, _ = self.crew("queue", "join", cwd=self.trees["second"])
        self.assertIn("place 2 in the push queue", out)
        self.assertIn("first is ahead of you and changes src/shared.py too: rebase onto its push before your full checks",
                      flat(out))
        code, out, _ = self.crew("queue", "join", cwd=self.trees["third"])
        self.assertIn("place 3", out)
        self.assertNotIn("rebase", out)                                          # it shares no file with those ahead
        code, out, _ = self.crew("queue")
        self.assertIn("1. first, since", out)
        self.assertIn("the parser", out)
        self.assertIn("2. second, since", out)
        code, out, _ = self.crew()                                                # the look shows it too
        self.assertIn("The push queue (crew queue):", out)
        # A heavy check behind a worktree that changes the same file is told so, and still runs.
        code, out, err = self.crew("run", "--", sys.executable, "-c", "print('ran')", cwd=self.trees["second"])
        self.assertEqual(code, 0, out + err)
        self.assertIn("first is ahead of you in the push queue and changes src/shared.py too", flat(err))
        self.assertIn("ran", out)
        # first pushes to main: its place is given up, and it is told who comes next and shares its files.
        git(self.trees["first"], "push", "-q", "origin", "HEAD:main")
        code, out = self.hook("after-push", "git push -q origin HEAD:main", self.trees["first"])
        said = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("first's place in the push queue is given up", flat(said))
        self.assertIn("second comes next and changes src/shared.py too: tell it to rebase onto this push now", flat(said))
        code, out, _ = self.crew("queue")
        self.assertIn("1. second", out)
        self.assertNotIn("first,", out)
        code, out, _ = self.crew("queue", "leave", cwd=self.trees["second"])
        self.assertIn("left the push queue", out)
        code, out, _ = self.crew("queue", "leave", cwd=self.trees["second"])
        self.assertIn("had no place", out)

    def test_a_push_to_a_branch_of_its_own_keeps_the_place(self):
        self.crew("queue", "join", cwd=self.trees["first"])
        git(self.trees["first"], "push", "-q", "origin", "HEAD:refs/heads/first")
        code, out = self.hook("after-push", "git push -q origin HEAD:first", self.trees["first"])
        self.assertNotIn("given up", out)
        self.assertIn("1. first", self.crew("queue")[1])


if __name__ == "__main__":
    unittest.main()
