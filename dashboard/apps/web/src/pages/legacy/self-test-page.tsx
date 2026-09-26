import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  AlertCircleIcon,
  PlayIcon,
  RefreshCwIcon,
  ServerIcon,
  TestTubeDiagonalIcon,
} from "lucide-react"

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@workspace/ui/components/alert"
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
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Spinner } from "@workspace/ui/components/spinner"

import { PageHeader } from "@/components/page-header"
import { SelfTestDeviceStatusTable } from "@/components/self-test-device-status-table"
import { SelfTestLogsCard } from "@/components/self-test-logs-card"
import { SelfTestRecentJobsCard } from "@/components/self-test-recent-jobs-card"
import { SelfTestResultsCard } from "@/components/self-test-results-card"
import { useFleetDevicesQuery, useMachinesQuery } from "@/hooks/use-cdi-queries"
import { useSelfTestPolling } from "@/hooks/use-self-test-polling"
import {
  hostHasAddress,
  machineStatusBadgeVariant,
  machineStatusLabel,
} from "@/lib/host-utils"
import { useSelectedHostId } from "@/lib/selected-host"
import { hasStaleSelfTestApi } from "@/lib/self-test-utils"

const THIS_BENCH = "local"

type BenchOption = {
  /** Select value: the machine id, or THIS_BENCH. */
  value: string
  machineId: string | null
  name: string
  /** Last known connection status; the live calls below have the final say. */
  status: string
}

const THIS_BENCH_OPTION: BenchOption = {
  value: THIS_BENCH,
  machineId: null,
  name: "This bench",
  status: "",
}

/** Benches with an address (self-tests run there), then "This bench" last. */
function useBenchOptions() {
  const machinesQuery = useMachinesQuery()
  const machines = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const hasRemote = machines.some(hostHasAddress)
  const fleetQuery = useFleetDevicesQuery(hasRemote)

  const options = useMemo(() => {
    const fleetHosts = fleetQuery.data?.hosts
    const remote: BenchOption[] = fleetHosts
      ? fleetHosts
          .filter((host) => host.machine_id && hostHasAddress(host))
          .map((host) => ({
            value: host.machine_id as string,
            machineId: host.machine_id,
            name: host.name,
            status: host.status,
          }))
      : machines.filter(hostHasAddress).map((host) => ({
          value: host.id,
          machineId: host.id,
          name: host.name,
          status: host.status,
        }))
    return [...remote, THIS_BENCH_OPTION]
  }, [fleetQuery.data, machines])

  const loading = machinesQuery.isLoading || (hasRemote && fleetQuery.isLoading)
  return { options, loading }
}

function pickDefaultBench(
  options: BenchOption[],
  selectedHostId: string | null
): string {
  const remote = options.filter((option) => option.machineId)
  if (
    selectedHostId &&
    remote.some((option) => option.value === selectedHostId)
  ) {
    return selectedHostId
  }
  const online = remote.find((option) => option.status === "reachable")
  return online?.value ?? remote[0]?.value ?? THIS_BENCH
}

