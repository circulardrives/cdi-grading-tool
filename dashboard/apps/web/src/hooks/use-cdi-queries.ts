import { useEffect, useState } from "react"
import {
  useInfiniteQuery,
  useMutation,
  useMutationState,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { toast } from "sonner"

import {
  ApiError,
  generateReport,
  getDevices,
  getFleetDevices,
  getHealth,
  getHistory,
  getSelfTestStatus,
  isNotFoundError,
  listHistory,
  listJobs,
  listMachines,
  listReports,
  scanAllHosts,
} from "@/lib/api"
import { fleetScanToast } from "@/lib/host-utils"
import { queryKeys } from "@/lib/query-keys"
import {
  deliverReport,
  describeReportError,
  loadLocalReports,
  localReportsAsList,
  OLD_API_REPORT_MESSAGE,
  reportFileOf,
  reportIgnoredSource,
  reportReadyMessage,
  saveLocalReport,
} from "@/lib/report-utils"
import type { ReportFormat, ReportListEntry } from "@/lib/types"

export function useHealthQuery() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: getHealth,
  })
}

export function useDevicesQuery(machineId?: string | null, enabled = true) {
  return useQuery({
    queryKey: queryKeys.devices(machineId),
    queryFn: () => getDevices(false, machineId),
    enabled,
  })
}

export function useMachinesQuery() {
  return useQuery({
    queryKey: queryKeys.machines,
    queryFn: listMachines,
  })
}

/**
 * Cached drives from every registered host. Resolves to `null` when the API
 * predates the fleet endpoint (404), so pages can fall back to one host.
 */
export function useFleetDevicesQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.fleetDevices,
    queryFn: async () => {
      try {
        return await getFleetDevices()
      } catch (error) {
        if (isNotFoundError(error)) {
          return null
        }
        throw error
      }
    },
    enabled,
  })
}

const SCAN_ALL_MUTATION_KEY = ["fleet", "scan-all"] as const

/**
 * Scans every host (POST /fleet/scan). Registered with a
 * mutation key so the in-progress state is visible on every page.
 */
export function useScanAllHostsMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: SCAN_ALL_MUTATION_KEY,
    mutationFn: scanAllHosts,
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.fleetDevices, data)
      const toastMessage = fleetScanToast(data)
      if (toastMessage.ok) {
        toast.success(toastMessage.text)
      } else {
        toast.warning(toastMessage.text)
      }
    },
    onError: (error) => {
      toast.error(
        isNotFoundError(error)
          ? "Scan all hosts needs a newer CDI Health on this bench"
          : error instanceof Error
            ? error.message
            : "Scan all hosts failed"
      )
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.machines }),
        queryClient.invalidateQueries({ queryKey: ["devices"] }),
        queryClient.invalidateQueries({ queryKey: ["history"] }),
      ]),
  })
}

/** Whether a "Scan all hosts" run is in flight anywhere, and since when. */
export function useScanAllStatus(): {
  pending: boolean
  elapsedSeconds: number
} {
  const startedAt = useMutationState({
    filters: { mutationKey: SCAN_ALL_MUTATION_KEY, status: "pending" },
    select: (mutation) => mutation.state.submittedAt,
  })
  const since = startedAt.length > 0 ? startedAt[startedAt.length - 1] : null
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (since == null) {
      return
    }
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [since])

  return {
    pending: since != null,
    elapsedSeconds:
      since != null ? Math.max(0, Math.floor((now - since) / 1000)) : 0,
  }
}

/** API page size for scan history (server allows up to 500). */
export const HISTORY_PAGE_SIZE = 50

/** Paginated scan history; a short page means there is nothing more to load. */
export function useHistoryPagesQuery(machineId?: string | null) {
  return useInfiniteQuery({
    queryKey: queryKeys.historyPages(machineId),
    queryFn: ({ pageParam }) =>
      listHistory(machineId, { limit: HISTORY_PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length < HISTORY_PAGE_SIZE
        ? undefined
        : allPages.reduce((count, page) => count + page.length, 0),
  })
}

export function useHistoryDetailQuery(scanId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.historyDetail(scanId),
    queryFn: () => getHistory(scanId),
    enabled: Boolean(scanId) && enabled,
    // A deleted snapshot will not reappear; surface the 404 immediately.
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.status === 404) && failureCount < 1,
  })
}

/** Jobs on one bench (`null` = this bench). */
export function useJobsQuery(machineId?: string | null) {
  return useQuery({
    queryKey: queryKeys.jobs(machineId),
    queryFn: () => listJobs(machineId),
  })
}

