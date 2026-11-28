"""The crew on a scratch repository with two worktrees: who is here, claims and the next free number across worktrees,
a number that appears twice and a stale stamp after a rebase, who waits on a push, the wait for a quiet machine and the
turn, the line at a session's start when another session is at work, and memory lines lost between two sessions."""

import json
import os
import subprocess
import sys
import time
import unittest

from support import SCRIPTS, ScratchRepo, age_git_folder, git, read, write

import common  # noqa: E402 - support puts the scripts on the path
import crew  # noqa: E402

ROOT = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"
ROADMAP = "# Roadmap\n\n## Next\n\n1. **One.** First.\n2. **Two.** Second.\n3. **Three.** Third.\n"
HEAVY = "bowline-test-heavy-" + str(os.getpid())
# The stand-in for claude: `agents --json` lists the sessions of the file FAKE_CLAUDE_AGENTS names.
FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]


def flat(text):
    """A printout with its lines joined, since a long line is wrapped at 100 columns."""
    return " ".join(text.split())


class CrewTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        write(os.path.join(self.repo, "docs", "ROADMAP.md"), ROADMAP)
        self.configure({"heavy": [HEAVY], "keepPorts": [59999],
                        "numbers": {"roadmap": {"file": "docs/ROADMAP.md", "pattern": "^(\\d+)\\."}},
                        "stamps": [{"file": "web/.source-commit", "remake": "make stamp"}]})
        git(self.repo, "add", "CLAUDE.md", "docs/ROADMAP.md", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "a roadmap and the crew's settings")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.other = [tree["path"] for tree in crew.worktrees(self.repo) if not tree["main"]][0]

    def configure(self, settings):
        """Writes the crew's settings, with the stand-in for claude unless they name another program. The sentence a
        session's start gets about looking a decision up is turned off with them, so that a test which turns the line
        about other sessions off sees a start that says nothing."""
        write(os.path.join(self.repo, ".claude", "bowline.json"),
              json.dumps({"crew": dict({"claude": FAKE_CLAUDE}, **settings), "decisions": {"atStart": False}}) + "\n")

    def agents(self, *rows):
        """What `claude agents --json` lists from now on."""
        write(self.agents_file, json.dumps(list(rows)) + "\n")

    def crew(self, *args, cwd=None, stdin=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args], input=stdin,
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def hook(self, action, command, cwd):
        """Runs a crew check the way the PostToolUse hook does: the tool call's JSON on standard input."""
        payload = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
        return self.crew(action, "--hook", cwd=self.root, stdin=payload)

    def with_origin(self):
        bare = os.path.join(self.root, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        git(self.repo, "remote", "add", "origin", bare)
        git(self.repo, "push", "-q", "-u", "origin", "main")
        return bare

    def test_the_look_names_both_worktrees_and_the_persons_ports(self):
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        self.assertIn("2 worktrees", out)
        self.assertIn("\n  the main checkout (this one): ", out)
        self.assertIn("\n  other: ", out)                                       # a worktree goes by its folder's name
        self.assertIn("A worktree is named by its folder in .claude/worktrees.", flat(out))
        self.assertIn("Never stop what listens on them", out)
        self.assertIn("59999: nothing listens now", out)
        self.assertIn("The turn for a heavy check is free.", out)
        self.assertIn("To tell a session what you take: SendMessage.", out)
        code, out, _ = self.crew(cwd=self.other)
        self.assertIn("\n  other (this one): ", out)

    def test_a_file_changed_in_two_worktrees_is_named(self):
        write(os.path.join(self.repo, "docs", "ROADMAP.md"), ROADMAP + "4. **Four.** Mine.\n")
        write(os.path.join(self.other, "docs", "ROADMAP.md"), ROADMAP + "4. **Four.** Theirs.\n")
        write(os.path.join(self.repo, "src", "parser.py"), "mine = 1\n")
        write(os.path.join(self.other, "src", "parser.py"), "theirs = 1\n")
        code, out, _ = self.crew()
        self.assertIn("Changed differently in more than one worktree", out)
        # Grouped by the worktrees that share them, which says which sessions must talk.
        self.assertIn("the main checkout and other: docs/ROADMAP.md, src/parser.py", flat(out))
        # The roadmap is a record every session adds to: named apart, so that the list keeps what nobody expects.
        self.configure({"shared": ["docs/ROAD*.md"]})
        code, out, _ = self.crew()
        differently, _, records = flat(out).partition("Shared records (crew.shared)")
        self.assertIn("the main checkout and other: src/parser.py", differently)
        self.assertNotIn("docs/ROADMAP.md", differently.partition("ACROSS THE WORKTREES")[2])
        self.assertIn("docs/ROADMAP.md: the main checkout, other", records)
        # What the look measured is kept for a hook that must answer at once.
        kept = crew.cached_survey(self.repo)
        self.assertEqual([tree["name"] for tree in kept["trees"]], ["the main checkout", ".claude/worktrees/other"])
        self.assertIn("src/parser.py", kept["trees"][1]["files"])
        self.assertIn("src/parser.py", kept["trees"][1]["dirty"])
        os.remove(os.path.join(self.repo, ".git", "bowline", "crew", "changed.json"))
        self.assertIsNone(crew.cached_survey(self.repo))
        self.assertEqual(self.crew("refresh"), (0, "", ""))
        self.assertIsNotNone(crew.cached_survey(self.repo))

    def test_the_same_content_in_two_worktrees_is_not_a_collision(self):
        # The other branch is cut from this one's commit: both hold the file, and neither changed it differently.
        self.with_origin()
        write(os.path.join(self.repo, "src", "parser.py"), "shared = 1\n")
        git(self.repo, "add", "src/parser.py")
        git(self.repo, "commit", "-q", "-m", "a parser")
        git(self.other, "merge", "-q", "--ff-only", "main")
        trees = crew.survey(crew.Place(self.repo))["trees"]
        self.assertEqual(trees[0]["blobs"]["src/parser.py"], trees[1]["blobs"]["src/parser.py"])
        head = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.assertEqual([tree["head"] for tree in trees], [head, head])       # each worktree's commit is in the record
        self.assertEqual(crew.collisions(trees), {})
        write(os.path.join(self.other, "src", "parser.py"), "shared = 2\n")   # one goes on from there: still none
        self.assertEqual(crew.collisions(crew.survey(crew.Place(self.repo))["trees"]), {})
        write(os.path.join(self.repo, "src", "parser.py"), "shared = 3\n")    # both go on, each its own way
        self.assertEqual(crew.collisions(crew.survey(crew.Place(self.repo))["trees"]),
                         {"src/parser.py": ["the main checkout", ".claude/worktrees/other"]})

    def test_a_worktree_this_system_cannot_enter_is_said_and_keeps_its_claims(self):
        self.crew("claim", "file:src/a.py", cwd=self.other)
        os.rename(self.other, os.path.join(self.root, "moved-away"))              # git still lists it; the folder is gone
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        self.assertIn("1 worktree and 0 sessions", out)
        self.assertIn("Left out: 1 worktree that git lists and this system cannot enter", flat(out))
        self.assertNotIn("Dropped the claim", out)
        code, out, _ = self.crew("claim", "file:src/a.py")
        self.assertEqual(code, 1, out)

    def test_a_claim_is_refused_to_a_second_worktree_and_given_back(self):
        code, out, _ = self.crew("claim", "note:17", "--why", "the slow start")
        self.assertEqual(code, 0, out)
        self.assertIn("note:17 is this worktree's", out)
        code, out, _ = self.crew("claim", "Note:17", cwd=self.other)             # another spelling of the same key
        self.assertEqual(code, 1, out)
        self.assertIn("is taken by the main checkout", out)
        self.assertIn("the slow start", out)
        code, out, _ = self.crew("claim", "file:docs/README.md", cwd=self.other)  # a claim keeps the spelling typed
        self.assertIn("file:docs/README.md is this worktree's", out)
        code, out, _ = self.crew("claim", "FILE:docs/readme.md")
        self.assertEqual(code, 1, out)
        self.crew("release", "file:docs/readme.md", cwd=self.other)
        code, out, _ = self.crew("release", "note:17", cwd=self.other)          # not theirs to give back
        self.assertIn("note:17 is the main checkout's, not this worktree's; it was left.", out)
        code, out, _ = self.crew(cwd=self.other)
        self.assertIn("claim: note:17", out)
        code, out, _ = self.crew("release", "--all")
        self.assertIn("given back: note:17", out)
        code, out, _ = self.crew("claim", "note:17", cwd=self.other)
        self.assertEqual(code, 0, out)
        code, out, err = self.crew("claim", "seventeen")
        self.assertEqual(code, 2)
        self.assertIn("a kind and a name with a colon", err)
        claims = os.path.join(self.repo, ".git", "bowline", "crew", "claims.json")
        self.assertTrue(os.path.isfile(claims))                                  # in the git folder every worktree shares
        with open(claims, "rb") as handle:
            self.assertNotIn(b"\r", handle.read())

    def test_the_next_number_counts_every_worktrees_copy_and_every_claim(self):
        # The other session wrote item 4 an hour ago and has neither committed nor claimed it.
        write(os.path.join(self.other, "docs", "ROADMAP.md"), ROADMAP + "4. **Four.** Theirs, not committed.\n")
        code, out, _ = self.crew("claim", "roadmap", "--new", "--why", "the log viewer")
        self.assertEqual(code, 0, out)
        self.assertIn("roadmap:5 is this worktree's", out)
        code, out, _ = self.crew("claim", "roadmap", "--new", cwd=self.other)    # a claim counts before it is written
        self.assertIn("roadmap:6 is this worktree's", out)
        code, out, _ = self.crew("claim", "roadmap:5", cwd=self.other)
        self.assertEqual(code, 1, out)
        self.assertIn("the log viewer", out)
        code, out, err = self.crew("claim", "backlog", "--new")
        self.assertEqual(code, 2)
        self.assertIn("names no numbered list called 'backlog'", err)

    def test_a_claim_of_a_worktree_that_is_gone_is_dropped(self):
        self.crew("claim", "file:src/a.py", cwd=self.other)
        git(self.repo, "worktree", "remove", "--force", self.other)
        code, out, _ = self.crew()
        self.assertIn("Dropped the claim file:src/a.py", flat(out))
        self.assertIn("its worktree is gone", flat(out))
        code, out, _ = self.crew("claim", "file:src/a.py")
        self.assertEqual(code, 0, out)

    def test_several_may_wait_on_one_push_and_the_pusher_is_told(self):
        self.with_origin()
        code, out, _ = self.crew("claim", "waits:main", "--why", "the parser fix", cwd=self.other)
        self.assertEqual(code, 0, out)
        code, out, err = self.hook("after-push", "git push -q origin HEAD:main", self.repo)
        self.assertEqual(code, 0, err)
        said = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(said["hookEventName"], "PostToolUse")
        self.assertIn("1 session waits on this worktree; after this push its HEAD is", said["additionalContext"])
        self.assertIn(".claude/worktrees/other, for: the parser fix", said["additionalContext"])
        self.assertIn("SendMessage", said["additionalContext"])
        code, out, _ = self.hook("after-push", "git status", self.repo)          # not a push: nothing
        self.assertEqual((code, out), (0, ""))
        code, out, _ = self.hook("after-push", "git push", self.other)           # nobody waits on the other worktree,
        self.assertIn("still holds: waits:main", out)                            # but it is reminded of what it holds
        self.crew("release", "--all", cwd=self.other)
        self.crew("claim", "waits:other", "--why", "its branch, by name")        # a wait may name a branch or a folder
        code, out, _ = self.hook("after-push", "git push", self.other)
        self.assertIn("the main checkout, for: its branch, by name", out)
        # A session on a branch of its own commits long before it pushes: whoever waits is said after a commit too.
        code, out, _ = self.hook("after-commit", "git commit -q -F message.txt", self.other)
        said = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1 session waits on this worktree; after this commit its HEAD is", said)
        self.assertNotIn("still holds", said)
        code, out, _ = self.hook("after-commit", "git push", self.other)          # not a commit: nothing
        self.assertEqual((code, out), (0, ""))
        self.crew("release", "--all")
        code, out, _ = self.hook("after-push", "git push", self.repo)
        self.assertEqual((code, out), (0, ""))

    def test_after_a_rebase_a_number_twice_and_a_landed_claim_are_said(self):
        self.with_origin()
        code, out, _ = self.hook("after-rebase", "git pull --rebase origin main", self.repo)
        self.assertEqual((code, out), (0, ""))                                    # nothing wrong: nothing said
        # Two sessions each added item 4; the other one pushed first, and this one's rebase joined both.
        self.crew("claim", "roadmap:4")
        write(os.path.join(self.other, "docs", "ROADMAP.md"), ROADMAP + "4. **Four.** Theirs.\n")
        git(self.other, "commit", "-q", "-am", "item 4, theirs")
        git(self.other, "push", "-q", "origin", "HEAD:main")
        write(os.path.join(self.repo, "docs", "ROADMAP.md"), ROADMAP + "4. **Four.** Theirs.\n4. **Four.** Mine.\n")
        git(self.repo, "fetch", "-q", "origin")
        code, out, _ = self.hook("after-rebase", "cd . && git rebase origin/main", self.repo)
        said = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("docs/ROADMAP.md now holds the number 4 2 times (lines 8, 9)", said)
        self.assertIn("crew claim roadmap --new", said)
        self.assertIn("roadmap:4, which this worktree claimed, is dropped: origin/main now holds it", said)
        code, out, _ = self.crew("after-rebase")                                  # by hand: plain lines, exit code 1
        self.assertEqual(code, 1, out)
        self.assertIn("holds the number 4 2 times", out)
        code, out, _ = self.run_script("doctor", "--no-memory")                  # and the doctor warns
        self.assertIn("WARNING  docs/ROADMAP.md holds the number 4 2 times, at lines 8, 9.", out)
        self.assertIn("/bowline:crew", out)

    def test_a_stamp_that_names_a_commit_the_branch_lost_is_stale(self):
        head = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        write(os.path.join(self.repo, "web", ".source-commit"), head + "\n")
        self.assertEqual(crew.stale_stamps(self.repo, common.load_config(self.repo)), [])
        code, out, _ = self.crew("after-rebase")
        self.assertEqual((code, out), (0, ""))
        gone = "1a2b3c4d5e6f7a8b9c0d1a2b3c4d5e6f7a8b9c0d"
        write(os.path.join(self.repo, "web", ".source-commit"), gone + "\n")
        code, out, _ = self.crew("after-rebase")
        self.assertEqual(code, 1, out)
        self.assertIn("The stamp web/.source-commit names the commit 1a2b3c4d5e6f, which is not in this branch's history", out)
        self.assertIn("Remake it: make stamp.", out)
        code, out, _ = self.run_script("doctor", "--no-memory")
        self.assertIn("WARNING  The stamp web/.source-commit names the commit 1a2b3c4d5e6f", out)

    def test_run_waits_for_a_heavy_process_and_then_passes_the_exit_code(self):
        heavy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", HEAVY])
        try:
            time.sleep(1)
            code, out, err = self.crew("run", "--timeout", "0.05", "--every", "0.5", "--", sys.executable, "-c", "print('ran')")
            self.assertEqual(code, 3, out + err)
            self.assertNotIn("ran", out)
            self.assertIn("waiting for a quiet machine", err)
            self.assertIn(f"pid {heavy.pid}", err)
            self.assertIn("Nothing was stopped", err)
            self.assertIsNone(heavy.poll())                                       # and nothing was stopped
        finally:
            heavy.kill()
            heavy.wait()
        # The command's own words match the heavy pattern: the waiting command and the shell above it are not the
        # heavy process, or two waiting sessions would wait for each other.
        code, out, err = self.crew("run", "--timeout", "0.5", "--every", "0.5", "--", sys.executable, "-c",
                                   "import sys; print('ran'); sys.exit(7)", HEAVY)
        self.assertEqual(code, 7, out + err)
        self.assertIn("ran", out)
        self.assertIn("the machine is quiet", err)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".git", "bowline", "crew", "turn.json")))

    def test_run_waits_for_the_turn_and_takes_one_whose_holder_is_gone(self):
        turn = os.path.join(self.repo, ".git", "bowline", "crew", "turn.json")
        write(turn, json.dumps({"pid": os.getpid(), "worktree": self.other, "command": "the suite", "since": "2026-11-21 10:00"}) + "\n")
        code, out, err = self.crew("run", "--timeout", "0.03", "--every", "0.5", "--", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 3, out + err)
        self.assertIn("the turn, held since 2026-11-21 10:00 by .claude/worktrees/other for: the suite", err)
        code, out, _ = self.crew()
        self.assertIn("The turn for a heavy check is held since 2026-11-21 10:00 by other", flat(out))
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        write(turn, json.dumps({"pid": dead.pid, "worktree": self.other, "command": "the suite", "since": "2026-11-21 10:00"}) + "\n")
        code, out, err = self.crew("run", "--timeout", "0.5", "--every", "0.5", "--", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 0, out + err)
        self.assertIn("ran", out)

    def test_run_without_heavy_patterns_says_so_and_runs(self):
        self.configure({})
        code, out, err = self.crew("run", "--", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 0, out + err)
        self.assertIn("names no heavy processes (crew.heavy)", err)
        self.assertIn("ran", out)
        code, out, err = self.crew("run")
        self.assertEqual(code, 2)
        self.assertIn("name the command after two dashes", err)

    def transcript(self, tree, name, minutes_ago=0):
        path = os.path.join(common.project_folder(tree), name + ".jsonl")
        write(path, "{}\n")
        stamp = time.time() - minutes_ago * 60
        os.utime(path, (stamp, stamp))
        return path

    def brief(self, stdin, mode="--brief"):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "doctor.py"), mode, "--no-memory"], input=stdin,
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def quiet_git_folder(self, tree, minutes_ago):
        """Makes a worktree's own git folder look last written some time ago, as one nobody commits in is."""
        age_git_folder(self.repo, tree, minutes_ago * 60)

    def test_a_sessions_start_says_when_another_session_is_at_work(self):
        mine = self.transcript(self.repo, "mine")
        payload = json.dumps({"hook_event_name": "SessionStart", "transcript_path": mine, "cwd": self.repo})
        # A worktree made a moment ago shows a sign of work, its git folder, with no transcript at all: a session
        # started in another folder that works here by path is seen this way.
        code, out, _ = self.brief(payload)
        self.assertIn("1 other Claude Code session has worked in this repository", out)
        self.quiet_git_folder(self.other, 120)
        code, out, err = self.brief(payload)                                     # alone: the line says so, and why it came
        self.assertEqual((code, err), (0, ""))
        self.assertIn("bowline: no other Claude Code session shows a sign of work in this repository right now.", out)
        self.assertIn("Work as if one may start at any moment", out)
        self.assertIn("follow /bowline:crew", out)
        self.crew("claim", "note:3", cwd=self.other)                             # a claim is a sign of work too
        code, out, _ = self.brief(payload)
        self.assertIn("in .claude/worktrees/other.", out)
        self.crew("release", "--all", cwd=self.other)
        self.transcript(self.other, "theirs", minutes_ago=90)
        self.assertIn("bowline: no other Claude Code session shows a sign of work in this repository right now.", self.brief(payload)[1])                 # a session that ended long ago: nobody
        self.transcript(self.other, "theirs", minutes_ago=5)
        code, out, err = self.brief(payload)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("1 other Claude Code session has worked in this repository in the last 30 minutes: in "
                      ".claude/worktrees/other.", out)
        self.assertIn("follow /bowline:crew", out)
        self.assertIn("work with it as a team: /bowline:collaborate.", out)
        self.assertIn("send that session the person's words with SendMessage, as /bowline:collaborate says", out)
        # A repository without a rule gets the rule's main points and where the setup is; one with a rule does not.
        self.assertIn("This repository has no rule about working beside other sessions", out)
        self.assertIn("The last section of /bowline:crew sets the repository up", out)
        rule = os.path.join(self.repo, ".claude", "rules", "beside-other-sessions.md")
        write(rule, read(os.path.join(os.path.dirname(SCRIPTS), "templates", "crew", "beside-other-sessions.md")))
        code, out, _ = self.brief(payload)
        self.assertIn("work with it as a team: /bowline:collaborate.", out)
        self.assertIn("send that session the person's words with SendMessage, as /bowline:collaborate says", out)
        self.assertNotIn("no rule about working beside other sessions", out)
        self.assertNotIn("sets the repository up", out)
        os.remove(rule)
        self.transcript(self.repo, "a-second-session-in-this-folder", minutes_ago=2)
        code, out, _ = self.brief(payload)
        self.assertIn("2 other Claude Code sessions have worked", out)
        self.assertIn("in .claude/worktrees/other; in your own folder, the main checkout.", out)    # each place on its own
        self.assertEqual(crew.others_active(self.repo, {"crew": {"activeMinutes": 0}}), [])   # 0 turns the line off
        self.configure({"activeMinutes": 0})
        self.assertEqual(self.brief(payload), (0, "", ""))

    def test_a_running_session_is_told_before_a_prompt_when_another_one_appears(self):
        mine = self.transcript(self.repo, "mine")
        start = json.dumps({"hook_event_name": "SessionStart", "transcript_path": mine, "cwd": self.repo})
        prompt = json.dumps({"hook_event_name": "UserPromptSubmit", "transcript_path": mine, "cwd": self.repo})
        self.quiet_git_folder(self.other, 120)
        self.assertEqual(self.brief(prompt, "--pending"), (0, "", ""))           # no record of a start: nothing to compare
        self.assertIn("bowline: no other Claude Code session shows a sign of work in this repository right now.", self.brief(start)[1])
        self.assertEqual(self.brief(prompt, "--pending"), (0, "", ""))           # still alone
        self.transcript(self.other, "theirs")                                    # a session starts in the other worktree
        code, out, err = self.brief(prompt, "--pending")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("bowline: 1 other Claude Code session has started to work in this repository since you were last "
                      "told: in .claude/worktrees/other.", out)
        self.assertIn("/bowline:crew before your next edit", out)
        self.assertIn("/bowline:collaborate", out)
        self.assertIn("send that session the person's words with SendMessage, as /bowline:collaborate says", out)
        self.assertEqual(self.brief(prompt, "--pending"), (0, "", ""))           # named once
        self.transcript(self.repo, "a-second-session-in-this-folder")
        code, out, _ = self.brief(prompt, "--pending")
        self.assertIn("1 other Claude Code session has started", out)
        self.assertIn("told: in your own folder, the main checkout.", out)
        self.assertNotIn("worktrees/other", out)                                 # the one already named is not named again
        self.assertEqual(self.brief(prompt, "--pending"), (0, "", ""))
        # A session's start names who is there, so the prompt after it names nobody again.
        code, out, _ = self.brief(start)
        self.assertIn("2 other Claude Code sessions have worked", out)
        self.assertEqual(self.brief(prompt, "--pending"), (0, "", ""))
        # Seen only when it is there: with the line turned off for a session alone, a start alone says nothing.
        self.configure({"assumeOthers": False})
        os.remove(os.path.join(common.project_folder(self.repo), "a-second-session-in-this-folder.jsonl"))
        os.remove(os.path.join(common.project_folder(self.other), "theirs.jsonl"))
        self.assertEqual(self.brief(start), (0, "", ""))


