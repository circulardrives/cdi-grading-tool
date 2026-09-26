/**
 * Drive rows for the Drives page: the latest scan of every bench, flattened
 * into one list with the display values precomputed (so sorting, filtering,
 * and rendering hundreds of rows stays cheap).
 */
import { useMemo } from "react"

import {
  gradeOf,
  useBenchNames,
  useBenchScope,
  type GradeLetter,
} from "@/components/ui-cdi"
import { useDevicesQuery, useFleetDevicesQuery } from "@/hooks/use-cdi-queries"
import { deviceRowKeys } from "@/lib/drive-labels"
import type { DeviceRecord, DriveClass, FleetHost } from "@/lib/types"

import {
  capacityLabel,
  driveType,
  friendlyModel,
  modelNumber,
  powerOnHours,
  serialOf,
  shortDevicePath,
  spare,
  writesUsed,
} from "./drive-format"

/** URL/bench-filter id for the bench this dashboard runs on (machine_id null). */
export const THIS_BENCH_ID = "local"

export type DriveRow = {
  key: string
  device: DeviceRecord
  /** Registered bench id, or null for the bench this dashboard runs on. */
  benchId: string | null
  benchName: string
  serial: string
  model: string
  name: string
  capacity: string
  type: DriveClass
  grade: GradeLetter | null
  hours: number | null
  writes: number | null
  spare: number | null
  /** "nvme1" */
  slot: string
  /** When the scan that found this drive ran (ISO), if known. */
  scannedAt: string | null
  /** Lower-case text the search box matches against. */
  haystack: string
}

export function benchFilterId(benchId: string | null): string {
  return benchId ?? THIS_BENCH_ID
}

/** One drive's display row (also used by the drive details page). */
export function driveRowOf(
  device: DeviceRecord,
  {
    key,
    benchName,
    scannedAt,
  }: { key: string; benchName: string; scannedAt: string | null }
): DriveRow {
  const serial = serialOf(device)
  const model = modelNumber(device)
  const name = friendlyModel(device)
  const slot = shortDevicePath(device)
  return {
    key,
    device,
    benchId: device.machine_id ?? null,
    benchName,
    serial,
    model,
    name,
    capacity: capacityLabel(device),
    type: driveType(device),
    grade: gradeOf(device),
    hours: powerOnHours(device),
    writes: writesUsed(device),
    spare: spare(device),
    slot,
    scannedAt: device.scan_timestamp ?? scannedAt,
    haystack: [serial, model, name, device.vendor, benchName, slot]
      .filter(Boolean)
      .join(" ")
      .toLowerCase(),
  }
}

export type DriveRowsResult = {
  rows: DriveRow[]
  /** Benches in the latest data, for problem lines. */
  hosts: FleetHost[]
  isLoading: boolean
  error: unknown
  refetch: () => void
}

/** Every drive from the latest scans, limited to the header bench scope. */
export function useDriveRows(): DriveRowsResult {
  const { scopeId } = useBenchScope()
  const nameOf = useBenchNames()

  const fleetQuery = useFleetDevicesQuery()
  // `null` = the API predates the all-benches view: show one bench instead.
  const fleetMissing = fleetQuery.isSuccess && fleetQuery.data === null
  const singleQuery = useDevicesQuery(scopeId, fleetMissing)

  const hosts = useMemo(
    () =>
      (fleetQuery.data?.hosts ?? []).filter(
        (host) => !scopeId || host.machine_id === scopeId
      ),
    [fleetQuery.data, scopeId]
  )

  const rows = useMemo(() => {
    let devices: DeviceRecord[]
    const scannedAtByBench = new Map<string | null, string | null>()
    if (fleetMissing) {
      const single = singleQuery.data
      devices = (single?.devices ?? []).map((device) => ({
        ...device,
        machine_id: scopeId,
      }))
      scannedAtByBench.set(scopeId, single?.scanned_at ?? null)
    } else {
      for (const host of fleetQuery.data?.hosts ?? []) {
        scannedAtByBench.set(host.machine_id, host.scanned_at)
      }
      devices = (fleetQuery.data?.devices ?? []).filter(
        (device) => !scopeId || device.machine_id === scopeId
      )
    }

    const keys = deviceRowKeys(devices)
    return devices.map((device) => {
      const benchId = device.machine_id ?? null
      return driveRowOf(device, {
        key: keys.get(device) ?? serialOf(device),
        benchName: nameOf(benchId, device.machine_name),
        scannedAt: scannedAtByBench.get(benchId) ?? null,
      })
    })
  }, [fleetMissing, fleetQuery.data, singleQuery.data, scopeId, nameOf])

  const active = fleetMissing ? singleQuery : fleetQuery
  return {
    rows,
    hosts,
    isLoading: fleetQuery.isLoading || (fleetMissing && singleQuery.isLoading),
    // An old single-bench API answers "No scan cached" before the first scan.
    error:
      active.error instanceof Error &&
      active.error.message.includes("No scan cached")
        ? null
        : active.error,
    refetch: () => void active.refetch(),
  }
}
