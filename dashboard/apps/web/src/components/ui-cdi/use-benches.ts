/**
 * Bench hooks shared by the shell and pages.
 *
 * - useBenchScope()  → the header "All benches ▾" scope: { scopeId, setScope, scopedBench, benches }
 *                      scopeId null = all benches. Backed by lib/selected-host.ts (per tab).
 * - useBenchNames()  → (machineId, fallback?) => display name, incl. this bench (machine_id null)
 * - useLastScan()    → { at, label } for "Last scan 9:00 AM · both benches", respecting the scope
 */
import { useCallback, useMemo } from "react"

import { benchName, fleetHostName } from "@/components/ui-cdi/bench"
import {
  useFleetDevicesQuery,
  useHealthQuery,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import { hostHasAddress } from "@/lib/host-utils"
import { setSelectedHostId, useSelectedHostId } from "@/lib/selected-host"
import type { FleetHost, Machine } from "@/lib/types"

export type BenchScope = {
  /** Selected bench id, or null for all benches. */
  scopeId: string | null
  setScope: (machineId: string | null) => void
  /** The selected bench, when the scope is one bench. */
  scopedBench: Machine | null
  /** Benches the dashboard can scan (registered with an address), by name. */
  benches: Machine[]
  isLoading: boolean
}

/** The header scope switcher state. Pages filter their data by `scopeId`. */
export function useBenchScope(): BenchScope {
  const selectedId = useSelectedHostId()
  const machinesQuery = useMachinesQuery()

  const benches = useMemo(
    () =>
      (machinesQuery.data ?? [])
        .filter(hostHasAddress)
        .slice()
        .sort((a, b) => benchName(a).localeCompare(benchName(b))),
    [machinesQuery.data]
  )
  const scopedBench = selectedId
    ? (benches.find((bench) => bench.id === selectedId) ?? null)
    : null
  // A stale id (bench removed, or registry-only) reads as "all benches" once
  // the list has loaded.
  const scopeId =
    selectedId && (scopedBench || machinesQuery.isLoading) ? selectedId : null

  return {
    scopeId,
    setScope: setSelectedHostId,
    scopedBench,
    benches,
    isLoading: machinesQuery.isLoading,
  }
}

/**
 * Resolver for bench names on drive rows and fleet hosts. `machineId` null
 * is the bench this dashboard runs on (named from its /health hostname).
 */
export function useBenchNames(): (
  machineId: string | null | undefined,
  fallback?: string | null
) => string {
  const machines = useMachinesQuery().data
  const thisBench = useHealthQuery().data?.hostname ?? null
  return useCallback(
    (machineId, fallback) => {
      if (!machineId) {
        return fleetHostName(
          { machine_id: null, name: "", address: null },
          null,
          thisBench
        )
      }
      const machine = machines?.find((m) => m.id === machineId)
      return machine ? benchName(machine) : fallback?.trim() || "Unknown bench"
    },
    [machines, thisBench]
  )
}

export type LastScan = {
  /** Newest scan time, or null when nothing was scanned yet. */
  at: Date | null
  /** Which benches that covers: "both benches", "all 5 benches", "bench-01", … */
  label: string
}

/** Benches scanned within this window of the newest scan count as "that scan". */
const SAME_SCAN_WINDOW_MS = 15 * 60_000

export function summarizeLastScan(
  hosts: FleetHost[],
  nameOf: (host: FleetHost) => string
): LastScan {
  const scanned = hosts
    .map((host) => ({
      host,
      time: host.scanned_at ? Date.parse(host.scanned_at) : NaN,
    }))
    .filter((entry) => !Number.isNaN(entry.time))
  if (scanned.length === 0) {
    return { at: null, label: hosts.length ? "no bench scanned yet" : "" }
  }
  const newest = Math.max(...scanned.map((entry) => entry.time))
  const recent = scanned.filter(
    (entry) => newest - entry.time <= SAME_SCAN_WINDOW_MS
  )
  let label: string
  if (hosts.length > 1 && recent.length === hosts.length) {
    label = hosts.length === 2 ? "both benches" : `all ${hosts.length} benches`
  } else if (recent.length <= 2) {
    label = recent.map((entry) => nameOf(entry.host)).join(" and ")
  } else {
    label = `${recent.length} of ${hosts.length} benches`
  }
  return { at: new Date(newest), label }
}

/** "Last scan" for the header, limited to the scoped bench when one is picked. */
export function useLastScan(): LastScan {
  const fleet = useFleetDevicesQuery().data
  const { scopeId } = useBenchScope()
  const machines = useMachinesQuery().data
  const thisBench = useHealthQuery().data?.hostname ?? null

  return useMemo(() => {
    const hosts = (fleet?.hosts ?? []).filter(
      (host) => !scopeId || host.machine_id === scopeId
    )
    return summarizeLastScan(hosts, (host) =>
      fleetHostName(host, machines, thisBench)
    )
  }, [fleet, scopeId, machines, thisBench])
}
