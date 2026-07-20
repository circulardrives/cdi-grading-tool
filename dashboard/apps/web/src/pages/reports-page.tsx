import { useState } from "react"
import {
  AlertCircleIcon,
  DownloadIcon,
  ExternalLinkIcon,
  FileTextIcon,
  FolderOutputIcon,
  PlayIcon,
} from "lucide-react"
import { toast } from "sonner"

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
import { Switch } from "@workspace/ui/components/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { Spinner } from "@workspace/ui/components/spinner"

import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"

import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import {
  useDevicesQuery,
  useHealthQuery,
  useInvalidateCdiQueries,
} from "@/hooks/use-cdi-queries"
import {
  downloadReportFile,
  generateReport,
  openReportFile,
  reportFilename,
} from "@/lib/api"
import type { ReportHistoryEntry } from "@/lib/types"

const HISTORY_KEY = "cdi-report-history"

/** Prefer crypto.randomUUID; fall back on HTTP LAN where it is unavailable. */
function newReportId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function loadReportHistory(): ReportHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) {
      return []
    }
    return JSON.parse(raw) as ReportHistoryEntry[]
  } catch {
    return []
  }
}

function saveReportHistory(entries: ReportHistoryEntry[]): void {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries))
}

export function ReportsPage() {
  const { useMockData, mockDataPath } = useMockDataSettings()
  const { invalidateDevices, invalidateHealth } = useInvalidateCdiQueries()
  const healthQuery = useHealthQuery()
  const devicesQuery = useDevicesQuery()
  const [format, setFormat] = useState<"html" | "pdf" | "csv">("html")
  const [outputPath, setOutputPath] = useState("")
  const [device, setDevice] = useState("")
  const [ignoreAta, setIgnoreAta] = useState(false)
  const [ignoreNvme, setIgnoreNvme] = useState(false)
  const [ignoreScsi, setIgnoreScsi] = useState(false)
  const [running, setRunning] = useState(false)
  const [history, setHistory] = useState<ReportHistoryEntry[]>(() =>
    loadReportHistory()
  )
  const [reportAction, setReportAction] = useState<string | null>(null)

  const devices = devicesQuery.data?.devices ?? []
  const pdfAvailable = healthQuery.data?.weasyprint_available === true
  const preloadError =
    healthQuery.error instanceof Error
      ? healthQuery.error.message
      : devicesQuery.error instanceof Error
        ? devicesQuery.error.message
        : null

  const runReport = async () => {
    setRunning(true)
    try {
      const result = await generateReport({
        format,
        output_file: outputPath.trim() || undefined,
        ignore_ata: ignoreAta,
        ignore_nvme: ignoreNvme,
        ignore_scsi: ignoreScsi,
        device: device.trim() || undefined,
        ...mockDataRequestFields(useMockData, mockDataPath),
      })

      const entry: ReportHistoryEntry = {
        ...result,
        filename: result.filename || reportFilename(result.output_file),
        id: newReportId(),
      }
      const nextHistory = [entry, ...history].slice(0, 20)
      setHistory(nextHistory)
      saveReportHistory(nextHistory)
      await Promise.all([invalidateDevices(), invalidateHealth()])
      toast.success(`Report generated — ${result.devices_count} device(s)`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report generation failed")
    } finally {
      setRunning(false)
    }
  }

  const handleOpenReport = async (entry: ReportHistoryEntry) => {
    const filename = entry.filename || reportFilename(entry.output_file)
    setReportAction(`${entry.id}-open`)
    try {
      await openReportFile(filename)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not open report")
    } finally {
      setReportAction(null)
    }
  }

  const handleDownloadReport = async (entry: ReportHistoryEntry) => {
    const filename = entry.filename || reportFilename(entry.output_file)
    setReportAction(`${entry.id}-download`)
    try {
      await downloadReportFile(filename)
      toast.success(`Downloaded ${filename}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not download report")
    } finally {
      setReportAction(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-2">
        <p className="text-muted-foreground font-mono text-xs uppercase tracking-[0.28em]">
          Reports
        </p>
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Technician Handoff Exports
          </h1>
          <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
            Generate HTML, PDF, or CSV reports from the current scan data via
            the CDI backend.
          </p>
        </div>
      </section>

      {preloadError ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Could not preload report context</AlertTitle>
          <AlertDescription>{preloadError}</AlertDescription>
        </Alert>
      ) : null}

      {format === "pdf" && !pdfAvailable ? (
        <Alert variant="destructive">
          <AlertTitle>PDF preflight failed</AlertTitle>
          <AlertDescription>
            {healthQuery.isLoading
              ? "Checking WeasyPrint availability on this grading host…"
              : "WeasyPrint is not available on this grading host. Install with "}
            {!healthQuery.isLoading ? (
              <>
                <span className="font-mono">pip install weasyprint</span> before
                generating PDF reports.
              </>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileTextIcon className="text-primary" />
              Generate Report
            </CardTitle>
            <CardDescription>
              Configure format and filters, then execute against the local API.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="report-format">Output format</FieldLabel>
                <Select
                  value={format}
                  onValueChange={(value) =>
                    setFormat(value as "html" | "pdf" | "csv")
                  }
                >
                  <SelectTrigger id="report-format" className="w-full">
                    <SelectValue placeholder="Select format" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="html">HTML</SelectItem>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="csv">CSV</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>

              <Field>
                <FieldLabel htmlFor="output-path">Output path (optional)</FieldLabel>
                <Input
                  id="output-path"
                  value={outputPath}
                  onChange={(e) => setOutputPath(e.target.value)}
                  placeholder="/tmp/cdi-report.html"
                />
                <FieldDescription>
                  Leave blank to use the API default output location.
                </FieldDescription>
              </Field>

              <Field>
                <FieldLabel htmlFor="device-filter">
                  Single device (optional)
                </FieldLabel>
                <Input
                  id="device-filter"
                  value={device}
                  onChange={(e) => setDevice(e.target.value)}
                  placeholder="/dev/nvme0"
                  list="device-options"
                />
                <datalist id="device-options">
                  {devices.map((d) =>
                    d.dut ? <option key={d.dut} value={d.dut} /> : null
                  )}
                </datalist>
              </Field>

              <Field orientation="horizontal">
                <Switch checked={ignoreAta} onCheckedChange={setIgnoreAta} />
                <FieldLabel>Ignore ATA/SATA</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch checked={ignoreNvme} onCheckedChange={setIgnoreNvme} />
                <FieldLabel>Ignore NVMe</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch checked={ignoreScsi} onCheckedChange={setIgnoreScsi} />
                <FieldLabel>Ignore SCSI/SAS</FieldLabel>
              </Field>
            </FieldGroup>

            <Button
              onClick={() => void runReport()}
              disabled={running}
              aria-busy={running}
            >
              {running ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <PlayIcon data-icon="inline-start" />
              )}
              {running ? "Generating…" : "Execute report"}
            </Button>
            <span className="sr-only" aria-live="polite">
              {running ? "Generating report" : reportAction ? "Working on report" : ""}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderOutputIcon className="text-primary" />
              Latest Output
            </CardTitle>
            <CardDescription>
              Most recent report from this session or browser history.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {history[0] ? (
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">{history[0].format.toUpperCase()}</Badge>
                  <Badge variant="outline">
                    {history[0].devices_count} device(s)
                  </Badge>
                </div>
                <p className="font-mono text-sm break-all">{history[0].output_file}</p>
                <p className="text-muted-foreground text-sm">
                  Generated {new Date(history[0].generated_at).toLocaleString()}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={reportAction === `${history[0].id}-open`}
                    aria-busy={reportAction === `${history[0].id}-open`}
                    onClick={() => void handleOpenReport(history[0])}
                  >
                    {reportAction === `${history[0].id}-open` ? (
                      <Spinner data-icon="inline-start" />
                    ) : (
                      <ExternalLinkIcon data-icon="inline-start" />
                    )}
                    Open
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={reportAction === `${history[0].id}-download`}
                    aria-busy={reportAction === `${history[0].id}-download`}
                    onClick={() => void handleDownloadReport(history[0])}
                  >
                    {reportAction === `${history[0].id}-download` ? (
                      <Spinner data-icon="inline-start" />
                    ) : (
                      <DownloadIcon data-icon="inline-start" />
                    )}
                    Download
                  </Button>
                </div>
              </div>
            ) : (
              <Empty className="border">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <FileTextIcon />
                  </EmptyMedia>
                  <EmptyTitle>No reports yet</EmptyTitle>
                  <EmptyDescription>
                    Run a report to see output details here.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Report History</CardTitle>
          <CardDescription>
            Last {history.length} report(s) stored in browser local storage.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {history.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Generated</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Output file</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell>
                      {new Date(entry.generated_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{entry.format.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{entry.devices_count}</TableCell>
                    <TableCell className="max-w-md truncate font-mono text-xs">
                      {entry.output_file}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={reportAction === `${entry.id}-open`}
                          aria-busy={reportAction === `${entry.id}-open`}
                          onClick={() => void handleOpenReport(entry)}
                        >
                          Open
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={reportAction === `${entry.id}-download`}
                          aria-busy={reportAction === `${entry.id}-download`}
                          onClick={() => void handleDownloadReport(entry)}
                        >
                          Download
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-sm">
              Report history will appear here after your first export.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
