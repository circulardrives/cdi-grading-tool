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
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from cdi_health.api.discovery import DISCOVER_COOLDOWN_SECONDS, DiscoveryError, discover_hosts
from cdi_health.api.history import ScanHistoryStore
from cdi_health.api.jobs import JobStore
from cdi_health.api.machines import MachineStore
from cdi_health.api.remote import (
    RemoteAddressError,
    RemoteHostClient,
    RemoteHostError,
    forwarded_scan_body,
    remote_auth_mode,
)
from cdi_health.api.schemas import (
    DiscoverRequest,
    DiscoverResponse,
    FleetDevicesResponse,
    HealthResponse,
    HistoryDetail,
    HistorySummary,
    JobResponse,
    MachineCheckResponse,
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
    auth_mode,
    client_is_loopback,
    is_root_user,
    optional_api_token,
    verify_api_token,
    warn_if_auth_disabled,
)
from cdi_health.api.services import (
    abort_selftest,
    apply_scan_defaults,
    generate_report,
    get_selftest_status,
    http_error_detail,
    media_type_for_report,
    resolve_report_file,
    run_scan,
    run_selftest_start,
    weasyprint_available,
)
from cdi_health.cli import __version__ as PACKAGE_VERSION
from cdi_health.cli import check_prerequisites

logger = logging.getLogger(__name__)

SELFTEST_MAX_WORKERS = 2
# Max remote hosts scanned concurrently by GET /api/v1/fleet/devices?refresh=true.
FLEET_REFRESH_MAX_WORKERS = 4
LOCAL_HOST_NAME = "Local API"
SUMMARY_KEYS = ("total", "healthy", "warning", "failed", "ungraded")
# Report the installed cdi_health package version (setuptools-scm), same as `cdi-health --version`.
API_VERSION = PACKAGE_VERSION
HARDWARE_BUSY_DETAIL = "Drive hardware is busy with another scan, report, or self-test start. Retry when it completes."


class HardwareBusyError(Exception):
    """Raised when another operation already holds the drive hardware lock."""


class ApiState:
    """Shared runtime state for the CDI Health API process."""

    def __init__(self):
        self.job_store = JobStore()
        self.machine_store = MachineStore()
        self.history_store = ScanHistoryStore()
        # Only one scan / report / self-test start may touch drives at a time.
        # Busy callers get HTTP 409 instead of queueing (see hardware_session).
        self.hardware_lock = Lock()
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

    def try_acquire_hardware(self) -> bool:
        """Non-blocking acquire of the drive hardware lock."""
        return self.hardware_lock.acquire(blocking=False)

    @contextmanager
    def hardware_session(self) -> Iterator[None]:
        """Hold the hardware lock for the duration of the block, or raise HardwareBusyError."""
        if not self.try_acquire_hardware():
            raise HardwareBusyError(HARDWARE_BUSY_DETAIL)
        try:
            yield
        finally:
            self.hardware_lock.release()


