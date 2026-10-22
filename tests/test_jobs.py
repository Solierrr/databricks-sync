import threading

import pytest

from app.errors import JobAlreadyRunning, SyncConfigurationError, SyncExecutionError
from app.services.jobs import JobManager


def test_completed_job_keeps_the_result_and_progress():
    manager = JobManager()

    def runner(progress):
        progress({"event": "source_started", "source": "DB_CORE", "tables": 2})
        progress({"event": "table_synced", "source": "DB_CORE", "table": "a", "rows": 5})
        progress({"event": "table_failed", "source": "DB_CORE", "table": "b"})
        return {"status": "completed"}

    job = manager.run_blocking(runner)

    assert job.status == "completed"
    assert job.result == {"status": "completed"}
    assert (job.progress.tables_total, job.progress.tables_synced, job.progress.tables_failed) == (2, 1, 1)
    assert job.progress.rows_synced == 5
    assert job.finished_at is not None
    assert manager.get(job.id) is job


def test_execution_error_keeps_the_summary():
    def runner(progress):
        raise SyncExecutionError({"status": "failed", "errors": []})

    job = JobManager().run_blocking(runner)

    assert job.status == "failed"
    assert job.result == {"status": "failed", "errors": []}


@pytest.mark.parametrize("error", [SyncConfigurationError("missing"), RuntimeError("boom")])
def test_other_errors_fail_the_job_with_a_message(error):
    def runner(progress):
        raise error

    job = JobManager().run_blocking(runner)

    assert job.status == "failed"
    assert job.result is None
    assert job.error == str(error)


def test_only_one_job_runs_at_a_time():
    manager = JobManager()
    release = threading.Event()
    started = threading.Event()

    def slow(progress):
        started.set()
        release.wait(5)
        return {"status": "completed"}

    first = manager.start(slow)
    assert started.wait(5)
    with pytest.raises(JobAlreadyRunning):
        manager.start(lambda progress: {})

    release.set()
    for _ in range(100):
        if first.status != "running":
            break
        threading.Event().wait(0.05)
    assert first.status == "completed"
    assert manager.run_blocking(lambda progress: {"status": "completed"}).status == "completed"


def test_history_is_bounded():
    manager = JobManager(max_history=2)
    jobs = [manager.run_blocking(lambda progress: {}) for _ in range(3)]

    assert manager.get(jobs[0].id) is None
    assert manager.get(jobs[2].id) is jobs[2]
