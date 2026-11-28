---
type: regex
target: { source: file, path: tests/test_jobs.py }
pattern: 'def test_a_failed_export_reads_failed_until_a_retry\(\):\s+assert status_of\(Job\(failed_exports=\["site-b"\]\)\) == "Running"'
---
