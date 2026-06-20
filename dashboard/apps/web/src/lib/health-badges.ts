import type { DeviceRecord } from "@/lib/types"

export function healthBadgeVariant(
  status?: string,
  grade?: string
): "default" | "secondary" | "destructive" | "outline" {
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

export function formatHealthLabel(device: DeviceRecord): string {
  if (device.health_grade) {
    return device.health_grade
  }
  return device.health_status ?? "—"
}
