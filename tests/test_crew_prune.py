"""crew prune and the push queue, on scratch repositories with an origin. prune names the worktrees that are safe to
remove (nothing not committed, every commit on the pushed branch by content, no process, no session, no claim, no
place in the queue, not locked, and no sign of work for hours) and why each other one is not, and removes only the
ones it is told to, checked again first, with plain `git worktree remove`. The queue says in which order the
worktrees push, and tells one behind another that changes the same file to rebase before its full checks."""

import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from support import SCRIPTS, ScratchRepo, age_git_folder, git, write

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
        age_git_folder(self.repo, tree, hours * 3600)

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
        for words in ("dirty: 1 untracked file, written less than a minute ago (git worktree remove refuses untracked "
                      "files too: commit or delete them first)", "ahead: 1 commit not on origin/main",
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
        self.assertIn("dirty is not removed: 1 untracked file, written less than a minute ago", flat(out))
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


def make_link(link, target):
    """A link to a folder, as a worktree's node_modules often is: a directory junction on Windows, which needs no
    administrator, and a symbolic link elsewhere."""
    link, target = os.path.normpath(link), os.path.normpath(target)        # mklink takes no forward slash
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", link, target], check=True, capture_output=True)
    else:
        os.symlink(target, link, target_is_directory=True)


def contents(folder):
    """Every file under a folder, by its path from the folder, with what it holds."""
    found = {}
    for top, _, files in os.walk(folder):
        for name in files:
            with open(os.path.join(top, name), encoding="utf-8") as handle:
                found[os.path.relpath(os.path.join(top, name), folder)] = handle.read()
    return found


class LinkTests(CrewCase):
    """On 2026-11-22 Git for Windows' `git worktree remove` followed two directory junctions inside a worktree prune had
    called safe, webui/node_modules and docs-site/node_modules, and deleted the main checkout's packages they pointed
    to. Here each worktree's links point to sacrificial folders outside the repository."""

    def setUp(self):
        super().setUp()
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\nnode_modules\n")
        self.packages = {}
        for part in ("webui", "docs-site"):
            folder = os.path.join(self.root, "the-main-checkouts-" + part + "-packages")
            for name in ("@adobe/css-tools/index.js", "@reduxjs/toolkit/index.js", "vite/bin/vite.js"):
                write(os.path.join(folder, name), f"the {part} package {name}\n")
            self.packages[part] = folder
        self.before = {part: contents(folder) for part, folder in self.packages.items()}
        self.linked = self.worktree("linked")
        for part, folder in self.packages.items():
            make_link(os.path.join(self.linked, part, "node_modules"), folder)
        self.age(self.linked, 8)
        self.age(self.repo, 8)

    def test_a_link_outside_is_named_and_the_worktree_is_not_called_safe(self):
        code, out, err = self.crew("prune")
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        self.assertIn("Safe to remove: none.", text)
        self.assertIn("Not safe while its links stand: 1 worktree.", text)
        self.assertIn(f"linked: quiet for 8 hours; links: docs-site/node_modules -> {self.packages['docs-site']}, "
                      f"webui/node_modules -> {self.packages['webui']}", text)
        self.assertEqual({part: contents(folder) for part, folder in self.packages.items()}, self.before)

    def test_remove_takes_each_link_away_alone_and_never_deletes_through_it(self):
        code, out, err = self.crew("prune", "--remove", "linked")
        # Every file the links pointed to is still there, as it was.
        self.assertEqual({part: contents(folder) for part, folder in self.packages.items()}, self.before, out + err)
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        for part in ("docs-site", "webui"):
            self.assertIn(f"linked: took away the link {part}/node_modules, the link alone; {self.packages[part]} keeps "
                          "its 3 entries.", text)
        self.assertIn("removed linked", text)
        self.assertFalse(os.path.exists(self.linked))

    def test_a_folder_left_with_a_link_is_never_to_be_deleted_whole(self):
        words = crew.left_behind_words(self.linked)
        self.assertIn("It still holds a link to a folder outside it", words)
        self.assertIn("take each link away alone first, and only then delete the folder", words)
        self.assertIn("Never delete a folder that holds a link with a command that goes into every folder", words)
        for part in ("docs-site", "webui"):
            os.rmdir(os.path.join(self.linked, part, "node_modules")) if os.name == "nt" else \
                os.unlink(os.path.join(self.linked, part, "node_modules"))
        self.assertEqual(crew.left_behind_words(self.linked), "Close what holds the files git names, then delete the folder.")
        self.assertEqual({part: contents(folder) for part, folder in self.packages.items()}, self.before)


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
