"""What the tests share: a scratch git repository, a scratch Claude Code configuration folder, and the path to the
scripts. Every test writes only under the system's temp folder and removes it afterwards."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugin", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def load_json(path):
    import json
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class ScratchRepo(unittest.TestCase):
    """A test case with a fresh git repository (one committed file) and a fresh CLAUDE_CONFIG_DIR."""

    def setUp(self):
        # The real path, because git reports real paths: on macOS the temp folder is behind a symlink (/var is
        # /private/var) and on Windows it may be a short name (RUNNER~1), and the scripts name the memory folder from
        # what git says.
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="bowline-test-"))
        self.repo = os.path.join(self.root, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "core.autocrlf", "false")
        write(os.path.join(self.repo, "README.md"), "# A scratch repository\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "init")
        self.config_dir = os.path.join(self.root, "claude-config")
        os.makedirs(self.config_dir)
        self._old_env = dict(os.environ)
        os.environ["CLAUDE_CONFIG_DIR"] = self.config_dir
        os.environ.pop("HOME", None)
        os.environ["HOME"] = self.root
        os.environ["USERPROFILE"] = self.root

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)
        shutil.rmtree(self.root, ignore_errors=True)

    def run_script(self, module, *args):
        """Runs a script as a separate process, the way a hook or a person would, and returns (exit code, stdout, stderr)."""
        result = subprocess.run(
            [sys.executable, "-I", os.path.join(SCRIPTS, module + ".py"), *args],
            cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ),
        )
        return result.returncode, result.stdout, result.stderr
