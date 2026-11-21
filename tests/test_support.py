"""What the tests share, tested: a test's scratch folder is really removed when the test ends, with git's read-only
object files on Windows and also when the test's own setUp fails, and a test whose folder stays fails and says so."""

import os
import stat
import tempfile
import unittest
from unittest import mock

import support
from support import ScratchRepo, remove_tree, write


def files_under(folder):
    return [os.path.join(where, name) for where, _, names in os.walk(folder) for name in names]


class Probe(ScratchRepo):
    """A test case that the tests below run by hand, to look at its folder afterwards. No method's name starts with
    "test", so the discovery of the suite finds nothing to run in it."""

    def looks_at_its_objects(self):
        self.objects = files_under(os.path.join(self.repo, ".git", "objects"))
        self.read_only = [path for path in self.objects if not os.access(path, os.W_OK)]
        self.home_inside = os.environ["HOME"]


class ProbeWithABrokenSetUp(Probe):
    def setUp(self):
        super().setUp()
        raise RuntimeError("this setUp fails after the scratch folder was made")


def run_by_hand(case):
    result = unittest.TestResult()
    case.run(result)
    return result


class RemoveTreeTests(unittest.TestCase):
    def test_a_folder_with_a_read_only_file_and_a_read_only_folder_is_removed(self):
        root = tempfile.mkdtemp(prefix="bowline-test-")
        self.addCleanup(remove_tree, root)
        locked = os.path.join(root, "objects", "ab", "cdef")
        write(locked, "an object\n")
        os.chmod(locked, stat.S_IREAD)
        if os.name == "nt":
            # Elsewhere a folder that cannot be written keeps its files whoever asks, so only Windows gets one.
            os.chmod(os.path.dirname(locked), stat.S_IREAD)
        self.assertEqual(remove_tree(root), [])
        self.assertFalse(os.path.lexists(root))

    def test_a_folder_that_is_already_gone_is_no_refusal(self):
        root = tempfile.mkdtemp(prefix="bowline-test-")
        os.rmdir(root)
        self.assertEqual(remove_tree(root, seconds=0), [])

    def test_a_folder_that_stays_is_reported(self):
        root = tempfile.mkdtemp(prefix="bowline-test-")
        self.addCleanup(remove_tree, root)
        with mock.patch.object(support.shutil, "rmtree", lambda *args, **kwargs: None):
            left = remove_tree(root, seconds=0)
        self.assertEqual(len(left), 1)
        self.assertIn(root, left[0])
        self.assertTrue(os.path.isdir(root))

    def test_a_refused_file_is_named_with_the_reason(self):
        root = tempfile.mkdtemp(prefix="bowline-test-")
        self.addCleanup(remove_tree, root)
        kept = os.path.join(root, "kept.txt")
        write(kept, "kept\n")

        def refuse(path, *args, **kwargs):
            raise PermissionError(13, "Access is denied", path)

        with mock.patch.object(support.os, "unlink", refuse), mock.patch.object(support.os, "remove", refuse):
            left = remove_tree(root, seconds=0)
        self.assertTrue(left)
        self.assertTrue(any("kept.txt" in line and "Access is denied" in line for line in left), left)
        self.assertTrue(os.path.isfile(kept))


class ScratchFolderTests(unittest.TestCase):
    def test_a_scratch_repository_is_removed_when_the_test_ends(self):
        environment = dict(os.environ)
        case = Probe("looks_at_its_objects")
        result = run_by_hand(case)
        self.addCleanup(remove_tree, case.root)
        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
        self.assertTrue(case.objects, "the scratch repository has a commit, so it has object files")
        if os.name == "nt":
            # The reason this test exists: without a read-only file in the folder, it would not show what it claims.
            self.assertTrue(case.read_only, "on Windows git writes its object files read-only")
        self.assertFalse(os.path.lexists(case.root), f"{case.root} is still there after the test")
        self.assertEqual(case.home_inside, case.root)
        self.assertEqual(dict(os.environ), environment, "the environment is the one from before the test")

    def test_a_scratch_repository_is_removed_when_a_tests_own_set_up_fails(self):
        # unittest runs no tearDown after a setUp that failed, only the cleanups.
        environment = dict(os.environ)
        case = ProbeWithABrokenSetUp("looks_at_its_objects")
        result = run_by_hand(case)
        self.addCleanup(remove_tree, case.root)
        self.assertEqual(len(result.errors), 1, result.errors + result.failures)
        self.assertIn("this setUp fails", result.errors[0][1])
        self.assertFalse(os.path.lexists(case.root), f"{case.root} is still there after the test")
        self.assertEqual(dict(os.environ), environment, "the environment is the one from before the test")

    def test_a_scratch_folder_that_stays_fails_the_test(self):
        case = Probe("looks_at_its_objects")
        with mock.patch.object(support, "remove_tree", lambda path: [path + ": refused for the test"]):
            result = run_by_hand(case)
        self.addCleanup(remove_tree, case.root)
        self.assertTrue(os.path.isdir(case.root))
        said = "".join(text for _, text in result.failures + result.errors)
        self.assertEqual(len(result.failures) + len(result.errors), 1, said)
        self.assertIn(case.root, said)
        self.assertIn("refused for the test", said)


if __name__ == "__main__":
    unittest.main()
