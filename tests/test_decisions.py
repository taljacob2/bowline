"""The lookup of a decision, on a made-up repository that replays how one was once missed: a job runner whose status
reads "Running" after an export failed, while its manual and the name of a test say "Failed", a comment cites a
decision by its date, and the record of that date says only "all three as recommended"."""

import contextlib
import io
import json
import os
import subprocess
import unittest

from support import ScratchRepo, assert_lines_fit, git, write

import common
import decisions

DESIGN = """# Design

## Decisions, and questions still open

- **Open: what a job reads after one export fails (2026-02-20).** A job has several exports. When one
  export failed and a retry can still finish it, the word the job reads is not settled.
"""

ROADMAP = """# Roadmap

## Next, in this order

1. **The job page.** Three answers still wait: where the retry button goes; Failed as the word of a
   job whose export failed; and the order of the exports on the page.
   **Decided (2026-03-02): all three as recommended** (the owner: "yes, go ahead").
2. **The import page.** Nothing is open here.
"""

MANUAL = """# Manual

## Jobs

A job whose export failed reads Failed until someone retries it.
"""

STATUS = """def status_of(job):
    # A failed export keeps the job Running until a retry: the owner's decision of 2026-03-02.
    if job.failed_exports and job.can_retry:
        return "Running"
    return "Failed" if job.failed_exports else "Done"
"""

TEST = """def test_a_failed_export_reads_failed_until_a_retry():
    assert status_of(job_with_a_failed_export()) == "Running"
"""


