import type { JobResponse, SelfTestDeviceStatus, SelfTestResultEntry } from "@/lib/types"

export const LOG_WAIT_POLL_INTERVAL_MS = 1500
export const MAX_LOG_WAIT_POLLS = 40

export function formatStatus(entry: SelfTestDeviceStatus): string {
  if (entry.in_progress) {
    if (entry.progress_percent != null) {
      return `in_progress (${entry.progress_percent}%)`
    }
    if (entry.current_completion != null && entry.current_completion > 0) {
      return `in_progress (${entry.current_completion}%)`
    }
    return entry.status ?? "in_progress"
  }
  if (entry.passed) {
    return "passed"
  }
  if (entry.failed) {
    return "failed"
  }
  if (entry.aborted) {
    return "aborted"
  }
  return entry.status ?? "unknown"
}

export function formatResultLabel(entry: SelfTestDeviceStatus): string {
  if (entry.latest_result?.result) {
    return entry.latest_result.result
  }
  if (entry.passed) {
    return "Success"
  }
  if (entry.failed) {
    return "Failed"
  }
  if (entry.aborted) {
    return "Aborted"
  }
  return "—"
}

export function formatResultCode(entry: SelfTestDeviceStatus): string {
  const code = entry.latest_result?.result_code
  return code != null ? String(code) : "—"
}

export function formatTestType(entry: SelfTestDeviceStatus): string {
  if (entry.latest_result?.test_type) {
    return entry.latest_result.test_type
  }
  if (entry.test_type) {
    return entry.test_type
  }
  return "—"
}

export function lookupSerial(
  devicePath: string | undefined,
  serialByController: Map<string, string>
): string {
  if (!devicePath) {
    return "—"
  }
  return serialByController.get(devicePath) ?? "—"
}

export function summarizeJob(job: JobResponse): string {
  const summary = job.result?.summary
  if (!summary) {
    return job.status
  }
  const completed = summary.completed ?? 0
  const started = summary.started ?? 0
  const failedToStart = summary.failed_to_start ?? 0
  return `${completed}/${started} completed, ${failedToStart} failed to start`
}

export function hasLogData(entry: SelfTestDeviceStatus): boolean {
  return Boolean(entry.latest_result) || (entry.recent_results?.length ?? 0) > 0
}

export function hasStaleSelfTestApi(devices: SelfTestDeviceStatus[]): boolean {
  return devices.some(
    (entry) =>
      entry.supported &&
      entry.latest_result === undefined &&
      entry.recent_results === undefined
  )
}

export function describeMissingLogs(entry: SelfTestDeviceStatus): string {
  if (entry.logs_message) {
    return entry.logs_message
  }
  if (entry.in_progress) {
    return "Self-test is still running on the device. Log Page 0x06 entries appear after completion."
  }
  if (entry.error) {
    return entry.error
  }
  if (!entry.supported) {
    return "This controller does not support NVMe device self-test."
  }
  if (entry.passed || entry.failed || entry.aborted) {
    return "The drive reported a result but no log entries were returned. Try Refresh status — the NVMe log can lag briefly after completion."
  }
  return "No self-test log entries on this controller yet. Run a short self-test to populate Log Page 0x06."
}

export function logEntriesForDevice(entry: SelfTestDeviceStatus): SelfTestResultEntry[] {
  if ((entry.recent_results?.length ?? 0) > 0) {
    return entry.recent_results ?? []
  }
  if (entry.latest_result) {
    return [entry.latest_result]
  }
  return []
}

export function buildSerialByController(
  devices: { dut?: string | null; serial_number?: string | null }[]
): Map<string, string> {
  const serialMap = new Map<string, string>()
  for (const device of devices) {
    const dut = String(device.dut ?? "")
    if (!dut.startsWith("/dev/nvme")) {
      continue
    }
    const controllerMatch = dut.match(/^(\/dev\/nvme\d+)/)
    const controller = controllerMatch?.[1] ?? dut
    if (device.serial_number && !serialMap.has(controller)) {
      serialMap.set(controller, device.serial_number)
    }
  }
  return serialMap
}

export function nvmeControllersFromDevices(
  devices: { dut?: string | null; transport_protocol?: string | null }[]
): string[] {
  const controllers = devices
    .filter((device) => device.transport_protocol === "NVMe")
    .map((device) => String(device.dut ?? ""))
    .filter((path) => path.startsWith("/dev/nvme"))
  return Array.from(new Set(controllers)).sort()
}
