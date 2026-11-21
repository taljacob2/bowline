"""What the tests share: a scratch git repository, a scratch Claude Code configuration folder, and the path to the
scripts. Every test writes only under the system's temp folder and removes it afterwards."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def wait_for_split(test, state_file, seconds=120):
    """Waits until autosplit's background worker has recorded how the split ended, and returns that record. The worker
    needs about a second with the stand-in for claude, so a wait of two minutes that runs out is a worker that stalled
    or died, never a slow machine. The test then fails with the record as it stands and the end of the worker's log,
    which is the only place where a worker that died says why."""
    deadline = time.time() + seconds
    state = None
    while time.time() < deadline:
        try:
            state = load_json(state_file)
            if state.get("state") in ("ready", "failed"):
                return state
        except (OSError, ValueError):
            pass
        time.sleep(0.2)
    log = os.path.splitext(state_file)[0] + ".log"
    try:
        with open(log, encoding="utf-8", errors="replace") as handle:
            said = handle.read()[-3000:]
    except OSError as problem:
        said = f"(the log could not be read: {problem})"
    test.fail(f"the worker recorded no end of the split within {seconds} seconds.\nIts record as it stands: "
              f"{json.dumps(state, indent=1)}\nThe end of its log, {log}:\n{said}")


def assert_starts_hidden(test, kwargs):
    """Checks the arguments a process was started with in the background: it must open no window. On Windows that means
    a console of its own that is never shown, which every program it starts shares. It never means DETACHED_PROCESS,
    which leaves the process no console at all, so that every git it starts opens a window of its own. Elsewhere it
    means a session of its own."""
    if os.name == "nt":
        flags = kwargs.get("creationflags", 0)
        test.assertTrue(flags & subprocess.CREATE_NO_WINDOW, "a console of its own that is never shown")
        test.assertFalse(flags & subprocess.DETACHED_PROCESS, "never no console at all")
        test.assertTrue(flags & subprocess.CREATE_NEW_PROCESS_GROUP, "a process group of its own")
    else:
        test.assertTrue(kwargs.get("start_new_session"), "a session of its own")


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
