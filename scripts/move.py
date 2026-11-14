"""Moves an oversized instruction file into pages, rules and an index without losing a line, and updates the pointers.

    python -I scripts/bowline.py move plan --file <CLAUDE.md>
    python -I scripts/bowline.py move run --file <CLAUDE.md> --spec <spec.json> [--check]
    python -I scripts/bowline.py move find-pointers --name <file or section words> [--repo <path>]
    python -I scripts/bowline.py move pointers --spec <pointers.json> [--check]
    python -I scripts/bowline.py move place --spec <place.json> [--check]

`plan` lists the file's "## " sections with their line ranges and sizes, and where Claude Code's two cutoffs fall, so a
person and Claude can decide which sections become long-form pages, which become scoped rules, and which become
skills. `run` carries a decision written as a spec out, verbatim: each named section goes whole into its page or its
rule; the only change on the way is that characters outside ASCII which a commit gate would refuse are normalized to
their spellings (counted and printed; an unknown one stops the run unless --allow-unknown), and the index text given in
the spec replaces the file. Nothing is deleted: the long form is the pages. `find-pointers` lists every line in the
repository that names the file or a section, so the pointers can be updated; `pointers` applies replacements that must
each match exactly once, or nothing is written. `place` copies finished drafts, written in a scratch folder, into
instruction files only (a rule, a skill, a page under the conventions folder, or a CLAUDE.md), normalized the same way:
the condensed rules of a split are drafted in scratch and placed with it, because a session that runs unattended
cannot write under .claude/ itself. --check on `run`, `pointers` and `place` prints and changes nothing.

A spec:
{
  "pages": [ {"target": "docs/conventions/architecture.md", "title": "# The architecture, the long form",
              "sections": ["Architecture", "API documentation"]} ],
  "rules": [ {"target": ".claude/rules/platform/words.md", "paths": ["platform/**"], "sections": ["Words a person reads"],
              "drop": ["- **A bullet that stays in the page only"]} ],
  "index": "docs/new-index.md"
}
A pointers spec: [ {"file": "README.md", "old": "see CLAUDE.md's Architecture", "new": "see docs/conventions/architecture.md"} ]
A place spec: [ {"source": ".bowline-scratch/words/rule.md", "target": ".claude/rules/platform/words.md"} ]
"""

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ASCII = {
    "\u2014": " - ", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201C": '"', "\u201D": '"', "\u2026": "...",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->", "\u00D7": "x", "\u2265": ">=", "\u2264": "<=", "\u2260": "!=",
    "\u00A0": " ", "\u2022": "-", "\u2713": "yes", "\u2714": "yes", "\u2717": "no", "\u2718": "no", "\u00B1": "+/-",
    "\u00E9": "e", "\u2032": "'", "\u2033": '"', "\u00AB": '"', "\u00BB": '"', "\u2011": "-", "\u00B0": " degrees",
    "\u2248": "about ", "\u03BC": "u", "\u00BD": "1/2", "\u2212": "-", "\u2039": "<", "\u0394": "delta ", "\u2191": "up",
    "\u2193": "down", "\u00F7": "/", "\u00E8": "e", "\u00E0": "a", "\u00FC": "u", "\u00F6": "o", "\u00E4": "a",
}

PREAMBLE = (
    "<!-- Moved verbatim from {source} on {date} by bowline, with characters outside ASCII normalized to the repository's\n"
    "spelling. This is the long form: every entry's history and reasoning, as it was written. The short form that\n"
    "Claude Code loads is under {rules_dir}/; its rules point here by title. -->\n\n"
)


def split_sections(text):
    """The file as (preamble, [(title, body)]) where each body includes its '## ' heading line."""
    lines = text.split("\n")
    preamble, sections, current, buffer = [], [], None, []
    for line in lines:
        if line.startswith("## "):
            if current is None:
                preamble = buffer
            else:
                sections.append((current, buffer))
            current, buffer = line[3:].strip(), [line]
        else:
            buffer.append(line)
    if current is None:
        preamble = buffer
    else:
        sections.append((current, buffer))
    return preamble, sections


def find_section(sections, wanted):
    """The one section whose title starts with the wanted words; an error when none or several match."""
    hits = [(t, b) for t, b in sections if t.lower().startswith(wanted.lower())]
    if len(hits) != 1:
        raise SystemExit(f"bowline move: the section '{wanted}' matches {len(hits)} heading(s); name it so it matches one.")
    return hits[0]


def normalize(text, accepted, allow_unknown):
    counts = collections.Counter()
    unknown = set()
    out = []
    for ch in text:
        code = ord(ch)
        if code > 127 and code not in accepted:
            counts[ch] += 1
            if ch in ASCII:
                out.append(ASCII[ch])
            else:
                unknown.add(ch)
                out.append("?")
        else:
            out.append(ch)
    if unknown and not allow_unknown:
        raise SystemExit("bowline move: characters with no ASCII spelling: " + ", ".join(f"U+{ord(c):04X}" for c in sorted(unknown))
                         + ". Add them to the repository's acceptedCharacters, or pass --allow-unknown to write '?' for them.")
    return "".join(out), counts


