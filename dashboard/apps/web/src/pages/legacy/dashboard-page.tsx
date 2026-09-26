import { Link, useNavigate } from "react-router-dom"
import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AlertCircleIcon,
  HardDriveIcon,
  RefreshCwIcon,
  ServerIcon,
  ShieldCheckIcon,
} from "lucide-react"
import { toast } from "sonner"

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
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Switch } from "@workspace/ui/components/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { FleetHostList } from "@/components/fleet-host-list"
import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import {
  ScanAllHostsButton,
  ScanAllHostsProgress,
} from "@/components/scan-all-hosts"
import {
  useDevicesQuery,
  useFleetDevicesQuery,
  useHealthQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
  useScanAllStatus,
} from "@/hooks/use-cdi-queries"
import { scanDevices } from "@/lib/api"
import {
  deviceBadgeVariant,
  formatHealthLabel,
  formatHealthScore,
} from "@/lib/health-badges"
import { deviceRowKeys } from "@/lib/drive-labels"
import { describeRequestError, fleetHostProblem } from "@/lib/host-utils"
import { setSelectedHostId, useSelectedHostId } from "@/lib/selected-host"
import type { DeviceRecord, HealthResponse, ScanSummary } from "@/lib/types"

const AUTO_REFRESH_MS = 30_000
const RECENT_DRIVE_LIMIT = 8

function StatCardsSkeleton() {
  return (
    <>
      {Array.from({ length: 4 }).map((_, index) => (
        <Card key={index}>
          <CardHeader>
            <Skeleton className="h-4 w-24" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-16" />
          </CardContent>
        </Card>
      ))}
    </>
  )
}

function SummaryStatCards({
  summary,
  scannedAt,
}: {
  summary: ScanSummary | null | undefined
  scannedAt?: string | null
}) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardDescription>Total Devices</CardDescription>
          <CardTitle className="text-2xl">{summary?.total ?? 0}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {scannedAt !== undefined
            ? `Last scan ${scannedAt ? new Date(scannedAt).toLocaleString() : "not yet run"}`
            : "Across all hosts"}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardDescription>Healthy</CardDescription>
          <CardTitle className="text-2xl text-primary">
            {summary?.healthy ?? 0}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Passing CDI health thresholds
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardDescription>Warnings / Failed</CardDescription>
          <CardTitle className="text-2xl">
            {(summary?.warning ?? 0) + (summary?.failed ?? 0)}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {summary?.warning ?? 0} warning · {summary?.failed ?? 0} failed
          {summary?.ungraded ? ` · ${summary.ungraded} ungraded` : ""}
        </CardContent>
      </Card>
    </>
  )
}

function benchStatusLine(health: HealthResponse | null): string {
  if (!health) {
    return "—"
  }
  const parts = [health.version ? `v${health.version}` : null]
  if (health.is_root == null) {
    parts.push("Limited status (not authenticated)")
  } else {
    parts.push(health.is_root ? "Running as root" : "Non-root dev mode")
  }
  if (health.api_token_enabled) {
    parts.push("Token auth on")
  }
  if (health.weasyprint_available === false) {
    parts.push("PDF export unavailable")
  }
  return parts.filter(Boolean).join(" · ")
}