def said(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class DecisionsTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        for path, text in (("docs/DESIGN.md", DESIGN), ("docs/ROADMAP.md", ROADMAP), ("docs/MANUAL.md", MANUAL),
                           ("jobs/status.py", STATUS), ("tests/test_jobs.py", TEST)):
            write(os.path.join(self.repo, *path.split("/")), text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "A failed export keeps the job waiting for a retry")
        self.commit = said("rev-parse", "HEAD", cwd=self.repo)[:7]
        self.day = said("log", "-1", "--format=%ad", "--date=format:%Y-%m-%d", cwd=self.repo)

    def find(self, *args):
        code, out, err = self.run_script("decisions", "find", *args)
        self.assertEqual(code, 0, out + err)
        return out

    def part(self, out, title):
        """The lines of one part of the list, from its title to the blank line that ends it."""
        lines = out.split("\n")
        start = next(index for index, line in enumerate(lines) if line.startswith(title))
        end = next(index for index in range(start, len(lines)) if not lines[index].strip())
        return "\n".join(lines[start:end])

    def test_find_lists_every_part_with_what_git_knows(self):
        out = self.find("export", "failed")
        self.assertIn('bowline decisions: "export" with "failed"', out)
        self.assertIn("within 3 lines of each other", out)
        records = self.part(out, "RECORDS OF DECISIONS")
        self.assertIn("RECORDS OF DECISIONS  docs/DESIGN.md, docs/ROADMAP.md", records)
        self.assertIn("docs/DESIGN.md:6  export failed and a retry can still finish it", records)
        self.assertIn("in the entry at line 5: - **Open: what a job reads after one export fails (2026-02-20).**", records)
        # The line that holds the words is the place, and the line above it, which opens the entry, is named under it.
        self.assertIn("docs/ROADMAP.md:6  job whose export failed; and the order of the exports on the page.", records)
        self.assertIn("in the entry at line 5: 1. **The job page.** Three answers still wait", records)
        self.assertIn('line 7 says "all three as recommended": it names a recommendation without saying it', records)
        documents = self.part(out, "OTHER DOCUMENTS")
        self.assertIn("docs/MANUAL.md:5  A job whose export failed reads Failed until someone retries it.", documents)
        self.assertIn("in the entry at line 3: ## Jobs", documents)
        tests = self.part(out, "TESTS")
        self.assertIn("tests/test_jobs.py:1  def test_a_failed_export_reads_failed_until_a_retry():", tests)
        self.assertIn(f"last written in {self.commit}, ", tests)
        code = self.part(out, "CODE")
        self.assertIn("jobs/status.py:2  # A failed export keeps the job Running until a retry", code)
        self.assertIn("it cites 2026-03-02; a record holds that date at docs/ROADMAP.md:7", code)
        self.assertIn(f"last written in {self.commit}, ", code)
        messages = self.part(out, "COMMIT MESSAGES")
        self.assertIn(f"{self.commit}  {self.day}  A failed export keeps the job waiting for a retry", messages)
        self.assertIn("NOT SEARCHED  a page outside this repository that a record points to", out)
        self.assertTrue(out.rstrip().endswith("Read each line in its file before you rely on it."))
        assert_lines_fit(self, out)

    def test_a_comment_that_cites_a_date_no_record_holds_is_told(self):
        write(os.path.join(self.repo, "jobs", "order.py"),
              "# The exports run oldest first, and a failed one last: agreed on 2025-01-01.\nORDER = 'oldest'\n")
        out = self.find("export", "failed")
        self.assertIn("it cites 2025-01-01, and no record of decisions holds that date", self.part(out, "CODE"))
        self.assertIn("not committed yet", self.part(out, "CODE"))

    def test_words_on_neighbouring_lines_are_a_place_and_words_far_apart_are_not(self):
        self.assertEqual(decisions.places(["an export", "", "that failed"], ["export", "failed"], 3), [0])
        self.assertEqual(decisions.places(["an export", "", "", "that failed"], ["export", "failed"], 3), [])
        self.assertEqual(decisions.places(["Export FAILED", "the export failed again"], ["export", "failed"], 1), [0, 1])
        # A line that holds every word is a place of its own, so the entry under another entry is not swallowed by it.
        self.assertEqual(decisions.places(["export failed"] * 3, ["export", "failed"], 3), [0, 1, 2])
        # A sentence wrapped over two lines is one place, though its second line starts a stretch with the third.
        self.assertEqual(decisions.places(["an export", "that failed", "an export again"], ["export", "failed"], 3), [0])
        # The line above a sentence is never listed in the sentence's stead.
        self.assertEqual(decisions.places(["when every export arrives", "the export failed here"], ["export", "failed"], 3), [1])
        write(os.path.join(self.repo, "docs", "NOTES.md"), "The export\nis slow.\n\n\n\n\nIt never failed.\n")
        self.assertNotIn("docs/NOTES.md", self.find("export", "failed"))

    def test_one_word_and_a_word_nobody_wrote(self):
        out = self.find("retries")
        self.assertIn("A place is listed where the word appears, in any case.", out)
        self.assertIn("docs/MANUAL.md:5", out)
        out = self.find("zebra")
        for title in ("RECORDS OF DECISIONS", "OTHER DOCUMENTS", "TESTS", "CODE", "COMMIT MESSAGES"):
            self.assertTrue(self.part(out, title).rstrip().endswith("nothing"), title)

    def test_the_places_that_say_decided_come_first_and_the_rest_are_counted(self):
        write(os.path.join(self.repo, "CHANGELOG.md"),
              "# Changelog\n\n- A failed export is shown in red.\n\n- An export that failed twice is named.\n\n"
              "- Decided: a failed export never hides the others.\n")
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"decisions": {"shown": 1}}))
        records = self.part(self.find("export", "failed"), "RECORDS OF DECISIONS")
        self.assertIn("CHANGELOG.md:7  - Decided: a failed export never hides the others.", records)
        self.assertNotIn("CHANGELOG.md:3", records)
        self.assertIn("and 4 more (--verbose lists every one; the places that say decided, agreed or approved", records)
        records = self.part(self.find("export", "failed", "--verbose"), "RECORDS OF DECISIONS")
        self.assertIn("CHANGELOG.md:3  - A failed export is shown in red.", records)
        self.assertNotIn("more (", records)

    def test_a_repository_names_its_records_and_a_rule_is_never_one(self):
        write(os.path.join(self.repo, ".claude", "rules", "recording-decisions.md"), "# A rule\n\nA failed export.\n")
        write(os.path.join(self.repo, "docs", "adr", "0001-status.md"), "# The status\n\nA failed export.\n")
        code, out, err = self.run_script("decisions", "records")
        self.assertEqual(code, 0, out + err)
        self.assertIn("3 files are taken as records of decisions, found by their names", out)
        self.assertEqual([line.strip() for line in out.split("\n")[1:] if line.strip()],
                         ["docs/DESIGN.md", "docs/ROADMAP.md", "docs/adr/0001-status.md"])

        write(os.path.join(self.repo, "notes", "choices.md"), "# Choices\n\nAn export that failed is retried once.\n")
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"decisions": {"records": ["notes/*.md"]}}))
        code, out, err = self.run_script("decisions", "records")
        self.assertIn("1 file is taken as records of decisions, named in .claude/bowline.json (decisions.records)", out)
        out = self.find("export", "failed")
        self.assertIn("notes/choices.md:3", self.part(out, "RECORDS OF DECISIONS"))
        self.assertIn("docs/ROADMAP.md:6", self.part(out, "OTHER DOCUMENTS"))

    def test_no_record_at_all_says_where_to_name_one(self):
        git(self.repo, "rm", "-q", "docs/DESIGN.md", "docs/ROADMAP.md")
        out = self.find("export", "failed")
        self.assertIn("RECORDS OF DECISIONS  none found. Name them in .claude/bowline.json (decisions.records).", out)
        self.assertIn("docs/MANUAL.md:5", self.part(out, "OTHER DOCUMENTS"))

    def test_a_file_not_added_yet_is_searched_and_an_ignored_one_is_not(self):
        write(os.path.join(self.repo, ".gitignore"), "build/\n")
        write(os.path.join(self.repo, "build", "out.py"), "# the export failed here\n")
        write(os.path.join(self.repo, "jobs", "new.py"), "# the export failed there\n")
        out = self.find("export", "failed")
        self.assertIn("jobs/new.py:1", out)
        self.assertNotIn("build/out.py", out)

    def test_the_memory_gives_the_names_of_its_notes_and_never_their_words(self):
        folder = common.memory_folder(common.main_checkout(self.repo))
        write(os.path.join(folder, "project_jobs.md"), "I recommended keeping Running when an export failed. A secret.\n")
        write(os.path.join(folder, "MEMORY.md"), "- [jobs](project_jobs.md): export failed\n")
        out = self.find("export", "failed")
        self.assertIn("Notes that hold the words: project_jobs.md.", out)
        self.assertNotIn("secret", out)
        self.assertNotIn("MEMORY.md", out)
        self.assertNotIn("project_jobs.md", self.find("export", "failed", "--no-memory"))

    def test_a_search_that_runs_out_of_time_still_reads_the_records(self):
        real = decisions.holding_every_word
        decisions.holding_every_word = lambda *args: None
        self.addCleanup(setattr, decisions, "holding_every_word", real)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = decisions.main(["find", "export", "failed", "--repo", self.repo, "--seconds", "5", "--no-memory"])
        self.assertEqual(code, 0)
        out = out.getvalue()
        self.assertIn("docs/ROADMAP.md:6", self.part(out, "RECORDS OF DECISIONS"))
        for title in ("OTHER DOCUMENTS", "TESTS", "CODE"):
            self.assertIn("not searched: git did not answer within 5 seconds", self.part(out, title))
        self.assertNotIn("docs/MANUAL.md", out)
        assert_lines_fit(self, out)

    def test_outside_a_repository_it_says_so(self):
        code, out, err = self.run_script("decisions", "find", "export", "--repo", self.root)
        self.assertEqual(code, 2)
        self.assertIn("this is a folder of repositories. Name the one the subject belongs to: --repo repo", err)
        empty = os.path.join(self.root, "empty")
        os.makedirs(empty)
        code, out, err = self.run_script("decisions", "records", "--repo", empty)
        self.assertEqual(code, 2)
        self.assertIn("not inside a git repository", err)

    def test_the_entry_point_knows_the_command(self):
        code, out, err = self.run_script("bowline", "decisions", "records")
        self.assertEqual(code, 0, out + err)
        self.assertIn("taken as records of decisions", out)
        code, out, err = self.run_script("bowline")
        self.assertIn("decisions find <word>...", out)

    def test_which_part_a_file_belongs_to(self):
        records = ["docs/ROADMAP.md"]
        self.assertEqual(decisions.part_of("docs/ROADMAP.md", records), "records")
        self.assertEqual(decisions.part_of("docs/MANUAL.md", records), "documents")
        self.assertEqual(decisions.part_of("tests/test_jobs.py", records), "tests")
        self.assertEqual(decisions.part_of("src/Jobs.Tests/StatusTests.cs", records), "tests")
        self.assertEqual(decisions.part_of("web/status.spec.ts", records), "tests")
        self.assertEqual(decisions.part_of("jobs/latest.py", records), "code")

    def test_the_default_shape_of_an_approval_by_reference(self):
        shape = decisions.re.compile(common.load_config(None)["decisions"]["byReference"], decisions.re.IGNORECASE)
        for line in ("Decided: all seven as recommended.", "Both as proposed (the owner: yes).",
                     "each of the four, as suggested", "all of them as recommended", "all as recommended",
                     "all seven answers as recommended", "All 3 open questions, as proposed"):
            self.assertTrue(shape.search(line), line)
        # A sentence that says the decision and adds that it was the recommendation holds the decision.
        for line in ("Transport: one connection for each page, as recommended.", "The defaults as proposed: 10 % or 5 GB.",
                     "All of it is written here. The word stays Failed, as recommended.",
                     "All sessions use one connection, as recommended."):
            self.assertFalse(shape.search(line), line)


if __name__ == "__main__":
    unittest.main()
