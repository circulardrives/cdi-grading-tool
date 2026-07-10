import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"

import {
  abortSelfTest,
  getDevices,
  getJob,
  getSelfTestStatus,
  listJobs,
  startSelfTest,
} from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"
import {
  buildSerialByController,
  hasLogData,
  LOG_WAIT_POLL_INTERVAL_MS,
  MAX_LOG_WAIT_POLLS,
  nvmeControllersFromDevices,
} from "@/lib/self-test-utils"
import type { JobResponse, SelfTestDeviceStatus } from "@/lib/types"

export function useSelfTestPolling() {
  const queryClient = useQueryClient()
  const [devices, setDevices] = useState<SelfTestDeviceStatus[]>([])
  const [nvmeControllers, setNvmeControllers] = useState<string[]>([])
  const [serialByController, setSerialByController] = useState<Map<string, string>>(
    new Map()
  )
  const [selectedDevice, setSelectedDevice] = useState<string>("all")
  const [testType, setTestType] = useState<"short" | "extended">("short")
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [starting, setStarting] = useState(false)
  const [abortingDevice, setAbortingDevice] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [watchingTests, setWatchingTests] = useState(false)
  const [lastCompletedJob, setLastCompletedJob] = useState<JobResponse | null>(null)
  const [recentJobs, setRecentJobs] = useState<JobResponse[]>([])
  const [error, setError] = useState<string | null>(null)

  const pollRef = useRef<number | null>(null)
  const logWaitPollsRef = useRef(0)
  const pollGenerationRef = useRef(0)
  const mountedRef = useRef(true)

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
    const scanResult = await getDevices(false)
    if (!mountedRef.current) {
      return
    }
    setNvmeControllers(nvmeControllersFromDevices(scanResult.devices))
    setSerialByController(buildSerialByController(scanResult.devices))
    void queryClient.setQueryData(queryKeys.devices(null), scanResult)
  }, [queryClient])

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
          getSelfTestStatus(),
          loadScanContext(),
        ])
        if (!mountedRef.current || generation !== pollGenerationRef.current) {
          return [] as SelfTestDeviceStatus[]
        }
        setDevices(statusResult.devices)
        void queryClient.setQueryData(queryKeys.selfTestStatus, statusResult)
        return statusResult.devices
      } catch (err) {
        if (!mountedRef.current || generation !== pollGenerationRef.current) {
          return [] as SelfTestDeviceStatus[]
        }
        setError(
          err instanceof Error ? err.message : "Could not load self-test status"
        )
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
    [loadScanContext, queryClient]
  )

  const refreshRecentJobs = useCallback(async () => {
    const generation = pollGenerationRef.current
    try {
      const jobs = await listJobs()
      if (!mountedRef.current || generation !== pollGenerationRef.current) {
        return
      }
      setRecentJobs(jobs.filter((job) => job.job_type === "selftest").slice(0, 8))
      void queryClient.setQueryData(queryKeys.jobs, jobs)
    } catch {
      /* optional history — ignore failures */
    }
  }, [queryClient])

  const reloadAll = useCallback(async () => {
    await Promise.all([refreshStatus(), refreshRecentJobs()])
  }, [refreshStatus, refreshRecentJobs])

  useEffect(() => {
    void refreshStatus()
    void refreshRecentJobs()
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
          const job = await getJob(activeJobId)
          if (!mountedRef.current || generation !== pollGenerationRef.current) {
            return
          }

          if (job.status === "completed" || job.status === "failed") {
            setActiveJobId(null)
            setLastCompletedJob(job)
            void refreshRecentJobs()

            if (job.status === "failed") {
              toast.error(job.error ?? "Self-test job failed")
            } else {
              toast.success("Self-test job submitted — waiting for device results")
            }

            const statusDevices = await refreshStatus({ background: true })
            if (!mountedRef.current || generation !== pollGenerationRef.current) {
              return
            }

            const stillRunning = statusDevices.some((entry) => entry.in_progress)
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
                toast.success("Self-test finished")
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
            (entry) => entry.supported && !entry.in_progress && !hasLogData(entry)
          )

          if (stillRunning) {
            logWaitPollsRef.current = 0
          } else if (awaitingLogs && logWaitPollsRef.current < MAX_LOG_WAIT_POLLS) {
            logWaitPollsRef.current += 1
          } else {
            setWatchingTests(false)
            if (awaitingLogs) {
              toast.message(
                "Self-test finished — log data not available yet. Use Refresh status."
              )
            } else {
              toast.success("Self-test finished")
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
        toast.error(err instanceof Error ? err.message : "Job polling failed")
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
  }, [activeJobId, watchingTests, refreshStatus, refreshRecentJobs])

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
      })
      if (!mountedRef.current) {
        return
      }
      setActiveJobId(job.job_id)
      toast.success("Self-test started — polling job status")
      await refreshStatus({ background: true })
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start self-test")
    } finally {
      if (mountedRef.current) {
        setStarting(false)
      }
    }
  }

  const handleAbort = async (devicePath: string) => {
    setAbortingDevice(devicePath)
    try {
      await abortSelfTest(devicePath)
      toast.success(`Abort requested for ${devicePath}`)
      await refreshStatus({ background: true })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Abort failed")
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
