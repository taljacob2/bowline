"""The replay's own parts that need no Claude Code session: the copy of the plugin with the cases in it, and the
made-up repository each case starts in. The repository is built by the same bash script a case runs, and then the
lookup is run on it, so that a change to a template, to the fixture or to the lookup that breaks the replay's shape
fails here and not in a paid run."""

import os
import re
import shutil
import subprocess
import sys
import unittest

from support import ScratchRepo, read, write

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPLAY = os.path.join(ROOT, "evals", "replay.py")
CASES = ("a-record-and-the-program-disagree", "asked-again-after-a-summary", "the-same-without-the-rule")


def find_bash():
    """A bash that runs a script in a Windows folder as Git Bash does, or None. On Windows the first bash on the path
    can be the one that starts WSL, which sees the folder under another name, so Git's own is looked for first."""
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            for up in (1, 2):
                top = git
                for _ in range(up + 1):
                    top = os.path.dirname(top)
                for sub in ("bin", os.path.join("usr", "bin")):
                    candidate = os.path.join(top, sub, "bash.exe")
                    if os.path.isfile(candidate):
                        return candidate
        return None
    return shutil.which("bash")


class ReplayTests(ScratchRepo):
    def build(self, *args):
        self.target = os.path.join(self.root, "build")
        result = subprocess.run([sys.executable, "-I", REPLAY, "--to", self.target, *args], cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def test_the_build_is_the_plugin_with_the_cases_in_it_and_the_command_is_only_printed(self):
        code, out, err = self.build()
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(os.path.join(self.target, ".claude-plugin", "plugin.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.target, "skills", "decide", "SKILL.md")))
        for folder, _, _ in os.walk(self.target):
            self.assertNotEqual(os.path.basename(folder), "__pycache__")
        for case in CASES:
            for name in ("prompt.md", "case.yaml", "fixture.sh"):
                self.assertTrue(os.path.isfile(os.path.join(self.target, "evals", case, name)), f"{case}/{name}")
            self.assertTrue(os.listdir(os.path.join(self.target, "evals", case, "graders")))
            self.assertNotIn("\r", read(os.path.join(self.target, "evals", case, "fixture.sh")))
        self.assertIn("3 cases built", out)
        self.assertIn("about 30 Claude Code sessions on your account", out)
        last = out.strip().split("\n")[-1]
        self.assertTrue(last.startswith("claude plugin eval "), last)
        for part in ("--scaffold", "--allow-tools Edit Write", "--runs 5", "--max-cost-usd 15", "--no-publish"):
            self.assertIn(part, last)
        # Whether the folder is trusted is the person's answer, in the terminal.
        self.assertNotIn("--trust-plugin", out)

        code, out, err = self.build("--runs", "2", "--max-cost-usd", "4", "--case", "asked-*")
        self.assertEqual(code, 0, out + err)
        self.assertIn("--runs 2", out)
        self.assertIn("--max-cost-usd 4 ", out)
        self.assertIn("--case asked-*", out)

    def test_a_folder_that_is_not_an_earlier_build_is_left_alone(self):
        write(os.path.join(self.root, "build", "mine.txt"), "not a build\n")
        code, out, err = self.build()
        self.assertNotEqual(code, 0)
        self.assertIn("is not an earlier build of the replay, so it is left alone", err)
        self.assertEqual(read(os.path.join(self.root, "build", "mine.txt")), "not a build\n")

    def test_the_made_up_repository_has_the_shape_of_the_incident(self):
        bash = find_bash()
        if not bash:
            self.skipTest("no bash on this machine to run a case's fixture.sh")
        code, out, err = self.build()
        self.assertEqual(code, 0, out + err)
        template = read(os.path.join(ROOT, "plugin", "templates", "rules", "recording-decisions.md"))
        for case in CASES:
            repo = os.path.join(self.root, "made-up", case)
            os.makedirs(repo)
            script = os.path.join(self.target, "evals", case, "fixture.sh")
            done = subprocess.run([bash, script], cwd=repo, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertTrue(os.path.isfile(os.path.join(repo, "CLAUDE.md")), case)
            rule = os.path.join(repo, ".claude", "rules", "recording-decisions.md")
            if case == "the-same-without-the-rule":
                self.assertFalse(os.path.exists(rule))
            else:
                self.assertEqual(read(rule), template)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
            self.assertEqual(status.stdout.strip(), "", "everything is committed")

            # Each grader that reads a file passes on the repository as it was built: it fails only after an edit.
            graders = os.path.join(self.target, "evals", case, "graders")
            read_a_file = 0
            for name in sorted(os.listdir(graders)):
                text = read(os.path.join(graders, name))
                target = re.search(r"^target: \{ source: file, path: (\S+) \}$", text, re.MULTILINE)
                if not target:
                    continue
                pattern = re.search(r"^pattern: '(.*)'$", text, re.MULTILINE).group(1)
                self.assertTrue(re.search(pattern, read(os.path.join(repo, *target.group(1).split("/")))), f"{case}/{name}")
                read_a_file += 1
            self.assertGreaterEqual(read_a_file, 1, case)

            # The lookup finds what a session should have read: the label, the manual, the test's name and the comment.
            code, out, err = self.run_script("decisions", "find", "export", "failed", "--repo", repo, "--no-memory")
            self.assertEqual(code, 0, out + err)
            self.assertIn("docs/ROADMAP.md:11  export failed; and the order of the exports on the page.", out)
            self.assertIn("in the entry at line 10: 2. **The job page.** Three answers still wait", out)
            self.assertIn('line 12 says "all three as recommended": it names a recommendation without saying it', out)
            # The item above it in the list holds the words too, and is another entry: the mark is not put on it.
            self.assertIn("docs/ROADMAP.md:9  1. **Retries.**", out)
            self.assertEqual(out.count("it names a recommendation without saying it"), 1)
            self.assertIn("docs/MANUAL.md:8  - A job whose export failed reads **Failed** until someone retries it.", out)
            self.assertIn("tests/test_jobs.py:16  def test_a_failed_export_reads_failed_until_a_retry():", out)
            self.assertIn("jobs/status.py:7  # A failed export keeps the job Running until a retry", out)
            self.assertIn("it cites 2026-03-02; a record holds that date at docs/DESIGN.md:13, docs/ROADMAP.md:12", out)


if __name__ == "__main__":
    unittest.main()
