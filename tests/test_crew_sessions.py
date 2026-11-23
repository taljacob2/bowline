"""The crew's view of the sessions and their processes, on a scratch repository with two worktrees: a worktree whose
folder lost its .git file is said and left out, a process is given the worktree of its session, its children or its
parents, wmic's escaped characters are read back, the sessions Claude Code lists are named beside their worktree, a
transcript's title stands in when claude cannot be asked, and the lines at a session's start and before a prompt name
each place on its own, with its sessions."""

import json
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

from support import NO_PROCESS, SCRIPTS, ScratchRepo, git, write

import common  # noqa: E402 - support puts the scripts on the path
import crew  # noqa: E402

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]


class SessionTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        self.configure({})
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.main, self.other = crew.worktrees(self.repo)

    def configure(self, settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"),
              json.dumps({"crew": dict({"claude": FAKE_CLAUDE}, **settings)}) + "\n")

    def agents(self, *rows):
        write(self.agents_file, json.dumps(list(rows)) + "\n")

    def crew(self, *args, cwd=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def block(self, out, name):
        """One worktree's lines in a look, from its heading to the next empty line, joined, since a long line is
        wrapped at 100 columns. A worktree goes by its folder's name."""
        return " ".join(out[out.index(f"\n  {name}"):].split("\n\n")[0].split())

    def transcript(self, folder, session, title=None, minutes_ago=0, after=0):
        """A session's transcript in Claude Code's project folder for a folder, with a title line when one is given and
        `after` bytes of other lines written after it."""
        path = os.path.join(common.project_folder(folder), session + ".jsonl")
        lines = ['{"type":"user","message":"the session\'s own work"}']
        if title:
            lines.append(json.dumps({"type": "custom-title", "customTitle": title, "sessionId": session}))
        if after:
            lines += ['{"type":"assistant","text":"' + "x" * 1000 + '"}'] * (after // 1000 + 1)
        write(path, "\n".join(lines) + "\n")
        stamp = time.time() - minutes_ago * 60
        os.utime(path, (stamp, stamp))
        return path

    def test_a_worktree_folder_without_its_git_file_is_broken_and_left_out(self):
        git(self.repo, "worktree", "add", "-q", "-b", "leaving", os.path.join(".claude", "worktrees", "leaving"))
        leaving = os.path.join(self.repo, ".claude", "worktrees", "leaving")
        write(os.path.join(self.repo, "src", "parser.py"), "mine = 1\n")
        write(os.path.join(self.other["path"], "src", "parser.py"), "theirs = 1\n")
        os.remove(os.path.join(leaving, ".git"))            # as while git removes it: the folder is there, its .git is not
        self.assertEqual({tree["short"]: tree["broken"] for tree in crew.worktrees(self.repo)},
                         {"repo": False, "other": False, "leaving": True})
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        flat = " ".join(out.split())
        self.assertIn("2 worktrees and 0 sessions: 0 wait for you, 2 at work, 0 idle, 0 quiet, 1 broken.", flat)
        self.assertIn("BROKEN OR BEING REMOVED: leaving. Its folder has no .git file of its own", flat)
        # git asked in that folder answers for the main checkout: its file is not the broken one's, and no overlap.
        self.assertIn("the main checkout and other: src/parser.py", flat)
        self.assertEqual(flat.count("leaving"), 1, out)
        kept = [tree for tree in crew.cached_survey(self.repo)["trees"] if tree["name"].endswith("leaving")][0]
        self.assertEqual((kept["broken"], kept["files"], kept["uncommitted"]), (True, [], 0))
        self.assertEqual(crew.collisions(crew.cached_survey(self.repo)["trees"]),
                         {"src/parser.py": ["the main checkout", ".claude/worktrees/other"]})

    def test_a_process_is_given_the_worktree_of_its_session_its_children_or_its_parents(self):
        main, other = self.main["path"], self.other["path"]
        snapshot = [
            # A Claude Desktop session in the other worktree: its command line names the main checkout as the project's
            # settings, which is not where it works.
            {"pid": 10, "ppid": 1, "name": "claude.exe", "command": f'claude.exe --project-config-root "{main}" --verbose'},
            {"pid": 11, "ppid": 10, "name": "bash.exe", "command": "bash -c \"eval 'cd webui && npm run build'\""},
            {"pid": 12, "ppid": 11, "name": "cmd.exe", "command": "cmd.exe /d /s /c tsc -b && vite build"},
            {"pid": 13, "ppid": 12, "name": "node.exe", "command": f"node {os.path.join(other, 'webui', 'vite.js')} build"},
            # A system process with many children, one of which names the main checkout: it belongs to none.
            {"pid": 20, "ppid": 4, "name": "services.exe", "command": "services.exe"},
            {"pid": 21, "ppid": 20, "name": "agent.exe", "command": os.path.join(main, "bin", "agent.exe")},
            {"pid": 22, "ppid": 20, "name": "svchost.exe", "command": "svchost.exe -k netsvcs"},
            {"pid": 30, "ppid": 0, "name": "lonely.exe", "command": "lonely.exe --port 4000"},
            {"pid": 40, "ppid": 40, "name": "loop.exe", "command": "its own parent"},
            # Git Bash's processes report a parent that has exited; the chain down names the worktree only at its end.
            {"pid": 50, "ppid": 9999, "name": "bash.exe", "command": "bash.exe /c/node/npx vitest run"},
            {"pid": 51, "ppid": 50, "name": "node.exe", "command": "node.exe npx-cli.js vitest run"},
            {"pid": 52, "ppid": 51, "name": "cmd.exe", "command": "cmd.exe /d /s /c vitest run"},
            {"pid": 53, "ppid": 52, "name": "node.exe", "command": f"node {os.path.join(other, 'node_modules', 'vitest.mjs')} run"},
            # A worker started from the main checkout's node_modules, which the worktree shares through a link.
            {"pid": 54, "ppid": 53, "name": "node.exe", "command": f"node {os.path.join(main, 'node_modules', 'forks.js')}"},
        ]
        trees = crew.worktrees(self.repo)
        named = {pid: (tree["name"] if tree else None) for pid, tree in crew.owners(snapshot, trees, {10: trees[1]}).items()}
        self.assertEqual(named, {10: ".claude/worktrees/other", 11: ".claude/worktrees/other", 12: ".claude/worktrees/other",
                                 13: ".claude/worktrees/other", 20: None, 21: "the main checkout", 22: None, 30: None,
                                 40: None, 50: ".claude/worktrees/other", 51: ".claude/worktrees/other",
                                 52: ".claude/worktrees/other", 53: ".claude/worktrees/other", 54: ".claude/worktrees/other"})
        # Without the list of sessions the Desktop session names no worktree itself, and is found by what it runs.
        named = {pid: (tree["name"] if tree else None) for pid, tree in crew.owners(snapshot, trees).items()}
        self.assertEqual((named[10], named[11], named[12]), (".claude/worktrees/other",) * 3)
        lonely = [p for p in snapshot if p["pid"] in (10, 30)] + [dict(snapshot[1], ppid=10), dict(snapshot[7], pid=31, ppid=10)]
        named = {pid: (tree["name"] if tree else None) for pid, tree in crew.owners(lonely, trees).items()}
        self.assertIsNone(named[10])                                             # two children that do not agree
        self.assertIsNone(crew.owner(f"claude.exe --project-config-root={main}", trees))

    def test_a_process_is_shown_by_what_it_runs(self):
        other = self.other["path"]
        shell = ('bash.exe -c "source /c/x/.claude/shell-snapshots/snapshot-bash-1.sh && eval \'cd \\"'
                 + other.replace("\\", "/") + '/webui\\" && npx vitest run\' < /dev/null && pwd -P"')
        self.assertEqual(crew.plain_command(shell, other), "a shell: cd webui && npx vitest run")
        vite = '"node" "' + os.path.join(other, "webui", "node_modules", ".bin", "..", "vite", "bin", "vite.js") + '" --port 5197'
        self.assertEqual(crew.plain_command(vite, other),
                         "node " + os.path.join("webui", "node_modules", "vite", "bin", "vite.js") + " --port 5197")

    @unittest.skipUnless(os.name == "nt", "wmic is a Windows program")
    def test_the_characters_wmic_escapes_are_read_back(self):
        table = ("\r\r\nNode,CommandLine,Name,ParentProcessId,ProcessId,WorkingSetSize\r\r\n"
                 "HOST,cmd.exe /c tsc -b &amp;&amp; vite build &gt; out.log,cmd.exe,4,5,4096000\r\r\n"
                 # A command line with line breaks in it, as a `python -c` script of several lines has.
                 'HOST,python -c "import time\ntime.sleep(60)\n",python.exe,5,6,8192\r\r\n'
                 "HOST,,System Idle Process,0,0,8192\r\r\n").encode("oem")
        answer = subprocess.CompletedProcess([], 0, stdout=table)
        with mock.patch.object(crew.shutil, "which", return_value="wmic"), \
                mock.patch.object(crew.subprocess, "run", return_value=answer), \
                mock.patch.dict(os.environ, {"COMPUTERNAME": "HOST"}):
            found = crew.processes()
        self.assertEqual(found, [{"pid": 5, "ppid": 4, "name": "cmd.exe", "command": "cmd.exe /c tsc -b && vite build > out.log",
                                  "memory": 4096000},
                                 {"pid": 6, "ppid": 5, "name": "python.exe", "command": 'python -c "import time\ntime.sleep(60)\n"',
                                  "memory": 8192},
                                 {"pid": 0, "ppid": 0, "name": "System Idle Process", "command": "System Idle Process",
                                  "memory": 8192}])

    def test_the_sessions_claude_lists_are_named_beside_their_worktree(self):
        os.makedirs(os.path.join(self.other["path"], "docs"))
        now = int(time.time() * 1000)
        self.agents(
            {"sessionId": "sess-parser", "cwd": self.other["path"], "kind": "interactive", "name": "the parser",
             "pid": NO_PROCESS, "status": "busy", "startedAt": now},
            {"sessionId": "sess-docs", "cwd": os.path.join(self.other["path"], "docs"), "kind": "interactive",
             "name": "the docs", "status": "busy", "startedAt": now},
            {"sessionId": "sess-release", "cwd": self.main["path"], "kind": "interactive", "name": "the release",
             "status": "idle", "startedAt": now},
            # A background session whose process runs is listed with its pid; without one it is offline.
            {"sessionId": "sess-nightly", "cwd": self.main["path"], "kind": "background", "name": "nightly",
             "pid": NO_PROCESS + 1, "state": "blocked"},
            {"sessionId": "sess-elsewhere", "cwd": self.root, "kind": "interactive", "name": "elsewhere", "status": "busy"})
        self.transcript(self.main["path"], "sess-release", minutes_ago=5)
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        theirs = self.block(out, "other")
        self.assertIn('session "the parser": busy', theirs)
        self.assertIn('session "the docs": busy', theirs)                      # started in a folder inside the worktree
        self.assertIn("warning: more than one session is busy in this one worktree", theirs)
        mine = self.block(out, "the main checkout")
        self.assertIn('session "the release": idle for 5 minutes', mine)
        self.assertIn('session "nightly": blocked in the background', mine)
        self.assertNotIn("warning", mine)
        self.assertNotIn("elsewhere", out)                                       # a session of another repository
        self.assertNotIn("could not be asked", out)
        kept = crew.cached_sessions(self.repo)                                   # kept for the hooks, which never ask claude
        self.assertEqual(len(kept), 5)
        self.assertEqual(crew.sessions_by_tree(crew.worktrees(self.repo), kept)[crew.same(self.other["path"])][0]["pid"], NO_PROCESS)

    def test_without_claude_a_transcripts_title_names_the_session(self):
        self.configure({"claude": "bowline-test-no-such-program"})
        self.transcript(self.other["path"], "sess-parser", title="the parser")
        self.transcript(self.other["path"], "sess-old", title="long gone", minutes_ago=90)
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        self.assertIn("Claude Code's list of sessions could not be asked (bowline-test-no-such-program agents --json)", out)
        theirs = self.block(out, "other")
        self.assertIn('session "the parser": last wrote less than a minute ago', theirs)
        self.assertNotIn("long gone", out)                                       # only a transcript written lately counts
        self.assertIn("ListAgents", out)
        self.configure({})
        os.environ["FAKE_CLAUDE_AGENTS_FAIL"] = "1"                              # a claude that fails is the same
        self.assertIn("could not be asked", self.crew()[1])

    def test_only_the_end_of_a_transcript_is_read_for_its_title(self):
        folder = self.other["path"]
        self.assertEqual(crew.session_title(self.transcript(folder, "plain")), None)
        self.assertEqual(crew.session_title(self.transcript(folder, "titled", title="  the   parser ")), "the parser")
        path = self.transcript(folder, "buried", title="the parser", after=crew.TITLE_TAIL + 5000)
        self.assertIsNone(crew.session_title(path))
        with open(path, "a", encoding="utf-8", newline="\n") as handle:          # the newest title wins
            handle.write(json.dumps({"type": "custom-title", "customTitle": "the parser, renamed"}) + "\n")
        self.assertEqual(crew.session_title(path), "the parser, renamed")
        self.assertIsNone(crew.session_title(os.path.join(self.root, "missing.jsonl")))

    def test_the_lines_at_a_start_and_before_a_prompt_name_each_place_and_its_sessions(self):
        mine = self.transcript(self.main["path"], "sess-mine", title="this session")
        self.transcript(self.main["path"], "sess-docs", title="the docs")
        self.transcript(self.other["path"], "sess-parser")                       # no title; claude named it in the last look
        self.agents({"sessionId": "sess-parser", "cwd": self.other["path"], "name": "the parser", "status": "busy"})
        self.crew()
        places = crew.others_active(self.repo, common.load_config(self.repo), transcript=mine)
        self.assertEqual(places, [{"name": ".claude/worktrees/other", "own": False, "sessions": ["the parser"]},
                                  {"name": "the main checkout", "own": True, "sessions": ["the docs"]}])
        self.assertEqual(crew.places_words(places),
                         (2, 'in .claude/worktrees/other, "the parser"; in your own folder, the main checkout, "the docs"'))
        start = json.dumps({"hook_event_name": "SessionStart", "transcript_path": mine, "cwd": self.repo})
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "doctor.py"), "--brief", "--no-memory"],
                                input=start, cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        self.assertIn('bowline: 2 other Claude Code sessions have worked in this repository in the last 30 minutes: in '
                      '.claude/worktrees/other, "the parser"; in your own folder, the main checkout, "the docs". ',
                      result.stdout)
        # Two sessions in one place are counted as two; a place where none is named counts as one.
        self.transcript(self.other["path"], "sess-tests", title="the tests")
        places = crew.others_active(self.repo, common.load_config(self.repo), transcript=mine)
        self.assertEqual(places[0]["sessions"], ["the tests", "the parser"])
        self.assertEqual(crew.places_words([{"name": "x", "own": False, "sessions": []}] + places)[0], 4)
        self.assertEqual(crew.quoted('the "fast" one'), "\"the 'fast' one\"")


if __name__ == "__main__":
    unittest.main()
