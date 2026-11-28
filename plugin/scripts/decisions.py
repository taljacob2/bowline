"""Decisions: where a subject was decided, so that a session reads it before it asks the person or decides itself.

    python -I scripts/decisions.py find <word>... [--repo <path>] [--verbose] [--seconds <n>] [--no-memory]
    python -I scripts/decisions.py records [--repo <path>]
    python -I scripts/decisions.py section [--repo <path>]

find lists every place in the repository where the words stand close together, in any case: the records of decisions
first, then the other documents, the tests, the code, and the commit messages. A place is one where every word appears
within a few lines of the others (decisions.within, 3 by default), because a sentence in a document is wrapped over
two or three lines. In the records, the places that say decided, agreed or approved come first. For a line of a test
or of the code, it names the commit that last wrote the line. For a comment that cites a decision by its date, it
names the record that holds that date, or says that none does. For a record's entry that approves a number of things
by reference, such as "all three as recommended", it says that the entry names a recommendation without saying it. It
ends with what it did not search: a page outside the repository, the conversation, and the memory's notes, of which it
gives only the names of those that hold the words.

It is a list of places, never an answer. It cannot see that two lines disagree, and it cannot find the nearest similar
case in a product; the decide skill asks Claude for both.

records prints the files taken as records of decisions: those named in .claude/bowline.json (decisions.records), or,
when none is named, the documents whose name says so: a roadmap, a design document, a decisions page, a changelog, or
a file in a folder named adr or decisions. A file under .claude is an instruction, never a record.

section is for a repository whose rule about recording decisions was written before the starter rule had its section
"Before a question goes to the person". It says whether the repository's instructions have such a section, and if
not: where it goes, how many characters it adds to the rules every session loads, the bullet of the earlier starter
rule that it replaces, and the text. It changes no file: the rule is the repository's own, and the conventions skill
makes the edit with the person.

This module also gives the doctor its two findings about decisions (findings), and a session's start its sentence for
a repository without the section (start_line).

The files are found by git grep, over the files git tracks and the ones it would add, and only those that hold every
word are read. The documents are searched first and the tests and the code after them, because on a disk that was not
read lately the search of every file can take a minute or more: on the first repository it was measured on, about 80
seconds the first time and 0.2 seconds after that. The search has a time limit (decisions.seconds); when it runs out,
the list says which parts were not searched, and a second run is fast, because the first one read the files.
Exit codes: 0 when the search ran, whatever it found; 2 when the script could not run.
"""

import argparse
import concurrent.futures
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import budget  # noqa: E402
import common  # noqa: E402

DOCUMENT =(".md", ".markdown", ".txt", ".rst", ".adoc")
# A document whose name says that it records decisions, and a folder that holds such documents.
RECORD_NAME = re.compile(r"(?<![a-z])(decisions?|adrs?|roadmap|design|changelog)(?![a-z])", re.IGNORECASE)
RECORD_FOLDER = ("adr", "adrs", "decisions")
TEST = re.compile(r"(^|[/_.-])(tests?|specs?|__tests__|e2e)([/_.-]|$)", re.IGNORECASE)
DATE = re.compile(r"(?<![0-9])\d{4}-\d{2}-\d{2}(?![0-9])")
CITES = re.compile(r"\b(decision|decided|agreed|approved)\b", re.IGNORECASE)
# What a place in a record says when it is where the subject was settled, or left open.
DECIDES = re.compile(r"\b(decided|decision|agreed|approved)\b|\bopen\s*[:(]", re.IGNORECASE)
# Where an entry of a document starts: a heading, a numbered item, or a list item that opens in bold.
LEAD = re.compile(r"^(#{1,6}\s|\d+[.)]\s|[-*]\s+\*\*)")
# Where the next entry starts, for the lines that follow a place: a heading or any item of a list, at the margin.
NEXT = re.compile(r"^(#{1,6}\s|\d+[.)]\s|[-*+]\s)")
# How many lines after a place still belong to it, when no blank line ends the paragraph sooner: a record names what
# was asked over a few lines and says "all seven as recommended" at the end of them.
FOLLOWS = 8
# The heading of the section that tells a session to look a decision up, as the starter rule has it, and the skill a
# repository's own wording names; the rule the section is taken from; and the bullet of the starter rule before
# 0.19.0 that the section replaces.
SECTION = re.compile(r"^#{1,4}\s.*\bbefore a question\b.*$", re.IGNORECASE | re.MULTILINE)
SKILL = "/bowline:decide"
STARTER_RULE = os.path.join(common.PLUGIN_ROOT, "templates", "rules", "recording-decisions.md")
OLD_BULLET = re.compile(r"^- \*\*[^*\n]*\bis a claim, not a fact\.\*\*", re.MULTILINE)
WIDTH = 100
PARTS = (("records", "RECORDS OF DECISIONS"), ("documents", "OTHER DOCUMENTS"), ("tests", "TESTS"), ("code", "CODE"))
BLAMES_AT_ONCE = 8


