# Testing Guide

This guide helps you test CDI Health functionality, including with mock data and real devices.

## Quick Start Testing

### Test with Mock Data (No Physical Devices Required)

```bash
# Basic scan with mock data
cdi-health scan --mock-data src/cdi_health/mock_data

# Scan specific mock device
cdi-health scan --mock-file src/cdi_health/mock_data/nvme/healthy_ssd.json

# Output as JSON
cdi-health scan --mock-data src/cdi_health/mock_data -o json

# Generate HTML report from mock data
cdi-health report --format html --mock-data src/cdi_health/mock_data
```

### Test with Real Devices

**Prerequisites:**
- Linux system with storage devices
- Required tools installed (see README.md)
- Appropriate permissions (may need sudo for some operations)

```bash
# Scan all devices
cdi-health scan

# Scan only NVMe devices
cdi-health scan --ignore-ata --ignore-scsi

# Scan specific device
cdi-health scan --device /dev/nvme0

# Output as CSV for analysis
cdi-health scan -o csv > drive_health.csv
```

## Testing Self-Test Functionality

### Check Device Support

First, verify your NVMe device supports self-test:

```bash
# Check if device supports self-test (look for bit 4 in OACS)
nvme id-ctrl /dev/nvme0 | grep -i oacs

# Or use the tool to check
cdi-health selftest --device /dev/nvme0 --status
```

### Run Self-Tests

```bash
# Run short self-tests on all supported devices (default)
cdi-health selftest

# Run extended self-test on specific device
cdi-health selftest --device /dev/nvme0 --type extended

# Check status of running test
cdi-health selftest --device /dev/nvme0 --status

# Wait for test to complete
cdi-health selftest --device /dev/nvme0 --wait
```

### Verify Results

After running a test, run the command again to see results:

```bash
# First run - starts tests
cdi-health selftest

# Second run - shows results from previous tests
cdi-health selftest
```

## Testing Output Formats

### Table Format (Default)
```bash
cdi-health scan --mock-data src/cdi_health/mock_data
```

### JSON Format
```bash
cdi-health scan --mock-data src/cdi_health/mock_data -o json | jq .
```

### CSV Format
```bash
cdi-health scan --mock-data src/cdi_health/mock_data -o csv
```

### YAML Format
```bash
cdi-health scan --mock-data src/cdi_health/mock_data -o yaml
```

## Testing Report Generation

```bash
# Generate HTML report
cdi-health report --format html --mock-data src/cdi_health/mock_data

# Generate PDF report (requires additional dependencies)
cdi-health report --format pdf --mock-data src/cdi_health/mock_data

# Custom output filename
cdi-health report --format html --output-file my_report.html --mock-data src/cdi_health/mock_data
```

## Testing Watch Mode

```bash
# Monitor every 60 seconds (default)
cdi-health watch --mock-data src/cdi_health/mock_data

# Monitor every 30 seconds
cdi-health watch --interval 30 --mock-data src/cdi_health/mock_data
```

## Testing Terminal Width Adaptation

Test how the output adapts to different terminal sizes:

```bash
# Narrow terminal (70 columns)
COLUMNS=70 cdi-health selftest

# Medium terminal (100 columns)
COLUMNS=100 cdi-health selftest

# Wide terminal (150 columns)
COLUMNS=150 cdi-health selftest
```

## Common Test Scenarios

### 1. Test All Commands with Mock Data
```bash
cdi-health scan --mock-data src/cdi_health/mock_data
cdi-health report --format html --mock-data src/cdi_health/mock_data
cdi-health watch --interval 5 --mock-data src/cdi_health/mock_data
```

### 2. Test Protocol Filtering
```bash
# Only ATA devices
cdi-health scan --ignore-nvme --ignore-scsi --mock-data src/cdi_health/mock_data

# Only NVMe devices
cdi-health scan --ignore-ata --ignore-scsi --mock-data src/cdi_health/mock_data

# Only SCSI devices
cdi-health scan --ignore-ata --ignore-nvme --mock-data src/cdi_health/mock_data
```

### 3. Test Error Handling
```bash
# Test with non-existent device
cdi-health scan --device /dev/nonexistent

# Test with invalid mock file
cdi-health scan --mock-file /path/to/invalid.json
```

## Troubleshooting

### Permission Issues
Some operations require root privileges:
```bash
# Try with sudo if needed
sudo cdi-health scan
sudo cdi-health selftest
```

### Missing Tools
If tools are missing, install them:
```bash
sudo apt install nvme-cli smartmontools sg3-utils
```

### Mock Data Not Found
Ensure you're running from the repository root:
```bash
cd /path/to/cdi-grading-tool
cdi-health scan --mock-data src/cdi_health/mock_data
```

## Reporting Issues

If you encounter issues during testing:

1. Check the [GitHub Issues](https://github.com/circulardrives/cdi-grading-tool/issues)
2. Include:
   - Command you ran
   - Error message
   - System information (OS, Python version)
   - Device information (if applicable)
