/**
 * Pure helpers for the Drives page (names, capacity and hours come from
 * lib/drive-names and are re-exported here): the
 * numbers shown in the list and panel, and the "healthy signals" sentence.
 */
import {
  gradeOf,
  GRADE_ORDER,
  normalizeGrade,
  type GradeLetter,
} from "@/components/ui-cdi"
import { getReportCategory } from "@/lib/drive-labels"
import {
  formatHours,
  formatInt,
  poweredOnSpan,
  reported,
  toNumber,
} from "@/lib/drive-names"
import type { DeviceRecord, DriveClass, ScoreDeduction } from "@/lib/types"

// ---------------------------------------------------------------------------
// Numbers and names (shared with Overview and grade sentences)
// ---------------------------------------------------------------------------

export {
  capacityLabel,
  driveTitle,
  formatCapacity,
  formatHours,
  formatInt,
  formatPoweredOn,
  friendlyModel,
  modelNumber,
  poweredOnSpan,
  reported,
  serialOf,
  toNumber,
} from "@/lib/drive-names"

export function formatPercent(value: number | null): string {
  return value == null ? "—" : `${formatInt(value)}%`
}

/** "/dev/nvme1" → "nvme1". */
export function shortDevicePath(device: DeviceRecord): string {
  return reported(device.dut).replace(/^\/dev\//, "")
}

// ---------------------------------------------------------------------------
// Drive type
// ---------------------------------------------------------------------------

export const DRIVE_TYPES: DriveClass[] = [
  "NVMe SSD",
  "SATA SSD",
  "SAS SSD",
  "SATA HDD",
  "SAS HDD",
]

export function driveType(device: DeviceRecord): DriveClass {
  return getReportCategory(device)
}

/** "NVMe SSD" → "nvme-ssd" (URL value). */
export function driveTypeSlug(type: string): string {
  return type.trim().toLowerCase().replace(/\s+/g, "-")
}

export function driveTypeFromSlug(slug: string | null): DriveClass | null {
  if (!slug) {
    return null
  }
  const wanted = driveTypeSlug(slug)
  return (
    [...DRIVE_TYPES, "Other" as DriveClass].find(
      (type) => driveTypeSlug(type) === wanted
    ) ?? null
  )
}

export function isNvme(device: DeviceRecord): boolean {
  return (
    device.transport_protocol === "NVMe" || driveType(device) === "NVMe SSD"
  )
}

function isSsd(device: DeviceRecord): boolean {
  return driveType(device).endsWith("SSD")
}

// ---------------------------------------------------------------------------
// Readings
// ---------------------------------------------------------------------------

export function powerOnHours(device: DeviceRecord): number | null {
  return toNumber(device.power_on_hours)
}

/** Percent of rated writes used (SSDs). */
export function writesUsed(device: DeviceRecord): number | null {
  return (
    toNumber(device.percentage_used) ??
    toNumber(device.ssd_percentage_used_endurance)
  )
}

/** Spare space left, percent (SSDs). */
export function spare(device: DeviceRecord): number | null {
  const record = device as Record<string, unknown>
  return (
    toNumber(device.available_spare) ??
    toNumber(record.available_reserved_space)
  )
}

function attributeValue(device: DeviceRecord, key: string): number | null {
  return toNumber(device.attribute_grades?.[key]?.value)
}

function grownDefects(device: DeviceRecord): number | null {
  return (
    toNumber(device.grown_defects) ?? attributeValue(device, "grown_defects")
  )
}

function uncorrected(device: DeviceRecord): number | null {
  return (
    toNumber(device.uncorrectable_errors) ??
    attributeValue(device, "uncorrected_errors")
  )
}

function pending(device: DeviceRecord): number | null {
  return (
    toNumber(device.pending_sectors) ??
    toNumber(device.pending_reallocated_sectors)
  )
}

export type KeyNumber = { label: string; value: string; hint?: string }

/** The numbers worth showing for this kind of drive, skipping unreported ones. */
export function keyNumbers(device: DeviceRecord): KeyNumber[] {
  const out: KeyNumber[] = [
    // formatPoweredOn split for a tile: "40,858 h" over "4 yrs 242 days".
    {
      label: "Powered on",
      value: formatHours(powerOnHours(device)),
      hint: poweredOnSpan(powerOnHours(device)) ?? undefined,
    },
  ]
  const add = (label: string, value: number | null, format = formatInt) => {
    if (value != null) {
      out.push({ label, value: format(value) })
    }
  }
  if (isSsd(device)) {
    add("Writes used", writesUsed(device), (v) => formatPercent(v))
    add("Spare", spare(device), (v) => formatPercent(v))
  }
  if (isNvme(device)) {
    add("Media errors", toNumber(device.media_errors))
  } else if (driveType(device).startsWith("SAS")) {
    add("Grown defects", grownDefects(device))
    add("Uncorrected errors", uncorrected(device))
  } else {
    add("Reallocated sectors", toNumber(device.reallocated_sectors))
    add("Pending sectors", pending(device))
    add("Uncorrectable errors", uncorrected(device))
  }
  add("Temperature", toNumber(device.current_temperature), (v) => `${v} °C`)
  return out
}

// ---------------------------------------------------------------------------
// "Everything else is healthy"
// ---------------------------------------------------------------------------

function attributeIsBad(device: DeviceRecord, keys: string[]): boolean {
  return keys.some((key) => {
    const grade = normalizeGrade(device.attribute_grades?.[key]?.grade)
    return grade != null && grade !== "A"
  })
}

/**
 * Healthy readings in plain words ("no media errors", "spare 92%",
 * "17% of rated writes used"). Readings that pulled the grade down are left out.
 */
export function healthySignals(device: DeviceRecord): string[] {
  const out: string[] = []
  const zero = (
    value: number | null,
    text: string,
    attributeKeys: string[] = []
  ) => {
    if (value === 0 && !attributeIsBad(device, attributeKeys)) {
      out.push(text)
    }
  }

  if (isNvme(device)) {
    zero(toNumber(device.media_errors), "no media errors", ["media_errors"])
    zero(toNumber(device.critical_warning), "no critical warnings")
  } else if (driveType(device).startsWith("SAS")) {
    zero(grownDefects(device), "no grown defects", ["grown_defects"])
    zero(uncorrected(device), "no uncorrected errors", ["uncorrected_errors"])
  } else {
    zero(toNumber(device.reallocated_sectors), "no reallocated sectors", [
      "reallocated_sectors",
    ])
    zero(pending(device), "no pending sectors", ["pending_sectors"])
    zero(uncorrected(device), "no uncorrectable errors", [
      "uncorrectable_errors",
    ])
  }

  const sp = spare(device)
  if (
    sp != null &&
    sp >= 50 &&
    !attributeIsBad(device, ["available_spare", "available_reserved_space"])
  ) {
    out.push(`spare ${formatInt(sp)}%`)
  }
  const used = writesUsed(device)
  if (used != null && used < 100 && !attributeIsBad(device, ["endurance"])) {
    out.push(`${formatInt(used)}% of rated writes used`)
  }
  return out
}

// ---------------------------------------------------------------------------
// Sorting and grouping
// ---------------------------------------------------------------------------

export function gradeRank(grade: GradeLetter | null): number {
  return grade == null ? GRADE_ORDER.length : GRADE_ORDER.indexOf(grade)
}

export function deviceGradeRank(device: DeviceRecord): number {
  return gradeRank(gradeOf(device))
}

const collator = new Intl.Collator("en", { numeric: true })

export function naturalCompare(a: string, b: string): number {
  return collator.compare(a, b)
}

export function deductionsOf(device: DeviceRecord): ScoreDeduction[] {
  return device.health_deductions ?? device.deductions ?? []
}

// ---------------------------------------------------------------------------
// Raw attributes ("All data")
// ---------------------------------------------------------------------------

export type RawRow = { name: string; value: string; extra?: string }

function scalarText(value: unknown): string | null {
  if (value == null || value === "") {
    return null
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>
    if ("string" in record && record.string != null) {
      return String(record.string)
    }
    if ("value" in record && typeof record.value !== "object") {
      return String(record.value)
    }
    return null
  }
  return String(value)
}

function flatten(
  record: Record<string, unknown>,
  prefix = "",
  out: RawRow[] = []
): RawRow[] {
  for (const [key, value] of Object.entries(record)) {
    // NVMe logs repeat each counter as "_s" (string) and "_le" (bytes).
    if (/_(s|le)$/.test(key)) {
      continue
    }
    const name = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const text = scalarText(value)
      if (text != null) {
        out.push({ name, value: text })
      } else {
        flatten(value as Record<string, unknown>, name, out)
      }
    } else if (Array.isArray(value)) {
      out.push({ name, value: value.map(String).join(", ") })
    } else if (value != null && value !== "") {
      out.push({ name, value: String(value) })
    }
  }
  return out
}

