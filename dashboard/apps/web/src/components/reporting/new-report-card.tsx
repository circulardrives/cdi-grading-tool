/**
 * Reports › New report: what goes in (latest scan of every bench, picked
 * saved scans, or — only when this bench has drives — a fresh scan of this
 * bench), the format, and Create report. Respects the header bench scope.
 */
import { useMemo, useState, type ReactNode } from "react"
import {
  CheckCircle2Icon,
  DownloadIcon,
  ExternalLinkIcon,
  FileTextIcon,
  ScanLineIcon,
} from "lucide-react"
import { toast } from "sonner"

import { Button } from "@workspace/ui/components/button"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import {
  mockDataRequestFields,
  useMockDataSettings,
} from "@/components/mock-data-provider"
import { GradeCounts } from "@/components/reporting/report-bits"
import {
  usePdfAvailability,
  useReportFileActions,
} from "@/components/reporting/use-report-actions"
import {
  benchName,
  EmptyState,
  fleetHostName,
  Note,
  PageSection,
  SectionLabel,
  useBenchNames,
  useBenchScope,
} from "@/components/ui-cdi"
import {
  useFleetDevicesQuery,
  useGenerateReportMutation,
  useHealthQuery,
  useHistoryPagesQuery,
  useMachinesQuery,
  useScanAllBenches,
} from "@/hooks/use-cdi-queries"
import {
  describeReportError,
  formatDrives,
  formatExactTime,
  formatScanTime,
  isPdfUnavailableError,
  MAX_REPORT_SCANS,
  OLD_API_REPORT_MESSAGE,
  PDF_UNAVAILABLE_MESSAGE,
  REPORT_FORMAT_LABEL,
  REPORT_FORMAT_SHORT,
  REPORT_FORMATS,
  reportFileOf,
  reportIgnoredSource,
  reportReadyMessage,
} from "@/lib/report-utils"
import type {
  FleetHost,
  ReportFormat,
  ReportRequest,
  ReportResponse,
} from "@/lib/types"

type Source = "latest" | "picked" | "scan"

/** Bench names shown in one line before "+N more". */
const MAX_NAMED_BENCHES = 3

function SourceOption({
  value,
  checked,
  disabled = false,
  onSelect,
  title,
  description,
  children,
}: {
  value: Source
  checked: boolean
  disabled?: boolean
  onSelect: (value: Source) => void
  title: ReactNode
  description: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3">
      <label
        className={cn(
          "flex cursor-pointer gap-3.5 rounded-xl border border-border p-4 transition-colors",
          "hover:bg-muted/60 has-checked:border-primary has-checked:bg-row-selected has-checked:ring-1 has-checked:ring-primary",
          "has-disabled:cursor-not-allowed has-disabled:opacity-60 has-disabled:hover:bg-transparent"
        )}
      >
        <input
          type="radio"
          name="report-source"
          value={value}
          checked={checked}
          disabled={disabled}
          onChange={() => onSelect(value)}
          className="mt-0.5 size-5 shrink-0 accent-primary"
        />
        <span className="flex min-w-0 flex-col gap-1">
          <span className="text-[17px] leading-snug font-bold">{title}</span>
          <span className="text-[15px] text-muted-foreground">
            {description}
          </span>
        </span>
      </label>
      {checked ? children : null}
    </div>
  )
}

