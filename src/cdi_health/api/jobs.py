#
# Copyright (c) 2026 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

DEFAULT_JOB_TTL_SECONDS = 3600
DEFAULT_MAX_JOBS = 200


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class JobRecord:
    """In-memory representation of an asynchronous API job."""

    job_id: str
    job_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-ready dictionary."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
        }


class JobStore:
    """Thread-safe in-memory job registry with TTL and max-size eviction."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_JOB_TTL_SECONDS,
        max_jobs: int = DEFAULT_MAX_JOBS,
    ):
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()
        self.ttl_seconds = ttl_seconds
        self.max_jobs = max_jobs

    def _is_terminal(self, job: JobRecord) -> bool:
        return job.status in {"completed", "failed"}

    def _evict_locked(self) -> None:
        """Drop expired terminal jobs, then oldest terminal jobs over max size."""
        now = utc_now()
        ttl = timedelta(seconds=self.ttl_seconds)
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if self._is_terminal(job) and job.completed_at is not None and now - job.completed_at > ttl
        ]
        for job_id in expired:
            del self._jobs[job_id]

        if len(self._jobs) <= self.max_jobs:
            return

        terminal = sorted(
            (job for job in self._jobs.values() if self._is_terminal(job)),
            key=lambda j: j.completed_at or j.updated_at,
        )
        overflow = len(self._jobs) - self.max_jobs
        for job in terminal[:overflow]:
            del self._jobs[job.job_id]

    def create(self, job_type: str, payload: dict[str, Any] | None = None) -> JobRecord:
        """Create a new queued job."""
        now = utc_now()
        job = JobRecord(
            job_id=str(uuid4()),
            job_type=job_type,
            status="queued",
            created_at=now,
            updated_at=now,
            payload=payload or {},
        )
        with self._lock:
            self._evict_locked()
            self._jobs[job.job_id] = job
        return job

    def start(self, job_id: str) -> JobRecord:
        """Transition a queued job to running."""
        with self._lock:
            job = self._jobs[job_id]
            now = utc_now()
            job.status = "running"
            job.started_at = now
            job.updated_at = now
            return job

    def complete(self, job_id: str, result: dict[str, Any]) -> JobRecord:
        """Mark job as completed with result payload."""
        with self._lock:
            job = self._jobs[job_id]
            now = utc_now()
            job.status = "completed"
            job.result = result
            job.error = None
            job.updated_at = now
            job.completed_at = now
            self._evict_locked()
            return job

    def fail(self, job_id: str, error: str) -> JobRecord:
        """Mark job as failed with error string."""
        with self._lock:
            job = self._jobs[job_id]
            now = utc_now()
            job.status = "failed"
            job.error = error
            job.updated_at = now
            job.completed_at = now
            self._evict_locked()
            return job

    def get(self, job_id: str) -> JobRecord | None:
        """Get job by id."""
        with self._lock:
            self._evict_locked()
            return self._jobs.get(job_id)

    def list(self, *, limit: int | None = None, offset: int = 0) -> list[JobRecord]:
        """List jobs ordered by creation time descending, with optional pagination."""
        with self._lock:
            self._evict_locked()
            jobs = list(self._jobs.values())
        ordered = sorted(jobs, key=lambda j: j.created_at, reverse=True)
        if offset:
            ordered = ordered[offset:]
        if limit is not None:
            ordered = ordered[:limit]
        return ordered

    def active_count(self) -> int:
        """Return the number of queued or running jobs."""
        with self._lock:
            return sum(1 for job in self._jobs.values() if job.status in {"queued", "running"})