/** Self-test status on one bench (`null` = this bench). */
export function useSelfTestStatusQuery(
  machineId?: string | null,
  enabled = true
) {
  return useQuery({
    queryKey: queryKeys.selfTestStatus(machineId),
    queryFn: () => getSelfTestStatus(undefined, machineId),
    enabled,
  })
}

export type ReportsList = {
  reports: ReportListEntry[]
  /** False when the API has no GET /reports and the list lives in this browser. */
  savedOnServer: boolean
}

/**
 * Recent reports from GET /reports; falls back to the browser-only list
 * when the API predates that endpoint (404).
 */
export function useReportsQuery() {
  return useQuery({
    queryKey: queryKeys.reports,
    queryFn: async (): Promise<ReportsList> => {
      try {
        return { reports: await listReports(), savedOnServer: true }
      } catch (error) {
        if (isNotFoundError(error)) {
          return {
            reports: localReportsAsList(loadLocalReports()),
            savedOnServer: false,
          }
        }
        throw error
      }
    },
  })
}

/** POST /reports; refreshes the recent-reports list afterwards. */
export function useGenerateReportMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: generateReport,
    onSuccess: (result, variables) => {
      // Browser copy only matters for older APIs without GET /reports.
      saveLocalReport(result)
      const invalidations = [
        queryClient.invalidateQueries({ queryKey: queryKeys.reports }),
      ]
      if (!variables.source || variables.source === "scan") {
        invalidations.push(
          queryClient.invalidateQueries({ queryKey: ["devices"] }),
          queryClient.invalidateQueries({ queryKey: queryKeys.health })
        )
      }
      return Promise.all(invalidations)
    },
  })
}

/**
 * "Report" actions for one saved scan (History page): makes the report from
 * that scan, then opens or downloads it.
 */
export function useSavedScanReport() {
  const generate = useGenerateReportMutation()
  const [busyKey, setBusyKey] = useState<string | null>(null)

  const makeReport = async (scanId: string, format: ReportFormat) => {
    setBusyKey(`${scanId}:${format}`)
    try {
      const result = await generate.mutateAsync({
        format,
        source: "history",
        history_ids: [scanId],
      })
      if (reportIgnoredSource("history", result)) {
        toast.warning(OLD_API_REPORT_MESSAGE)
      } else {
        toast.success(reportReadyMessage(result))
      }
      await deliverReport(reportFileOf(result), format)
    } catch (error) {
      toast.error(describeReportError(error))
    } finally {
      setBusyKey(null)
    }
  }

  return {
    makeReport,
    isBusy: (scanId: string, format?: ReportFormat) =>
      format
        ? busyKey === `${scanId}:${format}`
        : busyKey?.startsWith(`${scanId}:`) === true,
    anyBusy: busyKey != null,
  }
}

export function useInvalidateCdiQueries() {
  const queryClient = useQueryClient()

  return {
    invalidateDevices: (machineId?: string | null) =>
      queryClient.invalidateQueries({
        queryKey: machineId ? queryKeys.devices(machineId) : ["devices"],
      }),
    // Host edits change names, status, and tokens shown in the fleet view.
    invalidateMachines: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.machines }),
        queryClient.invalidateQueries({ queryKey: ["fleet"] }),
      ]),
    invalidateFleet: () =>
      queryClient.invalidateQueries({ queryKey: ["fleet"] }),
    invalidateHistory: () =>
      queryClient.invalidateQueries({ queryKey: ["history"] }),
    invalidateHealth: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.health }),
    invalidateJobs: (machineId?: string | null) =>
      queryClient.invalidateQueries({
        queryKey:
          machineId !== undefined ? queryKeys.jobs(machineId) : ["jobs"],
      }),
    invalidateSelfTest: (machineId?: string | null) =>
      queryClient.invalidateQueries({
        queryKey:
          machineId !== undefined
            ? queryKeys.selfTestStatus(machineId)
            : ["self-test-status"],
      }),
    invalidateReports: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.reports }),
    invalidateAfterScan: (machineId?: string | null) =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: machineId ? queryKeys.devices(machineId) : ["devices"],
        }),
        queryClient.invalidateQueries({ queryKey: queryKeys.machines }),
        queryClient.invalidateQueries({ queryKey: ["fleet"] }),
        queryClient.invalidateQueries({ queryKey: ["history"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.health }),
      ]),
  }
}
