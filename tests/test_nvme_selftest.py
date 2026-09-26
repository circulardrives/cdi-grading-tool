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

"""Tests for NVMe self-test functionality."""

from __future__ import annotations

import json
from argparse import Namespace
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cdi_health.classes import nvme_selftest as nst
from cdi_health.classes.nvme_selftest import NVMeSelfTest


class TestNVMeSelfTest:
    """Test NVMeSelfTest class."""

    @patch("shutil.which")
    def test_initialization(self, mock_which: MagicMock) -> None:
        """Test NVMeSelfTest initialization."""
        mock_which.return_value = "/usr/bin/nvme"
        selftest = NVMeSelfTest("/dev/nvme0")
        assert selftest.device_path == "/dev/nvme0"
        assert selftest.nvme_path is not None

    @patch("shutil.which")
    def test_find_nvme_cli_not_found(self, mock_which: MagicMock) -> None:
        """Test when nvme-cli is not found."""
        mock_which.return_value = None
        with pytest.raises(Exception):  # Should raise CommandException
            NVMeSelfTest("/dev/nvme0")

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_is_supported_true(self, mock_which: MagicMock, mock_run: MagicMock) -> None:
        """Test is_supported when device supports self-test."""
        mock_which.return_value = "/usr/bin/nvme"
        mock_result = MagicMock()
        mock_result.return_code = 0
        mock_result.output = b'{"oacs": 16}'  # Bit 4 set (0x10 = 16)
        mock_run.return_value = mock_result

        with patch("cdi_health.classes.tools.Command") as mock_command:
            mock_cmd = MagicMock()
            mock_cmd.return_code = 0
            mock_cmd.output = b'{"oacs": 16}'
            mock_command.return_value = mock_cmd

            selftest = NVMeSelfTest("/dev/nvme0")
            # Mock the command run
            mock_cmd.run = MagicMock()
            result = selftest.is_supported()
            # Should return True if OACS bit 4 is set
            assert isinstance(result, bool)

    @patch("cdi_health.classes.nvme_selftest.Command")
    @patch("cdi_health.classes.nvme_selftest.shutil.which")
    def test_find_nvme_devices(self, mock_which: MagicMock, mock_command: MagicMock) -> None:
        """Test finding NVMe devices extracts controllers from namespace paths."""
        mock_which.return_value = "/usr/bin/nvme"
        mock_cmd = MagicMock()
        mock_cmd.return_code = 0
        mock_cmd.output = b'{"Devices": [{"DevicePath": "/dev/nvme0n1"}, {"DevicePath": "/dev/nvme1n1"}]}'
        mock_command.return_value = mock_cmd

        devices = NVMeSelfTest.find_nvme_devices()
        assert devices == ["/dev/nvme0", "/dev/nvme1"]

    @patch("shutil.which")
    def test_find_supported_devices(self, mock_which: MagicMock) -> None:
        """Test finding devices that support self-test."""
        mock_which.return_value = "/usr/bin/nvme"
        with patch.object(NVMeSelfTest, "find_nvme_devices", return_value=["/dev/nvme0"]):
            with patch.object(NVMeSelfTest, "is_supported", return_value=True):
                devices = NVMeSelfTest.find_supported_devices()
                assert isinstance(devices, list)
                assert len(devices) > 0
                assert devices[0]["device"] == "/dev/nvme0"
                assert devices[0]["supported"] is True


# ---------------------------------------------------------------------------
# Log Page 06h decoding (issue #130)
# ---------------------------------------------------------------------------


def _entry_bytes(
    result: int,
    code: int,
    *,
    segment: int = 0,
    vdi: int = 0,
    poh: int = 0,
    nsid: int = 0,
    lba: int = 0,
    sct: int = 0,
    sc: int = 0,
) -> bytes:
    raw = bytearray(nst.LOG_06H_ENTRY_LEN)
    raw[0] = (code << 4) | result
    raw[1] = segment
    raw[2] = vdi
    raw[4:12] = poh.to_bytes(8, "little")
    raw[12:16] = nsid.to_bytes(4, "little")
    raw[16:24] = lba.to_bytes(8, "little")
    raw[24] = sct
    raw[25] = sc
    return bytes(raw)


