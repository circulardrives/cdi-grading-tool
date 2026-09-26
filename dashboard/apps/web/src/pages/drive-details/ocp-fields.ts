/**
 * OCP Datacenter NVMe SSD Spec v2.7 §4.8.6 — SMART / Health Information
 * Extended log (Log Identifier C0h), as `ocp_smart_log` from
 * `nvme ocp smart-add-log -o json`. Each field: requirement ID, plain label,
 * one-line meaning, units, and — for the fields CDI grades on
 * (docs/NVME_HEALTH_POLICY.md, scoring.py `_check_ocp_smart`) — the check.
 *
 * nvme-cli key spellings vary by version ("Bad user nand blocks - Raw",
 * "bad_user_nand_blocks_raw"), so keys match case- and punctuation-blind.
 * Keys not listed here still show, under "Other fields".
 */
import type { DeviceRecord } from "@/lib/types"
import { formatInt, toNumber } from "@/pages/drives/drive-format"

import {
  bigCounter,
  checkFromDeductions,
  formatBig,
  formatBytes,
  formatCelsius,
  formatCount,
  hex,
  humanizeCode,
  type GradeCheck,
  type Obj,
} from "./details-format"
import type { FieldRow } from "./field-table"

export const OCP_GROUPS = [
  "Media & wear",
  "Errors & recovery",
  "Power loss & shutdown",
  "Thermal",
  "Identity & version",
  "Other fields",
] as const

export type OcpGroup = (typeof OCP_GROUPS)[number]

/** Defaults from src/cdi_health/config/thresholds.yaml (nvme.ocp). */
const LIMITS = {
  capacitorHealthMin: 100,
  badUserNandWarning: 90,
  badUserNandCritical: 50,
  systemDataWarning: 90,
  incompleteShutdownsWarning: 10,
  throttleEventsWarning: 20,
}

const NO_PLP = 0xffff

function norm(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]/g, "")
}

type Lookup = {
  /** First present value among these key spellings (marks it shown). */
  get: (...keys: string[]) => unknown
  num: (...keys: string[]) => number | null
  device: DeviceRecord
}

type Rendered = Omit<FieldRow, "key" | "label" | "spec" | "meaning"> | null

type OcpField = {
  id: string
  group: OcpGroup
  label: string
  /** Field name in the OCP spec. */
  spec: string
  meaning: string
  render: (lookup: Lookup) => Rendered
}

// ---------------------------------------------------------------------------
// Renderers
// ---------------------------------------------------------------------------

function bytes128(...keys: string[]) {
  return ({ get }: Lookup): Rendered => {
    const counter = bigCounter(get(...keys))
    if (!counter) {
      return null
    }
    const exact = `${formatBig(counter.exact)} bytes`
    return {
      value: formatBytes(counter.approx),
      exact,
      valueTitle: exact,
    }
  }
}

function count(unit = "", ...keys: string[]) {
  return ({ num }: Lookup): Rendered => {
    const value = num(...keys)
    if (value == null) {
      return null
    }
    return { value: `${formatInt(value)}${unit ? ` ${unit}` : ""}` }
  }
}

function percent(...keys: string[]) {
  return ({ num }: Lookup): Rendered => {
    const value = num(...keys)
    return value == null ? null : { value: `${formatInt(value)}%` }
  }
}

/** Normalized (percent of spare left) + raw count, as in SMART-3/4/43–45/52. */
function normalizedAndRaw(
  normalizedKeys: string[],
  rawKeys: string[],
  rawUnit: string,
  check?: (normalized: number | null, lookup: Lookup) => GradeCheck
) {
  return (lookup: Lookup): Rendered => {
    const normalized = lookup.num(...normalizedKeys)
    const raw = lookup.num(...rawKeys)
    if (normalized == null && raw == null) {
      return null
    }
    const invalid = normalized === NO_PLP
    return {
      value:
        normalized == null
          ? `${formatInt(raw ?? 0)} ${rawUnit}`
          : invalid
            ? "Not valid on this drive (FFFFh)"
            : `${formatInt(normalized)}% left`,
      exact: [
        normalized != null && !invalid
          ? `Normalized ${formatInt(normalized)}`
          : null,
        raw != null ? `Raw ${formatInt(raw)} ${rawUnit}` : null,
      ]
        .filter(Boolean)
        .join(" · "),
      check: check && !invalid ? check(normalized, lookup) : undefined,
    }
  }
}

