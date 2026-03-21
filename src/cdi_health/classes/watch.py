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
Continuous Monitoring (Watch Mode) for CDI Health

Provides continuous monitoring of device health with change detection.
"""

from __future__ import annotations

import json
import signal
import sys
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any


class DeviceStateChange:
    """Represents a change in device state between scans."""

    def __init__(
        self,
        device_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        timestamp: datetime = None,
    ):
        """
        Initialize a device state change.

        :param device_id: Device identifier
        :param field: Field that changed
        :param old_value: Previous value
        :param new_value: New value
        :param timestamp: When the change was detected
        """
        self.device_id = device_id
        self.field = field
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = timestamp or datetime.now()

    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.device_id} - {self.field}: {self.old_value} -> {self.new_value}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
        }


class WatchMode:
    """
    Continuous monitoring mode for CDI Health.

    Periodically scans devices and reports changes.
    """

    # Fields to monitor for changes
    MONITORED_FIELDS = [
        "cdi_grade",
        "cdi_certified",
        "cdi_eligible",
        "smart_status",
        "reallocated_sectors",
        "pending_sectors",
        "pending_reallocated_sectors",
        "offline_uncorrectable_sectors",
        "uncorrectable_errors",
        "current_temperature",
        "state",
    ]

    def __init__(
        self,
        interval: int = 60,
        scan_function: Callable = None,
        on_change: Callable[[DeviceStateChange], None] = None,
        on_scan: Callable[[list[dict]], None] = None,
        mock_mode: bool = False,
        mock_data_path: str = None,
    ):
        """
        Initialize watch mode.

        :param interval: Seconds between scans
        :param scan_function: Function to call for scanning (returns list of device dicts)
        :param on_change: Callback for state changes
        :param on_scan: Callback after each scan
        :param mock_mode: Use mock data instead of real devices
        :param mock_data_path: Path to mock data (if mock_mode is True)
        """
        self.interval = max(1, interval)  # Minimum 1 second
        self.scan_function = scan_function
        self.on_change = on_change
        self.on_scan = on_scan
        self.mock_mode = mock_mode
        self.mock_data_path = mock_data_path

        self._running = False
        self._previous_state: dict[str, dict] = {}
        self._changes: list[DeviceStateChange] = []
        self._scan_count = 0
        self._start_time: datetime = None

    def start(self) -> None:
        """Start continuous monitoring."""
        self._running = True
        self._start_time = datetime.now()
        self._scan_count = 0

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print(f"Starting watch mode (interval: {self.interval}s)")
        print("Press Ctrl+C to stop")
        print("-" * 40)

        try:
            while self._running:
                self._scan_cycle()
                if self._running:
                    time.sleep(self.interval)
        except KeyboardInterrupt:
            self._shutdown()

    def stop(self) -> None:
        """Stop continuous monitoring."""
        self._running = False

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        self._shutdown()

    def _shutdown(self) -> None:
        """Perform graceful shutdown."""
        self._running = False
        print("\n" + "-" * 40)
        print("Watch mode stopped")
        self._print_summary()

    def _scan_cycle(self) -> None:
        """Perform one scan cycle."""
        self._scan_count += 1
        timestamp = datetime.now()

        print(f"\n[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Scan #{self._scan_count}")

        try:
            # Get current device states
            if self.scan_function:
                devices = self.scan_function()
            elif self.mock_mode:
                devices = self._mock_scan()
            else:
                devices = self._real_scan()

            # Detect changes
            changes = self._detect_changes(devices)

            # Report changes
            if changes:
                print(f"  Changes detected: {len(changes)}")
                for change in changes:
                    print(f"    {change}")
                    if self.on_change:
                        self.on_change(change)
            else:
                print(f"  No changes ({len(devices)} devices)")

            # Store current state
            self._store_state(devices)

            # Callback after scan
            if self.on_scan:
                self.on_scan(devices)

        except Exception as e:
            print(f"  Error during scan: {e}")

    def _real_scan(self) -> list[dict]:
        """Scan real devices."""
        from cdi_health.classes.devices import Devices

        devices = Devices()
        return devices.devices

    def _mock_scan(self) -> list[dict]:
        """Scan mock devices."""
        from cdi_health.classes.mock import MockDevices

        devices = MockDevices(mock_data_path=self.mock_data_path)
        return devices.devices

    def _detect_changes(self, devices: list[dict]) -> list[DeviceStateChange]:
        """
        Detect changes between current and previous state.

        :param devices: Current device states
        :return: List of detected changes
        """
        changes = []
        timestamp = datetime.now()

        for device in devices:
            device_id = device.get("dut", "unknown")
            previous = self._previous_state.get(device_id, {})

            # Check monitored fields for changes
            for field in self.MONITORED_FIELDS:
                current_value = device.get(field)
                previous_value = previous.get(field)

                # Skip if both are None or field doesn't exist
                if current_value is None and previous_value is None:
                    continue

                # Detect change
                if current_value != previous_value:
                    change = DeviceStateChange(
                        device_id=device_id,
                        field=field,
                        old_value=previous_value,
                        new_value=current_value,
                        timestamp=timestamp,
                    )
                    changes.append(change)
                    self._changes.append(change)

        return changes

    def _store_state(self, devices: list[dict]) -> None:
        """Store current device state for comparison."""
        self._previous_state = {}
        for device in devices:
            device_id = device.get("dut", "unknown")
            self._previous_state[device_id] = device.copy()

    def _print_summary(self) -> None:
        """Print summary of watch session."""
        if not self._start_time:
            return

        duration = datetime.now() - self._start_time
        print(f"\nWatch Summary:")
        print(f"  Duration: {duration}")
        print(f"  Total scans: {self._scan_count}")
        print(f"  Total changes detected: {len(self._changes)}")

        if self._changes:
            print(f"\n  Change summary:")
            # Group changes by device
            by_device: dict[str, list[DeviceStateChange]] = {}
            for change in self._changes:
                if change.device_id not in by_device:
                    by_device[change.device_id] = []
                by_device[change.device_id].append(change)

            for device_id, device_changes in by_device.items():
                print(f"    {device_id}: {len(device_changes)} changes")

    def get_changes(self) -> list[DeviceStateChange]:
        """Get all detected changes."""
        return self._changes.copy()

    def get_changes_json(self) -> str:
        """Get all changes as JSON string."""
        return json.dumps([c.to_dict() for c in self._changes], indent=2)


def run_watch_mode(
    interval: int = 60,
    mock_mode: bool = False,
    mock_data_path: str = None,
    on_change: Callable = None,
) -> WatchMode:
    """
    Run watch mode with default settings.

    :param interval: Seconds between scans
    :param mock_mode: Use mock data
    :param mock_data_path: Path to mock data
    :param on_change: Callback for changes
    :return: WatchMode instance
    """
    watch = WatchMode(
        interval=interval,
        mock_mode=mock_mode,
        mock_data_path=mock_data_path,
        on_change=on_change,
    )
    watch.start()
    return watch
