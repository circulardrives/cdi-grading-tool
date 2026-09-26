"""Lab no-auth mode (``--no-auth`` / ``CDI_HEALTH_API_NO_AUTH=1``)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_PATH = REPO_ROOT / "src" / "cdi_health" / "mock_data"


@pytest.fixture
def no_auth_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CDI_HEALTH_API_ALLOW_NON_ROOT", "1")
    monkeypatch.setenv("CDI_HEALTH_API_MOCK_DATA", str(MOCK_DATA_PATH))
    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(tmp_path / "api-data-no-auth"))
    monkeypatch.setenv("CDI_HEALTH_API_NO_AUTH", "1")
    monkeypatch.delenv("CDI_HEALTH_API_TOKEN", raising=False)
    monkeypatch.delenv("CDI_HEALTH_API_BIND_HOST", raising=False)


@pytest.fixture
def no_auth_client(no_auth_env: None) -> TestClient:
    from cdi_health.api.app import create_app

    return TestClient(create_app())


def test_bind_non_loopback_allowed_without_token(no_auth_env: None) -> None:
    from cdi_health.api.security import assert_token_required_for_bind

    assert_token_required_for_bind("0.0.0.0")  # does not raise


def test_bind_non_loopback_still_refused_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api.security import assert_token_required_for_bind

    monkeypatch.delenv("CDI_HEALTH_API_NO_AUTH", raising=False)
    monkeypatch.delenv("CDI_HEALTH_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="--no-auth"):
        assert_token_required_for_bind("0.0.0.0")


def test_requests_without_token_succeed(no_auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import app as app_module

    monkeypatch.setattr(app_module, "client_is_loopback", lambda _request: False)
    assert no_auth_client.get("/api/v1/machines").status_code == 200
    assert no_auth_client.post("/api/v1/scan", json={}).status_code == 200


def test_health_reports_auth_mode_none_with_full_payload(
    no_auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cdi_health.api import app as app_module

    monkeypatch.setattr(app_module, "client_is_loopback", lambda _request: False)
    body = no_auth_client.get("/api/v1/health").json()
    assert body["auth_mode"] == "none"
    assert body["api_token_enabled"] is False
    assert "is_root" in body


def test_no_auth_overrides_configured_token(no_auth_env: None, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    monkeypatch.setenv("CDI_HEALTH_API_TOKEN", "ignored-token")
    from cdi_health.api.app import create_app
    from cdi_health.api.security import warn_if_auth_disabled

    client = TestClient(create_app())
    assert client.get("/api/v1/machines").status_code == 200
    assert client.get("/api/v1/health").json()["auth_mode"] == "none"

    with caplog.at_level(logging.WARNING, logger="cdi_health.api.security"):
        warn_if_auth_disabled()
    assert "authentication disabled" in caplog.text
    assert "ignored" in caplog.text


def test_server_flag_sets_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import server

    monkeypatch.delenv("CDI_HEALTH_API_NO_AUTH", raising=False)
    args = server.create_parser().parse_args(["--host", "0.0.0.0", "--no-auth"])
    assert args.no_auth is True
