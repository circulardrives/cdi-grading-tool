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
  ScanAllHostsButton,
  ScanAllHostsProgress,
} from "@/components/scan-all-hosts"
import {
  useFleetDevicesQuery,
  useHealthQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import { scanDevices } from "@/lib/api"
import { describeRequestError, hostHasAddress } from "@/lib/host-utils"
import { setSelectedHostId, useSelectedHostId } from "@/lib/selected-host"
import type { ScanResponse } from "@/lib/types"

const LOCAL_SCAN_TARGET = "local"

/** "Scanned on pecan09" / "Scanned on this bench", from where the API ran the scan. */
function scannedOnLabel(result: ScanResponse, hostName: string | null): string {
  if (result.executed_on === "remote") {
    return `Scanned on ${hostName ?? result.remote_address ?? "the host"}`
  }
  if (result.executed_on === "local") {
    return "Scanned on this bench"
  }
  return hostName ? `Scanned for ${hostName}` : "Scanned"
}

export function ScanPage() {
  const { useMockData, mockDataPath } = useMockDataSettings()
  const { invalidateAfterScan } = useInvalidateCdiQueries()
  const machinesQuery = useMachinesQuery()
  const healthQuery = useHealthQuery()
  const [scanning, setScanning] = useState(false)
  const selectedHostId = useSelectedHostId()
  const scanTarget = selectedHostId ?? LOCAL_SCAN_TARGET
  const [ignoreAta, setIgnoreAta] = useState(false)
  const [ignoreNvme, setIgnoreNvme] = useState(false)
  const [ignoreScsi, setIgnoreScsi] = useState(false)
  const [lastResult, setLastResult] = useState<ScanResponse | null>(null)
  const [lastResultHost, setLastResultHost] = useState<string | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)

  const hosts = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const health = healthQuery.data ?? null
  const loading = machinesQuery.isLoading || healthQuery.isLoading

  const selectedHost = useMemo(
    () => (scanTarget === LOCAL_SCAN_TARGET ? null : hosts.find((host) => host.id === scanTarget) ?? null),
    [hosts, scanTarget]
  )
  const targetName = selectedHost?.name ?? "this bench"
  // Scans for a host with an address run on that host, not on this bench.
  const targetIsRemote = Boolean(selectedHost && hostHasAddress(selectedHost))

  const hasAddressedHosts = hosts.some(hostHasAddress)
  const fleetQuery = useFleetDevicesQuery(hasAddressedHosts)
  // `null` means the API predates /fleet/devices (no Scan all hosts).
  const canScanAll = hasAddressedHosts && fleetQuery.data !== null

  useEffect(() => {
    // A stale selection (host deleted elsewhere) falls back to the local API.
    if (!machinesQuery.isSuccess || !selectedHostId) {
      return
    }
    if (!hosts.some((host) => host.id === selectedHostId)) {
      setSelectedHostId(null)
    }
  }, [machinesQuery.isSuccess, hosts, selectedHostId])

  const selectTarget = (value: string) => {
    setSelectedHostId(value === LOCAL_SCAN_TARGET ? null : value)
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
      setLastResultHost(targetName)
      await invalidateAfterScan(machineId)
      toast.success(`Scanned ${targetName} — ${result.summary.total} drive(s)`)
    } catch (err) {
      const message = describeRequestError(err, targetName, "Scan failed")
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
        description={
          canScanAll
            ? "Scan every host at once, or pick one host. Each host's drives are graded on that host."
            : "Grade the drives attached to this bench, or to a host you pick."
        }
        actions={
          <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
            <RefreshCwIcon data-icon="inline-start" />
            Refresh
          </Button>
        }
      />

      {canScanAll ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ServerIcon className="size-4" />
              Scan all hosts
            </CardTitle>
            <CardDescription>
              Grades the drives on every host in your fleet. Hosts that can&apos;t be reached are
              listed with what to fix — the rest still get scanned.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              <ScanAllHostsButton size="lg" />
              <Button variant="outline" size="lg" asChild>
                <Link to="/drives" onClick={() => setSelectedHostId(null)}>
                  <HardDriveIcon data-icon="inline-start" />
                  View all drives
                </Link>
              </Button>
            </div>
            <ScanAllHostsProgress hostCount={fleetQuery.data?.hosts.length} />
          </CardContent>
        </Card>
      ) : null}

      {!targetIsRemote && missingTools.length > 0 ? (
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

      {!targetIsRemote && health?.is_root === false ? (
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
            <CardTitle>{canScanAll ? "Scan one host" : "Run scan"}</CardTitle>
            <CardDescription>
              {targetIsRemote && selectedHost
                ? `Runs on ${selectedHost.name} at ${selectedHost.address}`
                : selectedHost
                  ? `Grade drives for ${selectedHost.name} on this bench`
                  : "Grade the drives attached to this bench"}
              {useMockData ? " · mock data enabled" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {loading ? (
              <Skeleton className="h-10 w-full max-w-xs" />
            ) : (
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="scan-target">Host</FieldLabel>
                  <Select value={scanTarget} onValueChange={selectTarget}>
                    <SelectTrigger id="scan-target" className="w-full max-w-xs">
                      <SelectValue placeholder="Select target" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={LOCAL_SCAN_TARGET}>This bench</SelectItem>
                      {hosts.map((host) => (
                        <SelectItem key={host.id} value={host.id}>
                          {host.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FieldDescription>
                    {hosts.length === 0
                      ? "No hosts yet — this scans the bench running the dashboard. Add hosts on the Hosts page."
                      : "The host you pick here is also used on Hosts and Drive Health."}
                  </FieldDescription>
                </Field>
              </FieldGroup>
            )}

            <FieldGroup>
              <Field orientation="horizontal">
                <Switch
                  id="scan-ignore-ata"
                  checked={ignoreAta}
                  onCheckedChange={setIgnoreAta}
                  disabled={scanning}
                />
                <FieldLabel htmlFor="scan-ignore-ata">Ignore ATA/SATA</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch
                  id="scan-ignore-nvme"
                  checked={ignoreNvme}
                  onCheckedChange={setIgnoreNvme}
                  disabled={scanning}
                />
                <FieldLabel htmlFor="scan-ignore-nvme">Ignore NVMe</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch
                  id="scan-ignore-scsi"
                  checked={ignoreScsi}
                  onCheckedChange={setIgnoreScsi}
                  disabled={scanning}
                />
                <FieldLabel htmlFor="scan-ignore-scsi">Ignore SCSI/SAS</FieldLabel>
              </Field>
            </FieldGroup>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void runScan()} disabled={scanning || loading}>
                {scanning ? <Spinner data-icon="inline-start" /> : <ScanSearchIcon data-icon="inline-start" />}
                {scanning ? "Scanning…" : `Scan ${targetName}`}
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
                  <Link to="/hosts">Add hosts</Link>
                </Button>
              ) : null}
            </div>

            {scanning ? (
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <Spinner />
                Grading drives on {targetName} — this may take a minute on large inventories…
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
                ? `${scannedOnLabel(lastResult, lastResultHost)} · ${new Date(lastResult.scanned_at).toLocaleString()}`
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
                  {lastResult.summary.ungraded ? (
                    <Badge variant="outline">{lastResult.summary.ungraded} ungraded</Badge>
                  ) : null}
                </div>
                {scanTarget !== LOCAL_SCAN_TARGET ? (
                  <Button variant="outline" className="w-fit" asChild>
                    <Link to="/drives">View full drive tables</Link>
                  </Button>
                ) : null}
              </>
            ) : (
              <p className="text-muted-foreground text-sm">
                Summary appears here after a successful scan. For per-drive grades and telemetry,
                open Drive Health.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
