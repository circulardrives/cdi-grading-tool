import { Link } from "react-router-dom"
import { useCallback, useEffect, useState } from "react"
import {
  AlertCircleIcon,
  HardDriveIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
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
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import { Skeleton } from "@workspace/ui/components/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { getDevices, getHealth, scanDevices } from "@/lib/api"
import { appConfig } from "@/lib/config"
import type { HealthResponse, ScanResponse } from "@/lib/types"

function statusBadgeVariant(status?: string) {
  const normalized = status?.toLowerCase() ?? ""
  if (normalized.includes("fail") || normalized.includes("critical")) {
    return "destructive" as const
  }
  if (normalized.includes("warn")) {
    return "secondary" as const
  }
  return "outline" as const
}

export function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [scan, setScan] = useState<ScanResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [healthResult, devicesResult] = await Promise.all([
        getHealth(),
        getDevices(false),
      ])
      setHealth(healthResult)
      setScan(devicesResult)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load dashboard data"
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const runScan = async () => {
    setScanning(true)
    try {
      const result = await scanDevices({
        ignore_ata: false,
        ignore_nvme: false,
        ignore_scsi: false,
        ...(appConfig.useMockData
          ? { mock_data: appConfig.mockDataPath }
          : {}),
      })
      setScan(result)
      toast.success(`Scan complete — ${result.summary.total} device(s) found`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Scan failed")
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2">
        <p className="text-muted-foreground font-mono text-xs uppercase tracking-[0.28em]">
          Overview
        </p>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              Fleet Health Snapshot
            </h1>
            <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
              Monitor API readiness, run inventory scans, and inspect the latest
              drive telemetry from the local CDI backend.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
              <RefreshCwIcon data-icon="inline-start" />
              Refresh
            </Button>
            <Button onClick={() => void runScan()} disabled={scanning}>
              <HardDriveIcon data-icon="inline-start" />
              {scanning ? "Scanning…" : "Run Scan"}
            </Button>
          </div>
        </div>
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
          Array.from({ length: 4 }).map((_, index) => (
            <Card key={index}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))
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
              <CardContent className="text-muted-foreground text-sm">
                {health?.is_root ? "Running as root" : "Non-root dev mode"}
                {health?.api_token_enabled ? " · Token auth on" : ""}
                {health?.weasyprint_available === false
                  ? " · PDF export unavailable"
                  : ""}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Total Devices</CardDescription>
                <CardTitle className="text-2xl">
                  {scan?.summary.total ?? 0}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground text-sm">
                Last scan{" "}
                {scan?.scanned_at
                  ? new Date(scan.scanned_at).toLocaleString()
                  : "not yet run"}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Healthy</CardDescription>
                <CardTitle className="text-2xl text-primary">
                  {scan?.summary.healthy ?? 0}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground text-sm">
                Passing CDI health thresholds
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Warnings / Failed</CardDescription>
                <CardTitle className="text-2xl">
                  {(scan?.summary.warning ?? 0) + (scan?.summary.failed ?? 0)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground text-sm">
                {scan?.summary.warning ?? 0} warning · {scan?.summary.failed ?? 0}{" "}
                failed
              </CardContent>
            </Card>
          </>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent Drives</CardTitle>
          <CardDescription>
            Quick snapshot from the latest scan. Open Drive Health for Simple and
            Detailed tables by drive class.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : scan && scan.devices.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Protocol</TableHead>
                  <TableHead>Grade</TableHead>
                  <TableHead>Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {scan.devices.slice(0, 8).map((device) => (
                  <TableRow key={String(device.dut ?? device.serial_number)}>
                    <TableCell className="font-mono text-xs">
                      {device.dut ?? "—"}
                    </TableCell>
                    <TableCell>{device.model_number ?? "—"}</TableCell>
                    <TableCell>{device.transport_protocol ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(device.health_status)}>
                        {device.health_grade ?? device.health_status ?? "—"}
                      </Badge>
                    </TableCell>
                    <TableCell>{device.health_score ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Empty className="border">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <HardDriveIcon />
                </EmptyMedia>
                <EmptyTitle>No drives scanned yet</EmptyTitle>
                <EmptyDescription>
                  Run a scan to grade attached drives, then review full tables on
                  Drive Health.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button asChild>
                  <Link to="/drives">Open Drive Health</Link>
                </Button>
              </EmptyContent>
            </Empty>
          )}
          {scan && scan.devices.length > 0 ? (
            <Button variant="outline" className="w-fit" asChild>
              <Link to="/drives">View all drives — Simple / Detailed</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
