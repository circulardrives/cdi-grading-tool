/**
 * Drive detail panel: grade + why, key numbers, grade history, actions, and
 * a "Full details" link to the full-screen drive page (every log, raw data).
 */
import { type ReactNode } from "react"
import { Link, useLocation } from "react-router-dom"
import { ActivityIcon, ArrowRightIcon, FileTextIcon, XIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import {
  driveNote,
  GRADE_INFO,
  GradeChip,
  gradeReason,
  Note,
  SectionLabel,
  StatTile,
  type Tone,
} from "@/components/ui-cdi"
import { useSavedScanReport } from "@/hooks/use-cdi-queries"
import {
  driveDetailsHref,
  type DriveDetailsState,
} from "@/pages/drive-details/drive-details-href"

import {
  formatScanTime,
  healthySignals,
  isNvme,
  isToday,
  keyNumbers,
} from "./drive-format"
import { useDriveHistory, type DriveHistoryEntry } from "./use-drive-history"
import type { DriveRow } from "./use-drive-rows"

// ---------------------------------------------------------------------------

const REASON_TONE: Record<string, Tone> = {
  B: "info",
  C: "warn",
  D: "warn",
  F: "bad",
  UNGRADED: "info",
}

/** Adds a full stop unless the text already ends a sentence. */
function sentence(text: string): string {
  return /[.!?]$/.test(text.trim()) ? text : `${text}.`
}

function healthyLead(grade: DriveRow["grade"], hasReason: boolean): string {
  if (grade === "F") {
    return "Other readings are fine"
  }
  return hasReason ? "Everything else is healthy" : "Healthy"
}

// ---------------------------------------------------------------------------

function HistoryLine({ row }: { row: DriveRow }) {
  const history = useDriveHistory(
    row.benchId,
    row.serial,
    row.device.dut,
    Boolean(row.serial)
  )

  let body: ReactNode
  if (!row.serial) {
    body = (
      <span className="text-muted-foreground">
        This drive doesn't report a serial, so its history can't be matched.
      </span>
    )
  } else if (history.isLoading) {
    body = (
      <span className="flex items-center gap-2 text-muted-foreground">
        <Spinner /> Checking saved scans…
      </span>
    )
  } else if (history.isError) {
    body = (
      <span className="text-muted-foreground">
        Couldn't load saved scans — try again in a moment.
      </span>
    )
  } else if (history.entries.length === 0) {
    body = (
      <span className="text-muted-foreground">
        No saved scans of this drive yet.
      </span>
    )
  } else {
    body = <HistorySummary entries={history.entries} />
  }

  return (
    <div className="flex flex-col gap-2">
      <SectionLabel>History</SectionLabel>
      <div className="text-base">{body}</div>
    </div>
  )
}

function HistorySummary({ entries }: { entries: DriveHistoryEntry[] }) {
  const grades = new Set(entries.map((entry) => entry.grade ?? "—"))
  const first = entries[0]
  if (grades.size === 1 && first) {
    const allToday = entries.every((entry) =>
      isToday(new Date(entry.scannedAt))
    )
    const label = GRADE_INFO[first.grade ?? "UNGRADED"]
    const gradeText =
      first.grade === "UNGRADED" || first.grade == null
        ? "couldn't grade"
        : `grade ${label.symbol}`
    if (entries.length === 1) {
      return (
        <span>
          One saved scan ({formatScanTime(first.scannedAt)}): {gradeText}
        </span>
      )
    }
    return (
      <span>
        {allToday
          ? `Every scan today: ${gradeText}`
          : `Last ${entries.length} scans: ${gradeText} every time`}
      </span>
    )
  }
  return (
    <ul className="flex flex-col gap-1.5">
      {entries.map((entry) => (
        <li key={entry.scanId} className="flex items-center gap-3">
          <span className="w-32 shrink-0 text-muted-foreground tabular-nums">
            {formatScanTime(entry.scannedAt)}
          </span>
          <GradeChip grade={entry.grade} size="sm" />
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------

/** "Scan report" for the newest saved scan of the drive's bench. */
export function ReportButton({ row }: { row: DriveRow }) {
  const history = useDriveHistory(row.benchId, row.serial, row.device.dut, true)
  const report = useSavedScanReport()
  const scanId = history.latestScanId
  if (!scanId) {
    return null
  }
  const busy = report.isBusy(scanId)
  return (
    <Button
      variant="outline"
      disabled={report.anyBusy}
      onClick={() => void report.makeReport(scanId, "html")}
    >
      {busy ? (
        <Spinner data-icon="inline-start" />
      ) : (
        <FileTextIcon data-icon="inline-start" />
      )}
      {busy ? "Making report…" : "Scan report"}
    </Button>
  )
}

export type DrivePanelProps = {
  row: DriveRow
  onClose: () => void
  /** Id of the element that labels the panel (for the dialog/aside). */
  titleId: string
  className?: string
}

export function DrivePanel({
  row,
  onClose,
  titleId,
  className,
}: DrivePanelProps) {
  const location = useLocation()
  const { device, grade } = row

  const reason = gradeReason(device)
  const note = driveNote(device)
  const healthy = grade === "UNGRADED" ? [] : healthySignals(device)
  const numbers = keyNumbers(device)
  const letter = grade ? GRADE_INFO[grade].symbol : "—"
  const scanned = formatScanTime(row.scannedAt)
  const selfTestHref = `/self-tests?${new URLSearchParams({
    ...(row.benchId ? { bench: row.benchId } : {}),
    ...(row.serial ? { serial: row.serial } : {}),
  }).toString()}`
  // "← Drives" on the details page comes back to this list, filters and all.
  const detailsState: DriveDetailsState = {
    fromDrives: `${location.pathname}${location.search}`,
  }

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="flex flex-col gap-3 border-b px-6 py-5 max-sm:px-4">
        <div className="flex items-center gap-2.5">
          <GradeChip grade={grade} size="lg" showWord="both" />
          <div className="flex-1" />
          <Button
            variant="quiet"
            size="icon"
            aria-label="Close drive details"
            onClick={onClose}
          >
            <XIcon className="size-5" />
          </Button>
        </div>
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2
            id={titleId}
            className="text-[22px] leading-tight font-bold break-words"
          >
            {row.name}
            {row.capacity ? ` · ${row.capacity}` : ""}
          </h2>
          <span className="font-mono text-[15px] break-all text-muted-foreground">
            {[
              row.serial || "No serial reported",
              row.model && row.model !== row.name ? row.model : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
          <span className="text-[15px] text-muted-foreground">
            {[row.benchName, device.dut, scanned ? `scanned ${scanned}` : null]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-6 py-5 max-sm:px-4">
        <div className="flex flex-col gap-2.5">
          <SectionLabel>
            Why {letter === "?" ? "no grade" : letter}
          </SectionLabel>
          {reason ? (
            <Note tone={REASON_TONE[grade ?? ""] ?? "info"}>
              {sentence(reason)}
            </Note>
          ) : null}
          {healthy.length > 0 ? (
            <Note tone="ok" neutralText>
              {healthyLead(grade, Boolean(reason))}: {healthy.join(", ")}.
            </Note>
          ) : null}
          {!reason && healthy.length === 0 ? (
            <Note tone="info">
              {grade ? GRADE_INFO[grade].description : "Not graded yet."}
            </Note>
          ) : null}
          {note && note !== reason ? (
            <Note tone="info">{sentence(note)}</Note>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-3">
          {numbers.map((entry) => (
            <StatTile
              key={entry.label}
              label={entry.label}
              value={entry.value}
              hint={entry.hint}
            />
          ))}
        </div>

        <HistoryLine row={row} />
      </div>

      <div className="flex flex-wrap gap-2.5 border-t px-6 py-4 max-sm:px-4">
        {isNvme(device) ? (
          <Button variant="outline" asChild>
            <Link to={selfTestHref}>
              <ActivityIcon data-icon="inline-start" />
              Run self-test
            </Link>
          </Button>
        ) : null}
        <ReportButton row={row} />
        <Button variant="quiet" asChild>
          <Link to={driveDetailsHref(row)} state={detailsState}>
            Full details
            <ArrowRightIcon data-icon="inline-end" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
