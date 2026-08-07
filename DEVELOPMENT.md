# Development Guide

This guide provides information for developers working on CDI Health.

## Code Quality Standards

### Type Hints
- All functions should have type hints
- Use `from __future__ import annotations` for forward references
- Use `typing` module for complex types

### Logging
- Use the logging system instead of `print()` statements
- Import logger: `from cdi_health.logger import get_logger`
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Code Style
- Follow PEP 8
- Use `ruff` for linting and formatting
- Line length: 100 characters
- Use double quotes for strings

### Documentation
- Use Google-style docstrings
- Document all public functions and classes
- Include parameter and return type information

## Testing

Continuous integration is defined in **`.github/workflows/ci.yml`** (pytest matrix on Python 3.10–3.13, pre-commit, dashboard lint/typecheck/build, wheel smoke, license headers). Install **`pip install -e '.[dev,api]'`** locally so FastAPI tests (`tests/test_api.py`) collect.

For manual/hardware QA with mock data or real devices, see **[TESTING.md](TESTING.md)**.

### Dashboard (frontend)

The technician UI is a Vite + React monorepo under `dashboard/` (bun + Turborepo). From repo root:

```bash
./scripts/start-local-mock.sh          # API + dashboard with mock data
# or manually:
cd dashboard && bun install && bun run dev
```

See [dashboard/README.md](dashboard/README.md) and [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md).

### Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=cdi_health --cov-report=term-missing

# Specific test file
pytest tests/test_scoring.py

# Specific test
pytest tests/test_scoring.py::TestHealthScoreCalculator::test_calculate_perfect_device

# Verbose output
pytest tests/ -v
```

Coverage is enforced via `--cov-fail-under` in `pyproject.toml` (and CI). Run `pytest --cov=cdi_health --cov-report=html` for a detailed HTML report; do not hardcode coverage percentages in docs.

### Test Structure

Tests are organized by component under `tests/`, including:

- `test_scoring.py` — health scoring
- `test_tools.py` — tool path detection and command execution
- `test_cli.py` — CLI argument parsing and command routing
- `test_api.py` — FastAPI HTTP tests
- `test_nvme_selftest.py` — NVMe self-test
- `test_formatter.py` / `test_selftest_formatter.py` — output formatters
- `test_integration.py` — end-to-end integration tests

Mock fixtures live in `src/cdi_health/mock_data/` (`ata/`, `nvme/`, `scsi/`, `scan_results/`).

### Writing Tests

- Place tests in `tests/`; name files `test_*.py`, classes `Test*`, methods `test_*`
- Use fixtures from `conftest.py` for common test data
- Mock external calls; keep each test independent

```python
from unittest.mock import MagicMock, patch

from cdi_health.classes.scoring import HealthScoreCalculator


class TestMyFeature:
    def test_basic_functionality(self) -> None:
        calculator = HealthScoreCalculator()
        result = calculator.calculate({...})
        assert result.score == 100


@patch("shutil.which")
def test_path_detection(mock_which: MagicMock) -> None:
    mock_which.return_value = "/usr/bin/tool"