def build_log(op: int = 0, pct: int = 0, entries: list[bytes] | None = None) -> bytes:
    """Synthetic 564-byte Device Self-test log; unused slots have result Fh."""
    data = bytearray(nst.LOG_06H_LEN)
    data[0] = op
    data[1] = pct
    entries = entries or []
    for i in range(nst.LOG_06H_MAX_ENTRIES):
        off = nst.LOG_06H_HEADER_LEN + i * nst.LOG_06H_ENTRY_LEN
        raw = entries[i] if i < len(entries) else _entry_bytes(nst.RESULT_UNUSED, 0)
        data[off : off + nst.LOG_06H_ENTRY_LEN] = raw
    return bytes(data)


def to_hex_dump(data: bytes) -> str:
    lines = [
        "Device:nvme0 log-id:6 namespace-id:0xffffffff",
        "      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f",
    ]
    for off in range(0, len(data), 16):
        chunk = data[off : off + 16]
        lines.append(f"{off:04x}: " + " ".join(f"{b:02x}" for b in chunk) + ' "................"')
    return "\n".join(lines)


class TestLogPage06hBytes:
    def test_pass_entry(self) -> None:
        log = nst.parse_self_test_log_bytes(build_log(entries=[_entry_bytes(0, 1, poh=1234)]))
        assert log["in_progress"] is False
        assert len(log["entries"]) == 1
        entry = log["entries"][0]
        assert entry["result"] == 0
        assert entry["type"] == 1
        assert entry["type_string"] == "Short"
        assert entry["status"] == "passed"
        assert entry["power_on_hours"] == 1234
        assert entry["completion_time"] == 1234

    @pytest.mark.parametrize("result", [1, 2, 3, 4, 8, 9])
    def test_aborted_entries(self, result: int) -> None:
        log = nst.parse_self_test_log_bytes(build_log(entries=[_entry_bytes(result, 2, poh=10)]))
        entry = log["entries"][0]
        assert entry["status"] == "aborted"
        assert entry["type_string"] == "Extended"
        assert "fail" not in entry["result_string"].lower()

    def test_failed_segment_entry(self) -> None:
        raw = _entry_bytes(7, 2, segment=3, vdi=0x0F, poh=500, nsid=1, lba=0xDEADBEEF, sct=2, sc=0x81)
        entry = nst.parse_self_test_log_bytes(build_log(entries=[raw]))["entries"][0]
        assert entry["result"] == 7
        assert entry["status"] == "failed"
        assert entry["segment"] == 3
        assert entry["nsid"] == 1
        assert entry["failing_lba"] == 0xDEADBEEF
        assert entry["status_code_type"] == 2
        assert entry["status_code"] == 0x81
        assert "fail" in entry["result_string"].lower()

    @pytest.mark.parametrize("result", [5, 6])
    def test_fatal_and_unknown_segment_are_failures(self, result: int) -> None:
        entry = nst.parse_self_test_log_bytes(build_log(entries=[_entry_bytes(result, 1)]))["entries"][0]
        assert entry["status"] == "failed"

    def test_diag_fields_hidden_when_not_valid(self) -> None:
        raw = _entry_bytes(7, 1, vdi=0, nsid=9, lba=77, sct=1, sc=1)
        entry = nst.parse_self_test_log_bytes(build_log(entries=[raw]))["entries"][0]
        assert entry["nsid"] is None
        assert entry["failing_lba"] is None
        assert entry["status_code_type"] is None
        assert entry["status_code"] is None

    def test_unused_slots_skipped_and_order_kept(self) -> None:
        entries = [
            _entry_bytes(7, 1, poh=30),
            _entry_bytes(nst.RESULT_UNUSED, 0),
            _entry_bytes(0, 2, poh=20),
        ]
        log = nst.parse_self_test_log_bytes(build_log(entries=entries))
        assert [e["result"] for e in log["entries"]] == [7, 0]
        assert [e["power_on_hours"] for e in log["entries"]] == [30, 20]

    def test_all_unused_is_empty(self) -> None:
        log = nst.parse_self_test_log_bytes(build_log())
        assert log["entries"] == []

    def test_in_progress_header(self) -> None:
        data = build_log(op=0x2, pct=0x80 | 45, entries=[_entry_bytes(0, 1, poh=5)])
        log = nst.parse_self_test_log_bytes(data)
        assert log["in_progress"] is True
        assert log["current_self_test_operation"]["value"] == 2
        assert log["current_self_test_operation"]["string"] == "Extended self-test in progress"
        assert log["current_self_test_completion"] == 45  # bits 6:0 only

    def test_twenty_full_entries(self) -> None:
        entries = [_entry_bytes(0, 1, poh=100 - i) for i in range(20)]
        log = nst.parse_self_test_log_bytes(build_log(entries=entries))
        assert len(log["entries"]) == 20
        assert log["entries"][-1]["power_on_hours"] == 81

    def test_short_buffer(self) -> None:
        assert nst.parse_self_test_log_bytes(b"\x01")["entries"] == []

    def test_hex_dump_roundtrip(self) -> None:
        data = build_log(op=1, pct=10, entries=[_entry_bytes(5, 1, poh=99)])
        assert nst.parse_hex_dump(to_hex_dump(data)) == data

    def test_classify_reserved_is_unknown(self) -> None:
        assert nst.classify_result(0xA) == "unknown"
        assert nst.classify_result(None) == "unknown"
        assert nst.classify_result(0xF) == "unused"


NVME_CLI_TEXT = """Device Self Test Log for NVME device:nvme0
Current operation  : 0x1
Current Completion : 37%
Self Test Result[0]:
  Operation Result             : 0x7
  Self Test Code               : 0x2
  Failing Segment              : 0x3
  Valid Diagnostic Information : 0xf
  Power on hours (POH)         : 0x1c8
  Namespace Identifier         : 0x1
  Failing LBA                  : 0x1000
  Status Code Type             : 0x2
  Status Code                  : 0x81
  Vendor Specific              : 0 0
Self Test Result[1]:
  Operation Result             : 0x1 (Operation aborted by a Device Self-test command)
  Self Test Code               : 0x1
  Valid Diagnostic Information : 0
  Power on hours (POH)         : 0x1c0
  Vendor Specific              : 0 0
Self Test Result[2]:
  Operation Result             : 0
  Self Test Code               : 0x1
  Valid Diagnostic Information : 0
  Power on hours (POH)         : 0x10
  Vendor Specific              : 0 0
Self Test Result[3]:
  Operation Result             : 0xf
Self Test Result[4]:
  Operation Result             : 0xf
"""


class TestLogPage06hText:
    def test_hex_values_decoded(self) -> None:
        log = nst.parse_self_test_log_text(NVME_CLI_TEXT)
        assert log is not None
        assert log["current_self_test_operation"]["value"] == 1
        assert log["in_progress"] is True
        assert log["current_self_test_completion"] == 37
        assert [e["result"] for e in log["entries"]] == [7, 1, 0]
        first = log["entries"][0]
        assert first["status"] == "failed"
        assert first["type"] == 2
        assert first["segment"] == 3
        assert first["power_on_hours"] == 0x1C8
        assert first["failing_lba"] == 0x1000
        assert log["entries"][1]["status"] == "aborted"
        assert log["entries"][2]["status"] == "passed"

    def test_raw_dsts_byte_split(self) -> None:
        text = "Current operation  : 0\nCurrent Completion : 0%\nSelf Test Result[0]:\n  Operation Result : 0x25\n"
        entry = nst.parse_self_test_log_text(text)["entries"][0]
        assert entry["result"] == 5
        assert entry["type"] == 2
        assert entry["status"] == "failed"

    def test_unrecognised_output(self) -> None:
        assert nst.parse_self_test_log_text("garbage") is None


class TestFindNewEntry:
    @staticmethod
    def _e(result: int = 0, code: int = 1, poh: int = 10) -> dict:
        return nst._make_entry(result, code, power_on_hours=poh)

    def test_empty_after_is_none(self) -> None:
        assert nst.find_new_entry([], []) is None

    def test_no_baseline_is_none(self) -> None:
        assert nst.find_new_entry(None, [self._e()]) is None

    def test_first_entry_is_new(self) -> None:
        e = self._e()
        assert nst.find_new_entry([], [e]) is e

    def test_unchanged_log_is_none(self) -> None:
        assert nst.find_new_entry([self._e(poh=5)], [self._e(poh=5)]) is None

    def test_same_hour_identical_entry_detected_by_count(self) -> None:
        after = [self._e(poh=5), self._e(poh=5)]
        assert nst.find_new_entry([self._e(poh=5)], after) is after[0]

    def test_full_log_shift_detected(self) -> None:
        before = [self._e(poh=100 - i) for i in range(20)]
        after = [self._e(result=7, poh=101)] + before[:19]
        assert nst.find_new_entry(before, after)["result"] == 7

    def test_wrong_code_rejected(self) -> None:
        assert nst.find_new_entry([], [self._e(code=2)], expected_code=1) is None

    def test_older_poh_rejected(self) -> None:
        after = [self._e(poh=40), self._e(poh=50)]
        assert nst.find_new_entry([self._e(poh=50)], after) is None


