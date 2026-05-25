import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  AlertCircleIcon,
  BanIcon,
  CheckCircle2Icon,
  PlayIcon,
  RefreshCwIcon,
  TestTubeDiagonalIcon,
} from "lucide-react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@workspace/ui/components/field"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { Spinner } from "@workspace/ui/components/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { Separator } from "@workspace/ui/components/separator"

import { PageHeader } from "@/components/page-header"
import {
  abortSelfTest,
  getDevices,
  getJob,
  getSelfTestStatus,
  listJobs,
  startSelfTest,
} from "@/lib/api"
import type { DeviceRecord, JobResponse, SelfTestDeviceStatus, SelfTestResultEntry } from "@/lib/types"

function statusBadgeVariant(status?: string) {
  const normalized = status?.toLowerCase() ?? ""
  if (
    normalized.includes("fail") ||
    normalized.includes("error") ||
    normalized.includes("timeout")
  ) {
    return "destructive" as const
  }
  if (
    normalized.includes("progress") ||
    normalized.includes("started") ||
    normalized.includes("running")
  ) {
    return "secondary" as const
  }
  if (normalized.includes("pass") || normalized.includes("complete")) {
    return "outline" as const
  }
  return "outline" as const
}

function formatStatus(entry: SelfTestDeviceStatus): string {
  if (entry.in_progress) {
    if (entry.progress_percent != null) {
      return `in_progress (${entry.progress_percent}%)`
    }
    if (entry.current_completion != null && entry.current_completion > 0) {
      return `in_progress (${entry.current_completion}%)`
    }
    return entry.status ?? "in_progress"
  }
  if (entry.passed) {
    return "passed"
  }
  if (entry.failed) {
    return "failed"
  }
  if (entry.aborted) {
    return "aborted"
  }
  return entry.status ?? "unknown"
}

function formatResultLabel(entry: SelfTestDeviceStatus): string {
  if (entry.latest_result?.result) {
    return entry.latest_result.result
  }
  if (entry.passed) {
    return "Success"
  }
  if (entry.failed) {
    return "Failed"
  }
  if (entry.aborted) {
    return "Aborted"
  }
  return "—"
}

function formatResultCode(entry: SelfTestDeviceStatus): string {
  const code = entry.latest_result?.result_code
  return code != null ? String(code) : "—"
}

function formatTestType(entry: SelfTestDeviceStatus): string {
  if (entry.latest_result?.test_type) {
    return entry.latest_result.test_type
  }
  if (entry.test_type) {
    return entry.test_type
  }
  return "—"
}

function lookupSerial(
  devicePath: string | undefined,
  serialByController: Map<string, string>
): string {
  if (!devicePath) {
    return "—"
  }
  return serialByController.get(devicePath) ?? "—"
}

function summarizeJob(job: JobResponse): string {
  const summary = job.result?.summary
  if (!summary) {
    return job.status
  }
  const completed = summary.completed ?? 0
  const started = summary.started ?? 0
  const failedToStart = summary.failed_to_start ?? 0
  return `${completed}/${started} completed, ${failedToStart} failed to start`
}

const LOG_WAIT_POLL_INTERVAL_MS = 1500
const MAX_LOG_WAIT_POLLS = 40

function hasLogData(entry: SelfTestDeviceStatus): boolean {
  return Boolean(entry.latest_result) || (entry.recent_results?.length ?? 0) > 0
}

function hasStaleSelfTestApi(devices: SelfTestDeviceStatus[]): boolean {
  return devices.some(
    (entry) =>
      entry.supported &&
      entry.latest_result === undefined &&
      entry.recent_results === undefined
  )
}

function describeMissingLogs(entry: SelfTestDeviceStatus): string {
  if (entry.logs_message) {
    return entry.logs_message
  }
  if (entry.in_progress) {
    return "Self-test is still running on the device. Log Page 0x06 entries appear after completion."
  }
  if (entry.error) {
    return entry.error
  }
  if (!entry.supported) {
    return "This controller does not support NVMe device self-test."
  }
  if (entry.passed || entry.failed || entry.aborted) {
    return "The drive reported a result but no log entries were returned. Try Refresh status — the NVMe log can lag briefly after completion."
  }
  return "No self-test log entries on this controller yet. Run a short self-test to populate Log Page 0x06."
}

function logEntriesForDevice(entry: SelfTestDeviceStatus): SelfTestResultEntry[] {
  if ((entry.recent_results?.length ?? 0) > 0) {
    return entry.recent_results ?? []
  }
  if (entry.latest_result) {
    return [entry.latest_result]
  }
  return []
}

