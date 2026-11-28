# Where a decision is written down

A decision that lives only in a conversation, a commit message or a session's memory is lost to the next reader. These
rules say where each kind goes, in the same round it is made.

- **A settled design question goes in the design document's decisions section.** When a discussion settles or narrows a
  real design question, add the entry without being asked: the decision and the reasoning behind it. Later readers need
  the why more than the what.
- **A deliberate scope cut gets a numbered slot in the roadmap.** When a round leaves out a concrete, understood piece
  of work, add it in the same round as a numbered item in the roadmap's Next list, placed where it should run. A gap
  with a name but no slot gets forgotten. Only ideas with no concrete shape yet belong under "Later".
- **A convention goes in the repository's instruction files**, a rule under `.claude/rules/` or a procedure under
  `.claude/skills/`, never only in a session's memory. Memory is personal and per machine; the next contributor, and
  the next machine, never see it.
- **Read a written decision back.** Before treating a decision as recorded, compare the text with what was said; watch
  for "confirmed" or "agreed" attached to what was really an inference. Then check it landed in every document that
  should reflect it.

## Before a question goes to the person

- **Look the subject up first.** Before you put a design question to the person, or settle one yourself, read what was
  decided about it (the decisions section, the roadmap, the commit that brought the behaviour, the comments and tests
  that name it), and find the nearest case the product already handles: its way is one of the choices.
  `/bowline:decide` is the procedure.
- **When a record and the program disagree, find which one is the mistake before you edit either.** A sentence in a
  document may be the decision and the program the mistake, or the document may be out of date. Tell the person what
  disagrees, and correct a document with a dated note only once you know that it is the one that is wrong.
