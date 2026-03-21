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

import argparse
import os

ALLOW_NON_ROOT_ENV = "CDI_HEALTH_API_ALLOW_NON_ROOT"
API_TOKEN_ENV = "CDI_HEALTH_API_TOKEN"


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for local API daemon."""
    parser = argparse.ArgumentParser(
        prog="cdi-health-api",
        description="Run CDI Health local API backend (designed for technician dashboard integration).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8844, help="Bind port (default: 8844)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument(
        "--allow-non-root",
        action="store_true",
        help="Allow non-root mode for development/testing only",
    )
    parser.add_argument(
        "--api-token",
        metavar="TOKEN",
        help="Optional static API token (sent by client via X-API-Token header)",
    )
    return parser


def main() -> int:
    """Run uvicorn server for the CDI Health API."""
    parser = create_parser()
    args = parser.parse_args()

    if args.allow_non_root:
        os.environ[ALLOW_NON_ROOT_ENV] = "1"
    if args.api_token:
        os.environ[API_TOKEN_ENV] = args.api_token

    try:
        import uvicorn
    except ImportError as exc:
        parser.error("Missing API dependencies. Install with: pip install -e .[api]")
        raise SystemExit(2) from exc

    try:
        import fastapi  # noqa: F401
    except ImportError as exc:
        parser.error("Missing API dependencies. Install with: pip install -e .[api]")
        raise SystemExit(2) from exc

    uvicorn.run(
        "cdi_health.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
