/**
 * Health log tab (NVMe): every field of the SMART / Health Information log
 * (Log Identifier 02h), with units and — for the fields CDI grades on — the
 * status and limit (docs/NVME_HEALTH_POLICY.md, scoring.py).
 */
import { HardDriveIcon } from "lucide-react"

import { EmptyState } from "@/components/ui-cdi"
import { formatPoweredOn } from "@/lib/drive-names"
import type { DeviceRecord } from "@/lib/types"
import { formatInt, toNumber } from "@/pages/drives/drive-format"

import {
  asArray,
  asRecord,
  celsius,
  checkFromDeductions,
  DATA_UNIT_BYTES,
  formatBytes,
  formatCelsius,
  formatCount,
  formatMinutes,
  hex,
  humanizeCode,
  type GradeCheck,
} from "./details-format"
import { FieldTable, TableCard, type FieldRow } from "./field-table"

/** Critical Warning bits (NVMe Base Spec, SMART / Health log byte 0). */
const CRITICAL_WARNING_BITS: [number, string, string][] = [
  [0, "Spare below the drive's limit", "ASCBT"],
  [1, "Temperature past a limit", "TTC"],
  [2, "Reliability degraded", "NDR"],
  [3, "Media is read-only", "AMRO"],
  [4, "Backup power (capacitor) failed", "VMBF"],
  [5, "Persistent memory is read-only", "PMRRO"],
  [6, "Indeterminate personality state", "IPS"],
]

const EGCWS_BITS: [number, string][] = [
  [0, "Endurance group spare below limit"],
  [2, "Endurance group reliability degraded"],
  [3, "Endurance group read-only"],
]

function decodeBits(value: number, bits: [number, string, ...string[]][]) {
  const names = bits
    .filter(([bit]) => value & (1 << bit))
    .map(([, name, abbr]) => (abbr ? `${name} (${abbr})` : name))
  const known = bits.reduce((mask, [bit]) => mask | (1 << bit), 0)
  if (value & ~known) {
    names.push(`other bits ${hex(value & ~known)}`)
  }
  return names
}

/** Fields shown by this table (keys also hide their `_s` / `_le` copies). */
const HANDLED = new Set([
  "critical_warning",
  "temperature",
  "available_spare",
  "available_spare_threshold",
  "percentage_used",
  "endurance_group_critical_warning_summary",
  "data_units_read",
  "data_units_written",
  "host_reads",
  "host_writes",
  "controller_busy_time",
  "power_cycles",
  "power_on_hours",
  "unsafe_shutdowns",
  "media_errors",
  "num_err_log_entries",
  "warning_temp_time",
  "critical_comp_time",
  "temperature_sensors",
])

function dataUnitsRow(
  key: string,
  label: string,
  spec: string,
  units: number | null,
  meaning: string
): FieldRow {
  return {
    key,
    label,
    spec,
    meaning,
    value: units == null ? "—" : formatBytes(units * DATA_UNIT_BYTES),
    exact:
      units == null
        ? undefined
        : `${formatInt(units)} units × 512,000 bytes = ${formatInt(units * DATA_UNIT_BYTES)} bytes`,
  }
}