def settings(config):
    return config.get("decisions") or {}


def is_document(path):
    return path.lower().endswith(DOCUMENT)


def record_files(files, config):
    """The files of a listing that are records of decisions: those the repository names (decisions.records, as paths or
    patterns from its top), or, when it names none, the documents whose name or folder says so. An instruction file
    under .claude is never one: a rule about recording decisions is not a record of them."""
    named = [str(pattern).replace("\\", "/") for pattern in settings(config).get("records") or []]
    if named:
        return sorted({path for pattern in named for path in common.matching(files, pattern)})
    found = []
    for path in files:
        parts = path.split("/")
        if not is_document(path) or parts[0] == ".claude":
            continue
        stem = os.path.splitext(parts[-1])[0]
        if RECORD_NAME.search(stem) or any(part.lower() in RECORD_FOLDER for part in parts[:-1]):
            found.append(path)
    return sorted(found)


def part_of(path, records):
    """Which part of the list a file belongs to: records, documents, tests or code."""
    if path in records:
        return "records"
    if is_document(path):
        return "documents"
    return "tests" if TEST.search(path) else "code"


def holding_every_word(root, words, documents, deadline):
    """The files that hold every word somewhere, in any case, among the files git tracks and the ones it would add: one
    git grep, so that only those files are read. documents chooses the documents alone, or every other file. None when
    git did not answer before the deadline."""
    left = deadline - time.monotonic()
    if left <= 0:
        return None
    command = ["git", "-C", root, "--no-optional-locks", "grep", "-l", "-z", "-I", "-i", "-F", "--untracked", "--all-match"]
    for word in words:
        command += ["-e", word]
    command += ["--"] + ([] if documents else ["."])
    command += [(":(glob)**/*" if documents else ":(exclude,glob)**/*") + suffix for suffix in DOCUMENT]
    try:
        result = subprocess.run(command, capture_output=True, timeout=left)
    except subprocess.TimeoutExpired:
        return None
    return sorted(path for path in result.stdout.decode("utf-8", "replace").split("\0") if path)


def places(lines, words, within):
    """The places in a text's lines where every word appears within `within` consecutive lines, as the indexes of each
    place's first line. A line that holds every word is a place of its own, always. A stretch of two or more lines is
    a place only when it reaches no line that is one already, because that line says it better: without this, the
    line above a sentence was listed in the sentence's stead. A place takes only the lines it needs, so a sentence
    wrapped over two lines is one place and not two. The words are given in lower case."""
    lowered = [line.lower() for line in lines]
    found = {index for index, line in enumerate(lowered) if all(word in line for word in words)}
    taken = set(found)
    for index, line in enumerate(lowered):
        if index in taken or not any(word in line for word in words):
            continue
        for more in range(1, within):
            stretch = range(index, min(len(lowered), index + more + 1))
            if any(at in taken for at in stretch):
                break
            if all(word in "\n".join(lowered[at] for at in stretch) for word in words):
                found.add(index)
                taken.update(stretch)
                break
    return sorted(found)


def paragraph_from(lines, index):
    """The lines of a place and the ones that follow it in the same entry, as (index, line) pairs: up to FOLLOWS
    lines, ending sooner at a blank line, a heading or the next item of a list, which belongs to another entry."""
    out = []
    for at in range(index, min(len(lines), index + FOLLOWS)):
        if at > index and (not lines[at].strip() or NEXT.match(lines[at])):
            break
        out.append((at, lines[at]))
    return out


def lead_of(lines, index):
    """The line that opens the entry a line belongs to, for a line deep inside a long entry of a document: the nearest
    heading, numbered item or bold list item above it. None when the line opens its own entry or nothing does."""
    if LEAD.match(lines[index]):
        return None
    for above in range(index - 1, max(-1, index - 400), -1):
        if LEAD.match(lines[above]):
            return above
    return None


