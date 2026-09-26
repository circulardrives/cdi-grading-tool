/**
 * The bench table: Bench · Status · Drives · Last scan · Access · actions,
 * with a one-line problem under a row when something needs fixing.
 */
import { Fragment } from "react"

import { Button } from "@workspace/ui/components/button"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Spinner } from "@workspace/ui/components/spinner"
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
  BENCH_ACCESS_LABEL,
  benchAccess,
  formatElapsedSeconds,
  formatRelativeScan,
  type BenchRow,
} from "@/components/benches/bench-utils"
import {
  benchProblem,
  BenchProblemLine,
  BenchStatusPill,
  GRADE_ORDER,
  GradeChip,
} from "@/components/ui-cdi"
import { hostHasAddress } from "@/lib/host-utils"
import type { Machine } from "@/lib/types"

export type BenchRowState = {
  scanning: boolean
  /** When this row's own scan started (ms), for the elapsed timer. */
  scanSince: number | null
  checking: boolean
  /** Latest problem from a check or scan on this page. */
  problem: string | null
}

type BenchTableProps = {
  rows: BenchRow[]
  loading: boolean
  now: number
  stateOf: (row: BenchRow) => BenchRowState
  /** A scan of every bench is running; per-bench scans wait for it. */
  scanAllRunning: boolean
  onScan: (row: BenchRow) => void
  onCheck: (machine: Machine) => void
  onEdit: (machine: Machine) => void
}

function DrivesCell({ row }: { row: BenchRow }) {
  if (row.driveCount == null) {
    return <span className="text-muted-foreground">Not scanned yet</span>
  }
  if (row.driveCount === 0) {
    return <span className="text-muted-foreground">No drives</span>
  }
  const grades = row.grades
  return (
    <span className="flex min-w-[9.5rem] flex-wrap items-center gap-x-1.5 gap-y-1 lg:min-w-[11.5rem]">
      <span className="font-semibold tabular-nums">
        {row.driveCount}
        <span className="sr-only"> drives</span>
      </span>
      {grades && GRADE_ORDER.some((grade) => grades[grade] > 0) ? (
        <>
          <span aria-hidden="true" className="text-muted-foreground">
            ·
          </span>
          {GRADE_ORDER.filter((grade) => grades[grade] > 0).map((grade) => (
            <GradeChip
              key={grade}
              grade={grade}
              label={grades[grade]}
              className="tabular-nums"
            />
          ))}
        </>
      ) : null}
    </span>
  )
}

function AccessText({ row, className }: { row: BenchRow; className?: string }) {
  if (!row.machine) {
    return <span className={cn("text-muted-foreground", className)}>—</span>
  }
  const access = benchAccess(row.machine)
  return (
    <span
      className={cn(
        access === "needs_token"
          ? "font-semibold text-tone-warn-fg"
          : "text-muted-foreground",
        className
      )}
    >
      {BENCH_ACCESS_LABEL[access]}
    </span>
  )
}

function LastScanText({
  row,
  now,
  className,
}: {
  row: BenchRow
  now: number
  className?: string
}) {
  const text = formatRelativeScan(row.lastScanAt, now)
  if (!text || !row.lastScanAt) {
    return <span className={cn("text-muted-foreground", className)}>—</span>
  }
  return (
    <time
      dateTime={row.lastScanAt}
      title={new Date(row.lastScanAt).toLocaleString()}
      className={className}
    >
      {text}
    </time>
  )
}

function problemFor(row: BenchRow, state: BenchRowState): string | null {
  if (row.machine && !hostHasAddress(row.machine)) {
    return `${row.name} has no address — add it under Edit so the dashboard can scan it`
  }
  return state.problem ?? row.fleetError
}