function healthLogRows(device: DeviceRecord): FieldRow[] {
  const log = asRecord(device.nvme_smart_health_information_log) ?? {}
  const pick = (key: string, fallback?: unknown) =>
    toNumber(log[key]) ?? toNumber(fallback)
  const extra = device as Record<string, unknown>

  const rows: FieldRow[] = []

  // Critical warning ---------------------------------------------------------
  const cw = pick("critical_warning", device.critical_warning)
  const cwNames = cw ? decodeBits(cw, CRITICAL_WARNING_BITS) : []
  rows.push({
    key: "critical_warning",
    label: "Critical warnings",
    spec: "Critical Warning (CW) · byte 0",
    meaning: "Alarms the drive raises about itself; any one fails the drive.",
    value: cw == null ? "—" : cw === 0 ? "None" : cwNames.join(", "),
    exact: cw == null ? undefined : `Raw ${hex(cw)}`,
    check: checkFromDeductions(
      device,
      ["critical_warning"],
      cw,
      "Must be none (0)"
    ),
  })

  // Temperature --------------------------------------------------------------
  const temp = celsius(log.temperature ?? device.current_temperature)
  const warnTemp = celsius(device.warning_temperature)
  const critTemp = celsius(device.maximum_temperature)
  const sensors = asArray(log.temperature_sensors)
    .map((value) => celsius(value))
    .filter((value): value is number => value != null)
  const tempLimit = [
    warnTemp != null ? `warning above ${warnTemp} °C` : null,
    critTemp != null ? `fails above ${critTemp} °C` : null,
  ]
    .filter(Boolean)
    .join(" · ")
  rows.push({
    key: "temperature",
    label: "Temperature now",
    spec: "Composite Temperature · bytes 2:1",
    meaning: "Drive temperature at scan time.",
    value: formatCelsius(temp),
    exact: sensors.length
      ? `Sensors: ${sensors.map((s) => `${s} °C`).join(", ")}`
      : undefined,
    check: tempLimit
      ? checkFromDeductions(
          device,
          ["current_temperature"],
          temp,
          `Drive's own limits: ${tempLimit}`
        )
      : null,
    note: tempLimit
      ? undefined
      : "No — this drive reports no limits; critical warnings cover heat",
  })

  // Spare --------------------------------------------------------------------
  const sparePct = pick("available_spare", device.available_spare)
  const spareLimit = pick(
    "available_spare_threshold",
    extra.available_spare_threshold
  )
  const spareBand = device.attribute_grades?.available_spare?.grade ?? null
  const spareCheck: GradeCheck = checkFromDeductions(
    device,
    ["available_spare"],
    sparePct,
    `Fails below ${spareLimit ?? 10}% · A ≥ 80%, B ≥ 60%, C ≥ 40%, else D`
  )
  if (spareCheck.status === "ok" && spareBand && spareBand !== "A") {
    spareCheck.status = "warn"
    spareCheck.detail = `Band grade ${spareBand}`
  }
  rows.push({
    key: "available_spare",
    label: "Spare",
    spec: "Available Spare (AVSP) · byte 3",
    meaning: "Spare flash left for replacing worn blocks.",
    value: sparePct == null ? "—" : `${formatInt(sparePct)}%`,
    exact: spareBand ? `Band grade ${spareBand}` : undefined,
    check: spareCheck,
  })
  rows.push({
    key: "available_spare_threshold",
    label: "Spare limit (set by the drive)",
    spec: "Available Spare Threshold (AVSPT) · byte 4",
    meaning: "Below this, the drive itself says it's worn out.",
    value: spareLimit == null ? "—" : `${formatInt(spareLimit)}%`,
    note: "Used as the spare limit above",
  })

  // Writes used --------------------------------------------------------------
  const used = pick("percentage_used", device.percentage_used)
  rows.push({
    key: "percentage_used",
    label: "Writes used",
    spec: "Percentage Used (PUSED) · byte 5",
    meaning: "Share of the drive's rated write endurance used up.",
    value: used == null ? "—" : `${formatInt(used)}%`,
    exact:
      used != null && used > 100
        ? "Past rated writes (can exceed 100%)"
        : undefined,
    check: checkFromDeductions(
      device,
      ["percentage_used"],
      used,
      "Score drops at 80% and 90% · 100% or more grades C"
    ),
  })

  const egcws = pick(
    "endurance_group_critical_warning_summary",
    device.endurance_group_critical_warning_summary
  )
  if (egcws != null) {
    rows.push({
      key: "egcws",
      label: "Endurance group warnings",
      spec: "Endurance Group Critical Warning Summary (EGCWS) · byte 6",
      value: egcws === 0 ? "None" : decodeBits(egcws, EGCWS_BITS).join(", "),
      exact: `Raw ${hex(egcws)}`,
      check: checkFromDeductions(
        device,
        ["endurance_group_critical_warning_summary"],
        egcws,
        "Must be none (0)"
      ),
    })
  }

  // Data and commands ----------------------------------------------------------
  rows.push(
    dataUnitsRow(
      "data_units_read",
      "Data read",
      "Data Units Read (DUR) · bytes 47:32",
      pick("data_units_read"),
      "Host data read from the drive."
    ),
    dataUnitsRow(
      "data_units_written",
      "Data written",
      "Data Units Written (DUW) · bytes 63:48",
      pick("data_units_written"),
      "Host data written to the drive."
    )
  )
  rows.push({
    key: "host_reads",
    label: "Read commands",
    spec: "Host Read Commands (HRC) · bytes 79:64",
    value: formatCount(pick("host_reads")),
  })
  rows.push({
    key: "host_writes",
    label: "Write commands",
    spec: "Host Write Commands (HWC) · bytes 95:80",
    value: formatCount(pick("host_writes")),
  })
  rows.push({
    key: "controller_busy_time",
    label: "Controller busy time",
    spec: "Controller Busy Time (CBT) · bytes 111:96",
    meaning: "Time spent processing commands.",
    value: formatMinutes(pick("controller_busy_time")),
  })

  // Power --------------------------------------------------------------------
  rows.push({
    key: "power_cycles",
    label: "Power cycles",
    spec: "Power Cycles (PC) · bytes 127:112",
    value: formatCount(pick("power_cycles", device.power_cycle_count)),
  })
  const hours = pick("power_on_hours", device.power_on_hours)
  const ageCap = device.age_cap_grade
  rows.push({
    key: "power_on_hours",
    label: "Powered on",
    spec: "Power On Hours (POH) · bytes 143:128",
    meaning: "Very high hours cap the best grade the drive can get.",
    value: formatPoweredOn(hours),
    check: {
      status: hours == null ? null : ageCap && ageCap !== "A" ? "warn" : "ok",
      limit: "Age limits depend on drive class",
      detail:
        ageCap && ageCap !== "A" ? `Caps the grade at ${ageCap}` : undefined,
    },
  })
  rows.push({
    key: "unsafe_shutdowns",
    label: "Unsafe shutdowns",
    spec: "Unsafe Shutdowns (UPL) · bytes 159:144",
    meaning: "Power lost without a clean shutdown.",
    value: formatCount(pick("unsafe_shutdowns")),
    note: "No — telemetry only",
  })

  // Errors -------------------------------------------------------------------
  const media = pick("media_errors", device.media_errors)
  rows.push({
    key: "media_errors",
    label: "Media and data integrity errors",
    spec: "Media and Data Integrity Errors (MDIE) · bytes 175:160",
    meaning: "Data the drive couldn't recover; any one fails the drive.",
    value: formatCount(media),
    check: checkFromDeductions(device, ["media_errors"], media, "Must be 0"),
  })
  rows.push({
    key: "num_err_log_entries",
    label: "Error log entries",
    spec: "Number of Error Information Log Entries (NERLE) · bytes 191:176",
    meaning:
      "Lifetime count of logged command errors — usually harmless (see Error log).",
    value: formatCount(pick("num_err_log_entries")),
  })

  // Temperature time ----------------------------------------------------------
  const wctt = pick("warning_temp_time", extra.warning_temp_time)
  rows.push({
    key: "warning_temp_time",
    label: "Time above warning temperature",
    spec: "Warning Composite Temperature Time (WCTT) · bytes 195:192",
    value: formatMinutes(wctt),
    check: checkFromDeductions(
      device,
      ["warning_temp_time"],
      wctt,
      "Warning above 0 min"
    ),
  })
  const cctt = pick("critical_comp_time", extra.critical_comp_time)
  rows.push({
    key: "critical_comp_time",
    label: "Time above critical temperature",
    spec: "Critical Composite Temperature Time (CCTT) · bytes 199:196",
    value: formatMinutes(cctt),
    check: checkFromDeductions(
      device,
      ["critical_comp_time"],
      cctt,
      "Must be 0 min"
    ),
  })
  sensors.forEach((value, index) => {
    rows.push({
      key: `sensor-${index}`,
      label: `Temperature sensor ${index + 1}`,
      spec: `Temperature Sensor ${index + 1} (TS${index + 1})`,
      value: formatCelsius(value),
    })
  })

  // Anything else the drive reported --------------------------------------------
  for (const [key, value] of Object.entries(log)) {
    const base = key.replace(/_(s|le)$/, "")
    if (HANDLED.has(key) || HANDLED.has(base) || /_(s|le)$/.test(key)) {
      continue
    }
    const n = toNumber(value)
    rows.push({
      key,
      label: humanizeCode(key),
      spec: key,
      value:
        n != null
          ? formatInt(n)
          : typeof value === "object"
            ? JSON.stringify(value)
            : String(value ?? "—"),
    })
  }

  return rows
}

export function HealthLogTab({ device }: { device: DeviceRecord }) {
  const hasLog = Boolean(asRecord(device.nvme_smart_health_information_log))
  if (!hasLog && device.critical_warning == null) {
    return (
      <EmptyState
        icon={<HardDriveIcon />}
        title="No health log in this scan"
        description="The drive didn't return its SMART / Health log (02h). Scan it again, or check the Raw data tab."
      />
    )
  }
  const rows = healthLogRows(device)
  const graded = rows.filter((row) => row.check).length
  return (
    <TableCard
      title="SMART / Health Information log"
      description={`NVMe log page 02h · ${rows.length} fields · ${graded} count toward the grade (marked with a bar and a status).`}
    >
      {!hasLog ? (
        <p className="border-b px-6 py-3 text-[15px] text-muted-foreground max-sm:px-4">
          The full log wasn't saved with this scan — showing the readings CDI
          kept.
        </p>
      ) : null}
      <FieldTable label="SMART / Health Information log fields" rows={rows} />
    </TableCard>
  )
}
