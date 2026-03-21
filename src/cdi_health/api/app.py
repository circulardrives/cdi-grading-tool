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

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cdi_health.api.jobs import JobStore
from cdi_health.api.schemas import (
    HealthResponse,
    JobResponse,
    ReportRequest,
    ReportResponse,
    ScanRequest,
    ScanResponse,
    SelfTestAbortRequest,
    SelfTestStartRequest,
)
from cdi_health.api.security import (
    allow_non_root_mode,
    api_token_is_enabled,
    assert_root_access,
    is_root_user,
    verify_api_token,
)
from cdi_health.api.services import (
    abort_selftest,
    generate_report,
    get_selftest_status,
    run_scan,
    run_selftest_start,
)
from cdi_health.cli import check_prerequisites


class ApiState:
    """Shared runtime state for the CDI Health API process."""

    def __init__(self):
        self.job_store = JobStore()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cdi-api")
        self.latest_scan: dict | None = None
        self.lock = Lock()


def create_app() -> FastAPI:
    """Create and configure the CDI Health API application."""
    app = FastAPI(
        title="CDI Health API",
        version="1.0.0",
        description="Local backend API for CDI drive scan, self-test, and reporting workflows.",
    )
    app.state.runtime = ApiState()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        assert_root_access()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        app.state.runtime.executor.shutdown(wait=False, cancel_futures=False)

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        missing_required_tools = check_prerequisites(ignore_ata=False, ignore_nvme=False, ignore_scsi=False)
        message = None
        if not is_root_user() and allow_non_root_mode():
            message = "Running in non-root development mode."
        return HealthResponse(
            status="ok",
            is_root=is_root_user(),
            allow_non_root_mode=allow_non_root_mode(),
            api_token_enabled=api_token_is_enabled(),
            missing_required_tools=missing_required_tools,
            message=message,
        )

    @app.post("/api/v1/scan", response_model=ScanResponse)
    def scan(request: ScanRequest, _: None = Depends(verify_api_token)) -> ScanResponse:
        try:
            result = run_scan(request)
            with app.state.runtime.lock:
                app.state.runtime.latest_scan = result
            return ScanResponse.model_validate(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/v1/devices", response_model=ScanResponse)
    def devices(refresh: bool = False, _: None = Depends(verify_api_token)) -> ScanResponse:
        try:
            with app.state.runtime.lock:
                cached = app.state.runtime.latest_scan
            if refresh or cached is None:
                result = run_scan(ScanRequest())
                with app.state.runtime.lock:
                    app.state.runtime.latest_scan = result
                return ScanResponse.model_validate(result)
            return ScanResponse.model_validate(cached)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/v1/selftests", response_model=JobResponse)
    def start_selftests(request: SelfTestStartRequest, _: None = Depends(verify_api_token)) -> JobResponse:
        runtime = app.state.runtime
        payload = request.model_dump(mode="python")
        job = runtime.job_store.create("selftest", payload=payload)

        def _run_job(job_id: str, request_payload: dict) -> None:
            runtime.job_store.start(job_id)
            try:
                parsed_request = SelfTestStartRequest.model_validate(request_payload)
                result = run_selftest_start(parsed_request)
                runtime.job_store.complete(job_id, result)
            except Exception as exc:
                runtime.job_store.fail(job_id, str(exc))

        runtime.executor.submit(_run_job, job.job_id, payload)
        return JobResponse.model_validate(job.to_dict())

    @app.get("/api/v1/selftests/status")
    def selftest_status(device: str | None = None, _: None = Depends(verify_api_token)) -> dict:
        try:
            return get_selftest_status(device=device)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/v1/selftests/abort")
    def selftest_abort(request: SelfTestAbortRequest, _: None = Depends(verify_api_token)) -> dict:
        try:
            return abort_selftest(request.device)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/v1/jobs", response_model=list[JobResponse])
    def list_jobs(_: None = Depends(verify_api_token)) -> list[JobResponse]:
        jobs = [job.to_dict() for job in app.state.runtime.job_store.list()]
        return [JobResponse.model_validate(job) for job in jobs]

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str, _: None = Depends(verify_api_token)) -> JobResponse:
        job = app.state.runtime.job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse.model_validate(job.to_dict())

    @app.post("/api/v1/reports", response_model=ReportResponse)
    def report(request: ReportRequest, _: None = Depends(verify_api_token)) -> ReportResponse:
        try:
            result = generate_report(request)
            return ReportResponse.model_validate(result)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app

