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
Circular Drive Initiative - Toolkit Classes

@language Python 3.12
@version  0.0.1
"""

from __future__ import annotations

# Modules
import json
import os
import shlex
import shutil
import subprocess

# Date and Time
from datetime import datetime

# Exceptions
from cdi_health.classes.exceptions import CommandException


def resolve_tool_path(tool_name: str, fallback: str | None = None) -> str:
    """
    Resolve an executable path from PATH, then common install locations.

    :param tool_name: Binary name (e.g. "nvme", "smartctl", "sudo")
    :param fallback: Path to return if discovery fails (defaults to tool_name)
    :return: Absolute path when found, otherwise fallback or bare tool name
    """
    path = shutil.which(tool_name)
    if path:
        return path

    for base in ("/usr/bin", "/usr/sbin", "/bin", "/sbin"):
        candidate = os.path.join(base, tool_name)
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate

    try:
        result = subprocess.run(
            ["whereis", tool_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for candidate in result.stdout.strip().split()[1:]:
                if candidate.startswith("/") and "man" not in candidate.lower():
                    if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                        return candidate
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    return fallback if fallback is not None else tool_name


class Command:
    """
    Command Class
    """

    # Default timeout for subprocesses; generous enough for slow spun-down HDDs
    # responding to smartctl --xall, but bounded so a wedged drive or bridge
    # cannot stall a scan thread forever.
    DEFAULT_TIMEOUT: int = 120

    def __init__(self, command: str = None, timeout: int | None = DEFAULT_TIMEOUT):
        """
        Constructor
        :param command: command string to run
        :param timeout: seconds before the subprocess is killed (None disables)
        """

        # Properties
        self.command = " ".join(command.split()) if command else None
        self.timeout = timeout
        self.arguments = None
        self.process = None
        self.process_id = None
        self.return_code = None
        self.output = None
        self.errors = None
        self.started = None
        self.finished = None
        self.duration = None

    def run(self):
        """
        Run
        :return:
        """

        # Try
        try:
            # Start Time
            start_time = datetime.now()

            # Build argv safely (supports quoted args)
            argv = shlex.split(self.command)
            if not argv:
                raise CommandException("Empty command")

            # If already running as root, drop leading sudo to avoid unnecessary
            # dependency on sudo binary and nested privilege escalation.
            if os.path.basename(argv[0]) == "sudo" and hasattr(os, "geteuid") and os.geteuid() == 0:
                argv = argv[1:]
                if not argv:
                    raise CommandException("Invalid command: sudo without target command")

            # Launch Process
            self.process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Capture Args
            self.arguments = self.process.args

            # Capture Output
            try:
                self.output, self.errors = self.process.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.communicate()
                raise CommandException(f"Command timed out after {self.timeout}s: {self.command}")

            # Capture Return Code
            self.return_code = self.process.returncode

            # Capture Process ID
            self.process_id = self.process.pid

            # Finished Time
            finished_time = datetime.now()

            # Start Time
            self.started = start_time.strftime("%d/%m/%Y %H:%M:%S")

            # End Time
            self.finished = finished_time.strftime("%d/%m/%Y %H:%M:%S")

            # Capture Process Duration
            self.duration = str(finished_time - start_time)

        # If FileNotFoundError
        except FileNotFoundError:
            # Raise Command Exception
            raise CommandException("Command not found")

        # If Command Exception (e.g. timeout) - propagate unchanged
        except CommandException:
            raise

        # If Exception
        except Exception:
            # Raise Command Exception
            raise CommandException("An Error occurred while running the Command")

    def get_command(self):
        """
        Command Property
        :return:
        """

        return self.command

    def get_arguments(self):
        """
        Arguments Property
        :return:
        """

        return self.arguments

    def get_return_code(self):
        """
        Return Code Property
        :return:
        """

        return self.return_code

    def get_process_id(self):
        """
        Process ID Property
        :return:
        """

        return self.process_id

    def get_output(self):
        """
        Output Property
        :return:
        """

        return self.output

    def get_errors(self):
        """
        Errors Property
        :return:
        """

        return self.errors

    def execute(self):
        """
        Execute command and return (output, errors, return_code) tuple.
        Convenience method that runs the command and returns decoded output.
        :return: tuple of (output, errors, return_code)
        """
        # Run the command
        self.run()

        # Get output and decode if bytes
        output = self.get_output()
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        output = output.strip()

        # Get errors and decode if bytes
        errors = self.get_errors()
        if isinstance(errors, bytes):
            errors = errors.decode("utf-8")
        errors = errors.strip() if errors else ""

        # Get return code
        return_code = self.get_return_code()

        return output, errors, return_code

    def get_duration(self):
        """
        Duration Property
        :return:
        """

        return self.duration

    def has_errors(self):
        """
        Has Errors Property
        :return:
        """

        # If Return Code is not 0
        if self.return_code != 0:
            return True

        return False


class SG3Utils:
    """
    SG3Utils Class
    """

    # Tool paths are process-wide; cache so each Device does not re-run whereis.
    _path_cache: dict[str, str] = {}

    def __init__(self, device_id: str):
        """
        Constructor
        """

        # Get the full paths for sg3_utils binaries
        self.sg_map26_path = self.get_sg3utils_path("sg_map26")
        self.sg_turs_path = self.get_sg3utils_path("sg_turs")

        # Properties
        self.dut = device_id

    def get_sg3utils_path(self, tool_name: str) -> str:
        """
        Get the full path of sg3_utils tools.

        Searches in the following order:
        1. Class-level cache from a prior lookup
        2. PATH / standard paths / whereis via resolve_tool_path
        3. Returns tool name as fallback (will use from PATH at runtime)

        Args:
            tool_name: Name of the tool (e.g., "sg_map26", "sg_turs")

        Returns:
            Full path of the tool or tool name if not found
        """
        cached = SG3Utils._path_cache.get(tool_name)
        if cached:
            return cached

        path = resolve_tool_path(tool_name, fallback=tool_name)
        SG3Utils._path_cache[tool_name] = path
        return path

    def sg_map26(self) -> str | bool:
        """
        Map26 Command
        Returns the SCSI Generic ID for the Block Device
        :return str SCSI Generic ID | bool False for Failure:
        """

        # If it's an NVMe device, return as is
        if "/dev/nvme" in self.dut:
            return self.dut

        # Try
        try:
            # Set Command
            command = Command(f"sudo {self.sg_map26_path} {self.dut}")

            # Run Command
            command.run()

            # If Error
            if command.get_return_code() != 0:
                # Return
                return False

            # Return
            return command.get_output().strip().decode("utf-8")

        # If Command Exception
        except CommandException:
            # Return
            return False

    def test_unit_ready(self):
        """
        Test Unit Ready
        :return:
        """

        # Try
        try:
            # Set Command
            command = Command(f"sudo {self.sg_turs_path} -vvvv {self.dut}")

            # Run Command
            command.run()

            # If Error
            if command.get_return_code() != 0:
                # Return
                return "Not Ready"

            # Return
            return "Ready"

        # Command Exception
        except CommandException:
            # Return
            return "Not Ready"


class Smartctl:
    """
    Smartctl Class
    """

    def __init__(self, device_id: str = None):
        """
        Smartctl
        :param device_id:
        """

        # Get the full path of smartctl
        self.smartctl_path = self.get_smartctl_path()

        # Set Device ID
        self.dut = device_id

        # Set Bit Mask Codes (used by get_all_as_json for hard-failure messages)
        self.bitmask_codes = {
            0: "Command line did not parse correctly",
            1: "Device open failed, or device did not return an IDENTIFY DEVICE structure",
            2: "S.M.A.R.T command failed, or there was a checksum error in the S.M.A.R.T data structure",
            3: "S.M.A.R.T Status returned 'DISK FAILING'",
            4: "S.M.A.R.T Status returned 'DISK OK' but found pre-fail attributes that have previously exceeded threshold",
            5: "S.M.A.R.T Status returned 'DISK OK' but found usage or pre-fail attributes have previously exceeded threshold in the past",
            6: "S.M.A.R.T Error Log contains 1 or more record of errors",
            7: "S.M.A.R.T Self-test Log contains 1 or more record of failed self-tests",
        }

        self.get_all_device_information_command = f"sudo {self.smartctl_path} --xall"

    def get_smartctl_path(self) -> str:
        """
        Get the full path of smartctl using PATH discovery.
        :return: Full path of smartctl
        """
        return resolve_tool_path("smartctl", fallback="smartctl")

    def get_all_as_json(self) -> dict:
        """
        Get All as JSON
        :return: dict of smartctl JSON output
        :raises CommandException: on hard smartctl failure or unparseable output
        """

        # Prepare Command String
        get_all_command = f"{self.get_all_device_information_command} {self.dut} --json=ov"

        # Prepare Command
        command = Command(get_all_command)

        # Run Command
        command.run()

        # Return Code
        return_code = command.get_return_code()

        # Bits 0 (command line did not parse) and 1 (device open failed) are hard
        # failures. Higher bits indicate a failing/failed disk but smartctl still
        # emits valid JSON, which is exactly what a grading scan needs to see.
        if return_code is not None and return_code & 0b11:
            messages = [message for bit, message in self.bitmask_codes.items() if return_code & (1 << bit)]
            errors = command.get_errors()
            if isinstance(errors, bytes):
                errors = errors.decode("utf-8", errors="replace")
            raise CommandException(
                f"smartctl failed for {self.dut} (return code {return_code}): "
                f"{'; '.join(messages) or 'unknown error'}"
                f"{f' | stderr: {errors.strip()[:200]}' if errors and errors.strip() else ''}"
            )

        # Decode Output
        output = command.get_output()
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        output = (output or "").strip()

        # If Empty Output
        if not output:
            raise CommandException(f"smartctl returned empty output for {self.dut} (return code {return_code})")

        # Try Decode JSON
        try:
            # Return Smartctl Output as JSON
            return json.loads(output)

        # If JSON Decode Error
        except json.JSONDecodeError as exception:
            raise CommandException(f"Failed to parse smartctl JSON for {self.dut}: {exception}. Output: {output[:200]}")
