# Design

## What a job is

A job has three stages: it imports its files, works on them, and exports the results to each of its targets. Each
stage has a word that the job's page shows.

## Decisions, and questions still open

- **A failed import says so (2026-01-15).** A job whose import failed reads "Import failed" on its page, with the
  file that could not be read beside it. The owner: "say what failed, not only that something did". Why: a person who
  sees only "Failed" has to open the log to learn which stage it was.
- **The job page, version 4 (2026-03-02).** The three open points of the job page are decided as the design page's
  version 4 recommends them; the roadmap's item 2 names them.
