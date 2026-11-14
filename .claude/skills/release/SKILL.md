---
name: release
description: Release a version of bowline so that `claude plugin update` and Anthropic's plugin directory pick it up - the checks, the version in the plugin manifest, the changelog heading, the strict validation, one commit, the push to main, a plain git tag named after the version, the release branch the directory follows, and the proof on this machine. Use when a round is merged on main and ready for people to install.
---

# Release a version

bowline reaches people through two channels, and a release feeds both.

- **bowline's own marketplace.** Claude Code reads no release page and no tag. A person's
  `claude plugin update bowline@bowline` fetches the default branch of this repository and installs its `plugin/`
  folder, the source the marketplace file names, when the `version` in `plugin/.claude-plugin/plugin.json` differs from
  the one they have. So changing that field is the release, and a commit pushed without it reaches nobody.
- **Anthropic's plugin directory.** It follows the `release` branch, not main, with `plugin` as the plugin's path, and
  checks every new commit there, scans it and, by default, has an Anthropic reviewer publish it. The `release` branch
  moves only at the end of a release (step 5), so the directory sees the released versions and nothing in between.
  Until a new version is published there, the directory keeps serving the last one.

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

This moves `release` to the commit the tag names, and Anthropic's directory picks it up from there. The quotes keep
the braces intact in PowerShell too. git refuses the push when it would move `release` backward or sideways, and that
refusal is the safeguard: never force it, never push anything to `release` but a tagged release, and never delete
the branch, because the directory's listing follows it. Running the command twice changes nothing.

## 6. Prove that it arrived

On your own machine, `claude plugin update bowline@bowline` prints "updated from <the old version> to X.Y.Z". Restart
Claude Code; the first session shows the new hooks at work, starting with the one line at its start. Say in the reply
which version is installed now. The directory's portal, claude.ai/directory/manage, lists the new commit on the
listing's Versions tab with the result of its checks; it goes live there when it is published.

## What the marketplace does not need

No upload, no form, no release on GitHub. `.claude-plugin/marketplace.json` names this repository as the plugin's
source with no `ref`, so the default branch is what people get; pin a `ref` to a tag only if a stable channel is ever
wanted. Third-party directories, such as claudemarketplaces.com, crawl GitHub on their own schedule and are not part of
a release.

## What the directory does not need

No resubmission. After the first submission, the directory checks the `release` branch on a schedule, and at once on
a push when the repository has the directory's GitHub push webhook. A version that fails a check, or waits for a
reviewer, leaves the last published one live. The portal is needed only when a version is held or a setting changes.
