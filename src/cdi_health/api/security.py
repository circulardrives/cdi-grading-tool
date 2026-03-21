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

import os

from fastapi import Header, HTTPException, status


ALLOW_NON_ROOT_ENV = "CDI_HEALTH_API_ALLOW_NON_ROOT"
API_TOKEN_ENV = "CDI_HEALTH_API_TOKEN"


def is_root_user() -> bool:
    """Return True if the current process is running as root."""
    return hasattr(os, "geteuid") and os.geteuid() == 0


def allow_non_root_mode() -> bool:
    """Allow non-root mode for local development/testing."""
    return os.getenv(ALLOW_NON_ROOT_ENV, "0") == "1"


def assert_root_access() -> None:
    """
    Ensure the backend process has root privileges.

    Real device operations rely on privileged access to block devices.
    """
    if is_root_user() or allow_non_root_mode():
        return

    raise PermissionError(
        "CDI Health API must run as root for real device operations. "
        f"Set {ALLOW_NON_ROOT_ENV}=1 for non-root development mode."
    )


def api_token_is_enabled() -> bool:
    """Return True when an API token is configured."""
    return bool(os.getenv(API_TOKEN_ENV))


def verify_api_token(x_api_token: str | None = Header(default=None, alias="X-API-Token")) -> None:
    """
    Optional header-based API token check for local dashboard/backend traffic.
    """
    expected = os.getenv(API_TOKEN_ENV)
    if not expected:
        return

    if x_api_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )

