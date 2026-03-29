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

"""Tests for mock export / anonymization helpers."""

from __future__ import annotations

from cdi_health.classes.mock_export import (
    anonymize_serial,
    deep_replace_str,
    nvme_controller_from_dut,
)


def test_anonymize_serial_edge_cases() -> None:
    assert anonymize_serial("", 3) == "MOCK000003"
    assert anonymize_serial("Not Reported", 1) == "MOCK000001"
    assert anonymize_serial("123456", 5) == "MOCK000005"


def test_anonymize_serial_letter_prefix() -> None:
    assert anonymize_serial("AB1234567", 2) == "AB000002"


def test_nvme_controller_from_dut() -> None:
    assert nvme_controller_from_dut("/dev/nvme0n1") == "/dev/nvme0"
    assert nvme_controller_from_dut("/dev/nvme196n1") == "/dev/nvme196"
    assert nvme_controller_from_dut("/dev/nvme0") == "/dev/nvme0"
    assert nvme_controller_from_dut("/dev/sda") == "/dev/sda"


def test_deep_replace_str_nested() -> None:
    obj = {"a": "prefix-SECRET-suffix", "b": [{"x": "SECRET"}]}
    assert deep_replace_str(obj, "SECRET", "X") == {"a": "prefix-X-suffix", "b": [{"x": "X"}]}
    assert deep_replace_str({"k": 1}, "OLD", "NEW") == {"k": 1}
