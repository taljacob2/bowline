"""A link inside a worktree that points to a folder outside it, named before anything removes the worktree. On
2026-11-22 Git for Windows' `git worktree remove` followed two directory junctions inside a worktree and deleted the
main checkout's packages they pointed to. prune guards a removal that goes through bowline; these warnings reach the
person earlier, at every session's start and in every look, because a worktree can also be removed by Claude
Desktop's own clean-up or by hand. Each link here is a directory junction on Windows and a symbolic link elsewhere,
and points to a sacrificial folder outside the repository."""

import json
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

from support import SCRIPTS, ScratchRepo, age_git_folder, assert_lines_fit, contents, git, make_link, read, write

import crew  # noqa: E402 - support puts the scripts on the path

FAKE_CLAUDE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude.py")]
ROOT = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"
PLUGIN = os.path.dirname(SCRIPTS)
KIND = "a directory junction" if os.name == "nt" else "a symbolic link"
COMMAND = re.compile(r'(cmd /c rmdir "[^"]+"|rm "[^"]+")')


def flat(text):
    return " ".join(text.split())


def take_away(command):
    """Runs the command the warning gives, as a person would type it: on Windows the line itself, which starts cmd."""
    if os.name == "nt":
        return subprocess.run(command, capture_output=True, text=True)
    return subprocess.run(command, shell=True, capture_output=True, text=True)


class LinkCase(ScratchRepo):
    def setUp(self):
        super().setUp()
        os.environ["FAKE_CLAUDE_AGENTS"] = os.path.join(self.root, "agents.json")
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"crew": {"claude": FAKE_CLAUDE}}) + "\n")
        git(self.repo, "add", "CLAUDE.md", ".claude/bowline.json")
        git(self.repo, "commit", "-q", "-m", "the root file and the crew's settings")
        write(os.path.join(self.repo, ".git", "info", "exclude"), ".claude/worktrees/\nnode_modules\n")
        self.packages = os.path.join(self.root, "the-main-checkouts-webui-packages")
        for name in ("@adobe/css-tools/index.js", "vite/bin/vite.js"):
            write(os.path.join(self.packages, name), f"the package {name}\n")
        self.before = contents(self.packages)
        self.trees = {}

    def worktree(self, name):
        git(self.repo, "worktree", "add", "-q", "-b", name, os.path.join(".claude", "worktrees", name))
        self.trees[name] = os.path.join(self.repo, ".claude", "worktrees", name)
        return self.trees[name]

    def link(self, tree, path):
        make_link(os.path.join(tree, *path.split("/")), self.packages)
        return os.path.normpath(os.path.join(tree, *path.split("/")))

    def crew(self, *args):
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "bowline.py"), "crew", *args],
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr


class SessionStartTests(LinkCase):
    """Part 1: the doctor's line at a session's start names each worktree with such a link, the link, where it points,
    why it matters and the command that takes it away alone."""

    def test_the_session_start_names_the_link_where_it_points_why_and_the_fix(self):
        linked = self.worktree("linked")
        path = self.link(linked, "webui/node_modules")
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")
        self.assertEqual((code, err), (0, ""), out)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("bowline: The worktree .claude/worktrees/linked holds a link to a folder "
                                            "outside it: "), out)
        line = lines[0]
        self.assertIn(f"webui/node_modules, {KIND} to {self.packages}.", line)
        self.assertIn("A worktree can also be removed by something that never asks bowline, such as Claude Desktop's "
                      "own clean-up of worktrees", line)
        if os.name == "nt":
            self.assertIn("Git for Windows' git worktree remove follows a directory junction and deletes the files it "
                          "points to", line)
            self.assertIn(f'take the link away alone: cmd /c rmdir "{path}", with no /s.', line)
        else:
            self.assertIn(f'take the link away alone: rm "{path}", with no -r.', line)
        self.assertIn("Never delete a folder that holds a link with a command that goes into every folder", line)
        self.assertIn("its own packages from npm ci", line)
        # The warning is not counted among the findings about the instructions and the memory.
        self.assertNotIn("bowline found", out)
        # The command it gives takes the link away and nothing else: every file it pointed to stays.
        taken = take_away(COMMAND.search(line).group(1))
        self.assertEqual(taken.returncode, 0, taken.stdout + taken.stderr)
        self.assertFalse(os.path.lexists(path))
        self.assertEqual(contents(self.packages), self.before)
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")
        self.assertNotIn("holds a link", out)

    def test_the_report_gives_the_warning_with_its_reasons(self):
        self.link(self.worktree("linked"), "webui/node_modules")
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertIn("WARNING  The worktree .claude/worktrees/linked holds a link to a folder outside it", out)
        self.assertIn("why: ", out)
        self.assertIn("fix: Before anything removes the worktree, take the link away alone", out)

    def test_only_two_levels_and_only_links_that_lead_out_of_a_worktree_are_named(self):
        # The main checkout is never removed; a link deeper than one level down is past the cheap scan; a link that
        # points inside its worktree goes with it; a link to a file is removed as a link.
        self.link(self.repo, "node_modules")
        deep = self.worktree("deep")
        self.link(deep, "a/b/node_modules")
        inside = self.worktree("inside")
        os.makedirs(os.path.join(inside, "real"))
        make_link(os.path.join(inside, "webui", "node_modules"), os.path.join(inside, "real"))
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")
        self.assertNotIn("holds a link", out)
        self.assertNotIn("holds 2 links", out)

    def test_each_worktree_is_named_with_every_link_it_holds(self):
        two = self.worktree("two")
        self.link(two, "webui/node_modules")
        self.link(two, "docs-site/node_modules")
        self.link(self.worktree("top"), "node_modules")
        code, out, err = self.run_script("doctor", "--brief", "--no-memory")
        text = flat(out)
        self.assertIn(f"The worktree .claude/worktrees/two holds 2 links to folders outside it: docs-site/node_modules, "
                      f"{KIND} to {self.packages}; webui/node_modules, {KIND} to {self.packages}.", text)
        self.assertIn("take each link away alone: ", text)
        self.assertIn("The worktree .claude/worktrees/top holds a link to a folder outside it: node_modules,", text)

    def test_a_link_made_during_a_session_is_said_after_the_next_reply(self):
        self.run_script("doctor", "--brief", "--no-memory")                     # the session starts with no link
        self.link(self.worktree("later"), "webui/node_modules")
        stdin = json.dumps({"cwd": self.repo, "hook_event_name": "Stop"})
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "doctor.py"), "--watch", "--no-memory"],
                                input=stdin, cwd=self.root, capture_output=True, text=True, encoding="utf-8",
                                env=dict(os.environ))
        said = json.loads(result.stdout)["systemMessage"]
        self.assertIn("The worktree .claude/worktrees/later holds a link to a folder outside it", said)


