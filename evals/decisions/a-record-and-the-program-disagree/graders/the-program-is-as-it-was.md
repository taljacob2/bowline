---
type: regex
target: { source: file, path: jobs/status.py }
pattern: 'if job\.failed_exports and job\.can_retry:\s+return "Running"'
---