def do_plan(options):
    root = common.repo_root(options.repo)
    config = common.load_config(root)
    text = common.read_text(options.file)
    preamble, sections = split_sections(text)
    small, large = config["limits"]["onDemandCutoffSmallWindow"], config["limits"]["onDemandCutoffLargeWindow"]
    total_lines = common.count_lines(text)
    print(f"bowline move plan: {options.file}: {total_lines} lines, {len(text):,} characters")
    offset = len("\n".join(preamble)) + 1
    line = len(preamble) + 1
    print(f"  {'section':50} {'lines':>12} {'chars':>9}  {'starts at char':>14}")
    print(f"  {'(before the first heading)':50} {f'1-{len(preamble)}':>12} {offset - 1:>9}")
    for title, body in sections:
        body_text = "\n".join(body)
        marks = []
        if offset <= small < offset + len(body_text):
            marks.append("200K window cut falls here")
        if offset <= large < offset + len(body_text):
            marks.append("1M window cut falls here")
        if offset >= large:
            marks.append("never read on either window")
        elif offset >= small:
            marks.append("never read on a 200K window")
        print(f"  {title[:50]:50} {f'{line}-{line + len(body) - 1}':>12} {len(body_text):>9}  {offset:>14}  {'; '.join(marks)}")
        offset += len(body_text) + 1
        line += len(body)
    print("\nDecide for each section: a long-form page (docs/conventions), a scoped rule (.claude/rules/<area>/), a skill, or the"
          " index. Write the decision as a spec and run `bowline move run --spec <file> --check`.")
    return 0


def do_run(options):
    root = common.repo_root(options.repo)
    config = common.load_config(root)
    accepted = common.accepted_characters(config.get("gate", {}).get("acceptedCharacters"))
    rules_dir = config.get("rulesDir", ".claude/rules")
    with open(options.spec, encoding="utf-8") as handle:
        spec = json.load(handle)
    source_path = options.file
    # Real paths on both sides: git reports the repository root resolved, and the file may be given through a symlink
    # or a short name (macOS's /var, Windows's RUNNER~1), which would make the relative path wrong.
    source_rel = os.path.relpath(os.path.realpath(source_path), os.path.realpath(root)).replace("\\", "/")
    text = common.read_text(source_path)
    preamble, sections = split_sections(text)
    date = __import__("datetime").date.today().isoformat()
    outputs = []
    used = []
    total = collections.Counter()

    for page in spec.get("pages", []):
        bodies = []
        for wanted in page["sections"]:
            title, body = find_section(sections, wanted)
            used.append(title)
            bodies.append("\n".join(body).rstrip("\n"))
        content, counts = normalize("\n\n".join(bodies), accepted, options.allow_unknown)
        total.update(counts)
        head = page.get("title", f"# {', '.join(page['sections'])}, the long form") + "\n\n"
        outputs.append((page["target"], head + PREAMBLE.format(source=source_rel, date=date, rules_dir=rules_dir) + content + "\n"))

    for rule in spec.get("rules", []):
        bodies = []
        for wanted in rule["sections"]:
            title, body = find_section(sections, wanted)
            used.append(title)
            kept, skipping = [], False
            for line in body:
                if line.startswith("- "):
                    skipping = any(line.startswith(d) for d in rule.get("drop", []))
                elif not line.startswith("  "):
                    skipping = False
                if not skipping:
                    kept.append(line)
            kept[0] = "# " + kept[0][3:] if kept and kept[0].startswith("## ") else (kept[0] if kept else "")
            bodies.append("\n".join(kept).rstrip("\n"))
        content, counts = normalize("\n\n".join(bodies), accepted, options.allow_unknown)
        total.update(counts)
        front = "---\npaths:\n" + "".join(f'  - "{p}"\n' for p in rule.get("paths", [])) + "---\n\n" if rule.get("paths") else ""
        note = ""
        if rule.get("drop"):
            note = f"\n\nThe long form of these rules, with every entry, is under `{config.get('conventionsDir', 'docs/conventions')}/`.\n"
        outputs.append((rule["target"], front + content + ("\n" if not note else note)))

    if "index" in spec:
        index = common.read_text(spec["index"])
        bad = sorted({ord(c) for c in index if ord(c) > 127 and ord(c) not in accepted})
        if bad:
            raise SystemExit("bowline move: the index has characters outside ASCII: " + ", ".join(f"U+{c:04X}" for c in bad))
        outputs.append((source_rel, index))

    unused = [t for t, _ in sections if t not in used]
    for target, content in outputs:
        print(f"  {target}: {common.count_lines(content)} lines, {len(content):,} characters")
    print(f"normalized: {dict((f'U+{ord(k):04X}', v) for k, v in total.most_common())}")
    if unused:
        print(f"sections not named by the spec (they leave the file unless the index keeps them): {', '.join(unused)}")
    if options.check:
        print("check only; nothing written.")
        return 0
    for target, content in outputs:
        full = os.path.join(root, target)
        os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        print("wrote", target)
    return 0


