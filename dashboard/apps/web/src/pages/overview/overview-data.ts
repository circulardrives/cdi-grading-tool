/**
 * Overview data: the benches and drives in the current scope, plus the plain
 * sentences the page shows ("14 drives on 2 benches", "All 14 certified …").
 *
 * Reads the fleet view (every bench's latest scan). Older APIs without it fall
 * back to the one bench this dashboard talks to, as the pre-redesign page did.
 */
import { useEffect, useMemo } from "react"

import {
  countByGrade,
  driveNote,
  fleetHostName,
  gradeOf,
  gradeReason,
  useBenchScope,
  useBenchNames,
  type GradeLetter,
} from "@/components/ui-cdi"
import {
  useDevicesQuery,
  useFleetDevicesQuery,
  useHealthQuery,
  useMachinesQuery,
  useScanAllStatus,
} from "@/hooks/use-cdi-queries"
import type { DeviceRecord, MachineStatus } from "@/lib/types"

/** Quiet background refresh so the page stays current on a wall monitor. */
const REFRESH_MS = 60_000

export type OverviewBench = {
  key: string
  machineId: string | null
  name: string
  status: MachineStatus | string
  error: string | null
  scannedAt: string | null
  driveCount: number
  counts: Record<GradeLetter, number>
}

export type OverviewDrive = {
  key: string
  device: DeviceRecord
  grade: GradeLetter | null
  benchName: string
  machineId: string | null
}

export type OverviewData = {
  isLoading: boolean
  error: unknown
  retry: () => void
  scanning: boolean
  /** Name of the scoped bench, or null for all benches. */
  scopeName: string | null
  scopeId: string | null
  benches: OverviewBench[]
  drives: OverviewDrive[]
  counts: Record<GradeLetter, number>
}

function emptyCounts(): Record<GradeLetter, number> {
  return countByGrade([])
}

export function useOverviewData(): OverviewData {
  const { scopeId, scopedBench } = useBenchScope()
  const nameOf = useBenchNames()
  const healthQuery = useHealthQuery()
  const machinesQuery = useMachinesQuery()
  const fleetQuery = useFleetDevicesQuery()
  // `null` = this API predates the fleet view; read one bench instead.
  const singleBench = fleetQuery.isSuccess && fleetQuery.data === null
  const devicesQuery = useDevicesQuery(scopeId, singleBench)
  const scanAll = useScanAllStatus()

  const activeQuery = singleBench ? devicesQuery : fleetQuery
  const refetch = activeQuery.refetch

  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refetch()
      }
    }, REFRESH_MS)
    return () => window.clearInterval(id)
  }, [refetch])

  const machines = machinesQuery.data
  const thisBench = healthQuery.data?.hostname ?? null
  const healthStatus = healthQuery.data?.status

  const { benches, drives } = useMemo(() => {
    if (singleBench) {
      const scan = devicesQuery.data
      const name = nameOf(scopeId, scopedBench?.name)
      const devices = scan?.devices ?? []
      const bench: OverviewBench = {
        key: scopeId ?? "this-bench",
        machineId: scopeId,
        name,
        status: scopedBench?.status ?? (healthStatus ? "reachable" : "unknown"),
        error: null,
        scannedAt: scan?.scanned_at ?? null,
        driveCount: devices.length,
        counts: countByGrade(devices),
      }
      return {
        benches: scan || scopedBench ? [bench] : [],
        drives: devices.map((device, index) => ({
          key: `${bench.key}-${index}`,
          device,
          grade: gradeOf(device),
          benchName: name,
          machineId: scopeId,
        })),
      }
    }

    const fleet = fleetQuery.data
    const inScope = (machineId: string | null) =>
      !scopeId || machineId === scopeId
    const hosts = (fleet?.hosts ?? []).filter((host) =>
      inScope(host.machine_id)
    )
    const devices = (fleet?.devices ?? []).filter((device) =>
      inScope(device.machine_id)
    )
    const benchRows: OverviewBench[] = hosts.map((host) => {
      const own = devices.filter((d) => d.machine_id === host.machine_id)
      return {
        key: host.machine_id ?? "this-bench",
        machineId: host.machine_id,
        name: fleetHostName(host, machines, thisBench),
        status: host.status,
        error: host.error,
        scannedAt: host.scanned_at,
        driveCount: own.length || host.device_count,
        counts: countByGrade(own),
      }
    })
    const names = new Map(benchRows.map((b) => [b.machineId, b.name]))
    return {
      benches: benchRows,
      drives: devices.map((device, index) => ({
        key: `${device.machine_id ?? "this-bench"}-${index}`,
        device,
        grade: gradeOf(device),
        benchName:
          names.get(device.machine_id) ??
          nameOf(device.machine_id, device.machine_name),
        machineId: device.machine_id,
      })),
    }
  }, [
    singleBench,
    devicesQuery.data,
    fleetQuery.data,
    scopeId,
    scopedBench,
    nameOf,
    machines,
    thisBench,
    healthStatus,
  ])

  const counts = useMemo(() => {
    const result = emptyCounts()
    for (const drive of drives) {
      if (drive.grade) {
        result[drive.grade] += 1
      }
    }
    return result
  }, [drives])

  return {
    // isPending (not isLoading): a retry paused in a background tab must not
    // read as "no drives".
    isLoading: fleetQuery.isPending || (singleBench && devicesQuery.isPending),
    error: activeQuery.error,
    retry: () => void refetch(),
    scanning: scanAll.pending,
    scopeName: scopeId
      ? (benches[0]?.name ?? nameOf(scopeId, scopedBench?.name))
      : null,
    scopeId,
    benches,
    drives,
    counts,
  }
}

