"""What the tests share: a scratch git repository, a scratch Claude Code configuration folder, and the path to the
scripts. Every test writes only under the system's temp folder and removes it afterwards."""

import json
import os
import shutil
import stat
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


def age_git_folder(repo, tree, seconds):
    """Makes a worktree's own git folder look last written some seconds ago, as one nobody has worked in since: its
    index, its HEAD and the log of its HEAD are given that time, and so is every entry of the log, which bowline reads
    when the newest entry moved no commit (`git worktree add` ends the log with such an entry, "reset: moving to
    HEAD"). tree is the main checkout's path or a worktree's."""
    folder = os.path.join(repo, ".git") if os.path.normcase(tree) == os.path.normcase(repo) else \
        os.path.join(repo, ".git", "worktrees", os.path.basename(tree))
    stamp = time.time() - seconds
    log = os.path.join(folder, "logs", "HEAD")
    if os.path.exists(log):
        with open(log, encoding="utf-8", newline="") as handle:
            lines = handle.read().split("\n")
        # An entry is "<old> <new> <who> <seconds> <zone>\t<message>"; the seconds are the second word from the end of
        # the part before the tab.
        for index, line in enumerate(lines):
            head, tab, message = line.partition("\t")
            words = head.split(" ")
            if len(words) >= 4 and words[-2].isdigit():
                words[-2] = str(int(stamp))
                lines[index] = " ".join(words) + tab + message
        with open(log, "w", encoding="utf-8", newline="") as handle:
            handle.write("\n".join(lines))
    for name in ("index", "HEAD", os.path.join("logs", "HEAD")):
        if os.path.exists(os.path.join(folder, name)):
            os.utime(os.path.join(folder, name), (stamp, stamp))


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


def remove_tree(path, seconds=10):
    """Removes a folder with everything in it, and returns what refused: an empty list when the folder is gone.

    On Windows git writes its object files read-only, and Windows does not remove a read-only file, so a plain
    shutil.rmtree() stops at the first object of a scratch repository; with ignore_errors it stops in silence, and
    every test left its folder in the temp folder. Here a file or a folder that is refused is made writable and removed
    again. What still refuses after that is most often a file that a process the test started has not closed yet, which
    is a matter of moments, so the removal is tried again for a few seconds before it is reported."""
    refused = []

    def make_writable_and_retry(function, target, problem):
        # Python 3.12 and later pass the exception itself (onexc); earlier ones pass the three values of
        # sys.exc_info() (onerror). Only a refused removal is tried again: a folder that could not be listed is not
        # something a second try would change.
        if isinstance(problem, tuple):
            problem = problem[1]
        try:
            if function not in (os.unlink, os.remove, os.rmdir) or not isinstance(problem, PermissionError):
                raise problem
            os.chmod(target, stat.S_IWRITE)
            function(target)
        except OSError as still:
            refused.append(f"{target}: {still}")

    # onerror is deprecated since Python 3.12, which has onexc in its place; Python 3.8 to 3.11 know only onerror.
    handler = {"onexc" if sys.version_info >= (3, 12) else "onerror": make_writable_and_retry}
    deadline = time.time() + seconds
    while True:
        del refused[:]
        shutil.rmtree(path, **handler)
        if not os.path.lexists(path):
            return []
        if time.time() >= deadline:
            return list(refused) or [f"{path}: it is still there, and nothing said why"]
        time.sleep(0.2)


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


def make_link(link, target):
    """A link to a folder, as a worktree's node_modules often is: a directory junction on Windows, which needs no
    administrator, and a symbolic link elsewhere."""
    link, target = os.path.normpath(link), os.path.normpath(target)        # mklink takes no forward slash
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", link, target], check=True, capture_output=True)
    else:
        os.symlink(target, link, target_is_directory=True)


def contents(folder):
    """Every file under a folder, by its path from the folder, with what it holds."""
    found = {}
    for top, _, files in os.walk(folder):
        for name in files:
            with open(os.path.join(top, name), encoding="utf-8") as handle:
                found[os.path.relpath(os.path.join(top, name), folder)] = handle.read()
    return found


def assert_lines_fit(test, text, width=100):
    """Checks that every line of a printout fits in width columns. The one line allowed to be longer holds a single
    word, such as a long path, which the crew keeps whole so that a person who copies it gets the path itself."""
    for line in text.splitlines():
        if len(line) > width:
            test.assertEqual(len(line.split()), 1, "a line over %d columns holds more than one word: %s" % (width, line))


class ScratchRepo(unittest.TestCase):
    """A test case with a fresh git repository (one committed file) and a fresh CLAUDE_CONFIG_DIR."""

    def setUp(self):
        # The real path, because git reports real paths: on macOS the temp folder is behind a symlink (/var is
        # /private/var) and on Windows it may be a short name (RUNNER~1), and the scripts name the memory folder from
        # what git says.
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="bowline-test-"))
        # A cleanup, registered before anything else can fail, and not a tearDown: unittest skips tearDown when setUp
        # fails, here or in a test's own setUp, and the folder would stay in the temp folder.
        self.addCleanup(self.remove_scratch_folder)
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
        self.addCleanup(self.restore_environment)
        os.environ["CLAUDE_CONFIG_DIR"] = self.config_dir
        os.environ.pop("HOME", None)
        os.environ["HOME"] = self.root
        os.environ["USERPROFILE"] = self.root
        # Claude Desktop's records of its sessions are found under these on Windows and Linux (under HOME on macOS),
        # so a test never reads the sessions of the machine it runs on.
        os.environ["APPDATA"] = os.path.join(self.root, "AppData", "Roaming")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.root, ".config")
        # A test run from inside a Claude Code session inherits its CLAUDECODE; each test starts without it, as in CI.
        os.environ.pop("CLAUDECODE", None)

    def restore_environment(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    def remove_scratch_folder(self):
        """Runs when the test has ended, however it ended, and fails the test when its folder cannot be removed: a
        folder that stays in silence is how thousands of them once piled up in a temp folder."""
        left = remove_tree(self.root)
        if left:
            self.fail(f"the test's scratch folder {self.root} could not be removed, so it stays in the temp folder. "
                      "What refused: " + "; ".join(left[:5]))

    def run_script(self, module, *args):
        """Runs a script as a separate process, the way a hook or a person would, and returns (exit code, stdout, stderr)."""
        result = subprocess.run(
            [sys.executable, "-I", os.path.join(SCRIPTS, module + ".py"), *args],
            cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ),
        )
        return result.returncode, result.stdout, result.stderr