def cut(text, room):
    """A line as the list shows it: its spaces folded, and cut with three dots when it is longer than the room."""
    text = " ".join(text.split())
    return text if len(text) <= room else text[:max(room - 3, 1)].rstrip() + "..."


def last_written(root, path, numbers, deadline):
    """The commit that last wrote each of some lines of one file, as {line number: words}: one git blame for the file.
    git refuses a file that no commit holds, and such a file's lines are said to be not committed yet. A line the time
    limit left unanswered is left out."""
    left = deadline - time.monotonic()
    if left <= 0:
        return {}
    command = ["git", "-C", root, "--no-optional-locks", "blame", "--porcelain"]
    for number in sorted(set(numbers)):
        command += ["-L", f"{number},{number}"]
    try:
        result = subprocess.run(command + ["--", path], capture_output=True, timeout=left)
    except subprocess.TimeoutExpired:
        return {}
    if result.returncode != 0:
        return {number: "not committed yet" for number in numbers}
    days, lines_of, commit = {}, {}, None
    for line in result.stdout.decode("utf-8", "replace").split("\n"):
        head = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", line)
        if head:
            commit = head.group(1)
            lines_of[int(head.group(2))] = commit
        elif commit and line.startswith("author-time "):
            when = line.split(" ", 1)[1].strip()
            if when.isdigit():
                days[commit] = time.strftime("%Y-%m-%d", time.gmtime(int(when)))
    out = {}
    for number, commit in lines_of.items():
        if not commit.strip("0"):
            out[number] = "not committed yet"
        else:
            out[number] = f"last written in {commit[:7]}, {days.get(commit, 'on an unknown day')}"
    return out


def commit_messages(root, words, limit):
    """The commits of the current branch whose message holds every word, newest first, as (hash, day, subject)."""
    command = ["git", "-C", root, "--no-optional-locks", "log", "--no-show-signature", "-i", "-F", "--all-match",
               "--format=%h%x09%ad%x09%s", "--date=short", "-n", str(limit)]
    for word in words:
        command += ["--grep", word]
    result = subprocess.run(command, capture_output=True)
    if result.returncode != 0:
        return []
    return [tuple(line.split("\t", 2)) for line in result.stdout.decode("utf-8", "replace").split("\n") if line.count("\t") >= 2]


def notes_holding(root, words):
    """The names of the memory's notes that hold every word. Only the names: a note's words are shown to a person who
    asks for them, and a note is working notes, never the record."""
    folder = common.memory_folder(common.main_checkout(root))
    if not os.path.isdir(folder):
        return []
    found = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md") or name == "MEMORY.md":
            continue
        try:
            text = common.read_text(os.path.join(folder, name)).lower()
        except OSError:
            continue
        if all(word in text for word in words):
            found.append(name)
    return found


def quoted(lines, index, at):
    """Whether a place in a line stands inside quotation marks or backquotes: a phrase that a document quotes is
    spoken about, not used, and a document that explains what an approval by reference is must not be taken for
    one. The marks are counted from the start of the paragraph, because a quotation that opens at the end of one
    line closes on the next: bowline's own record of this check was taken for an approval until they were."""
    start = index
    while start > 0 and lines[start - 1].strip():
        start -= 1
    before = " ".join(lines[start:index] + [lines[index][:at]])
    return before.count('"') % 2 == 1 or before.count("`") % 2 == 1


def approvals_by_reference(root, config):
    """The lines of the records of decisions that approve a number of things by reference, such as "all three as
    recommended", outside quotation marks: (path, line number, the phrase, the line). Nothing when the repository set
    the pattern (decisions.byReference) to an empty one."""
    pattern = settings(config).get("byReference")
    if not pattern:
        return []
    expression = re.compile(pattern, re.IGNORECASE)
    found = []
    for path in record_files(common.listed_files(root), config):
        try:
            lines = common.read_text(os.path.join(root, path)).replace("\r\n", "\n").split("\n")
        except OSError:
            continue
        for index, line in enumerate(lines):
            label = next((match for match in expression.finditer(line) if not quoted(lines, index, match.start())), None)
            if label:
                found.append((path, index + 1, label.group(0), line))
    return found


