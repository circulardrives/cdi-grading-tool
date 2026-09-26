import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"
import { useQuery, useQueryClient } from "@tanstack/react-query"

import { describeRequestError } from "@/components/ui-cdi"
import {
  buildDriveRows,
  FAST_POLL_MS,
  hasLogData,
  latestResult,
  resultKind,
  runningType,
  RUNNING_POLL_MS,
  SETTLE_MS,
  SLOW_POLL_MS,
  StaleBenchApiError,
  type TestType,
} from "@/components/self-tests/self-test-format"
import {
  queueSelfTests,
  useBenchQueue,
} from "@/components/self-tests/start-queue"
import {
  abortSelfTest,
  getDevices,
  getSelfTestStatus,
  isNotFoundError,
} from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"
import type { SelfTestStatusResponse } from "@/lib/types"

type UseSelfTestBenchOptions = {
  /** Registered bench to run on; `null` = the bench serving this dashboard. */
  machineId: string | null
  /** Plain name for messages ("pecan09", "this bench"). */
  benchName: string
}

/** How often to ask the bench for status, or false to stop polling. */
function pollInterval(
  data: SelfTestStatusResponse | undefined,
  busy: boolean,
  settling: boolean,
  started: ReadonlyMap<string, TestType>
): number | false {
  if (busy) {
    return FAST_POLL_MS
  }
  const running = (data?.devices ?? []).filter((entry) => entry.in_progress)
  if (running.length > 0) {
    const onlyExtended = running.every(
      (entry) =>
        runningType(entry, started.get(entry.device ?? "")) === "extended"
    )
    return onlyExtended ? SLOW_POLL_MS : RUNNING_POLL_MS
  }
  if (settling) {
    // Just started, stopped or finished: the drive's log can lag a little.
    const waitingForLog = (data?.devices ?? []).some(
      (entry) => started.has(entry.device ?? "") && !hasLogData(entry)
    )
    return waitingForLog || !data ? FAST_POLL_MS : RUNNING_POLL_MS
  }
  return false
}

/**
 * Self-test state for ONE bench: its drives (status + saved scan), the start
 * queue, and stop. Every call and cache key carries the bench's machine_id so
 * results from two benches never mix. Polls only while something is running.
 */
