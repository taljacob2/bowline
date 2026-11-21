"""The turn for a heavy check, by memory, on a scratch repository with two worktrees: every process comes with its
memory; a small check runs beside a full one, one small check at a time; crew.slots lets more than one full check run;
a check beside another waits until its peak is free; each run records the most memory its command took; and the look
shows each session's memory, the machine's, and the turns."""

import json
import os
import signal
import subprocess
import sys
import time
import unittest

from support import SCRIPTS, ScratchRepo, git, write

import crew  # noqa: E402 - support puts the scripts on the path

HEAVY = "bowline-test-heavy-" + str(os.getpid())
FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]
SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]


def flat(text):
    return " ".join(text.split())


class TurnTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        self.configure({})
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.other = [tree["path"] for tree in crew.worktrees(self.repo) if not tree["main"]][0]
        self.state = os.path.join(self.repo, ".git", "bowline", "crew")
        self.started = []

    def tearDown(self):
        for started in self.started:
            try:
                if isinstance(started, int):
                    os.kill(started, signal.SIGTERM)                       # a process a started one started
                else:
                    started.kill()
                    started.wait()
            except OSError:
                pass
        super().tearDown()

    def configure(self, settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"),
              json.dumps({"crew": dict({"claude": FAKE_CLAUDE, "heavy": [HEAVY]}, **settings)}) + "\n")

    def crew(self, *args, cwd=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def start(self, command):
        process = subprocess.Popen(command)
        self.started.append(process)
        return process

    def hold(self, slot, pid, command="the suite"):
        """A turn held by a running process: slot 1 is turn.json, "small" the small check's."""
        name = "turn.json" if slot == 1 else f"turn-{slot}.json"
        write(os.path.join(self.state, name), json.dumps({"pid": pid, "worktree": self.other, "command": command,
                                                          "since": "2026-11-21 10:00"}) + "\n")

    def suite_with_a_heavy_child(self):
        """A process that holds a turn and has started a heavy process below it, as `crew run` of a suite does."""
        marker = os.path.join(self.root, "child.pid")
        parent = self.start([sys.executable, "-c",
                             "import subprocess, sys, time\n"
                             f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', {HEAVY!r}])\n"
                             f"open({marker!r}, 'w').write(str(child.pid))\n"
                             "time.sleep(60)\n"])
        child = ""
        for _ in range(100):
            if os.path.exists(marker):
                with open(marker, encoding="ascii") as handle:
                    child = handle.read().strip()
                if child:
                    break
            time.sleep(0.1)
        self.started.insert(0, int(child))
        time.sleep(0.5)
        return parent

    def test_every_process_comes_with_its_memory(self):
        found = {p["pid"]: p for p in crew.processes()}
        if not found:
            self.skipTest("this system would not list its processes")
        self.assertGreater(found[os.getpid()]["memory"] or 0, 1024 * 1024)
        memory = crew.machine_memory()
        if memory is not None:
            self.assertGreater(memory["total"], 0)
            self.assertLessEqual(memory["available"], memory["total"])
        self.assertEqual(crew.size(3 * 1024 ** 3 // 2), "1.5 GB")
        self.assertEqual(crew.size(300 * 1024 ** 2), "300 MB")

    def test_the_memory_of_a_process_and_those_below_it_counts_each_once(self):
        snapshot = [{"pid": 1, "ppid": 0, "memory": 100}, {"pid": 2, "ppid": 1, "memory": 20},
                    {"pid": 3, "ppid": 2, "memory": 3}, {"pid": 4, "ppid": 0, "memory": 4000},
                    {"pid": 5, "ppid": 5, "memory": None}]
        self.assertEqual(crew.below([1], snapshot), {1, 2, 3})
        self.assertEqual(crew.memory_of(crew.below([1, 2], snapshot), snapshot), 123)
        self.assertIsNone(crew.memory_of({5}, snapshot))

    def test_a_small_check_runs_beside_a_full_one_and_waits_for_another_small_one(self):
        suite = self.suite_with_a_heavy_child()
        self.hold(1, suite.pid)
        code, out, err = self.crew("run", "--timeout", "0.03", "--every", "0.5", "--", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 3, out + err)
        self.assertIn("the turn, held since 2026-11-21 10:00 by .claude/worktrees/other for: the suite", err)
        # The suite's own heavy process runs under its turn, so it is not a second check outside the turn.
        code, out, err = self.crew("run", "--small", "--timeout", "0.5", "--every", "0.5", "--",
                                   sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 0, out + err)
        self.assertIn("ran", out)
        self.assertIn("the small check is this worktree's, beside 1 other check", flat(err))
        self.assertFalse(os.path.exists(os.path.join(self.state, "turn-small.json")))
        self.hold("small", self.start(SLEEPER).pid, "one test file")
        code, out, err = self.crew("run", "--small", "--timeout", "0.03", "--every", "0.5", "--",
                                   sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 3, out + err)
        self.assertIn("the small check's turn, held since 2026-11-21 10:00 by .claude/worktrees/other for: one test file",
                      flat(err))
        code, out, _ = self.crew()
        text = flat(out)
        self.assertIn("The turn for a heavy check is held since 2026-11-21 10:00 by other, for: the suite", text)
        self.assertIn("The turn for a small check is held since 2026-11-21 10:00 by other, for: one test file", text)
        self.assertIn("holds the turn for a small check since", text)
        self.assertIn("crew.slots lets 1 full check run at a time, and a small one (crew run --small) beside them.", text)

    def test_slots_let_two_full_checks_run_and_a_heavy_process_outside_the_turn_takes_one(self):
        self.configure({"slots": 2})
        self.hold(1, self.start(SLEEPER).pid)          # a holder of its own: what the test starts is not below it
        code, out, err = self.crew("run", "--timeout", "0.5", "--every", "0.5", "--", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 0, out + err)
        self.assertIn("a turn is this worktree's, beside 1 other check", flat(err))
        self.assertFalse(os.path.exists(os.path.join(self.state, "turn-2.json")))
        self.assertTrue(os.path.exists(os.path.join(self.state, "turn.json")))     # the other one's is left alone
        self.start(SLEEPER + [HEAVY])
        time.sleep(1)
        code, out, err = self.crew("run", "--timeout", "0.03", "--every", "0.5", "--", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 3, out + err)
        self.assertIn("crew.slots lets 2 full checks run at once", flat(err))

    def test_a_check_beside_another_waits_until_its_peak_is_free(self):
        if crew.machine_memory() is None:
            self.skipTest("this system does not say how much memory is free")
        self.configure({"slots": 2})
        command = [sys.executable, "-c", "print('ran')"]
        write(os.path.join(self.state, "peaks.json"),
              json.dumps({"peaks": [{"command": crew.shown(" ".join(command)), "recent": [10 ** 15], "runs": 1}]}) + "\n")
        self.hold(1, self.start(SLEEPER).pid)
        code, out, err = self.crew("run", "--timeout", "0.03", "--every", "0.5", "--", *command)
        self.assertEqual(code, 3, out + err)
        self.assertIn("too little memory beside them: this command took at most about", flat(err))
        os.remove(os.path.join(self.state, "turn.json"))
        code, out, err = self.crew("run", "--timeout", "0.5", "--every", "0.5", "--", *command)
        self.assertEqual(code, 0, out + err)                                    # alone on the machine, it starts
        self.assertIn("the machine is quiet", err)

    def test_a_run_records_the_most_memory_its_command_took(self):
        if not crew.processes():
            self.skipTest("this system would not list its processes")
        command = [sys.executable, "-c", "import time; held = b'x' * (60 * 1024 * 1024); time.sleep(3)"]
        code, out, err = self.crew("run", "--sample", "0.3", "--", *command)
        self.assertEqual(code, 0, out + err)
        self.assertIn("held at most about", err)
        with open(os.path.join(self.state, "peaks.json"), encoding="utf-8") as handle:
            peaks = json.load(handle)["peaks"]
        self.assertEqual(peaks[0]["command"], crew.shown(" ".join(command)))
        self.assertEqual(peaks[0]["runs"], 1)
        self.assertGreater(peaks[0]["recent"][0], 40 * 1024 * 1024)
        code, out, _ = self.crew()
        self.assertIn("The most memory the checks run through the turn took:", flat(out))
        code, out, _ = self.crew("--json")
        self.assertGreater(json.loads(out)["peaks"][0]["peak"], 40 * 1024 * 1024)

    def test_the_look_shows_each_sessions_memory_and_the_machines(self):
        session = self.start(SLEEPER)
        time.sleep(0.5)
        write(self.agents_file, json.dumps([{"sessionId": "s1", "cwd": self.other, "kind": "interactive",
                                             "name": "the parser", "pid": session.pid, "status": "busy"}]) + "\n")
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        if not crew.processes():
            self.skipTest("this system would not list its processes")
        self.assertRegex(flat(out), r'session "the parser": busy, \d+(\.\d)? [MG]B of memory')
        if crew.machine_memory() is not None:
            self.assertRegex(flat(out), r"Memory: \S+ [MG]B of \S+ [MG]B in use; the sessions listed")
        code, out, _ = self.crew("--json")
        model = json.loads(out)
        sessions = [s for item in model["worktrees"] for s in item["sessions"]]
        self.assertGreater(sessions[0]["memory"], 0)
        self.assertEqual(model["slots"], 1)


if __name__ == "__main__":
    unittest.main()
