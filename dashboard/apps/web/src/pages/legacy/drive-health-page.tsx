import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  AlertCircleIcon,
  HardDriveIcon,
  RefreshCwIcon,
  ScanSearchIcon,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { Spinner } from "@workspace/ui/components/spinner"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"

import { DriveHealthTable } from "@/components/drive-health-table"
import { FleetHostList } from "@/components/fleet-host-list"
import { PageHeader } from "@/components/page-header"
import {
  ScanAllHostsButton,
  ScanAllHostsProgress,
} from "@/components/scan-all-hosts"
import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import {
  useDevicesQuery,
  useFleetDevicesQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
  useScanAllStatus,
} from "@/hooks/use-cdi-queries"
import { scanDevices } from "@/lib/api"
import {
  getDetailedColumns,
  getSimpleColumns,
  withHostColumn,
} from "@/lib/drive-columns"
import {
  countByDriveClass,
  DRIVE_CLASS_ORDER,
  getReportCategory,
} from "@/lib/drive-labels"
import { describeRequestError, hostHasAddress } from "@/lib/host-utils"
import { setSelectedHostId, useSelectedHostId } from "@/lib/selected-host"
import type { DeviceRecord, DriveClass, DriveViewMode } from "@/lib/types"

const ALL_HOSTS = "all"
const NO_HOST = "none"

