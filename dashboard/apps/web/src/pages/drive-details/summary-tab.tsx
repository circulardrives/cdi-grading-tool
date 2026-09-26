/**
 * Summary tab: why this grade, every deduction, attribute grades, warning
 * flags, key numbers, and the grade across saved scans of this drive.
 */
import type { ReactNode } from "react"

import { Spinner } from "@workspace/ui/components/spinner"

import {
  driveNote,
  GRADE_INFO,
  GradeChip,
  gradeReason,
  Note,
  PageSection,
  Pill,
  StatTile,
  ungradedReasonText,
  warningFlagText,
  type Tone,
} from "@/components/ui-cdi"
import { formatPoweredOn, poweredOnSpan } from "@/lib/drive-names"
import {
  deductionsOf,
  formatHours,
  formatInt,
  healthySignals,
  keyNumbers,
  toNumber,
  type KeyNumber,
} from "@/pages/drives/drive-format"
import { useDriveHistory } from "@/pages/drives/use-drive-history"
import type { DriveRow } from "@/pages/drives/use-drive-rows"

import {
  formatWhen,
  humanizeCode,
  SEVERITY_WORDS,
  severityTone,
} from "./details-format"
import { ScrollTable, Secondary, Td, Th } from "./field-table"

/** Saved scans checked for the grade history table. */
const HISTORY_SCANS = 12

const REASON_TONE: Record<string, Tone> = {
  B: "info",
  C: "warn",
  D: "warn",
  F: "bad",
  UNGRADED: "info",
}

function sentence(text: string): string {
  return /[.!?]$/.test(text.trim()) ? text : `${text}.`
}

/** attribute_grades keys → plain labels. */
const ATTRIBUTE_LABELS: Record<string, string> = {
  available_spare: "Spare",
  available_reserved_space: "Spare (reserved space)",
  endurance: "Writes used",
  percentage_used: "Writes used",
  reallocated_sectors: "Reallocated sectors",
  pending_sectors: "Sectors waiting to be reallocated",
  uncorrectable_errors: "Uncorrectable errors",
  uncorrected_errors: "Uncorrected read/write errors",
  grown_defects: "Grown defects",
  self_test_history: "Self-test history",
  missing_defect_data: "Defect counters",
  power_on_hours: "Powered on",
}

function attributeLabel(key: string): string {
  return ATTRIBUTE_LABELS[key] ?? humanizeCode(key)
}

function valueText(key: string, value: unknown): string {
  const n = toNumber(value)
  if (n == null) {
    return value == null || value === "" ? "—" : String(value)
  }
  if (
    key === "available_spare" ||
    key === "available_reserved_space" ||
    key === "endurance" ||
    key === "percentage_used"
  ) {
    return `${formatInt(n)}%`
  }
  if (key === "power_on_hours") {
    return formatPoweredOn(n)
  }
  return formatInt(n)
}

// ---------------------------------------------------------------------------

