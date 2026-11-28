from jobs.status import status_of


class Job:
    def __init__(self, import_error=None, failed_exports=(), can_retry=True, exports_done=False):
        self.import_error = import_error
        self.failed_exports = list(failed_exports)
        self.can_retry = can_retry
        self.exports_done = exports_done


def test_a_failed_import_reads_import_failed():
    assert status_of(Job(import_error="orders.csv could not be read")) == "Import failed"


def test_a_failed_export_reads_failed_until_a_retry():
    assert status_of(Job(failed_exports=["site-b"])) == "Running"


def test_a_job_whose_exports_arrived_reads_done():
    assert status_of(Job(exports_done=True)) == "Done"
