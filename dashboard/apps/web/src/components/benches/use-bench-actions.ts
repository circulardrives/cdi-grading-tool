/**
 * Row actions for the Benches page: scan one bench, check its connection,
 * and remember the last problem each one reported (shown under its row).
 */
import { useCallback, useEffect, useState } from "react"
import { useMutation, useMutationState } from "@tanstack/react-query"
import { toast } from "sonner"

import { benchName, describeRequestError } from "@/components/ui-cdi"
import { useInvalidateCdiQueries } from "@/hooks/use-cdi-queries"
import { scanDevices } from "@/lib/api"
import { checkHostConnection } from "@/lib/host-utils"
import type { Machine } from "@/lib/types"

const BENCH_SCAN_KEY = ["bench-scan"] as const

/** Problems from the latest check or scan, by bench id. Shared across the page. */
export function useBenchProblems() {
  const [problems, setProblems] = useState<Record<string, string>>({})
  const setProblem = useCallback((id: string, text: string | null) => {
    setProblems((current) => {
      if (text == null) {
        if (!(id in current)) {
          return current
        }
        const next = { ...current }
        delete next[id]
        return next
      }
      return { ...current, [id]: text }
    })
  }, [])
  return { problems, setProblem }
}

/**
 * Scans one registered bench (POST /scan with its id). Uses a mutation key so
 * a scan keeps showing as running if the technician leaves and comes back.
 */
export function useScanBench(
  onProblem: (id: string, text: string | null) => void
) {
  const { invalidateAfterScan } = useInvalidateCdiQueries()
  const mutation = useMutation({
    mutationKey: BENCH_SCAN_KEY,
    mutationFn: (machine: Machine) =>
      scanDevices({
        ignore_ata: false,
        ignore_nvme: false,
        ignore_scsi: false,
        machine_id: machine.id,
      }),
    onSuccess: (result, machine) => {
      onProblem(machine.id, null)
      const total = result.summary.total
      toast.success(
        `Scanned ${benchName(machine)} — ${total} drive${total === 1 ? "" : "s"}`
      )
    },
    onError: (error, machine) => {
      const name = benchName(machine)
      const text = describeRequestError(
        error,
        name,
        `Couldn't scan ${name} — try again`
      )
      onProblem(machine.id, text)
      toast.error(text)
    },
    onSettled: (_data, _error, machine) => invalidateAfterScan(machine.id),
  })

  // Every bench scan in flight (from this page or an earlier visit to it).
  const running = useMutationState({
    filters: { mutationKey: BENCH_SCAN_KEY, status: "pending" },
    select: (entry) => ({
      id: (entry.state.variables as Machine | undefined)?.id ?? "",
      since: entry.state.submittedAt,
    }),
  })

  return {
    scan: (machine: Machine) => mutation.mutate(machine),
    /** When this bench's scan started (ms), or null when it isn't scanning. */
    scanningSince: (id: string): number | null =>
      running.find((entry) => entry.id === id)?.since ?? null,
  }
}

export type BenchCheckResult = {
  /** The bench as the check left it, when the check reached the dashboard. */
  machine: Machine | null
  ok: boolean
  text: string
}

/** Runs a connection check and phrases the result as a toast + row problem. */
export function useCheckBench(
  onProblem: (id: string, text: string | null) => void
) {
  const { invalidateMachines } = useInvalidateCdiQueries()
  const [checking, setChecking] = useState<Set<string>>(() => new Set())

  const check = useCallback(
    async (
      machine: Pick<Machine, "id" | "name">,
      options: { prefix?: string; silent?: boolean } = {}
    ): Promise<BenchCheckResult | null> => {
      setChecking((current) => new Set(current).add(machine.id))
      try {
        const outcome = await checkHostConnection(machine)
        if (!outcome) {
          if (!options.silent) {
            toast.message(
              "This bench runs an older CDI Health that can't be checked — scan it instead"
            )
          }
          return null
        }
        onProblem(machine.id, outcome.ok ? null : outcome.text)
        const text = options.prefix
          ? `${options.prefix} — ${outcome.text}`
          : outcome.text
        if (!options.silent) {
          if (outcome.ok) {
            toast.success(text)
          } else {
            toast.warning(text)
          }
        }
        return { machine: outcome.machine, ok: outcome.ok, text }
      } finally {
        setChecking((current) => {
          const next = new Set(current)
          next.delete(machine.id)
          return next
        })
        await invalidateMachines()
      }
    },
    [invalidateMachines, onProblem]
  )

  return { check, isChecking: (id: string) => checking.has(id) }
}

/** Current time, refreshed every `intervalMs` (for "12 min ago" and timers). */
export function useNow(intervalMs: number, active = true): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) {
      return
    }
    const id = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs, active])
  return now
}
