import { useMemo, useState } from "react"
import {
  AlertCircleIcon,
  CheckCircle2Icon,
  DownloadIcon,
  ExternalLinkIcon,
  FileTextIcon,
  HistoryIcon,
  PlayIcon,
  ScanSearchIcon,
  ServerIcon,
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
import { Input } from "@workspace/ui/components/input"
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
import { Switch } from "@workspace/ui/components/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { cn } from "@workspace/ui/lib/utils"

import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import { PageHeader } from "@/components/page-header"
import {
  ScanAllHostsButton,
  ScanAllHostsProgress,
} from "@/components/scan-all-hosts"
import {
  useDevicesQuery,
  useFleetDevicesQuery,
  useGenerateReportMutation,
  useHealthQuery,
  useHistoryPagesQuery,
  useMachinesQuery,
  useReportsQuery,
} from "@/hooks/use-cdi-queries"
import { downloadReportFile, openReportFile } from "@/lib/api"
import { formatScannedAgo, hostProblemMessage } from "@/lib/host-utils"
import {
  describeReportError,
  formatDrives,
  formatReportBenches,
  OLD_API_REPORT_MESSAGE,
  reportFileOf,
  reportIgnoredSource,
  reportReadyMessage,
  reportSourceLabel,
} from "@/lib/report-utils"
import type {
  FleetHost,
  HistorySummary,
  ReportFormat,
  ReportListEntry,
  ReportResponse,
  ReportSource,
} from "@/lib/types"

function formatWhen(value?: string | null): string {
  if (!value) {
    return "—"
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

type SourceOptionProps = {
  selected: boolean
  onSelect: () => void
  icon: typeof ServerIcon
  title: string
  description: string
  badge?: string
}

function SourceOption({
  selected,
  onSelect,
  icon: Icon,
  title,
  description,
  badge,
}: SourceOptionProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "flex flex-col gap-1 rounded-2xl border p-4 text-left transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/30",
        selected
          ? "border-primary bg-primary/5 ring-1 ring-primary/40"
          : "hover:bg-muted/60"
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        <Icon className="size-4 text-primary" aria-hidden />
        {title}
        {badge ? <Badge variant="secondary">{badge}</Badge> : null}
      </span>
      <span className="text-sm text-muted-foreground">{description}</span>
    </button>
  )
}

/** Benches the "Latest scans from all benches" report will include. */
function FleetPreview({
  hosts,
  loading,
  unsupported,
  error,
}: {
  hosts: FleetHost[]
  loading: boolean
  unsupported: boolean
  error: string | null
}) {
  if (loading) {
    return <Skeleton className="h-20 w-full" />
  }
  if (error) {
    return (
      <p className="text-sm text-destructive">
        Couldn't load the benches' saved scans: {error}
      </p>
    )
  }
  if (unsupported) {
    return (
      <Alert>
        <AlertCircleIcon />
        <AlertTitle>Can't combine benches yet</AlertTitle>
        <AlertDescription>
          CDI Health on this computer is too old to report on other benches.
          Update it, or use Scan this bench now below.
        </AlertDescription>
      </Alert>
    )
  }

  const included = hosts.filter((host) => host.scanned_at)
  const missing = hosts.filter((host) => !host.scanned_at)

  if (included.length === 0) {
    return (
      <div className="flex flex-col gap-3 rounded-2xl border border-dashed p-4">
        <p className="text-sm">
          <span className="font-medium">No saved scans yet.</span> Scan all
          benches first, then come back and make the report.
        </p>
        <div>
          <ScanAllHostsButton size="sm" />
        </div>
        <ScanAllHostsProgress hostCount={hosts.length} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium">
        Will include {included.length} bench{included.length === 1 ? "" : "es"}:
      </p>
      <ul className="flex flex-col gap-1.5" aria-label="Benches in this report">
        {included.map((host, index) => {
          const problem = hostProblemMessage(host.name, host.status, host.error)
          return (
            <li
              key={host.machine_id ?? `${host.name}-${index}`}
              className="flex flex-col gap-0.5 rounded-xl border px-3 py-2 text-sm"
            >
              <span className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{host.name}</span>
                <span className="text-xs text-muted-foreground">
                  {formatDrives(host.device_count)} ·{" "}
                  {formatScannedAgo(host.scanned_at)}
                </span>
              </span>
              {problem ? (
                <span className="text-xs text-muted-foreground">
                  Last scan attempt failed, so this uses the older scan.{" "}
                  {problem}
                </span>
              ) : null}
            </li>
          )
        })}
      </ul>
      {missing.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Not included (never scanned):{" "}
          {missing.map((host) => host.name).join(", ")}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span>Want fresher results? Scan all benches first.</span>
        <ScanAllHostsButton size="sm" />
      </div>
      <ScanAllHostsProgress hostCount={hosts.length} />
    </div>
  )
}

/** Pick one or more saved scans from History. */
function SavedScanPicker({
  selectedIds,
  onToggle,
  hostName,
}: {
  selectedIds: string[]
  onToggle: (entry: HistorySummary) => void
  hostName: (machineId?: string | null) => string
}) {
  const historyQuery = useHistoryPagesQuery(null)
  const entries = useMemo(
    () => historyQuery.data?.pages.flat() ?? [],
    [historyQuery.data]
  )

  if (historyQuery.isLoading) {
    return <Skeleton className="h-32 w-full" />
  }
  if (historyQuery.error instanceof Error) {
    return (
      <p className="text-sm text-destructive">
        Couldn't load saved scans: {historyQuery.error.message}
      </p>
    )
  }
  if (entries.length === 0) {
    return (
      <div className="flex flex-col gap-3 rounded-2xl border border-dashed p-4">
        <p className="text-sm">
          <span className="font-medium">No saved scans yet.</span> Scan all
          benches first, then pick a scan here.
        </p>
        <div>
          <ScanAllHostsButton size="sm" />
        </div>
        <ScanAllHostsProgress />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium">
        Pick one or more saved scans
        {selectedIds.length > 0 ? ` · ${selectedIds.length} picked` : ""}
      </p>
      <ul
        className="flex max-h-80 flex-col gap-1.5 overflow-y-auto pr-1"
        aria-label="Saved scans"
      >
        {entries.map((entry) => {
          const checked = selectedIds.includes(entry.id)
          const id = `saved-scan-${entry.id}`
          return (
            <li key={entry.id}>
              <label
                htmlFor={id}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2 text-sm",
                  checked ? "border-primary bg-primary/5" : "hover:bg-muted/60"
                )}
              >
                <input
                  id={id}
                  type="checkbox"
                  className="size-4 shrink-0 accent-primary"
                  checked={checked}
                  onChange={() => onToggle(entry)}
                />
                <span className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">
                    {hostName(entry.machine_id)}
                    {entry.mock ? (
                      <Badge variant="secondary" className="ml-2">
                        Mock
                      </Badge>
                    ) : null}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDrives(entry.device_count)} · Scanned{" "}
                    {formatWhen(entry.scanned_at)}
                  </span>
                </span>
              </label>
            </li>
          )
        })}
      </ul>
      {historyQuery.hasNextPage ? (
        <div>
          <Button
            variant="outline"
            size="sm"
            disabled={historyQuery.isFetchingNextPage}
            aria-busy={historyQuery.isFetchingNextPage}
            onClick={() => void historyQuery.fetchNextPage()}
          >
            {historyQuery.isFetchingNextPage ? (
              <Spinner data-icon="inline-start" />
            ) : null}
            Show older scans
          </Button>
        </div>
      ) : null}
    </div>
  )
}

export function ReportsPage() {
  const { useMockData, mockDataPath } = useMockDataSettings()
  const healthQuery = useHealthQuery()
  const machinesQuery = useMachinesQuery()
  const fleetQuery = useFleetDevicesQuery()
  const reportsQuery = useReportsQuery()
  const generate = useGenerateReportMutation()

  const [source, setSource] = useState<ReportSource>("fleet")
  const [format, setFormat] = useState<ReportFormat>("html")
  const [historyIds, setHistoryIds] = useState<string[]>([])
  const [historyPicks, setHistoryPicks] = useState<HistorySummary[]>([])
  const [outputPath, setOutputPath] = useState("")
  const [device, setDevice] = useState("")
  const [ignoreAta, setIgnoreAta] = useState(false)
  const [ignoreNvme, setIgnoreNvme] = useState(false)
  const [ignoreScsi, setIgnoreScsi] = useState(false)
  const [lastReport, setLastReport] = useState<ReportResponse | null>(null)
  const [reportAction, setReportAction] = useState<string | null>(null)

  // Drive paths for the "Scan this bench now" device filter.
  const devicesQuery = useDevicesQuery(null, source === "scan")
  const localDevices = devicesQuery.data?.devices ?? []

  const hostNames = useMemo(() => {
    const map = new Map<string, string>()
    for (const host of machinesQuery.data ?? []) {
      map.set(host.id, host.name)
    }
    return map
  }, [machinesQuery.data])
  const hostName = (machineId?: string | null) =>
    machineId ? (hostNames.get(machineId) ?? "Unknown bench") : "This bench"

  const fleetHosts = fleetQuery.data?.hosts ?? []
  const fleetUnsupported = fleetQuery.data === null
  const fleetHasSaved = fleetHosts.some((host) => host.scanned_at)
  const pdfAvailable = healthQuery.data?.weasyprint_available === true
  const running = generate.isPending

  const canGenerate =
    !running &&
    (source === "scan" ||
      (source === "fleet" && fleetHasSaved && !fleetUnsupported) ||
      (source === "history" && historyIds.length > 0))

  const toggleHistory = (entry: HistorySummary) => {
    setHistoryIds((ids) =>
      ids.includes(entry.id)
        ? ids.filter((id) => id !== entry.id)
        : [...ids, entry.id]
    )
    setHistoryPicks((picks) =>
      picks.some((pick) => pick.id === entry.id)
        ? picks.filter((pick) => pick.id !== entry.id)
        : [...picks, entry]
    )
  }

  const runReport = async () => {
    try {
      const result = await generate.mutateAsync(
        source === "scan"
          ? {
              format,
              source,
              output_file: outputPath.trim() || undefined,
              ignore_ata: ignoreAta,
              ignore_nvme: ignoreNvme,
              ignore_scsi: ignoreScsi,
              device: device.trim() || undefined,
              ...mockDataRequestFields(useMockData, mockDataPath),
            }
          : source === "history"
            ? { format, source, history_ids: historyIds }
            : { format, source }
      )
      setLastReport(result)
      if (reportIgnoredSource(source, result)) {
        toast.warning(OLD_API_REPORT_MESSAGE)
      } else {
        toast.success(reportReadyMessage(result))
      }
    } catch (err) {
      toast.error(describeReportError(err))
    }
  }

  const handleOpen = async (filename: string) => {
    setReportAction(`${filename}-open`)
    try {
      await openReportFile(filename)
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Couldn't open the report"
      )
    } finally {
      setReportAction(null)
    }
  }

  const handleDownload = async (filename: string) => {
    setReportAction(`${filename}-download`)
    try {
      await downloadReportFile(filename)
      toast.success(`Downloaded ${filename}`)
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Couldn't download the report"
      )
    } finally {
      setReportAction(null)
    }
  }

  const reportButtons = (filename: string) => (
    <>
      <Button
        variant="outline"
        size="sm"
        disabled={reportAction === `${filename}-open`}
        aria-busy={reportAction === `${filename}-open`}
        onClick={() => void handleOpen(filename)}
      >
        {reportAction === `${filename}-open` ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <ExternalLinkIcon data-icon="inline-start" />
        )}
        Open
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={reportAction === `${filename}-download`}
        aria-busy={reportAction === `${filename}-download`}
        onClick={() => void handleDownload(filename)}
      >
        {reportAction === `${filename}-download` ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <DownloadIcon data-icon="inline-start" />
        )}
        Download
      </Button>
    </>
  )

  const recent: ReportListEntry[] = reportsQuery.data?.reports ?? []
  const savedOnServer = reportsQuery.data?.savedOnServer ?? true

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Reports"
        title="Health Reports"
        description="Make an HTML, CSV, or PDF drive health report to hand off — from the latest scans of every bench, or from a saved scan."
      />

      {format === "pdf" && !pdfAvailable ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>PDF isn't available here</AlertTitle>
          <AlertDescription>
            {healthQuery.isLoading ? (
              "Checking whether this computer can make PDFs…"
            ) : (
              <>
                This computer's CDI Health can't make PDFs (WeasyPrint is
                missing). Pick HTML or CSV, or install it with{" "}
                <span className="font-mono">pip install weasyprint</span>.
              </>
            )}
          </AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileTextIcon className="text-primary" />
            Make a report
          </CardTitle>
          <CardDescription>
            Reports use scans that are already saved — nothing is rescanned
            unless you pick Scan this bench now.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium" id="report-source-label">
              What to report on
            </p>
            <div
              role="radiogroup"
              aria-labelledby="report-source-label"
              className="flex flex-col gap-2"
            >
              <div className="grid gap-2 md:grid-cols-2">
                <SourceOption
                  selected={source === "fleet"}
                  onSelect={() => setSource("fleet")}
                  icon={ServerIcon}
                  title="Latest scans from all benches"
                  badge="Recommended"
                  description="One report with the most recent saved scan of every bench."
                />
                <SourceOption
                  selected={source === "history"}
                  onSelect={() => setSource("history")}
                  icon={HistoryIcon}
                  title="A saved scan…"
                  description="Pick one or more scans from History."
                />
              </div>
              <button
                type="button"
                role="radio"
                aria-checked={source === "scan"}
                onClick={() => setSource("scan")}
                className={cn(
                  "flex w-fit items-center gap-2 rounded-xl px-2 py-1 text-left text-sm text-muted-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/30",
                  source === "scan"
                    ? "bg-muted font-medium text-foreground"
                    : "hover:text-foreground"
                )}
              >
                <ScanSearchIcon className="size-4" aria-hidden />
                Or: Scan this bench now (only drives plugged into this computer)
              </button>
            </div>
          </div>

          <div className="rounded-2xl border bg-muted/30 p-4">
            {source === "fleet" ? (
              <FleetPreview
                hosts={fleetHosts}
                loading={fleetQuery.isLoading}
                unsupported={fleetUnsupported}
                error={
                  fleetQuery.error instanceof Error
                    ? fleetQuery.error.message
                    : null
                }
              />
            ) : source === "history" ? (
              <div className="flex flex-col gap-3">
                <SavedScanPicker
                  selectedIds={historyIds}
                  onToggle={toggleHistory}
                  hostName={hostName}
                />
                {historyPicks.length > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Will include:{" "}
                    {historyPicks
                      .map(
                        (pick) =>
                          `${hostName(pick.machine_id)} (${formatDrives(pick.device_count)}, ${formatWhen(pick.scanned_at)})`
                      )
                      .join("; ")}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <p className="text-sm">
                  Scans the drives plugged into{" "}
                  <span className="font-medium">this computer</span> right now,
                  then makes the report. On a technician laptop this is usually
                  empty — use Latest scans from all benches instead.
                </p>
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="device-filter">
                      Only one drive (optional)
                    </FieldLabel>
                    <Input
                      id="device-filter"
                      value={device}
                      onChange={(e) => setDevice(e.target.value)}
                      placeholder="/dev/nvme0"
                      list="device-options"
                    />
                    <datalist id="device-options">
                      {localDevices.map((d) =>
                        d.dut ? <option key={d.dut} value={d.dut} /> : null
                      )}
                    </datalist>
                  </Field>
                  <Field orientation="horizontal">
                    <Switch
                      id="report-ignore-ata"
                      checked={ignoreAta}
                      onCheckedChange={setIgnoreAta}
                    />
                    <FieldLabel htmlFor="report-ignore-ata">
                      Skip ATA/SATA drives
                    </FieldLabel>
                  </Field>
                  <Field orientation="horizontal">
                    <Switch
                      id="report-ignore-nvme"
                      checked={ignoreNvme}
                      onCheckedChange={setIgnoreNvme}
                    />
                    <FieldLabel htmlFor="report-ignore-nvme">
                      Skip NVMe drives
                    </FieldLabel>
                  </Field>
                  <Field orientation="horizontal">
                    <Switch
                      id="report-ignore-scsi"
                      checked={ignoreScsi}
                      onCheckedChange={setIgnoreScsi}
                    />
                    <FieldLabel htmlFor="report-ignore-scsi">
                      Skip SCSI/SAS drives
                    </FieldLabel>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="output-path">
                      Save to (optional)
                    </FieldLabel>
                    <Input
                      id="output-path"
                      value={outputPath}
                      onChange={(e) => setOutputPath(e.target.value)}
                      placeholder="/tmp/cdi-report.html"
                    />
                    <FieldDescription>
                      Leave blank to use the usual reports folder.
                    </FieldDescription>
                  </Field>
                </FieldGroup>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <Field className="w-full max-w-48">
              <FieldLabel htmlFor="report-format">Format</FieldLabel>
              <Select
                value={format}
                onValueChange={(value) => setFormat(value as ReportFormat)}
              >
                <SelectTrigger id="report-format" className="w-full">
                  <SelectValue placeholder="Select format" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="html">HTML</SelectItem>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="pdf">PDF</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            <Button
              onClick={() => void runReport()}
              disabled={!canGenerate}
              aria-busy={running}
            >
              {running ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <PlayIcon data-icon="inline-start" />
              )}
              {running
                ? source === "scan"
                  ? "Scanning and making report…"
                  : "Making report…"
                : "Make report"}
            </Button>
          </div>

          {lastReport ? (
            <div
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border p-3"
              role="status"
            >
              <span className="flex items-center gap-2 text-sm">
                <CheckCircle2Icon className="size-4 text-primary" aria-hidden />
                <span>
                  <span className="font-medium">Report ready</span> ·{" "}
                  {lastReport.format.toUpperCase()} ·{" "}
                  {formatDrives(lastReport.devices_count)}
                  {lastReport.hosts?.length
                    ? ` · ${formatReportBenches(lastReport.hosts)}`
                    : ""}
                </span>
              </span>
              <span className="flex flex-wrap gap-2">
                {reportButtons(reportFileOf(lastReport))}
              </span>
            </div>
          ) : null}
          <span className="sr-only" aria-live="polite">
            {running
              ? "Making report"
              : reportAction
                ? "Working on report"
                : ""}
          </span>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent reports</CardTitle>
          <CardDescription>
            {savedOnServer
              ? "Newest first. Anyone using this dashboard sees the same list."
              : "Kept in this browser only — update CDI Health to keep reports for everyone."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reportsQuery.isLoading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : reportsQuery.error instanceof Error ? (
            <p className="text-sm text-destructive">
              Couldn't load recent reports: {reportsQuery.error.message}
            </p>
          ) : recent.length === 0 ? (
            <Empty className="border">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <FileTextIcon />
                </EmptyMedia>
                <EmptyTitle>No reports yet</EmptyTitle>
                <EmptyDescription>
                  Reports you make appear here so you can open or download them
                  again.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Benches</TableHead>
                  <TableHead>Drives</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent.map((entry, index) => (
                  <TableRow key={`${entry.filename}-${index}`}>
                    <TableCell className="whitespace-nowrap">
                      {formatWhen(entry.generated_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {entry.format.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="flex flex-col">
                        <span>{formatReportBenches(entry.hosts)}</span>
                        {reportSourceLabel(entry.source) ? (
                          <span className="text-xs text-muted-foreground">
                            {reportSourceLabel(entry.source)}
                          </span>
                        ) : null}
                      </span>
                    </TableCell>
                    <TableCell>{entry.devices_count}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {reportButtons(entry.filename)}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