def instruction_files(root, config):
    """The files a session of the repository has in front of it or may load as a rule: each root CLAUDE.md and every
    rule under the rules folder."""
    rules = os.path.join(root, *str(config.get("rulesDir") or ".claude/rules").split("/"))
    paths = [os.path.join(root, path) for path in common.root_claude_md(root)]
    for folder, _, files in os.walk(rules):
        paths += [os.path.join(folder, name) for name in sorted(files) if name.endswith(".md")]
    return paths


def has_section(root, config):
    """Whether the repository's instructions tell a session to look a decision up before it asks: a heading that says
    "before a question", as the starter rule's does, or the name of the skill, in a rule or in a root CLAUDE.md. A
    repository that words its own rule is recognised by naming the skill in it."""
    for path in instruction_files(root, config):
        try:
            text = common.read_text(path)
        except OSError:
            continue
        if SECTION.search(text) or SKILL in text:
            return True
    return False


def template_section():
    """The section as the plugin's starter rule has it, from its heading to the end of the rule: the one text that
    init writes into a new repository and that an existing rule file takes."""
    text = common.read_text(STARTER_RULE).replace("\r\n", "\n")
    start = SECTION.search(text)
    if not start:
        return ""
    rest = text[start.start():]
    following = re.search(r"^#{1,2}\s", rest[len(start.group(0)):], re.MULTILINE)
    return (rest[:len(start.group(0)) + following.start()] if following else rest).rstrip("\n") + "\n"


BY_REFERENCE_WHY = (
    "An entry that says only that a recommendation was approved keeps the approval and loses the decision: what was "
    "recommended stayed in a conversation or on a page the next reader does not have. A later session reads into the "
    "label what it expects, and the code, a test and the manual can each claim the same decision for a different answer.")
BY_REFERENCE_FIX = (
    "Write into each such entry what was decided, in a sentence that stands alone, with the person's own words; where "
    "what was recommended can no longer be found, say so in the entry and ask the person. /bowline:decide is the "
    f"procedure. A phrase inside quotation marks is not counted, and an empty decisions.byReference in {common.CONFIG_FILE} "
    "turns this off.")
NO_SECTION_WHY = (
    "A question to the person most often goes wrong before it is asked: the answer was already in a record, or a "
    "document and the program disagreed and the session picked a side. In a replay of such a round, sessions with "
    "the rule's two bullets in front of them edited nothing and asked in 5 of 5 runs, and without them in 6 of 13.")
NO_SECTION_FIX = (
    "/bowline:conventions adds the section to the rule about recording decisions, or /bowline:init writes the starter "
    "rule where the repository has none; `bowline decisions section` prints the text and what it costs. A repository "
    "with its own words for it is recognised by a heading that says \"Before a question\" or by naming /bowline:decide.")
WITHOUT_THE_SECTION = (
    "bowline: before you put a design question to the person, recommend an answer or settle one yourself, and when a "
    "document, a test's name or a comment says one thing and the program does another, edit neither and run the skill "
    "/bowline:decide first. This repository's instructions have no rule about looking a decision up, so this holds "
    "until they have one.")
OFFER_THE_SECTION = " /bowline:conventions adds the rule's two bullets to the repository; offer that to the person."
# How many of the places a finding names one by one; the lookup lists every one.
PLACES_SHOWN = 3


def findings(root, config):
    """The doctor's two findings about decisions. A warning when an entry of the records approves by reference: it
    names up to PLACES_SHOWN places, and each labelled line is one thing of its own (keys), so that a line written
    during a session is told once and a line that was there all along is not told again. And a note when the
    repository's instructions have no section about looking a decision up; the line at a session's start is where a
    session meets that unasked (start_line), and this is its long form for a person who reads the report."""
    out = []
    places = approvals_by_reference(root, config)
    if places:
        shown = "; ".join(f"{path}:{number} says \"{phrase}\"" for path, number, phrase, _ in places[:PLACES_SHOWN])
        more = f"; and {len(places) - PLACES_SHOWN} more" if len(places) > PLACES_SHOWN else ""
        counted = common.count(len(places), "entry of the records of decisions approves by reference and does not say",
                               "entries of the records of decisions approve by reference and do not say")
        finding = common.Finding(
            "warning", f"{counted} what was decided: {shown}{more}.",
            BY_REFERENCE_WHY, BY_REFERENCE_FIX,
            many="{count} repositories have an entry of their records of decisions that approves by reference.")
        finding.keys = [f"approves by reference: {path}: {' '.join(line.split())}" for path, _, _, line in places]
        out.append(finding)
    if not has_section(root, config):
        out.append(common.Finding(
            "note", "The repository's instructions have no section about looking a decision up before a question goes to the person.",
            NO_SECTION_WHY, NO_SECTION_FIX,
            many="{count} repositories have no section about looking a decision up before a question goes to the person."))
    return out


