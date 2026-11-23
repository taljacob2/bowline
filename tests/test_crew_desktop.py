"""The crew and Claude Desktop's record of its sessions, on a scratch repository with two worktrees and a scratch
folder of records where the app keeps them: a session the app records is named by its full title and given its id
in the app, by which a reply there links it, and the look, run inside a Claude Code session, ends with those links."""

import json
import os
import subprocess
import sys
import time
import unittest

from support import NO_PROCESS, SCRIPTS, ScratchRepo, age_git_folder, assert_lines_fit, git, write

import common  # noqa: E402 - support puts the scripts on the path
import crew  # noqa: E402

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]
PARSER = "local_11111111-2222-3333-4444-555555555555"
PARKED = "local_22222222-3333-4444-5555-666666666666"
GONE = "local_33333333-4444-5555-6666-777777777777"
ARCHIVED = "local_44444444-5555-6666-7777-888888888888"


def flat(text):
    return " ".join(text.split())


class DesktopTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.agents_file = os.path.join(self.root, "agents.json")
        os.environ["FAKE_CLAUDE_AGENTS"] = self.agents_file
        self.configure({})
        git(self.repo, "add", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\n")
        git(self.repo, "worktree", "add", "-q", "-b", "other", os.path.join(".claude", "worktrees", "other"))
        self.main, self.other = (tree["path"] for tree in crew.worktrees(self.repo))
        # Where the app keeps its records on this system; support points it into the test's own folder.
        if os.name == "nt":
            base = os.environ["APPDATA"]
        elif sys.platform == "darwin":
            base = os.path.join(self.root, "Library", "Application Support")
        else:
            base = os.environ["XDG_CONFIG_HOME"]
        self.desktop = os.path.join(base, "Claude", "claude-code-sessions")
        self.assertTrue(crew.same(self.desktop).startswith(crew.same(self.root) + "/"), self.desktop)

    def configure(self, settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"),
              json.dumps({"crew": dict({"claude": FAKE_CLAUDE}, **settings)}) + "\n")

    def agents(self, *rows):
        write(self.agents_file, json.dumps(list(rows)) + "\n")

    def record(self, local_id, cli, title, folder, archived=False, account="account-1", worktree=True):
        """A session's record as Claude Desktop writes it, with some of the fields the crew never reads. worktree
        False is a session the app started in a folder of its own choosing, with no worktree made for it."""
        write(os.path.join(self.desktop, account, "organization-1", local_id + ".json"), json.dumps({
            "sessionId": local_id, "cliSessionId": cli, "cwd": folder, "worktreePath": folder if worktree else None,
            "title": title,
            "isArchived": archived, "lastActivityAt": 1795313419720, "model": "a model",
            "enabledMcpTools": {"local:a-server:a-tool": True}, "remoteMcpServersConfig": [{"url": "https://example.invalid"}],
        }) + "\n")

    def crew(self, *args, env=None):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8",
                                env=dict(os.environ, **(env or {})))
        return result.returncode, result.stdout, result.stderr

    def test_a_session_the_app_records_has_its_full_title_and_its_link(self):
        # `claude agents` gives a session's Claude Code id and its title cut at 50 characters; a reply in Claude Desktop
        # links a session by the app's own id, which only the app's record holds.
        self.agents({"sessionId": "cli-parser", "cwd": self.other, "kind": "interactive", "pid": NO_PROCESS, "status": "busy",
                     "name": "The parser keeps every comment and every blank l"},
                    {"sessionId": "cli-terminal", "cwd": self.main, "kind": "interactive", "pid": NO_PROCESS + 1, "status": "idle",
                     "name": "a session in a terminal"})
        self.record(PARSER, "cli-parser", "The parser keeps every comment and every blank line it reads", self.other)
        write(os.path.join(self.desktop, "account-1", "organization-1", "local_broken.json"), "not a record\n")
        code, out, err = self.crew(env={"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        self.assertIn('session "The parser keeps every comment and every blank line it reads": busy', text)
        links = text[text.index("SESSION LINKS"):]
        self.assertIn("SESSION LINKS: in a reply in Claude Desktop, link a session as [its title](#<its id>)", links)
        self.assertIn(f'#{PARSER} "The parser keeps every comment and every blank line it reads"', links)
        self.assertNotIn("a session in a terminal", links)                       # the app has no record of it
        self.assertNotIn("enabledMcpTools", out)
        assert_lines_fit(self, out)
        # A person's own terminal, and crew watch, go without the links; --json always has them.
        self.assertNotIn("SESSION LINKS", self.crew()[1])
        model = json.loads(self.crew("--json")[1])
        by = {item["display"]: item for item in model["worktrees"]}
        self.assertEqual(by["other"]["sessions"][0]["desktop"], PARSER)
        self.assertIsNone(by["the main checkout"]["sessions"][0]["desktop"])
        # crew.desktop false reads no record.
        self.configure({"desktop": False})
        model = json.loads(self.crew("--json")[1])
        session = next(item for item in model["worktrees"] if item["display"] == "other")["sessions"][0]
        self.assertEqual((session["name"], session["desktop"]), ("The parser keeps every comment and every blank l", None))

    def origin(self):
        bare = os.path.join(self.root, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        git(self.repo, "remote", "add", "origin", bare)
        git(self.repo, "push", "-q", "-u", "origin", "main")

    def age(self, tree, hours):
        """Makes a worktree's own git folder look last written some hours ago, as one nobody works in is."""
        age_git_folder(self.repo, tree, hours * 3600)

    def test_a_session_offline_in_the_sidebar_keeps_its_worktree_until_it_is_archived(self):
        # On 2026-11-22 prune called four worktrees safe to remove whose sessions were still in the person's sidebar,
        # offline: `claude agents` lists a session of the app only while its process runs, and the look put those
        # worktrees under QUIET, with no session.
        self.origin()
        self.age(self.repo, 8)
        self.age(self.other, 8)
        self.agents()
        title = "#128: refuse a vault left as the template's placeholder"
        self.record(PARKED, "cli-parked", title, self.other)
        self.record(GONE, "cli-gone", "#129: the status-tick tests", os.path.join(self.repo, ".claude", "worktrees", "removed"))
        # A deleted folder of the main checkout, where a session was started with no worktree, is not a worktree gone.
        self.record("local_55555555-6666-7777-8888-999999999999", "cli-scratch", "a scratch folder",
                    os.path.join(self.repo, "scratch"), worktree=False)
        code, out, err = self.crew(env={"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        self.assertIn("2 worktrees and 0 sessions (1 more listed, offline)", text)
        self.assertIn(f"other: \"{title}\" (offline in Claude Desktop's sidebar: archive it before this worktree is "
                      "removed)", text)
        self.assertIn("In Claude Desktop's sidebar, not archived, 1 session whose worktree is gone or being removed: "
                      "\"#129: the status-tick tests\" (.claude/worktrees/removed). Reopened, it finds its folder "
                      "missing; archive it in the sidebar.", text)
        self.assertNotIn("a scratch folder", text)
        links = text[text.index("SESSION LINKS"):]
        self.assertIn(f'#{PARKED} "{title}"', links)
        self.assertIn(f'#{GONE} "#129: the status-tick tests"', links)
        model = json.loads(self.crew("--json")[1])
        by = {item["display"]: item for item in model["worktrees"]}
        self.assertEqual(by["other"]["group"], "idle")
        self.assertEqual([(s["status"], s["kind"], s["desktop"]) for s in by["other"]["sessions"]],
                         [("offline", "desktop", PARKED)])
        self.assertEqual(by["the main checkout"]["sessions"], [])                # a gone worktree's session is not its
        # Where the worktree's lines are written out, as when it holds work, the session's line says the same at length.
        self.assertEqual(crew.session_state(by["other"]["sessions"][0], time.time()),
                         "offline: it is in Claude Desktop's sidebar, not archived, and no process of it runs. Archive "
                         "it before this worktree is removed: reopened after, it would find its folder gone")
        # prune keeps the worktree, names the session and says what to do; --remove refuses it.
        code, out, err = self.crew("prune")
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        self.assertIn("Safe to remove: none.", text)
        self.assertIn(f"other: its session \"{title}\" is offline in Claude Desktop's sidebar, not archived: reopened "
                      "after a removal, it would find its folder gone, so archive it first", text)
        code, out, err = self.crew("prune", "--remove", "other")
        self.assertEqual(code, 1, out + err)
        self.assertIn("other is not removed: its session", flat(out))
        self.assertTrue(os.path.isdir(self.other))
        # Once the person archives it, the worktree is safe.
        self.record(PARKED, "cli-parked", title, self.other, archived=True)
        text = flat(self.crew("prune")[1])
        self.assertIn("Safe to remove: 1 worktree.", text)
        self.assertIn("other: quiet for 8 hours", text)

    def test_a_head_detached_at_its_own_commit_is_no_work_and_the_archived_session_is_named(self):
        # On 2026-11-22 the app archived the session "Bowline crew" and detached the HEAD of its worktree at the
        # commit it was on. The look put the worktree under AT WORK, "a sign of work less than a minute ago (its git
        # folder), and no session listed here", and prune called it not safe for the same reason.
        self.origin()
        done = os.path.join(self.repo, ".claude", "worktrees", "done")
        old = int(time.time()) - 8 * 3600
        os.environ["GIT_COMMITTER_DATE"] = f"{old} +0000"     # the log of its HEAD says it last moved 8 hours ago
        try:
            git(self.repo, "worktree", "add", "-q", "-b", "done", done)
            write(os.path.join(done, "src", "fix.py"), "fixed = 1\n")
            git(done, "add", "src/fix.py")
            git(done, "commit", "-q", "-m", "a fix")
        finally:
            del os.environ["GIT_COMMITTER_DATE"]
        git(done, "push", "-q", "origin", "done:main")
        git(self.repo, "fetch", "-q", "origin")
        self.age(done, 8)
        # What the app does when it archives the session: it detaches the HEAD at its own commit, and it writes to the
        # session's transcript.
        git(done, "checkout", "-q", "--detach")
        write(os.path.join(common.project_folder(done), "cli-archived.jsonl"), '{"type":"system"}\n')
        self.agents()
        self.record(ARCHIVED, "cli-archived", "Bowline crew", done, archived=True)
        model = json.loads(self.crew("--json")[1])
        tree = next(item for item in model["worktrees"] if item["display"] == "done")
        self.assertAlmostEqual(tree["lastSign"]["at"], old, delta=60)
        self.assertEqual((tree["group"], tree["sessions"], tree["archived"]),
                         ("quiet", [], [{"name": "Bowline crew", "desktop": ARCHIVED, "cli": ["cli-archived"]}]))
        code, out, err = self.crew("--verbose", env={"CLAUDECODE": "1"})
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        self.assertNotIn("done (branch no branch): a sign of work", text)
        self.assertIn('done (branch no branch): quiet holds: nothing that is not on origin/main last sign of work: 8 '
                      'hours ago, its git folder its session "Bowline crew" is archived in Claude Desktop, so no session '
                      'is open here', text)
        self.assertIn(f'#{ARCHIVED} "Bowline crew"', text[text.index("SESSION LINKS"):])
        text = flat(self.crew("prune")[1])
        self.assertIn('Safe to remove: 1 worktree.', text)
        self.assertIn('done: quiet for 8 hours; its session "Bowline crew" is archived', text)
        # A commit is work, detached or not.
        git(done, "commit", "-q", "--allow-empty", "-m", "more")
        text = flat(self.crew("prune")[1])
        self.assertIn("done: 1 commit not on origin/main; a sign of work less than a minute ago (its git folder)", text)

    def test_a_session_whose_worktree_is_being_removed_is_named_too(self):
        leaving = os.path.join(self.repo, ".claude", "worktrees", "leaving")
        git(self.repo, "worktree", "add", "-q", "-b", "leaving", leaving)
        os.remove(os.path.join(leaving, ".git"))            # as while git removes it: the folder is there, its .git is not
        self.agents()
        self.record(PARKED, "cli-parked", "the leaving session", leaving)
        text = flat(self.crew()[1])
        self.assertIn("BROKEN OR BEING REMOVED: leaving.", text)
        self.assertIn("1 session whose worktree is gone or being removed: \"the leaving session\" "
                      "(.claude/worktrees/leaving).", text)


if __name__ == "__main__":
    unittest.main()