def create_app() -> FastAPI:
    """Create and configure the CDI Health API application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        assert_root_access()
        warn_if_auth_disabled()
        # Defense in depth when launched outside server.main (e.g. uvicorn factory).
        bind_host = os.getenv(BIND_HOST_ENV)
        if bind_host:
            assert_token_required_for_bind(bind_host)
        try:
            yield
        finally:
            app.state.runtime.selftest_executor.shutdown(wait=False, cancel_futures=False)

    app = FastAPI(
        title="CDI Health API",
        version=API_VERSION,
        description="Local backend API for CDI drive scan, self-test, and reporting workflows.",
        lifespan=lifespan,
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

    @app.exception_handler(HardwareBusyError)
    def _hardware_busy(_request: Request, exc: HardwareBusyError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(RemoteHostError)
    def _remote_host_error(_request: Request, exc: RemoteHostError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

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
            # auth_mode lets discovering clients know a token is required.
            return HealthResponse(status="ok", version=API_VERSION, auth_mode="token")

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
            auth_mode=auth_mode(),
            missing_required_tools=missing_required_tools,
            weasyprint_available=weasyprint_available(),
            message=message,
        )

    def _persist_successful_scan(
        runtime: ApiState,
        result: dict,
        request: ScanRequest,
    ) -> None:
        """Cache latest scan, update host registry, and append scan history."""
        normalized = apply_scan_defaults(request)
        mock = bool(normalized.mock_data or normalized.mock_file)
        result["machine_id"] = request.machine_id
        result["executed_on"] = "local"
        with runtime.lock:
            runtime.latest_scan = result
            if request.machine_id:
                machine = runtime.machine_store.record_scan(request.machine_id, result, success=True)
                if machine is None:
                    raise HTTPException(status_code=404, detail="Machine not found")
        runtime.history_store.record_scan(
            result,
            machine_id=request.machine_id,
            mock=mock,
        )

    def _get_machine_or_404(machine_id: str) -> dict[str, Any]:
        machine = app.state.runtime.machine_store.get_machine(machine_id)
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        return machine

    def _is_remote(machine: dict[str, Any]) -> bool:
        return bool(str(machine.get("address") or "").strip())

    def _remote_client(machine: dict[str, Any]) -> RemoteHostClient:
        return RemoteHostClient(
            name=machine["name"],
            address=machine["address"],
            token=app.state.runtime.machine_store.get_api_token(machine["id"]),
        )

    def _forward_scan(machine: dict[str, Any], request: ScanRequest) -> dict[str, Any]:
        """Run a scan on a remote host and persist it like a local scan.

        The local hardware lock is not taken: the remote API serializes its
        own drive access (and answers 409 when busy).
        """
        runtime = app.state.runtime
        try:
            remote_result = _remote_client(machine).scan(forwarded_scan_body(request))
            remote_result = {
                **remote_result,
                "machine_id": machine["id"],
                "executed_on": "remote",
                "remote_address": machine["address"],
            }
            try:
                result = ScanResponse.model_validate(remote_result).model_dump(mode="json")
            except ValidationError as exc:
                raise RemoteHostError(
                    502,
                    f"Host '{machine['name']}' returned an invalid scan response",
                    "reachable",
                ) from exc
        except RemoteHostError as exc:
            if exc.machine_status:
                runtime.machine_store.set_status(machine["id"], exc.machine_status)
            raise

        # Remote results never replace runtime.latest_scan (this API's own drives).
        if runtime.machine_store.record_scan(machine["id"], result, success=True) is None:
            raise HTTPException(status_code=404, detail="Machine not found")
        runtime.history_store.record_scan(result, machine_id=machine["id"], mock=False)
        return result

    @app.post("/api/v1/scan", response_model=ScanResponse)
    def scan(request: ScanRequest, _: None = Depends(verify_api_token)) -> ScanResponse:
        runtime = app.state.runtime
        if request.machine_id:
            machine = _get_machine_or_404(request.machine_id)
            if _is_remote(machine):
                return ScanResponse.model_validate(_forward_scan(machine, request))
        try:
            with runtime.hardware_session():
                result = run_scan(request)
            _persist_successful_scan(runtime, result, request)
            return ScanResponse.model_validate(result)
        except (HTTPException, HardwareBusyError):
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
                    scan_request = ScanRequest(machine_id=machine_id)
                    machine = _get_machine_or_404(machine_id)
                    if _is_remote(machine):
                        return ScanResponse.model_validate(_forward_scan(machine, scan_request))
                    with runtime.hardware_session():
                        result = run_scan(scan_request)
                    _persist_successful_scan(runtime, result, scan_request)
                    return ScanResponse.model_validate(result)

                cached = runtime.machine_store.get_scan(machine_id)
                if cached is None:
                    raise HTTPException(status_code=404, detail="No scan cached for this host")
                return ScanResponse.model_validate(cached)

            with runtime.lock:
                cached = runtime.latest_scan
            if refresh or cached is None:
                scan_request = ScanRequest()
                with runtime.hardware_session():
                    result = run_scan(scan_request)
                _persist_successful_scan(runtime, result, scan_request)
                return ScanResponse.model_validate(result)
            return ScanResponse.model_validate(cached)
        except (HTTPException, HardwareBusyError, RemoteHostError):
            raise
        except Exception as exc:
            _raise_mapped(exc, context="devices")

    def _scan_summary(scan_result: dict[str, Any]) -> dict[str, int]:
        summary = scan_result.get("summary") or {}
        return {key: int(summary.get(key, 0) or 0) for key in SUMMARY_KEYS}

    def _refresh_remote_host(machine: dict[str, Any]) -> str | None:
        """Scan one remote host for the fleet view; return an error string or None."""
        try:
            _forward_scan(machine, ScanRequest(machine_id=machine["id"]))
            return None
        except RemoteHostError as exc:
            return exc.detail
        except HTTPException as exc:
            return str(exc.detail)
        except Exception:
            logger.exception("Fleet refresh of host %s failed", machine.get("id"))
            return f"Host '{machine['name']}' scan failed"

    @app.get("/api/v1/fleet/devices", response_model=FleetDevicesResponse)
    def fleet_devices(
        refresh: bool = False,
        _: None = Depends(verify_api_token),
    ) -> FleetDevicesResponse:
        """Aggregate the latest scan of every remote host (plus this API's own).

        ``refresh=true`` first rescans all remote hosts (at most
        FLEET_REFRESH_MAX_WORKERS at a time). Per-host failures are reported
        in ``hosts[].error`` and never fail the request; a host whose refresh
        failed still contributes its previous cached scan.
        """
        runtime = app.state.runtime
        remote_machines = [m for m in runtime.machine_store.list_machines() if _is_remote(m)]

        errors: dict[str, str] = {}
        if refresh and remote_machines:
            workers = min(FLEET_REFRESH_MAX_WORKERS, len(remote_machines))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cdi-fleet") as executor:
                for machine, error in zip(
                    remote_machines,
                    executor.map(_refresh_remote_host, remote_machines),
                ):
                    if error:
                        errors[machine["id"]] = error

        hosts: list[dict[str, Any]] = []
        devices: list[dict[str, Any]] = []
        totals = dict.fromkeys(SUMMARY_KEYS, 0)

        def _add_host(host: dict[str, Any], scan_result: dict[str, Any] | None) -> None:
            if scan_result:
                summary = _scan_summary(scan_result)
                host_devices = [d for d in scan_result.get("devices") or [] if isinstance(d, dict)]
                host.update(
                    scanned_at=scan_result.get("scanned_at"),
                    summary=summary,
                    device_count=len(host_devices),
                )
                for key in SUMMARY_KEYS:
                    totals[key] += summary[key]
                for device in host_devices:
                    devices.append(
                        {
                            **device,
                            "machine_id": host["machine_id"],
                            "machine_name": host["name"],
                            "host_address": host["address"],
                        }
                    )
            hosts.append(host)

        with runtime.lock:
            local_scan = runtime.latest_scan
        if local_scan and local_scan.get("devices"):
            _add_host(
                {
                    "machine_id": None,
                    "name": LOCAL_HOST_NAME,
                    "address": None,
                    "status": "reachable",
                    "error": None,
                    "executed_on": "local",
                },
                local_scan,
            )

        for listed in remote_machines:
            machine = runtime.machine_store.get_machine(listed["id"]) or listed
            _add_host(
                {
                    "machine_id": machine["id"],
                    "name": machine["name"],
                    "address": machine["address"],
                    "status": machine.get("status") or "unknown",
                    "error": errors.get(machine["id"]),
                    "executed_on": "remote",
                },
                runtime.machine_store.get_scan(machine["id"]),
            )

        return FleetDevicesResponse.model_validate(
            {
                "hosts": hosts,
                "devices": devices,
                "summary": totals,
                "generated_at": datetime.now(timezone.utc),
            }
        )

    @app.get("/api/v1/history", response_model=list[HistorySummary])
    def list_history(
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        machine_id: str | None = None,
        _: None = Depends(verify_api_token),
    ) -> list[HistorySummary]:
        entries = app.state.runtime.history_store.list_scans(
            limit=limit,
            offset=offset,
            machine_id=machine_id,
        )
        return [HistorySummary.model_validate(entry) for entry in entries]

    @app.get("/api/v1/history/{scan_id}", response_model=HistoryDetail)
    def get_history(
        scan_id: str,
        _: None = Depends(verify_api_token),
    ) -> HistoryDetail:
        entry = app.state.runtime.history_store.get_scan(scan_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Scan history entry not found")
        return HistoryDetail.model_validate(entry)

    @app.delete("/api/v1/history/{scan_id}")
    def delete_history(
        scan_id: str,
        _: None = Depends(verify_api_token),
    ) -> dict[str, object]:
        deleted = app.state.runtime.history_store.delete_scan(scan_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Scan history entry not found")
        return {"deleted": True, "id": scan_id}

    @app.delete("/api/v1/history")
    def clear_history(
        _: None = Depends(verify_api_token),
    ) -> dict[str, object]:
        deleted = app.state.runtime.history_store.clear_scans()
        return {"deleted": deleted}

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

    @app.post("/api/v1/machines/{machine_id}/check", response_model=MachineCheckResponse)
    def check_machine(machine_id: str, _: None = Depends(verify_api_token)) -> MachineCheckResponse:
        """Probe a remote host's API with its stored token and update its status.

        Reachability failures are reported in ``error`` (HTTP 200); only a
        missing machine (404) or an address that is missing / not on a private
        network (400) fail the request.
        """
        store = app.state.runtime.machine_store
        machine = _get_machine_or_404(machine_id)
        if not _is_remote(machine):
            raise HTTPException(status_code=400, detail="Machine has no remote address")

        health: dict[str, Any] | None = None
        error: str | None = None
        status = "reachable"
        try:
            client = _remote_client(machine)
            health = client.health()
            # A no-auth remote never answers 401, so auth_failed is only
            # possible when it enforces a token and ours is missing/wrong.
            client.verify_token()
        except RemoteAddressError:
            raise
        except RemoteHostError as exc:
            error = exc.detail
            status = exc.machine_status or "unreachable"

        version = health.get("version") if health else None
        remote_auth = "token" if status == "auth_failed" else remote_auth_mode(health)
        updated = store.set_status(
            machine_id,
            status,
            seen=health is not None,
            remote_version=str(version) if version else None,
            remote_auth=remote_auth,
        )
        return MachineCheckResponse.model_validate({"machine": updated or machine, "health": health, "error": error})

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
            # Only accept a job when a worker is free: a job queued behind
            # long wait-mode jobs would otherwise sit holding the hardware lock.
            if runtime.selftest_inflight >= SELFTEST_MAX_WORKERS:
                raise HTTPException(
                    status_code=503,
                    detail="Self-test worker pool is saturated. Retry later.",
                )
            # Hold the hardware lock from request acceptance until the job has
            # issued its start commands; wait-mode polling runs unlocked.
            if not runtime.try_acquire_hardware():
                raise HardwareBusyError(HARDWARE_BUSY_DETAIL)
            runtime.selftest_inflight += 1

        release_lock = Lock()
        released = False

        def _release_hardware() -> None:
            nonlocal released
            with release_lock:
                if not released:
                    released = True
                    runtime.hardware_lock.release()

        payload = request.model_dump(mode="python")

        def _run_job(job_id: str, request_payload: dict) -> None:
            runtime.job_store.start(job_id)
            try:
                parsed_request = SelfTestStartRequest.model_validate(request_payload)
                result = run_selftest_start(parsed_request, on_started=_release_hardware)
                runtime.job_store.complete(job_id, result)
            except Exception:
                logger.exception("Self-test job %s failed", job_id)
                runtime.job_store.fail(job_id, "Self-test job failed")
            finally:
                _release_hardware()
                with runtime.lock:
                    runtime.selftest_inflight = max(0, runtime.selftest_inflight - 1)

        try:
            job = runtime.job_store.create("selftest", payload=payload)
            runtime.selftest_executor.submit(_run_job, job.job_id, payload)
        except BaseException:
            _release_hardware()
            with runtime.lock:
                runtime.selftest_inflight = max(0, runtime.selftest_inflight - 1)
            raise
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
        runtime = app.state.runtime
        try:
            with runtime.hardware_session():
                result = generate_report(request)
            with runtime.lock:
                runtime.report_paths.add(result["output_file"])
            return ReportResponse.model_validate(result)
        except HardwareBusyError:
            raise
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
