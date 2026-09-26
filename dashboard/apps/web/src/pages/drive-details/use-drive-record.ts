/**
 * The drive the details page shows: found in the latest scan of its bench
 * (all-benches data, or the single-bench API on older backends) by serial,
 * and by slot when two drives on the bench share a serial. Ignores the
 * header bench scope — the URL names the bench.
 */
import { useMemo } from "react"

import { useBenchNames } from "@/components/ui-cdi"
import { useDevicesQuery, useFleetDevicesQuery } from "@/hooks/use-cdi-queries"
import { deviceRowKeys } from "@/lib/drive-labels"
import type { DeviceRecord } from "@/lib/types"
import { serialOf, shortDevicePath } from "@/pages/drives/drive-format"
import { driveRowOf, type DriveRow } from "@/pages/drives/use-drive-rows"

import { benchIdFromKey, NO_SERIAL } from "./drive-details-href"

export type DriveRecordResult = {
  row: DriveRow | null
  /** Other drives on the bench reporting the same serial. */
  sameSerial: number
  isLoading: boolean
  error: unknown
  refetch: () => void
}

export function useDriveRecord(
  benchKey: string,
  serialParam: string,
  devParam: string | null
): DriveRecordResult {
  const benchId = benchIdFromKey(benchKey)
  const nameOf = useBenchNames()
  const fleetQuery = useFleetDevicesQuery()
  const fleetMissing = fleetQuery.isSuccess && fleetQuery.data === null
  const singleQuery = useDevicesQuery(benchId, fleetMissing)

  const result = useMemo(() => {
    let devices: DeviceRecord[]
    let scannedAt: string | null
    if (fleetMissing) {
      devices = (singleQuery.data?.devices ?? []).map((device) => ({
        ...device,
        machine_id: benchId,
      }))
      scannedAt = singleQuery.data?.scanned_at ?? null
    } else {
      devices = (fleetQuery.data?.devices ?? []).filter(
        (device) => (device.machine_id ?? null) === benchId
      )
      scannedAt =
        fleetQuery.data?.hosts.find(
          (host) => (host.machine_id ?? null) === benchId
        )?.scanned_at ?? null
    }

    const wanted = serialParam === NO_SERIAL ? "" : serialParam.toLowerCase()
    const matches = devices.filter(
      (device) => serialOf(device).toLowerCase() === wanted
    )
    const device =
      (devParam
        ? matches.find((d) => shortDevicePath(d) === devParam)
        : undefined) ??
      matches[0] ??
      null
    if (!device) {
      return { row: null, sameSerial: 0 }
    }
    const keys = deviceRowKeys(devices)
    return {
      row: driveRowOf(device, {
        key: keys.get(device) ?? serialOf(device),
        benchName: nameOf(benchId, device.machine_name),
        scannedAt,
      }),
      sameSerial: matches.length - 1,
    }
  }, [
    fleetMissing,
    fleetQuery.data,
    singleQuery.data,
    benchId,
    serialParam,
    devParam,
    nameOf,
  ])

  const active = fleetMissing ? singleQuery : fleetQuery
  return {
    ...result,
    isLoading: fleetQuery.isLoading || (fleetMissing && singleQuery.isLoading),
    error: active.error,
    refetch: () => void active.refetch(),
  }
}
