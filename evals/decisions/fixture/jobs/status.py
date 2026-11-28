"""The word a job's page shows."""


def status_of(job):
    if job.import_error:
        return "Import failed"
    # A failed export keeps the job Running until a retry: the owner's decision of 2026-03-02.
    if job.failed_exports and job.can_retry:
        return "Running"
    if job.failed_exports:
        return "Failed"
    return "Done" if job.exports_done else "Running"