function WhySection({ row }: { row: DriveRow }) {
  const { device, grade } = row
  const reason = gradeReason(device)
  const note = driveNote(device)
  const healthy = grade === "UNGRADED" ? [] : healthySignals(device)
  const letter = grade ? GRADE_INFO[grade].symbol : "—"
  const lead =
    grade === "F"
      ? "Other readings are fine"
      : reason
        ? "Everything else is healthy"
        : "Healthy"

  const facts: [string, ReactNode][] = []
  const score = toNumber(device.health_score)
  if (score != null) {
    facts.push(["Health score", `${formatInt(score)} / 100`])
  }
  if (device.recommended_use) {
    facts.push(["Recommended use", device.recommended_use])
  }
  if (device.certification_rationale) {
    facts.push(["Certification", device.certification_rationale])
  }
  if (device.drive_class) {
    facts.push([
      "Graded as",
      `${humanizeCode(device.drive_class)} drive${device.grading_profile ? ` · ${device.grading_profile} profile` : ""}`,
    ])
  }
  for (const code of device.ungraded_reasons ?? []) {
    facts.push([
      "Couldn't grade because",
      ungradedReasonText(code) ?? humanizeCode(code),
    ])
  }

  return (
    <PageSection title={`Why ${letter === "?" ? "no grade" : letter}`}>
      <div className="flex flex-col gap-2.5">
        {reason ? (
          <Note tone={REASON_TONE[grade ?? ""] ?? "info"}>
            {sentence(reason)}
          </Note>
        ) : null}
        {healthy.length > 0 ? (
          <Note tone="ok" neutralText>
            {lead}: {healthy.join(", ")}.
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
      {facts.length > 0 ? (
        <dl className="grid grid-cols-[minmax(0,12rem)_minmax(0,1fr)] gap-x-6 gap-y-2 text-base max-sm:grid-cols-1 max-sm:gap-y-0.5">
          {facts.map(([label, value]) => (
            <div key={`${label}-${String(value)}`} className="contents">
              <dt className="text-muted-foreground max-sm:mt-2">{label}</dt>
              <dd className="min-w-0 break-words">{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </PageSection>
  )
}

function DeductionsSection({ row }: { row: DriveRow }) {
  const deductions = deductionsOf(row.device)
  const points = toNumber(row.device.points_deducted)
  return (
    <PageSection
      title="Deductions"
      description={
        deductions.length === 0
          ? undefined
          : `${deductions.length} finding${deductions.length === 1 ? "" : "s"}${points ? ` · ${formatInt(points)} points off the score` : ""}`
      }
    >
      {deductions.length === 0 ? (
        <Note tone="ok" neutralText>
          No deductions — nothing took points off this drive's score.
        </Note>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {deductions.map((deduction, index) => {
            const severity = deduction.severity ?? "info"
            const details = [
              deduction.value != null && deduction.value !== ""
                ? `Reading ${String(deduction.value)}`
                : null,
              deduction.threshold != null && deduction.threshold !== ""
                ? `limit ${String(deduction.threshold)}`
                : null,
              deduction.points != null ? `−${deduction.points} points` : null,
            ].filter(Boolean)
            return (
              <li
                key={`${deduction.field ?? ""}-${index}`}
                className="flex flex-col gap-1.5 rounded-[10px] bg-muted px-4 py-3"
              >
                <span className="flex flex-wrap items-center gap-2">
                  <Pill tone={severityTone(severity)}>
                    {SEVERITY_WORDS[severity] ?? humanizeCode(severity)}
                  </Pill>
                  <span className="text-base font-semibold">
                    {deduction.reason ?? deduction.field ?? "Deduction"}
                  </span>
                </span>
                {details.length > 0 ? (
                  <span className="text-[15px] text-muted-foreground tabular-nums">
                    {details.join(" · ")}
                  </span>
                ) : null}
                {deduction.field ? (
                  <span className="font-mono text-sm text-muted-foreground">
                    {deduction.field}
                  </span>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}
    </PageSection>
  )
}

function AttributeGradesSection({ row }: { row: DriveRow }) {
  const entries = Object.entries(row.device.attribute_grades ?? {})
  if (entries.length === 0) {
    return null
  }
  return (
    <PageSection
      title="Attribute grades"
      description="Each reading CDI grades, and the band it falls in."
      flush
      className="overflow-hidden"
    >
      <ScrollTable label="Attribute grades">
        <thead>
          <tr>
            <Th className="pl-6">Attribute</Th>
            <Th align="right">Value</Th>
            <Th>Band</Th>
            <Th className="pr-6">Limit</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, info]) => {
            const extra = info as Record<string, unknown>
            const recent = toNumber(extra.recent_failures)
            const old = toNumber(extra.old_failures)
            return (
              <tr key={key} className="hover:bg-muted/60">
                <Td className="pl-6">
                  <div className="font-semibold">{attributeLabel(key)}</div>
                  <Secondary className="font-mono text-sm">{key}</Secondary>
                </Td>
                <Td align="right">
                  {valueText(key, info?.value)}
                  {recent != null || old != null ? (
                    <Secondary>
                      {formatInt(recent ?? 0)} recent · {formatInt(old ?? 0)}{" "}
                      older failures
                    </Secondary>
                  ) : null}
                </Td>
                <Td>
                  <GradeChip grade={info?.grade} size="sm" showWord="quality" />
                </Td>
                <Td className="pr-6">
                  {info?.threshold != null && info.threshold !== "" ? (
                    valueText(key, info.threshold)
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </Td>
              </tr>
            )
          })}
        </tbody>
      </ScrollTable>
    </PageSection>
  )
}

function FlagsSection({ row }: { row: DriveRow }) {
  const flags = row.device.warning_flags ?? []
  const codes = row.device.fail_reason_codes ?? []
  if (flags.length === 0 && codes.length === 0) {
    return null
  }
  return (
    <PageSection title="Warning flags">
      <ul className="flex flex-col gap-3">
        {flags.map((flag) => (
          <li key={flag} className="flex flex-col gap-0.5">
            <span className="text-base font-semibold">
              {warningFlagText(flag) ?? humanizeCode(flag)}
            </span>
            <span className="font-mono text-sm text-muted-foreground">
              {flag}
            </span>
          </li>
        ))}
        {codes.map((code) => (
          <li key={code} className="flex flex-col gap-0.5">
            <span className="text-base font-semibold">
              Fail code: {humanizeCode(code.replace(/^F-/, ""))}
            </span>
            <span className="font-mono text-sm text-muted-foreground">
              {code}
            </span>
          </li>
        ))}
      </ul>
    </PageSection>
  )
}

function KeyNumbersSection({ row }: { row: DriveRow }) {
  const { device } = row
  const numbers = keyNumbers(device)
  const cycles = toNumber(device.power_cycle_count)
  const written = toNumber(device.data_written_tb)
  const extra: KeyNumber[] = []
  if (cycles != null) {
    extra.push({ label: "Power cycles", value: formatInt(cycles) })
  }
  if (written != null) {
    extra.push({
      label: "Data written",
      value: `${Number(written.toFixed(2))} TB`,
    })
  }
  return (
    <PageSection title="Key numbers">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] gap-3">
        {[...numbers, ...extra].map((entry) => (
          <StatTile
            key={entry.label}
            label={entry.label}
            value={entry.value}
            hint={entry.hint}
          />
        ))}
      </div>
    </PageSection>
  )
}

function HistorySection({ row }: { row: DriveRow }) {
  const history = useDriveHistory(
    row.benchId,
    row.serial,
    row.device.dut,
    Boolean(row.serial),
    HISTORY_SCANS
  )

  let body: ReactNode
  if (!row.serial) {
    body = (
      <p className="px-6 pb-6 text-base text-muted-foreground max-sm:px-4">
        This drive doesn't report a serial, so its history can't be matched.
      </p>
    )
  } else if (history.isLoading) {
    body = (
      <p className="flex items-center gap-2 px-6 pb-6 text-base text-muted-foreground max-sm:px-4">
        <Spinner /> Checking saved scans…
      </p>
    )
  } else if (history.isError) {
    body = (
      <p className="px-6 pb-6 text-base text-muted-foreground max-sm:px-4">
        Couldn't load saved scans — try again in a moment.
      </p>
    )
  } else if (history.entries.length === 0) {
    body = (
      <p className="px-6 pb-6 text-base text-muted-foreground max-sm:px-4">
        No saved scans of this drive yet.
      </p>
    )
  } else {
    body = (
      <ScrollTable label="Grade history">
        <thead>
          <tr>
            <Th className="pl-6">When</Th>
            <Th>Grade</Th>
            <Th align="right">Score</Th>
            <Th align="right" className="pr-6">
              Powered on
            </Th>
          </tr>
        </thead>
        <tbody>
          {history.entries.map((entry) => (
            <tr key={entry.scanId} className="hover:bg-muted/60">
              <Td className="pl-6 whitespace-nowrap">
                {formatWhen(entry.scannedAt)}
              </Td>
              <Td>
                <GradeChip grade={entry.grade} size="sm" />
              </Td>
              <Td align="right">
                {entry.score == null ? "—" : formatInt(entry.score)}
              </Td>
              <Td align="right" className="pr-6 whitespace-nowrap">
                {formatHours(entry.hours)}
                {poweredOnSpan(entry.hours) ? (
                  <Secondary>{poweredOnSpan(entry.hours)}</Secondary>
                ) : null}
              </Td>
            </tr>
          ))}
        </tbody>
      </ScrollTable>
    )
  }

  return (
    <PageSection
      title="Grade history"
      description={
        row.serial && history.scansChecked > 0
          ? `This drive in the last ${history.scansChecked} saved scan${history.scansChecked === 1 ? "" : "s"} of ${row.benchName}.`
          : undefined
      }
      flush
      className="overflow-hidden"
    >
      {body}
    </PageSection>
  )
}

// ---------------------------------------------------------------------------

export function SummaryTab({ row }: { row: DriveRow }) {
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="flex min-w-0 flex-col gap-6">
        <WhySection row={row} />
        <DeductionsSection row={row} />
        <AttributeGradesSection row={row} />
      </div>
      <div className="flex min-w-0 flex-col gap-6">
        <KeyNumbersSection row={row} />
        <FlagsSection row={row} />
      </div>
      <div className="min-w-0 xl:col-span-2">
        <HistorySection row={row} />
      </div>
    </div>
  )
}
