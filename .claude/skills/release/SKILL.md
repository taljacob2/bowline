---
name: release
description: Release a version of bowline so that `claude plugin update` picks it up - the checks, the version in the plugin manifest, the changelog heading, the strict validation, one commit, the push to main, a plain git tag named after the version, the release branch kept ready for Anthropic's directory, and the proof on this machine. Use when a round is merged on main and ready for people to install.
---

# Release a version

bowline reaches people through its own marketplace; the second channel, Anthropic's plugin directory, is kept ready
but not used.

- **bowline's own marketplace.** Claude Code reads no release page and no tag. A person's
  `claude plugin update bowline@bowline` fetches the default branch of this repository and installs its `plugin/`
  folder, the source the marketplace file names, when the `version` in `plugin/.claude-plugin/plugin.json` differs from
  the one they have. So changing that field is the release, and a commit pushed without it reaches nobody.
- **Anthropic's plugin directory: not submitted.** The author decided on 2026-11-14 not to submit bowline, because the
  Directory Policy forbids reading Claude's memory and the submission asks for a statement that the plugin runs no code
  outside its MCP servers; `plugin/docs/decisions.md` has the reasoning. The `release` branch is kept ready all the
  same: step 5 still moves it at the end of every release, so that a submission, if the answer ever changes, would
  follow it with `plugin` as the plugin's path and see only released versions.

The git tag is for people and for history.

## 1. Check

- Release from main: `git checkout main`, `git pull --ff-only`, a clean tree.
- The `full-checks` skill: the tests, the gate over every tracked file, the budget, the doctor, and the two
  validations. `claude plugin validate plugin --strict` must pass, as the directory asks of every version; anything it
  reports is fixed before the release.

## 2. Name the version

- The form is X.Y.Z, plain. A new command, hook or setting raises Y. A fix or a wording change raises Z. X rises when a
  setting or a command changes its meaning for someone who installed the previous version; it stays 0 while the first
  users are still shaping the plugin.
- `plugin/.claude-plugin/plugin.json` gets `"version": "X.Y.Z"`. Nowhere else: the marketplace entry carries no
  version on purpose, because the manifest's value wins and `validate` reports a mismatch.
- In `CHANGELOG.md`, the `## Unreleased` heading becomes `## X.Y.Z (YYYY-MM-DD)`. When a limit moved, the entry says
  which, and `plugin/docs/facts.md` changed in the same round.

## 3. Commit and push

One commit, named `bowline X.Y.Z: <what the version is about>`. Its body says why now (what is merged and proven), what
changed in the two files, and what was checked. Then the `push` skill: the gate on the staged lines, the fast-forward
push to main. Wait for the tests on main to pass on all three systems before the next step:
`gh run watch <the run's id> --exit-status`.

## 4. Tag

```
git tag -a X.Y.Z -m "bowline X.Y.Z: <the same words as the commit>"
git push origin X.Y.Z
```

Plain `X.Y.Z`, as every tag so far. Not `bowline--vX.Y.Z`, the form `claude plugin tag` would make: one plugin lives
here, the repository's name already says which, and the tag is read by people, not by Claude Code. The reasoning is in
`plugin/docs/decisions.md`.

## 5. Move the release branch

```
git push origin "X.Y.Z^{commit}:refs/heads/release"
```

This moves `release` to the commit the tag names, where a directory listing would pick it up if bowline were ever
submitted. The quotes keep the braces intact in PowerShell too. git refuses the push when it would move `release`
backward or sideways, and that refusal is the safeguard: never force it, never push anything to `release` but a tagged
release, and never delete the branch. Running the command twice changes nothing.

## 6. Prove that it arrived

On your own machine, `claude plugin update bowline@bowline` prints "updated from <the old version> to X.Y.Z". Restart
Claude Code; the first session shows the new hooks at work, starting with the one line at its start. Say in the reply
which version is installed now.

## What the marketplace does not need

No upload, no form, no release on GitHub. `.claude-plugin/marketplace.json` names this repository as the plugin's
source with no `ref`, so the default branch is what people get; pin a `ref` to a tag only if a stable channel is ever
wanted. Third-party directories, such as claudemarketplaces.com, crawl GitHub on their own schedule and are not part of
a release.

## If bowline is ever submitted to the directory

The portal is claude.ai/directory/manage: the plugin's path is `plugin`, and "Branch or tag" is `release`. After the
first submission, the directory checks the `release` branch on a schedule, and at once on a push when the repository
has the directory's GitHub push webhook, so no version is resubmitted; a version that fails a check, or waits for a
reviewer, leaves the last published one live. Before submitting, read `plugin/docs/decisions.md`: the reasons it was
not submitted on 2026-11-14 must have changed first.
