"""What the doctor and a session's start say about decisions, on a scratch repository: the warning for an entry of the
records that approves by reference, told once when such a line is written during a session; the note and the sentence
for a repository whose instructions have no section about looking a decision up; and the command that prints the
section for a rule file that was written before the starter rule had it."""

import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from support import SCRIPTS, ScratchRepo, git, read, write

import common
import decisions

ROOT = "# Root\n\n## Compact Instructions\n\nKeep.\n\n## Memory between sessions\n\nShort.\n"

ROADMAP = """# Roadmap

1. **The job page.** Three answers still wait: where the retry button goes, the word of a failed job,
   and the order of the exports.
   **Decided (2026-03-02): all three as recommended** (the owner: "yes, go ahead").
"""

# A record that speaks about such phrases and approves nothing by one: a quotation that opens at the end of a line and
# closes on the next, a phrase in backquotes, and a sentence that says the decision itself.
DESIGN = """# Design

## Decisions

- **What counts as a label.** An entry such as "all seven as
  recommended", "both as proposed" or `each of the four, as suggested` holds a label and no decision.
- **The import page (2026-01-15).** A failed import reads "Import failed", as recommended in the review.
"""

# A rule about recording decisions as the starter rule was before it had the section, in a repository's own words.
OLD_RULE = """# Where a decision is written down

- **A settled design question goes in the design document.** Add the entry in the same round.
- **A line in `docs/` about what the app does today is a claim, not a fact.** Before building on one,
  check it against the code, and correct it with a dated note when it is wrong.
- **Read a written decision back.** Compare the text with what was said.
"""

SENTENCE = "bowline: before you put a design question to the person, recommend an answer or settle one yourself,"
TEMPLATE = os.path.join(os.path.dirname(SCRIPTS), "templates", "rules", "recording-decisions.md")


class DecisionsDoctorTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        write(os.path.join(self.repo, "docs", "ROADMAP.md"), ROADMAP)
        write(os.path.join(self.repo, "docs", "DESIGN.md"), DESIGN)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "the records")

    def hook(self, mode, event):
        """Runs the doctor the way a hook does: in the repository, with the event's JSON on standard input."""
        stdin = json.dumps({"cwd": self.repo, "hook_event_name": event})
        result = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "doctor.py"), mode, "--no-memory"], input=stdin,
                                cwd=self.repo, capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
        return result.returncode, result.stdout, result.stderr

    def configure(self, **settings):
        write(os.path.join(self.repo, ".claude", "bowline.json"), json.dumps({"decisions": settings}) + "\n")

    def test_the_doctor_warns_of_an_entry_that_approves_by_reference_and_not_of_a_quotation(self):
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertEqual(code, 0, out + err)
        self.assertIn("WARNING  1 entry of the records of decisions approves by reference and does not say what was decided: "
                      'docs/ROADMAP.md:5 says "all three as recommended".', out)
        self.assertIn("why: An entry that says only that a recommendation was approved keeps the approval and loses the decision", out)
        self.assertIn("fix: Write into each such entry what was decided, in a sentence that stands alone", out)
        self.assertIn("/bowline:decide is the procedure.", out)
        # The design document quotes three such phrases and approves nothing by one of them.
        self.assertNotIn("docs/DESIGN.md", out)
        self.assertIn("0 problem(s), 1 warning(s)", out)

        # More than three are counted, and the first three are named.
        write(os.path.join(self.repo, "docs", "decisions", "0001.md"),
              "# The export page\n\nApproved: both as proposed.\n\nApproved: all four as suggested.\n\nAgreed, each of the five as recommended.\n")
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertIn("4 entries of the records of decisions approve by reference and do not say what was decided: "
                      'docs/ROADMAP.md:5 says "all three as recommended"; docs/decisions/0001.md:3 says "both as proposed"; '
                      'docs/decisions/0001.md:5 says "all four as suggested"; and 1 more.', out)

        # A repository that names its records is measured on those alone, and one may turn the check off.
        self.configure(records=["docs/DESIGN.md"])
        self.assertNotIn("by reference", self.run_script("doctor", "--no-memory")[1])
        self.configure(byReference="")
        self.assertNotIn("by reference", self.run_script("doctor", "--no-memory")[1])
        # The lookup marks no quotation either: the design document's entry about labels is listed without a mark.
        os.remove(os.path.join(self.repo, ".claude", "bowline.json"))
        code, out, err = self.run_script("decisions", "find", "holds", "label", "--no-memory")
        self.assertIn("docs/DESIGN.md:6  recommended", out)
        self.assertNotIn("it names a recommendation without saying it", out)

    def test_a_label_written_during_a_session_is_told_once_and_one_that_was_there_is_not_told_again(self):
        code, out, err = self.hook("--brief", "SessionStart")
        self.assertEqual(code, 0, out + err)
        self.assertIn("bowline found 1 thing(s) worth a look", out)
        self.assertIn('docs/ROADMAP.md:5 says "all three as recommended". Fix: Write into each such entry', out)
        # Nothing new after a reply: the label was said at the start.
        self.assertEqual(self.hook("--watch", "Stop"), (0, "", ""))

        # A reply writes a second label into another record: the person is told once, and Claude before the next prompt.
        write(os.path.join(self.repo, "docs", "decisions", "0001.md"), "# The export page\n\nApproved: both as proposed.\n")
        code, out, err = self.hook("--watch", "Stop")
        message = json.loads(out)["systemMessage"]
        self.assertIn("2 entries of the records of decisions approve by reference", message)
        self.assertIn('docs/decisions/0001.md:3 says "both as proposed"', message)
        self.assertEqual(self.hook("--watch", "Stop"), (0, "", ""))
        code, out, err = self.hook("--pending", "UserPromptSubmit")
        self.assertIn("bowline found this during the session", out)
        self.assertIn('docs/decisions/0001.md:3 says "both as proposed"', out)
        self.assertEqual(self.hook("--pending", "UserPromptSubmit")[1], "")

        # The first label moves down two lines and the second is written out in full: nothing is new, so nothing is said.
        write(os.path.join(self.repo, "docs", "ROADMAP.md"), ROADMAP.replace("# Roadmap\n", "# Roadmap\n\nThe order work runs in.\n"))
        write(os.path.join(self.repo, "docs", "decisions", "0001.md"), "# The export page\n\nDecided: the page lists exports by name.\n")
        self.assertEqual(self.hook("--watch", "Stop"), (0, "", ""))

    def test_a_repository_without_the_section_gets_a_note_and_a_sentence_at_a_sessions_start(self):
        code, out, err = self.run_script("doctor", "--no-memory")
        self.assertIn("NOTE  The repository's instructions have no section about looking a decision up before a question goes to "
                      "the person.", out)
        self.assertIn("fix: /bowline:conventions adds the section to the rule about recording decisions", out)
        code, out, err = self.hook("--brief", "SessionStart")
        line = [line for line in out.split("\n") if line.startswith(SENTENCE)]
        self.assertEqual(len(line), 1, out)
        self.assertIn("edit neither and run the skill /bowline:decide first.", line[0])
        self.assertIn("This repository's instructions have no rule about looking a decision up, so this holds until they "
                      "have one.", line[0])
        self.assertTrue(line[0].endswith("/bowline:conventions adds the rule's two bullets to the repository; offer that to the person."))
        # The sentence comes after the findings and before the line about other sessions, which is the last and long.
        lines = out.strip().split("\n")
        self.assertEqual(lines[-2], line[0])
        self.assertTrue(lines[-1].startswith("bowline: no other Claude Code session shows a sign of work"), lines[-1])

        # The starter rule has the section: no note, and no sentence.
        write(os.path.join(self.repo, ".claude", "rules", "recording-decisions.md"), read(TEMPLATE))
        self.assertNotIn("looking a decision up", self.run_script("doctor", "--no-memory")[1])
        self.assertNotIn(SENTENCE, self.hook("--brief", "SessionStart")[1])

        # A repository's own words count when they name the skill, in a rule or in the root CLAUDE.md.
        os.remove(os.path.join(self.repo, ".claude", "rules", "recording-decisions.md"))
        self.assertIn(SENTENCE, self.hook("--brief", "SessionStart")[1])
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT + "\nBefore a design question goes to the owner, follow /bowline:decide.\n")
        self.assertNotIn(SENTENCE, self.hook("--brief", "SessionStart")[1])
        self.assertNotIn("looking a decision up", self.run_script("doctor", "--no-memory")[1])

        # The repository may turn the sentence off; the note in the report stays.
        write(os.path.join(self.repo, "CLAUDE.md"), ROOT)
        self.configure(atStart=False)
        self.assertNotIn(SENTENCE, self.hook("--brief", "SessionStart")[1])
        self.assertIn("NOTE  The repository's instructions have no section about looking a decision up", self.run_script("doctor", "--no-memory")[1])

    def test_a_repository_bowline_leaves_untouched_gets_the_sentence_without_the_offer(self):
        config = common.load_config(self.repo)
        with mock.patch.object(common, "writes_allowed", return_value=False):
            line = decisions.start_line(self.repo, config)
        self.assertTrue(line.startswith(SENTENCE), line)
        self.assertTrue(line.endswith("so this holds until they have one."), line)

    def test_the_section_command_says_where_it_goes_what_it_costs_and_what_it_replaces(self):
        section = decisions.template_section()
        self.assertTrue(section.startswith("## Before a question goes to the person\n\n- **Look the subject up first.**"), section)
        self.assertTrue(read(TEMPLATE).replace("\r\n", "\n").endswith(section))
        self.assertIn("- **When a record and the program disagree, find which one is the mistake before you edit either.**", section)

        # No rule file: init writes the starter rule.
        code, out, err = self.run_script("decisions", "section")
        self.assertEqual(code, 0, out + err)
        self.assertIn("this repository's instructions have no section about looking a decision up", out)
        self.assertIn(".claude/rules/recording-decisions.md does not exist. `bowline init` writes the starter rule there", out)
        self.assertTrue(out.replace("\r\n", "\n").endswith(section), out)

        # A rule file from before: the section goes at its end, and the bullet it replaces is named with its line.
        rule = os.path.join(self.repo, ".claude", "rules", "recording-decisions.md")
        write(rule, OLD_RULE)
        code, out, err = self.run_script("decisions", "section")
        self.assertIn("It goes at the end of .claude/rules/recording-decisions.md, which exists. Edit that file; never write a second one.", out)
        size, old = len(section), len(OLD_RULE.split("- **A line in")[1].split("- **Read")[0]) + len("- **A line in")
        self.assertIn(f"The section is {size} characters. The rules every session loads stand at {len(OLD_RULE)} of 10,000, and at "
                      f"{len(OLD_RULE) + size + 1:,} with it.", out)
        self.assertIn("Line 4 of .claude/rules/recording-decisions.md opens the bullet that the section replaces", out)
        self.assertIn(f"Taking it out frees {old} characters, and the rules then stand at {len(OLD_RULE) + size + 1 - old:,}.", out)
        self.assertEqual(read(rule), OLD_RULE, "the command changes no file")

        # Rules that would go over the limit say so.
        write(os.path.join(self.repo, ".claude", "rules", "long.md"), "# A long rule\n\n" + "words " * 1650 + "\n")
        code, out, err = self.run_script("decisions", "section")
        self.assertIn("with it, which is over the limit.", out)

        # With the section in place there is nothing to add.
        write(rule, OLD_RULE + "\n" + section)
        code, out, err = self.run_script("decisions", "section")
        self.assertIn("already have a section about looking a decision up", out)
        self.assertNotIn("## Before a question", out)


if __name__ == "__main__":
    unittest.main()