/** Checkbox list of saved scans (scoped to the header bench), newest first. */
function SavedScanPicker({
  scopeId,
  picked,
  onChange,
}: {
  scopeId: string | null
  picked: string[]
  onChange: (ids: string[]) => void
}) {
  const historyQuery = useHistoryPagesQuery(scopeId)
  const nameOf = useBenchNames()
  const entries = useMemo(
    () => historyQuery.data?.pages.flat() ?? [],
    [historyQuery.data]
  )
  const full = picked.length >= MAX_REPORT_SCANS

  if (historyQuery.isLoading) {
    return <Skeleton className="h-40 w-full" />
  }
  if (historyQuery.error) {
    return (
      <Note tone="bad">
        Couldn't load saved scans — {describeReportError(historyQuery.error)}.{" "}
        <button
          type="button"
          className="font-semibold text-link underline underline-offset-4"
          onClick={() => void historyQuery.refetch()}
        >
          Try again
        </button>
      </Note>
    )
  }
  if (entries.length === 0) {
    return (
      <p className="text-base text-muted-foreground">
        No saved scans yet — scan all benches first.
      </p>
    )
  }

  const toggle = (id: string) =>
    onChange(
      picked.includes(id)
        ? picked.filter((pickedId) => pickedId !== id)
        : [...picked, id]
    )

  return (
    <fieldset className="ml-2 flex flex-col gap-2 border-l-2 border-border pl-4 max-sm:ml-0 max-sm:border-l-0 max-sm:pl-0">
      <legend className="sr-only">Saved scans to include</legend>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-base font-semibold" aria-live="polite">
          {picked.length === 0
            ? "Pick one or more scans"
            : `${picked.length} picked`}
        </span>
        {full ? (
          <span className="text-[15px] text-muted-foreground">
            That's the most one report can hold ({MAX_REPORT_SCANS}).
          </span>
        ) : null}
        {picked.length > 0 ? (
          <Button
            variant="quiet"
            size="sm"
            className="h-11"
            onClick={() => onChange([])}
          >
            Clear picks
          </Button>
        ) : null}
      </div>
      <ul className="flex max-h-96 flex-col gap-1.5 overflow-y-auto pr-1">
        {entries.map((entry) => {
          const checked = picked.includes(entry.id)
          const disabled = !checked && full
          return (
            <li key={entry.id}>
              <label
                className={cn(
                  "flex min-h-14 cursor-pointer flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-border px-3 py-2",
                  "hover:bg-muted/60 has-checked:border-primary has-checked:bg-row-selected",
                  "has-disabled:cursor-not-allowed has-disabled:opacity-60"
                )}
              >
                <input
                  type="checkbox"
                  className="size-5 shrink-0 accent-primary"
                  checked={checked}
                  disabled={disabled}
                  onChange={() => toggle(entry.id)}
                />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-semibold">
                    {nameOf(entry.machine_id)}
                    <span className="font-normal text-muted-foreground">
                      {" "}
                      ·{" "}
                      <time
                        dateTime={entry.scanned_at}
                        title={formatExactTime(entry.scanned_at)}
                      >
                        {formatScanTime(entry.scanned_at)}
                      </time>
                    </span>
                  </span>
                  <span className="text-[15px] text-muted-foreground">
                    {formatDrives(entry.device_count)}
                    {entry.mock ? " · sample drives" : ""}
                  </span>
                </span>
                <GradeCounts grades={entry.grades} />
              </label>
            </li>
          )
        })}
      </ul>
      {historyQuery.hasNextPage ? (
        <div>
          <Button
            variant="outline"
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
    </fieldset>
  )
}

function FormatChoice({
  value,
  onChange,
  pdfAvailable,
}: {
  value: ReportFormat
  onChange: (format: ReportFormat) => void
  pdfAvailable: boolean
}) {
  return (
    <fieldset className="flex flex-col gap-2.5">
      <legend className="mb-2.5">
        <SectionLabel>Format</SectionLabel>
      </legend>
      <div className="flex flex-wrap gap-2">
        {REPORT_FORMATS.map((format) => (
          <label
            key={format}
            className={cn(
              "inline-flex h-11 cursor-pointer items-center rounded-[10px] border border-input bg-card px-[18px] text-base font-semibold transition-colors select-none",
              "hover:bg-muted has-checked:border-accent-foreground/30 has-checked:bg-accent has-checked:text-accent-foreground",
              "has-focus-visible:ring-3 has-focus-visible:ring-ring/40",
              "has-disabled:cursor-not-allowed has-disabled:opacity-50 has-disabled:hover:bg-card"
            )}
          >
            <input
              type="radio"
              name="report-format"
              value={format}
              checked={value === format}
              disabled={format === "pdf" && !pdfAvailable}
              onChange={() => onChange(format)}
              className="sr-only"
            />
            {REPORT_FORMAT_LABEL[format]}
          </label>
        ))}
      </div>
      {!pdfAvailable ? (
        <p className="text-[15px] text-muted-foreground">
          {PDF_UNAVAILABLE_MESSAGE}
        </p>
      ) : null}
    </fieldset>
  )
}

/** "pecan09 at 9:00 AM · pecan10 at 9:00 AM" (+N more). */
function benchesLine(hosts: FleetHost[], nameOf: (host: FleetHost) => string) {
  const parts = hosts
    .slice(0, MAX_NAMED_BENCHES)
    .map((host) => `${nameOf(host)} at ${formatScanTime(host.scanned_at)}`)
  if (hosts.length > MAX_NAMED_BENCHES) {
    parts.push(`${hosts.length - MAX_NAMED_BENCHES} more`)
  }
  return parts.join(" · ")
}

function ReportReady({ report }: { report: ReportResponse }) {
  const actions = useReportFileActions()
  const filename = reportFileOf(report)
  const nameOf = useBenchNames()
  const benches = (report.hosts ?? [])
    .map((host) => nameOf(host.machine_id, host.name))
    .join(", ")

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-primary/40 bg-row-selected px-4 py-3"
    >
      <span className="flex min-w-0 flex-1 items-start gap-2.5 text-base">
        <CheckCircle2Icon
          className="mt-0.5 size-5 shrink-0 text-primary"
          aria-hidden
        />
        <span>
          <span className="font-semibold">Report ready</span> ·{" "}
          {REPORT_FORMAT_SHORT[report.format]} ·{" "}
          {formatDrives(report.devices_count)}
          {benches ? ` · ${benches}` : ""}
        </span>
      </span>
      <span className="flex flex-wrap gap-2">
        {report.format !== "csv" ? (
          <Button
            variant="outline"
            disabled={actions.isBusy(filename, "open")}
            aria-busy={actions.isBusy(filename, "open")}
            onClick={() => void actions.open(filename)}
          >
            {actions.isBusy(filename, "open") ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <ExternalLinkIcon data-icon="inline-start" />
            )}
            Open
          </Button>
        ) : null}
        <Button
          variant="outline"
          disabled={actions.isBusy(filename, "download")}
          aria-busy={actions.isBusy(filename, "download")}
          onClick={() => void actions.download(filename)}
        >
          {actions.isBusy(filename, "download") ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <DownloadIcon data-icon="inline-start" />
          )}
          Download
        </Button>
      </span>
    </div>
  )
}

