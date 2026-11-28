"""The replay's own parts that need no Claude Code session: the copy of the plugin with the cases in it, and the
made-up repository each case starts in. The repository is built by the same bash script a case runs, and then the
lookup is run on it, so that a change to a template, to the fixture or to the lookup that breaks the replay's shape
fails here and not in a paid run."""

import importlib.util
import json
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


def load_replay():
    spec = importlib.util.spec_from_file_location("bowline_replay", REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_bash():
    """A bash that runs a script in a Windows folder as Git Bash does, or None. On Windows the first bash on the path
    can be the one that starts WSL, which loses the backslashes of the script's path, so the replay's own way of
    finding Git's bash is used: the test and a real run then start a case's script with the same program."""
    if os.name == "nt":
        return load_replay().git_bash()
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
            # A session of the replay loads no rule from the made-up repository, so a case that has the rule hands
            # its text over in the prompt's front matter; the case without the rule hands over nothing.
            prompt = read(os.path.join(self.target, "evals", case, "prompt.md"))
            front = prompt.split("\n---\n", 1)[0]
            self.assertNotIn("append_system_prompt", read(os.path.join(ROOT, "evals", "decisions", case, "prompt.md")))
            if case == "the-same-without-the-rule":
                self.assertNotIn("append_system_prompt", prompt)
            else:
                self.assertIn("\nappend_system_prompt: |\n  Contents of .claude/rules/recording-decisions.md (project "
                              "instructions, checked into the codebase):\n\n  # Where a decision is written down\n", front)
                self.assertIn("\n  - **Look the subject up first.** Before you put a design question to the person", front)
                self.assertIn("\n  ## Before a question goes to the person\n", front)
                for line in front.split("append_system_prompt: |\n", 1)[1].split("\n"):
                    self.assertTrue(line == "" or line.startswith("  "), line)
        self.assertIn("3 cases built", out)
        self.assertIn("about 30 Claude Code sessions on your account", out)
        commands = [line for line in out.split("\n") if line.startswith("claude plugin eval ")]
        self.assertEqual(len(commands), 1, out)
        for part in ("--scaffold", "--allow-tools Edit Write", "--runs 5", "--max-cost-usd 15", "--no-publish"):
            self.assertIn(part, commands[0])
        # On Windows the printed line is not enough: only --run makes sure which bash runs a case's script.
        self.assertEqual("start it with --run and not by copying the line above" in out, os.name == "nt", out)
        # Whether the folder is trusted is the person's answer, in the terminal.
        self.assertNotIn("--trust-plugin", out)

        self.assertNotIn("--keep-temp", out)
        code, out, err = self.build("--runs", "2", "--max-cost-usd", "4", "--case", "asked-*", "--keep-temp")
        self.assertEqual(code, 0, out + err)
        self.assertIn("--runs 2", out)
        self.assertIn(" --keep-temp", out)
        self.assertNotIn("--ablation", out)
        self.assertIn("--max-cost-usd 4 ", out)
        self.assertIn("--case asked-*", out)
        code, out, err = self.build("--with-only")
        self.assertIn(" --ablation none", out)
        self.assertIn("about 15 Claude Code sessions on your account, every one with the plugin,", out)

    def test_a_folder_that_is_not_an_earlier_build_is_left_alone(self):
        write(os.path.join(self.root, "build", "mine.txt"), "not a build\n")
        code, out, err = self.build()
        self.assertNotEqual(code, 0)
        self.assertIn("is not an earlier build of the replay, so it is left alone", err)
        self.assertEqual(read(os.path.join(self.root, "build", "mine.txt")), "not a build\n")

    @unittest.skipUnless(os.name == "nt", "only on Windows can the first bash on the path be the wrong one")
    def test_on_windows_a_run_puts_the_bash_of_git_first_on_the_path(self):
        # `claude plugin eval` starts a case's fixture.sh with the first bash on the path. A stand-in for claude says
        # which bash that is, on a path where Windows' own folder, the home of the bash that starts WSL, comes first.
        git_bash = find_bash()
        if not git_bash:
            self.skipTest("no Git with its bash on this machine")
        stand_in = os.path.join(self.root, "stand-in")
        os.makedirs(stand_in)
        with open(os.path.join(stand_in, "claude.cmd"), "w", encoding="ascii", newline="\r\n") as handle:
            handle.write("@echo off\nwhere bash\n")
        windows = os.path.join(os.environ["SystemRoot"], "System32")
        environment = dict(os.environ)
        environment["PATH"] = os.pathsep.join([stand_in, windows, os.path.dirname(shutil.which("git"))])
        result = subprocess.run([sys.executable, "-I", REPLAY, "--to", os.path.join(self.root, "build"), "--run"],
                                cwd=self.root, capture_output=True, text=True, encoding="utf-8", env=environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        found = [line for line in result.stdout.split("\n") if line.lower().endswith("bash.exe")]
        self.assertTrue(found, result.stdout)
        self.assertEqual(os.path.normcase(found[0]), os.path.normcase(git_bash), result.stdout)
        self.assertIn("is put first on the search path", result.stdout)
        self.assertNotIn("--trust-plugin", result.stdout)

    def test_a_result_is_read_as_each_checks_passes_and_each_reply_as_a_file(self):
        def run(score, reply, **marks):
            graders = [{"name": name, "passed": passed} for name, passed in marks.items()]
            graders.append({"name": "the-reply-reports-and-asks", "passed": True, "evidence": reply})
            return {"score": score, "turns": 7, "costUsd": 0.2, "graders": graders}

        result = os.path.join(self.root, "result")
        case = {"name": "a-record-and-the-program-disagree", "arms": {
            "with": [run(1, "I have changed nothing.", **{"the-skill-was-used": True, "the-program-is-as-it-was": True}),
                     run(1, "Nothing is edited yet.", **{"the-skill-was-used": False, "the-program-is-as-it-was": True})],
            "without": [run(0.5, "I changed the code.", **{"the-program-is-as-it-was": False})]}}
        # The cost cap stopped the judge of one run: that run is not counted for the check.
        case["arms"]["with"][1]["graders"][-1] = {"name": "the-reply-reports-and-asks", "passed": False,
                                                "explanation": "skipped: cost ceiling"}
        write(os.path.join(result, "aggregate-result.json"), json.dumps({"costUsd": 0.6, "cases": [case]}))
        done = subprocess.run([sys.executable, "-I", REPLAY, "--read", result], cwd=self.root, capture_output=True,
                              text=True, encoding="utf-8")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("3 sessions, 0.60 dollars", done.stdout)
        lines = [" ".join(line.split()) for line in done.stdout.split("\n")]
        self.assertIn("check with without", lines)
        self.assertIn("the-skill-was-used 1 of 2 -", lines)
        self.assertIn("the-program-is-as-it-was 2 of 2 0 of 1", lines)
        self.assertIn("the-reply-reports-and-asks 1 of 1 1 of 1", lines)
        reply = read(os.path.join(result, "replies", "a-record-and-the-program-disagree.without.1.md"))
        self.assertIn("without the plugin, run 1: score 0.50, 7 turns, 0.20 dollars.", reply)
        self.assertIn("Failed: the-program-is-as-it-was.", reply)
        self.assertTrue(reply.endswith("I changed the code.\n"), reply)
        second = read(os.path.join(result, "replies", "a-record-and-the-program-disagree.with.2.md"))
        self.assertIn("Failed: the-skill-was-used. Skipped at the cost cap: the-reply-reports-and-asks.", second)
        self.assertIn("(The result holds no reply for this run.)", second)
        # No command was printed: reading a result builds and starts nothing.
        self.assertNotIn("claude plugin eval", done.stdout)

        done = subprocess.run([sys.executable, "-I", REPLAY, "--read", os.path.join(self.root, "no-such")],
                              cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(done.returncode, 2)
        self.assertIn("holds no aggregate-result.json", done.stderr)

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