/** The drive's raw health attributes as name/value rows, whatever the type. */
export function rawAttributes(device: DeviceRecord): RawRow[] {
  const attrs = device.smart_attributes
  if (Array.isArray(attrs)) {
    return attrs.map((entry) => {
      const item = (entry ?? {}) as Record<string, unknown>
      const id = item.id != null ? `${item.id} ` : ""
      const raw = scalarText(item.raw) ?? ""
      const norm = [item.value, item.worst, item.thresh]
        .map((v) => (v == null ? "—" : String(v)))
        .join(" / ")
      return {
        name: `${id}${String(item.name ?? "")}`.trim(),
        value: raw,
        extra: norm,
      }
    })
  }
  if (attrs && typeof attrs === "object") {
    return flatten(attrs as Record<string, unknown>)
  }
  if (device.nvme_smart_health_information_log) {
    return flatten(device.nvme_smart_health_information_log)
  }
  return []
}

/** Other reported fields worth a look in "All data" (label → text). */
export function driveDetails(device: DeviceRecord): RawRow[] {
  const rows: [string, unknown][] = [
    ["Vendor", reported(device.vendor)],
    ["Firmware", reported(device.firmware_revision)],
    ["Interface", reported(device.transport_version) || device.interface_link],
    ["Form factor", reported(device.form_factor)],
    [
      "Rotation",
      toNumber(device.rotation_rate)
        ? `${formatInt(toNumber(device.rotation_rate) ?? 0)} rpm`
        : null,
    ],
    ["Power cycles", device.power_cycle_count],
    [
      "Data written",
      toNumber(device.data_written_tb) != null
        ? `${Number(toNumber(device.data_written_tb)?.toFixed(1))} TB`
        : null,
    ],
    ["Highest temperature", device.highest_temperature],
    ["Health score", device.health_score],
    ["Recommended use", device.recommended_use],
    ["Certification", device.certification_rationale],
    ["Warning flags", (device.warning_flags ?? []).join(", ")],
    ["Fail codes", (device.fail_reason_codes ?? []).join(", ")],
    ["Couldn't grade because", (device.ungraded_reasons ?? []).join(", ")],
    ["Grading profile", device.grading_profile],
  ]
  return rows
    .map(([name, value]) => ({ name, value: scalarText(value) ?? "" }))
    .filter((row) => reported(row.value))
}

// ---------------------------------------------------------------------------
// Times
// ---------------------------------------------------------------------------

export function isToday(date: Date): boolean {
  const now = new Date()
  return date.toDateString() === now.toDateString()
}

/** "9:00 AM" today, "Sep 24, 9:00 AM" otherwise. */
export function formatScanTime(iso: string | null | undefined): string {
  if (!iso) {
    return ""
  }
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ""
  }
  const time = date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  })
  if (isToday(date)) {
    return time
  }
  return `${date.toLocaleDateString([], { month: "short", day: "numeric" })}, ${time}`
}