```

### Debugging Failed Tests

1. Verbose: `pytest tests/ -v`
2. Short traceback: `pytest tests/ --tb=short`
3. Single test: `pytest tests/test_file.py::TestClass::test_method -v`
4. Debugger: `pytest --pdb`

### Docker stack (mock UI / API smoke)

```bash
./scripts/docker-up.sh --build
curl -s http://127.0.0.1:3000/api/cdi/api/v1/health
```

Stop: `docker compose -f deploy/docker/docker-compose.yml down`
## Tool Path Detection

### openSeaChest (Deb Package)
When installed via deb package, openSeaChest binaries are in `/usr/local/bin/`:
- `/usr/local/bin/openSeaChest_Basics`
- `/usr/local/bin/openSeaChest_SMART`

The tool automatically detects these via:
1. `shutil.which()` - checks PATH (includes `/usr/local/bin`)
2. Explicit path checking - checks `/usr/local/bin` directly
3. `whereis` command - fallback search
4. Tool name fallback - uses tool name if not found (will work from PATH at runtime)

### smartctl
Located via:
1. PATH check (`shutil.which`)
2. Standard paths (`/usr/sbin`, `/usr/bin`)
3. `whereis` fallback

### sg3-utils
Located via:
1. PATH check
2. Standard paths (`/usr/bin`, `/usr/sbin`)
3. `whereis` fallback

## Project Structure

```
src/cdi_health/
├── __init__.py              # Package initialization
├── __main__.py              # CLI entry point
├── cli.py                   # Command-line interface
├── constants.py             # Constants and enums
├── logger.py                # Logging configuration
├── classes/
│   ├── colors.py           # Terminal colors and symbols
│   ├── config.py           # Configuration management
│   ├── devices.py          # Device detection and parsing
│   ├── exceptions.py       # Custom exceptions
│   ├── formatter.py        # Output formatters
│   ├── helpers.py          # Helper functions
│   ├── mock.py             # Mock data handling
│   ├── nvme_selftest.py    # NVMe self-test support
│   ├── reporter.py         # Report generation
│   ├── scoring.py          # Health scoring algorithm
│   ├── selftest_formatter.py # Self-test result formatting
│   ├── tools.py            # External tool integration
│   ├── validation.py       # Data validation
├── config/
│   └── thresholds.yaml     # Default thresholds
└── mock_data/              # Mock device data for testing
```

## Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**
   - Write code following style guidelines
   - Add type hints
   - Use logging instead of print
   - Write tests

3. **Run tests**
   ```bash
   pytest tests/
   ```

4. **Check code quality**
   ```bash
   ruff check .
   ruff format .
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

## Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

Hooks will automatically:
- Run ruff linting
- Run ruff formatting
- Check for common issues

Mypy is registered as a **manual** pre-commit stage (the tree still has many typing errors). Run it with:

```bash
pre-commit run mypy --all-files --hook-stage manual
```

## Building and Distribution

### Build Package
```bash
python -m build
```

### Debian package (`.deb`)

Linux release packages are built in CI (see `.github/workflows/release.yml`) using **nfpm** and `nfpm.yaml`. Artifacts install `cdi-health` / `cdi-health-api` under `/usr/local/bin` and libraries under `/opt/cdi-health/lib`. Local experiments (on a Linux host with nfpm and the packaging script prerequisites) follow the same `nfpm` invocation documented in that workflow.

### Docker images (GHCR)

The same release workflow builds and pushes multi-arch images on each `v*` tag:

- `ghcr.io/circulardrives/cdi-health-api`
- `ghcr.io/circulardrives/cdi-health-dashboard`

Dockerfiles live under `deploy/docker/`. Pull requests build images in CI (amd64, no push) to catch Dockerfile regressions.

**Build locally:**

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

**Test published GHCR images (`latest`):**

```bash
CDI_VERSION=latest docker compose -f deploy/docker/docker-compose.ghcr.yml up -d
```

### Install in Development Mode
```bash
pip install -e .[dev]
```

### Create Release
1. Update version in git tags
2. Build: `python -m build`
3. Test installation: `pip install dist/cdi_health-*.whl`
4. Upload to PyPI: `twine upload dist/*`

## Debugging

### Enable Verbose Logging
```bash
cdi-health scan -v
```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test with Mock Data
```bash
cdi-health scan --mock-data src/cdi_health/mock_data
```

## Common Issues

### Import Errors
- Ensure package is installed: `pip install -e .`
- Check Python version: `python --version` (requires 3.10+)

### Tool Not Found
- Check if tool is in PATH: `which tool_name`
- For deb-installed tools, check `/usr/local/bin`
- Tool will fallback to name if path not found (works if in PATH)

### Tests Fail
- Run with verbose: `pytest tests/ -v`
- Check test output for details
- Ensure mock data exists

### Ruff format check fails after `pip install -e .`

Setuptools-scm generates `src/cdi_health/_version.py` (gitignored) during editable installs. If `ruff format --check` reports that file, run `ruff format src/cdi_health/_version.py` once, or format the whole tree with `ruff format .`.

### `python3 -m venv` fails (ensurepip)

On minimal Ubuntu/Debian images, install **`python3-venv`** (or the versioned package your distro suggests, e.g. `python3.12-venv`) so `venv` can bootstrap pip.

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
