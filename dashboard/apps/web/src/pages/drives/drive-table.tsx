/**
 * The one drive list: grade, serial, drive, bench · slot, and three numbers.
 * Clicking a row (or its serial button, for keyboards) opens the panel.
 *
 * - `compact` (side panel open): Bench moves under the drive name on one
 *   line and Writes used / Spare drop out (the panel shows them), so the
 *   table fits next to the panel without clipping.
 * - `DriveStackedList` (phones, < 640px): one tappable card-row per drive
 *   instead of the table.
 */
import { memo } from "react"
import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon } from "lucide-react"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { cn } from "@workspace/ui/lib/utils"

import { GradeChip } from "@/components/ui-cdi"

import {
  formatHours,
  formatPercent,
  formatPoweredOn,
  poweredOnSpan,
} from "./drive-format"
import type { DriveRow } from "./use-drive-rows"

export type SortKey = "grade" | "hours" | "writes"
export type SortState = { key: SortKey; dir: "asc" | "desc" } | null

const SORT_LABELS: Record<SortKey, string> = {
  grade: "Grade",
  hours: "Powered on",
  writes: "Writes used",
}

function SortIcon({ sort, sortKey }: { sort: SortState; sortKey: SortKey }) {
  const className = "size-4 shrink-0"
  if (sort?.key !== sortKey) {
    return <ArrowUpDownIcon aria-hidden="true" className={className} />
  }
  return sort.dir === "asc" ? (
    <ArrowUpIcon aria-hidden="true" className={className} />
  ) : (
    <ArrowDownIcon aria-hidden="true" className={className} />
  )
}

type SortHeaderProps = {
  label: string
  sortKey: SortKey
  sort: SortState
  onSort: (key: SortKey) => void
  align?: "left" | "right"
}

function SortHeader({
  label,
  sortKey,
  sort,
  onSort,
  align = "left",
}: SortHeaderProps) {
  const active = sort?.key === sortKey
  return (
    <TableHead
      aria-sort={
        active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"
      }
      className={cn("p-0", align === "right" && "text-right")}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={cn(
          "inline-flex h-11 w-full items-center gap-1.5 px-4 font-bold tracking-[0.04em] uppercase outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/40",
          align === "right" && "justify-end",
          active && "text-foreground"
        )}
      >
        {label}
        <SortIcon sort={sort} sortKey={sortKey} />
      </button>
    </TableHead>
  )
}

/**
 * Serial with line-break chances after "_" and "-", so long ones
 * ("SN_IS_0x0100_SANITIZED") wrap instead of widening the table.
 */
function SerialText({ serial }: { serial: string }) {
  const parts = serial.split(/(?<=[_-])/)
  return (
    <>
      {parts.map((part, index) => (
        <span key={index}>
          {part}
          {index < parts.length - 1 ? <wbr /> : null}
        </span>
      ))}
    </>
  )
}

/** "40,858 h" over a muted "4 yrs 242 days" (formatPoweredOn in two lines). */
function PoweredOn({ hours }: { hours: number | null }) {
  const span = poweredOnSpan(hours)
  return (
    <>
      <div>{formatHours(hours)}</div>
      {span ? (
        <div className="text-sm whitespace-nowrap text-muted-foreground">
          {span}
        </div>
      ) : null}
    </>
  )
}

type RowProps = {
  row: DriveRow
  selected: boolean
  onSelect: (row: DriveRow) => void
  compact: boolean
}

const DriveTableRow = memo(function DriveTableRow({
  row,
  selected,
  onSelect,
  compact,
}: RowProps) {
  const benchSlot = (
    <>
      {row.benchName}
      {row.slot ? (
        <span className="text-muted-foreground"> · {row.slot}</span>
      ) : null}
    </>
  )
  return (
    <TableRow
      data-row-key={row.key}
      data-state={selected ? "selected" : undefined}
      className="cursor-pointer"
      onClick={() => onSelect(row)}
    >
      <TableCell>
        <GradeChip grade={row.grade} />
      </TableCell>
      <TableCell className="py-0 whitespace-normal">
        <button
          type="button"
          aria-current={selected ? "true" : undefined}
          onClick={(event) => {
            event.stopPropagation()
            onSelect(row)
          }}
          className="-mx-2 inline-flex min-h-11 items-center rounded-md px-2 text-left font-mono text-[15px] text-link underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/40"
        >
          {row.serial ? (
            <span className="min-w-0">
              <SerialText serial={row.serial} />
            </span>
          ) : (
            <span className="font-sans text-muted-foreground">No serial</span>
          )}
          <span className="sr-only"> — show details for {row.name}</span>
        </button>
      </TableCell>
      <TableCell className="min-w-40 whitespace-normal">
        <span className="font-semibold">{row.name}</span>
        {row.capacity ? (
          <span className="text-muted-foreground"> {row.capacity}</span>
        ) : null}
        {compact ? (
          // Bench · slot on one line under the name (truncated, full on hover).
          <div
            className="max-w-64 truncate text-[15px]"
            title={`${row.benchName}${row.slot ? ` · ${row.slot}` : ""}`}
          >
            {benchSlot}
          </div>
        ) : null}
      </TableCell>
      {compact ? null : (
        <TableCell className="min-w-28 whitespace-normal">
          {benchSlot}
        </TableCell>
      )}
      <TableCell className="text-right tabular-nums">
        <PoweredOn hours={row.hours} />
      </TableCell>
      {compact ? null : (
        <>
          <TableCell className="text-right tabular-nums">
            {formatPercent(row.writes)}
          </TableCell>
          <TableCell className="text-right tabular-nums">
            {formatPercent(row.spare)}
          </TableCell>
        </>
      )}
    </TableRow>
  )
})

