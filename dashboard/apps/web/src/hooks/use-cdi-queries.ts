import { useQuery, useQueryClient } from "@tanstack/react-query"

import {
  getDevices,
  getHealth,
  getSelfTestStatus,
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
        queryClient.invalidateQueries({ queryKey: queryKeys.health }),
      ]),
  }
}