def start_line(root, config):
    """The sentence a session's start gets in a repository whose instructions have no section about looking a
    decision up, or None. In the line itself, because a session that does not know the rule has no reason to open the
    skill that holds it: in the replay, with the plugin and no rule, the skill was left unused in 5 of 13 runs, and
    with the rule's text, which names the skill, in none of 10. Its words and its place were tried on live sessions:
    said last, after the line about other sessions, and as a description ("this repository has no rule ..., so this
    holds"), 2 of 5 sessions used the skill; said before that line and as the action to take, 5 of 5. So the action
    comes first in it, and doctor --brief prints it before the line about other sessions. decisions.atStart false
    gives no sentence."""
    if settings(config).get("atStart") is False or has_section(root, config):
        return None
    return WITHOUT_THE_SECTION + (OFFER_THE_SECTION if common.writes_allowed(root) else "")


def show_section(root, config):
    """What `section` prints: whether the repository has the section, and if not, where it goes, what it costs
    against the rules every session loads, the bullet of the earlier starter rule that it replaces, and the text."""
    if has_section(root, config):
        print("bowline decisions: this repository's instructions already have a section about looking a decision up, "
              "or name /bowline:decide. Nothing to add.")
        return 0
    section = template_section()
    rules = str(config.get("rulesDir") or ".claude/rules").replace("\\", "/")
    target = f"{rules}/recording-decisions.md"
    print("bowline decisions: this repository's instructions have no section about looking a decision up before a "
          "question goes to the person.")
    print()
    path = os.path.join(root, *target.split("/"))
    bullet, line = "", 0
    if not os.path.isfile(path):
        print(f"{target} does not exist. `bowline init` writes the starter rule there, with the section in it. If the")
        print("repository keeps its rule about decisions under another name, the section goes at that file's end.")
    else:
        print(f"It goes at the end of {target}, which exists. Edit that file; never write a second one.")
        text = common.read_text(path).replace("\r\n", "\n")
        old = OLD_BULLET.search(text)
        if old:
            end = re.search(r"^(?:- |#)", text[old.end():], re.MULTILINE)
            bullet = text[old.start():old.end() + end.start()] if end else text[old.start():]
            line = text[:old.start()].count("\n") + 1
    limit = config["limits"]["unscopedChars"]
    now = budget.measure(root, config)[1]["unscoped"]
    then = now + len(section) + 1
    print("It belongs in a rule without a path, or in the root CLAUDE.md: a question can come at any moment.")
    print()
    print(f"The section is {len(section):,} characters. The rules every session loads stand at {now:,} of {limit:,}, and "
          f"at {then:,} with it" + (", which is over the limit." if then > limit else "."))
    if bullet:
        print(f"Line {line} of {target} opens the bullet that the section replaces, the one that calls a line in a")
        print("document \"a claim, not a fact\": it told a session to correct the document, which is one of the two ways")
        print(f"to be wrong. Taking it out frees {len(bullet):,} characters, and the rules then stand at {then - len(bullet):,}.")
    elif then > limit:
        print("Move or trim a rule first, with the person; `bowline budget` measures the rules.")
    print()
    print("The section, to add as it is or in the repository's own words:")
    print()
    print(section, end="")
    return 0


