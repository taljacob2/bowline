"""The move on a scratch repository: the plan, a run from a spec (pages verbatim and normalized, a rule with a dropped
bullet and front matter, the index), a missing section refused, and the pointers that must match once."""

import json
import os
import unittest

from support import ScratchRepo, read, write

EM = chr(0x2014)
ARROW = chr(0x2192)


class MoveTests(ScratchRepo):
    def setUp(self):
        super().setUp()
        self.claude = os.path.join(self.repo, "sub", "CLAUDE.md")
        write(self.claude, "\n".join([
            "# Sub " + EM + " conventions",
            "",
            "Intro line.",
            "",
            "## Architecture",
            "",
            "- **Core holds the logic.** The hosts are glue " + ARROW + " wiring only.",
            "",
            "## API documentation",
            "",
            "Regenerate swagger.yaml every round.",
            "",
            "## Words a person reads",
            "",
            "- **Agent, never machine.** Because the product says so.",
            "  A second line of that bullet.",
            "- **A CSV for a spreadsheet.** UTF-8 with a BOM.",
            "- **Mermaid starts with an init block.** So labels are not clipped.",
            "",
            "## Workflow",
            "",
            "Build, test, smoke test.",
        ]) + "\n")
        write(os.path.join(self.repo, "README.md"), "See sub/CLAUDE.md's Architecture section for why.\n")
        write(os.path.join(self.repo, "new-index.md"), "# Sub: where its rules are\n\nAn index.\n")

    def test_plan_lists_sections_with_ranges(self):
        code, out, err = self.run_script("move", "plan", "--file", self.claude)
        self.assertEqual(code, 0, out + err)
        for title in ("Architecture", "API documentation", "Words a person reads", "Workflow"):
            self.assertIn(title, out)
        self.assertIn("5-8", out)          # Architecture's line range
        self.assertIn("never read", out) if len(read(self.claude)) > 40000 else self.assertNotIn("never read", out)

    def test_run_moves_verbatim_normalized_and_writes_the_index(self):
        spec = {
            "pages": [{"target": "docs/conventions/sub-architecture.md", "title": "# Sub's architecture, the long form",
                       "sections": ["Architecture", "API documentation"]}],
            "rules": [{"target": ".claude/rules/sub/words.md", "paths": ["sub/**"], "sections": ["Words a person reads"],
                       "drop": ["- **A CSV for a spreadsheet.**"]}],
            "index": os.path.join(self.repo, "new-index.md"),
        }
        spec_path = os.path.join(self.root, "spec.json")
        write(spec_path, json.dumps(spec))
        code, out, err = self.run_script("move", "run", "--file", self.claude, "--spec", spec_path, "--check")
        self.assertEqual(code, 0, out + err)
        self.assertIn("check only", out)
        self.assertIn("sections not named by the spec", out)
        self.assertIn("Workflow", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "docs", "conventions", "sub-architecture.md")))

        code, out, err = self.run_script("move", "run", "--file", self.claude, "--spec", spec_path)
        self.assertEqual(code, 0, out + err)
        page = read(os.path.join(self.repo, "docs", "conventions", "sub-architecture.md"))
        self.assertTrue(page.startswith("# Sub's architecture, the long form\n\n<!-- Moved verbatim from sub/CLAUDE.md"))
        self.assertIn("## Architecture\n\n- **Core holds the logic.** The hosts are glue -> wiring only.", page)
        self.assertIn("## API documentation\n\nRegenerate swagger.yaml every round.", page)
        self.assertNotIn(ARROW, page)
        rule = read(os.path.join(self.repo, ".claude", "rules", "sub", "words.md"))
        self.assertTrue(rule.startswith('---\npaths:\n  - "sub/**"\n---\n\n# Words a person reads\n'))
        self.assertIn("A second line of that bullet.", rule)
        self.assertNotIn("A CSV for a spreadsheet", rule)
        self.assertIn("Mermaid starts with an init block", rule)
        self.assertIn("The long form of these rules", rule)
        self.assertEqual(read(self.claude), "# Sub: where its rules are\n\nAn index.\n")
        self.assertIn("U+2192", out)

    def test_missing_section_is_refused_and_nothing_written(self):
        spec_path = os.path.join(self.root, "spec.json")
        write(spec_path, json.dumps({"pages": [{"target": "docs/x.md", "sections": ["Nonsense"]}]}))
        code, out, err = self.run_script("move", "run", "--file", self.claude, "--spec", spec_path)
        self.assertEqual(code, 1)
        self.assertIn("matches 0 heading(s)", err)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "docs", "x.md")))

    def test_pointers_find_and_replace_once(self):
        code, out, err = self.run_script("move", "find-pointers", "--name", "sub/CLAUDE.md")
        self.assertEqual(code, 0, out + err)
        self.assertIn("README.md:1:", out)
        spec_path = os.path.join(self.root, "pointers.json")
        write(spec_path, json.dumps([{"file": "README.md", "old": "sub/CLAUDE.md's Architecture section", "new": "docs/conventions/sub-architecture.md"}]))
        code, out, err = self.run_script("move", "pointers", "--spec", spec_path, "--check")
        self.assertEqual(code, 0, out + err)
        self.assertIn("check only", out)
        self.assertIn("sub/CLAUDE.md", read(os.path.join(self.repo, "README.md")))
        code, out, err = self.run_script("move", "pointers", "--spec", spec_path)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(read(os.path.join(self.repo, "README.md")), "See docs/conventions/sub-architecture.md for why.\n")
        write(spec_path, json.dumps([{"file": "README.md", "old": "for", "new": "x"}, {"file": "README.md", "old": "nothing here", "new": "y"}]))
        code, out, err = self.run_script("move", "pointers", "--spec", spec_path)
        self.assertEqual(code, 1)
        self.assertIn("occurs 0 time(s)", err)
        self.assertEqual(read(os.path.join(self.repo, "README.md")), "See docs/conventions/sub-architecture.md for why.\n")

    def test_place_copies_drafts_into_instruction_files_only(self):
        write(os.path.join(self.repo, ".bowline-scratch", "words", "rule.md"),
              '---\npaths:\n  - "sub/**"\n---\n\n# Words\n\n- **Agent, never machine.** Because ' + ARROW + ' the product says so.\n')
        write(os.path.join(self.repo, ".bowline-scratch", "index.md"), "# Sub, the index\n\nWhere things are.\n")
        write(os.path.join(self.repo, ".bowline-scratch", "loose.md"), "# No front matter\n")
        spec_path = os.path.join(self.root, "place.json")
        write(spec_path, json.dumps([{"source": ".bowline-scratch/words/rule.md", "target": "src/words.md"}]))
        code, out, err = self.run_script("move", "place", "--spec", spec_path)
        self.assertEqual(code, 1)
        self.assertIn("is not an instruction file", err)
        write(spec_path, json.dumps([
            {"source": ".bowline-scratch/words/rule.md", "target": "./.claude/rules/sub/words.md"},
            {"source": ".bowline-scratch/index.md", "target": "sub/CLAUDE.md"},
            {"source": ".bowline-scratch/loose.md", "target": ".claude/rules/loose.md"},
        ]))
        code, out, err = self.run_script("move", "place", "--spec", spec_path, "--check")
        self.assertEqual(code, 0, out + err)
        self.assertIn("check only", out)
        self.assertIn("would load in every session", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".claude", "rules", "sub", "words.md")))
        self.assertNotEqual(read(self.claude), "# Sub, the index\n\nWhere things are.\n")
        code, out, err = self.run_script("move", "place", "--spec", spec_path)
        self.assertEqual(code, 0, out + err)
        rule = read(os.path.join(self.repo, ".claude", "rules", "sub", "words.md"))
        self.assertTrue(rule.startswith('---\npaths:\n  - "sub/**"\n---\n'))
        self.assertIn("Because -> the product says so.", rule)
        self.assertEqual(read(self.claude), "# Sub, the index\n\nWhere things are.\n")
        self.assertIn("U+2192", out)
        write(spec_path, json.dumps([{"source": ".bowline-scratch/missing.md", "target": ".claude/rules/x.md"}]))
        code, out, err = self.run_script("move", "place", "--spec", spec_path)
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err)


if __name__ == "__main__":
    unittest.main()