export type DriveTableProps = {
  rows: DriveRow[]
  selectedKey: string | null
  onSelect: (row: DriveRow) => void
  sort: SortState
  onSort: (key: SortKey) => void
  /** Side panel open: bench under the name; no Writes used / Spare columns. */
  compact?: boolean
}

export function DriveTable({
  rows,
  selectedKey,
  onSelect,
  sort,
  onSort,
  compact = false,
}: DriveTableProps) {
  return (
    <Table>
      <caption className="sr-only">
        Drives from the latest scans. Choose a serial to see details.
      </caption>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <SortHeader
            label="Grade"
            sortKey="grade"
            sort={sort}
            onSort={onSort}
          />
          <TableHead>Serial</TableHead>
          <TableHead>{compact ? "Drive · bench" : "Drive"}</TableHead>
          {compact ? null : <TableHead>Bench</TableHead>}
          <SortHeader
            label="Powered on"
            sortKey="hours"
            sort={sort}
            onSort={onSort}
            align="right"
          />
          {compact ? null : (
            <>
              <SortHeader
                label="Writes used"
                sortKey="writes"
                sort={sort}
                onSort={onSort}
                align="right"
              />
              <TableHead className="text-right">Spare</TableHead>
            </>
          )}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <DriveTableRow
            key={row.key}
            row={row}
            selected={row.key === selectedKey}
            onSelect={onSelect}
            compact={compact}
          />
        ))}
      </TableBody>
    </Table>
  )
}

// ---------------------------------------------------------------------------
// Phones: stacked card-rows
// ---------------------------------------------------------------------------

const DriveStackedRow = memo(function DriveStackedRow({
  row,
  selected,
  onSelect,
}: Omit<RowProps, "compact">) {
  const numbers = [
    `Powered on ${formatPoweredOn(row.hours)}`,
    row.writes != null ? `Writes used ${formatPercent(row.writes)}` : null,
    row.spare != null ? `Spare ${formatPercent(row.spare)}` : null,
  ].filter(Boolean)
  return (
    <li data-row-key={row.key} className="border-b last:border-b-0">
      <button
        type="button"
        aria-current={selected ? "true" : undefined}
        onClick={() => onSelect(row)}
        className={cn(
          "flex min-h-11 w-full flex-col gap-1 px-4 py-3 text-left outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:ring-inset",
          selected && "bg-row-selected"
        )}
      >
        <span className="flex min-w-0 items-center gap-2.5">
          <GradeChip grade={row.grade} />
          <span className="min-w-0 font-semibold break-words">
            {row.name}
            {row.capacity ? (
              <span className="font-normal text-muted-foreground">
                {" "}
                · {row.capacity}
              </span>
            ) : null}
          </span>
        </span>
        <span className="flex min-w-0 flex-wrap gap-x-2 text-[15px] text-muted-foreground">
          <span className="font-mono break-all text-link">
            {row.serial || "No serial"}
          </span>
          <span aria-hidden="true">·</span>
          <span>
            {row.benchName}
            {row.slot ? ` · ${row.slot}` : ""}
          </span>
        </span>
        <span className="text-[15px] tabular-nums">{numbers.join(" · ")}</span>
      </button>
    </li>
  )
})

export function DriveStackedList({
  rows,
  selectedKey,
  onSelect,
  sort,
  onSort,
}: Omit<DriveTableProps, "compact">) {
  return (
    <div>
      <div
        role="group"
        aria-label="Sort drives"
        className="flex flex-wrap items-center gap-1 border-b px-2 py-1.5"
      >
        <span className="px-2 text-[13px] font-bold tracking-[0.04em] text-muted-foreground uppercase">
          Sort
        </span>
        {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => {
          const active = sort?.key === key
          return (
            <button
              key={key}
              type="button"
              aria-pressed={active}
              onClick={() => onSort(key)}
              className={cn(
                "inline-flex h-11 items-center gap-1.5 rounded-md px-2.5 text-[15px] font-semibold text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/40",
                active && "text-foreground"
              )}
            >
              {SORT_LABELS[key]}
              <SortIcon sort={sort} sortKey={key} />
              {active ? (
                <span className="sr-only">
                  {sort.dir === "asc" ? "ascending" : "descending"}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
      <ul aria-label="Drives from the latest scans">
        {rows.map((row) => (
          <DriveStackedRow
            key={row.key}
            row={row}
            selected={row.key === selectedKey}
            onSelect={onSelect}
          />
        ))}
      </ul>
    </div>
  )
}
