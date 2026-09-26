/**
 * Drive detail panel: grade + why, key numbers, grade history, actions, and
 * "All data" (deductions and raw attributes) on demand.
 */
import { useId, useState, type ReactNode } from "react"
import { Link } from "react-router-dom"
import {
  ActivityIcon,
  ChevronDownIcon,
  FileTextIcon,
  XIcon,
} from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import {
  driveNote,
  GRADE_INFO,
  GradeChip,
  gradeReason,
  Note,
  Pill,
  SectionLabel,
  StatTile,
  type Tone,
} from "@/components/ui-cdi"
import { useSavedScanReport } from "@/hooks/use-cdi-queries"

import {
  deductionsOf,
  driveDetails,
  formatScanTime,
  healthySignals,
  isNvme,
  isToday,
  keyNumbers,
  rawAttributes,
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

function AllData({ row }: { row: DriveRow }) {
  const deductions = deductionsOf(row.device)
  const details = driveDetails(row.device)
  const raw = rawAttributes(row.device)
  const hasNormalized = raw.some((entry) => entry.extra)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <SectionLabel>Deductions</SectionLabel>
        {deductions.length === 0 ? (
          <span className="text-base text-muted-foreground">None.</span>
        ) : (
          <ul className="flex flex-col gap-2">
            {deductions.map((deduction, index) => (
              <li
                key={`${deduction.field ?? ""}-${index}`}
                className="flex flex-col gap-1 rounded-[10px] bg-muted px-3.5 py-2.5"
              >
                <span className="flex flex-wrap items-center gap-2">
                  <Pill
                    tone={
                      deduction.severity === "critical"
                        ? "bad"
                        : deduction.severity === "warning"
                          ? "warn"
                          : "info"
                    }
                  >
                    {deduction.severity === "critical"
                      ? "Critical"
                      : deduction.severity === "warning"
                        ? "Warning"
                        : (deduction.severity ?? "Note")}
                  </Pill>
                  <span className="text-base font-semibold">
                    {deduction.reason ?? deduction.field ?? "Deduction"}
                  </span>
                </span>
                <span className="font-mono text-[15px] text-muted-foreground">
                  {[
                    deduction.value != null
                      ? `value ${String(deduction.value)}`
                      : null,
                    deduction.threshold != null
                      ? `limit ${String(deduction.threshold)}`
                      : null,
                    deduction.points != null
                      ? `−${deduction.points} points`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {details.length > 0 ? (
        <div className="flex flex-col gap-2">
          <SectionLabel>Details</SectionLabel>
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-base">
            {details.map((entry) => (
              <div key={entry.name} className="contents">
                <dt className="text-muted-foreground">{entry.name}</dt>
                <dd className="min-w-0 break-words">{entry.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <SectionLabel>Raw attributes</SectionLabel>
        {raw.length === 0 ? (
          <span className="text-base text-muted-foreground">
            The drive didn't report any.
          </span>
        ) : (
          <div className="overflow-x-auto rounded-[10px] border">
            <table className="w-full font-mono text-[15px]">
              <thead>
                <tr className="border-b text-left text-[13px] tracking-[0.04em] text-muted-foreground uppercase">
                  <th scope="col" className="px-3 py-2 font-bold">
                    Attribute
                  </th>
                  {hasNormalized ? (
                    <th scope="col" className="px-3 py-2 text-right font-bold">
                      Now / worst / limit
                    </th>
                  ) : null}
                  <th scope="col" className="px-3 py-2 text-right font-bold">
                    Raw
                  </th>
                </tr>
              </thead>
              <tbody>
                {raw.map((entry, index) => (
                  <tr
                    key={`${entry.name}-${index}`}
                    className="border-b last:border-0"
                  >
                    <td className="px-3 py-1.5 break-all">{entry.name}</td>
                    {hasNormalized ? (
                      <td className="px-3 py-1.5 text-right whitespace-nowrap">
                        {entry.extra ?? ""}
                      </td>
                    ) : null}
                    <td className="px-3 py-1.5 text-right break-all">
                      {entry.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------

function ReportButton({ row }: { row: DriveRow }) {
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
  const [showAll, setShowAll] = useState(false)
  const allDataId = useId()
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
            />
          ))}
        </div>

        <HistoryLine row={row} />

        <div id={allDataId} hidden={!showAll}>
          {showAll ? <AllData row={row} /> : null}
        </div>
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
        <Button
          variant="quiet"
          aria-expanded={showAll}
          aria-controls={allDataId}
          onClick={() => setShowAll((value) => !value)}
        >
          All data
          <ChevronDownIcon
            data-icon="inline-end"
            className={cn("transition-transform", showAll && "rotate-180")}
          />
        </Button>
      </div>
    </div>
  )
}
