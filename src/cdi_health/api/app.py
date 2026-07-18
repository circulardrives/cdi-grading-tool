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

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError

from cdi_health.api.discovery import DISCOVER_COOLDOWN_SECONDS, DiscoveryError, discover_hosts
from cdi_health.api.jobs import JobStore
from cdi_health.api.machines import MachineStore
from cdi_health.api.schemas import (
    DiscoverRequest,
    DiscoverResponse,
    HealthResponse,
    JobResponse,
    MachineCreate,
    MachineResponse,
    MachineUpdate,
    ReportRequest,
    ReportResponse,
    ScanRequest,
    ScanResponse,
    SelfTestAbortRequest,
    SelfTestStartRequest,
)
from cdi_health.api.security import (
    BIND_HOST_ENV,
    allow_non_root_mode,
    api_token_is_enabled,
    assert_root_access,
    assert_token_required_for_bind,
    client_is_loopback,
    is_root_user,
    optional_api_token,
    verify_api_token,
)
from cdi_health.api.services import (
    abort_selftest,
    generate_report,
    get_selftest_status,
    http_error_detail,
    media_type_for_report,
    resolve_report_file,
    run_scan,
    run_selftest_start,
    weasyprint_available,
)
from cdi_health.cli import check_prerequisites

logger = logging.getLogger(__name__)

SELFTEST_MAX_WORKERS = 2
SELFTEST_MAX_QUEUED = 4
API_VERSION = "1.0.0"


class ApiState:
    """Shared runtime state for the CDI Health API process."""

    def __init__(self):
        self.job_store = JobStore()
        self.machine_store = MachineStore()
        # General work (scan/report) — keep separate from long-running self-tests.
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cdi-api")
        self.selftest_executor = ThreadPoolExecutor(
            max_workers=SELFTEST_MAX_WORKERS,
            thread_name_prefix="cdi-selftest",
        )
        self.latest_scan: dict | None = None
        self.report_paths: set[str] = set()
        self.lock = Lock()
        self.last_discover_at: float | None = None
        self.discover_in_progress = False
        self.latest_discover: dict | None = None
        self.selftest_inflight = 0