def _mock_selftest() -> NVMeSelfTest:
    with patch("cdi_health.classes.nvme_selftest.shutil.which", return_value="/usr/bin/nvme"):
        return NVMeSelfTest("/dev/nvme0")


class TestResultsAndHistory:
    def test_get_results_hex_fallback(self) -> None:
        selftest = _mock_selftest()
        text_cmd = MagicMock(return_code=1, output=b"", errors=b"")
        hex_cmd = MagicMock(
            return_code=0,
            output=to_hex_dump(build_log(entries=[_entry_bytes(6, 1, poh=77)])).encode(),
            errors=b"",
        )
        with patch("cdi_health.classes.nvme_selftest.Command", side_effect=[text_cmd, hex_cmd]) as cmd_cls:
            log = selftest.get_results()
        assert "--log-len=564" in cmd_cls.call_args_list[1].args[0]
        assert log["entries"][0]["status"] == "failed"
        assert log["entries"][0]["power_on_hours"] == 77

    def test_get_results_text(self) -> None:
        selftest = _mock_selftest()
        text_cmd = MagicMock(return_code=0, output=NVME_CLI_TEXT.encode(), errors=b"")
        with patch("cdi_health.classes.nvme_selftest.Command", return_value=text_cmd):
            log = selftest.get_results()
        assert [e["result"] for e in log["entries"]] == [7, 1, 0]

    @staticmethod
    def _with_log(selftest: NVMeSelfTest, entries: list[dict], current_poh: int | None):
        return (
            patch.object(selftest, "get_results", return_value={"entries": entries}),
            patch.object(selftest, "get_power_on_hours", return_value=current_poh),
        )

    def test_failed_tests_honor_cutoff(self) -> None:
        selftest = _mock_selftest()
        entries = [
            nst._make_entry(7, 1, power_on_hours=10_000),  # recent failure
            nst._make_entry(1, 1, power_on_hours=9_990),  # aborted, not a failure
            nst._make_entry(5, 2, power_on_hours=1_000),  # old failure
        ]
        p1, p2 = self._with_log(selftest, entries, 10_010)
        with p1, p2:
            failed = selftest.get_failed_tests(days=30)
            assert [e["power_on_hours"] for e in failed] == [10_000]
            assert len(selftest.get_failed_tests(days=400)) == 2
            assert selftest.has_recent_failures(days=30) is True

    def test_failed_tests_without_current_poh_returns_all(self) -> None:
        selftest = _mock_selftest()
        entries = [nst._make_entry(7, 1, power_on_hours=1), nst._make_entry(6, 1, power_on_hours=2)]
        p1, p2 = self._with_log(selftest, entries, None)
        with p1, p2:
            assert len(selftest.get_failed_tests()) == 2

    def test_last_test_date_relative_to_poh(self) -> None:
        selftest = _mock_selftest()
        # Treating POH as a Unix epoch would have produced a 1970 date
        p1, p2 = self._with_log(selftest, [nst._make_entry(0, 1, power_on_hours=1_000)], 1_048)
        with p1, p2:
            assert selftest.get_last_test_power_on_hours() == 1_000
            assert selftest.hours_since_last_test() == 48
            assert selftest.days_since_last_test() == 2
            last = selftest.get_last_test_date()
        assert last is not None
        assert abs((datetime.now() - timedelta(hours=48)) - last) < timedelta(minutes=1)

    def test_last_test_date_unknown_without_current_poh(self) -> None:
        selftest = _mock_selftest()
        p1, p2 = self._with_log(selftest, [nst._make_entry(0, 1, power_on_hours=1_000)], None)
        with p1, p2:
            assert selftest.get_last_test_date() is None
            assert selftest.days_since_last_test() is None

    def test_get_power_on_hours_parses_string(self) -> None:
        selftest = _mock_selftest()
        cmd = MagicMock(return_code=0, output=b'{"power_on_hours": "12,345"}')
        with patch("cdi_health.classes.nvme_selftest.Command", return_value=cmd):
            assert selftest.get_power_on_hours() == 12345


# ---------------------------------------------------------------------------
# cmd_selftest --wait result verification
# ---------------------------------------------------------------------------


def _args(**overrides) -> Namespace:
    base = {
        "device": "/dev/nvme0",
        "status": False,
        "abort": False,
        "type": "short",
        "wait": True,
        "verbose": False,
        "no_color": True,
        "output": "json",
    }
    base.update(overrides)
    return Namespace(**base)


