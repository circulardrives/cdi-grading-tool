import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  AlertCircleIcon,
  HardDriveIcon,
  RefreshCwIcon,
  ScanSearchIcon,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"

import { DriveHealthTable } from "@/components/drive-health-table"
import { PageHeader } from "@/components/page-header"
import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import {
  useDevicesQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import { scanDevices } from "@/lib/api"
import { getDetailedColumns, getSimpleColumns } from "@/lib/drive-columns"
import {
  countByDriveClass,
  DRIVE_CLASS_ORDER,
  getReportCategory,
} from "@/lib/drive-labels"
import { getSelectedHostId, setSelectedHostId } from "@/lib/selected-host"
import type { DriveClass, DriveViewMode } from "@/lib/types"

export function DriveHealthPage() {
  const { useMockData, mockDataPath } = useMockDataSettings()
  const { invalidateAfterScan } = useInvalidateCdiQueries()
  const [selectedHostId, setSelectedHostIdState] = useState<string | null>(
    () => getSelectedHostId()
  )
  const [scanning, setScanning] = useState(false)
  const [viewMode, setViewMode] = useState<DriveViewMode>("simple")
  const [activeClass, setActiveClass] = useState<DriveClass | "all">("all")

  const machinesQuery = useMachinesQuery()
  const devicesQuery = useDevicesQuery(selectedHostId, true)

  const noScanCached = Boolean(
    selectedHostId &&
      devicesQuery.error instanceof Error &&
      devicesQuery.error.message.includes("No scan cached")
  )

  const hosts = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const devices = useMemo(
    () => (noScanCached ? [] : (devicesQuery.data?.devices ?? [])),
    [devicesQuery.data?.devices, noScanCached]
  )
  const scannedAt = devicesQuery.data?.scanned_at ?? null
  const loading = machinesQuery.isLoading || devicesQuery.isLoading

  const selectedHost = useMemo(
    () => hosts.find((host) => host.id === selectedHostId) ?? null,
    [hosts, selectedHostId]
  )

  const error =
    noScanCached
      ? null
      : devicesQuery.error instanceof Error
        ? devicesQuery.error.message
        : machinesQuery.error instanceof Error
          ? machinesQuery.error.message
          : null

  const selectHost = (hostId: string | null) => {
    setSelectedHostIdState(hostId)
    setSelectedHostId(hostId)
  }

  const refresh = async () => {
    await Promise.all([machinesQuery.refetch(), devicesQuery.refetch()])
  }

  const runScan = async () => {
    if (!selectedHostId) {
      toast.error("Select a host on the Hosts page before running a scan")
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
      toast.success(`Scan complete — ${result.summary.total} drive(s) graded`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Scan failed")
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
    return devices.filter(
      (device) => getReportCategory(device) === activeClass
    )
  }, [activeClass, devices])

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Drive inventory"
        title="Attached Drive Health"
        description="Review graded drives for a selected fleet host. Rows are keyed by serial number and grouped by drive class."
        badge={
          scannedAt
            ? `Last scan ${new Date(scannedAt).toLocaleString()}`
            : undefined
        }
        actions={
          <>
            <Select
              value={selectedHostId ?? "none"}
              onValueChange={(value) => selectHost(value === "none" ? null : value)}
            >
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="Select host" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No host selected</SelectItem>
                {hosts.map((host) => (
                  <SelectItem key={host.id} value={host.id}>
                    {host.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
              <RefreshCwIcon data-icon="inline-start" />
              Refresh
            </Button>
            <Button onClick={() => void runScan()} disabled={scanning || !selectedHostId}>
              <ScanSearchIcon data-icon="inline-start" />
              {scanning ? "Scanning…" : "Run scan"}
            </Button>
          </>
        }
      />

      {!selectedHostId ? (
        <Alert>
          <AlertCircleIcon />
          <AlertTitle>Select a fleet host</AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>
              Drive scans are associated with a registered host. Choose one here or register hosts
              on the Hosts page.
            </span>
            <Button variant="outline" className="w-fit" asChild>
              <Link to="/hosts">Open Hosts</Link>
            </Button>
          </AlertDescription>
        </Alert>
      ) : selectedHost ? (
        <Alert>
          <AlertCircleIcon />
          <AlertTitle>Host context: {selectedHost.name}</AlertTitle>
          <AlertDescription>
            Showing drives from the latest scan for{" "}
            <span className="font-mono">{selectedHost.hostname}</span>. Selecting a host filters
            by <span className="font-mono">machine_id</span> on the configured API; host addresses
            are registry-only and do not switch backends.
          </AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Cannot reach grading host</AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>{error}</span>
            <span>
              Confirm `cdi-health-api` is running on this host (typically{" "}
              <span className="font-mono">127.0.0.1:8844</span>) and run as root
              for live SMART access. Use mock mode for bench testing without
              hardware.
            </span>
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader className="gap-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle>Drive tables</CardTitle>
              <CardDescription>
                {devices.length} attached drive(s) · switch between grading
                summary and full telemetry columns
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
                  Run a scan for the selected host from this page or from Scan to inventory attached
                  SATA, SAS, and NVMe drives.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent className="flex flex-wrap gap-2">
                <Button onClick={() => void runScan()} disabled={scanning}>
                  <ScanSearchIcon data-icon="inline-start" />
                  Run scan
                </Button>
                <Button variant="outline" asChild>
                  <Link to="/scan">Open Scan</Link>
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
                {viewMode === "simple" ? (
                  visibleClasses.map((driveClass) => {
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
                          columns={getSimpleColumns(driveClass)}
                        />
                      </section>
                    )
                  })
                ) : (
                  visibleClasses.map((driveClass) => {
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
                          columns={getDetailedColumns(driveClass)}
                        />
                      </section>
                    )
                  })
                )}
              </TabsContent>

              {visibleClasses.map((driveClass) => (
                <TabsContent key={driveClass} value={driveClass}>
                  <DriveHealthTable
                    devices={filteredDevices}
                    columns={
                      viewMode === "simple"
                        ? getSimpleColumns(driveClass)
                        : getDetailedColumns(driveClass)
                    }
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
