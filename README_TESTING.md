# Testing Guide for Developers

This document provides comprehensive information about testing the CDI Health project.

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
pytest tests/ --cov=cdi_health --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_scoring.py
```

### Run Specific Test

```bash
pytest tests/test_scoring.py::TestHealthScoreCalculator::test_calculate_perfect_device
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

## Test Structure

Tests are organized by component:

- `test_scoring.py` - Health scoring algorithm tests
- `test_tools.py` - Tool path detection and command execution
- `test_logger.py` - Logging system tests
- `test_constants.py` - Constants and enums
- `test_formatter.py` - Output formatters (table, JSON, CSV, YAML)
- `test_selftest_formatter.py` - Self-test result formatting
- `test_cli.py` - CLI argument parsing and command routing
- `test_nvme_selftest.py` - NVMe self-test functionality
- `test_colors.py` - Color and symbol utilities
- `test_integration.py` - End-to-end integration tests

## Test Coverage

Current test coverage: **~39%**

Key areas with good coverage:

- Constants (100%)
- Logger (97%)
- Colors (90%)
- Formatters (79%)
- Scoring (65%)

Areas needing more coverage:

- CLI commands (20%)
- Device detection (1%)
- Mock data handling (33%)

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test`*
- Test methods: `test_*`

### Example Test Structure

```python
import pytest
from cdi_health.classes.scoring import HealthScoreCalculator

class TestMyFeature:
    """Test cases for my feature."""

    def test_basic_functionality(self) -> None:
        """Test basic functionality."""
        calculator = HealthScoreCalculator()
        result = calculator.calculate({...})
        assert result.score == 100
```

### Using Fixtures

```python
def test_with_mock_device(sample_nvme_device: dict) -> None:
    """Test using mock device fixture."""
    assert sample_nvme_device is not None
```

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

@patch("shutil.which")
def test_path_detection(mock_which: MagicMock) -> None:
    mock_which.return_value = "/usr/bin/tool"
    # Test code here
```

## Continuous Integration

Tests run automatically on:

- Push to main/develop branches
- Pull requests
- Multiple Python versions (3.10, 3.11, 3.12)

See `.github/workflows/ci.yml` for CI (pytest matrix, pre-commit, dashboard build, wheel smoke).

## Test Data

Mock data is located in `src/cdi_health/mock_data/`:

- `ata/` - ATA/SATA device mock data
- `nvme/` - NVMe device mock data
- `scsi/` - SCSI/SAS device mock data
- `scan_results/` - Complete scan result examples

## Common Test Scenarios

### Testing Scoring Logic

```python
def test_scoring_scenario():
    calculator = HealthScoreCalculator()
    device = {
        "transport_protocol": "NVME",
        "smart_status": "PASSED",
        # ... other fields
    }
    result = calculator.calculate(device)
    assert result.grade == "A"
```

### Testing Path Detection

```python
@patch("shutil.which")
def test_tool_detection(mock_which):
    mock_which.return_value = "/usr/local/bin/tool"
    # Test detection logic
```

### Testing Formatters

```python
def test_formatter():
    formatter = TableFormatter()
    result = formatter.format([device_dict])
    assert "Device" in result
```

## Debugging Failed Tests

1. Run with verbose output: `pytest tests/ -v`
2. Run with traceback: `pytest tests/ --tb=short`
3. Run single test: `pytest tests/test_file.py::TestClass::test_method -v`
4. Use `pytest --pdb` to drop into debugger on failure

## Coverage Goals

- Target: 80%+ coverage
- Critical paths: 90%+ coverage
- CLI commands: 60%+ coverage
- Device detection: 50%+ coverage

## Best Practices

1. **Test edge cases** - Empty inputs, None values, boundary conditions
2. **Test error handling** - Invalid inputs, missing dependencies
3. **Use fixtures** - Share common test data
4. **Mock external calls** - Don't depend on system state
5. **Test in isolation** - Each test should be independent
6. **Clear assertions** - Use descriptive assert messages
7. **Document tests** - Explain what each test validates

## Troubleshooting

### Cannot create a venv (`ensurepip` / `python3-venv`)

On some Linux images, `python3 -m venv .venv` fails until you install the venv module, e.g. `sudo apt install python3-venv` (or `python3.12-venv` matching your Python).

### Tests Fail with Import Errors

- Ensure package is installed: `pip install -e .[dev]`
- Check Python version: `python --version` (requires 3.10+)

### Mock Data Not Found

- Verify mock data directory exists
- Check path in test fixtures
- Ensure JSON files are valid

### Coverage Not Increasing

- Check that tests actually execute the code
- Verify coverage configuration in `pyproject.toml`
- Run with `--cov-report=html` to see detailed coverage