export function SelfTestPage() {
  const [devices, setDevices] = useState<SelfTestDeviceStatus[]>([])
  const [nvmeControllers, setNvmeControllers] = useState<string[]>([])
  const [serialByController, setSerialByController] = useState<Map<string, string>>(
    new Map()
  )
  const [selectedDevice, setSelectedDevice] = useState<string>("all")
  const [testType, setTestType] = useState<"short" | "extended">("short")
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [abortingDevice, setAbortingDevice] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [watchingTests, setWatchingTests] = useState(false)
  const [lastCompletedJob, setLastCompletedJob] = useState<JobResponse | null>(null)
  const [recentJobs, setRecentJobs] = useState<JobResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)
  const logWaitPollsRef = useRef(0)

  const loadScanContext = useCallback(async () => {
    const scanResult = await getDevices(false)
    const controllers = scanResult.devices
      .filter((device: DeviceRecord) => device.transport_protocol === "NVMe")
      .map((device) => String(device.dut ?? ""))
      .filter((path) => path.startsWith("/dev/nvme"))
    setNvmeControllers(Array.from(new Set(controllers)).sort())

    const serialMap = new Map<string, string>()
    for (const device of scanResult.devices) {
      const dut = String(device.dut ?? "")
      if (!dut.startsWith("/dev/nvme")) {
        continue
      }
      const controllerMatch = dut.match(/^(\/dev\/nvme\d+)/)
      const controller = controllerMatch?.[1] ?? dut
      if (device.serial_number && !serialMap.has(controller)) {
        serialMap.set(controller, device.serial_number)
      }
    }
    setSerialByController(serialMap)
  }, [])

  const refreshStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statusResult] = await Promise.all([getSelfTestStatus(), loadScanContext()])
      setDevices(statusResult.devices)
      return statusResult.devices
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load self-test status")
      return []
    } finally {
      setLoading(false)
    }
  }, [loadScanContext])

  const refreshRecentJobs = useCallback(async () => {
    try {
      const jobs = await listJobs()
      setRecentJobs(jobs.filter((job) => job.job_type === "selftest").slice(0, 8))
    } catch {
      /* optional history — ignore failures */
    }
  }, [])

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

    const poll = async () => {
      try {
        if (activeJobId) {
          const job = await getJob(activeJobId)
          if (job.status === "completed" || job.status === "failed") {
            setActiveJobId(null)
            setLastCompletedJob(job)
            void refreshRecentJobs()

            if (job.status === "failed") {
              toast.error(job.error ?? "Self-test job failed")
            } else {
              toast.success("Self-test job submitted — waiting for device results")
            }

            const statusDevices = await refreshStatus()
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
          const statusDevices = await refreshStatus()
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

        pollRef.current = window.setTimeout(() => {
          void poll()
        }, LOG_WAIT_POLL_INTERVAL_MS)
      } catch (err) {
        setActiveJobId(null)
        setWatchingTests(false)
        toast.error(err instanceof Error ? err.message : "Job polling failed")
      }
    }

    void poll()

    return () => {
      if (pollRef.current != null) {
        window.clearTimeout(pollRef.current)
      }
    }
  }, [activeJobId, watchingTests, refreshStatus, refreshRecentJobs])

  const supportedDevices = useMemo(
    () => devices.filter((entry) => entry.supported),
    [devices]
  )

  const staleSelfTestApi = useMemo(() => hasStaleSelfTestApi(devices), [devices])

  const resultDevices = useMemo(() => {
    const fromJob = lastCompletedJob?.result?.devices ?? []
    if (fromJob.length > 0) {
      return fromJob
    }
    return devices.filter(
      (entry) =>
        entry.latest_result ||
        entry.passed ||
        entry.failed ||
        entry.aborted ||
        entry.in_progress
    )
  }, [devices, lastCompletedJob])

  const hasResultDetails = useMemo(
    () =>
      resultDevices.some(
        (entry) =>
          entry.latest_result ||
          entry.passed ||
          entry.failed ||
          entry.aborted ||
          entry.started ||
          entry.in_progress
      ),
    [resultDevices]
  )

  const runSelfTest = async () => {
    setStarting(true)
    setLastCompletedJob(null)
    logWaitPollsRef.current = 0
    try {
      const job = await startSelfTest({
        test_type: testType,
        wait: false,
        device: selectedDevice === "all" ? undefined : selectedDevice,
      })
      setActiveJobId(job.job_id)
      toast.success("Self-test started — polling job status")
      await refreshStatus()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start self-test")
    } finally {
      setStarting(false)
    }
  }

  const handleAbort = async (devicePath: string) => {
    setAbortingDevice(devicePath)
    try {
      await abortSelfTest(devicePath)
      toast.success(`Abort requested for ${devicePath}`)
      await refreshStatus()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Abort failed")
    } finally {
      setAbortingDevice(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="NVMe diagnostics"
        title="Self-Test Console"
        description="Start NVMe short or extended self-tests, monitor progress, and abort active runs on this grading host."
        badge={
          supportedDevices.length > 0
            ? `${supportedDevices.length} supported controller(s)`
            : "No supported NVMe controllers"
        }
        actions={
          <Button variant="outline" onClick={() => void reloadAll()} disabled={loading}>
            <RefreshCwIcon data-icon="inline-start" />
            Refresh status
          </Button>
        }
      />

      {error ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Self-test unavailable</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {activeJobId || watchingTests ? (
        <Alert>
          <TestTubeDiagonalIcon />
          <AlertTitle>
            {activeJobId ? "Job in progress" : "Self-test running on device"}
          </AlertTitle>
          <AlertDescription className="font-mono text-xs">
            {activeJobId
              ? `Polling job ${activeJobId}`
              : "Polling device status and NVMe Log Page 0x06 until results appear"}
          </AlertDescription>
        </Alert>
      ) : null}

      {staleSelfTestApi ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Self-test log API is out of date</AlertTitle>
          <AlertDescription>
            The grading host API is not returning log fields (
            <span className="font-mono">latest_result</span>,{" "}
            <span className="font-mono">recent_results</span>). Redeploy the latest CDI
            Health API on this host, then use Refresh status.
          </AlertDescription>
        </Alert>
      ) : null}

      {lastCompletedJob ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2Icon className="text-primary" />
              Latest run results
            </CardTitle>
            <CardDescription>
              Job {lastCompletedJob.job_id.slice(0, 8)} ·{" "}
              {lastCompletedJob.completed_at
                ? new Date(lastCompletedJob.completed_at).toLocaleString()
                : "just now"}{" "}
              · {summarizeJob(lastCompletedJob)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {hasResultDetails ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Serial</TableHead>
                    <TableHead>Test type</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resultDevices.map((entry) => {
                    const devicePath = entry.device ?? "—"
                    const statusLabel = formatStatus(entry)
                    return (
                      <TableRow key={`result-${devicePath}`}>
                        <TableCell className="font-mono text-xs">{devicePath}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {lookupSerial(devicePath, serialByController)}
                        </TableCell>
                        <TableCell>{formatTestType(entry)}</TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(formatResultLabel(entry))}>
                            {formatResultLabel(entry)}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {formatResultCode(entry)}
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(statusLabel)}>
                            {statusLabel}
                          </Badge>
                          {entry.error ? (
                            <p className="text-muted-foreground mt-1 text-xs">{entry.error}</p>
                          ) : null}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            ) : (
              <Empty className="border">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <TestTubeDiagonalIcon />
                  </EmptyMedia>
                  <EmptyTitle>No result payload yet</EmptyTitle>
                  <EmptyDescription>
                    The job finished but the API did not return per-device self-test log
                    entries. Refresh status after the drive completes its NVMe self-test.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayIcon className="text-primary" />
              Start self-test
            </CardTitle>
            <CardDescription>
              Runs asynchronously via the local API. Extended tests may take hours.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FieldGroup>
              <Field>
                <FieldLabel>Target device</FieldLabel>
                <Select value={selectedDevice} onValueChange={setSelectedDevice}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select NVMe controller" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="all">All supported NVMe controllers</SelectItem>
                      {nvmeControllers.map((path) => (
                        <SelectItem key={path} value={path}>
                          {path}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Controller paths only (for example /dev/nvme0), not namespaces.
                </FieldDescription>
              </Field>

              <Field>
                <FieldLabel>Test type</FieldLabel>
                <Select
                  value={testType}
                  onValueChange={(value) =>
                    setTestType(value as "short" | "extended")
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select test type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="short">Short (default)</SelectItem>
                      <SelectItem value="extended">Extended</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
            </FieldGroup>

            <Button
              onClick={() => void runSelfTest()}
              disabled={starting || !!activeJobId || watchingTests}
            >
              {starting ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <PlayIcon data-icon="inline-start" />
              )}
              {starting ? "Starting…" : "Start self-test"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Device status</CardTitle>
            <CardDescription>
              Live status from GET /api/v1/selftests/status on this host.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex flex-col gap-2">
                <Spinner />
              </div>
            ) : devices.length === 0 ? (
              <Empty className="border">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <TestTubeDiagonalIcon />
                  </EmptyMedia>
                  <EmptyTitle>No NVMe self-test targets</EmptyTitle>
                  <EmptyDescription>
                    Run a scan on Drive Health first, or connect NVMe drives that
                    support nvme-cli self-test on this host.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Supported</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Last test</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {devices.map((entry) => {
                    const devicePath = entry.device ?? "—"
                    const statusLabel = formatStatus(entry)
                    return (
                      <TableRow key={devicePath}>
                        <TableCell className="font-mono text-xs">{devicePath}</TableCell>
                        <TableCell>
                          <Badge variant={entry.supported ? "outline" : "secondary"}>
                            {entry.supported ? "Yes" : "No"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(statusLabel)}>
                            {statusLabel}
                          </Badge>
                          {entry.error ? (
                            <p className="text-muted-foreground mt-1 text-xs">{entry.error}</p>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          {entry.latest_result || entry.passed || entry.failed || entry.aborted ? (
                            <Badge variant={statusBadgeVariant(formatResultLabel(entry))}>
                              {formatResultLabel(entry)}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {formatResultCode(entry)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {entry.last_test_date
                            ? new Date(entry.last_test_date).toLocaleString()
                            : entry.latest_result?.test_type
                              ? `${entry.latest_result.test_type} (log)`
                              : "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          {entry.in_progress && entry.device ? (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={abortingDevice === entry.device}
                              onClick={() => void handleAbort(entry.device!)}
                            >
                              {abortingDevice === entry.device ? (
                                <Spinner data-icon="inline-start" />
                              ) : (
                                <BanIcon data-icon="inline-start" />
                              )}
                              Abort
                            </Button>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </section>

      {recentJobs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Recent self-test jobs</CardTitle>
            <CardDescription>
              In-memory job history from GET /api/v1/jobs on this API process.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Test type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentJobs.map((job) => (
                  <TableRow key={job.job_id}>
                    <TableCell className="font-mono text-xs">
                      {job.job_id.slice(0, 8)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {job.created_at ? new Date(job.created_at).toLocaleString() : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(job.status)}>{job.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{summarizeJob(job)}</TableCell>
                    <TableCell>
                      {(job.payload?.test_type as string | undefined) ?? "short"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}

      {supportedDevices.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Self-test logs</CardTitle>
            <CardDescription>
              Raw entries from NVMe Device Self-test Log (Log Page 0x06) via{" "}
              <span className="font-mono">GET /api/v1/selftests/status</span>.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            {supportedDevices.map((entry, index) => {
              const devicePath = entry.device ?? "—"
              const logEntries = logEntriesForDevice(entry)
              return (
                <div key={`logs-${devicePath}`} className="flex flex-col gap-3">
                  {index > 0 ? <Separator /> : null}
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-mono text-xs font-medium">{devicePath}</p>
                    <Badge variant="outline">
                      {lookupSerial(devicePath, serialByController)}
                    </Badge>
                    {entry.in_progress ? (
                      <Badge variant="secondary">in progress</Badge>
                    ) : hasLogData(entry) ? (
                      <Badge variant="outline">log available</Badge>
                    ) : (
                      <Badge variant="secondary">no log entries</Badge>
                    )}
                  </div>
                  {entry.current_operation ? (
                    <p className="text-muted-foreground text-xs">
                      Current operation: {String(entry.current_operation)}
                      {entry.current_completion != null
                        ? ` · ${entry.current_completion}% complete`
                        : entry.progress_percent != null
                          ? ` · ${entry.progress_percent}% complete`
                          : null}
                    </p>
                  ) : null}
                  {logEntries.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>#</TableHead>
                          <TableHead>Result</TableHead>
                          <TableHead>Code</TableHead>
                          <TableHead>Test type</TableHead>
                          <TableHead>Type code</TableHead>
                          <TableHead>Completion time</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {logEntries.map((result, logIndex) => (
                          <TableRow key={`${devicePath}-log-${logIndex}`}>
                            <TableCell className="font-mono text-xs">{logIndex}</TableCell>
                            <TableCell>
                              <Badge variant={statusBadgeVariant(result.result ?? "")}>
                                {result.result ?? "—"}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {result.result_code ?? "—"}
                            </TableCell>
                            <TableCell>{result.test_type ?? "—"}</TableCell>
                            <TableCell className="font-mono text-xs">
                              {result.test_type_code ?? "—"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {result.completion_time ?? "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <Empty className="border">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <TestTubeDiagonalIcon />
                        </EmptyMedia>
                        <EmptyTitle>No log entries yet</EmptyTitle>
                        <EmptyDescription>{describeMissingLogs(entry)}</EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  )}
                </div>
              )
            })}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
