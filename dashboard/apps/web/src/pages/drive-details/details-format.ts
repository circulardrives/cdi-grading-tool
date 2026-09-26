/**
 * Pure helpers for the drive details page: units (bytes, data units,
 * 128-bit counters, minutes, °C), and grading status from deductions.
 */
import { deductionsOf } from "@/pages/drives/drive-format"
import { formatInt, toNumber } from "@/lib/drive-names"
import type { DeviceRecord, ScoreDeduction } from "@/lib/types"

export type Obj = Record<string, unknown>

export function asRecord(value: unknown): Obj | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Obj)
    : null
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

/** `{value, string}` objects from smartctl → the string; scalars as text. */
export function textOf(value: unknown): string {
  if (value == null) {
    return ""
  }
  const record = asRecord(value)
  if (record) {
    if (record.string != null) {
      return String(record.string).trim()
    }
    if (record.value != null && typeof record.value !== "object") {
      return String(record.value)
    }
    return ""
  }
  return String(value).trim()
}

/** `{value}` objects from smartctl → the number; plain numbers as is. */
export function numberOf(value: unknown): number | null {
  const record = asRecord(value)
  if (record && "value" in record) {
    return toNumber(record.value)
  }
  return toNumber(value)
}

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

const BYTE_UNITS: [number, string][] = [
  [1e18, "EB"],
  [1e15, "PB"],
  [1e12, "TB"],
  [1e9, "GB"],
  [1e6, "MB"],
  [1e3, "kB"],
]

/** Decimal bytes, as on drive labels: 923.6 GB, 1.01 TB, 24.79 PB. */
export function formatBytes(bytes: number): string {
  for (const [size, unit] of BYTE_UNITS) {
    if (Math.abs(bytes) >= size) {
      const value = bytes / size
      const digits = value >= 100 ? 1 : 2
      return `${Number(value.toFixed(digits)).toLocaleString("en-US")} ${unit}`
    }
  }
  return `${formatInt(bytes)} bytes`
}

/** NVMe data units (02h): one unit is 1,000 × 512 bytes. */
export const DATA_UNIT_BYTES = 512_000

/** A 128-bit OCP counter: plain number, numeric string, or `{hi, lo}`. */
export type BigCounter = { exact: bigint; approx: number }

export function bigCounter(value: unknown): BigCounter | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return { exact: BigInt(Math.trunc(value)), approx: value }
  }
  if (typeof value === "string" && /^\s*\d+\s*$/.test(value)) {
    const exact = BigInt(value.trim())
    return { exact, approx: Number(exact) }
  }
  const record = asRecord(value)
  if (record && ("hi" in record || "lo" in record)) {
    const hi = toNumber(record.hi) ?? 0
    const lo = toNumber(record.lo) ?? 0
    const exact =
      (BigInt(Math.trunc(hi)) << BigInt(64)) + BigInt(Math.trunc(lo))
    return { exact, approx: Number(exact) }
  }
  return null
}

export function formatBig(value: bigint): string {
  return value.toLocaleString("en-US")
}

/** Temperature in °C (nvme-cli reports Kelvin; smartctl already converts). */
export function celsius(value: unknown): number | null {
  const n = toNumber(value)
  if (n == null) {
    return null
  }
  return n > 200 ? Math.round(n - 273.15) : n
}

export function formatCelsius(value: number | null): string {
  return value == null ? "—" : `${formatInt(value)} °C`
}

/** "44 min", "1,234 min (20.6 h)". */
export function formatMinutes(value: number | null): string {
  if (value == null) {
    return "—"
  }
  const base = `${formatInt(value)} min`
  return value >= 120
    ? `${base} (${Number((value / 60).toFixed(1)).toLocaleString("en-US")} h)`
    : base
}

export function formatCount(value: number | null): string {
  return value == null ? "—" : formatInt(value)
}

export function hex(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`
}

// ---------------------------------------------------------------------------
// Grading status
// ---------------------------------------------------------------------------

export type Status = "ok" | "warn" | "fail"

/** How a field counts toward the grade: a status and the limit it's held to. */
export type GradeCheck = {
  status: Status | null
  /** "Must be 0", "At least 100%". */
  limit?: string
  /** Extra words after the status ("caps the grade at B"). */
  detail?: string
}

/** Deductions on any of these scoring fields (see scoring.py `field=`). */
export function deductionFor(
  device: DeviceRecord,
  fields: string[]
): ScoreDeduction | undefined {
  return deductionsOf(device).find(
    (deduction) => deduction.field && fields.includes(deduction.field)
  )
}

export function statusOfDeduction(deduction: ScoreDeduction): Status {
  return deduction.severity === "critical" ? "fail" : "warn"
}

/**
 * Status for a graded field: the scoring deduction when there is one (so the
 * page always agrees with the grade), otherwise OK when the drive reported it.
 */
export function checkFromDeductions(
  device: DeviceRecord,
  fields: string[],
  reportedValue: unknown,
  limit?: string
): GradeCheck {
  const deduction = deductionFor(device, fields)
  if (deduction) {
    const threshold =
      deduction.threshold != null && deduction.threshold !== ""
        ? String(deduction.threshold)
        : null
    return {
      status: statusOfDeduction(deduction),
      limit: limit ?? (threshold ? `Limit ${threshold}` : undefined),
      detail: deduction.reason,
    }
  }
  return {
    status: reportedValue == null || reportedValue === "" ? null : "ok",
    limit,
  }
}

export const SEVERITY_WORDS: Record<string, string> = {
  critical: "Serious — fails or caps the grade",
  warning: "Warning — lowers the score",
  info: "Note",
}

export function severityTone(severity: string | undefined) {
  return severity === "critical"
    ? ("bad" as const)
    : severity === "warning"
      ? ("warn" as const)
      : ("info" as const)
}

// ---------------------------------------------------------------------------
// Misc
// ---------------------------------------------------------------------------

/** "SOME_FLAG_NAME" → "Some flag name". */
export function humanizeCode(code: string): string {
  const words = code.replace(/[_-]+/g, " ").trim().toLowerCase()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** "2026-09-26" in local time, for file names. */
export function dateStamp(iso: string | null | undefined): string {
  const date = iso ? new Date(iso) : new Date()
  const valid = Number.isNaN(date.getTime()) ? new Date() : date
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${valid.getFullYear()}-${pad(valid.getMonth() + 1)}-${pad(valid.getDate())}`
}

/** Safe file-name part: "bench 01" → "bench-01". */
export function fileSlug(text: string): string {
  return (
    text
      .trim()
      .replace(/[^A-Za-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "drive"
  )
}

/** Long exact date/time: "Sep 26, 2026, 10:39 AM". */
export function formatWhen(iso: string | null | undefined): string {
  if (!iso) {
    return "—"
  }
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}