class Search:
    """One lookup: the files read, the places found in each part, and what the time limit left out. A place is
    (path, line number, the line, the notes under it), and a note is its words."""

    def __init__(self, root, config, words, seconds):
        self.root, self.words = root, [word.lower() for word in words]
        chosen = settings(config)
        self.within = max(1, int(chosen.get("within") or 3))
        self.by_reference = re.compile(chosen.get("byReference") or r"(?!)", re.IGNORECASE)
        self.records = record_files(common.listed_files(root), config)
        self.texts = {}
        self.found = {name: [] for name, _ in PARTS}
        self.deadline = time.monotonic() + seconds
        documents = holding_every_word(root, self.words, True, self.deadline)
        rest = holding_every_word(root, self.words, False, self.deadline) if documents is not None else None
        self.searched = {"documents": documents is not None, "tests": rest is not None, "code": rest is not None}
        # The records are read whatever git said: they are few, and they are what the lookup is for.
        for path in sorted(set(self.records) | set(documents or []) | set(rest or [])):
            self.read(path)
        # Where the subject was settled comes before where it is only mentioned.
        self.found["records"].sort(key=lambda place: not place[4])
        self.found = {name: [place[:4] for place in found] for name, found in self.found.items()}

    def lines_of(self, path):
        if path not in self.texts:
            try:
                self.texts[path] = common.read_text(os.path.join(self.root, path)).replace("\r\n", "\n").split("\n")
            except OSError:
                self.texts[path] = []
        return self.texts[path]

    def read(self, path):
        lines = self.lines_of(path)
        part = part_of(path, self.records)
        for index in places(lines, self.words, self.within):
            notes, decides, lead = [], False, None
            if part in ("records", "documents"):
                lead = lead_of(lines, index)
                if lead is not None:
                    notes.append(f"in the entry at line {lead + 1}: {lines[lead]}")
            if part == "records":
                paragraph = paragraph_from(lines, index)
                # The word that says so is often in the entry's first line: "Open: ..." above the lines of the question.
                opening = lines[lead] if lead is not None else ""
                decides = any(DECIDES.search(line) for line in [opening] + [line for _, line in paragraph])
                for at, line in paragraph:
                    label = next((match for match in self.by_reference.finditer(line) if not quoted(lines, at, match.start())), None)
                    if label:
                        notes.append(f"line {at + 1} says \"{label.group(0)}\": it names a recommendation without saying "
                                     "it, so this entry cannot tell you what was decided")
                        break
            if part in ("tests", "code"):
                stretch = " ".join(lines[index:index + self.within])
                if CITES.search(stretch):
                    for day in sorted(set(DATE.findall(stretch))):
                        notes.append(self.record_of(day))
            self.found[part].append((path, index + 1, lines[index], notes, decides))

    def record_of(self, day):
        """Where the records hold a date that a comment cites, in words."""
        held = []
        for path in self.records:
            for index, line in enumerate(self.lines_of(path)):
                if day in line:
                    held.append(f"{path}:{index + 1}")
        if not held:
            return f"it cites {day}, and no record of decisions holds that date"
        more = f" and {len(held) - 2} more" if len(held) > 2 else ""
        return f"it cites {day}; a record holds that date at {', '.join(held[:2])}{more}"

    def written(self, shown):
        """For the places of the tests and the code that are shown: the commit that last wrote each line, asked of git
        once per file and for several files at once, as {(path, line number): words}."""
        by_file = {}
        for name in ("tests", "code"):
            for path, number, _, _ in shown[name]:
                by_file.setdefault(path, []).append(number)
        out = {}
        if not by_file:
            return out
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(BLAMES_AT_ONCE, len(by_file))) as pool:
            futures = {path: pool.submit(last_written, self.root, path, numbers, self.deadline) for path, numbers in by_file.items()}
            for path, future in futures.items():
                for number, words in future.result().items():
                    out[(path, number)] = words
        return out


def print_wrapped(text, indent="      "):
    """Prints words under a place, folded at the list's width, so that a note is read whole."""
    words, line = " ".join(text.split()).split(" "), indent
    for word in words:
        if len(line) + len(word) + 1 > WIDTH and line.strip():
            print(line.rstrip())
            line = indent
        line += word + " "
    if line.strip():
        print(line.rstrip())