function errataChar(value: number | null): string | null {
  if (value == null) {
    return null
  }
  if (value === 0) {
    return "None"
  }
  return value >= 0x61 && value <= 0x7a
    ? `Errata ${String.fromCharCode(value)}`
    : hex(value)
}

function text(...keys: string[]) {
  return ({ get }: Lookup): Rendered => {
    const value = get(...keys)
    if (value == null || value === "") {
      return null
    }
    const n = toNumber(value)
    return {
      value: typeof value === "string" ? value.trim() || "—" : formatCount(n),
    }
  }
}

// ---------------------------------------------------------------------------
// The C0h fields, in spec order within each group
// ---------------------------------------------------------------------------

export const OCP_FIELDS: OcpField[] = [
  // Media & wear -------------------------------------------------------------
  {
    id: "SMART-1",
    group: "Media & wear",
    label: "Flash written",
    spec: "Physical Media Units Written",
    meaning:
      "Bytes written to flash, including the drive's own housekeeping (compare with data written for write amplification).",
    render: bytes128(
      "Physical media units written",
      "physical_media_units_written"
    ),
  },
  {
    id: "SMART-2",
    group: "Media & wear",
    label: "Flash read",
    spec: "Physical Media Units Read",
    meaning: "Bytes read from flash, user and system areas.",
    render: bytes128("Physical media units read", "physical_media_units_read"),
  },
  {
    id: "SMART-3",
    group: "Media & wear",
    label: "Bad user flash blocks",
    spec: "Bad User NAND Blocks (normalized / raw)",
    meaning:
      "Retired user blocks; normalized is the % of user spare blocks left (100 at the factory).",
    render: normalizedAndRaw(
      ["Bad user nand blocks - Normalized", "bad_user_nand_blocks_normalized"],
      ["Bad user nand blocks - Raw", "bad_user_nand_blocks_raw"],
      "blocks",
      (normalized, { device }) =>
        checkFromDeductions(
          device,
          ["ocp_bad_user_nand_normalized"],
          normalized,
          `Normalized: warning below ${LIMITS.badUserNandWarning} · fails below ${LIMITS.badUserNandCritical}`
        )
    ),
  },
  {
    id: "SMART-4",
    group: "Media & wear",
    label: "Bad system flash blocks",
    spec: "Bad System NAND Blocks (normalized / raw)",
    meaning: "Retired blocks in the drive's own system area.",
    render: normalizedAndRaw(
      [
        "Bad system nand blocks - Normalized",
        "bad_system_nand_blocks_normalized",
      ],
      ["Bad system nand blocks - Raw", "bad_system_nand_blocks_raw"],
      "blocks"
    ),
  },
  {
    id: "SMART-9",
    group: "Media & wear",
    label: "System area wear",
    spec: "System Data % Used",
    meaning:
      "Wear of the firmware/metadata area; at 100% the drive may no longer work reliably.",
    render: (lookup) => {
      const value = lookup.num(
        "System data percent used",
        "system_data_percent_used",
        "System data % used"
      )
      if (value == null) {
        return null
      }
      return {
        value: `${formatInt(value)}%`,
        check: checkFromDeductions(
          lookup.device,
          ["ocp_system_data_percent_used"],
          value,
          `Warning at ${LIMITS.systemDataWarning}% · fails at 100%`
        ),
      }
    },
  },
  {
    id: "SMART-10",
    group: "Media & wear",
    label: "Refreshed blocks",
    spec: "Refresh Counts",
    meaning:
      "Blocks rewritten to keep data intact (not garbage collection or wear levelling).",
    render: count("blocks", "Refresh counts", "refresh_counts"),
  },
  {
    id: "SMART-11",
    group: "Media & wear",
    label: "Erase counts (most / least worn block)",
    spec: "User Data Erase Counts (max / min)",
    meaning:
      "How many times the most- and least-erased user blocks were erased.",
    render: ({ num }) => {
      const max = num(
        "Max User data erase counts",
        "max_user_data_erase_counts"
      )
      const min = num(
        "Min User data erase counts",
        "min_user_data_erase_counts"
      )
      if (max == null && min == null) {
        return null
      }
      return {
        value: `${formatCount(max)} / ${formatCount(min)}`,
        exact: "Most worn / least worn",
      }
    },
  },
  {
    id: "SMART-17",
    group: "Media & wear",
    label: "Free spare blocks",
    spec: "% Free Blocks",
    meaning: "Share of the spare area erased and ready to take writes.",
    render: percent("Percent free blocks", "percent_free_blocks"),
  },
  {
    id: "SMART-23",
    group: "Media & wear",
    label: "Space in use",
    spec: "Total NUSE (namespace utilization)",
    meaning: "Logical blocks holding data, across all namespaces.",
    render: count(
      "blocks",
      "NUSE - Namespace utilization",
      "nuse_namespace_utilization",
      "Total NUSE"
    ),
  },
  {
    id: "SMART-25",
    group: "Media & wear",
    label: "Rated endurance",
    spec: "Endurance Estimate",
    meaning: "Estimated total bytes the drive can take over its life.",
    render: bytes128("Endurance estimate", "endurance_estimate"),
  },
  {
    id: "SMART-30",
    group: "Media & wear",
    label: "Dies retired early",
    spec: "Proactive Bad Die Retirement",
    meaning: "Dies taken offline because the drive predicted they would fail.",
    render: count(
      "",
      "Proactive bad die retirement count",
      "proactive_bad_die_retirement"
    ),
  },
  {
    id: "SMART-36",
    group: "Media & wear",
    label: "Flash dies",
    spec: "Total Media Dies",
    meaning: "Number of flash dies in the drive.",
    render: count("", "Total media dies", "total_media_dies"),
  },
  {
    id: "SMART-37",
    group: "Media & wear",
    label: "Dies allowed to fail",
    spec: "Media Die Failure Tolerance",
    meaning: "Dies that can fail with the drive still working.",
    render: count(
      "",
      "Media die failure tolerance",
      "media_die_failure_tolerance"
    ),
  },
  {
    id: "SMART-38",
    group: "Media & wear",
    label: "Dies offline",
    spec: "Media Dies Offline",
    meaning: "Dies permanently retired.",
    render: count("", "Media dies offline", "media_dies_offline"),
  },
  {
    id: "SMART-41",
    group: "Media & wear",
    label: "Average erase count",
    spec: "NAND Avg. Erase Count",
    meaning: "Average erases across all flash blocks.",
    render: count(
      "",
      "Nand avg erase count",
      "NAND avg erase count",
      "nand_avg_erase_count"
    ),
  },
  {
    id: "SMART-43",
    group: "Media & wear",
    label: "System area program failures",
    spec: "System Area Program Fail Count (normalized / raw)",
    meaning:
      "Program failures in the system area; normalized is % of allowed failures left.",
    render: normalizedAndRaw(
      [
        "System area program fail count normalized",
        "System area program fail count - Normalized",
      ],
      [
        "System area program fail count raw",
        "System area program fail count - Raw",
      ],
      "failures"
    ),
  },
  {
    id: "SMART-44",
    group: "Media & wear",
    label: "System area read failures",
    spec: "System Area Uncorrectable Read Count (normalized / raw)",
    meaning: "Uncorrectable reads in the system area.",
    render: normalizedAndRaw(
      [
        "System area uncorrectable read count normalized",
        "System area uncorrectable read count - Normalized",
      ],
      [
        "System area uncorrectable read count raw",
        "System area uncorrectable read count - Raw",
      ],
      "reads"
    ),
  },
  {
    id: "SMART-45",
    group: "Media & wear",
    label: "System area erase failures",
    spec: "System Area Erase Fail Count (normalized / raw)",
    meaning: "Erase failures in the system area.",
    render: normalizedAndRaw(
      [
        "System area erase fail count normalized",
        "System area erase fail count - Normalized",
      ],
      [
        "System area erase fail count raw",
        "System area erase fail count - Raw",
      ],
      "failures"
    ),
  },
  {
    id: "SMART-52",
    group: "Media & wear",
    label: "Bad blocks on dies in use",
    spec: "Dies In Use Bad NAND Blocks (normalized / raw)",
    meaning: "Retired blocks on the dies still in service.",
    render: normalizedAndRaw(
      [
        "Dies in use bad nand blocks - Normalized",
        "dies_in_use_bad_nand_blocks_normalized",
      ],
      ["Dies in use bad nand blocks - Raw", "dies_in_use_bad_nand_blocks_raw"],
      "blocks"
    ),
  },

  // Errors & recovery ----------------------------------------------------------
  {
    id: "SMART-5",
    group: "Errors & recovery",
    label: "XOR recoveries",
    spec: "XOR Recovery Count",
    meaning:
      "Times the drive used XOR parity to rebuild data (may have succeeded).",
    render: count("", "XOR recovery count", "xor_recovery_count"),
  },
  {
    id: "SMART-6",
    group: "Errors & recovery",
    label: "Uncorrectable read errors",
    spec: "Uncorrectable Read Error Count",
    meaning:
      "Reads no retry, ECC or XOR could fix — data returned as an error.",
    render: (lookup) => {
      const value = lookup.num(
        "Uncorrectable read error count",
        "uncorrectable_read_error_count"
      )
      if (value == null) {
        return null
      }
      return {
        value: formatInt(value),
        check: checkFromDeductions(
          lookup.device,
          ["ocp_uncorrectable_read_error_count"],
          value,
          "Must be 0"
        ),
      }
    },
  },
  {
    id: "SMART-7",
    group: "Errors & recovery",
    label: "Soft ECC errors",
    spec: "Soft ECC Error Count",
    meaning: "Reads that needed extra recovery beyond first-level ECC.",
    render: (lookup) => {
      const value = lookup.num("Soft ecc error count", "soft_ecc_error_count")
      return value == null
        ? null
        : { value: formatInt(value), note: "No — telemetry (recovered)" }
    },
  },
  {
    id: "SMART-8",
    group: "Errors & recovery",
    label: "End-to-end errors (detected / corrected)",
    spec: "End to End Correction Counts",
    meaning:
      "Errors caught by the drive's internal DRAM/SRAM/CRC protection; any left uncorrected fails the drive.",
    render: (lookup) => {
      const detected = lookup.num(
        "End to end detected errors",
        "end_to_end_detected_errors"
      )
      const corrected = lookup.num(
        "End to end corrected errors",
        "end_to_end_corrected_errors"
      )
      if (detected == null && corrected == null) {
        return null
      }
      const uncorrected = Math.max(0, (detected ?? 0) - (corrected ?? 0))
      return {
        value: `${formatCount(detected)} / ${formatCount(corrected)}`,
        exact: `Uncorrected (detected − corrected): ${formatInt(uncorrected)}`,
        check: checkFromDeductions(
          lookup.device,
          ["ocp_end_to_end_errors"],
          detected,
          "Detected − corrected must be 0"
        ),
      }
    },
  },
  {
    id: "SMART-14",
    group: "Errors & recovery",
    label: "PCIe correctable errors",
    spec: "PCIe Correctable Error Count",
    meaning: "Link-level errors the PCIe link fixed on its own.",
    render: (lookup) => {
      const value = lookup.num(
        "PCIe correctable error count",
        "pcie_correctable_error_count"
      )
      return value == null
        ? null
        : { value: formatInt(value), note: "No — telemetry (corrected)" }
    },
  },
  {
    id: "SMART-21",
    group: "Errors & recovery",
    label: "Unaligned writes",
    spec: "Unaligned I/O",
    meaning:
      "Writes not aligned to the drive's internal unit (resets on power cycle).",
    render: count("", "Unaligned I/O", "unaligned_io"),
  },
  {
    id: "SMART-29",
    group: "Errors & recovery",
    label: "PCIe link retrains",
    spec: "PCIe Link Retraining Count",
    meaning: "Link speed/width changes while running.",
    render: count(
      "",
      "PCIe Link Retraining Count",
      "pcie_link_retraining_count"
    ),
  },
  {
    id: "SMART-42",
    group: "Errors & recovery",
    label: "Command timeouts",
    spec: "Command Timeouts",
    meaning: "Limited-retry commands that ran past their time limit.",
    render: count("", "Command timeouts", "command_timeouts"),
  },

  // Power loss & shutdown ------------------------------------------------------
  {
    id: "SMART-15",
    group: "Power loss & shutdown",
    label: "Incomplete shutdowns",
    spec: "Incomplete Shutdowns",
    meaning: "Shutdowns that didn't finish saving all data and metadata.",
    render: (lookup) => {
      const value = lookup.num("Incomplete shutdowns", "incomplete_shutdowns")
      if (value == null) {
        return null
      }
      return {
        value: formatInt(value),
        check: checkFromDeductions(
          lookup.device,
          ["ocp_incomplete_shutdowns"],
          value,
          `Warning at ${LIMITS.incompleteShutdownsWarning} or more`
        ),
      }
    },
  },
  {
    id: "SMART-19",
    group: "Power loss & shutdown",
    label: "Capacitor health",
    spec: "Capacitor Health (PLP hold-up energy)",
    meaning:
      "Hold-up energy for a safe shutdown on power loss; 100% is the factory pass mark.",
    render: (lookup) => {
      const value = lookup.num("Capacitor health", "capacitor_health")
      if (value == null) {
        return null
      }
      if (value === NO_PLP) {
        return {
          value: "No power-loss protection",
          exact: "Reported FFFFh",
          note: "No — drive has no capacitors to check",
        }
      }
      return {
        value: `${formatInt(value)}%`,
        check: checkFromDeductions(
          lookup.device,
          ["ocp_capacitor_health"],
          value,
          `At least ${LIMITS.capacitorHealthMin}%`
        ),
      }
    },
  },
  {
    id: "SMART-24",
    group: "Power loss & shutdown",
    label: "Power-loss events",
    spec: "PLP Start Count",
    meaning: "Times the drive ran its power-loss protection on a supply drop.",
    render: ({ get }) => {
      const counter = bigCounter(get("PLP start count", "plp_start_count"))
      return counter ? { value: formatBig(counter.exact) } : null
    },
  },
  {
    id: "SMART-31",
    group: "Power loss & shutdown",
    label: "Power state changes",
    spec: "Power State Change Count",
    meaning: "NVMe power state changes, host or drive initiated.",
    render: count("", "Power State Change Count", "power_state_change_count"),
  },
  {
    id: "SMART-46",
    group: "Power loss & shutdown",
    label: "Peak power",
    spec: "Max Peak Power Capability",
    meaning: "Most power the drive can draw (100 µs window).",
    render: count(
      "W",
      "Max peak power capability",
      "max_peak_power_capability"
    ),
  },
  {
    id: "SMART-47",
    group: "Power loss & shutdown",
    label: "Average power now",
    spec: "Current Average Power",
    meaning: "Power over the last second.",
    render: count("W", "Current average power", "current_average_power"),
  },
  {
    id: "SMART-48",
    group: "Power loss & shutdown",
    label: "Lifetime energy used",
    spec: "Lifetime Power Consumed",
    meaning: "Total energy used since the factory.",
    render: count("kWh", "Lifetime power consumed", "lifetime_power_consumed"),
  },

  // Thermal ------------------------------------------------------------------
  {
    id: "SMART-12",
    group: "Thermal",
    label: "Thermal throttling",
    spec: "Thermal Throttling Status and Count",
    meaning:
      "Whether the drive is slowing itself to cool down, and how often it has.",
    render: (lookup) => {
      const status = lookup.num(
        "Current throttling status",
        "current_throttling_status"
      )
      const events = lookup.num(
        "Number of Thermal throttling events",
        "number_of_thermal_throttling_events"
      )
      if (status == null && events == null) {
        return null
      }
      const statusText =
        status == null
          ? "status not reported"
          : status === 0
            ? "not throttled now"
            : status <= 3
              ? `throttling now (level ${status})`
              : `status ${hex(status)}`
      return {
        value: `${formatCount(events)} event${events === 1 ? "" : "s"} · ${statusText}`,
        check: checkFromDeductions(
          lookup.device,
          ["ocp_current_throttling_status", "ocp_thermal_throttling_events"],
          events ?? status,
          `Warning at level 2+ or ${LIMITS.throttleEventsWarning}+ events`
        ),
      }
    },
  },
  {
    id: "SMART-39",
    group: "Thermal",
    label: "Hottest ever",
    spec: "Max Temperature Recorded",
    meaning: "Highest composite temperature over the drive's life.",
    render: ({ num }) => {
      const value = num("Max temperature recorded", "max_temperature_recorded")
      return value == null ? null : { value: formatCelsius(value) }
    },
  },

  // Identity & version ---------------------------------------------------------
  {
    id: "SMART-13",
    group: "Identity & version",
    label: "OCP spec version",
    spec: "DSSD Specification Version (major.minor.point, errata)",
    meaning: "Version of the OCP datacenter spec the drive follows.",
    render: ({ num }) => {
      const major = num("Major Version Field", "major_version_field")
      const minor = num("Minor Version Field", "minor_version_field")
      const point = num("Point Version Field", "point_version_field")
      const errata = num("Errata Version Field", "errata_version_field")
      if (major == null && minor == null) {
        return null
      }
      const version = `${major ?? 0}.${minor ?? 0}.${point ?? 0}`
      return {
        value: major ? version : "Not reported",
        exact: `Major ${major ?? 0} · minor ${minor ?? 0} · point ${point ?? 0} · errata ${errata ?? 0}`,
      }
    },
  },
  {
    id: "SMART-20",
    group: "Identity & version",
    label: "NVMe base spec errata",
    spec: "NVM Express Base Errata Version",
    meaning:
      "Newest base-spec errata with breaking changes the drive implements.",
    render: ({ num }) => {
      const value = errataChar(
        num("NVMe Base Errata Version", "nvme_base_errata_version")
      )
      return value ? { value } : null
    },
  },
  {
    id: "SMART-32",
    group: "Identity & version",
    label: "NVM command set errata",
    spec: "NVM Command Set Errata Version",
    meaning: "Newest command-set errata with breaking changes.",
    render: ({ num }) => {
      const value = errataChar(
        num(
          "NVMe Command Set Errata Version",
          "NVM Command Set Errata Version",
          "nvme_command_set_errata_version"
        )
      )
      return value ? { value } : null
    },
  },
  {
    id: "SMART-34",
    group: "Identity & version",
    label: "PCIe transport errata",
    spec: "NVMe over PCIe Transport Errata Version",
    meaning: "Newest transport-spec errata with breaking changes.",
    render: ({ num }) => {
      const value = errataChar(
        num(
          "NVMe over PCIe Transport Errata Version",
          "PCIe Transport Errata Version",
          "nvme_over_pcie_transport_errata_version"
        )
      )
      return value ? { value } : null
    },
  },
  {
    id: "SMART-35",
    group: "Identity & version",
    label: "Management interface errata",
    spec: "NVM Express Management Interface Errata Version",
    meaning: "Newest NVMe-MI errata with breaking changes.",
    render: ({ num }) => {
      const value = errataChar(
        num(
          "NVMe Mi Errata Version",
          "NVMe-MI Errata Version",
          "NVM Express Management Interface Errata Version",
          "nvme_mi_errata_version"
        )
      )
      return value ? { value } : null
    },
  },
  {
    id: "SMART-22",
    group: "Identity & version",
    label: "Firmware security version",
    spec: "Security Version Number",
    meaning:
      "Bumped when firmware carries a security fix; blocks rollback below it.",
    render: count("", "Security Version Number", "security_version_number"),
  },
  {
    id: "SMART-33",
    group: "Identity & version",
    label: "Lowest firmware allowed",
    spec: "Lowest Permitted Firmware Revision",
    meaning: "Oldest firmware the drive lets you roll back to (0 = any).",
    render: text(
      "Lowest Permitted Firmware Revision",
      "lowest_permitted_firmware_revision"
    ),
  },
  {
    id: "SMART-40",
    group: "Identity & version",
    label: "Form factor code",
    spec: "Form Factor",
    meaning: "Form factor from the NVMe-MI MultiRecord area.",
    render: text("Form factor", "form_factor"),
  },
  {
    id: "SMART-49",
    group: "Identity & version",
    label: "OCP firmware revision",
    spec: "DSSD Firmware Revision",
    meaning: "Firmware revision as major.minor.release.",
    render: text("DSSD firmware revision", "dssd_firmware_revision"),
  },
  {
    id: "SMART-50",
    group: "Identity & version",
    label: "Firmware build ID",
    spec: "DSSD Firmware Build UUID",
    meaning: "Unique ID of this firmware build.",
    render: text("DSSD firmware build UUID", "dssd_firmware_build_uuid"),
  },
  {
    id: "SMART-51",
    group: "Identity & version",
    label: "Firmware build label",
    spec: "DSSD Firmware Build Label",
    meaning: "Free-text label for test or debug builds.",
    render: text("DSSD firmware build label", "dssd_firmware_build_label"),
  },
  {
    id: "SMART-27",
    group: "Identity & version",
    label: "Log page version",
    spec: "Log Page Version",
    meaning: "Layout version of this log page.",
    render: count("", "Log page version", "log_page_version"),
  },
  {
    id: "SMART-28",
    group: "Identity & version",
    label: "Log page ID",
    spec: "Log Page GUID",
    meaning: "Fixed ID marking this as the OCP extended SMART log.",
    render: text("Log page GUID", "log_page_guid"),
  },
]

