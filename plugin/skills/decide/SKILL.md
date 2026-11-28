---
name: decide
description: Look up what was already decided before a design question goes to the person, and bring the question well - list where the subject appears in the records, the documents, the tests, the code and the commits, find which side is the mistake when a record and the program disagree before editing either, make what the product already does in the nearest case one of the choices, give each reason its source with the strongest argument against the recommendation, and record the answer in the person's own words. Use before you ask the person a design question or recommend an answer, before you settle such a question yourself, when a document, a test's name or a comment says one thing and the program does another, when the person asks why you recommend something, when you are about to repeat a recommendation from your notes or from a summary, and when you write down what the person decided.
---

# Decide

A decision is made once and read many times. A wrong question to a person most often comes from asking before
reading: the answer was already in a record, or a record and the program disagreed and the session picked a side, or
the obvious choice was never offered. Each step below answers one of those. All of them come from one round in which
a session changed a manual to match the program, asked its person a question with two choices, repeated its own
recommendation five times from its notes, and found the better third choice only when the person asked why.

The command, in every step below, is `node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" decisions`.

## 1. Say the question, and its subject

Write the question in one sentence, in the words a person would use for what they see: the page, the word on it,
what happens next. Then choose the two or three words of its subject, such as `export failed`.

## 2. Look it up

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/run.mjs" decisions find <the words of the subject>
```

It lists every place where the words stand close together: the records of decisions first, then the other documents,
the tests, the code and the commit messages. It is a list of places and never an answer, so read each place in its
file, the whole entry and not only the line that is listed. Then:

- **Read the decision's own words.** When the list says that an entry "names a recommendation without saying it", the
  decision is not in the repository. Follow what the entry points to, a design page or a document outside the
  repository too. When that is out of your reach, tell the person that you could not read it, and ask for it. Never
  fill it in from memory or from a summary.
- **Read the commit that brought the behaviour.** The list names the commit that last wrote each line of the tests
  and the code; `git show <commit>` gives its message, which often says why.
- **A note in the memory is not the record.** The list gives the names of the notes that hold the words. A note may
  hold your own earlier recommendation without its reasons. Read the record.
- **Nothing in the records is a finding too.** The subject was never decided, or the records do not hold it. Say
  which.

`decisions records` prints the files taken as records. When the repository's own records are not among them, offer
to name them in `.claude/bowline.json`, under `decisions.records`.

## 3. When a record and the program disagree, edit neither

A sentence in a document may be the decision, and the program the mistake. Or the program is right and the document
is out of date. Or a test's name says one thing and its body asserts another. Until you know which one is the
mistake, neither side is the truth, and an edit that makes them agree hides the question from the person.

- **Find out.** What does the decision's entry say? Which was written first? Does the test assert what its name says?
- **Tell the person, before any edit.** Say what the program does and what each record says, each with its file and
  its line, and which side you take for the mistake, with your reason.
- **Then change only the side that is wrong.** A document that was wrong gets a dated note.
- **If you have already changed one side to match the other, say so** in the same report, and offer to put it back.

## 4. Find the nearest existing case

Before you write the choices, ask what the product already does in the most similar situation: the same kind of state
on another page, the sibling feature, the word that is used one screen away. "Do what it does there" is always one of
the choices, named with the place it comes from. The lookup cannot find the neighbour for you. Search for the
neighbour's own words, and read the code beside what you find.

## 5. Keep the mechanism apart from the wording

A reason about what the engine does, such as "it can still retry", is a reason for the mechanism. It is not a reason
for the word or the look that a person meets. When the question is about what a person reads, give reasons about
what a person reads, and say apart from them what the mechanism allows.

## 6. Write the question for the person

- **The real problem first**, in plain words, and then what a person would see with each choice.
- **Your recommendation first among the choices**, then the others, with what the product already does among them.
- **Each reason with its source**: the file and the line, the entry and its date, the commit. A reason that has no
  source is your own view; say so.
- **The strongest argument against your recommendation**, said as someone who holds it would say it.
- **What you did not check**, and what you could not read.
- **Whose words are whose.** The person's words go in quotation marks and are marked as theirs. An inference is
  marked as yours. Never write "the person's rule" for something the person did not say.
- **Say when your recommendation is also the smallest change to work you have just finished**, because that is when
  a recommendation is easiest to believe and least tested.

Then ask once.

## 7. While the question is open

Keep it where the repository keeps open questions: an entry marked open in the decisions section, the roadmap's item,
or the notes queue. Keep it with its choices, their reasons and the places you read. Never keep "I recommended this"
alone, in a record, in a memory note or in a status.

When the person asks again, or asks why, or the conversation was summarized since, do steps 2 to 6 again from the
record. A recommendation in your notes or in a summary is a conclusion without its evidence.

## 8. When the person answers

- **Write the entry in the round they answer**: the decision in a sentence that stands alone, their words in
  quotation marks, the cases it covers and the ones it leaves open, and where it shows.
- **"Approved as recommended" is never the entry.** Write what was recommended. When the person approves several
  things at once, write each one's own sentence.
- **Bring every place that states it into line**: the manual, the test's name and what the test asserts, the comment.
  A comment or a test that cites the decision names the entry, by its date and its first words.
- **Read it back** against what was said.

When the decision is about work that another session holds, `/bowline:collaborate` says who carries it out.

## What not to do

- Do not ask the person what the repository already answers.
- Do not make a record agree with the program, or the program agree with a record, to make a disagreement go away.
- Do not offer two choices where the product already shows a third.
- Do not repeat a recommendation. Work it out again, or say that nothing has changed since the evidence you name.
