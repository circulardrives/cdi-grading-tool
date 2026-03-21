#
# Copyright (c) 2025 Circular Drive Initiative.
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
Self-Test Results Formatter

Formats self-test execution results in a table similar to scan output.
"""

from __future__ import annotations

import shutil

from cdi_health.classes.colors import Colors, Symbols


class SelfTestFormatter:
    """Format self-test results as a table."""

    def __init__(self):
        """Initialize formatter with terminal width detection."""
        import os
        
        # Try multiple methods to detect terminal width
        terminal_width = None
        
        # Method 1: Check COLUMNS environment variable
        if "COLUMNS" in os.environ:
            try:
                terminal_width = int(os.environ["COLUMNS"])
            except (ValueError, TypeError):
                pass
        
        # Method 2: Use shutil.get_terminal_size()
        if terminal_width is None:
            try:
                terminal_width = shutil.get_terminal_size().columns
            except (AttributeError, OSError):
                pass
        
        # Method 3: Fallback to default
        if terminal_width is None:
            terminal_width = 80
        
        # Ensure minimum width
        if terminal_width < 60:
            terminal_width = 60
        
        self.terminal_width = terminal_width

    def format_summary(self, results: list[dict]) -> str:
        """
        Format self-test results summary.
        
        :param results: List of self-test result dictionaries
        :return: Formatted table string
        """
        if not results:
            return "No devices found or no self-tests executed."

        # Count statistics
        total = len(results)
        supported = sum(1 for r in results if r.get("supported", False))
        started = sum(1 for r in results if r.get("test_started", False))
        completed = sum(1 for r in results if r.get("test_completed", False))
        failed = sum(1 for r in results if r.get("test_failed", False))
        passed = sum(1 for r in results if r.get("test_passed", False))
        in_progress = sum(1 for r in results if r.get("test_in_progress", False))

        # Format header box (responsive to terminal width)
        box_width = min(self.terminal_width - 2, 120)  # Max 120 chars, but respect terminal width
        title = "CDI Self-Test Summary"
        stats_line = f"Devices: {total} | Supported: {supported} | Started: {started} | Completed: {completed} | Passed: {passed} | Failed: {failed} | In Progress: {in_progress}"
        
        # If stats line is too long, wrap it
        if len(stats_line) > box_width - 4:
            # Split stats into two lines
            stats_part1 = f"Devices: {total} | Supported: {supported} | Started: {started} | Completed: {completed}"
            stats_part2 = f"Passed: {passed} | Failed: {failed} | In Progress: {in_progress}"
            header_lines = [
                Symbols.BOX_TL + Symbols.BOX_H * (box_width - 2) + Symbols.BOX_TR,
                Symbols.BOX_V + title.center(box_width - 2) + Symbols.BOX_V,
                Symbols.BOX_VL + Symbols.BOX_H * (box_width - 2) + Symbols.BOX_VR,
                Symbols.BOX_V + stats_part1.center(box_width - 2) + Symbols.BOX_V,
                Symbols.BOX_V + stats_part2.center(box_width - 2) + Symbols.BOX_V,
                Symbols.BOX_BL + Symbols.BOX_H * (box_width - 2) + Symbols.BOX_BR,
            ]
        else:
            header_lines = [
                Symbols.BOX_TL + Symbols.BOX_H * (box_width - 2) + Symbols.BOX_TR,
                Symbols.BOX_V + title.center(box_width - 2) + Symbols.BOX_V,
                Symbols.BOX_VL + Symbols.BOX_H * (box_width - 2) + Symbols.BOX_VR,
                Symbols.BOX_V + stats_line.center(box_width - 2) + Symbols.BOX_V,
                Symbols.BOX_BL + Symbols.BOX_H * (box_width - 2) + Symbols.BOX_BR,
            ]
        
        header = Colors.bold("\n".join(header_lines))

        # Determine if we should use compact layout (for narrow terminals)
        use_compact = self.terminal_width < 100
        
        if use_compact:
            # Compact layout: fewer columns, shorter names
            return self._format_compact_table(results, header)
        else:
            # Full layout: all columns
            return self._format_full_table(results, header)

    def _format_full_table(self, results: list[dict], header: str) -> str:
        """Format full-width table with all columns including serial."""
        # Calculate column widths based on content and terminal width
        device_width = max(12, min(15, self.terminal_width // 9))
        model_width = max(18, min(25, self.terminal_width // 6))
        serial_width = max(12, min(18, self.terminal_width // 7))
        support_width = 12
        status_width = 14
        type_width = 12
        result_width = 12
        last_test_width = 12
        
        # Adjust if terminal is narrow
        total_table_width = device_width + model_width + serial_width + support_width + status_width + type_width + result_width + last_test_width + 9
        if total_table_width > self.terminal_width - 4:
            # Reduce widths to fit
            excess = total_table_width - (self.terminal_width - 4)
            model_width = max(12, model_width - excess // 2)
            serial_width = max(10, serial_width - excess // 2)
        
        # Table header
        table_header = (
            f"┌{'─' * (device_width + 2)}┬{'─' * (model_width + 2)}┬{'─' * (serial_width + 2)}┬{'─' * (support_width + 2)}┬{'─' * (status_width + 2)}┬{'─' * (type_width + 2)}┬{'─' * (result_width + 2)}┬{'─' * (last_test_width + 2)}┐\n"
            f"│ {'Device':<{device_width}} │ {'Model':<{model_width}} │ {'Serial':<{serial_width}} │ {'Support':<{support_width}} │ {'Test Status':<{status_width}} │ {'Test Type':<{type_width}} │ {'Result':<{result_width}} │ {'Last Test':<{last_test_width}} │\n"
            f"├{'─' * (device_width + 2)}┼{'─' * (model_width + 2)}┼{'─' * (serial_width + 2)}┼{'─' * (support_width + 2)}┼{'─' * (status_width + 2)}┼{'─' * (type_width + 2)}┼{'─' * (result_width + 2)}┼{'─' * (last_test_width + 2)}┤"
        )

        # Table rows
        rows = []
        for result in results:
            device = result.get("device", "Unknown")
            model = result.get("model", "Unknown")
            if len(model) > model_width:
                model = model[:model_width-3] + "..."
            serial = result.get("serial", "Unknown")
            if len(serial) > serial_width:
                serial = serial[:serial_width-3] + "..."
            supported = "✓ Yes" if result.get("supported", False) else "✗ No"
            test_status = self._format_test_status(result)
            # Strip ANSI codes for width calculation
            test_status_plain = self._strip_ansi(str(test_status))
            if len(test_status_plain) > status_width:
                test_status = test_status[:status_width-3] + "..."
            test_type = result.get("test_type", "-") or "-"
            if len(test_type) > type_width:
                test_type = test_type[:type_width-3] + "..."
            test_result = self._format_test_result(result)
            test_result_plain = self._strip_ansi(str(test_result))
            if len(test_result_plain) > result_width:
                test_result = test_result[:result_width-3] + "..."
            last_test = self._format_last_test(result)
            if len(str(last_test)) > last_test_width:
                last_test = str(last_test)[:last_test_width-3] + "..."

            rows.append(
                f"│ {device:<{device_width}} │ {model:<{model_width}} │ {serial:<{serial_width}} │ {supported:<{support_width}} │ {test_status:<{status_width}} │ {test_type:<{type_width}} │ {test_result:<{result_width}} │ {last_test:<{last_test_width}} │"
            )

        # Table footer
        table_footer = f"└{'─' * (device_width + 2)}┴{'─' * (model_width + 2)}┴{'─' * (serial_width + 2)}┴{'─' * (support_width + 2)}┴{'─' * (status_width + 2)}┴{'─' * (type_width + 2)}┴{'─' * (result_width + 2)}┴{'─' * (last_test_width + 2)}┘"

        # Combine
        output = [header, "", table_header]
        output.extend(rows)
        output.append(table_footer)
        output.append("")
        output.append("Legend: ✓ Supported/Passed  ✗ Not Supported/Failed  ⏳ In Progress")

        return "\n".join(output)

    def _format_compact_table(self, results: list[dict], header: str) -> str:
        """Format compact table for narrow terminals (includes serial if space allows)."""
        # Compact layout: Device | Model | Serial | Status | Result (if wide enough)
        device_width = 12
        model_width = max(12, min(20, (self.terminal_width - 60) // 3))
        # Include serial if terminal is wide enough (>= 80 chars)
        has_serial_column = self.terminal_width >= 80
        serial_width = 12 if has_serial_column else 0
        status_width = 16
        result_width = 12
        
        # Table header
        if has_serial_column:
            table_header = (
                f"┌{'─' * (device_width + 2)}┬{'─' * (model_width + 2)}┬{'─' * (serial_width + 2)}┬{'─' * (status_width + 2)}┬{'─' * (result_width + 2)}┐\n"
                f"│ {'Device':<{device_width}} │ {'Model':<{model_width}} │ {'Serial':<{serial_width}} │ {'Status':<{status_width}} │ {'Result':<{result_width}} │\n"
                f"├{'─' * (device_width + 2)}┼{'─' * (model_width + 2)}┼{'─' * (serial_width + 2)}┼{'─' * (status_width + 2)}┼{'─' * (result_width + 2)}┤"
            )
        else:
            table_header = (
                f"┌{'─' * (device_width + 2)}┬{'─' * (model_width + 2)}┬{'─' * (status_width + 2)}┬{'─' * (result_width + 2)}┐\n"
                f"│ {'Device':<{device_width}} │ {'Model':<{model_width}} │ {'Status':<{status_width}} │ {'Result':<{result_width}} │\n"
                f"├{'─' * (device_width + 2)}┼{'─' * (model_width + 2)}┼{'─' * (status_width + 2)}┼{'─' * (result_width + 2)}┤"
            )

        # Table rows
        rows = []
        for result in results:
            device = result.get("device", "Unknown")
            model = result.get("model", "Unknown")
            if len(model) > model_width:
                model = model[:model_width-3] + "..."
            
            serial = result.get("serial", "Unknown")
            if has_serial_column and len(serial) > serial_width:
                serial = serial[:serial_width-3] + "..."
            
            # Combine support and test status
            supported = "✓" if result.get("supported", False) else "✗"
            test_status = self._format_test_status(result)
            status_text = f"{supported} {test_status}"
            status_plain = self._strip_ansi(status_text)
            if len(status_plain) > status_width:
                status_text = status_text[:status_width-3] + "..."
            
            test_result = self._format_test_result(result)
            result_plain = self._strip_ansi(str(test_result))
            if len(result_plain) > result_width:
                test_result = test_result[:result_width-3] + "..."

            if has_serial_column:
                rows.append(
                    f"│ {device:<{device_width}} │ {model:<{model_width}} │ {serial:<{serial_width}} │ {status_text:<{status_width}} │ {test_result:<{result_width}} │"
                )
            else:
                rows.append(
                    f"│ {device:<{device_width}} │ {model:<{model_width}} │ {status_text:<{status_width}} │ {test_result:<{result_width}} │"
                )

        # Table footer
        if has_serial_column:
            table_footer = f"└{'─' * (device_width + 2)}┴{'─' * (model_width + 2)}┴{'─' * (serial_width + 2)}┴{'─' * (status_width + 2)}┴{'─' * (result_width + 2)}┘"
        else:
            table_footer = f"└{'─' * (device_width + 2)}┴{'─' * (model_width + 2)}┴{'─' * (status_width + 2)}┴{'─' * (result_width + 2)}┘"

        # Combine
        output = [header, "", table_header]
        output.extend(rows)
        output.append(table_footer)
        output.append("")
        output.append("Legend: ✓ Supported/Passed  ✗ Not Supported/Failed  ⏳ In Progress")

        return "\n".join(output)

    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI color codes from text for width calculation."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _format_test_status(self, result: dict) -> str:
        """Format test status."""
        if result.get("test_in_progress", False):
            return Colors.yellow("⏳ Running")
        if result.get("test_completed", False):
            return Colors.green("✓ Complete")
        if result.get("test_started", False):
            return Colors.cyan("▶ Started")
        if result.get("test_error"):
            return Colors.red("✗ Error")
        if result.get("supported", False):
            return "○ Ready"
        return "-"

    def _format_test_result(self, result: dict) -> str:
        """Format test result."""
        if result.get("test_failed", False):
            return Colors.red("✗ Failed")
        if result.get("test_passed", False):
            return Colors.green("✓ Passed")
        if result.get("test_aborted", False):
            return Colors.yellow("⚠ Aborted")
        return "-"

    def _format_last_test(self, result: dict) -> str:
        """Format last test information."""
        last_test = result.get("last_test_date")
        if last_test:
            # Format as relative time or date
            return str(last_test)[:12]
        return "-"


def format_selftest_summary(results: list[dict]) -> str:
    """
    Convenience function to format self-test summary.
    
    :param results: List of self-test result dictionaries
    :return: Formatted table string
    """
    formatter = SelfTestFormatter()
    return formatter.format_summary(results)
