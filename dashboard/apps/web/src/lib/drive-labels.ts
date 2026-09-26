import type { DeviceRecord, DriveClass } from "@/lib/types"

export function getReportCategory(device: DeviceRecord): DriveClass {
  if (device.report_category) {
    return device.report_category as DriveClass
  }

  const proto = device.transport_protocol ?? ""
  const media = device.media_type ?? ""
  const link = String(device.interface_link ?? "").toUpperCase()

  if (proto === "NVMe") {
    return "NVMe SSD"
  }
  if (proto === "ATA") {
    return media === "HDD" ? "SATA HDD" : "SATA SSD"
  }
  if (proto === "SCSI") {
    if (link.includes("SAS")) {
      return media === "HDD" ? "SAS HDD" : "SAS SSD"
    }
    if (link.includes("SATA")) {
      return media === "HDD" ? "SATA HDD" : "SATA SSD"
    }
    return media === "HDD" ? "SAS HDD" : "SAS SSD"
  }

  return "Other"
}

/**
 * Stable React keys for device rows: serial plus device path, so multipath
 * duplicates and drives without a serial do not collide. Falls back to the
 * row index only when both are missing, and suffixes exact repeats (e.g.
 * mock fixtures that reuse a serial and path) so keys stay unique.
 */
export function deviceRowKeys(devices: DeviceRecord[]): Map<DeviceRecord, string> {
  const seen = new Map<string, number>()
  const keys = new Map<DeviceRecord, string>()
  devices.forEach((device, index) => {
    const serial = String(device.serial_number ?? "").trim()
    const path = String(device.dut ?? "").trim()
    const base = serial || path ? `${serial}|${path}` : `row-${index}`
    const repeat = seen.get(base) ?? 0
    seen.set(base, repeat + 1)
    keys.set(device, repeat ? `${base}#${repeat}` : base)
  })
  return keys
}

export function countByDriveClass(devices: DeviceRecord[]): Record<DriveClass, number> {
  const counts: Record<DriveClass, number> = {
    "SATA HDD": 0,
    "SAS HDD": 0,
    "SATA SSD": 0,
    "SAS SSD": 0,
    "NVMe SSD": 0,
    Other: 0,
  }

  for (const device of devices) {
    counts[getReportCategory(device)] += 1
  }

  return counts
}

export const DRIVE_CLASS_ORDER: DriveClass[] = [
  "SATA HDD",
  "SAS HDD",
  "SATA SSD",
  "SAS SSD",
  "NVMe SSD",
  "Other",
]
