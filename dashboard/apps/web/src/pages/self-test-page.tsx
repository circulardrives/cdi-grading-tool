import { useMemo } from "react"
import {
  AlertCircleIcon,
  PlayIcon,
  RefreshCwIcon,
  TestTubeDiagonalIcon,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
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

import { PageHeader } from "@/components/page-header"
import { SelfTestDeviceStatusTable } from "@/components/self-test-device-status-table"
import { SelfTestLogsCard } from "@/components/self-test-logs-card"
import { SelfTestRecentJobsCard } from "@/components/self-test-recent-jobs-card"
import { SelfTestResultsCard } from "@/components/self-test-results-card"
import { useSelfTestPolling } from "@/hooks/use-self-test-polling"
import { hasStaleSelfTestApi } from "@/lib/self-test-utils"

export function SelfTestPage() {
  const {
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
  } = useSelfTestPolling()

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

  const showInitialSpinner = loading && devices.length === 0

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
          <Button
            variant="outline"
            onClick={() => void reloadAll()}
            disabled={loading || isRefreshing}
          >
            <RefreshCwIcon data-icon="inline-start" />
            {isRefreshing ? "Refreshing…" : "Refresh status"}
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
        <SelfTestResultsCard
          job={lastCompletedJob}
          resultDevices={resultDevices}
          hasResultDetails={hasResultDetails}
          serialByController={serialByController}
        />
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
                <FieldLabel htmlFor="self-test-device">Target device</FieldLabel>
                <Select value={selectedDevice} onValueChange={setSelectedDevice}>
                  <SelectTrigger id="self-test-device" className="w-full">
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
                <FieldLabel htmlFor="self-test-type">Test type</FieldLabel>
                <Select
                  value={testType}
                  onValueChange={(value) =>
                    setTestType(value as "short" | "extended")
                  }
                >
                  <SelectTrigger id="self-test-type" className="w-full">
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
              {isRefreshing ? " · Updating…" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SelfTestDeviceStatusTable
              devices={devices}
              loading={showInitialSpinner}
              abortingDevice={abortingDevice}
              onAbort={(path) => void handleAbort(path)}
            />
          </CardContent>
        </Card>
      </section>

      <SelfTestRecentJobsCard jobs={recentJobs} />

      <SelfTestLogsCard
        devices={supportedDevices}
        serialByController={serialByController}
      />
    </div>
  )
}
