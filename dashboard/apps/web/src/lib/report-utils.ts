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

/** "pecan09, pecan10" (or "pecan09, pecan10 +3 more"); "—" when unknown. */
export function formatReportBenches(
  hosts: ReportHost[] | null | undefined,
  max = 3
): string {
  const names = (hosts ?? []).map((host) => host.name).filter(Boolean)
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
export function reportReadyMessage(result: ReportResponse): string {
  const benches = formatReportBenches(result.hosts)
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

/** Plain one-line message for a failed report request. */
export function describeReportError(error: unknown): string {
  if (isValidationError(error)) {
    return "CDI Health on this computer is too old for this kind of report — update it, or use Scan this bench now"
  }
  if (error instanceof Error && error.message) {
    return error.message.split("\n")[0] ?? error.message
  }
  return "Couldn't make the report"
}
