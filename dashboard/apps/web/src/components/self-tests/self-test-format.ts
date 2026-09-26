/**
 * Pure helpers for the Self-tests page: turning a bench's self-test status
 * and its saved scan into drive rows, and self-test results into plain words.
 */
import { getReportCategory } from "@/lib/drive-labels"
import type {
  DeviceRecord,
  SelfTestDeviceStatus,
  SelfTestResultEntry,
} from "@/lib/types"

export type TestType = "short" | "extended"

/** Fast polling while tests are starting or results are settling in. */
export const FAST_POLL_MS = 1500
/** While short tests run. */
export const RUNNING_POLL_MS = 3000
/** While only extended tests (hours) run. */
export const SLOW_POLL_MS = 10_000
/** Keep polling this long after a start (or a finish) for the log to catch up. */
export const SETTLE_MS = 60_000

const CONTROLLER = /^(\/dev\/nvme\d+)/

/** "/dev/nvme3n1" → "/dev/nvme3"; null for anything that isn't NVMe. */
export function controllerOf(path: string | null | undefined): string | null {
  const match = String(path ?? "").match(CONTROLLER)
  return match?.[1] ?? null
}

/** "/dev/nvme3" → "nvme3". */
export function slotOf(controller: string): string {
  return controller.replace(/^\/dev\//, "")
}

/** "Intel SSDPE2KE032T8" style name from the saved scan. */
export function driveTitle(device: DeviceRecord | null | undefined): string {
  const model = String(device?.model_number ?? "").trim()
  const vendor = String(device?.vendor ?? "").trim()
  const usefulVendor =
    vendor && !/^(unknown|not reported|n\/a)$/i.test(vendor) ? vendor : ""
  if (!model || /^not reported$/i.test(model)) {
    return usefulVendor ? `${usefulVendor} NVMe drive` : "NVMe drive"
  }
  if (
    usefulVendor &&
    !model.toLowerCase().includes(usefulVendor.toLowerCase())
  ) {
    const nice =
      usefulVendor.length > 3 && usefulVendor === usefulVendor.toUpperCase()
        ? usefulVendor[0] + usefulVendor.slice(1).toLowerCase()
        : usefulVendor
    return `${nice} ${model}`
  }
  return model
}

function toBytes(device: DeviceRecord): number | null {
  const bytes = Number(device.bytes)
  if (Number.isFinite(bytes) && bytes > 0) {
    return bytes
  }
  const gib = Number(device.gibibytes)
  if (Number.isFinite(gib) && gib > 0) {
    return gib * 1024 ** 3
  }
  return null
}

/** Marketing capacity: "7.68 TB", "960 GB". Empty when unknown. */
export function formatDriveCapacity(
  device: DeviceRecord | null | undefined
): string {
  const bytes = device ? toBytes(device) : null
  if (!bytes) {
    return ""
  }
  const tb = bytes / 1e12
  if (tb >= 1) {
    return `${Number(tb.toFixed(tb >= 10 ? 1 : 2))} TB`
  }
  return `${Math.round(bytes / 1e9)} GB`
}

// ---------------------------------------------------------------------------
// Rows
// ---------------------------------------------------------------------------

export type DriveRow = {
  /** Controller path, e.g. /dev/nvme3 — what the bench tests. */
  device: string
  slot: string
  serial: string
  title: string
  capacity: string
  /** Live self-test status (null when the bench didn't list this drive). */
  status: SelfTestDeviceStatus | null
  /** Why the checkbox is disabled, or null when the drive can be tested. */
  unavailable: string | null
}

export type BenchDrives = {
  rows: DriveRow[]
  /** SATA/SAS drives in the saved scan (not testable yet). */
  otherDrives: number
  /** Rows without a serial (no saved scan for that drive yet). */
  unnamed: number
}

/**
 * Drive rows for one bench: the drives its self-test status lists, named from
 * its saved scan, plus NVMe drives the scan saw that the bench no longer lists.
 */
export function buildDriveRows(
  statusDevices: SelfTestDeviceStatus[] | null,
  scanDevices: DeviceRecord[]
): BenchDrives {
  const scanByController = new Map<string, DeviceRecord>()
  let otherDrives = 0
  for (const device of scanDevices) {
    const controller = controllerOf(device.dut)
    if (controller && getReportCategory(device) === "NVMe SSD") {
      if (!scanByController.has(controller)) {
        scanByController.set(controller, device)
      }
    } else if (!controller) {
      otherDrives += 1
    }
  }

  const rows: DriveRow[] = []
  const seen = new Set<string>()
  for (const entry of statusDevices ?? []) {
    const controller = controllerOf(entry.device)
    if (!controller || seen.has(controller)) {
      continue
    }
    seen.add(controller)
    const scanned = scanByController.get(controller)
    rows.push({
      device: controller,
      slot: slotOf(controller),
      serial: String(scanned?.serial_number ?? "").trim(),
      title: driveTitle(scanned),
      capacity: formatDriveCapacity(scanned),
      status: entry,
      unavailable:
        entry.supported === false
          ? "This drive doesn't support self-tests"
          : null,
    })
  }

  // Only when the bench answered: otherwise every row would say "not found".
  if (statusDevices) {
    for (const [controller, scanned] of scanByController) {
      if (seen.has(controller)) {
        continue
      }
      rows.push({
        device: controller,
        slot: slotOf(controller),
        serial: String(scanned.serial_number ?? "").trim(),
        title: driveTitle(scanned),
        capacity: formatDriveCapacity(scanned),
        status: null,
        unavailable: "Not found on the bench now",
      })
    }
  }

  rows.sort((a, b) =>
    a.slot.localeCompare(b.slot, undefined, { numeric: true })
  )
  return {
    rows,
    otherDrives,
    unnamed: rows.filter((row) => !row.serial).length,
  }
}

// ---------------------------------------------------------------------------
// Status → words
// ---------------------------------------------------------------------------

export function isRunning(entry: SelfTestDeviceStatus | null): boolean {
  return Boolean(entry?.in_progress)
}

export function hasLogData(entry: SelfTestDeviceStatus): boolean {
  return Boolean(entry.latest_result) || (entry.recent_results?.length ?? 0) > 0
}

/** Older benches don't send the self-test log at all. */
export function hasStaleSelfTestApi(devices: SelfTestDeviceStatus[]): boolean {
  return devices.some(
    (entry) =>
      entry.supported &&
      entry.latest_result === undefined &&
      entry.recent_results === undefined
  )
}

/** Type of the test running now, from the drive or from what we started. */
export function runningType(
  entry: SelfTestDeviceStatus,
  started?: TestType
): TestType | null {
  const op = String(entry.current_operation ?? entry.status ?? "")
  if (/extended/i.test(op)) {
    return "extended"
  }
  if (/short/i.test(op)) {
    return "short"
  }
  return started ?? null
}

/** 0–100, or null when the drive doesn't say. */
export function runningPercent(entry: SelfTestDeviceStatus): number | null {
  const value = entry.progress_percent ?? entry.current_completion
  if (value == null || !Number.isFinite(Number(value))) {
    return null
  }
  return Math.max(0, Math.min(100, Math.round(Number(value))))
}

export type ResultKind = "passed" | "failed" | "aborted"

/** NVMe self-test result code → passed / failed / aborted. */
export function resultKind(entry: SelfTestResultEntry): ResultKind | null {
  const code = entry.result_code
  if (code === 0) {
    return "passed"
  }
  if (code === 5 || code === 6 || code === 7) {
    return "failed"
  }
  if (code != null && [1, 2, 3, 4, 8, 9].includes(code)) {
    return "aborted"
  }
  const text = String(entry.result ?? "").toLowerCase()
  if (text.startsWith("success")) {
    return "passed"
  }
  if (text.startsWith("failed")) {
    return "failed"
  }
  if (text.startsWith("aborted")) {
    return "aborted"
  }
  return null
}

/** One plain reason for a failed or aborted result. */
export function resultReason(entry: SelfTestResultEntry): string | null {
  switch (entry.result_code) {
    case 5:
      return "the drive reported a serious error"
    case 6:
    case 7:
      return "part of the drive failed the test"
    case 1:
      return "stopped before it finished"
    case 2:
      return "the drive was reset during the test"
    case 3:
    case 4:
      return "the drive was changed during the test"
    case 9:
      return "the drive was erased during the test"
    case 8:
      return "didn't finish"
    default:
      return null
  }
}

/** "short" / "extended" for a log entry, or null. */
export function entryType(entry: SelfTestResultEntry): TestType | null {
  if (entry.test_type_code === 2 || /extended/i.test(entry.test_type ?? "")) {
    return "extended"
  }
  if (entry.test_type_code === 1 || /short/i.test(entry.test_type ?? "")) {
    return "short"
  }
  return null
}

/** Latest finished result for a drive, from the status payload. */
export function latestResult(
  entry: SelfTestDeviceStatus | null
): SelfTestResultEntry | null {
  if (!entry) {
    return null
  }
  if (entry.latest_result) {
    return entry.latest_result
  }
  return entry.recent_results?.[0] ?? null
}

/**
 * "in the last hour", "3 h ago", "2 days ago". The bench estimates the time
 * from the drive's powered-on hours, so it is never more precise than that.
 */
export function formatTestedAgo(
  iso: string | null | undefined,
  now = Date.now()
): string | null {
  if (!iso) {
    return null
  }
  const time = Date.parse(iso)
  if (Number.isNaN(time)) {
    return null
  }
  const hours = Math.floor((now - time) / 3_600_000)
  if (hours < 1) {
    return "in the last hour"
  }
  if (hours < 24) {
    return `${hours} h ago`
  }
  const days = Math.floor(hours / 24)
  return days === 1 ? "yesterday" : `${days} days ago`
}

/** One line for the drive's row when the bench refused to start its test. */
export function startFailureReason(
  status: string | null | undefined,
  error: string | null | undefined
): string {
  const text = String(error ?? "").toLowerCase()
  if (status === "not_supported" || text.includes("not support")) {
    return "Couldn't start — this drive doesn't support self-tests"
  }
  if (text.includes("permission") || text.includes("denied")) {
    return "Couldn't start — the bench wasn't allowed to test this drive. Check CDI Health runs as an administrator there."
  }
  if (text.includes("no such") || text.includes("not found")) {
    return "Couldn't start — the bench can't find this drive. Check it's seated, then scan again."
  }
  return "Couldn't start — the drive didn't accept the test. Try again, or scan the bench first."
}

/**
 * Raised when we asked a bench for self-tests but CDI Health on this computer
 * is too old to pass the request on (it answers for its own drives instead).
 */
export class StaleBenchApiError extends Error {
  constructor(benchName: string) {
    super(
      `CDI Health on this computer is too old to run self-tests on ${benchName} — update it, or pick This bench`
    )
    this.name = "StaleBenchApiError"
  }
}