export function NewReportCard({ className }: { className?: string }) {
  const { scopeId, scopedBench } = useBenchScope()
  const fleetQuery = useFleetDevicesQuery()
  const historyQuery = useHistoryPagesQuery(scopeId)
  const machines = useMachinesQuery().data
  const thisBenchHostname = useHealthQuery().data?.hostname ?? null
  const nameOf = useBenchNames()
  const scanAll = useScanAllBenches()
  const generate = useGenerateReportMutation()
  const { pdfAvailable, markPdfUnavailable } = usePdfAvailability()
  const { useMockData, mockDataPath } = useMockDataSettings()

  const [chosenSource, setSource] = useState<Source>("latest")
  const [chosenFormat, setFormat] = useState<ReportFormat>("pdf")
  const [picked, setPicked] = useState<string[]>([])
  const [lastReport, setLastReport] = useState<ReportResponse | null>(null)

  // undefined while loading; null when the bench predates the combined view.
  const fleet = fleetQuery.data
  const hostName = (host: FleetHost) =>
    fleetHostName(host, machines, thisBenchHostname)
  const scopedHosts = (fleet?.hosts ?? []).filter(
    (host) => !scopeId || host.machine_id === scopeId
  )
  const scannedHosts = scopedHosts.filter(
    (host) => host.scanned_at && host.device_count > 0
  )
  const scannedDrives = scannedHosts.reduce(
    (total, host) => total + host.device_count,
    0
  )
  const neverScanned = scopedHosts.filter((host) => !host.scanned_at)
  const history = historyQuery.data?.pages[0] ?? []
  // One bench in scope: its newest saved scan stands in for "latest".
  const latestScoped = scopeId ? (history[0] ?? null) : null
  const thisBench = (fleet?.hosts ?? []).find((host) => !host.machine_id)
  const canScanThisBench = !scopeId && (thisBench?.device_count ?? 0) > 0

  const source: Source =
    chosenSource === "scan" && !canScanThisBench ? "latest" : chosenSource
  const format: ReportFormat =
    chosenFormat === "pdf" && !pdfAvailable ? "html" : chosenFormat

  const scopeName = scopeId
    ? scopedBench
      ? benchName(scopedBench)
      : nameOf(scopeId)
    : null
  const latestReady = scopeId
    ? latestScoped != null
    : fleet != null && scannedHosts.length > 0

  const loading = fleetQuery.isLoading || historyQuery.isLoading
  const loadError = historyQuery.error ?? fleetQuery.error
  const nothingSaved =
    !loading && !loadError && history.length === 0 && scannedHosts.length === 0

  let latestDescription: ReactNode
  if (scopeId) {
    latestDescription = latestScoped
      ? `${formatDrives(latestScoped.device_count)} · scanned at ${formatScanTime(latestScoped.scanned_at)}`
      : `${scopeName} hasn't been scanned yet`
  } else if (fleet === null) {
    latestDescription =
      "Needs a newer CDI Health on this bench — pick saved scans instead"
  } else if (scannedHosts.length === 0) {
    latestDescription = "No bench has been scanned yet"
  } else {
    latestDescription = `${formatDrives(scannedDrives)} · ${benchesLine(scannedHosts, hostName)}`
  }

  const request = (): ReportRequest | null => {
    if (source === "scan") {
      return {
        format,
        source: "scan",
        ...mockDataRequestFields(useMockData, mockDataPath),
      }
    }
    if (source === "picked") {
      return picked.length > 0
        ? { format, source: "history", history_ids: picked }
        : null
    }
    if (scopeId) {
      return latestScoped
        ? { format, source: "history", history_ids: [latestScoped.id] }
        : null
    }
    return latestReady ? { format, source: "fleet" } : null
  }
  const pendingRequest = request()
  const running = generate.isPending

  const create = async () => {
    if (!pendingRequest || running) {
      return
    }
    try {
      const result = await generate.mutateAsync(pendingRequest)
      setLastReport(result)
      const asked = pendingRequest.source ?? "scan"
      if (reportIgnoredSource(asked, result)) {
        toast.warning(OLD_API_REPORT_MESSAGE)
      } else {
        toast.success(
          reportReadyMessage(result, (host) =>
            nameOf(host.machine_id, host.name)
          )
        )
      }
    } catch (error) {
      if (pendingRequest.format === "pdf" && isPdfUnavailableError(error)) {
        // Switches the choice to Web page and shows the one-line reason.
        markPdfUnavailable()
        toast.warning(PDF_UNAVAILABLE_MESSAGE)
      } else {
        toast.error(describeReportError(error))
      }
    }
  }

  let body: ReactNode
  if (loading) {
    body = (
      <div className="flex flex-col gap-2.5" aria-busy="true">
        <Skeleton className="h-[86px] w-full rounded-xl" />
        <Skeleton className="h-[86px] w-full rounded-xl" />
        <span className="sr-only">Loading saved scans…</span>
      </div>
    )
  } else if (nothingSaved) {
    body = (
      <EmptyState
        icon={<FileTextIcon />}
        title="Nothing to report on yet"
        description={
          scopeName
            ? `${scopeName} has no saved scans. Scan the benches — every scan is saved and can go into a report.`
            : "Scan the benches — every scan is saved and can go into a report."
        }
        actions={
          <Button
            disabled={scanAll.pending}
            aria-busy={scanAll.pending}
            onClick={scanAll.start}
          >
            {scanAll.pending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <ScanLineIcon data-icon="inline-start" />
            )}
            {scanAll.pending ? "Scanning…" : "Scan all benches"}
          </Button>
        }
      />
    )
  } else {
    body = (
      <>
        {loadError ? (
          <Note tone="bad">
            Couldn't load saved scans — {describeReportError(loadError)}.{" "}
            <button
              type="button"
              className="font-semibold text-link underline underline-offset-4"
              onClick={() => {
                void fleetQuery.refetch()
                void historyQuery.refetch()
              }}
            >
              Try again
            </button>
          </Note>
        ) : null}
        <fieldset className="flex flex-col gap-2.5">
          <legend className="mb-2.5">
            <SectionLabel>What's in it</SectionLabel>
          </legend>
          <SourceOption
            value="latest"
            checked={source === "latest"}
            disabled={!latestReady}
            onSelect={setSource}
            title={
              scopeName
                ? `Latest scan of ${scopeName}`
                : "Latest scan of every bench"
            }
            description={latestDescription}
          >
            {!scopeId && neverScanned.length > 0 && latestReady ? (
              <p className="px-1 text-[15px] text-muted-foreground">
                Not included — never scanned:{" "}
                {neverScanned.map(hostName).join(", ")}
              </p>
            ) : null}
          </SourceOption>
          <SourceOption
            value="picked"
            checked={source === "picked"}
            onSelect={setSource}
            title="Pick saved scans"
            description="Choose from scan history — for a report on an earlier batch"
          >
            <SavedScanPicker
              scopeId={scopeId}
              picked={picked}
              onChange={setPicked}
            />
          </SourceOption>
          {canScanThisBench ? (
            <label className="flex min-h-11 w-fit cursor-pointer items-center gap-2.5 rounded-lg px-1 text-base text-link hover:text-link-hover has-checked:font-semibold">
              <input
                type="radio"
                name="report-source"
                value="scan"
                checked={source === "scan"}
                onChange={() => setSource("scan")}
                className="size-5 shrink-0 accent-primary"
              />
              <span>
                Or scan this bench now
                <span className="text-muted-foreground">
                  {" "}
                  — only the drives plugged into{" "}
                  {thisBench ? hostName(thisBench) : "this bench"}
                </span>
              </span>
            </label>
          ) : null}
        </fieldset>

        <FormatChoice
          value={format}
          onChange={setFormat}
          pdfAvailable={pdfAvailable}
        />

        <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2">
          <Button
            disabled={!pendingRequest || running}
            aria-busy={running}
            onClick={() => void create()}
          >
            {running ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <FileTextIcon data-icon="inline-start" />
            )}
            {running
              ? source === "scan"
                ? "Scanning and creating…"
                : "Creating report…"
              : "Create report"}
          </Button>
          <span className="text-[15px] text-muted-foreground">
            {source === "picked" && picked.length === 0
              ? "Pick at least one saved scan."
              : "Grades are shown exactly as they were at scan time."}
          </span>
        </div>

        {lastReport ? <ReportReady report={lastReport} /> : null}
      </>
    )
  }

  return (
    <PageSection
      id="new-report"
      title="New report"
      className={className}
      bodyClassName="gap-5"
    >
      {body}
    </PageSection>
  )
}
