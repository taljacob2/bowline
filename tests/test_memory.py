"""The memory backup on a scratch Claude Code configuration folder: a new machine, a first backup, an empty remote, both
sides with content, no project folder, status, and the push with and without --hook."""

import datetime
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

    def test_status_lists_each_note_the_largest_first_with_the_commits_it_names(self):
        folder = self.project_memory(self.repo)
        os.makedirs(folder)
        write(os.path.join(folder, "MEMORY.md"), "- [Progress](progress.md)\n- [Machines](machines.md)\n")
        write(os.path.join(folder, "machines.md"), "---\nname: machines\n---\nThe lab machine is off most days.\n" * 3)
        write(os.path.join(folder, "progress.md"), "Round one is `1a2b3c4d`, round two is 5e6f7a8b.\n" * 6)
        code, out, _ = self.bowline("status")
        self.assertEqual(code, 1, out)                       # no backup yet, said as before
        self.assertIn("notes: 2, the largest first", out)
        lines = out.splitlines()
        first = next(i for i, line in enumerate(lines) if line.startswith("  progress.md"))
        second = next(i for i, line in enumerate(lines) if line.startswith("  machines.md"))
        self.assertLess(first, second)
        size = os.path.getsize(os.path.join(folder, "progress.md"))
        self.assertIn(f"  progress.md: 6 lines, {size:,} bytes, 2 commit(s) named", out)
        self.assertIn("  machines.md: 12 lines,", out)
        self.assertIn("0 commit(s) named", lines[second])

    def test_push_leaves_a_plain_folder_alone(self):
        folder = self.project_memory(self.repo)
        os.makedirs(folder)
        write(os.path.join(folder, "MEMORY.md"), "- note\n")
        code, out, err = self.bowline("push", "--hook", stdin=json.dumps({"transcript_path": os.path.join(os.path.dirname(folder), "x.jsonl")}))
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertFalse(os.path.isdir(os.path.join(folder, ".git")))

    def backed_up(self, repo, name):
        """The memory folder of a repository, tied to a bare remote of its own with a first backup: (folder, remote)."""
        folder = self.project_memory(repo)
        bare = self.bare(name, seeded=True)
        subprocess.run(["git", "clone", "-q", bare, folder], check=True, capture_output=True)
        git(folder, "config", "user.email", "t@example.invalid")
        git(folder, "config", "user.name", "Test")
        return folder, bare

    def worktree(self, name="side"):
        """A worktree of the scratch repository where Claude Desktop makes them, and the project folder Claude Code
        writes the transcripts of its sessions in: (the worktree, the project folder)."""
        tree = os.path.join(self.repo, ".claude", "worktrees", name)
        git(self.repo, "worktree", "add", "-q", tree, "-b", name)
        return tree, os.path.dirname(self.project_memory(tree))

    def reply_ends(self, project, cwd, session="session-one", started_in=None):
        """The Stop hook after a reply, with the facts Claude Code hands it. The hook's own process runs outside every
        repository unless started_in says otherwise, so that only the facts can tell it where the notes are."""
        facts = {"hook_event_name": "Stop", "session_id": session, "transcript_path": os.path.join(project, session + ".jsonl")}
        if cwd:
            facts["cwd"] = cwd
        result = self.bowline("push", "--hook", stdin=json.dumps(facts), cwd=started_in or self.root)
        self.assertEqual(result, (0, "", ""))

    def backups(self, bare):
        """Every commit message the remote holds, the newest first, as one text."""
        return subprocess.run(["git", "-C", bare, "log", "--format=%B", "main"], capture_output=True, text=True, check=True).stdout

    def test_a_push_that_fails_says_so_to_a_person_and_nothing_as_a_hook(self):
        folder, _ = self.backed_up(self.repo, "m")
        git(folder, "remote", "set-url", "origin", os.path.join(self.root, "gone.git"))
        write(os.path.join(folder, "n.md"), "a fact\n")
        self.reply_ends(os.path.dirname(folder), self.repo)
        code, out, err = self.bowline("push")
        self.assertEqual(code, 1, out + err)
        self.assertIn("bowline memory: nothing new; the push failed, so 1 commit waits for the backup. git said:", out)
        self.assertIn("gone.git", out)

    def test_status_says_from_when_the_oldest_change_waits(self):
        folder, _ = self.backed_up(self.repo, "m")
        code, out, _ = self.bowline("status")
        self.assertIn("uncommitted changes: 0 file(s)\n", out)
        write(os.path.join(folder, "n.md"), "a fact\n")
        os.utime(os.path.join(folder, "n.md"), (1700000000, 1700000000))
        code, out, _ = self.bowline("status")
        stamp = datetime.datetime.fromtimestamp(1700000000).strftime("%Y-%m-%d %H:%M")
        self.assertIn(f"uncommitted changes: 1 file(s); the oldest change waits since {stamp}\n", out)

    def test_a_session_in_a_worktree_backs_up_the_notes_of_the_main_checkout(self):
        folder, bare = self.backed_up(self.repo, "m")
        tree, project = self.worktree()
        write(os.path.join(folder, "from-a-worktree.md"), "a fact\n")
        self.reply_ends(project, tree)
        self.assertIn("Memory as of", self.backups(bare))
        self.assertIn("Session: session-one", self.backups(bare))
        self.assertFalse(os.path.exists(os.path.join(project, "memory")))          # nothing is made beside the transcript

    def test_a_session_in_a_subfolder_of_a_worktree_backs_them_up_too(self):
        folder, bare = self.backed_up(self.repo, "m")
        tree, project = self.worktree()
        os.makedirs(os.path.join(tree, "src", "deep"))
        write(os.path.join(folder, "n.md"), "a fact\n")
        self.reply_ends(project, os.path.join(tree, "src", "deep"))
        self.assertIn("Memory as of", self.backups(bare))

    def test_a_memory_folder_without_a_backup_beside_the_transcript_does_not_hide_the_notes(self):
        folder, bare = self.backed_up(self.repo, "m")
        tree, project = self.worktree()
        write(os.path.join(project, "memory", "MEMORY.md"), "- left by something else\n")
        write(os.path.join(folder, "n.md"), "a fact\n")
        self.reply_ends(project, tree)
        self.assertIn("Memory as of", self.backups(bare))
        self.assertFalse(os.path.isdir(os.path.join(project, "memory", ".git")))

    def test_a_worktree_session_without_a_cwd_goes_by_the_folder_the_hook_runs_in(self):
        folder, bare = self.backed_up(self.repo, "m")
        tree, project = self.worktree()
        write(os.path.join(folder, "n.md"), "a fact\n")
        self.reply_ends(project, None, started_in=tree)
        self.assertIn("Memory as of", self.backups(bare))

    def test_a_session_whose_folder_changed_to_another_repository_backs_up_its_own_notes(self):
        folder, bare = self.backed_up(self.repo, "m")
        other = os.path.join(self.root, "other")
        os.makedirs(other)
        git(other, "init", "-q", "-b", "main")
        other_folder, other_bare = self.backed_up(other, "o")
        write(os.path.join(folder, "n.md"), "a fact\n")
        write(os.path.join(other_folder, "n.md"), "a fact of the other repository\n")
        self.reply_ends(os.path.dirname(folder), other)
        self.assertIn("Memory as of", self.backups(bare))
        self.assertNotIn("Memory as of", self.backups(other_bare))

    def test_a_worktree_of_a_repository_with_no_backup_is_left_alone(self):
        folder = self.project_memory(self.repo)
        write(os.path.join(folder, "MEMORY.md"), "- note\n")
        tree, project = self.worktree()
        self.reply_ends(project, tree)
        self.assertFalse(os.path.isdir(os.path.join(folder, ".git")))

    def test_a_worktree_that_is_gone_when_its_session_ends_says_nothing(self):
        folder, bare = self.backed_up(self.repo, "m")
        tree, project = self.worktree()
        git(self.repo, "worktree", "remove", tree)
        write(os.path.join(folder, "n.md"), "a fact\n")
        self.reply_ends(project, tree)                                              # quiet and exit 0, as for any failure
        self.reply_ends(os.path.dirname(folder), self.repo)                         # and the next reply catches up
        self.assertIn("Memory as of", self.backups(bare))


if __name__ == "__main__":
    unittest.main()
