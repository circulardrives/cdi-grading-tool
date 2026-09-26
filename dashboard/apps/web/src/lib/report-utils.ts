import {
  downloadReportFile,
  isValidationError,
  openReportFile,
  reportFilename,
} from "@/lib/api"
import type {
  ReportFormat,
  ReportHistoryEntry,
  ReportHost,
  ReportListEntry,
  ReportResponse,
  ReportSource,
} from "@/lib/types"

const LOCAL_REPORTS_KEY = "cdi-report-history"
const MAX_LOCAL_REPORTS = 20

/** Prefer crypto.randomUUID; fall back on HTTP LAN where it is unavailable. */
function newReportId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

/** Browser-only report list (fallback for APIs without GET /reports). */
export function loadLocalReports(): ReportHistoryEntry[] {
  try {
    const raw = localStorage.getItem(LOCAL_REPORTS_KEY)
    if (!raw) {
      return []
    }
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as ReportHistoryEntry[]) : []
  } catch {
    return []
  }
}

/** Remembers a report in this browser; returns the updated list. */
export function saveLocalReport(result: ReportResponse): ReportHistoryEntry[] {
  const entry: ReportHistoryEntry = {
    ...result,
    filename: reportFileOf(result),
    id: newReportId(),
  }
  const next = [entry, ...loadLocalReports()].slice(0, MAX_LOCAL_REPORTS)
  try {
    localStorage.setItem(LOCAL_REPORTS_KEY, JSON.stringify(next))
  } catch {
    /* quota exceeded or storage blocked */
  }
  return next
}

export function reportFileOf(
  report: Pick<ReportResponse, "filename"> & { output_file?: string }
): string {
  return report.filename || reportFilename(report.output_file ?? "")
}

/** Browser-stored entries shaped like rows of GET /reports. */
export function localReportsAsList(
  entries: ReportHistoryEntry[]
): ReportListEntry[] {
  return entries.map((entry) => ({
    filename: reportFileOf(entry),
    format: entry.format,
    generated_at: entry.generated_at,
    source: entry.source ?? null,
    devices_count: entry.devices_count,
    hosts: entry.hosts ?? null,
  }))
}

/** Bench name for a report host; pass useBenchNames() so this bench isn't "Local API". */
export type ReportHostName = (host: ReportHost) => string

/** "pecan09, pecan10" (or "pecan09, pecan10 +3 more"); "—" when unknown. */
export function formatReportBenches(
  hosts: ReportHost[] | null | undefined,
  max = 3,
  nameOf: ReportHostName = (host) => host.name
): string {
  const names = (hosts ?? []).map(nameOf).filter(Boolean)
  if (names.length === 0) {
    return "—"
  }
  if (names.length <= max) {
    return names.join(", ")
  }
  return `${names.slice(0, max).join(", ")} +${names.length - max} more`
}

export function reportSourceLabel(
  source: ReportSource | null | undefined
): string {
  switch (source) {
    case "fleet":
      return "Latest scans"
    case "history":
      return "Saved scan"
    case "scan":
      return "Scanned now"
    default:
      return ""
  }
}

export function formatDrives(count: number): string {
  return `${count} drive${count === 1 ? "" : "s"}`
}

/** Toast line after a report is made. */
export function reportReadyMessage(
  result: ReportResponse,
  nameOf?: ReportHostName
): string {
  const benches = formatReportBenches(result.hosts, 3, nameOf)
  const where = benches === "—" ? "" : ` from ${benches}`
  return `Report ready — ${formatDrives(result.devices_count)}${where}`
}

/**
 * True when we asked for saved scans but the API answered like an older
 * version that ignores `source` (it scanned its own drives instead).
 */
export function reportIgnoredSource(
  requested: ReportSource,
  result: ReportResponse
): boolean {
  return requested !== "scan" && result.source == null
}

export const OLD_API_REPORT_MESSAGE =
  "CDI Health on this computer is too old to report on saved scans, so it scanned only this computer's drives. Update CDI Health to report on all benches."

/** Opens HTML/PDF reports in a new tab and downloads CSV. */
export async function deliverReport(
  filename: string,
  format: ReportFormat
): Promise<void> {
  if (format === "csv") {
    await downloadReportFile(filename)
  } else {
    await openReportFile(filename)
  }
}

export const PDF_UNAVAILABLE_MESSAGE =
  "PDF isn't available on this bench — use Web page or Spreadsheet"

/** True when the API said it can't make PDFs (PDF library not installed). */
export function isPdfUnavailableError(error: unknown): boolean {
  return (
    error instanceof Error &&
    /weasyprint|pdf generation requires/i.test(error.message)
  )
}

/** Saved scans one report can combine (API limit). */
export const MAX_REPORT_SCANS = 50

/** Plain one-line message for a failed report request. */
export function describeReportError(error: unknown): string {
  if (isPdfUnavailableError(error)) {
    return PDF_UNAVAILABLE_MESSAGE
  }
  if (isValidationError(error)) {
    return "CDI Health on this computer is too old for this kind of report — update it, or use Scan this bench now"
  }
  if (error instanceof Error && error.message) {
    if (/no saved scans to report on/i.test(error.message)) {
      return "Nothing saved to report on yet — scan all benches first"
    }
    if (/scan history entry not found/i.test(error.message)) {
      return "One of those saved scans was deleted — pick again"
    }
    if (/at most \d+ history_ids/i.test(error.message)) {
      return `Pick at most ${MAX_REPORT_SCANS} saved scans for one report`
    }
    return error.message.split("\n")[0] ?? error.message
  }
  return "Couldn't make the report"
}

/** Words for each format (the New report choice, table cells). */
export const REPORT_FORMAT_LABEL: Record<ReportFormat, string> = {
  pdf: "PDF",
  html: "Web page",
  csv: "Spreadsheet (CSV)",
}

/** Shorter words for dense rows and menus. */
export const REPORT_FORMAT_SHORT: Record<ReportFormat, string> = {
  pdf: "PDF",
  html: "Web page",
  csv: "Spreadsheet",
}

export const REPORT_FORMATS: ReportFormat[] = ["pdf", "html", "csv"]

function parseTime(iso: string | null | undefined): Date | null {
  if (!iso) {
    return null
  }
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? null : date
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function clock(date: Date): string {
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
}

/** "9:00 AM" today, "Sep 24, 9:00 AM" otherwise (year added when not this year). */
export function formatScanTime(
  iso: string | null | undefined,
  now = new Date()
): string {
  const date = parseTime(iso)
  if (!date) {
    return "—"
  }
  if (sameDay(date, now)) {
    return clock(date)
  }
  const day = date.toLocaleDateString([], {
    month: "short",
    day: "numeric",
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: "numeric" }),
  })
  return `${day}, ${clock(date)}`
}

/** Full local date and time, for hover text. */
export function formatExactTime(iso: string | null | undefined): string {
  const date = parseTime(iso)
  if (!date) {
    return ""
  }
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
}

/** "just now", "12 min ago", "3 h ago", "yesterday, 4:10 PM", else the date. */
export function formatRelativeTime(
  iso: string | null | undefined,
  now = new Date()
): string {
  const date = parseTime(iso)
  if (!date) {
    return "—"
  }
  const minutes = Math.round((now.getTime() - date.getTime()) / 60_000)
  if (minutes < 1) {
    return "just now"
  }
  if (minutes < 60) {
    return `${minutes} min ago`
  }
  if (sameDay(date, now)) {
    return `${Math.round(minutes / 60)} h ago`
  }
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (sameDay(date, yesterday)) {
    return `yesterday, ${clock(date)}`
  }
  return formatScanTime(iso, now)
}
