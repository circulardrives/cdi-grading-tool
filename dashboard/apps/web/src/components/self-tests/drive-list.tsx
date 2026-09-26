/**
 * Drive list for one bench with the action bar on top (mockup SelfTests):
 * "<n> selected on <bench>" · Start short test · Extended test · Stop.
 */
import { useEffect, useRef, useState, type MouseEvent } from "react"
import { ActivityIcon, SquareIcon } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@workspace/ui/components/alert-dialog"
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

import { Card } from "@/components/ui-cdi"
import { SelfTestStatus } from "@/components/self-tests/self-test-status"
import type {
  DriveRow,
  TestType,
} from "@/components/self-tests/self-test-format"
import type { BenchQueue } from "@/components/self-tests/start-queue"

type DriveListProps = {
  benchName: string
  rows: DriveRow[]
  loading: boolean
  /** Status can't be read right now: nothing can be started or stopped. */
  blocked: boolean
  selected: ReadonlySet<string>
  onSelectedChange: (next: Set<string>) => void
  queue: BenchQueue
  stopping: ReadonlySet<string>
  onStart: (devices: string[], testType: TestType) => void
  onStop: (devices: string[]) => void
}

function drives(n: number): string {
  return n === 1 ? "1 drive" : `${n} drives`
}

export function DriveList({
  benchName,
  rows,
  loading,
  blocked,
  selected,
  onSelectedChange,
  queue,
  stopping,
  onStart,
  onStop,
}: DriveListProps) {
  const [confirm, setConfirm] = useState<"extended" | "stop" | null>(null)

  const selectable = rows.filter((row) => !row.unavailable)
  const chosen = rows.filter((row) => selected.has(row.device))
  const running = chosen.filter((row) => row.status?.in_progress)
  const startable = chosen.filter(
    (row) =>
      !row.unavailable &&
      !row.status?.in_progress &&
      !queue.pending.has(row.device)
  )
  const canAct = !blocked && !loading

  const allChecked =
    selectable.length > 0 && selectable.every((row) => selected.has(row.device))
  const someChecked = selectable.some((row) => selected.has(row.device))
  const headerBox = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (headerBox.current) {
      headerBox.current.indeterminate = someChecked && !allChecked
    }
  }, [someChecked, allChecked])

  const toggle = (device: string) => {
    const next = new Set(selected)
    if (next.has(device)) {
      next.delete(device)
    } else {
      next.add(device)
    }
    onSelectedChange(next)
  }

  const toggleAll = () => {
    onSelectedChange(
      allChecked ? new Set() : new Set(selectable.map((row) => row.device))
    )
  }

  // Tapping anywhere on a row toggles it (gloves); the checkbox stays the
  // keyboard control.
  const onRowClick = (event: MouseEvent, row: DriveRow) => {
    if (row.unavailable) {
      return
    }
    const target = event.target as HTMLElement
    if (target.closest("label, input, button, a")) {
      return
    }
    toggle(row.device)
  }

  const count = chosen.length
  const countLine =
    count === 0
      ? `Pick drives to test on ${benchName}`
      : `${count} selected on ${benchName}`

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b px-5 py-4 max-sm:px-4">
        <span
          className="text-[17px] font-bold"
          aria-live="polite"
          aria-atomic="true"
        >
          {countLine}
        </span>
        <div className="ml-auto flex flex-wrap justify-end gap-2">
          {running.length > 0 ? (
            <Button
              variant="outline"
              disabled={!canAct || stopping.size > 0}
              onClick={() => setConfirm("stop")}
            >
              {stopping.size > 0 ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <SquareIcon data-icon="inline-start" aria-hidden="true" />
              )}
              {running.length === 1
                ? "Stop test"
                : `Stop ${running.length} tests`}
            </Button>
          ) : null}
          <Button
            disabled={!canAct || startable.length === 0}
            onClick={() =>
              onStart(
                startable.map((row) => row.device),
                "short"
              )
            }
          >
            <ActivityIcon data-icon="inline-start" aria-hidden="true" />
            Start short test · about 2 min
          </Button>
          <Button
            variant="outline"
            disabled={!canAct || startable.length === 0}
            onClick={() => setConfirm("extended")}
          >
            Extended test · hours
          </Button>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-14 pr-0">
              <label className="flex size-11 cursor-pointer items-center justify-center">
                <input
                  ref={headerBox}
                  type="checkbox"
                  className="size-5 cursor-pointer accent-primary disabled:cursor-not-allowed"
                  aria-label="Select all drives"
                  checked={allChecked}
                  disabled={selectable.length === 0}
                  onChange={toggleAll}
                />
              </label>
            </TableHead>
            <TableHead className="max-lg:hidden">Serial</TableHead>
            <TableHead>Drive</TableHead>
            <TableHead className="max-lg:hidden">Slot</TableHead>
            <TableHead>Self-test</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading
            ? Array.from({ length: 4 }, (_, index) => (
                <TableRow key={index} className="hover:bg-transparent">
                  <TableCell className="pr-0">
                    <div className="flex size-11 items-center justify-center">
                      <Skeleton className="size-5 rounded" />
                    </div>
                  </TableCell>
                  <TableCell className="max-lg:hidden">
                    <Skeleton className="h-4 w-44" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-48" />
                  </TableCell>
                  <TableCell className="max-lg:hidden">
                    <Skeleton className="h-4 w-14" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-36" />
                  </TableCell>
                </TableRow>
              ))
            : rows.map((row) => {
                const isSelected = selected.has(row.device)
                const name = row.serial || row.slot
                const showReason = row.unavailable && !row.status?.in_progress
                return (
                  <TableRow
                    key={row.device}
                    data-state={isSelected ? "selected" : undefined}
                    className={
                      row.unavailable
                        ? "hover:bg-transparent"
                        : "cursor-pointer"
                    }
                    onClick={(event) => onRowClick(event, row)}
                  >
                    <TableCell className="pr-0">
                      <label
                        className={
                          row.unavailable
                            ? "flex size-11 items-center justify-center"
                            : "flex size-11 cursor-pointer items-center justify-center"
                        }
                      >
                        <input
                          type="checkbox"
                          className="size-5 cursor-pointer accent-primary disabled:cursor-not-allowed"
                          aria-label={`Select ${name}`}
                          aria-description={row.unavailable ?? undefined}
                          checked={isSelected}
                          disabled={Boolean(row.unavailable)}
                          onChange={() => toggle(row.device)}
                        />
                      </label>
                    </TableCell>
                    <TableCell className="font-mono text-[15px] max-lg:hidden">
                      {row.serial || (
                        <span className="font-sans text-muted-foreground">
                          —
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="max-lg:min-w-56 max-lg:whitespace-normal">
                      <span className="font-semibold">{row.title}</span>
                      {row.capacity ? (
                        <span className="whitespace-nowrap text-muted-foreground">
                          {" "}
                          {row.capacity}
                        </span>
                      ) : null}
                      {/* Tablets: serial and slot fold in under the name. */}
                      <div className="text-[15px] text-muted-foreground lg:hidden">
                        {row.serial ? (
                          <span className="font-mono text-foreground">
                            {row.serial}
                          </span>
                        ) : null}
                        {row.serial ? " · " : ""}
                        {row.slot}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground max-lg:hidden">
                      {row.slot}
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      {showReason ? (
                        <span className="text-muted-foreground">
                          {row.unavailable}
                        </span>
                      ) : (
                        <SelfTestStatus
                          row={row}
                          queued={queue.pending.get(row.device)}
                          startFailure={queue.failures.get(row.device)}
                          startedType={queue.started.get(row.device)}
                          stopping={stopping.has(row.device)}
                        />
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
        </TableBody>
      </Table>

      <AlertDialog
        open={confirm === "extended"}
        onOpenChange={(open) => !open && setConfirm(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl leading-tight font-bold">
              Start an extended test on {drives(startable.length)}?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-base">
              An extended test checks the whole drive and can take several
              hours. The drive stays usable, and the test keeps going on{" "}
              {benchName} if you close this page.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                onStart(
                  startable.map((row) => row.device),
                  "extended"
                )
                setConfirm(null)
              }}
            >
              Start extended test
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={confirm === "stop"}
        onOpenChange={(open) => !open && setConfirm(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl leading-tight font-bold">
              Stop the self-test on {drives(running.length)}?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-base">
              The test ends now and is recorded as aborted. You can start it
              again later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep testing</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                onStop(running.map((row) => row.device))
                setConfirm(null)
              }}
            >
              Stop test
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
