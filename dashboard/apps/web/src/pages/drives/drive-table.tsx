/**
 * The one drive list: grade, serial, drive, bench · slot, and three numbers.
 * Clicking a row (or its serial button, for keyboards) opens the panel.
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

import { formatHours, formatPercent } from "./drive-format"
import type { DriveRow } from "./use-drive-rows"

export type SortKey = "grade" | "hours" | "writes"
export type SortState = { key: SortKey; dir: "asc" | "desc" } | null

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
  const Icon = !active
    ? ArrowUpDownIcon
    : sort.dir === "asc"
      ? ArrowUpIcon
      : ArrowDownIcon
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
        <Icon aria-hidden="true" className="size-4 shrink-0" />
      </button>
    </TableHead>
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
      <TableCell className="py-0">
        <button
          type="button"
          aria-current={selected ? "true" : undefined}
          onClick={(event) => {
            event.stopPropagation()
            onSelect(row)
          }}
          className="-mx-2 inline-flex min-h-11 items-center rounded-md px-2 font-mono text-[15px] text-link underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/40"
        >
          {row.serial || (
            <span className="font-sans text-muted-foreground">No serial</span>
          )}
          <span className="sr-only"> — show details for {row.name}</span>
        </button>
      </TableCell>
      <TableCell className="min-w-44 whitespace-normal">
        <span className="font-semibold">{row.name}</span>
        {row.capacity ? (
          <span className="text-muted-foreground"> {row.capacity}</span>
        ) : null}
      </TableCell>
      <TableCell className="min-w-32 whitespace-normal">
        {row.benchName}
        {row.slot ? (
          <span className="text-muted-foreground"> · {row.slot}</span>
        ) : null}
      </TableCell>
      <TableCell className="text-right tabular-nums">
        {formatHours(row.hours)}
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
  /** Side panel open: leave out Writes used and Spare (the panel shows them). */
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
          <TableHead>Drive</TableHead>
          <TableHead>Bench</TableHead>
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