export function BenchTable({
  rows,
  loading,
  now,
  stateOf,
  scanAllRunning,
  onScan,
  onCheck,
  onEdit,
}: BenchTableProps) {
  return (
    <Table aria-label="Benches">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Bench</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Drives</TableHead>
          <TableHead className="max-lg:hidden">Last scan</TableHead>
          <TableHead className="max-xl:hidden">Access</TableHead>
          <TableHead>
            <span className="sr-only">Actions</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading
          ? [0, 1].map((index) => (
              <TableRow key={index} className="hover:bg-transparent">
                <TableCell colSpan={6}>
                  <Skeleton className="h-9 w-full" />
                </TableCell>
              </TableRow>
            ))
          : rows.map((row) => {
              const state = stateOf(row)
              const machine = row.machine
              const canReach = !machine || hostHasAddress(machine)
              const status = canReach ? row.status : "unknown"
              const problem = problemFor(row, state)
              const hasProblemLine =
                !state.scanning &&
                benchProblem(row.name, status, {
                  error: problem,
                  noDrives: row.driveCount === 0,
                }) != null
              const elapsed =
                state.scanSince != null
                  ? Math.max(0, Math.floor((now - state.scanSince) / 1000))
                  : null
              return (
                <Fragment key={row.key}>
                  <TableRow
                    className={cn(
                      "hover:bg-transparent",
                      hasProblemLine && "border-b-0"
                    )}
                  >
                    <TableCell className="py-2.5">
                      <div className="flex min-w-28 flex-col leading-tight">
                        <span className="text-[17px] font-bold">
                          {row.name}
                        </span>
                        {row.address && row.address !== row.name ? (
                          <span
                            className={cn(
                              "text-sm text-muted-foreground",
                              machine && "font-mono"
                            )}
                          >
                            {row.address}
                          </span>
                        ) : null}
                        {machine?.location ? (
                          <span className="text-sm text-muted-foreground">
                            {machine.location}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="py-2.5">
                      <div className="flex flex-col items-start gap-1">
                        <BenchStatusPill
                          status={status}
                          scanning={state.scanning}
                        />
                        <AccessText row={row} className="text-sm xl:hidden" />
                      </div>
                    </TableCell>
                    <TableCell className="py-2.5 whitespace-normal">
                      <div className="flex flex-col gap-1">
                        <DrivesCell row={row} />
                        <LastScanText
                          row={row}
                          now={now}
                          className="text-sm text-muted-foreground lg:hidden"
                        />
                      </div>
                    </TableCell>
                    <TableCell className="max-lg:hidden">
                      <LastScanText row={row} now={now} />
                    </TableCell>
                    <TableCell className="max-xl:hidden">
                      <AccessText row={row} />
                    </TableCell>
                    <TableCell className="py-1.5 text-right">
                      <div className="flex items-center justify-end gap-0.5 max-lg:flex-col max-lg:items-stretch">
                        {canReach ? (
                          <Button
                            variant="quiet"
                            onClick={() => onScan(row)}
                            disabled={
                              state.scanning ||
                              (machine != null && scanAllRunning)
                            }
                            aria-label={
                              state.scanning
                                ? `Scanning ${row.name}`
                                : `Scan ${row.name}`
                            }
                            className="min-w-[5.25rem] px-3"
                          >
                            {state.scanning ? (
                              <>
                                <Spinner data-icon="inline-start" />
                                <span className="tabular-nums">
                                  {elapsed != null
                                    ? formatElapsedSeconds(elapsed)
                                    : "…"}
                                </span>
                              </>
                            ) : (
                              "Scan"
                            )}
                          </Button>
                        ) : null}
                        {machine && canReach ? (
                          <Button
                            variant="quiet"
                            onClick={() => onCheck(machine)}
                            disabled={state.checking}
                            aria-label={`Check connection to ${row.name}`}
                            className="min-w-[6rem] px-3 2xl:min-w-44"
                          >
                            {state.checking ? (
                              <Spinner data-icon="inline-start" />
                            ) : null}
                            <span>
                              Check
                              <span className="max-2xl:hidden">
                                {" "}
                                connection
                              </span>
                            </span>
                          </Button>
                        ) : null}
                        {machine ? (
                          <Button
                            variant="quiet"
                            onClick={() => onEdit(machine)}
                            aria-label={`Edit ${row.name}`}
                            className="px-3"
                          >
                            Edit
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                  {hasProblemLine ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell
                        colSpan={6}
                        className="pt-0 pb-3 whitespace-normal"
                      >
                        <BenchProblemLine
                          name={row.name}
                          status={status}
                          error={problem}
                          noDrives={row.driveCount === 0}
                        />
                      </TableCell>
                    </TableRow>
                  ) : null}
                </Fragment>
              )
            })}
      </TableBody>
    </Table>
  )
}