class LookTests(LinkCase):
    """Part 2: the look names the same links under the worktree they are in, with the same cheap scan."""

    def test_the_look_names_the_link_under_its_worktree(self):
        linked = self.worktree("linked")
        path = self.link(linked, "webui/node_modules")
        code, out, err = self.crew()
        self.assertEqual(code, 0, out + err)
        text = flat(out)
        block = text[text.index("linked: "):]
        self.assertIn(f"warning: this worktree holds a link to a folder outside it: webui/node_modules, {KIND} to "
                      f"{self.packages}. A removal of the worktree can delete what it points to; before any removal, "
                      "take the link away alone: ", block)
        self.assertIn(path, block)
        assert_lines_fit(self, out)
        code, out, err = self.crew("--json")
        item = next(item for item in json.loads(out)["worktrees"] if item["name"] == ".claude/worktrees/linked")
        self.assertEqual([(link["link"], link["kind"], link["target"]) for link in item["links"]],
                         [("webui/node_modules", KIND, self.packages)])
        main = next(item for item in json.loads(out)["worktrees"] if item["main"])
        self.assertEqual(main["links"], [])

    def test_a_quiet_worktree_folded_into_one_line_still_names_its_link(self):
        linked = self.worktree("linked")
        self.link(linked, "webui/node_modules")
        age_git_folder(self.repo, linked, 8 * 3600)
        age_git_folder(self.repo, self.repo, 8 * 3600)
        code, out, err = self.crew()
        text = flat(out)
        self.assertIn("QUIET: ", text)
        self.assertIn("warning: the quiet worktree linked holds a link to a folder outside it: webui/node_modules", text)
        assert_lines_fit(self, out)

    def test_the_scan_never_goes_into_a_folder_below_the_second_level(self):
        # A worktree's own node_modules holds tens of thousands of folders; the look lists its entries and never one
        # of theirs, because crew watch draws the look every ten seconds.
        tree = self.worktree("packages")
        for name in ("react/index.js", "vite/bin/vite.js"):
            write(os.path.join(tree, "node_modules", *name.split("/")), "x\n")
        listed = []
        real = os.scandir

        def scandir(folder):
            listed.append(os.path.relpath(folder, tree).replace("\\", "/"))
            return real(folder)

        with mock.patch.object(crew.os, "scandir", side_effect=scandir):
            crew.folder_links(tree)
        self.assertIn("node_modules", listed)
        self.assertNotIn("node_modules/react", listed)
        self.assertNotIn("node_modules/vite", listed)


class WordsTests(unittest.TestCase):
    """Parts 3 and 4: the crew skill and the rule template say never to link a worktree's folders to another
    checkout's, and the facts record what is known of Claude Desktop's clean-up and a link."""

    def test_the_skill_and_the_rule_template_say_never_to_link_a_worktree_to_another_checkout(self):
        for path in (os.path.join(PLUGIN, "skills", "crew", "SKILL.md"),
                     os.path.join(PLUGIN, "templates", "crew", "beside-other-sessions.md"),
                     os.path.join(PLUGIN, "docs", "conventions.md")):
            text = flat(read(path))
            self.assertIn("Never link a worktree's `node_modules`, or any other folder, to another checkout's", text, path)
            self.assertIn("`npm ci`", text, path)

    def test_the_facts_say_what_is_known_of_claude_desktops_clean_up_and_a_link(self):
        text = flat(read(os.path.join(PLUGIN, "docs", "facts.md")))
        self.assertIn("| Claude Desktop's removal of a worktree and a link |", text)
        self.assertIn("not tested", text)


if __name__ == "__main__":
    unittest.main()