def create_app() -> FastAPI:
    """Create and configure the CDI Health API application."""
    app = FastAPI(
        title="CDI Health API",
        version=API_VERSION,
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
        # Defense in depth when launched outside server.main (e.g. uvicorn factory).
        bind_host = os.getenv(BIND_HOST_ENV)
        if bind_host:
            assert_token_required_for_bind(bind_host)

    @app.on_event("shutdown")
    def _shutdown() -> None:
        app.state.runtime.executor.shutdown(wait=False, cancel_futures=False)
        app.state.runtime.selftest_executor.shutdown(wait=False, cancel_futures=False)

    def _raise_mapped(exc: Exception, *, context: str) -> None:
        status_code, detail = http_error_detail(exc, context=context)
        logger.exception("%s failed: %s", context, exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc

    @app.get("/api/v1/health", response_model=HealthResponse, response_model_exclude_none=True)
    def health(
        request: Request,
        token_ok: bool = Depends(optional_api_token),
    ) -> HealthResponse:
        # When token auth is enabled, unauthenticated (non-loopback) callers
        # get a minimal public payload only.
        if api_token_is_enabled() and not token_ok and not client_is_loopback(request):
            return HealthResponse(status="ok", version=API_VERSION)

        missing_required_tools = check_prerequisites(ignore_ata=False, ignore_nvme=False, ignore_scsi=False)
        message = None
        if not is_root_user() and allow_non_root_mode():
            message = "Running in non-root development mode."
        return HealthResponse(
            status="ok",
            version=API_VERSION,
            is_root=is_root_user(),
            allow_non_root_mode=allow_non_root_mode(),
            api_token_enabled=api_token_is_enabled(),
            missing_required_tools=missing_required_tools,
            weasyprint_available=weasyprint_available(),
            message=message,
        )

    @app.post("/api/v1/scan", response_model=ScanResponse)
    def scan(request: ScanRequest, _: None = Depends(verify_api_token)) -> ScanResponse:
        runtime = app.state.runtime
        try:
            result = run_scan(request)
            with runtime.lock:
                runtime.latest_scan = result
                if request.machine_id:
                    machine = runtime.machine_store.record_scan(request.machine_id, result, success=True)
                    if machine is None:
                        raise HTTPException(status_code=404, detail="Machine not found")
            return ScanResponse.model_validate(result)
        except HTTPException:
            raise
        except Exception as exc:
            _raise_mapped(exc, context="scan")

    @app.get("/api/v1/devices", response_model=ScanResponse)
    def devices(
        refresh: bool = False,
        machine_id: str | None = None,
        _: None = Depends(verify_api_token),
    ) -> ScanResponse:
        runtime = app.state.runtime
        try:
            if machine_id:
                if refresh:
                    result = run_scan(ScanRequest(machine_id=machine_id))
                    with runtime.lock:
                        runtime.latest_scan = result
                        machine = runtime.machine_store.record_scan(machine_id, result, success=True)
                        if machine is None:
                            raise HTTPException(status_code=404, detail="Machine not found")
                    return ScanResponse.model_validate(result)

                cached = runtime.machine_store.get_scan(machine_id)
                if cached is None:
                    raise HTTPException(status_code=404, detail="No scan cached for this host")
                return ScanResponse.model_validate(cached)

            with runtime.lock:
                cached = runtime.latest_scan
            if refresh or cached is None:
                result = run_scan(ScanRequest())
                with runtime.lock:
                    runtime.latest_scan = result
                return ScanResponse.model_validate(result)
            return ScanResponse.model_validate(cached)
        except HTTPException:
            raise
        except Exception as exc:
            _raise_mapped(exc, context="devices")

    @app.get("/api/v1/machines", response_model=list[MachineResponse])
    def list_machines(
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        _: None = Depends(verify_api_token),
    ) -> list[MachineResponse]:
        machines = app.state.runtime.machine_store.list_machines()
        page = machines[offset : offset + limit]
        return [MachineResponse.model_validate(machine) for machine in page]

    @app.post("/api/v1/machines", response_model=MachineResponse)
    def create_machine(
        request: MachineCreate,
        _: None = Depends(verify_api_token),
    ) -> MachineResponse:
        machine = app.state.runtime.machine_store.create_machine(request.model_dump())
        return MachineResponse.model_validate(machine)

    @app.get("/api/v1/machines/{machine_id}", response_model=MachineResponse)
    def get_machine(machine_id: str, _: None = Depends(verify_api_token)) -> MachineResponse:
        machine = app.state.runtime.machine_store.get_machine(machine_id)
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        return MachineResponse.model_validate(machine)

    @app.patch("/api/v1/machines/{machine_id}", response_model=MachineResponse)
    def update_machine(
        machine_id: str,
        request: MachineUpdate,
        _: None = Depends(verify_api_token),
    ) -> MachineResponse:
        updates = request.model_dump(exclude_unset=True)
        machine = app.state.runtime.machine_store.update_machine(machine_id, updates)
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        return MachineResponse.model_validate(machine)

    @app.delete("/api/v1/machines/{machine_id}")
    def delete_machine(machine_id: str, _: None = Depends(verify_api_token)) -> dict[str, bool]:
        deleted = app.state.runtime.machine_store.delete_machine(machine_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Machine not found")
        return {"deleted": True}

    def _run_discovery(request: DiscoverRequest) -> DiscoverResponse:
        runtime = app.state.runtime
        now = time.monotonic()
        with runtime.lock:
            if runtime.discover_in_progress:
                raise HTTPException(
                    status_code=429,
                    detail="Discovery already in progress. Retry shortly.",
                )
            if runtime.last_discover_at is not None:
                elapsed = now - runtime.last_discover_at
                if elapsed < DISCOVER_COOLDOWN_SECONDS:
                    retry_after = int(DISCOVER_COOLDOWN_SECONDS - elapsed) + 1
                    raise HTTPException(
                        status_code=429,
                        detail=f"Discovery rate limit exceeded. Retry in {retry_after}s.",
                    )
            runtime.discover_in_progress = True
            runtime.last_discover_at = now

        machines = runtime.machine_store.list_machines()
        try:
            result = discover_hosts(
                subnet=request.subnet,
                subnets=request.subnets,
                port=request.port,
                timeout_seconds=request.timeout_seconds,
                probe_token=request.probe_token,
                registered_machines=machines,
            )
            with runtime.lock:
                runtime.latest_discover = result
            return DiscoverResponse.model_validate(result)
        except DiscoveryError as exc:
            logger.info("Discovery rejected: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            with runtime.lock:
                runtime.discover_in_progress = False

    @app.get("/api/v1/discover", response_model=DiscoverResponse)
    def discover_get(
        _: None = Depends(verify_api_token),
    ) -> DiscoverResponse:
        """Return the cached last discovery result (no side effects)."""
        with app.state.runtime.lock:
            cached = app.state.runtime.latest_discover
        if cached is None:
            raise HTTPException(
                status_code=404,
                detail="No discovery result cached. POST /api/v1/discover to scan.",
            )
        return DiscoverResponse.model_validate(cached)

    @app.post("/api/v1/discover", response_model=DiscoverResponse)
    def discover_post(
        request: DiscoverRequest,
        _: None = Depends(verify_api_token),
    ) -> DiscoverResponse:
        return _run_discovery(request)

    @app.post("/api/v1/selftests", response_model=JobResponse)
    def start_selftests(request: SelfTestStartRequest, _: None = Depends(verify_api_token)) -> JobResponse:
        runtime = app.state.runtime
        with runtime.lock:
            if runtime.selftest_inflight >= SELFTEST_MAX_QUEUED:
                raise HTTPException(
                    status_code=503,
                    detail="Self-test worker pool is saturated. Retry later.",
                )
            runtime.selftest_inflight += 1

        payload = request.model_dump(mode="python")
        job = runtime.job_store.create("selftest", payload=payload)

        def _run_job(job_id: str, request_payload: dict) -> None:
            runtime.job_store.start(job_id)
            try:
                parsed_request = SelfTestStartRequest.model_validate(request_payload)
                result = run_selftest_start(parsed_request)
                runtime.job_store.complete(job_id, result)
            except Exception as exc:
                logger.exception("Self-test job %s failed", job_id)
                runtime.job_store.fail(job_id, "Self-test job failed")
            finally:
                with runtime.lock:
                    runtime.selftest_inflight = max(0, runtime.selftest_inflight - 1)

        runtime.selftest_executor.submit(_run_job, job.job_id, payload)
        return JobResponse.model_validate(job.to_dict())

    @app.get("/api/v1/selftests/status")
    def selftest_status(device: str | None = None, _: None = Depends(verify_api_token)) -> dict:
        try:
            if device is not None:
                # Re-validate via schema so injection attempts fail with 422/400.
                SelfTestAbortRequest(device=device)
            return get_selftest_status(device=device)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail="Invalid device path") from exc
        except Exception as exc:
            _raise_mapped(exc, context="self-test status")

    @app.post("/api/v1/selftests/abort")
    def selftest_abort(request: SelfTestAbortRequest, _: None = Depends(verify_api_token)) -> dict:
        try:
            return abort_selftest(request.device)
        except Exception as exc:
            _raise_mapped(exc, context="self-test abort")

    @app.get("/api/v1/jobs", response_model=list[JobResponse])
    def list_jobs(
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        _: None = Depends(verify_api_token),
    ) -> list[JobResponse]:
        jobs = [job.to_dict() for job in app.state.runtime.job_store.list(limit=limit, offset=offset)]
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
            with app.state.runtime.lock:
                app.state.runtime.report_paths.add(result["output_file"])
            return ReportResponse.model_validate(result)
        except Exception as exc:
            _raise_mapped(exc, context="report")

    @app.get("/api/v1/reports/{filename}")
    def download_report(
        filename: str,
        download: bool = False,
        _: None = Depends(verify_api_token),
    ) -> FileResponse:
        with app.state.runtime.lock:
            registered = set(app.state.runtime.report_paths)
        try:
            report_path = resolve_report_file(filename, registered_paths=registered)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        disposition = "attachment" if download else "inline"
        return FileResponse(
            path=str(report_path),
            media_type=media_type_for_report(filename),
            filename=filename,
            headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
        )

    return app
