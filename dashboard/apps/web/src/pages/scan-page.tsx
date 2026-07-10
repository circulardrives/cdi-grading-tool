import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  AlertCircleIcon,
  HardDriveIcon,
  RefreshCwIcon,
  ScanSearchIcon,
  ServerIcon,
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
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@workspace/ui/components/field"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Spinner } from "@workspace/ui/components/spinner"
import { Switch } from "@workspace/ui/components/switch"

import { PageHeader } from "@/components/page-header"
import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import {
  useHealthQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import { scanDevices } from "@/lib/api"
import { getSelectedHostId, setSelectedHostId } from "@/lib/selected-host"
import type { ScanResponse } from "@/lib/types"

const LOCAL_SCAN_TARGET = "local"

export function ScanPage() {
  const { useMockData, mockDataPath } = useMockDataSettings()
  const { invalidateAfterScan } = useInvalidateCdiQueries()
  const machinesQuery = useMachinesQuery()
  const healthQuery = useHealthQuery()
  const [scanning, setScanning] = useState(false)
  const [scanTarget, setScanTarget] = useState<string>(() => getSelectedHostId() ?? LOCAL_SCAN_TARGET)
  const [ignoreAta, setIgnoreAta] = useState(false)
  const [ignoreNvme, setIgnoreNvme] = useState(false)
  const [ignoreScsi, setIgnoreScsi] = useState(false)
  const [lastResult, setLastResult] = useState<ScanResponse | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)

  const hosts = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const health = healthQuery.data ?? null
  const loading = machinesQuery.isLoading || healthQuery.isLoading

  const selectedHost = useMemo(
    () => (scanTarget === LOCAL_SCAN_TARGET ? null : hosts.find((host) => host.id === scanTarget) ?? null),
    [hosts, scanTarget]
  )

  useEffect(() => {
    if (
      machinesQuery.isLoading ||
      scanTarget === LOCAL_SCAN_TARGET ||
      hosts.length === 0
    ) {
      return
    }
    if (!hosts.some((host) => host.id === scanTarget)) {
      setScanTarget(getSelectedHostId() ?? (hosts[0]?.id ?? LOCAL_SCAN_TARGET))
    }
  }, [machinesQuery.isLoading, hosts, scanTarget])

  const selectTarget = (value: string) => {
    setScanTarget(value)
    if (value === LOCAL_SCAN_TARGET) {
      setSelectedHostId(null)
    } else {
      setSelectedHostId(value)
    }
  }

  const refresh = async () => {
    await Promise.all([machinesQuery.refetch(), healthQuery.refetch()])
  }

  const runScan = async () => {
    setScanning(true)
    setScanError(null)
    try {
      const machineId = scanTarget !== LOCAL_SCAN_TARGET ? scanTarget : null
      const result = await scanDevices({
        ignore_ata: ignoreAta,
        ignore_nvme: ignoreNvme,
        ignore_scsi: ignoreScsi,
        ...(machineId ? { machine_id: machineId } : {}),
        ...mockDataRequestFields(useMockData, mockDataPath),
      })
      setLastResult(result)
      await invalidateAfterScan(machineId)
      const label = selectedHost?.name ?? "local API"
      toast.success(`Scan complete for ${label} — ${result.summary.total} drive(s)`)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Scan failed"
      setScanError(message)
      toast.error(message)
    } finally {
      setScanning(false)
    }
  }

  const missingTools = health?.missing_required_tools ?? []

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Drive grading"
        title="Scan"
        description="Execute a CDI health scan on the local API. Associate results with a fleet host when registered."
        actions={
          <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
            <RefreshCwIcon data-icon="inline-start" />
            Refresh
          </Button>
        }
      />

      <Alert>
        <ServerIcon />
        <AlertTitle>Local scan mode (v1)</AlertTitle>
        <AlertDescription>
          Scans execute on the machine running <span className="font-mono">cdi-health-api</span>.
          Select a fleet host to store results against that host, or use Local API for an
          unregistered scan. View full drive tables on Drive Health.
        </AlertDescription>
      </Alert>

      {missingTools.length > 0 ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Missing grading tools</AlertTitle>
          <AlertDescription>
            The API reports missing required tools:{" "}
            <span className="font-mono">{missingTools.join(", ")}</span>. Install them on the
            grading host or use mock data mode for bench testing.
          </AlertDescription>
        </Alert>
      ) : null}

      {health && !health.is_root ? (
        <Alert>
          <AlertCircleIcon />
          <AlertTitle>Non-root API</AlertTitle>
          <AlertDescription>
            {health.message ??
              "Running without root may limit SMART access. Run cdi-health-api as root for live hardware grading."}
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Run scan</CardTitle>
            <CardDescription>
              {selectedHost
                ? `Grade drives for ${selectedHost.name}`
                : "Scan attached drives on the local API (no fleet host)"}
              {useMockData ? " · mock data enabled on Discover" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {loading ? (
              <Skeleton className="h-10 w-full max-w-xs" />
            ) : (
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="scan-target">Scan target</FieldLabel>
                  <Select value={scanTarget} onValueChange={selectTarget}>
                    <SelectTrigger id="scan-target" className="w-full max-w-xs">
                      <SelectValue placeholder="Select target" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={LOCAL_SCAN_TARGET}>Local API</SelectItem>
                      {hosts.map((host) => (
                        <SelectItem key={host.id} value={host.id}>
                          {host.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FieldDescription>
                    {hosts.length === 0
                      ? "No fleet hosts yet — scanning against the local API. Register hosts on the Hosts page."
                      : "Fleet host selection is shared with Drive Health via session storage."}
                  </FieldDescription>
                </Field>
              </FieldGroup>
            )}

            <FieldGroup>
              <Field orientation="horizontal">
                <Switch checked={ignoreAta} onCheckedChange={setIgnoreAta} disabled={scanning} />
                <FieldLabel>Ignore ATA/SATA</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch checked={ignoreNvme} onCheckedChange={setIgnoreNvme} disabled={scanning} />
                <FieldLabel>Ignore NVMe</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch checked={ignoreScsi} onCheckedChange={setIgnoreScsi} disabled={scanning} />
                <FieldLabel>Ignore SCSI/SAS</FieldLabel>
              </Field>
            </FieldGroup>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void runScan()} disabled={scanning || loading}>
                {scanning ? <Spinner data-icon="inline-start" /> : <ScanSearchIcon data-icon="inline-start" />}
                {scanning ? "Scanning…" : "Run scan"}
              </Button>
              {scanTarget !== LOCAL_SCAN_TARGET ? (
                <Button variant="outline" asChild>
                  <Link to="/drives">
                    <HardDriveIcon data-icon="inline-start" />
                    Drive Health
                  </Link>
                </Button>
              ) : null}
              {hosts.length === 0 ? (
                <Button variant="outline" asChild>
                  <Link to="/hosts">Register hosts</Link>
                </Button>
              ) : null}
            </div>

            {scanning ? (
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <Spinner />
                Grading attached drives — this may take a minute on large inventories…
              </div>
            ) : null}

            {scanError ? (
              <Alert variant="destructive">
                <AlertCircleIcon />
                <AlertTitle>Scan failed</AlertTitle>
                <AlertDescription>{scanError}</AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Last result</CardTitle>
            <CardDescription>
              {lastResult
                ? `Scanned ${new Date(lastResult.scanned_at).toLocaleString()}`
                : "Run a scan to see drive counts"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {lastResult ? (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-muted-foreground text-xs uppercase tracking-wide">Total</span>
                    <span className="text-2xl font-semibold">{lastResult.summary.total}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-muted-foreground text-xs uppercase tracking-wide">Healthy</span>
                    <span className="text-primary text-2xl font-semibold">
                      {lastResult.summary.healthy}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-muted-foreground text-xs uppercase tracking-wide">Warning</span>
                    <span className="text-2xl font-semibold">{lastResult.summary.warning}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-muted-foreground text-xs uppercase tracking-wide">Failed</span>
                    <span className="text-2xl font-semibold">{lastResult.summary.failed}</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{lastResult.summary.healthy} healthy</Badge>
                  <Badge variant="secondary">{lastResult.summary.warning} warning</Badge>
                  <Badge variant="destructive">{lastResult.summary.failed} failed</Badge>
                </div>
                {scanTarget !== LOCAL_SCAN_TARGET ? (
                  <Button variant="outline" className="w-fit" asChild>
                    <Link to="/drives">View full drive tables</Link>
                  </Button>
                ) : null}
              </>
            ) : (
              <p className="text-muted-foreground text-sm">
                Summary appears here after a successful scan. For per-drive grades and telemetry, open
                Drive Health once a fleet host is selected.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
