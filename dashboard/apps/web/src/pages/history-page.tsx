import { useMemo, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeftIcon,
  HistoryIcon,
  RefreshCwIcon,
  ScanSearchIcon,
  Trash2Icon,
} from "lucide-react"
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
import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import { Skeleton } from "@workspace/ui/components/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { DriveHealthTable } from "@/components/drive-health-table"
import { PageHeader } from "@/components/page-header"
import {
  useHistoryDetailQuery,
  useHistoryQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import { clearHistory, deleteHistory } from "@/lib/api"
import { getSimpleColumns } from "@/lib/drive-columns"
import type { HistorySummary, ScanSummary } from "@/lib/types"

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return "—"
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function formatSummaryCounts(summary: ScanSummary): string {
  return `${summary.total} drives · ${summary.healthy} healthy · ${summary.warning} warn · ${summary.failed} fail`
}

function formatGrades(grades: Record<string, number> | undefined): string {
  if (!grades || Object.keys(grades).length === 0) {
    return "—"
  }
  return Object.entries(grades)
    .map(([grade, count]) => `${grade}:${count}`)
    .join(" · ")
}

function HistoryList() {
  const historyQuery = useHistoryQuery()
  const machinesQuery = useMachinesQuery()
  const { invalidateHistory } = useInvalidateCdiQueries()
  const [deleteTarget, setDeleteTarget] = useState<HistorySummary | null>(null)
  const [clearOpen, setClearOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const entries = useMemo(
    () => historyQuery.data ?? [],
    [historyQuery.data]
  )
  const hostsById = useMemo(() => {
    const map = new Map<string, string>()
    for (const host of machinesQuery.data ?? []) {
      map.set(host.id, host.name)
    }
    return map
  }, [machinesQuery.data])

  const loading = historyQuery.isLoading
  const error =
    historyQuery.error instanceof Error
      ? historyQuery.error.message
      : machinesQuery.error instanceof Error
        ? machinesQuery.error.message
        : null

  const refresh = async () => {
    await Promise.all([historyQuery.refetch(), machinesQuery.refetch()])
  }

  const confirmDeleteOne = async () => {
    if (!deleteTarget) {
      return
    }
    setBusy(true)
    try {
      await deleteHistory(deleteTarget.id)
      toast.success("Scan deleted")
      setDeleteTarget(null)
      await invalidateHistory()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete scan")
    } finally {
      setBusy(false)
    }
  }

  const confirmClearAll = async () => {
    setBusy(true)
    try {
      const result = await clearHistory()
      toast.success(
        result.deleted === 1
          ? "Cleared 1 scan"
          : `Cleared ${result.deleted} scans`
      )
      setClearOpen(false)
      await invalidateHistory()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to clear history")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Operations"
        title="Scan History"
        description="Browse previous grading scans persisted on this API host."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void refresh()}>
              <RefreshCwIcon />
              Refresh
            </Button>
            <Button
              variant="destructive"
              disabled={busy || entries.length === 0}
              onClick={() => setClearOpen(true)}
            >
              <Trash2Icon />
              Clear all
            </Button>
          </div>
        }
      />

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load history</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Past scans</CardTitle>
          <CardDescription>
            Newest first. Open a scan to review the drive health snapshot.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : entries.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <HistoryIcon />
                </EmptyMedia>
                <EmptyTitle>No scan history yet</EmptyTitle>
                <EmptyDescription>
                  Run a scan from the Scan page. Successful results are saved
                  under this API data directory.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button asChild>
                  <Link to="/scan">
                    <ScanSearchIcon />
                    Go to Scan
                  </Link>
                </Button>
              </EmptyContent>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Scanned</TableHead>
                  <TableHead>Host</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Grades</TableHead>
                  <TableHead className="w-[1%]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry: HistorySummary) => (
                  <TableRow key={entry.id}>
                    <TableCell className="whitespace-nowrap font-mono text-xs">
                      {formatTimestamp(entry.scanned_at)}
                    </TableCell>
                    <TableCell>
                      {entry.machine_id
                        ? (hostsById.get(entry.machine_id) ?? entry.machine_id)
                        : "Local"}
                      {entry.mock ? (
                        <Badge variant="secondary" className="ml-2">
                          Mock
                        </Badge>
                      ) : null}
                    </TableCell>
                    <TableCell>{entry.device_count}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatSummaryCounts(entry.summary)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatGrades(entry.grades)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/history/${encodeURIComponent(entry.id)}`}>
                            View
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={busy}
                          onClick={() => setDeleteTarget(entry)}
                        >
                          <Trash2Icon />
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

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
            <AlertDialogDescription>
              {deleteTarget
                ? `Remove the snapshot from ${formatTimestamp(deleteTarget.scanned_at)}. This cannot be undone.`
                : "This cannot be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={busy}
              onClick={() => void confirmDeleteOne()}
            >
              Delete scan
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={clearOpen} onOpenChange={setClearOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear all scan history?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes all {entries.length} persisted scan
              snapshot{entries.length === 1 ? "" : "s"} on this API host.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={busy}
              onClick={() => void confirmClearAll()}
            >
              Clear all
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function HistoryDetailView({ scanId }: { scanId: string }) {
  const navigate = useNavigate()
  const detailQuery = useHistoryDetailQuery(scanId)
  const machinesQuery = useMachinesQuery()
  const { invalidateHistory } = useInvalidateCdiQueries()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const columns = useMemo(() => getSimpleColumns("Other"), [])
  const entry = detailQuery.data
  const hostName = !entry?.machine_id
    ? "Local"
    : (machinesQuery.data?.find((host) => host.id === entry.machine_id)?.name ??
      entry.machine_id)

  const loading = detailQuery.isLoading
  const error =
    detailQuery.error instanceof Error ? detailQuery.error.message : null

  const confirmDelete = async () => {
    setBusy(true)
    try {
      await deleteHistory(scanId)
      toast.success("Scan deleted")
      setDeleteOpen(false)
      await invalidateHistory()
      navigate("/history")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete scan")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Scan History"
        title={formatTimestamp(entry?.scanned_at)}
        description={`Snapshot ${scanId}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <Link to="/history">
                <ArrowLeftIcon />
                Back to history
              </Link>
            </Button>
            <Button variant="outline" onClick={() => void detailQuery.refetch()}>
              <RefreshCwIcon />
              Refresh
            </Button>
            <Button
              variant="destructive"
              disabled={busy || !entry}
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2Icon />
              Delete
            </Button>
          </div>
        }
      />

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load scan</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading || !entry ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{hostName}</Badge>
            <Badge variant="outline">{entry.device_count} devices</Badge>
            <Badge variant="secondary">
              {formatSummaryCounts(entry.summary)}
            </Badge>
            {entry.mock ? <Badge variant="secondary">Mock</Badge> : null}
            <Badge variant="outline" className="font-mono text-xs">
              {formatGrades(entry.grades)}
            </Badge>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Drive health snapshot</CardTitle>
              <CardDescription>
                Read-only view of drives at the time of this scan.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {entry.devices.length === 0 ? (
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <HistoryIcon />
                    </EmptyMedia>
                    <EmptyTitle>No devices in this scan</EmptyTitle>
                    <EmptyDescription>
                      The persisted snapshot has an empty device list.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : (
                <DriveHealthTable devices={entry.devices} columns={columns} />
              )}
            </CardContent>
          </Card>
        </>
      )}

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
            <AlertDialogDescription>
              Remove snapshot {scanId}. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={busy}
              onClick={() => void confirmDelete()}
            >
              Delete scan
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export function HistoryPage() {
  const { scanId } = useParams<{ scanId?: string }>()
  if (scanId) {
    return <HistoryDetailView scanId={scanId} />
  }
  return <HistoryList />
}
