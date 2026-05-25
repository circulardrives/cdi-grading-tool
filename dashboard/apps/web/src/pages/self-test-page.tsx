import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  AlertCircleIcon,
  BanIcon,
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

import { PageHeader } from "@/components/page-header"
import {
  abortSelfTest,
  getDevices,
  getJob,
  getSelfTestStatus,
  startSelfTest,
} from "@/lib/api"
import type { DeviceRecord, SelfTestDeviceStatus } from "@/lib/types"

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

export function SelfTestPage() {
  const [devices, setDevices] = useState<SelfTestDeviceStatus[]>([])
  const [nvmeControllers, setNvmeControllers] = useState<string[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string>("all")
  const [testType, setTestType] = useState<"short" | "extended">("short")
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [abortingDevice, setAbortingDevice] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  const refreshStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statusResult, scanResult] = await Promise.all([
        getSelfTestStatus(),
        getDevices(false),
      ])
      setDevices(statusResult.devices)

      const controllers = scanResult.devices
        .filter((device: DeviceRecord) => device.transport_protocol === "NVMe")
        .map((device) => String(device.dut ?? ""))
        .filter((path) => path.startsWith("/dev/nvme"))
      setNvmeControllers(Array.from(new Set(controllers)).sort())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load self-test status")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    if (!activeJobId) {
      return
    }

    const pollJob = async () => {
      try {
        const job = await getJob(activeJobId)
        if (job.status === "completed" || job.status === "failed") {
          setActiveJobId(null)
          if (job.status === "failed") {
            toast.error(job.error ?? "Self-test job failed")
          } else {
            toast.success("Self-test job finished")
          }
          await refreshStatus()
          return
        }
        pollRef.current = window.setTimeout(() => {
          void pollJob()
        }, 1500)
      } catch (err) {
        setActiveJobId(null)
        toast.error(err instanceof Error ? err.message : "Job polling failed")
      }
    }

    void pollJob()

    return () => {
      if (pollRef.current != null) {
        window.clearTimeout(pollRef.current)
      }
    }
  }, [activeJobId, refreshStatus])

  const supportedCount = useMemo(
    () => devices.filter((entry) => entry.supported).length,
    [devices]
  )

  const runSelfTest = async () => {
    setStarting(true)
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
          supportedCount > 0
            ? `${supportedCount} supported controller(s)`
            : "No supported NVMe controllers"
        }
        actions={
          <Button variant="outline" onClick={() => void refreshStatus()} disabled={loading}>
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

      {activeJobId ? (
        <Alert>
          <TestTubeDiagonalIcon />
          <AlertTitle>Job in progress</AlertTitle>
          <AlertDescription className="font-mono text-xs">
            Polling job {activeJobId}
          </AlertDescription>
        </Alert>
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

            <Button onClick={() => void runSelfTest()} disabled={starting || !!activeJobId}>
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
                        <TableCell className="text-sm">
                          {entry.last_test_date
                            ? new Date(entry.last_test_date).toLocaleString()
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
    </div>
  )
}
