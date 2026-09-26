import type { DeviceRecord } from "@/lib/types"

export type BadgeVariant = "default" | "secondary" | "destructive" | "outline"

export function healthBadgeVariant(
  status?: string,
  grade?: string
): BadgeVariant {
  const normalized = `${status ?? ""} ${grade ?? ""}`.toLowerCase()

  if (
    normalized.includes("fail") ||
    normalized.includes("critical") ||
    grade === "F" ||
    grade === "D"
  ) {
    return "destructive"
  }

  if (normalized.includes("warn") || grade === "C") {
    return "secondary"
  }

  if (grade === "A" || grade === "B") {
    return "default"
  }

  return "outline"
}

/** Status badge for self-test / job lifecycle strings (pass, fail, in progress, etc.). */
export function statusBadgeVariant(status?: string): BadgeVariant {
  const normalized = status?.toLowerCase() ?? ""
  if (
    normalized.includes("fail") ||
    normalized.includes("error") ||
    normalized.includes("timeout") ||
    normalized.includes("critical")
  ) {
    return "destructive"
  }
  if (
    normalized.includes("warn") ||
    normalized.includes("progress") ||
    normalized.includes("started") ||
    normalized.includes("running")
  ) {
    return "secondary"
  }
  if (
    normalized.includes("pass") ||
    normalized.includes("complete") ||
    normalized.includes("success")
  ) {
    return "outline"
  }
  return "outline"
}

const UNGRADED = "UNGRADED"

/**
 * True when the backend marked the drive UNGRADED (§15). Checks every field
 * the API may use so older payloads without `grading_status` still work.
 */
export function isUngradedDevice(device: DeviceRecord): boolean {
  return (
    device.grading_status === UNGRADED ||
    device.health_grade?.toUpperCase() === UNGRADED ||
    device.final_grade?.toUpperCase() === UNGRADED
  )
}

/** Badge variant for a device's grade/status; UNGRADED drives stay neutral. */
export function deviceBadgeVariant(device: DeviceRecord): BadgeVariant {
  if (isUngradedDevice(device)) {
    return "outline"
  }
  return healthBadgeVariant(device.health_status, device.health_grade)
}

/** Letter grade for display; "Ungraded" instead of a letter for UNGRADED drives. */
export function formatGradeLabel(device: DeviceRecord): string {
  if (isUngradedDevice(device)) {
    return "Ungraded"
  }
  return device.health_grade ?? device.final_grade ?? "—"
}

export function formatHealthLabel(device: DeviceRecord): string {
  if (isUngradedDevice(device)) {
    return "Ungraded"
  }
  if (device.health_grade) {
    return device.health_grade
  }
  return device.health_status ?? "—"
}

export function formatHealthScore(device: DeviceRecord): string | number {
  if (isUngradedDevice(device)) {
    return "—"
  }
  return device.health_score ?? "—"
}

/**
 * Tri-state certification label: Yes (A/B/C), Advisory (D), No (F).
 * Falls back to the binary `is_certified` flag for older APIs.
 */
export function formatCertification(device: DeviceRecord): string {
  if (isUngradedDevice(device)) {
    return "Ungraded"
  }
  const raw = String(device.certification ?? device.revert_certified ?? "")
    .trim()
    .toLowerCase()
  if (raw === "true") {
    return "Yes"
  }
  if (raw === "advisory") {
    return "Advisory"
  }
  if (raw === "false") {
    return "No"
  }
  if (device.is_certified == null) {
    return "—"
  }
  return device.is_certified ? "Yes" : "No"
}

export function warningFlags(device: DeviceRecord): string[] {
  return (device.warning_flags ?? []).filter(Boolean)
}