function RecentDrivesTable({
  devices,
  showHost,
}: {
  devices: DeviceRecord[]
  showHost: boolean
}) {
  const shown = useMemo(() => devices.slice(0, RECENT_DRIVE_LIMIT), [devices])
  const rowKeys = useMemo(() => deviceRowKeys(shown), [shown])
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {showHost ? <TableHead>Host</TableHead> : null}
          <TableHead>Device</TableHead>
          <TableHead>Model</TableHead>
          <TableHead>Protocol</TableHead>
          <TableHead>Grade</TableHead>
          <TableHead>Score</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {shown.map((device, index) => (
          <TableRow key={rowKeys.get(device) ?? `row-${index}`}>
            {showHost ? (
              <TableCell>{device.machine_name ?? "—"}</TableCell>
            ) : null}
            <TableCell className="font-mono text-xs">
              {device.dut ?? "—"}
            </TableCell>
            <TableCell>{device.model_number ?? "—"}</TableCell>
            <TableCell>{device.transport_protocol ?? "—"}</TableCell>
            <TableCell>
              <Badge variant={deviceBadgeVariant(device)}>
                {formatHealthLabel(device)}
              </Badge>
            </TableCell>
            <TableCell>{formatHealthScore(device)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { useMockData, mockDataPath } = useMockDataSettings()
  const { invalidateAfterScan } = useInvalidateCdiQueries()
  const [scanning, setScanning] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null)

  const healthQuery = useHealthQuery()
  const machinesQuery = useMachinesQuery()
  const selectedHostId = useSelectedHostId()
  const hostCount = machinesQuery.data?.length ?? 0

  // Fleet view whenever hosts exist; `null` means the API predates /fleet/devices.
  const fleetQuery = useFleetDevicesQuery(hostCount > 0)
  const fleetMode = hostCount > 0 && fleetQuery.data !== null
  const scanAll = useScanAllStatus()

  const devicesQuery = useDevicesQuery(
    selectedHostId,
    !machinesQuery.isLoading && !fleetMode
  )

  const health = healthQuery.data ?? null
  const scan = devicesQuery.data ?? null
  const fleet = fleetQuery.data ?? null
  const fleetHosts = fleet?.hosts ?? []
  const problemHosts = fleetHosts.filter(
    (host) => fleetHostProblem(host) != null
  )

  const loading =
    healthQuery.isLoading ||
    machinesQuery.isLoading ||
    (fleetMode ? fleetQuery.isLoading : devicesQuery.isLoading)
  const error =
    healthQuery.error instanceof Error
      ? healthQuery.error.message
      : fleetMode
        ? fleetQuery.error instanceof Error
          ? fleetQuery.error.message
          : null
        : devicesQuery.error instanceof Error
          ? devicesQuery.error.message
          : null

  useEffect(() => {
    if (
      healthQuery.isSuccess ||
      devicesQuery.isSuccess ||
      fleetQuery.isSuccess
    ) {
      setLastRefreshedAt(new Date())
    }
  }, [
    healthQuery.dataUpdatedAt,
    devicesQuery.dataUpdatedAt,
    fleetQuery.dataUpdatedAt,
    healthQuery.isSuccess,
    devicesQuery.isSuccess,
    fleetQuery.isSuccess,
  ])

  const refresh = useCallback(async () => {
    await Promise.all([
      healthQuery.refetch(),
      machinesQuery.refetch(),
      fleetMode ? fleetQuery.refetch() : devicesQuery.refetch(),
    ])
  }, [healthQuery, machinesQuery, fleetMode, fleetQuery, devicesQuery])

  useEffect(() => {
    if (!autoRefresh) {
      return
    }

    const tick = () => {
      if (document.visibilityState !== "visible") {
        return
      }
      void refresh()
    }

    const id = window.setInterval(tick, AUTO_REFRESH_MS)
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void refresh()
      }
    }
    document.addEventListener("visibilitychange", onVisibility)

    return () => {
      window.clearInterval(id)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [autoRefresh, refresh])

  const runScan = async () => {
    setScanning(true)
    const hostName =
      machinesQuery.data?.find((host) => host.id === selectedHostId)?.name ??
      "this bench"
    try {
      const machineId = selectedHostId
      const result = await scanDevices({
        ignore_ata: false,
        ignore_nvme: false,
        ignore_scsi: false,
        ...(machineId ? { machine_id: machineId } : {}),
        ...mockDataRequestFields(useMockData, mockDataPath),
      })
      await invalidateAfterScan(machineId)
      toast.success(
        `Scanned ${hostName} — ${result.summary.total} device(s) found`
      )
    } catch (err) {
      toast.error(describeRequestError(err, hostName, "Scan failed"))
    } finally {
      setScanning(false)
    }
  }

  const devices: DeviceRecord[] = fleetMode
    ? (fleet?.devices ?? [])
    : (scan?.devices ?? [])

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2">
        <p className="font-mono text-xs tracking-[0.28em] text-muted-foreground uppercase">
          Overview
        </p>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              Fleet Health Snapshot
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              {fleetMode
                ? "Drive health across every host in your fleet. Scan all hosts to refresh every bench at once."
                : "Monitor readiness, run inventory scans, and inspect the latest drive telemetry from this bench."}
            </p>
            {lastRefreshedAt ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Last refreshed {lastRefreshedAt.toLocaleTimeString()}
                {autoRefresh ? " · auto-refresh on" : ""}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Switch
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
                aria-label="Auto-refresh when tab is visible"
              />
              Live refresh
            </label>
            <Button
              variant="outline"
              onClick={() => void refresh()}
              disabled={loading || scanAll.pending}
            >
              <RefreshCwIcon data-icon="inline-start" />
              Refresh
            </Button>
            {/* Scan all benches lives in the app header. */}
            {fleetMode ? null : (
              <Button onClick={() => void runScan()} disabled={scanning}>
                <HardDriveIcon data-icon="inline-start" />
                {scanning ? "Scanning…" : "Run Scan"}
              </Button>
            )}
          </div>
        </div>
        {fleetMode ? (
          <ScanAllHostsProgress hostCount={fleetHosts.length} />
        ) : null}
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Connection issue</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          <StatCardsSkeleton />
        ) : fleetMode ? (
          <>
            <Card>
              <CardHeader>
                <CardDescription>Hosts OK</CardDescription>
                <CardTitle className="flex items-center gap-2 text-2xl">
                  <ServerIcon className="text-primary" />
                  {fleetHosts.length - problemHosts.length} of{" "}
                  {fleetHosts.length}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {problemHosts.length > 0
                  ? `${problemHosts.length} host${problemHosts.length === 1 ? " needs" : "s need"} attention — see below`
                  : "Every host is answering"}
              </CardContent>
            </Card>
            <SummaryStatCards summary={fleet?.summary} />
          </>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardDescription>API Status</CardDescription>
                <CardTitle className="flex items-center gap-2 text-2xl">
                  <ShieldCheckIcon className="text-primary" />
                  {health?.status ?? "—"}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {benchStatusLine(health)}
              </CardContent>
            </Card>
            <SummaryStatCards
              summary={scan?.summary}
              scannedAt={scan?.scanned_at ?? null}
            />
          </>
        )}
      </section>

      {fleetMode ? (
        <Card>
          <CardHeader>
            <CardTitle>Hosts</CardTitle>
            <CardDescription>
              Status and drive counts for each bench · this bench:{" "}
              {health?.status ?? "—"}
              {health?.version ? ` · v${health.version}` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <FleetHostList
                hosts={fleetHosts}
                scanning={scanAll.pending}
                showSummary
                selectLabel="View drives"
                onSelectHost={(host) => {
                  setSelectedHostId(host.machine_id)
                  navigate("/drives")
                }}
              />
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Recent Drives</CardTitle>
          <CardDescription>
            {fleetMode
              ? "A quick look across all hosts. Open Drive Health for Simple and Detailed tables by drive class."
              : "Quick snapshot from the latest scan. Open Drive Health for Simple and Detailed tables by drive class."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : devices.length > 0 ? (
            <RecentDrivesTable devices={devices} showHost={fleetMode} />
          ) : (
            <Empty className="border">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <HardDriveIcon />
                </EmptyMedia>
                <EmptyTitle>No drives scanned yet</EmptyTitle>
                <EmptyDescription>
                  {fleetMode
                    ? "Scan all hosts to grade attached drives, then review full tables on Drive Health."
                    : "Run a scan to grade attached drives, then review full tables on Drive Health."}
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent className="flex flex-wrap gap-2">
                {fleetMode ? <ScanAllHostsButton /> : null}
                <Button variant={fleetMode ? "outline" : "default"} asChild>
                  <Link to="/drives">Open Drive Health</Link>
                </Button>
              </EmptyContent>
            </Empty>
          )}
          {devices.length > 0 ? (
            <Button
              variant="outline"
              className="w-fit"
              asChild
              onClick={() => {
                if (fleetMode) {
                  setSelectedHostId(null)
                }
              }}
            >
              <Link to="/drives">View all drives — Simple / Detailed</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
