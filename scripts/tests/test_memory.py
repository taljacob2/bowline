"""The memory backup on a scratch Claude Code configuration folder: a new machine, a first backup, an empty remote, both
sides with content, no project folder, status, and the push with and without --hook."""

import json
import os
import re
import subprocess
import sys
import unittest

from support import SCRIPTS, ScratchRepo, git, load_json, write


class MemoryTests(ScratchRepo):
    def bowline(self, *args, stdin=None, cwd=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "memory", *args], input=stdin,
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def project_memory(self, repo):
        name = re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(repo))
        folder = os.path.join(self.config_dir, "projects", name, "memory")
        os.makedirs(os.path.dirname(folder), exist_ok=True)
        return folder

    def bare(self, name, seeded=False):
        bare = os.path.join(self.root, name + ".git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        if seeded:
            seed = os.path.join(self.root, name + "-seed")
            subprocess.run(["git", "clone", "-q", bare, seed], check=True, capture_output=True)
            git(seed, "config", "user.email", "t@example.invalid")
            git(seed, "config", "user.name", "Test")
            write(os.path.join(seed, "MEMORY.md"), "- a note\n")
            git(seed, "add", "MEMORY.md")
            git(seed, "commit", "-q", "-m", "seed")
            git(seed, "push", "-q", "-u", "origin", "main")
        return bare

    def test_no_project_folder_is_refused_with_the_hint(self):
        code, out, err = self.bowline("setup", self.bare("m"))
        self.assertEqual(code, 1)
        self.assertIn("Start Claude Code once", err)

    def test_new_machine_clones_installs_hook_and_is_idempotent(self):
        folder = self.project_memory(self.repo)
        bare = self.bare("m", seeded=True)
        code, out, err = self.bowline("setup", bare, "--dry-run")
        self.assertEqual(code, 0, out + err)
        self.assertIn("dry run", out)
        self.assertFalse(os.path.exists(folder))
        code, out, err = self.bowline("setup", bare)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(os.path.join(folder, "MEMORY.md")))
        settings = load_json(os.path.join(self.config_dir, "settings.json"))
        self.assertEqual(len(settings["hooks"]["Stop"]), 1)
        self.assertEqual(len(settings["hooks"]["SessionEnd"]), 1)
        self.assertEqual(settings["hooks"]["Stop"][0]["hooks"][0]["args"][-2:], ["push", "--hook"])
        code, out, _ = self.bowline("setup", bare)
        self.assertIn("already", out)
        self.assertEqual(load_json(os.path.join(self.config_dir, "settings.json")), settings)
        code, out, _ = self.bowline("status")
        self.assertEqual(code, 0, out)
        self.assertIn("hook on this machine: installed", out)
        self.assertIn("not yet pushed: 0", out)

    def test_first_backup_pushes_and_no_hook_is_honoured(self):
        folder = self.project_memory(self.repo)
        os.makedirs(folder)
        write(os.path.join(folder, "MEMORY.md"), "- my note\n")
        bare = self.bare("m")
        env = dict(os.environ, GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="t@example.invalid")
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "memory", "setup", bare, "--no-hook"],
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("first backup", subprocess.run(["git", "-C", bare, "log", "--format=%s", "main"], capture_output=True, text=True).stdout)
        self.assertFalse(os.path.exists(os.path.join(self.config_dir, "settings.json")))

    def test_both_with_content_is_refused(self):
        folder = self.project_memory(self.repo)
        os.makedirs(folder)
        write(os.path.join(folder, "MEMORY.md"), "- local\n")
        bare = self.bare("m", seeded=True)
        code, out, err = self.bowline("setup", bare)
        self.assertEqual(code, 1)
        self.assertIn("Merge them by hand", err)
        self.assertFalse(os.path.isdir(os.path.join(folder, ".git")))

    def test_push_commits_and_pushes_and_sets_upstream_after_an_empty_clone(self):
        folder = self.project_memory(self.repo)
        bare = self.bare("m")                              # empty remote: setup clones an empty repository
        self.bowline("setup", bare, "--no-hook")
        git(folder, "config", "user.email", "t@example.invalid")
        git(folder, "config", "user.name", "Test")
        write(os.path.join(folder, "MEMORY.md"), "- first\n")
        payload = json.dumps({"transcript_path": os.path.join(os.path.dirname(folder), "x.jsonl")})
        code, out, err = self.bowline("push", "--hook", stdin=payload)
        self.assertEqual(code, 0)
        self.assertEqual(out + err, "")
        log = subprocess.run(["git", "-C", bare, "log", "--format=%s", "--all"], capture_output=True, text=True).stdout
        self.assertIn("Memory as of", log)
        write(os.path.join(folder, "n.md"), "fact\n")
        code, out, _ = self.bowline("push")
        self.assertEqual(code, 0)
        self.assertIn("committed; pushed", out)
        code, out, _ = self.bowline("push")
        self.assertIn("nothing new; nothing to push", out)

    def test_push_leaves_a_plain_folder_alone(self):
        folder = self.project_memory(self.repo)
        os.makedirs(folder)
        write(os.path.join(folder, "MEMORY.md"), "- note\n")
        code, out, err = self.bowline("push", "--hook", stdin=json.dumps({"transcript_path": os.path.join(os.path.dirname(folder), "x.jsonl")}))
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertFalse(os.path.isdir(os.path.join(folder, ".git")))


if __name__ == "__main__":
    unittest.main()
