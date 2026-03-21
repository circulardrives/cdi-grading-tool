# Contributing to CDI Health

Thank you for your interest in contributing to CDI Health! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cdi-grading-tool.git
   cd cdi-grading-tool
   ```
3. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. **Install in development mode**:
   ```bash
   pip install -e .[dev]
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Linux (Debian/Ubuntu recommended)
- Required system tools:
  - `nvme-cli` - For NVMe device support
  - `smartmontools` - For SMART data collection
  - `sg3-utils` - Optional, for SCSI device support

### Code Style

This project uses:
- **Ruff** for linting and code formatting
- **Pre-commit hooks** for automatic checks

Before committing, run:
```bash
ruff check .
ruff format .
```

Or install pre-commit hooks:
```bash
pre-commit install
```

## Testing

### Using Mock Data

The project includes mock data for testing without physical devices:

```bash
# Test with mock data
cdi-health scan --mock-data src/cdi_health/mock_data

# Test specific mock device
cdi-health scan --mock-file src/cdi_health/mock_data/nvme/healthy_ssd.json
```

### Testing Self-Test Functionality

To test self-test functionality, you'll need NVMe devices that support self-test:

```bash
# Check if device supports self-test
nvme id-ctrl /dev/nvme0 | grep -i oacs

# Run self-test
cdi-health selftest --device /dev/nvme0
```

## Making Changes

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Test your changes**:
   - Run with mock data
   - Test on real devices if possible
   - Verify all commands work as expected

4. **Update documentation**:
   - Update README.md if adding new features
   - Update CHANGELOG.md with your changes
   - Add docstrings to new functions/classes

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** on GitHub

## Pull Request Guidelines

- **Clear description**: Explain what your PR does and why
- **Reference issues**: Link to any related issues
- **Test coverage**: Include tests if adding new features
- **Documentation**: Update relevant documentation
- **One feature per PR**: Keep PRs focused on a single feature or fix

## Code Structure

```
src/cdi_health/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── cli.py               # Command-line interface
├── constants.py         # Constants and enums
├── classes/             # Core classes
│   ├── devices.py       # Device detection and parsing
│   ├── scoring.py       # Health scoring algorithm
│   ├── formatter.py     # Output formatting
│   ├── nvme_selftest.py # NVMe self-test support
│   └── ...
├── config/              # Configuration files
│   └── thresholds.yaml # Default thresholds
└── mock_data/           # Mock device data for testing
```

## Questions?

If you have questions or need help, please:
- Open an issue on GitHub
- Check existing issues and discussions
- Review the documentation in `docs/`

Thank you for contributing to CDI Health!