def _handler(logs: list[list[dict]]) -> MagicMock:
    """Mock handler whose get_results() returns successive entry lists (last one repeats)."""
    handler = MagicMock()
    handler.is_supported.return_value = True
    handler.execute_short.return_value = MagicMock(return_code=0, errors=b"")
    handler.execute_extended.return_value = MagicMock(return_code=0, errors=b"")
    handler.get_current_status.return_value = {"in_progress": False, "status": "idle", "value": 0}
    state = {"idx": 0}

    def _results() -> dict:
        idx = min(state["idx"], len(logs) - 1)
        state["idx"] += 1
        return {"entries": logs[idx]}

    handler.get_results.side_effect = _results
    return handler


class TestCmdSelftestSingleDeviceWait:
    @staticmethod
    def _run(handler: MagicMock) -> int:
        from cdi_health.cli import cmd_selftest

        with (
            patch("cdi_health.cli.setup_logging"),
            patch("cdi_health.classes.nvme_selftest.NVMeSelfTest", return_value=handler),
            patch("time.sleep"),
        ):
            return cmd_selftest(_args())

    def test_new_pass_entry(self) -> None:
        old = nst._make_entry(0, 1, power_on_hours=5)
        new = nst._make_entry(0, 1, power_on_hours=9)
        assert self._run(_handler([[old], [new, old]])) == 0

    def test_empty_log_is_not_pass(self) -> None:
        assert self._run(_handler([[]])) == 1

    def test_stale_pass_entry_is_not_pass(self) -> None:
        old = nst._make_entry(0, 1, power_on_hours=5)
        assert self._run(_handler([[old]])) == 1

    def test_failed_segment_entry(self) -> None:
        new = nst._make_entry(7, 1, segment=2, power_on_hours=9)
        assert self._run(_handler([[], [new]])) == 1

    def test_aborted_entry(self) -> None:
        new = nst._make_entry(2, 1, power_on_hours=9)
        assert self._run(_handler([[], [new]])) == 1


class TestCmdSelftestScanWait:
    @staticmethod
    def _run(handler: MagicMock, capsys: pytest.CaptureFixture[str]) -> list[dict]:
        from cdi_health.cli import cmd_selftest

        supported = [{"device": "/dev/nvme0", "supported": True, "handler": handler}]
        with (
            patch("cdi_health.cli.setup_logging"),
            patch("cdi_health.classes.nvme_selftest.NVMeSelfTest", return_value=handler) as cls,
            patch("subprocess.run", side_effect=OSError("no nvme")),
            patch("cdi_health.classes.devices.Device", side_effect=OSError("no device")),
            patch("time.sleep"),
        ):
            cls.find_supported_devices.return_value = supported
            rc = cmd_selftest(_args(device=None))
        assert rc == 0
        out = capsys.readouterr().out
        # Initial and final JSON summaries are printed; the final one comes last.
        return json.loads(out[out.rindex("\n[") + 1 :])

    def test_empty_log_after_test_is_unknown_not_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = self._run(_handler([[]]), capsys)[0]
        assert result["test_completed"] is True
        assert result["test_passed"] is False
        assert result["test_result_unknown"] is True
        assert result["test_error"]

    def test_new_failed_entry_reported_failed(self, capsys: pytest.CaptureFixture[str]) -> None:
        new = nst._make_entry(5, 1, power_on_hours=42)
        # scan read, pre-start baseline read, then the finished test's entry
        result = self._run(_handler([[], [], [new]]), capsys)[0]
        assert result["test_failed"] is True
        assert result["test_passed"] is False
        assert result["last_test_date"] == "POH 42"

    def test_existing_failed_entry_classified_per_spec(self, capsys: pytest.CaptureFixture[str]) -> None:
        handler = _handler([[nst._make_entry(1, 1, power_on_hours=3)]])
        from cdi_health.cli import cmd_selftest

        supported = [{"device": "/dev/nvme0", "supported": True, "handler": handler}]
        with (
            patch("cdi_health.cli.setup_logging"),
            patch("cdi_health.classes.nvme_selftest.NVMeSelfTest", return_value=handler) as cls,
            patch("subprocess.run", side_effect=OSError("no nvme")),
            patch("cdi_health.classes.devices.Device", side_effect=OSError("no device")),
        ):
            cls.find_supported_devices.return_value = supported
            assert cmd_selftest(_args(device=None, wait=False)) == 0
        result = json.loads(capsys.readouterr().out)[0]
        # Result 1 = aborted by Device Self-test command, not a failure
        assert result["test_aborted"] is True
        assert result["test_failed"] is False
        handler.execute_short.assert_not_called()
