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

"""
CDI Health CLI - Command Line Interface

Main entry point for the CDI Health Scanner tool.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from cdi_health.classes.colors import Colors
from cdi_health.classes.formatter import get_formatter
from cdi_health.logger import get_logger, setup_logging

if TYPE_CHECKING:
    from argparse import Namespace

logger = get_logger(__name__)


# Version - try to get from package metadata, fallback to _version
try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("cdi_health")
    except PackageNotFoundError:
        # Fallback to _version if package not installed (development mode)
        try:
            from cdi_health._version import __version__
        except ImportError:
            __version__ = "dev"
except ImportError:
    # Python < 3.8 fallback
    try:
        import pkg_resources

        __version__ = pkg_resources.get_distribution("cdi_health").version
    except Exception:
        try:
            from cdi_health._version import __version__
        except ImportError:
            __version__ = "dev"


# Required tools for real device scanning
REQUIRED_TOOLS = {
    "nvme": ["nvme", "smartctl"],  # NVMe requires both nvme and smartctl
    "ata": ["smartctl"],  # ATA can use smartctl (openSeaChest is optional)
    "scsi": ["sg_map26", "sg_turs"],
}

# Optional tools (warn if missing but don't fail)
OPTIONAL_TOOLS = {
    "ata": ["openSeaChest_Basics", "openSeaChest_SMART"],  # Optional for ATA
}

# Default required tools (always checked)
DEFAULT_REQUIRED_TOOLS = ["nvme", "smartctl"]


def check_prerequisites(ignore_ata=False, ignore_nvme=False, ignore_scsi=False) -> list[str]:
    """Check for required tools and return list of missing ones based on device types."""
    missing = []

    # Always check default required tools (nvme and smartctl)
    for tool in DEFAULT_REQUIRED_TOOLS:
        if not shutil.which(tool):
            missing.append(tool)

    # Check NVMe-specific tools if not ignoring NVMe (already checked above, but keep for clarity)
    if not ignore_nvme:
        for tool in REQUIRED_TOOLS["nvme"]:
            if tool not in DEFAULT_REQUIRED_TOOLS and not shutil.which(tool):
                missing.append(tool)

    # Check ATA tools if not ignoring ATA (smartctl is already checked above)
    if not ignore_ata:
        for tool in REQUIRED_TOOLS["ata"]:
            if tool not in DEFAULT_REQUIRED_TOOLS and not shutil.which(tool):
                missing.append(tool)
        # Note: openSeaChest tools are optional for ATA devices

    # Check SCSI tools if not ignoring SCSI
    if not ignore_scsi:
        for tool in REQUIRED_TOOLS["scsi"]:
            if tool not in DEFAULT_REQUIRED_TOOLS and not shutil.which(tool):
                missing.append(tool)

    return missing


def scan_devices_real(ignore_ata=False, ignore_nvme=False, ignore_scsi=False) -> list[dict]:
    """Scan real devices."""
    from cdi_health.classes.devices import Devices

    devices = Devices(
        ignore_ata=ignore_ata,
        ignore_nvme=ignore_nvme,
        ignore_scsi=ignore_scsi,
    )
    return devices.devices


def scan_devices_mock(mock_path: str, ignore_ata=False, ignore_nvme=False, ignore_scsi=False) -> list[dict]:
    """Scan mock devices from directory."""
    from cdi_health.classes.mock import MockDevices

    devices = MockDevices(
        mock_data_path=mock_path,
        ignore_ata=ignore_ata,
        ignore_nvme=ignore_nvme,
        ignore_scsi=ignore_scsi,
    )
    return devices.devices


def scan_single_mock(mock_file: str) -> list[dict]:
    """Scan single mock device from file."""
    from cdi_health.classes.mock import create_mock_device

    device = create_mock_device(json_file=mock_file)
    return [device.to_dict(pop=True)]


def cmd_scan(args: Namespace) -> int:
    """
    Execute scan command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Setup logging
    setup_logging(verbose=args.verbose, no_color=args.no_color)

    # Auto-detect color support unless explicitly set
    if args.no_color:
        Colors.disable()
    else:
        Colors.auto_detect()

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None

    # Check prerequisites for real device scanning
    if not mock_mode:
        missing = check_prerequisites(
            ignore_ata=args.ignore_ata,
            ignore_nvme=args.ignore_nvme,
            ignore_scsi=args.ignore_scsi,
        )
        if missing:
            logger.error("Required tools not found: %s", ", ".join(missing))
            logger.info("Please install them before scanning real devices.")
            return 1

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)
        logger.info("Loaded configuration from: %s", args.config)

    # Scan devices
    try:
        if args.mock_file:
            logger.debug("Loading mock device from: %s", args.mock_file)
            devices = scan_single_mock(args.mock_file)
            logger.info("Loaded mock device from: %s", args.mock_file)
        elif args.mock_data:
            logger.debug("Loading mock devices from: %s", args.mock_data)
            devices = scan_devices_mock(
                args.mock_data,
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
            logger.info("Loaded %d mock devices from: %s", len(devices), args.mock_data)
        else:
            devices = scan_devices_real(
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
            if args.verbose:
                print(f"Scanned {len(devices)} devices")
    except Exception as e:
        print(f"Error scanning devices: {e}", file=sys.stderr)
        return 1

    if not devices:
        print("No devices found.")
        return 0

    # Format output
    try:
        # Use detailed mode for table output by default (or if explicitly requested)
        if args.output == "table":
            formatter = get_formatter(args.output, detailed=True)
        else:
            formatter = get_formatter(args.output)
        output = formatter.format(devices)
        print(output)
    except ValueError as e:
        logger.error("Formatting error: %s", e)
        return 1

    return 0


def cmd_report(args: Namespace) -> int:
    """
    Execute report command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Setup logging
    setup_logging(verbose=args.verbose, no_color=args.no_color)

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None

    # Check prerequisites for real device scanning
    if not mock_mode:
        missing = check_prerequisites(
            ignore_ata=args.ignore_ata,
            ignore_nvme=args.ignore_nvme,
            ignore_scsi=args.ignore_scsi,
        )
        if missing:
            logger.error("Required tools not found: %s", ", ".join(missing))
            return 1

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)

    # Scan devices
    try:
        if args.mock_file:
            devices = scan_single_mock(args.mock_file)
        elif args.mock_data:
            devices = scan_devices_mock(
                args.mock_data,
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
        else:
            devices = scan_devices_real(
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
    except Exception as e:
        print(f"Error scanning devices: {e}", file=sys.stderr)
        return 1

    if not devices:
        print("No devices found.")
        return 0

    # Generate report
    from cdi_health.classes.reporter import ReportGenerator

    reporter = ReportGenerator()

    # Determine output file
    if args.output_file:
        output_path = args.output_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        ext = "html" if args.format == "html" else "pdf"
        output_path = f"cdi-report-{timestamp}.{ext}"

    try:
        if args.format == "html":
            reporter.generate_html(devices, output_path)
        else:
            reporter.generate_pdf(devices, output_path)

        logger.info("Report generated: %s", output_path)
    except Exception as e:
        logger.error("Error generating report: %s", e, exc_info=args.verbose)
        return 1

    return 0


def cmd_selftest(args: Namespace) -> int:
    """
    Execute self-test command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Setup logging
    setup_logging(verbose=args.verbose, no_color=args.no_color)

    import time

    from cdi_health.classes.devices import Device
    from cdi_health.classes.exceptions import CommandException
    from cdi_health.classes.nvme_selftest import NVMeSelfTest
    from cdi_health.classes.selftest_formatter import format_selftest_summary

    # If device specified, handle single device operations
    if args.device:
        device_path = args.device

        # Check if device is NVMe
        if not device_path.startswith("/dev/nvme"):
            logger.error("Self-test currently only supports NVMe devices")
            logger.error("Device %s is not an NVMe device", device_path)
            return 1

        try:
            selftest = NVMeSelfTest(device_path)

            # Check support
            if not selftest.is_supported():
                logger.error("Device %s does not support self-test", device_path)
                return 1

            # Handle status request
            if args.status:
                status = selftest.get_current_status()
                print(f"Self-Test Status for {device_path}:")
                print(f"  Current Operation: {status['status']}")
                print(f"  In Progress: {status['in_progress']}")

                entries = status.get("entries", [])
                if entries:
                    print(f"\nSelf-Test History ({len(entries)} entries):")
                    for i, entry in enumerate(entries[:10], 1):  # Show last 10
                        print(f"  {i}. {entry.get('type_string', 'Unknown')} - {entry.get('result_string', 'Unknown')}")
                else:
                    print("  No self-tests logged.")

                last_test = selftest.get_last_test_date()
                if last_test:
                    days = selftest.days_since_last_test()
                    print(f"\nLast Test: {last_test.strftime('%Y-%m-%d %H:%M:%S')} ({days} days ago)")
                else:
                    print("\nNo previous self-tests found.")

                failed = selftest.get_failed_tests()
                if failed:
                    logger.warning("%d failed self-test(s) found in last 90 days", len(failed))

                return 0

            # Handle abort request
            if args.abort:
                logger.info("Aborting self-test on %s", device_path)
                cmd = selftest.abort()
                if cmd.return_code == 0:
                    logger.info("Self-test aborted successfully")
                    return 0
                else:
                    error_msg = cmd.errors.decode("utf-8") if cmd.errors else "Unknown error"
                    logger.error("Error aborting self-test: %s", error_msg)
                    return 1

            # Execute self-test
            test_type = args.type
            logger.info("Starting %s self-test on %s", test_type, device_path)
            logger.info("Note: Extended tests may take several hours to complete")

            if test_type == "short":
                cmd = selftest.execute_short()
            else:
                cmd = selftest.execute_extended()

            if cmd.return_code == 0:
                logger.info("%s self-test started successfully", test_type.capitalize())
                if args.wait:
                    logger.info("Waiting for self-test to complete...")
                    logger.info("This may take a long time for extended tests")
                    # Poll for completion
                    while True:
                        time.sleep(30)  # Check every 30 seconds
                        status = selftest.get_current_status()
                        if not status["in_progress"]:
                            logger.info("Self-test completed")
                            # Check results
                            results = selftest.get_results()
                            entries = results.get("entries", [])
                            if entries:
                                latest = entries[0]
                                if latest.get("result", 0) == 0:
                                    logger.info("Self-test passed")
                                else:
                                    logger.error("Self-test failed: %s", latest.get("result_string", "Unknown"))
                            break
                else:
                    logger.info("Use 'cdi-health selftest --device %s --status' to check progress", device_path)
                return 0
            else:
                error_msg = cmd.errors.decode("utf-8") if cmd.errors else "Unknown error"
                logger.error("Error starting self-test: %s", error_msg)
                return 1

        except CommandException as e:
            logger.error("Command error: %s", e)
            return 1
        except Exception as e:
            logger.error("Unexpected error: %s", e, exc_info=args.verbose)
            return 1

    # No device specified - scan all NVMe devices and run tests
    try:
        # Find all NVMe devices that support self-test
        logger.debug("Scanning for NVMe devices...")

        supported_devices = NVMeSelfTest.find_supported_devices()

        if not supported_devices:
            logger.warning("No NVMe devices found")
            return 0

        # Filter to only supported devices
        testable_devices = [d for d in supported_devices if d["supported"]]

        if not testable_devices:
            logger.warning("No NVMe devices found that support self-test")
            logger.info("Devices found:")
            for dev in supported_devices:
                logger.info("  %s: Self-test not supported", dev["device"])
            return 0

        logger.info("Found %d device(s) that support self-test:", len(testable_devices))
        for dev in testable_devices:
            logger.info("  %s", dev["device"])

        # Get device information for summary
        results = []
        test_type = args.type

        # First, check all devices for existing test status/results
        devices_with_tests = []
        devices_without_tests = []

        for dev_info in testable_devices:
            device_path = dev_info["device"]
            handler = dev_info["handler"]

            # Get device model and serial info
            model = "Unknown"
            serial = "Unknown"
            try:
                # Try to get model and serial from nvme id-ctrl (try with sudo first)
                import subprocess

                for use_sudo in [True, False]:
                    sudo_prefix = ["sudo"] if use_sudo else []
                    result = subprocess.run(
                        sudo_prefix + ["nvme", "id-ctrl", device_path, "-o", "json"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        import json

                        data = json.loads(result.stdout)
                        model = data.get("mn", "Unknown").strip() or "Unknown"
                        serial = data.get("sn", "Unknown").strip() or "Unknown"
                        if model != "Unknown":
                            break
            except Exception:
                # Fallback: try Device class
                try:
                    device = Device(device_id=device_path)
                    model = device.model_number or "Unknown"
                    serial = device.serial_number or "Unknown"
                except Exception:
                    pass

            # Check for existing test status/results
            has_existing_test = False
            result = {
                "device": device_path,
                "model": model,
                "serial": serial,
                "supported": True,
                "test_type": test_type,
                "test_started": False,
                "test_completed": False,
                "test_passed": False,
                "test_failed": False,
                "test_in_progress": False,
                "test_error": None,
                "last_test_date": None,
            }

            try:
                # Get current status
                status = handler.get_current_status()
                result["test_in_progress"] = status.get("in_progress", False)

                # Check for recent test results
                test_results = handler.get_results()
                entries = test_results.get("entries", [])

                # If test is in progress, we have an existing test
                if result["test_in_progress"]:
                    has_existing_test = True
                    result["test_started"] = True
                    # Try to determine test type from status or entries
                    if entries:
                        latest = entries[0]
                        result["test_type"] = latest.get("type_string", test_type) or test_type
                    else:
                        # Check status string for test type
                        status_str = status.get("status", "")
                        if "short" in status_str.lower():
                            result["test_type"] = "short"
                        elif "extended" in status_str.lower():
                            result["test_type"] = "extended"
                        else:
                            result["test_type"] = test_type

                elif entries:
                    # Test has completed - get results from entries
                    latest = entries[0]
                    result["test_type"] = latest.get("type_string", test_type) or test_type
                    result["test_started"] = True
                    result["test_completed"] = True
                    has_existing_test = True

                    # Check result - filter to valid entries first
                    valid_entries = [e for e in entries if e.get("result") in (0, 1, 2) and e.get("type") in (1, 2)]
                    if valid_entries:
                        latest = valid_entries[0]
                        result_value = latest.get("result", -1)
                        if result_value == 0:
                            result["test_passed"] = True
                        elif result_value == 1:
                            result["test_failed"] = True
                        elif result_value == 2:
                            result["test_aborted"] = True

                    # Get last test date
                    last_test = handler.get_last_test_date()
                    if last_test:
                        result["last_test_date"] = last_test.strftime("%Y-%m-%d %H:%M")

            except Exception as e:
                logger.debug("Could not check status for %s: %s", device_path, e)

            # Categorize device based on whether it has existing tests
            if has_existing_test:
                devices_with_tests.append((dev_info, result))
            else:
                devices_without_tests.append((dev_info, result))

        # If we have existing tests, display those results instead of starting new ones
        if devices_with_tests:
            logger.info("Found %d device(s) with existing test results. Displaying results...", len(devices_with_tests))
            # Show brief message even without verbose
            in_progress_count = sum(1 for _, r in devices_with_tests if r.get("test_in_progress"))
            completed_count = sum(1 for _, r in devices_with_tests if r.get("test_completed"))
            if in_progress_count > 0:
                logger.info("Displaying status of %d in-progress test(s)...", in_progress_count)
            elif completed_count > 0:
                logger.info("Displaying results from %d completed test(s)...", completed_count)

            for dev_info, result in devices_with_tests:
                results.append(result)

        # Only start new tests if no existing tests found
        if not devices_with_tests and devices_without_tests:
            logger.info("Starting new %s self-tests on %d device(s)...", test_type, len(devices_without_tests))

            for dev_info, result in devices_without_tests:
                device_path = result["device"]
                handler = dev_info["handler"]

                # Execute self-test
                try:
                    if test_type == "short":
                        cmd = handler.execute_short()
                    else:
                        cmd = handler.execute_extended()

                    if cmd.return_code == 0:
                        result["test_started"] = True
                        result["test_in_progress"] = True
                        logger.debug("Test started on %s", device_path)
                    else:
                        error_msg = cmd.errors.decode("utf-8") if cmd.errors else "Unknown error"
                        # Check if error is "already in progress"
                        if "in progress" in error_msg.lower() or "0x411d" in error_msg:
                            result["test_started"] = True
                            result["test_in_progress"] = True
                            logger.debug("Test already in progress on %s", device_path)
                        else:
                            result["test_error"] = error_msg
                            logger.warning("Failed to start test on %s: %s", device_path, error_msg)
                except Exception as e:
                    result["test_error"] = str(e)
                    logger.error("Error on %s: %s", device_path, e, exc_info=args.verbose)

                results.append(result)
        elif devices_without_tests:
            # Add devices without tests to results (for display)
            for dev_info, result in devices_without_tests:
                results.append(result)

        # Add devices that don't support self-test to results
        for dev_info in supported_devices:
            if not dev_info["supported"]:
                model = "Unknown"
                serial = "Unknown"
                try:
                    # Try to get model and serial from nvme id-ctrl (try with sudo first)
                    import subprocess

                    for use_sudo in [True, False]:
                        sudo_prefix = ["sudo"] if use_sudo else []
                        result = subprocess.run(
                            sudo_prefix + ["nvme", "id-ctrl", dev_info["device"], "-o", "json"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if result.returncode == 0:
                            import json

                            data = json.loads(result.stdout)
                            model = data.get("mn", "Unknown").strip() or "Unknown"
                            serial = data.get("sn", "Unknown").strip() or "Unknown"
                            if model != "Unknown":
                                break
                except Exception:
                    # Fallback: try Device class
                    try:
                        device = Device(device_id=dev_info["device"])
                        model = device.model_number or "Unknown"
                        serial = device.serial_number or "Unknown"
                    except Exception:
                        pass

                results.append(
                    {
                        "device": dev_info["device"],
                        "model": model,
                        "serial": serial,
                        "supported": False,
                        "test_type": "-",
                        "test_started": False,
                        "test_completed": False,
                        "test_passed": False,
                        "test_failed": False,
                        "test_in_progress": False,
                        "test_error": None,
                        "last_test_date": None,
                    }
                )

        # Print summary based on output format
        output_format = getattr(args, "output", "table")

        if output_format == "json":
            import json as json_lib

            # Remove ANSI codes and format as JSON
            json_results = []
            for r in results:
                json_result = {
                    "device": r.get("device"),
                    "model": r.get("model"),
                    "serial": r.get("serial", "Unknown"),
                    "supported": r.get("supported", False),
                    "test_started": r.get("test_started", False),
                    "test_completed": r.get("test_completed", False),
                    "test_passed": r.get("test_passed", False),
                    "test_failed": r.get("test_failed", False),
                    "test_aborted": r.get("test_aborted", False),
                    "test_in_progress": r.get("test_in_progress", False),
                    "test_type": r.get("test_type"),
                    "test_error": r.get("test_error"),
                    "last_test_date": r.get("last_test_date"),
                }
                json_results.append(json_result)
            print(json_lib.dumps(json_results, indent=2))
        elif output_format == "csv":
            import csv as csv_lib
            import io

            output_buffer = io.StringIO()
            fieldnames = [
                "device",
                "model",
                "serial",
                "supported",
                "test_status",
                "test_result",
                "test_type",
                "last_test_date",
            ]
            writer = csv_lib.DictWriter(output_buffer, fieldnames=fieldnames)
            writer.writeheader()

            for r in results:
                # Determine test status
                if r.get("test_in_progress"):
                    test_status = "Running"
                elif r.get("test_completed"):
                    test_status = "Complete"
                elif r.get("test_started"):
                    test_status = "Started"
                elif r.get("test_error"):
                    test_status = "Error"
                elif r.get("supported"):
                    test_status = "Ready"
                else:
                    test_status = "Not Supported"

                # Determine test result
                if r.get("test_passed"):
                    test_result = "Passed"
                elif r.get("test_failed"):
                    test_result = "Failed"
                elif r.get("test_aborted"):
                    test_result = "Aborted"
                else:
                    test_result = "-"

                writer.writerow(
                    {
                        "device": r.get("device", ""),
                        "model": r.get("model", "Unknown"),
                        "serial": r.get("serial", "Unknown"),
                        "supported": "Yes" if r.get("supported") else "No",
                        "test_status": test_status,
                        "test_result": test_result,
                        "test_type": r.get("test_type", "-"),
                        "last_test_date": r.get("last_test_date", "-"),
                    }
                )

            print(output_buffer.getvalue())
        else:
            # Default table format
            print(format_selftest_summary(results))

        # If wait requested, poll for completion
        if args.wait:
            logger.info("Waiting for self-tests to complete...")
            logger.info("Short tests typically take 1-2 minutes. Extended tests may take hours.")
            logger.info("Checking status every 30 seconds...")

            start_time = time.time()
            check_count = 0

            while True:
                time.sleep(30)  # Check every 30 seconds
                check_count += 1
                elapsed = int(time.time() - start_time)

                all_complete = True
                in_progress_count = 0

                for result in results:
                    if result.get("test_started") and not result.get("test_completed"):
                        try:
                            handler = NVMeSelfTest(result["device"])
                            status = handler.get_current_status()
                            if not status.get("in_progress", False):
                                result["test_completed"] = True
                                result["test_in_progress"] = False

                                # Check result - try multiple times as log may take time to update
                                import time

                                time.sleep(1)  # Give log page time to update

                                test_results = handler.get_results()
                                entries = test_results.get("entries", [])

                                # If no entries yet, try once more after a short delay
                                if not entries:
                                    time.sleep(2)
                                    test_results = handler.get_results()
                                    entries = test_results.get("entries", [])

                                if entries:
                                    latest = entries[0]
                                    result_value = latest.get("result", -1)
                                    if result_value == 0:
                                        result["test_passed"] = True
                                    elif result_value == 1:
                                        result["test_failed"] = True
                                    elif result_value == 2:
                                        result["test_aborted"] = True
                                else:
                                    # No entries found - assume passed if test completed without error
                                    # (Some drives may not populate log immediately)
                                    logger.debug("No log entries found for %s, assuming passed", result["device"])
                                    result["test_passed"] = True  # Optimistic assumption
                            else:
                                all_complete = False
                                in_progress_count += 1
                        except Exception as e:
                            logger.debug("Error checking status: %s", e)
                    elif result.get("test_started"):
                        # Already completed
                        pass
                    else:
                        # Not started, skip
                        pass

                # Show progress every check
                if in_progress_count > 0:
                    logger.info(
                        "Still waiting... %d test(s) in progress (elapsed: %dm %ds)",
                        in_progress_count,
                        elapsed // 60,
                        elapsed % 60,
                    )

                if all_complete:
                    logger.info("All self-tests completed!")
                    break

            # Print final summary
            # Print final summary based on output format
            output_format = getattr(args, "output", "table")

            if output_format == "json":
                import json as json_lib

                json_results = []
                for r in results:
                    json_result = {
                        "device": r.get("device"),
                        "model": r.get("model"),
                        "serial": r.get("serial", "Unknown"),
                        "supported": r.get("supported", False),
                        "test_started": r.get("test_started", False),
                        "test_completed": r.get("test_completed", False),
                        "test_passed": r.get("test_passed", False),
                        "test_failed": r.get("test_failed", False),
                        "test_aborted": r.get("test_aborted", False),
                        "test_in_progress": r.get("test_in_progress", False),
                        "test_type": r.get("test_type"),
                        "test_error": r.get("test_error"),
                        "last_test_date": r.get("last_test_date"),
                    }
                    json_results.append(json_result)
                print("\n" + json_lib.dumps(json_results, indent=2))
            elif output_format == "csv":
                import csv as csv_lib
                import io

                output_buffer = io.StringIO()
                fieldnames = [
                    "device",
                    "model",
                    "serial",
                    "supported",
                    "test_status",
                    "test_result",
                    "test_type",
                    "last_test_date",
                ]
                writer = csv_lib.DictWriter(output_buffer, fieldnames=fieldnames)
                writer.writeheader()

                for r in results:
                    if r.get("test_in_progress"):
                        test_status = "Running"
                    elif r.get("test_completed"):
                        test_status = "Complete"
                    elif r.get("test_started"):
                        test_status = "Started"
                    elif r.get("test_error"):
                        test_status = "Error"
                    elif r.get("supported"):
                        test_status = "Ready"
                    else:
                        test_status = "Not Supported"

                    if r.get("test_passed"):
                        test_result = "Passed"
                    elif r.get("test_failed"):
                        test_result = "Failed"
                    elif r.get("test_aborted"):
                        test_result = "Aborted"
                    else:
                        test_result = "-"

                    writer.writerow(
                        {
                            "device": r.get("device", ""),
                            "model": r.get("model", "Unknown"),
                            "serial": r.get("serial", "Unknown"),
                            "supported": "Yes" if r.get("supported") else "No",
                            "test_status": test_status,
                            "test_result": test_result,
                            "test_type": r.get("test_type", "-"),
                            "last_test_date": r.get("last_test_date", "-"),
                        }
                    )

                print("\n" + output_buffer.getvalue())
            else:
                print("\n" + format_selftest_summary(results))
        else:
            # Not waiting - show helpful message
            logger.info("Self-tests started. Use 'cdi-health selftest --wait' to wait for completion,")
            logger.info("or run 'cdi-health selftest' again to check status.")
            logger.info("Short tests typically complete in 1-2 minutes.")

        return 0

    except Exception as e:
        logger.error("Error: %s", e, exc_info=args.verbose)
        return 1


def cmd_watch(args: Namespace) -> int:
    """
    Execute watch command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Setup logging
    setup_logging(verbose=args.verbose, no_color=args.no_color)
    from cdi_health.classes.watch import WatchMode

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None
    mock_path = args.mock_data or args.mock_file

    # Check prerequisites for real device scanning
    if not mock_mode:
        missing = check_prerequisites(
            ignore_ata=args.ignore_ata,
            ignore_nvme=args.ignore_nvme,
            ignore_scsi=args.ignore_scsi,
        )
        if missing:
            print("Error: Required tools not found:", file=sys.stderr)
            for tool in missing:
                print(f"  - {tool}", file=sys.stderr)
            return 1

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)

    watch = WatchMode(
        interval=args.interval,
        mock_mode=mock_mode,
        mock_data_path=mock_path,
    )

    watch.start()
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser."""
    # Global options
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed information",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Path to YAML config file for custom thresholds",
    )

    # Mock mode options
    parser.add_argument(
        "--mock-data",
        metavar="PATH",
        help="Use mock data directory instead of real devices",
    )
    parser.add_argument(
        "--mock-file",
        metavar="FILE",
        help="Use specific mock JSON file for single device",
    )

    # Device filtering
    parser.add_argument(
        "--ignore-ata",
        action="store_true",
        help="Ignore ATA devices",
    )
    parser.add_argument(
        "--ignore-nvme",
        action="store_true",
        help="Ignore NVMe devices",
    )
    parser.add_argument(
        "--ignore-scsi",
        action="store_true",
        help="Ignore SCSI devices",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="cdi-health",
        description="CDI Health Scanner - Storage Device Health Assessment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all devices (default: table output)
  cdi-health scan

  # Scan with JSON output
  cdi-health scan -o json

  # Test with mock data
  cdi-health scan --mock-data src/cdi_health/mock_data

  # Generate HTML report
  cdi-health report --format html --mock-data src/cdi_health/mock_data

  # Continuous monitoring
  cdi-health watch --interval 30
""",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan and display drive health (default)",
        description="Scan storage devices and display health information.",
    )
    add_common_arguments(scan_parser)
    scan_parser.add_argument(
        "-o",
        "--output",
        choices=["table", "json", "csv", "yaml"],
        default="table",
        help="Output format (default: table)",
    )
    scan_parser.add_argument(
        "--all",
        action="store_true",
        help="Show all device attributes (not just summary)",
    )
    scan_parser.add_argument(
        "--details",
        action="store_true",
        help="Show detailed table with critical stats (power on hours, errors, percentage used)",
    )
    scan_parser.add_argument(
        "--device",
        metavar="PATH",
        help="Scan specific device only",
    )

    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate detailed health report",
        description="Generate a detailed HTML or PDF health report.",
    )
    add_common_arguments(report_parser)
    report_parser.add_argument(
        "--format",
        choices=["html", "pdf"],
        default="html",
        help="Report format (default: html)",
    )
    report_parser.add_argument(
        "--output-file",
        metavar="PATH",
        help="Output file path (default: cdi-report-{timestamp}.html)",
    )

    # Watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Continuous monitoring mode",
        description="Continuously monitor device health and report changes.",
    )
    add_common_arguments(watch_parser)
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="N",
        help="Seconds between scans (default: 60)",
    )

    # Self-test command
    selftest_parser = subparsers.add_parser(
        "selftest",
        help="Run device self-tests",
        description="Execute and manage device self-tests (NVMe only). By default, finds all NVMe devices that support self-test and runs short tests.",
    )
    add_common_arguments(selftest_parser)  # Add verbose, no-color, etc.
    selftest_parser.add_argument(
        "--device",
        metavar="PATH",
        help="Specific device to test (e.g., /dev/nvme0). If not specified, tests all supported NVMe devices.",
    )
    selftest_parser.add_argument(
        "--type",
        choices=["short", "extended"],
        default="short",
        help="Self-test type (default: short)",
    )
    selftest_parser.add_argument(
        "--abort",
        action="store_true",
        help="Abort running self-test (requires --device)",
    )
    selftest_parser.add_argument(
        "--status",
        action="store_true",
        help="Show self-test status and history (requires --device)",
    )
    selftest_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for self-test to complete (extended tests may take hours)",
    )
    selftest_parser.add_argument(
        "-o",
        "--output",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()

    # Handle no arguments - show help or run scan
    if len(sys.argv) == 1:
        # Default to scan command with table output
        sys.argv.append("scan")

    args = parser.parse_args()

    # Copy global args to command-specific namespace if needed
    if not hasattr(args, "ignore_ata"):
        args.ignore_ata = False
    if not hasattr(args, "ignore_nvme"):
        args.ignore_nvme = False
    if not hasattr(args, "ignore_scsi"):
        args.ignore_scsi = False

    # Execute command
    if args.command == "scan" or args.command is None:
        # Default output format for scan
        if not hasattr(args, "output"):
            args.output = "table"
        return cmd_scan(args)
    elif args.command == "report":
        return cmd_report(args)
    elif args.command == "watch":
        return cmd_watch(args)
    elif args.command == "selftest":
        return cmd_selftest(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
