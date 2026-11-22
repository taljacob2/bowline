"""The look, reorganized, on a scratch repository with six worktrees: what waits for the person comes first, then the
worktrees at work, then the idle ones in a line each and the quiet ones in one line; every line fits in 100 columns
of plain ASCII; `crew --json` is the model every view draws from; a session that asks the person a question, by
`crew say --asks` or by a reply that ends with one, waits for them until their next prompt; a quiet worktree whose
commits are on the pushed branch under other names holds nothing; and `crew watch` redraws until it is stopped."""

import json
import os
import subprocess
import sys
import time
import unittest

from support import SCRIPTS, ScratchRepo, git, write

import common  # noqa: E402 - support puts the scripts on the path
import crew  # noqa: E402

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]


class LookTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        self.configure({})
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        # A real repository ignores the folder its worktrees are made in; without that, git lists each as a file
        # not committed in the main checkout.
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        self.trees = {}
        for name in ("asking", "busy", "holding", "done", "quiet"):
            git(self.repo, "worktree", "add", "-q", "-b", name, os.path.join(".claude", "worktrees", name))
            self.trees[name] = os.path.join(self.repo, ".claude", "worktrees", name)
        self.age(self.repo, 120)
        self.age(self.trees["quiet"], 120)
        write(os.path.join(self.trees["holding"], "src", "half.py"), "half = 1\n")
        now = int(time.time() * 1000)
        self.agents(*[{"sessionId": "sess-" + name, "cwd": os.path.realpath(self.trees[name]), "kind": "interactive",
                       "name": "the " + name + " session", "pid": 1000 + i, "status": "busy" if name == "busy" else "idle",
                       "startedAt": now} for i, name in enumerate(("asking", "busy", "holding", "done"))])

    def configure(self, settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"),
              json.dumps({"crew": dict({"claude": FAKE_CLAUDE}, **settings)}) + "\n")

    def agents(self, *rows):
        write(self.agents_file, json.dumps(list(rows)) + "\n")

    def age(self, tree, minutes):
        """Makes a worktree's own git folder look last written some time ago, as one nobody commits in is."""
        folder = os.path.join(self.repo, ".git") if tree == self.repo else \
            os.path.join(self.repo, ".git", "worktrees", os.path.basename(tree))
        stamp = time.time() - minutes * 60
        for name in ("index", "HEAD", os.path.join("logs", "HEAD")):
            if os.path.exists(os.path.join(folder, name)):
                os.utime(os.path.join(folder, name), (stamp, stamp))

    def crew(self, *args, cwd=None, env=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8",
                                env=dict(os.environ, **(env or {})))
        return result.returncode, result.stdout, result.stderr

    def hook(self, mode, payload):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "doctor.py"), mode, "--no-memory"],
                                input=json.dumps(payload), cwd=self.repo, capture_output=True, text=True,
                                encoding="utf-8", env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_the_look_puts_what_waits_for_the_person_first(self):
        code, out, err = self.crew("say", "--asks", "Shall I push the parser?", cwd=self.trees["asking"],
                                   env={"CLAUDE_CODE_SESSION_ID": "sess-asking"})
        self.assertEqual(code, 0, out + err)
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        order = ["WAITS FOR YOU", "  asking: a session asks you a question", 'asks, less than a minute ago: "Shall I push the parser?"',
                 "  holding: idle, with work not committed", "AT WORK", "  busy: 1 session busy", "IDLE, HOLDING NOTHING",
                 '  done: "the done session"', "QUIET: 2 worktrees", "ACROSS THE WORKTREES"]
        places = [out.find(words) for words in order]
        self.assertNotIn(-1, places, out)
        self.assertEqual(places, sorted(places), out)
        self.assertIn("6 worktrees and 4 sessions: 2 wait for you, 1 at work, 1 idle, 2 quiet.", out)
        self.assertIn("holds: 1 untracked file, written less than a minute ago", out)
        self.assertIn('session "the holding session": idle', out)
        for line in out.splitlines():
            self.assertLessEqual(len(line), 100, line)
            self.assertTrue(all(32 <= ord(ch) < 127 for ch in line), line)
        code, out, _ = self.crew("say", "--asks", cwd=self.trees["asking"], env={"CLAUDE_CODE_SESSION_ID": "sess-asking"})
        self.assertIn("Shall I push the parser?", out)
        self.crew("say", "--asks", "--clear", cwd=self.trees["asking"], env={"CLAUDE_CODE_SESSION_ID": "sess-asking"})
        code, out, _ = self.crew()
        self.assertNotIn("asks you", out)
        self.assertIn('  asking: "the asking session"', out)                    # idle, holding nothing, now

    def test_json_is_the_model_the_printout_draws_from(self):
        self.crew("say", "--asks", "Which name?", cwd=self.trees["asking"], env={"CLAUDE_CODE_SESSION_ID": "sess-asking"})
        code, out, err = self.crew("--json")
        self.assertEqual(code, 0, out + err)
        model = json.loads(out)
        for key in ("repository", "base", "at", "sessionsListed", "counts", "worktrees", "overlaps", "shared",
                    "keepPorts", "outside", "turn", "unreachable", "dropped"):
            self.assertIn(key, model)
        by = {tree["display"]: tree for tree in model["worktrees"]}
        self.assertEqual({name: by[name]["group"] for name in by},
                         {"the main checkout": "quiet", "asking": "waits", "busy": "work", "holding": "waits",
                          "done": "idle", "quiet": "quiet"})
        self.assertEqual(by["asking"]["reason"], "asks")
        self.assertEqual(by["holding"]["reason"], "idle-uncommitted")
        self.assertEqual(by["asking"]["sessions"][0]["asks"]["words"], "Which name?")
        self.assertEqual(by["busy"]["sessions"][0]["status"], "busy")
        self.assertEqual(by["holding"]["uncommitted"], 1)
        self.assertEqual(model["counts"], {"worktrees": 6, "sessions": 4, "offline": 0, "waits": 2, "work": 1, "idle": 1,
                                           "quiet": 2, "broken": 0})
        self.assertTrue(model["sessionsListed"])

    def test_a_reply_that_ends_with_a_question_waits_for_the_person_until_the_next_prompt(self):
        stop = {"hook_event_name": "Stop", "session_id": "sess-done", "cwd": self.trees["done"],
                "last_assistant_message": "The parser is built and its tests pass.\n\n**Shall I push it to main?**\n"}
        self.hook("--watch", stop)
        asked = crew.load_asks(self.repo)
        self.assertEqual([(entry["session"], entry["words"], entry["by"]) for entry in asked],
                         [("sess-done", "Shall I push it to main?", "reply")])
        code, out, _ = self.crew()
        self.assertIn("  done: a session asks you a question", out)
        self.hook("--watch", dict(stop, last_assistant_message="Pushed as 1a2b3c4. Nothing is left."))
        self.assertEqual(crew.load_asks(self.repo), [])                          # the next reply asks nothing
        self.hook("--watch", stop)
        prompt = {"hook_event_name": "UserPromptSubmit", "session_id": "sess-done", "cwd": self.trees["done"],
                  "prompt": "yes"}
        self.hook("--pending", prompt)
        self.assertEqual(crew.load_asks(self.repo), [])                          # the person answered
        # A question in the middle of a reply that ends otherwise is not a wait, and the setting turns it off.
        self.hook("--watch", dict(stop, last_assistant_message="Why did it fail? The cache was cold. Fixed."))
        self.assertEqual(crew.load_asks(self.repo), [])
        # The setting is read where the session works: its worktree's own .claude/bowline.json.
        write(os.path.join(self.trees["done"], ".claude", "bowline.json"),
              json.dumps({"crew": {"claude": FAKE_CLAUDE, "asksFromReply": False}}) + "\n")
        self.hook("--watch", stop)
        self.assertEqual(crew.load_asks(self.repo), [])

    def test_a_quiet_worktree_whose_commits_are_on_the_branch_by_content_holds_nothing(self):
        bare = os.path.join(self.root, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        git(self.repo, "remote", "add", "origin", bare)
        write(os.path.join(self.trees["quiet"], "src", "fix.py"), "fixed = 1\n")
        git(self.trees["quiet"], "add", "src/fix.py")
        git(self.trees["quiet"], "commit", "-q", "-m", "a fix")
        git(self.repo, "cherry-pick", "-x", "quiet")                             # main takes it under another hash
        git(self.repo, "push", "-q", "-u", "origin", "main")
        self.age(self.repo, 120)
        self.age(self.trees["quiet"], 120)
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        self.assertIn("QUIET: 2 worktrees with no session and no sign of work in 30 minutes. None holds work that "
                      "is not on origin/main. quiet's 1 commit is on origin/main by content.", " ".join(out.split()))
        write(os.path.join(self.trees["quiet"], "src", "more.py"), "more = 1\n")
        git(self.trees["quiet"], "add", "src/more.py")
        git(self.trees["quiet"], "commit", "-q", "-m", "more, not pushed")
        self.age(self.trees["quiet"], 120)
        code, out, _ = self.crew()
        self.assertIn("1 holds work that is not on origin/main: quiet (1 commit not on origin/main).", " ".join(out.split()))

    def test_untracked_files_nobody_has_written_for_a_day_do_not_wait_for_the_person(self):
        # On 2026-11-22 the look put the main checkout of the first user's repository under WAITS FOR YOU, "idle, with
        # work not committed", for a Vite cache and an editor's settings, untracked, that nobody had written for weeks.
        done = self.trees["done"]
        old = time.time() - 29 * 24 * 3600
        for path in (".vite/deps/package.json", ".vite/deps/_metadata.json", ".vscode/settings.json"):
            write(os.path.join(done, path), "{}\n")
            os.utime(os.path.join(done, path), (old - 3600, old - 3600) if "vscode" in path else (old, old))
        day = time.localtime(old)
        months = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December")
        when = f"from {day.tm_mday} {months[day.tm_mon - 1]}" + (
            f" {day.tm_year}" if day.tm_year != time.localtime().tm_year else "")
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        text = " ".join(out.split())
        self.assertIn("IDLE, HOLDING NOTHING: nothing to commit but untracked files nobody has written in 24 hours", text)
        self.assertIn(f'done: "the done session", and 3 untracked files, the newest {when}, none written in 24 hours',
                      text)
        self.assertNotIn("done: idle, with work not committed", text)
        model = json.loads(self.crew("--json")[1])
        tree = next(item for item in model["worktrees"] if item["display"] == "done")
        self.assertEqual((tree["group"], tree["uncommitted"], tree["untracked"], tree["untrackedOld"]), ("idle", 3, 3, True))
        self.assertAlmostEqual(tree["untrackedAt"], old, delta=2)
        # A change to a tracked file is work in hand, whatever the untracked files' age.
        write(os.path.join(done, "README.md"), "# changed\n")
        text = " ".join(self.crew()[1].split())
        self.assertIn("done: idle, with work not committed", text)
        self.assertIn(f"holds: 1 file not committed, 3 untracked files, the newest {when}", text)
        # So is an untracked file written today.
        git(done, "checkout", "-q", "--", "README.md")
        write(os.path.join(done, "src", "new.py"), "new = 1\n")
        text = " ".join(self.crew()[1].split())
        self.assertIn("done: idle, with work not committed", text)
        self.assertIn("holds: 4 untracked files, the newest written less than a minute ago", text)
        self.assertIn("holds: 1 untracked file, written less than a minute ago", text)          # the holding worktree

    def test_watch_redraws_until_it_is_stopped(self):
        code, out, err = self.crew("watch", "--every", "0.5", "--times", "2")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(out.count("bowline crew: "), 2, out)
        self.assertIn("WAITS FOR YOU", out)
        self.assertIn("Redrawn every 0.5 seconds", out)
        self.assertIn("Ctrl+C stops it.", out)
        self.assertNotIn("\x1b", out)                                            # not a terminal: no codes that clear it


if __name__ == "__main__":
    unittest.main()