def do_find_pointers(options):
    root = common.repo_root(options.repo)
    needle = options.name
    hits = 0
    for path in common.tracked_files(root, "."):
        full = os.path.join(root, path)
        try:
            with open(full, "rb") as handle:
                content = handle.read()
        except OSError:
            continue
        if b"\0" in content[:8000]:
            continue
        for number, line in enumerate(content.decode("utf-8", "replace").split("\n"), start=1):
            if needle in line:
                hits += 1
                print(f"{path}:{number}: {line.strip()[:160]}")
    print(f"bowline move: {hits} line(s) name '{needle}'.")
    return 0


def do_pointers(options):
    root = common.repo_root(options.repo)
    with open(options.spec, encoding="utf-8") as handle:
        spec = json.load(handle)
    changes = []
    for entry in spec:
        full = os.path.join(root, entry["file"])
        text = common.read_text(full)
        count = text.count(entry["old"])
        if count != 1:
            raise SystemExit(f"bowline move: {entry['file']}: the old text occurs {count} time(s), not once: {entry['old'][:60]!r}")
        changes.append((full, entry["file"], text.replace(entry["old"], entry["new"], 1)))
        print(f"ok  {entry['file']}")
    if options.check:
        print(f"check only: {len(changes)} replacement(s) would be made.")
        return 0
    for full, path, text in changes:
        with open(full, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    print(f"{len(changes)} file(s) updated.")
    return 0


def do_place(options):
    """Copies finished drafts from a scratch folder into instruction files: rules, skills, pages, or a CLAUDE.md."""
    root = common.repo_root(options.repo)
    config = common.load_config(root)
    accepted = common.accepted_characters(config.get("gate", {}).get("acceptedCharacters"))
    skills = config.get("skillsDir", ".claude/skills")
    homes = [config.get("rulesDir", ".claude/rules"), config.get("conventionsDir", "docs/conventions")]
    homes += skills if isinstance(skills, list) else [skills]
    homes = [h.replace("\\", "/").strip("/") + "/" for h in homes]
    with open(options.spec, encoding="utf-8") as handle:
        spec = json.load(handle)
    outputs = []
    total = collections.Counter()
    for entry in spec:
        target = entry["target"].replace("\\", "/")
        while target.startswith("./"):
            target = target[2:]
        target = target.lstrip("/")
        if not (any(target.startswith(home) for home in homes) or os.path.basename(target) == "CLAUDE.md"):
            raise SystemExit(f"bowline move: {target} is not an instruction file; place writes only under "
                             f"{', '.join(home.rstrip('/') for home in homes)}, or a CLAUDE.md.")
        source = os.path.join(root, entry["source"])
        if not os.path.isfile(source):
            raise SystemExit(f"bowline move: the draft {entry['source']} does not exist.")
        content, counts = normalize(common.read_text(source), accepted, options.allow_unknown)
        total.update(counts)
        note = ""
        if target.startswith(homes[0]) and not content.startswith("---"):
            note = "  (no paths: front matter, so this rule would load in every session)"
        outputs.append((target, content, note))
    for target, content, note in outputs:
        print(f"  {target}: {common.count_lines(content)} lines, {len(content):,} characters{note}")
    print(f"normalized: {dict((f'U+{ord(k):04X}', v) for k, v in total.most_common())}")
    if options.check:
        print("check only; nothing written.")
        return 0
    for target, content, _ in outputs:
        full = os.path.join(root, target)
        os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        print("wrote", target)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Moves an oversized instruction file into pages, rules and an index.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan"); p.add_argument("--file", required=True); p.add_argument("--repo")
    p = sub.add_parser("run"); p.add_argument("--file", required=True); p.add_argument("--spec", required=True)
    p.add_argument("--check", action="store_true"); p.add_argument("--allow-unknown", action="store_true"); p.add_argument("--repo")
    p = sub.add_parser("find-pointers"); p.add_argument("--name", required=True); p.add_argument("--repo")
    p = sub.add_parser("pointers"); p.add_argument("--spec", required=True); p.add_argument("--check", action="store_true"); p.add_argument("--repo")
    p = sub.add_parser("place"); p.add_argument("--spec", required=True); p.add_argument("--check", action="store_true")
    p.add_argument("--allow-unknown", action="store_true"); p.add_argument("--repo")
    options = parser.parse_args(argv)
    if not common.repo_root(options.repo):
        print("bowline move: not inside a git repository.", file=sys.stderr)
        return 2
    commands = {"plan": do_plan, "run": do_run, "find-pointers": do_find_pointers, "pointers": do_pointers, "place": do_place}
    return commands[options.command](options)


if __name__ == "__main__":
    sys.exit(main())
