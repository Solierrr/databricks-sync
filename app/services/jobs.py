import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime

from app.errors import JobAlreadyRunning, SyncConfigurationError, SyncExecutionError
from app.models import JobProgress

Runner = Callable[[Callable[[dict], None]], dict]


class Job:
    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.status = "running"
        self.created_at = datetime.now(UTC)
        self.finished_at: datetime | None = None
        self.progress = JobProgress()
        self.result: dict | None = None
        self.error: str | None = None

    def update(self, event: dict) -> None:
        kind = event.get("event")
        if kind == "source_started":
            self.progress.current_source = event["source"]
            self.progress.tables_total += event["tables"]
        elif kind == "table_synced":
            self.progress.tables_synced += 1
            self.progress.rows_synced += event["rows"]
        elif kind == "table_failed":
            self.progress.tables_failed += 1

    def execute(self, runner: Runner) -> None:
        try:
            self.result = runner(self.update)
            self.status = "completed"
        except SyncExecutionError as exc:
            self.result = exc.summary
            self.error = str(exc)
            self.status = "failed"
        except SyncConfigurationError as exc:
            self.error = str(exc)
            self.status = "failed"
        except Exception as exc:
            self.error = str(exc)
            self.status = "failed"
        finally:
            self.progress.current_source = None
            self.finished_at = datetime.now(UTC)


class JobManager:
    def __init__(self, max_history: int = 20) -> None:
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._active: Job | None = None
        self._max_history = max_history

    def _register(self) -> Job:
        with self._lock:
            if self._active is not None and self._active.status == "running":
                raise JobAlreadyRunning("A synchronization is already running")
            job = Job()
            self._active = job
            self._jobs[job.id] = job
            while len(self._jobs) > self._max_history:
                self._jobs.popitem(last=False)
            return job

    def start(self, runner: Runner) -> Job:
        job = self._register()
        threading.Thread(target=job.execute, args=(runner,), name=f"sync-{job.id}", daemon=True).start()
        return job

    def run_blocking(self, runner: Runner) -> Job:
        job = self._register()
        job.execute(runner)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)
