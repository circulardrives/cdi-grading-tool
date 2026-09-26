/**
 * This drive's grade across the recent saved scans of its bench. Light on
 * requests: one short history list per bench plus the newest few saved scans,
 * all cached and shared by every drive on that bench.
 */
import { useQueries, useQuery } from "@tanstack/react-query"

import { gradeOf, type GradeLetter } from "@/components/ui-cdi"
import { getHistory, listHistory } from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"
import type { HistorySummary } from "@/lib/types"

/** Saved scans looked at per drive. */
const SCANS_TO_CHECK = 5
/** The unfiltered list mixes benches; fetch enough to find this bench's scans. */
const LOCAL_LIST_LIMIT = 40

export type DriveHistoryEntry = {
  scanId: string
  scannedAt: string
  grade: GradeLetter | null
}

export type DriveHistory = {
  /** Newest saved scan of the drive's bench (for the scan report). */
  latestScanId: string | null
  /** Newest first; only scans that contain this drive. */
  entries: DriveHistoryEntry[]
  isLoading: boolean
  isError: boolean
}

export function useDriveHistory(
  benchId: string | null,
  serial: string,
  devicePath: string | undefined,
  enabled: boolean
): DriveHistory {
  const listQuery = useQuery({
    // "history" prefix: refreshed with the rest of the history after a scan.
    queryKey: ["history", "drives-panel", benchId ?? "local"],
    queryFn: async (): Promise<HistorySummary[]> => {
      if (benchId) {
        return listHistory(benchId, { limit: SCANS_TO_CHECK })
      }
      const all = await listHistory(null, { limit: LOCAL_LIST_LIMIT })
      return all.filter((entry) => !entry.machine_id).slice(0, SCANS_TO_CHECK)
    },
    enabled,
    staleTime: 30_000,
  })

  const scans = listQuery.data ?? []
  const details = useQueries({
    queries: scans.map((scan) => ({
      queryKey: queryKeys.historyDetail(scan.id),
      queryFn: () => getHistory(scan.id),
      enabled: enabled && Boolean(serial),
      // Saved scans never change.
      staleTime: Infinity,
    })),
  })

  const entries: DriveHistoryEntry[] = []
  scans.forEach((scan, index) => {
    const detail = details[index]?.data
    if (!detail) {
      return
    }
    const matches = detail.devices.filter(
      (device) =>
        String(device.serial_number ?? "").trim() === serial && serial !== ""
    )
    const device =
      matches.find((d) => d.dut === devicePath) ?? matches[0] ?? null
    if (device) {
      entries.push({
        scanId: scan.id,
        scannedAt: scan.scanned_at,
        grade: gradeOf(device),
      })
    }
  })

  return {
    latestScanId: scans[0]?.id ?? null,
    entries,
    isLoading: listQuery.isLoading || details.some((query) => query.isLoading),
    isError: listQuery.isError,
  }
}