class WrapTests(unittest.TestCase):
    """The crew wraps its lines at 100 columns. A path longer than a line, as the temporary folders of GitHub's
    Windows and macOS machines make one, broke in the middle with a space in 0.16.0, so the person who copied it got a
    path that does not exist."""

    def test_a_word_longer_than_a_line_stays_whole(self):
        path = "C:\\Users\\runneradmin\\AppData\\Local\\Temp\\bowline-test-mspp_xek\\the-main-checkouts-docs-site-packages" \
            "\\and-a-folder-name-long-enough-to-pass-the-width"
        self.assertGreater(len(path), crew.WIDTH)
        lines = crew.lines_of("linked: quiet for 8 hours; links: docs-site/node_modules -> " + path + ", and more")
        self.assertIn(path, [line.strip().rstrip(",") for line in lines])
        self.assertEqual(" ".join(" ".join(lines).split()),
                         "linked: quiet for 8 hours; links: docs-site/node_modules -> " + path + ", and more")


class MemoryLossTests(ScratchRepo):
    """Two sessions and one memory folder: the second saves a note over from the copy it read before the first added
    to it. The backup's commits name each session, so the doctor can say that lines were lost and where they are."""

    def setUp(self):
        super().setUp()
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        git(self.repo, "add", "CLAUDE.md")
        git(self.repo, "commit", "-q", "-m", "root")
        self.memory = common.memory_folder(self.repo)
        os.makedirs(self.memory)
        self.queue = os.path.join(self.memory, "queue.md")
        write(os.path.join(self.memory, "MEMORY.md"), "- [The notes queue](queue.md)\n")
        write(self.queue, "# The notes queue\n\n- note one\n")
        git(self.memory, "init", "-q", "-b", "main")
        git(self.memory, "config", "user.email", "t@example.invalid")
        git(self.memory, "config", "user.name", "Test")
        git(self.memory, "config", "core.autocrlf", "false")
        git(self.memory, "add", "-A")
        git(self.memory, "commit", "-q", "-m", "The memory folder, first backup")

    def reply_ends(self, session):
        """What the Stop hook does after a session's reply: the backup commits what changed and names the session."""
        payload = json.dumps({"session_id": session, "transcript_path": os.path.join(os.path.dirname(self.memory), session + ".jsonl")})
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "memory", "push", "--hook"], input=payload,
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def memory_cmd(self, *args):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "memory", *args],
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def last_commit(self):
        return subprocess.run(["git", "-C", self.memory, "log", "-1", "--format=%H%n%B"], capture_output=True, text=True).stdout

    def test_a_note_saved_over_from_an_older_copy_is_found_and_put_right(self):
        older_copy = read(self.queue)                                             # session two reads the queue
        write(self.queue, older_copy + "- note two, from session one\n- note three, from session one\n")
        self.reply_ends("session-one")
        self.assertIn("Session: session-one", self.last_commit())
        code, out, _ = self.memory_cmd("losses")
        self.assertEqual(code, 0, out)
        self.assertIn("losses: none", out)
        write(self.queue, older_copy + "- note four, from session two\n")        # and saves its older copy over it
        self.reply_ends("session-two")
        commit = self.last_commit().splitlines()[0]
        code, out, _ = self.memory_cmd("losses")
        self.assertEqual(code, 1, out)
        self.assertIn(f"queue.md: 2 line(s) that another session had added were removed by the commit {commit[:12]}", out)
        self.assertIn("  - note two, from session one", out)
        self.assertIn("  - note three, from session one", out)
        code, out, _ = self.run_script("doctor")
        self.assertIn(f"WARNING  The memory note queue.md lost 2 lines that another session had added less than 24 hours "
                      f"before, in the backup's commit {commit[:12]}.", out)
        self.assertNotIn("note two", out)                                         # the doctor never quotes a note
        self.assertIn(f"bowline memory losses --meant {commit[:12]}", out)
        write(self.queue, read(self.queue) + "- note two, from session one\n")   # one line is put back
        code, out, _ = self.memory_cmd("losses")
        self.assertIn("queue.md: 1 line(s)", out)
        self.assertNotIn("  - note two", out)
        code, out, _ = self.memory_cmd("losses", "--meant", commit[:12])         # the other removal was meant
        self.assertEqual(code, 0, out)
        self.assertIn("was meant", out)
        code, out, _ = self.memory_cmd("losses")
        self.assertEqual(code, 0, out)
        code, out, _ = self.run_script("doctor")
        self.assertNotIn("queue.md lost", out)
        code, out, err = self.memory_cmd("losses", "--meant", "0123abc")
        self.assertEqual(code, 2)
        self.assertIn("is not a commit of the memory folder", err)

    def test_a_sessions_own_removal_a_move_and_an_unnamed_commit_are_not_losses(self):
        write(self.queue, read(self.queue) + "- note two\n- note three\n")
        self.reply_ends("session-one")
        write(self.queue, "# The notes queue\n\n- note one\n- note three\n")     # the same session removes its own line
        self.reply_ends("session-one")
        write(self.queue, "# The notes queue\n\n- note one\n- note six\n")       # another session moves a line to a new note
        write(os.path.join(self.memory, "done.md"), "- note three\n")
        self.reply_ends("session-two")
        write(self.queue, "# The notes queue\n\n- note one\n")                   # a push by hand names no session
        code, out, _ = self.memory_cmd("push")
        self.assertIn("committed", out)
        self.assertNotIn("Session:", self.last_commit())
        code, out, _ = self.memory_cmd("losses")
        self.assertEqual(code, 0, out)
        self.assertIn("losses: none", out)

    def test_a_front_matter_field_given_a_new_value_is_not_a_loss(self):
        # Claude Code writes a note's front matter again on every save, with a new `modified:` under `metadata:`. On
        # 2026-11-22 the doctor reported the old value as a line lost, because another session had written it.
        note = os.path.join(self.memory, "feedback_git.md")

        def save(modified, body, extra=""):
            write(note, "---\nname: feedback_git\ndescription: How git is used\nmetadata:\n  type: feedback\n"
                        f"{extra}  modified: {modified}\n---\n\n{body}Status: open\n")

        save("2026-11-21T02:11:05.819Z", "- push fast-forward only\n", extra="  originSessionId: one\n")
        self.reply_ends("session-one")
        save("2026-11-21T07:39:54.608Z", "- push fast-forward only\n- the HTTPS fallback\n", extra="  originSessionId: one\n")
        self.reply_ends("session-two")
        code, out, _ = self.memory_cmd("losses")
        self.assertEqual(code, 0, out)
        self.assertIn("losses: none", out)
        code, out, _ = self.run_script("doctor")
        self.assertNotIn("feedback_git.md lost", out)
        # A field removed with no new value, a line of the note's body that only looks like a field, and a line of the
        # body itself are still losses when a third session takes them out.
        write(note, read(note).replace("  originSessionId: one\n", "").replace("Status: open", "Status: closed")
              .replace("- the HTTPS fallback\n", ""))
        self.reply_ends("session-three")
        code, out, _ = self.memory_cmd("losses")
        self.assertEqual(code, 1, out)
        self.assertIn("feedback_git.md: 3 line(s) that another session had added", out)
        for line in ("originSessionId: one", "Status: open", "- the HTTPS fallback"):
            self.assertIn("\n  " + line + "\n", out)


if __name__ == "__main__":
    unittest.main()
