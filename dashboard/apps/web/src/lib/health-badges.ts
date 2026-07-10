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

export function formatHealthLabel(device: DeviceRecord): string {
  if (device.health_grade) {
    return device.health_grade
  }
  return device.health_status ?? "—"
}