export function DriveHealthPage() {
  const { useMockData, mockDataPath } = useMockDataSettings()
  const { invalidateAfterScan } = useInvalidateCdiQueries()
  const selectedHostId = useSelectedHostId()
  const [scanning, setScanning] = useState(false)
  const [viewMode, setViewMode] = useState<DriveViewMode>("simple")
  const [activeClass, setActiveClass] = useState<DriveClass | "all">("all")

  const machinesQuery = useMachinesQuery()
  const hosts = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const hasAddressedHosts = hosts.some(hostHasAddress)

  // `null` data means the API predates /fleet/devices: fall back to one host.
  const fleetQuery = useFleetDevicesQuery(hasAddressedHosts)
  const fleetAvailable = hasAddressedHosts && fleetQuery.data !== null
  const allHostsMode = fleetAvailable && !selectedHostId
  const scanAll = useScanAllStatus()

  const devicesQuery = useDevicesQuery(
    selectedHostId,
    !machinesQuery.isLoading && !allHostsMode
  )

  useEffect(() => {
    // A stale selection (host removed elsewhere) falls back to the default view.
    if (!machinesQuery.isSuccess || !selectedHostId) {
      return
    }
    if (!hosts.some((host) => host.id === selectedHostId)) {
      setSelectedHostId(null)
    }
  }, [machinesQuery.isSuccess, hosts, selectedHostId])

  const noScanCached = Boolean(
    selectedHostId &&
    devicesQuery.error instanceof Error &&
    devicesQuery.error.message.includes("No scan cached")
  )

  const devices: DeviceRecord[] = useMemo(() => {
    if (allHostsMode) {
      return fleetQuery.data?.devices ?? []
    }
    return noScanCached ? [] : (devicesQuery.data?.devices ?? [])
  }, [
    allHostsMode,
    fleetQuery.data?.devices,
    devicesQuery.data?.devices,
    noScanCached,
  ])

  const scannedAt = allHostsMode
    ? null
    : (devicesQuery.data?.scanned_at ?? null)
  const loading =
    machinesQuery.isLoading ||
    (allHostsMode ? fleetQuery.isLoading : devicesQuery.isLoading)

  const selectedHost = useMemo(
    () => hosts.find((host) => host.id === selectedHostId) ?? null,
    [hosts, selectedHostId]
  )
  const selectedHostName = selectedHost?.name ?? "this bench"

  const error = allHostsMode
    ? fleetQuery.error instanceof Error
      ? fleetQuery.error.message
      : null
    : noScanCached
      ? null
      : devicesQuery.error
        ? describeRequestError(
            devicesQuery.error,
            selectedHostName,
            "Could not load drives"
          )
        : machinesQuery.error instanceof Error
          ? machinesQuery.error.message
          : null

  const selectValue = selectedHostId ?? (fleetAvailable ? ALL_HOSTS : NO_HOST)

  const selectHost = (value: string) => {
    setSelectedHostId(value === ALL_HOSTS || value === NO_HOST ? null : value)
  }

  const refresh = async () => {
    await Promise.all([
      machinesQuery.refetch(),
      allHostsMode ? fleetQuery.refetch() : devicesQuery.refetch(),
    ])
  }

  const runScan = async () => {
    if (!selectedHostId) {
      toast.error("Pick a host first")
      return
    }

    setScanning(true)
    try {
      const result = await scanDevices({
        ignore_ata: false,
        ignore_nvme: false,
        ignore_scsi: false,
        machine_id: selectedHostId,
        ...mockDataRequestFields(useMockData, mockDataPath),
      })
      await invalidateAfterScan(selectedHostId)
      toast.success(
        `Scanned ${selectedHostName} — ${result.summary.total} drive(s) graded`
      )
    } catch (err) {
      toast.error(describeRequestError(err, selectedHostName, "Scan failed"))
    } finally {
      setScanning(false)
    }
  }

  const classCounts = useMemo(() => countByDriveClass(devices), [devices])

  const visibleClasses = useMemo(
    () => DRIVE_CLASS_ORDER.filter((driveClass) => classCounts[driveClass] > 0),
    [classCounts]
  )

  const filteredDevices = useMemo(() => {
    if (activeClass === "all") {
      return devices
    }
    return devices.filter((device) => getReportCategory(device) === activeClass)
  }, [activeClass, devices])

  const columnsFor = (driveClass: DriveClass) =>
    withHostColumn(
      viewMode === "simple"
        ? getSimpleColumns(driveClass)
        : getDetailedColumns(driveClass),
      allHostsMode
    )

  const fleetHosts = fleetQuery.data?.hosts ?? []

  const singleScanButton = (
    <Button
      onClick={() => void runScan()}
      disabled={scanning || !selectedHostId}
    >
      {scanning ? (
        <Spinner data-icon="inline-start" />
      ) : (
        <ScanSearchIcon data-icon="inline-start" />
      )}
      {scanning
        ? "Scanning…"
        : selectedHost
          ? `Scan ${selectedHost.name}`
          : "Run scan"}
    </Button>
  )

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Drive inventory"
        title="Attached Drive Health"
        description={
          allHostsMode
            ? "Graded drives from every host, grouped by drive class."
            : "Graded drives for one host, grouped by drive class."
        }
        badge={
          scannedAt
            ? `Last scan ${new Date(scannedAt).toLocaleString()}`
            : undefined
        }
        actions={
          <>
            <Select value={selectValue} onValueChange={selectHost}>
              <SelectTrigger
                className="w-[220px]"
                aria-label="Show drives from"
              >
                <SelectValue placeholder="Select host" />
              </SelectTrigger>
              <SelectContent>
                {fleetAvailable ? (
                  <SelectItem value={ALL_HOSTS}>All hosts</SelectItem>
                ) : (
                  <SelectItem value={NO_HOST}>No host selected</SelectItem>
                )}
                {hosts.map((host) => (
                  <SelectItem key={host.id} value={host.id}>
                    {host.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              onClick={() => void refresh()}
              disabled={loading || scanAll.pending}
            >
              <RefreshCwIcon data-icon="inline-start" />
              Refresh
            </Button>
            {/* Scan all benches lives in the app header. */}
            {allHostsMode ? null : singleScanButton}
          </>
        }
      />

      {allHostsMode ? null : !selectedHostId ? (
        <Alert>
          <AlertCircleIcon />
          <AlertTitle>Pick a host</AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>
              Choose a host above to see its drives, or add your benches on the
              Hosts page.
            </span>
            <Button variant="outline" className="w-fit" asChild>
              <Link to="/benches">Open Hosts</Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : selectedHost ? (
        <Alert>
          <AlertCircleIcon />
          <AlertTitle>Showing {selectedHost.name} only</AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>Drives from the latest scan of {selectedHost.name}.</span>
            {fleetAvailable ? (
              <Button
                variant="outline"
                className="w-fit"
                onClick={() => setSelectedHostId(null)}
              >
                Show all hosts
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>
            {allHostsMode
              ? "Couldn't load drives from your hosts"
              : "Couldn't load drives"}
          </AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>{error}</span>
            {!allHostsMode &&
            !(selectedHost && hostHasAddress(selectedHost)) ? (
              <span>
                Confirm `cdi-health-api` is running on this bench (typically{" "}
                <span className="font-mono">127.0.0.1:8844</span>) and run as
                root for live SMART access. Use mock mode for bench testing
                without hardware.
              </span>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {allHostsMode ? (
        <Card>
          <CardHeader>
            <CardTitle>Hosts</CardTitle>
            <CardDescription>
              {fleetHosts.length} host(s) · pick one to see only its drives
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <ScanAllHostsProgress hostCount={fleetHosts.length} />
            {fleetQuery.isLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <FleetHostList
                hosts={fleetHosts}
                scanning={scanAll.pending}
                onSelectHost={(host) => setSelectedHostId(host.machine_id)}
              />
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="gap-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle>Drive tables</CardTitle>
              <CardDescription>
                {devices.length} drive(s)
                {allHostsMode ? " across all hosts" : ""} · switch between
                grading summary and full telemetry columns
              </CardDescription>
            </div>
            <Tabs
              value={viewMode}
              onValueChange={(value) => setViewMode(value as DriveViewMode)}
            >
              <TabsList>
                <TabsTrigger value="simple">Simple</TabsTrigger>
                <TabsTrigger value="detailed">Detailed</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : devices.length === 0 ? (
            <Empty className="border">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <HardDriveIcon />
                </EmptyMedia>
                <EmptyTitle>No drives graded yet</EmptyTitle>
                <EmptyDescription>
                  {allHostsMode
                    ? "Scan all hosts to grade the SATA, SAS, and NVMe drives attached to every bench."
                    : "Scan the selected host to grade its attached SATA, SAS, and NVMe drives."}
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent className="flex flex-wrap gap-2">
                {allHostsMode ? <ScanAllHostsButton /> : singleScanButton}
                <Button variant="outline" asChild>
                  <Link to="/">Open Scan</Link>
                </Button>
              </EmptyContent>
            </Empty>
          ) : (
            <Tabs
              value={activeClass}
              onValueChange={(value) =>
                setActiveClass(value as DriveClass | "all")
              }
            >
              <TabsList className="h-auto flex-wrap justify-start">
                <TabsTrigger value="all">
                  All drives
                  <Badge variant="secondary">{devices.length}</Badge>
                </TabsTrigger>
                {visibleClasses.map((driveClass) => (
                  <TabsTrigger key={driveClass} value={driveClass}>
                    {driveClass}
                    <Badge variant="secondary">{classCounts[driveClass]}</Badge>
                  </TabsTrigger>
                ))}
              </TabsList>

              <TabsContent value="all" className="flex flex-col gap-4">
                {visibleClasses.map((driveClass) => {
                  const classDevices = devices.filter(
                    (device) => getReportCategory(device) === driveClass
                  )
                  return (
                    <section key={driveClass} className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <h2 className="font-heading text-base font-medium">
                          {driveClass}
                        </h2>
                        <Badge variant="outline">
                          {classDevices.length} drive(s)
                        </Badge>
                      </div>
                      <DriveHealthTable
                        devices={classDevices}
                        columns={columnsFor(driveClass)}
                      />
                    </section>
                  )
                })}
              </TabsContent>

              {visibleClasses.map((driveClass) => (
                <TabsContent key={driveClass} value={driveClass}>
                  <DriveHealthTable
                    devices={filteredDevices}
                    columns={columnsFor(driveClass)}
                  />
                </TabsContent>
              ))}
            </Tabs>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