export function useSelfTestBench({
  machineId,
  benchName,
}: UseSelfTestBenchOptions) {
  const queryClient = useQueryClient()
  const queue = useBenchQueue(machineId)
  const busy = queue.pending.size > 0

  // "Settling" = shortly after a start or a finish; keeps polling for results.
  const [settleUntil, setSettleUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const settling = now < Math.max(settleUntil, queue.lastStartAt + SETTLE_MS)
  useEffect(() => {
    const until = Math.max(settleUntil, queue.lastStartAt + SETTLE_MS)
    const wait = until - Date.now()
    if (wait <= 0) {
      return
    }
    const timer = window.setTimeout(() => setNow(Date.now()), wait + 50)
    return () => window.clearTimeout(timer)
  }, [settleUntil, queue.lastStartAt])

  const statusQuery = useQuery({
    queryKey: queryKeys.selfTestStatus(machineId),
    queryFn: async () => {
      const result = await getSelfTestStatus(undefined, machineId)
      // Older APIs ignore machine_id and answer for their own drives.
      if (machineId && result.machine_id === undefined) {
        throw new StaleBenchApiError(benchName)
      }
      return result
    },
    staleTime: 0,
    retry: (count, error) =>
      !(error instanceof StaleBenchApiError) && count < 1,
    refetchInterval: (query) =>
      pollInterval(query.state.data, busy, settling, queue.started),
  })

  // The bench's saved scan names the drives (serial, model, capacity).
  const scanQuery = useQuery({
    queryKey: queryKeys.devices(machineId),
    queryFn: async () => {
      try {
        return await getDevices(false, machineId)
      } catch (error) {
        if (isNotFoundError(error)) {
          return null // never scanned: rows still list controllers
        }
        throw error
      }
    },
  })

  const statusDevices = statusQuery.data?.devices ?? null
  const drives = useMemo(
    () => buildDriveRows(statusDevices, scanQuery.data?.devices ?? []),
    [statusDevices, scanQuery.data]
  )

  // Tell the technician when tests finish (while this page is open).
  const runningRef = useRef<Set<string> | null>(null)
  // Drives stopped from this page: "Stopped" already said it, no "finished" toast.
  const stoppedRef = useRef<Set<string>>(new Set())
  useEffect(() => {
    if (!statusDevices) {
      return
    }
    const nowRunning = new Set(
      statusDevices
        .filter((entry) => entry.in_progress)
        .map((entry) => entry.device ?? "")
    )
    const before = runningRef.current
    runningRef.current = nowRunning
    if (!before) {
      return
    }
    const ended = statusDevices.filter(
      (entry) => before.has(entry.device ?? "") && !entry.in_progress
    )
    if (ended.length === 0) {
      return
    }
    setSettleUntil(Date.now() + SETTLE_MS)
    setNow(Date.now())
    const finished = ended.filter(
      (entry) => !stoppedRef.current.delete(entry.device ?? "")
    )
    if (finished.length === 0) {
      return
    }
    const kinds = finished.map((entry) => {
      const latest = latestResult(entry)
      return latest ? resultKind(latest) : null
    })
    const failed = kinds.filter((kind) => kind === "failed").length
    const passed = kinds.filter((kind) => kind === "passed").length
    const n = finished.length
    const what = n === 1 ? "Self-test" : `${n} self-tests`
    if (failed > 0) {
      toast.error(
        `${what} finished on ${benchName} — ${failed} failed${passed ? `, ${passed} passed` : ""}`
      )
    } else if (passed === n) {
      toast.success(
        `${what} finished on ${benchName} — ${n === 1 ? "passed" : "all passed"}`
      )
    } else {
      toast.message(`${what} finished on ${benchName}`)
    }
  }, [statusDevices, benchName])

  const refreshStatus = useCallback(
    () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.selfTestStatus(machineId),
      }),
    [machineId, queryClient]
  )

  const start = useCallback(
    (devices: string[], testType: TestType) => {
      if (devices.length === 0) {
        return
      }
      queueSelfTests({
        machineId,
        benchName,
        devices,
        testType,
        onProgress: () => {
          void queryClient.invalidateQueries({
            queryKey: queryKeys.selfTestStatus(machineId),
          })
          void queryClient.invalidateQueries({
            queryKey: queryKeys.jobs(machineId),
          })
        },
      })
    },
    [benchName, machineId, queryClient]
  )

  const [stopping, setStopping] = useState<ReadonlySet<string>>(new Set())
  const stop = useCallback(
    async (devices: string[]) => {
      setStopping(new Set(devices))
      let stopped = 0
      let problem: string | null = null
      for (const device of devices) {
        try {
          await abortSelfTest(device, machineId)
          stoppedRef.current.add(device)
          stopped += 1
        } catch (error) {
          problem = describeRequestError(
            error,
            benchName,
            `Couldn't stop the test on ${benchName} — try again`
          )
        }
      }
      setStopping(new Set())
      setSettleUntil(Date.now() + SETTLE_MS)
      setNow(Date.now())
      await refreshStatus()
      if (problem) {
        toast.error(
          stopped > 0
            ? `Stopped ${stopped} of ${devices.length} tests on ${benchName}. ${problem}`
            : problem
        )
      } else {
        toast.success(
          `Stopped the self-test on ${stopped === 1 ? "1 drive" : `${stopped} drives`} on ${benchName}`
        )
      }
    },
    [benchName, machineId, refreshStatus]
  )

  const statusError = statusQuery.error
  const error = statusError
    ? statusError instanceof StaleBenchApiError
      ? statusError.message
      : describeRequestError(
          statusError,
          benchName,
          `Couldn't get self-test status from ${benchName} — try again`
        )
    : null

  return {
    drives,
    statusDevices,
    /** First load of the status (no rows to show yet). */
    loading: statusQuery.isPending || scanQuery.isPending,
    /** The status can't be read; rows (if any) are from an earlier answer. */
    error,
    retry: refreshStatus,
    retrying: statusQuery.isFetching,
    scanMissing: scanQuery.data === null,
    /** Drive names (serials) are still loading. */
    scanLoading: scanQuery.isPending,
    queue,
    start,
    stop,
    stopping,
  }
}
