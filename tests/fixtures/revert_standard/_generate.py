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
Generator for the Revert Drive Grading Standard v2.0 regression fixtures.

Run from the repository root to (re)generate every smartctl-JSON-shaped mock
fixture in this directory:

    python tests/fixtures/revert_standard/_generate.py

The fixtures cover the sections of the Revert Standard that the August 2026
gap-analysis report flagged as unverifiable because the physical test fleet
never contained a triggering drive:

- Revert Standard section 6  — ATA HDD defect attributes (IDs 5/197/198/187/188/199)
- Revert Standard section 7  — ATA SSD wear / endurance
- Revert Standard section 9  — NVMe SMART / Health Information Log (Log Page 02h)
- Revert Standard section 5  — age cap (enterprise SAS and consumer ATA)
- Revert Standard section 8  — SCSI grown defects / uncorrected errors, graduated bands
- Revert Standard section 10 — self-test history recency weighting
- Finding 8 drives — reconstructions of the report's fourth 23-drive sample

The expected Revert Standard grade for every fixture lives in
tests/test_revert_standard_regression.py (hardcoded table, Finding 8 method).
"""

from __future__ import annotations

import json
from pathlib import Path

OUT_DIR = Path(__file__).parent

# Leading underscore keeps pytest from collecting this module.

_FLAGS_EVENT = {
    "value": 50,
    "string": "-O--CK ",
    "prefailure": False,
    "updated_online": True,
    "performance": False,
    "error_rate": False,
    "event_count": True,
    "auto_keep": True,
}

_FLAGS_PREFAIL = {
    "value": 51,
    "string": "PO--CK ",
    "prefailure": True,
    "updated_online": True,
    "performance": False,
    "error_rate": False,
    "event_count": True,
    "auto_keep": True,
}


def ata_attr(attr_id: int, name: str, raw: int, *, value: int = 100, thresh: int = 0, prefail: bool = False) -> dict:
    """Build one smartctl-shaped ATA SMART attribute table entry."""
    return {
        "id": attr_id,
        "name": name,
        "value": value,
        "worst": value,
        "thresh": thresh,
        "when_failed": "",
        "flags": _FLAGS_PREFAIL if prefail else _FLAGS_EVENT,
        "raw": {"value": raw, "string": str(raw)},
    }


def ata_selftest_entry(*, passed: bool, lifetime_hours: int, extended: bool = False) -> dict:
    """Build one smartctl-shaped ATA self-test log entry."""
    if passed:
        status = {"value": 0, "string": "Completed without error", "passed": True}
    else:
        status = {"value": 116, "string": "Completed: read failure", "passed": False}
    return {
        "type": {"value": 2 if extended else 1, "string": "Extended offline" if extended else "Short offline"},
        "status": status,
        "lifetime_hours": lifetime_hours,
    }


def ata_fixture(
    *,
    dev: str,
    model: str,
    serial: str,
    poh: int,
    ssd: bool = False,
    smart_passed: bool = True,
    reallocated: int = 0,
    pending: int = 0,
    offline_uncorrectable: int = 0,
    reported_uncorrect: int = 0,
    command_timeout: int = 0,
    crc_errors: int = 0,
    pct_used_endurance: int | None = None,
    self_tests: list[dict] | None = None,
) -> dict:
    """smartctl --xall --json=ov shaped ATA (SATA) drive."""
    table = [
        ata_attr(5, "Reallocated_Sector_Ct", reallocated, thresh=10, prefail=True),
        ata_attr(9, "Power_On_Hours", poh),
        ata_attr(12, "Power_Cycle_Count", 120),
        ata_attr(187, "Reported_Uncorrect", reported_uncorrect),
        ata_attr(188, "Command_Timeout", command_timeout),
        ata_attr(197, "Current_Pending_Sector", pending),
        ata_attr(198, "Offline_Uncorrectable", offline_uncorrectable),
        ata_attr(199, "UDMA_CRC_Error_Count", crc_errors),
    ]

    data: dict = {
        "json_format_version": [1, 0],
        "smartctl": {
            "version": [7, 4],
            "svn_revision": "5530",
            "platform_info": "x86_64-linux-6.6.0",
            "build_info": "(local build)",
            "argv": ["smartctl", "--xall", "--json=ov", dev],
            "exit_status": 0,
        },
        "local_time": {"time_t": 1754450000, "asctime": "Wed Aug  5 00:00:00 2026 UTC"},
        "device": {"name": dev, "info_name": f"{dev} [SAT]", "type": "sat", "protocol": "ATA"},
        "model_name": model,
        "serial_number": serial,
        "firmware_version": "RV01",
        "user_capacity": {"blocks": 1953525168, "bytes": 1000204886016},
        "logical_block_size": 512,
        "physical_block_size": 4096,
        "rotation_rate": 0 if ssd else 7200,
        "form_factor": {"ata_value": 3, "name": "2.5 inches"},
        "in_smartctl_database": True,
        "ata_version": {"string": "ACS-3 T13/2161-D revision 5", "major_value": 2046, "minor_value": 109},
        "sata_version": {"string": "SATA 3.2", "value": 255},
        "smart_support": {"available": True, "enabled": True},
        "smart_status": {"passed": smart_passed},
        "ata_smart_data": {
            "self_test": {
                "status": {"value": 0, "string": "completed without error", "passed": True},
                "polling_minutes": {"short": 2, "extended": 120},
            },
            "capabilities": {
                "values": [123, 3],
                "exec_offline_immediate_supported": True,
                "self_tests_supported": True,
                "conveyance_self_test_supported": False,
                "selective_self_test_supported": True,
                "attribute_autosave_enabled": True,
                "error_logging_supported": True,
                "gp_logging_supported": True,
            },
        },
        "ata_smart_attributes": {"revision": 10, "table": table},
        "temperature": {"current": 30},
        "power_cycle_count": 120,
        "power_on_time": {"hours": poh},
    }

    if ssd:
        # SSD wear telemetry: Device Statistics Log page 7 (authoritative for
        # devices.py) plus attribute 233 so media-type inference has evidence.
        wearout_normalized = 100 - (pct_used_endurance or 0)
        table.append(ata_attr(233, "Media_Wearout_Indicator", 0, value=wearout_normalized))
        data["ata_device_statistics"] = {
            "pages": [
                {
                    "number": 7,
                    "name": "Solid State Device Statistics",
                    "revision": 1,
                    "table": [
                        {
                            "offset": 8,
                            "name": "Percentage Used Endurance Indicator",
                            "value": pct_used_endurance or 0,
                            "flags": {"value": 93, "string": "V---N"},
                        }
                    ],
                }
            ]
        }
        data["trim"] = {"supported": True, "deterministic": True, "zeroed": True}

    if self_tests is None:
        self_tests = [ata_selftest_entry(passed=True, lifetime_hours=max(poh - 100, 0))]
    data["ata_smart_self_test_log"] = {
        "standard": {
            "revision": 1,
            "table": self_tests,
            "count": len(self_tests),
            "error_count_total": sum(1 for t in self_tests if not t["status"]["passed"]),
            "error_count_outdated": 0,
        }
    }

    return data


def scsi_selftest_entry(*, passed: bool, poh_at_test: int, background: bool = True) -> dict:
    """Build one smartctl-shaped SCSI self-test log entry (scsi_self_test_N)."""
    if passed:
        result = {"value": 0, "string": "Completed"}
    else:
        result = {"value": 3, "string": "Completed, medium failure"}
    return {
        "code": {"value": 1 if background else 5, "string": "Background short" if background else "Foreground short"},
        "result": result,
        # Include both smartctl's ``aggregate`` key and a ``hours`` alias so the
        # scorer's self-test recency window can resolve POH at test time.
        "power_on_time": {"aggregate": poh_at_test, "hours": poh_at_test, "reserved": 0},
    }


def scsi_fixture(
    *,
    dev: str,
    model: str,
    serial: str,
    poh: int,
    smart_passed: bool = True,
    grown_defects: int = 0,
    read_uncorrected: int = 0,
    write_uncorrected: int = 0,
    self_tests: list[dict] | None = None,
) -> dict:
    """smartctl --xall --json=ov shaped SAS/SCSI drive."""
    data: dict = {
        "json_format_version": [1, 0],
        "smartctl": {
            "version": [7, 4],
            "svn_revision": "5530",
            "platform_info": "x86_64-linux-6.6.0",
            "build_info": "(local build)",
            "argv": ["smartctl", "--xall", "--json=ov", dev],
            "exit_status": 0,
        },
        "local_time": {"time_t": 1754450000, "asctime": "Wed Aug  5 00:00:00 2026 UTC"},
        "device": {"name": dev, "info_name": dev, "type": "scsi", "protocol": "SCSI"},
        "vendor": "REVERT",
        "product": model,
        "model_name": f"REVERT {model}",
        "revision": "RS20",
        "scsi_version": "SPC-4",
        "user_capacity": {"blocks": 2344225968, "bytes": 1200243695616},
        "logical_block_size": 512,
        "physical_block_size": 512,
        "rotation_rate": 10000,
        "form_factor": {"scsi_value": 3, "name": "2.5 inches"},
        "serial_number": serial,
        "device_type": {"scsi_value": 0, "name": "disk"},
        "transport_protocol": {"name": "SAS", "value": 6},
        "smart_support": {"available": True, "enabled": True},
        "smart_status": {"passed": smart_passed},
        "temperature": {"current": 34, "drive_trip": 65},
        "scsi_grown_defect_list": grown_defects,
        "scsi_error_counter_log": {
            "read": {
                "errors_corrected_by_eccfast": 0,
                "errors_corrected_by_eccdelayed": 0,
                "errors_corrected_by_rereads_rewrites": 0,
                "total_errors_corrected": 0,
                "correction_algorithm_invocations": 0,
                "gigabytes_processed": "10000.000",
                "total_uncorrected_errors": read_uncorrected,
            },
            "write": {
                "errors_corrected_by_eccfast": 0,
                "errors_corrected_by_eccdelayed": 0,
                "errors_corrected_by_rereads_rewrites": 0,
                "total_errors_corrected": 0,
                "correction_algorithm_invocations": 0,
                "gigabytes_processed": "8000.000",
                "total_uncorrected_errors": write_uncorrected,
            },
        },
        "power_on_time": {"hours": poh, "minutes": 30},
        "scsi_start_stop_cycle_counter": {
            "specified_cycle_count_over_device_lifetime": 10000,
            "accumulated_start_stop_cycles": 120,
            "specified_load_unload_count_over_device_lifetime": 600000,
            "accumulated_load_unload_cycles": 900,
        },
    }

    for i, entry in enumerate(self_tests or []):
        data[f"scsi_self_test_{i}"] = entry

    return data


def nvme_fixture(
    *,
    dev: str,
    model: str,
    serial: str,
    poh: int,
    critical_warning: int = 0,
    percentage_used: int = 0,
    available_spare: int = 100,
    available_spare_threshold: int = 10,
    media_errors: int = 0,
    temperature: int = 32,
) -> dict:
    """smartctl --xall --json=ov shaped NVMe drive with Log Page 02h data."""
    return {
        "json_format_version": [1, 0],
        "smartctl": {
            "version": [7, 4],
            "svn_revision": "5530",
            "platform_info": "x86_64-linux-6.6.0",
            "build_info": "(local build)",
            "argv": ["smartctl", "--xall", "--json=ov", dev],
            "exit_status": 0,
        },
        "local_time": {"time_t": 1754450000, "asctime": "Wed Aug  5 00:00:00 2026 UTC"},
        "device": {"name": dev, "info_name": dev, "type": "nvme", "protocol": "NVMe"},
        "model_name": model,
        "serial_number": serial,
        "firmware_version": "RV01",
        "nvme_pci_vendor": {"id": 5197, "subsystem_id": 5197},
        "nvme_total_capacity": 1920383410176,
        "nvme_unallocated_capacity": 0,
        "nvme_controller_id": 1,
        "nvme_version": {"string": "2.0", "value": 131072},
        "nvme_number_of_namespaces": 1,
        "user_capacity": {"blocks": 3750748545, "bytes": 1920383410176},
        "logical_block_size": 512,
        "smart_support": {"available": True, "enabled": True},
        "smart_status": {"passed": critical_warning == 0, "nvme": {"value": critical_warning}},
        "nvme_smart_health_information_log": {
            "critical_warning": critical_warning,
            "temperature": temperature,
            "available_spare": available_spare,
            "available_spare_threshold": available_spare_threshold,
            "percentage_used": percentage_used,
            "data_units_read": 100000000,
            "data_units_written": 80000000,
            "host_reads": 900000000,
            "host_writes": 700000000,
            "controller_busy_time": 4000,
            "power_cycles": 40,
            "power_on_hours": poh,
            "unsafe_shutdowns": 3,
            "media_errors": media_errors,
            "num_err_log_entries": 0,
            "warning_temp_time": 0,
            "critical_comp_time": 0,
        },
        "temperature": {"current": temperature},
        "power_cycle_count": 40,
        "power_on_time": {"hours": poh},
        "nvme_self_test_log": {
            "current_self_test_operation": {"value": 0, "string": "No self-test in progress"},
            "table": [
                {
                    "self_test_code": {"value": 1, "string": "Short"},
                    "self_test_result": {"value": 0, "string": "Completed without error"},
                    "power_on_hours": max(poh - 24, 0),
                }
            ],
        },
    }


def build_fixtures() -> dict[str, dict]:
    """Return mapping of fixture stem -> smartctl-shaped JSON payload."""
    fixtures: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Revert Standard section 6 — ATA HDD defect attributes, one fixture per band.
    # Sector-count attributes (5/197/198) use the defect bands
    # (A=0, B=1-9, C=10-50, D=51-100, F>100); error-count attributes
    # (187, and by reconstruction 188/199) use the uncorrected-error bands
    # (A=0, B=1-5, C=6-25, D=26-100, F>100). Worst attribute wins.
    # ------------------------------------------------------------------
    fixtures["ata_hdd_defects_band_a"] = ata_fixture(
        dev="/dev/sda", model="ST1000DM010-2EP102", serial="RVATAHDA01", poh=8000
    )
    # Band fixtures keep a single primary attribute in-band so §12.5
    # multi-factor degradation does not escalate past the band under test.
    fixtures["ata_hdd_defects_band_b"] = ata_fixture(
        dev="/dev/sdb",
        model="ST1000DM010-2EP102",
        serial="RVATAHDB01",
        poh=8100,
        reallocated=5,
    )
    fixtures["ata_hdd_defects_band_c"] = ata_fixture(
        dev="/dev/sdc",
        model="ST1000DM010-2EP102",
        serial="RVATAHDC01",
        poh=8200,
        reallocated=30,
    )
    fixtures["ata_hdd_defects_band_d"] = ata_fixture(
        dev="/dev/sdd",
        model="ST1000DM010-2EP102",
        serial="RVATAHDD01",
        poh=8300,
        reallocated=75,
    )
    fixtures["ata_hdd_defects_band_f"] = ata_fixture(
        dev="/dev/sde",
        model="ST1000DM010-2EP102",
        serial="RVATAHDF01",
        poh=8400,
        reallocated=150,
    )

    # ------------------------------------------------------------------
    # Revert Standard section 7 — ATA SSD wear / endurance.
    # Reconstruction: ~55 % used = mid-life (B); >=90 % used = end-of-life (F).
    # ------------------------------------------------------------------
    fixtures["ata_ssd_midlife_wear"] = ata_fixture(
        dev="/dev/sdf",
        model="Samsung SSD 870 EVO 1TB",
        serial="RVATASSDM1",
        poh=12000,
        ssd=True,
        pct_used_endurance=55,
    )
    fixtures["ata_ssd_end_of_life_wear"] = ata_fixture(
        dev="/dev/sdg",
        model="Samsung SSD 870 EVO 1TB",
        serial="RVATASSDE1",
        poh=18000,
        ssd=True,
        pct_used_endurance=97,
    )

    # ------------------------------------------------------------------
    # Revert Standard section 9 — NVMe Log Page 02h.
    # ------------------------------------------------------------------
    fixtures["nvme_healthy_log_page_02h"] = nvme_fixture(
        dev="/dev/nvme8",
        model="REVERT NV1920",
        serial="RVNVMEOK01",
        poh=9000,
        percentage_used=3,
    )
    # Critical Warning bit 2 (NVM subsystem degraded reliability) + 95 % used.
    # smart_status.passed mirrors real smartctl behavior (false when CW != 0).
    fixtures["nvme_critical_warning_high_wear"] = nvme_fixture(
        dev="/dev/nvme9",
        model="REVERT NV1920",
        serial="RVNVMEKO01",
        poh=31000,
        critical_warning=0x04,
        percentage_used=95,
        available_spare=4,
        available_spare_threshold=10,
        media_errors=12,
    )

    # ------------------------------------------------------------------
    # Revert Standard section 5 — age cap with otherwise clean SMART.
    # Enterprise (SAS): >40k POH caps B, >60k caps C.
    # Consumer (ATA):   >20k POH caps B, >60k caps D.
    # ------------------------------------------------------------------
    fixtures["sas_enterprise_45k_poh_clean"] = scsi_fixture(
        dev="/dev/sdh", model="HUC101212CSS600", serial="RVSAS45K01", poh=45000
    )
    fixtures["sas_enterprise_65k_poh_clean"] = scsi_fixture(
        dev="/dev/sdi", model="HUC101212CSS600", serial="RVSAS65K01", poh=65000
    )
    fixtures["ata_consumer_25k_poh_clean"] = ata_fixture(
        dev="/dev/sdj", model="WDC WD10EZEX-08WN4A0", serial="RVATA25K01", poh=25000
    )
    fixtures["ata_consumer_65k_poh_clean"] = ata_fixture(
        dev="/dev/sdk", model="WDC WD10EZEX-08WN4A0", serial="RVATA65K01", poh=65000
    )

    # ------------------------------------------------------------------
    # Revert Standard section 8 — SCSI graduated bands (POH kept low so the
    # age cap never interferes with the defect grade).
    # Grown defects:      A=0, B=1-9, C=10-50, D=51-100, F>100
    # Uncorrected errors: A=0, B=1-5, C=6-25,  D=26-100, F>100
    # ------------------------------------------------------------------
    fixtures["scsi_defects_clean"] = scsi_fixture(
        dev="/dev/sdl", model="ST1200MM0009", serial="RVSCSICLN1", poh=3000
    )
    for band, count in (("b", 5), ("c", 30), ("d", 75), ("f", 150)):
        fixtures[f"scsi_grown_defects_band_{band}"] = scsi_fixture(
            dev=f"/dev/sd{band}g",
            model="ST1200MM0009",
            serial=f"RVSCSIGD{band.upper()}1",
            poh=3000,
            grown_defects=count,
        )
    for band, (read_errs, write_errs) in (("b", (2, 1)), ("c", (10, 5)), ("d", (40, 20)), ("f", (100, 50))):
        fixtures[f"scsi_uncorrected_band_{band}"] = scsi_fixture(
            dev=f"/dev/sd{band}u",
            model="ST1200MM0009",
            serial=f"RVSCSIUE{band.upper()}1",
            poh=3000,
            read_uncorrected=read_errs,
            write_uncorrected=write_errs,
        )

    # ------------------------------------------------------------------
    # Revert Standard section 10 — self-test history, recency-weighted.
    # C = one old failure; D = 2+ old failures or 1 recent failure;
    # F = 2+ recent failures. "Recent" reconstructed as within the last
    # 1,000 power-on hours. ATA drives kept below the 20k consumer age cap.
    # ------------------------------------------------------------------
    poh = 15000
    fixtures["ata_selftest_one_old_failure"] = ata_fixture(
        dev="/dev/sdm",
        model="ST1000DM010-2EP102",
        serial="RVSTOLD101",
        poh=poh,
        self_tests=[
            ata_selftest_entry(passed=True, lifetime_hours=14900),
            ata_selftest_entry(passed=True, lifetime_hours=12000),
            ata_selftest_entry(passed=False, lifetime_hours=4000),
        ],
    )
    fixtures["ata_selftest_two_old_failures"] = ata_fixture(
        dev="/dev/sdn",
        model="ST1000DM010-2EP102",
        serial="RVSTOLD201",
        poh=poh,
        self_tests=[
            ata_selftest_entry(passed=True, lifetime_hours=14900),
            ata_selftest_entry(passed=False, lifetime_hours=5200),
            ata_selftest_entry(passed=False, lifetime_hours=4000),
        ],
    )
    fixtures["ata_selftest_one_recent_failure"] = ata_fixture(
        dev="/dev/sdo",
        model="ST1000DM010-2EP102",
        serial="RVSTNEW101",
        poh=poh,
        self_tests=[
            ata_selftest_entry(passed=False, lifetime_hours=14900),
            ata_selftest_entry(passed=True, lifetime_hours=12000),
        ],
    )
    fixtures["ata_selftest_two_recent_failures"] = ata_fixture(
        dev="/dev/sdp",
        model="ST1000DM010-2EP102",
        serial="RVSTNEW201",
        poh=poh,
        self_tests=[
            ata_selftest_entry(passed=False, lifetime_hours=14950),
            ata_selftest_entry(passed=False, lifetime_hours=14820, extended=True),
            ata_selftest_entry(passed=True, lifetime_hours=12000),
        ],
    )
    # Finding 8 noted no sample ever exercised a self-test failure in
    # isolation: everything else on this drive is perfectly clean.
    fixtures["scsi_selftest_only_failure"] = scsi_fixture(
        dev="/dev/sdq",
        model="ST1200MM0009",
        serial="RVSTONLY01",
        poh=9000,
        self_tests=[
            scsi_selftest_entry(passed=False, poh_at_test=8900),
            scsi_selftest_entry(passed=True, poh_at_test=6000),
        ],
    )

    # ------------------------------------------------------------------
    # Finding 8 reconstructions — the fourth 23-drive sample
    # (sas_testing_v0.11.0_jsonoutput.json) is not in this repository, so the
    # disagreeing drives are reconstructed here from the values published in
    # the gap-analysis report, pinning the report's expected Revert grades.
    # ------------------------------------------------------------------
    fixtures["report_1SHK383Z"] = scsi_fixture(
        dev="/dev/sdr",
        model="ST900MM0006",
        serial="1SHK383Z",
        poh=3192,
        grown_defects=13,
        read_uncorrected=4,
        write_uncorrected=2,
    )
    fixtures["report_JEHXTXVN"] = scsi_fixture(
        dev="/dev/sds",
        model="HUC109090CSS600",
        serial="JEHXTXVN",
        poh=3190,
        grown_defects=31,
    )
    fixtures["report_1SHKKWGZ"] = scsi_fixture(
        dev="/dev/sdt",
        model="ST900MM0006",
        serial="1SHKKWGZ",
        poh=3172,
        grown_defects=19,
        read_uncorrected=7,
        write_uncorrected=4,
    )
    fixtures["report_ZC19AACC"] = scsi_fixture(
        dev="/dev/sdu",
        model="ST600MP0005",
        serial="ZC19AACC",
        poh=30160,
        grown_defects=49,
    )
    # Both drives below carry a failed SMART status and >100 grown defects —
    # either is an independent Stage 1 fail-gate per Revert Standard section 4.
    fixtures["report_ZAD2AZ2A"] = scsi_fixture(
        dev="/dev/sdv",
        model="ST1800MM0129",
        serial="ZAD2AZ2A",
        poh=41000,
        smart_passed=False,
        grown_defects=118,
        read_uncorrected=30,
        write_uncorrected=12,
        self_tests=[scsi_selftest_entry(passed=False, poh_at_test=40900)],
    )
    fixtures["report_ZAD2AX9T"] = scsi_fixture(
        dev="/dev/sdw",
        model="ST1800MM0129",
        serial="ZAD2AX9T",
        poh=39500,
        smart_passed=False,
        grown_defects=132,
        read_uncorrected=44,
        write_uncorrected=9,
        self_tests=[scsi_selftest_entry(passed=False, poh_at_test=39400)],
    )

    return fixtures


def main() -> None:
    fixtures = build_fixtures()
    for stem, payload in sorted(fixtures.items()):
        path = OUT_DIR / f"{stem}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(OUT_DIR.parent.parent.parent)}")
    print(f"{len(fixtures)} fixtures")


if __name__ == "__main__":
    main()