// ---------------------------------------------------------------------------
// Sentences
// ---------------------------------------------------------------------------

function plural(count: number, word: string, many = `${word}s`): string {
  return `${count} ${count === 1 ? word : many}`
}

/** "14 drives on 2 benches" / "8 drives on bench-01". */
export function headline(
  driveCount: number,
  benches: OverviewBench[],
  scopeName: string | null
): string {
  if (driveCount === 0) {
    return "No drives scanned yet"
  }
  const drives = plural(driveCount, "drive")
  if (scopeName) {
    return `${drives} on ${scopeName}`
  }
  if (benches.length === 1) {
    return `${drives} on ${benches[0]!.name}`
  }
  return `${drives} on ${plural(benches.length, "bench", "benches")}`
}

function benchesAnswering(benches: OverviewBench[]): string | null {
  if (benches.length === 0) {
    return null
  }
  const answering = benches.filter(
    (bench) => bench.status === "reachable" && !bench.error
  ).length
  if (benches.length === 1) {
    return answering === 1
      ? `${benches[0]!.name} answering`
      : `${benches[0]!.name} not answering`
  }
  if (answering === benches.length) {
    return benches.length === 2
      ? "both benches answering"
      : `all ${benches.length} benches answering`
  }
  return `${answering} of ${benches.length} benches answering`
}

/** "All 14 certified for reuse · nothing failed · both benches answering". */
export function statusLine(
  counts: Record<GradeLetter, number>,
  benches: OverviewBench[]
): string {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0)
  const parts: string[] = []
  if (total === 0) {
    parts.push("Press Scan all benches to grade every drive")
  } else {
    const certified = counts.A + counts.B + counts.C
    if (certified === total) {
      parts.push(
        total === 1 ? "Certified for reuse" : `All ${total} certified for reuse`
      )
    } else {
      parts.push(`${certified} of ${total} certified for reuse`)
    }
    parts.push(
      counts.F === 0 ? "nothing failed" : `${counts.F} failed — do not reuse`
    )
    if (counts.UNGRADED > 0) {
      parts.push(`${counts.UNGRADED} couldn't be graded`)
    }
  }
  const answering = benchesAnswering(benches)
  if (answering) {
    parts.push(answering)
  }
  return parts.join(" · ")
}

/** "9:00 AM", or "Sep 24, 9:00 AM" for another day. */
export function formatScanTime(iso: string, now = new Date()): string | null {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) {
    return null
  }
  const time = at.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  if (at.toDateString() === now.toDateString()) {
    return time
  }
  return `${at.toLocaleDateString([], { month: "short", day: "numeric" })}, ${time}`
}

// ---------------------------------------------------------------------------
// Worth a look
// ---------------------------------------------------------------------------

const LOOK_ORDER: Record<GradeLetter, number> = {
  F: 0,
  UNGRADED: 1,
  D: 2,
  C: 3,
  B: 4,
  A: 5,
}

/** Drives that aren't an A or carry a note, worst first. */
export function worthALook(drives: OverviewDrive[]): OverviewDrive[] {
  return drives
    .filter(
      (drive) =>
        (drive.grade != null && drive.grade !== "A") ||
        driveNote(drive.device) != null
    )
    .sort(
      (a, b) =>
        LOOK_ORDER[a.grade ?? "A"] - LOOK_ORDER[b.grade ?? "A"] ||
        a.benchName.localeCompare(b.benchName) ||
        slotOf(a.device).localeCompare(slotOf(b.device), undefined, {
          numeric: true,
        })
    )
}

/** Why the drive is on the list: the grade reason, and a separate note. */
export function whyLines(drive: OverviewDrive): {
  reason: string | null
  note: string | null
} {
  const note = driveNote(drive.device)
  const reason =
    drive.grade && drive.grade !== "A" ? gradeReason(drive.device) : null
  return { reason, note: note && note !== reason ? note : null }
}

/** "/dev/nvme1" → "nvme1". */
export function slotOf(device: DeviceRecord): string {
  return (device.dut ?? "").replace(/^\/dev\//, "").trim()
}