// ---------------------------------------------------------------------------

export type OcpRow = FieldRow & { group: OcpGroup }

function otherValue(value: unknown): string {
  const counter = bigCounter(value)
  if (counter) {
    return formatBig(counter.exact)
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value)
  }
  return String(value ?? "—")
}

/** Every field of the drive's C0h log, grouped, known fields first. */
export function ocpRows(device: DeviceRecord, log: Obj): OcpRow[] {
  const byNorm = new Map<string, string>()
  for (const key of Object.keys(log)) {
    byNorm.set(norm(key), key)
  }
  const used = new Set<string>()
  const get = (...keys: string[]): unknown => {
    for (const candidate of keys) {
      const key = byNorm.get(norm(candidate))
      if (key !== undefined) {
        used.add(key)
        return log[key]
      }
    }
    return undefined
  }
  const lookup: Lookup = {
    get,
    num: (...keys) => {
      const value = get(...keys)
      const counter = bigCounter(value)
      return counter ? counter.approx : toNumber(value)
    },
    device,
  }

  const rows: OcpRow[] = []
  for (const field of OCP_FIELDS) {
    const rendered = field.render(lookup)
    if (!rendered) {
      continue
    }
    rows.push({
      key: field.id,
      group: field.group,
      label: field.label,
      spec: `${field.id} · ${field.spec}`,
      meaning: field.meaning,
      ...rendered,
    })
  }
  for (const [key, value] of Object.entries(log)) {
    if (used.has(key)) {
      continue
    }
    rows.push({
      key: `other-${key}`,
      group: "Other fields",
      label: humanizeCode(key),
      spec: key,
      value: otherValue(value),
    })
  }
  return rows
}