def show(search, limit, verbose, memory, seconds):
    one = len(search.words) == 1
    words = " with ".join(f'"{word}"' for word in search.words)
    print(f"bowline decisions: {words}, in the repository at")
    print(f"  {search.root}")
    print("A place is listed where " + ("the word appears" if one else
                                         f"the words appear within {search.within} lines of each other") + ", in any case.")
    shown = {name: (found if verbose else found[:limit]) for name, found in search.found.items()}
    written = search.written(shown)
    for name, title in PARTS:
        print()
        found = search.found[name]
        if name == "records":
            if not search.records:
                print(f"{title}  none found. Name them in {common.CONFIG_FILE} (decisions.records).")
                continue
            files = ", ".join(search.records)
            if len(title) + 2 + len(files) > WIDTH:
                files = f"{len(search.records)} files, which `bowline decisions records` lists"
            print(f"{title}  {files}")
        elif not search.searched[name]:
            print(f"{title}  not searched: git did not answer within {seconds} seconds. Run it again: the files are read")
            print("  now, so the second search is fast.")
            continue
        else:
            print(title)
        if not found:
            print("  nothing")
            continue
        for path, number, line, notes in shown[name]:
            where = f"{path}:{number}"
            if len(where) > WIDTH // 2:
                print(f"  {where}")
                print(f"      {cut(line, WIDTH - 6)}")
            else:
                print(f"  {where}  {cut(line, WIDTH - 4 - len(where))}")
            for note in notes:
                if note.startswith("in the entry"):
                    print("      " + cut(note, WIDTH - 6))
                else:
                    print_wrapped(note)
            if (path, number) in written:
                print(f"      {written[(path, number)]}")
        if len(found) > len(shown[name]):
            first = "; the places that say decided, agreed or approved are listed first" if name == "records" else ""
            print_wrapped(f"and {len(found) - len(shown[name])} more (--verbose lists every one{first})", "  ")
    print()
    messages = commit_messages(search.root, search.words, 200)
    print("COMMIT MESSAGES")
    if not messages:
        print("  nothing")
    for commit, day, subject in messages if verbose else messages[:limit]:
        print(f"  {commit}  {day}  {cut(subject, WIDTH - 6 - len(commit) - len(day))}")
    if not verbose and len(messages) > limit:
        print(f"  and {len(messages) - limit} more (--verbose lists every one)")
    print()
    print("NOT SEARCHED  a page outside this repository that a record points to; this conversation; and the")
    print("  memory's notes, which are working notes and never the record.")
    if memory:
        notes = notes_holding(search.root, search.words)
        if notes:
            print_wrapped(f"Notes that hold the {'word' if one else 'words'}: {common.names(notes, verbose, 6)}.", "  ")
    print("This is a list of places, not an answer. Read each line in its file before you rely on it.")


def root_or_exit(start):
    root = common.repo_root(start)
    if root:
        return root
    workspace, roots = common.roots_for(start)
    if roots:
        print("bowline decisions: this is a folder of repositories. Name the one the subject belongs to: "
              f"--repo {os.path.basename(roots[0])}", file=sys.stderr)
    else:
        print("bowline decisions: not inside a git repository.", file=sys.stderr)
    sys.exit(2)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lists where a subject was decided, before a question goes to the person.")
    commands = parser.add_subparsers(dest="command")
    find = commands.add_parser("find", help="every place where the words stand close together: records, documents, tests, code, commits")
    find.add_argument("words", nargs="+", help="the words of the subject, such as: export failed")
    find.add_argument("--verbose", action="store_true", help="list every place, not only the first ones of each part")
    find.add_argument("--seconds", type=int, help="how long the search of the files may take (default: decisions.seconds)")
    find.add_argument("--no-memory", action="store_true", help="do not name the memory's notes that hold the words")
    records = commands.add_parser("records", help="the files taken as records of decisions")
    section = commands.add_parser("section", help="the section about looking a decision up, for a rule file that lacks it: "
                                                   "where it goes, what it costs, and its text")
    for command in (find, records, section):
        command.add_argument("--repo", help="a path inside the repository (default: the current folder)")
    options = parser.parse_args(argv)
    if not options.command:
        parser.print_help()
        return 2
    root = root_or_exit(options.repo)
    config = common.load_config(root)
    if options.command == "section":
        return show_section(root, config)
    if options.command == "records":
        found = record_files(common.listed_files(root), config)
        named = bool(settings(config).get("records"))
        how = f"named in {common.CONFIG_FILE} (decisions.records)" if named else "found by their names, because decisions.records names none"
        print(f"bowline decisions: {common.count(len(found), 'file is', 'files are')} taken as records of decisions, {how}.")
        for path in found:
            print(f"  {path}")
        return 0
    words = [word for word in (w.strip() for w in options.words) if word]
    if not words:
        print("bowline decisions: give at least one word of the subject.", file=sys.stderr)
        return 2
    chosen = settings(config)
    seconds = max(1, options.seconds if options.seconds is not None else int(chosen.get("seconds") or 60))
    search = Search(root, config, words, seconds)
    show(search, max(1, int(chosen.get("shown") or 8)), options.verbose, not options.no_memory, seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
