import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"

import {
  ApiError,
  getDevices,
  getHealth,
  getHistory,
  getSelfTestStatus,
  listHistory,
  listJobs,
  listMachines,
} from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"

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

export function useJobsQuery() {
  return useQuery({
    queryKey: queryKeys.jobs,
    queryFn: listJobs,
  })
}

export function useSelfTestStatusQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.selfTestStatus,
    queryFn: () => getSelfTestStatus(),
    enabled,
  })
}

export function useInvalidateCdiQueries() {
  const queryClient = useQueryClient()

  return {
    invalidateDevices: (machineId?: string | null) =>
      queryClient.invalidateQueries({
        queryKey: machineId
          ? queryKeys.devices(machineId)
          : ["devices"],
      }),
    invalidateMachines: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.machines }),
    invalidateHistory: () =>
      queryClient.invalidateQueries({ queryKey: ["history"] }),
    invalidateHealth: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.health }),
    invalidateJobs: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs }),
    invalidateSelfTest: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.selfTestStatus }),
    invalidateAfterScan: (machineId?: string | null) =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: machineId ? queryKeys.devices(machineId) : ["devices"],
        }),
        queryClient.invalidateQueries({ queryKey: queryKeys.machines }),
        queryClient.invalidateQueries({ queryKey: ["history"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.health }),
      ]),
  }
}
