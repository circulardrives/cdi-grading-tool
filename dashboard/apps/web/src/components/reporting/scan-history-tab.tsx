/**
 * Reports › Scan history: every saved scan, newest first, with View,
 * Report ▾, and Delete. The bench filter is the header bench scope.
 */
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { HistoryIcon, ScanLineIcon, Trash2Icon } from "lucide-react"
import { toast } from "sonner"

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
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

import { GradeCounts } from "@/components/reporting/report-bits"
import { ScanReportMenu } from "@/components/reporting/scan-report-actions"
import {
  benchName,
  EmptyState,
  Note,
  PageSection,
  Pill,
  useBenchNames,
  useBenchScope,
} from "@/components/ui-cdi"
import {
  useHistoryPagesQuery,
  useInvalidateCdiQueries,
  useScanAllBenches,
} from "@/hooks/use-cdi-queries"
import { clearHistory, deleteHistory } from "@/lib/api"
import {
  describeReportError,
  formatExactTime,
  formatRelativeTime,
  formatScanTime,
} from "@/lib/report-utils"
import type { HistorySummary } from "@/lib/types"

const ALL_BENCHES = "all"

function scansWord(count: number): string {
  return `${count.toLocaleString()} saved scan${count === 1 ? "" : "s"}`
}

export function ScanHistoryTab() {
  const { scopeId, setScope, scopedBench, benches } = useBenchScope()
  const historyQuery = useHistoryPagesQuery(scopeId)
  const nameOf = useBenchNames()
  const scanAll = useScanAllBenches()
  const { invalidateHistory } = useInvalidateCdiQueries()
  const [deleteTarget, setDeleteTarget] = useState<HistorySummary | null>(null)
  const [clearOpen, setClearOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  const entries = useMemo(
    () => historyQuery.data?.pages.flat() ?? [],
    [historyQuery.data]
  )
  const scopeName = scopeId
    ? scopedBench
      ? benchName(scopedBench)
      : nameOf(scopeId)
    : null
  // Clear all deletes every saved scan, so only quote a count when the whole
  // unfiltered list is loaded.
  const totalKnown =
    !scopeId && historyQuery.isSuccess && !historyQuery.hasNextPage
  const describeScan = (entry: HistorySummary) =>
    `${nameOf(entry.machine_id)}, ${formatScanTime(entry.scanned_at)}`

  const confirmDelete = async () => {
    if (!deleteTarget) {
      return
    }
    setBusy(true)
    try {
      await deleteHistory(deleteTarget.id)
      toast.success("Scan deleted")
      setDeleteTarget(null)
      await invalidateHistory()
    } catch (error) {
      toast.error(`Couldn't delete the scan — ${describeReportError(error)}`)
    } finally {
      setBusy(false)
    }
  }

  const confirmClear = async () => {
    setBusy(true)
    try {
      const result = await clearHistory()
      toast.success(`Deleted ${scansWord(result.deleted)}`)
      setClearOpen(false)
      await invalidateHistory()
    } catch (error) {
      toast.error(`Couldn't clear scan history — ${describeReportError(error)}`)
    } finally {
      setBusy(false)
    }
  }

  const scanButton = (
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
  )

  let body
  if (historyQuery.isLoading) {
    body = (
      <div className="flex flex-col gap-2 px-6 pb-6" aria-busy="true">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
        <span className="sr-only">Loading saved scans…</span>
      </div>
    )
  } else if (historyQuery.error) {
    body = (
      <div className="px-6 pb-6">
        <Note tone="bad">
          Couldn't load scan history — {describeReportError(historyQuery.error)}
          .{" "}
          <button
            type="button"
            className="font-semibold text-link underline underline-offset-4"
            onClick={() => void historyQuery.refetch()}
          >
            Try again
          </button>
        </Note>
      </div>
    )
  } else if (entries.length === 0) {
    body = (
      <div className="px-6 pb-6 max-sm:px-4">
        <EmptyState
          icon={<HistoryIcon />}
          title={
            scopeName
              ? `No saved scans of ${scopeName} yet`
              : "No saved scans yet"
          }
          description="Every scan is saved here automatically."
          actions={scanButton}
        />
      </div>
    )
  } else {
    body = (
      <>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6">When</TableHead>
              <TableHead>Bench</TableHead>
              <TableHead className="text-right">Drives</TableHead>
              <TableHead>Grades</TableHead>
              <TableHead className="pr-6 text-right">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="pl-6 whitespace-nowrap">
                  <span className="flex flex-col leading-tight">
                    <time
                      dateTime={entry.scanned_at}
                      title={formatExactTime(entry.scanned_at)}
                      className="font-semibold"
                    >
                      {formatScanTime(entry.scanned_at)}
                    </time>
                    <span className="text-[15px] text-muted-foreground">
                      {formatRelativeTime(entry.scanned_at)}
                    </span>
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  <span className="flex flex-wrap items-center gap-2">
                    {nameOf(entry.machine_id)}
                    {entry.mock ? <Pill tone="info">Sample drives</Pill> : null}
                  </span>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {entry.device_count.toLocaleString()}
                </TableCell>
                <TableCell className="min-w-56">
                  <GradeCounts grades={entry.grades} />
                </TableCell>
                <TableCell className="pr-6">
                  <div className="flex justify-end gap-1">
                    <Button variant="quiet" asChild>
                      <Link
                        to={`/reports/history/${encodeURIComponent(entry.id)}`}
                        aria-label={`View the scan of ${describeScan(entry)}`}
                      >
                        View
                      </Link>
                    </Button>
                    <ScanReportMenu
                      scanId={entry.id}
                      label={`Report on the scan of ${describeScan(entry)}`}
                    />
                    <Button
                      variant="quiet"
                      className="text-destructive hover:text-destructive"
                      disabled={busy}
                      aria-label={`Delete the scan of ${describeScan(entry)}`}
                      onClick={() => setDeleteTarget(entry)}
                    >
                      <Trash2Icon data-icon="inline-start" />
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="flex flex-wrap items-center gap-3 border-t border-border px-6 py-4 text-[15px] text-muted-foreground max-sm:px-4">
          <span aria-live="polite">
            Showing {scansWord(entries.length)}
            {historyQuery.hasNextPage ? " — there are more" : ""}
          </span>
          {historyQuery.hasNextPage ? (
            <Button
              variant="outline"
              disabled={historyQuery.isFetchingNextPage}
              aria-busy={historyQuery.isFetchingNextPage}
              onClick={() => void historyQuery.fetchNextPage()}
            >
              {historyQuery.isFetchingNextPage ? (
                <Spinner data-icon="inline-start" />
              ) : null}
              Show more
            </Button>
          ) : null}
        </div>
      </>
    )
  }

  return (
    <>
      <PageSection
        id="scan-history"
        title="Scan history"
        description="Newest first — every scan is saved automatically"
        flush
        actions={
          <>
            {benches.length > 0 ? (
              <div className="flex items-center gap-2">
                <label
                  htmlFor="scan-history-bench"
                  className="text-base font-semibold"
                >
                  Bench
                </label>
                <Select
                  value={scopeId ?? ALL_BENCHES}
                  onValueChange={(value) =>
                    setScope(value === ALL_BENCHES ? null : value)
                  }
                >
                  <SelectTrigger
                    id="scan-history-bench"
                    className="h-11! min-w-48 rounded-[10px] border-input bg-card text-base"
                  >
                    <SelectValue placeholder="All benches" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      value={ALL_BENCHES}
                      className="min-h-11 text-base"
                    >
                      All benches
                    </SelectItem>
                    {benches.map((bench) => (
                      <SelectItem
                        key={bench.id}
                        value={bench.id}
                        className="min-h-11 text-base"
                      >
                        {benchName(bench)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : null}
            <Button
              variant="destructive"
              disabled={busy || (totalKnown && entries.length === 0)}
              onClick={() => setClearOpen(true)}
            >
              <Trash2Icon data-icon="inline-start" />
              Clear all
            </Button>
          </>
        }
      >
        {body}
      </PageSection>

      <AlertDialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
            <AlertDialogDescription className="text-base">
              {deleteTarget
                ? `The saved scan of ${nameOf(deleteTarget.machine_id)} from ${formatExactTime(deleteTarget.scanned_at)} will be deleted. Reports already made from it stay. This can't be undone.`
                : "This can't be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={busy}
              onClick={(event) => {
                event.preventDefault()
                void confirmDelete()
              }}
            >
              {busy ? <Spinner data-icon="inline-start" /> : null}
              Delete scan
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={clearOpen} onOpenChange={setClearOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete all saved scans?</AlertDialogTitle>
            <AlertDialogDescription className="text-base">
              {totalKnown
                ? `All ${scansWord(entries.length)} will be deleted.`
                : scopeName
                  ? `Every saved scan from every bench will be deleted — not only ${scopeName}.`
                  : "Every saved scan from every bench will be deleted."}{" "}
              Reports already made stay. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={busy}
              onClick={(event) => {
                event.preventDefault()
                void confirmClear()
              }}
            >
              {busy ? <Spinner data-icon="inline-start" /> : null}
              Delete all
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
