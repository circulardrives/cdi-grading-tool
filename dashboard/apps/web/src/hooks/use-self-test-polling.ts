import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"

import {
  abortSelfTest,
  getDevices,
  getJob,
  getSelfTestStatus,
  isNotFoundError,
  listJobs,
  startSelfTest,
} from "@/lib/api"
import { describeHostProblem, describeRequestError } from "@/lib/host-utils"
import { queryKeys } from "@/lib/query-keys"
import {
  buildSerialByController,
  hasLogData,
  LOG_WAIT_POLL_INTERVAL_MS,
  MAX_LOG_WAIT_POLLS,
  mergeControllers,
  nvmeControllersFromDevices,
  StaleBenchApiError,
} from "@/lib/self-test-utils"
import type { JobResponse, SelfTestDeviceStatus } from "@/lib/types"

type UseSelfTestPollingOptions = {
  /** Registered bench to run on; `null` = the API serving this dashboard. */
  machineId: string | null
  /** Plain name for messages ("pecan09", "this bench"). */
  benchName: string
}

/**
 * Self-test state for ONE bench. Mount it under a `key` per bench so switching
 * bench starts from a clean slate; every call and cache key carries the
 * bench's machine_id so results from two benches never mix.
 */
export function useSelfTestPolling({
  machineId,
  benchName,
}: UseSelfTestPollingOptions) {
  const queryClient = useQueryClient()
  const [devices, setDevices] = useState<SelfTestDeviceStatus[]>([])
  const [scanControllers, setScanControllers] = useState<string[]>([])
  const [serialByController, setSerialByController] = useState<
    Map<string, string>
  >(new Map())
  const [selectedDevice, setSelectedDevice] = useState<string>("all")
  const [testType, setTestType] = useState<"short" | "extended">("short")
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [starting, setStarting] = useState(false)
  const [abortingDevice, setAbortingDevice] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [watchingTests, setWatchingTests] = useState(false)
  const [lastCompletedJob, setLastCompletedJob] = useState<JobResponse | null>(
    null
  )
  const [recentJobs, setRecentJobs] = useState<JobResponse[]>([])
  const [error, setError] = useState<string | null>(null)

  const pollRef = useRef<number | null>(null)
  const logWaitPollsRef = useRef(0)
  const pollGenerationRef = useRef(0)
  const mountedRef = useRef(true)

  const nvmeControllers = useMemo(
    () => mergeControllers(scanControllers, devices),
    [scanControllers, devices]
  )

  const describe = useCallback(
    (err: unknown, fallback: string) =>
      err instanceof StaleBenchApiError
        ? err.message
        : describeRequestError(err, benchName, fallback),
    [benchName]
  )

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      pollGenerationRef.current += 1
      if (pollRef.current != null) {
        window.clearTimeout(pollRef.current)
      }
    }
  }, [])

  const loadScanContext = useCallback(async () => {
    try {
      const scanResult = await getDevices(false, machineId)
      if (!mountedRef.current) {
        return
      }
      setScanControllers(nvmeControllersFromDevices(scanResult.devices))
      setSerialByController(buildSerialByController(scanResult.devices))
      void queryClient.setQueryData(queryKeys.devices(machineId), scanResult)
    } catch (err) {
      // No saved scan for this bench yet: the self-test status still lists
      // its controllers, just without serial numbers.
      if (!isNotFoundError(err)) {
        throw err
      }
    }
  }, [machineId, queryClient])

  const refreshStatus = useCallback(
    async (opts?: { background?: boolean }) => {
      const background = opts?.background ?? false
      const generation = pollGenerationRef.current

      if (background) {
        setIsRefreshing(true)
      } else {
        setLoading(true)
      }
      setError(null)

      try {
        const [statusResult] = await Promise.all([
          getSelfTestStatus(undefined, machineId),
          loadScanContext(),
        ])
        // Older APIs ignore machine_id and answer for their own drives.
        if (machineId && statusResult.machine_id === undefined) {
          throw new StaleBenchApiError(benchName)
        }
        if (!mountedRef.current || generation !== pollGenerationRef.current) {
          return [] as SelfTestDeviceStatus[]
        }
        setDevices(statusResult.devices)
        void queryClient.setQueryData(
          queryKeys.selfTestStatus(machineId),
          statusResult
        )
        return statusResult.devices
      } catch (err) {
        if (!mountedRef.current || generation !== pollGenerationRef.current) {
          return [] as SelfTestDeviceStatus[]
        }
        if (!background) {
          // Show the problem instead of an empty or stale table.
          setDevices([])
        }
        setError(describe(err, `Couldn't load self-tests on ${benchName}`))
        return [] as SelfTestDeviceStatus[]
      } finally {
        if (mountedRef.current && generation === pollGenerationRef.current) {
          if (background) {
            setIsRefreshing(false)
          } else {
            setLoading(false)
          }
        }
      }
    },
    [benchName, describe, loadScanContext, machineId, queryClient]
  )

  const refreshRecentJobs = useCallback(async () => {
    const generation = pollGenerationRef.current
    try {
      const jobs = await listJobs(machineId)
      if (!mountedRef.current || generation !== pollGenerationRef.current) {
        return
      }
      // Belt and braces: never show another bench's jobs.
      const onThisBench = machineId
        ? jobs.filter(
            (job) => job.machine_id == null || job.machine_id === machineId
          )
        : jobs
      setRecentJobs(
        onThisBench.filter((job) => job.job_type === "selftest").slice(0, 8)
      )
      void queryClient.setQueryData(queryKeys.jobs(machineId), jobs)
    } catch {
      /* optional history — ignore failures */
    }
  }, [machineId, queryClient])

  const reloadAll = useCallback(async () => {
    await Promise.all([refreshStatus(), refreshRecentJobs()])
  }, [refreshStatus, refreshRecentJobs])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      const statusDevices = await refreshStatus()
      // Coming back to a bench with a test still running: keep watching it.
      if (!cancelled && statusDevices.some((entry) => entry.in_progress)) {
        logWaitPollsRef.current = 0
        setWatchingTests(true)
      }
    })()
    void refreshRecentJobs()
    return () => {
      cancelled = true
    }
  }, [refreshStatus, refreshRecentJobs])

  useEffect(() => {
    if (!activeJobId && !watchingTests) {
      return
    }

    const generation = ++pollGenerationRef.current

    const poll = async () => {
      if (!mountedRef.current || generation !== pollGenerationRef.current) {
        return
      }

      try {
        if (activeJobId) {
          // Remote job ids only make sense to the bench that issued them.
          const job = await getJob(activeJobId, machineId)
          if (!mountedRef.current || generation !== pollGenerationRef.current) {
            return
          }

          if (job.status === "completed" || job.status === "failed") {
            setActiveJobId(null)
            setLastCompletedJob(job)
            void refreshRecentJobs()

            if (job.status === "failed") {
              toast.error(
                describeHostProblem(benchName, job.error) ??
                  `Self-test on ${benchName} failed`
              )
            } else {
              toast.success(
                `Self-test started on ${benchName} — waiting for drive results`
              )
            }

            const statusDevices = await refreshStatus({ background: true })
            if (
              !mountedRef.current ||
              generation !== pollGenerationRef.current
            ) {
              return
            }

            const stillRunning = statusDevices.some(
              (entry) => entry.in_progress
            )
            if (stillRunning) {
              logWaitPollsRef.current = 0
              setWatchingTests(true)
            } else {
              const awaitingLogs = statusDevices.some(
                (entry) => entry.supported && !hasLogData(entry)
              )
              if (awaitingLogs) {
                logWaitPollsRef.current = 0
                setWatchingTests(true)
              } else {
                setWatchingTests(false)
                toast.success(`Self-test finished on ${benchName}`)
              }
            }
            return
          }
        } else if (watchingTests) {
          const statusDevices = await refreshStatus({ background: true })
          if (!mountedRef.current || generation !== pollGenerationRef.current) {
            return
          }

          const stillRunning = statusDevices.some((entry) => entry.in_progress)
          const awaitingLogs = statusDevices.some(
            (entry) =>
              entry.supported && !entry.in_progress && !hasLogData(entry)
          )

          if (stillRunning) {
            logWaitPollsRef.current = 0
          } else if (
            awaitingLogs &&
            logWaitPollsRef.current < MAX_LOG_WAIT_POLLS
          ) {
            logWaitPollsRef.current += 1
          } else {
            setWatchingTests(false)
            if (statusDevices.length === 0) {
              // The status call failed; its message is already on the page.
              return
            }
            if (awaitingLogs) {
              toast.message(
                `Self-test finished on ${benchName} — log data not available yet. Use Refresh status.`
              )
            } else {
              toast.success(`Self-test finished on ${benchName}`)
            }
            return
          }
        }

        if (!mountedRef.current || generation !== pollGenerationRef.current) {
          return
        }

        pollRef.current = window.setTimeout(() => {
          void poll()
        }, LOG_WAIT_POLL_INTERVAL_MS)
      } catch (err) {
        if (!mountedRef.current || generation !== pollGenerationRef.current) {
          return
        }
        setActiveJobId(null)
        setWatchingTests(false)
        toast.error(
          describe(err, `Lost track of the self-test on ${benchName}`)
        )
      }
    }

    void poll()

    return () => {
      pollGenerationRef.current += 1
      if (pollRef.current != null) {
        window.clearTimeout(pollRef.current)
        pollRef.current = null
      }
    }
  }, [
    activeJobId,
    watchingTests,
    benchName,
    describe,
    machineId,
    refreshStatus,
    refreshRecentJobs,
  ])

  const runSelfTest = async () => {
    pollGenerationRef.current += 1
    setStarting(true)
    setLastCompletedJob(null)
    logWaitPollsRef.current = 0
    try {
      const job = await startSelfTest({
        test_type: testType,
        wait: false,
        device: selectedDevice === "all" ? undefined : selectedDevice,
        ...(machineId ? { machine_id: machineId } : {}),
      })
      if (!mountedRef.current) {
        return
      }
      if (machineId && job.machine_id === undefined) {
        throw new StaleBenchApiError(benchName)
      }
      setActiveJobId(job.job_id)
      toast.success(`Starting self-test on ${benchName}…`)
      await refreshStatus({ background: true })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.jobs(machineId),
      })
    } catch (err) {
      toast.error(describe(err, `Couldn't start the self-test on ${benchName}`))
    } finally {
      if (mountedRef.current) {
        setStarting(false)
      }
    }
  }

  const handleAbort = async (devicePath: string) => {
    setAbortingDevice(devicePath)
    try {
      await abortSelfTest(devicePath, machineId)
      toast.success(`Stop requested for ${devicePath} on ${benchName}`)
      await refreshStatus({ background: true })
    } catch (err) {
      toast.error(describe(err, `Couldn't stop the self-test on ${benchName}`))
    } finally {
      if (mountedRef.current) {
        setAbortingDevice(null)
      }
    }
  }

  return {
    devices,
    nvmeControllers,
    serialByController,
    selectedDevice,
    setSelectedDevice,
    testType,
    setTestType,
    loading,
    isRefreshing,
    starting,
    abortingDevice,
    activeJobId,
    watchingTests,
    lastCompletedJob,
    recentJobs,
    error,
    reloadAll,
    runSelfTest,
    handleAbort,
  }
}
