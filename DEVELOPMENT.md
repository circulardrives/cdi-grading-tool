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

### Running Tests
```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=cdi_health --cov-report=term-missing

# Specific test file
pytest tests/test_scoring.py

# Verbose output
pytest tests/ -v
```

### Writing Tests
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test classes `Test*`
- Name test methods `test_*`
- Use fixtures from `conftest.py` for common test data

### Test Coverage
- Aim for 80%+ coverage
- Critical paths should have 90%+ coverage
- Run `pytest --cov=cdi_health --cov-report=html` to view detailed coverage

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
│   └── watch.py            # Watch/monitoring mode
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

## Building and Distribution

### Build Package
```bash
python -m build
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

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