export function SelfTestPage() {
  const selectedHostId = useSelectedHostId()
  const { options, loading } = useBenchOptions()
  // Chosen once the bench list has loaded; later status changes must not
  // switch the bench under a running test.
  const [choice, setChoice] = useState<string | null>(null)
  if (!loading && choice === null) {
    setChoice(pickDefaultBench(options, selectedHostId))
  }
  const bench =
    options.find((option) => option.value === choice) ??
    (choice === null ? null : THIS_BENCH_OPTION)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="NVMe diagnostics"
        title="NVMe Self-Test"
        description="Pick a bench, then start short or extended NVMe self-tests on its drives, watch progress, and stop running tests."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ServerIcon className="text-primary" />
            Bench
          </CardTitle>
          <CardDescription>
            Everything on this page — drives, starting and stopping tests,
            results — happens on the bench you pick here.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {bench == null ? (
            <Skeleton className="h-9 w-full max-w-sm" />
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <Select value={bench.value} onValueChange={setChoice}>
                <SelectTrigger
                  className="w-full max-w-sm"
                  aria-label="Bench to run self-tests on"
                >
                  <SelectValue placeholder="Pick a bench" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {options.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.machineId
                          ? `${option.name} · ${machineStatusLabel(option.status)}`
                          : "This bench (this computer)"}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              {bench.machineId ? (
                <Badge variant={machineStatusBadgeVariant(bench.status)}>
                  {machineStatusLabel(bench.status)}
                </Badge>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      {bench ? (
        // Keyed by bench: switching bench throws away the old bench's state
        // and stops its polling before anything is shown for the new one.
        <SelfTestConsole
          key={bench.value}
          machineId={bench.machineId}
          benchName={bench.machineId ? bench.name : "this bench"}
        />
      ) : (
        <Skeleton className="h-64 w-full" />
      )}
    </div>
  )
}

type SelfTestConsoleProps = {
  machineId: string | null
  benchName: string
}

function SelfTestConsole({ machineId, benchName }: SelfTestConsoleProps) {
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
  } = useSelfTestPolling({ machineId, benchName })

  const supportedDevices = useMemo(
    () => devices.filter((entry) => entry.supported),
    [devices]
  )

  const staleSelfTestApi = useMemo(
    () => hasStaleSelfTestApi(devices),
    [devices]
  )

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
  const runningOn = machineId ? benchName : "this bench"
  const RunningOnIcon = machineId ? ServerIcon : TestTubeDiagonalIcon

  // Bench can't be reached (or other hard failure): one line + where to fix it.
  if (error && devices.length === 0 && !loading) {
    return (
      <Alert variant="destructive">
        <AlertCircleIcon />
        <AlertTitle>Can't run self-tests on {runningOn} right now</AlertTitle>
        <AlertDescription className="flex flex-col gap-3">
          <span>{error}</span>
          <span className="flex flex-wrap gap-2">
            {machineId ? (
              <Button size="sm" variant="outline" asChild>
                <Link to="/benches">Go to Hosts</Link>
              </Button>
            ) : null}
            <Button
              size="sm"
              variant="outline"
              onClick={() => void reloadAll()}
              disabled={isRefreshing}
            >
              <RefreshCwIcon data-icon="inline-start" />
              Try again
            </Button>
          </span>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <>
      {error ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Couldn't update self-test status</AlertTitle>
          <AlertDescription>
            {error}
            {machineId ? (
              <>
                {" "}
                <Link to="/hosts" className="underline underline-offset-3">
                  Go to Hosts
                </Link>
              </>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {activeJobId || watchingTests ? (
        <Alert>
          <TestTubeDiagonalIcon />
          <AlertTitle>Self-test running on {runningOn}</AlertTitle>
          <AlertDescription>
            {activeJobId
              ? "Starting the test on the drives…"
              : "Checking progress every few seconds until the drives report results."}
          </AlertDescription>
        </Alert>
      ) : null}

      {staleSelfTestApi ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>CDI Health on {runningOn} is out of date</AlertTitle>
          <AlertDescription>
            It isn't sending self-test log details. Update CDI Health on{" "}
            {runningOn}, then use Refresh status.
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
              Short tests take a few minutes; extended tests can take hours.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="self-test-device">Drive</FieldLabel>
                <Select
                  value={selectedDevice}
                  onValueChange={setSelectedDevice}
                >
                  <SelectTrigger id="self-test-device" className="w-full">
                    <SelectValue placeholder="Select NVMe controller" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="all">
                        All NVMe drives that support it
                      </SelectItem>
                      {nvmeControllers.map((path) => (
                        <SelectItem key={path} value={path}>
                          {serialByController.get(path)
                            ? `${path} · ${serialByController.get(path)}`
                            : path}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Controller paths only (for example /dev/nvme0), not
                  namespaces.
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

            <p
              className="flex items-center gap-2 rounded-xl bg-muted px-3 py-2 text-sm"
              aria-live="polite"
            >
              <RunningOnIcon
                className="size-4 shrink-0 text-primary"
                aria-hidden
              />
              <span>
                Running on <span className="font-semibold">{runningOn}</span>
              </span>
            </p>

            <Button
              onClick={() => void runSelfTest()}
              disabled={starting || !!activeJobId || watchingTests || loading}
            >
              {starting ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <PlayIcon data-icon="inline-start" />
              )}
              {starting ? "Starting…" : `Start self-test on ${runningOn}`}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1.5">
              <CardTitle>Drive status</CardTitle>
              <CardDescription>
                NVMe drives on {runningOn}
                {supportedDevices.length > 0
                  ? ` · ${supportedDevices.length} support self-test`
                  : ""}
                {isRefreshing ? " · Updating…" : ""}
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void reloadAll()}
              disabled={loading || isRefreshing}
            >
              <RefreshCwIcon data-icon="inline-start" />
              {isRefreshing ? "Refreshing…" : "Refresh status"}
            </Button>
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

      <SelfTestRecentJobsCard jobs={recentJobs} benchName={runningOn} />

      <SelfTestLogsCard
        devices={supportedDevices}
        serialByController={serialByController}
      />
    </>
  )
}
