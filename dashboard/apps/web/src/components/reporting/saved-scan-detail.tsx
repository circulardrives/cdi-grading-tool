/**
 * /reports/history/:scanId — one saved scan: bench + time, grade summary,
 * the drives as they were at scan time, Report buttons, and Delete.
 */
import { useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeftIcon, HistoryIcon, Trash2Icon } from "lucide-react"
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

import { ScanReportButtons } from "@/components/reporting/scan-report-actions"
import {
  Card,
  countByGrade,
  driveNote,
  EmptyState,
  GRADE_INFO,
  GRADE_ORDER,
  GradeChip,
  gradeOf,
  gradeReason,
  PageHeadline,
  Pill,
  SectionLabel,
  useBenchNames,
} from "@/components/ui-cdi"
import {
  useHistoryDetailQuery,
  useInvalidateCdiQueries,
} from "@/hooks/use-cdi-queries"
import { ApiError, deleteHistory } from "@/lib/api"
import { deviceRowKeys } from "@/lib/drive-labels"
import { formatPoweredOn } from "@/lib/drive-names"
import {
  describeReportError,
  formatDrives,
  formatExactTime,
  formatScanTime,
} from "@/lib/report-utils"
import type { DeviceRecord } from "@/lib/types"

const HISTORY_PATH = "/reports?tab=history"

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.replace(/[,%]/g, "").trim())
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function percent(value: unknown): string {
  const n = toNumber(value)
  return n == null ? "—" : `${n.toLocaleString()}%`
}

function poweredOn(device: DeviceRecord): string {
  const hours = toNumber(device.power_on_hours)
  return formatPoweredOn(hours)
}

/** SSD writes used (NVMe percentage used, or the SATA/SAS endurance figure). */
function writesUsed(device: DeviceRecord): string {
  return percent(device.percentage_used ?? device.ssd_percentage_used_endurance)
}

function capacity(device: DeviceRecord): string | null {
  const bytes = toNumber(device.bytes)
  const gib = toNumber(device.gibibytes)
  const total = bytes ?? (gib != null ? gib * 1024 ** 3 : null)
  if (total == null || total <= 0) {
    return null
  }
  const tb = total / 1e12
  if (tb >= 1) {
    return `${tb.toLocaleString(undefined, { maximumFractionDigits: tb >= 10 ? 0 : 2 })} TB`
  }
  return `${Math.round(total / 1e9).toLocaleString()} GB`
}

function driveLabel(device: DeviceRecord): string {
  const model = [device.vendor, device.model_number]
    .map((part) => String(part ?? "").trim())
    .filter((part) => part && part.toLowerCase() !== "unknown")
    // Models often already start with the vendor name.
    .filter((part, index, parts) => index === 0 || !part.startsWith(parts[0]))
  const size = capacity(device)
  return [model.join(" "), size].filter(Boolean).join(" · ") || "—"
}

function DriveTable({ devices }: { devices: DeviceRecord[] }) {
  const keys = useMemo(() => deviceRowKeys(devices), [devices])
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="pl-6">Grade</TableHead>
          <TableHead>Serial</TableHead>
          <TableHead>Drive</TableHead>
          <TableHead className="text-right">Powered on</TableHead>
          <TableHead className="text-right">Writes used</TableHead>
          <TableHead className="text-right">Spare</TableHead>
          <TableHead className="pr-6">Why</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {devices.map((device) => (
          <TableRow key={keys.get(device)}>
            <TableCell className="pl-6">
              <GradeChip grade={gradeOf(device)} />
            </TableCell>
            <TableCell className="font-mono text-[15px] whitespace-nowrap">
              {String(device.serial_number ?? "").trim() || "—"}
            </TableCell>
            <TableCell className="min-w-48">{driveLabel(device)}</TableCell>
            <TableCell className="text-right whitespace-nowrap tabular-nums">
              {poweredOn(device)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {writesUsed(device)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {percent(device.available_spare)}
            </TableCell>
            <TableCell className="max-w-md min-w-64 pr-6 whitespace-normal">
              {gradeReason(device) ?? driveNote(device) ?? (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function BackLink() {
  return (
    <Button variant="quiet" asChild className="-ml-3 w-fit">
      <Link to={HISTORY_PATH}>
        <ArrowLeftIcon data-icon="inline-start" />
        Scan history
      </Link>
    </Button>
  )
}

export function SavedScanDetail({ scanId }: { scanId: string }) {
  const navigate = useNavigate()
  const detailQuery = useHistoryDetailQuery(scanId)
  const nameOf = useBenchNames()
  const { invalidateHistory } = useInvalidateCdiQueries()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const entry = detailQuery.data

  const confirmDelete = async () => {
    setBusy(true)
    try {
      await deleteHistory(scanId)
      toast.success("Scan deleted")
      setDeleteOpen(false)
      await invalidateHistory()
      navigate(HISTORY_PATH)
    } catch (error) {
      toast.error(`Couldn't delete the scan — ${describeReportError(error)}`)
    } finally {
      setBusy(false)
    }
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <BackLink />
        <Skeleton className="h-12 w-80 max-w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-72 w-full" />
        <span className="sr-only">Loading the saved scan…</span>
      </div>
    )
  }

  if (!entry) {
    const missing =
      !detailQuery.error ||
      (detailQuery.error instanceof ApiError &&
        detailQuery.error.status === 404)
    return (
      <div className="flex flex-col gap-6">
        <BackLink />
        <EmptyState
          icon={<HistoryIcon />}
          title={
            missing
              ? "This scan isn't saved any more"
              : "Couldn't load this scan"
          }
          description={
            missing
              ? "It may have been deleted. Pick another scan from Scan history."
              : describeReportError(detailQuery.error)
          }
          actions={
            <>
              {!missing ? (
                <Button
                  variant="outline"
                  disabled={detailQuery.isFetching}
                  onClick={() => void detailQuery.refetch()}
                >
                  {detailQuery.isFetching ? (
                    <Spinner data-icon="inline-start" />
                  ) : null}
                  Try again
                </Button>
              ) : null}
              <Button asChild>
                <Link to={HISTORY_PATH}>Go to Scan history</Link>
              </Button>
            </>
          }
        />
      </div>
    )
  }

  const bench = nameOf(entry.machine_id)
  const counts = countByGrade(entry.devices)
  const gradesFromDevices = GRADE_ORDER.some((letter) => counts[letter] > 0)

  return (
    <div className="flex flex-col gap-6">
      <BackLink />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <PageHeadline
          title={`${bench} · ${formatScanTime(entry.scanned_at)}`}
          subtitle={
            <span className="flex flex-wrap items-center gap-2">
              Saved scan from {formatExactTime(entry.scanned_at)} ·{" "}
              {formatDrives(entry.device_count)}
              {entry.mock ? <Pill tone="info">Sample drives</Pill> : null}
            </span>
          }
        />
        <Button
          variant="destructive"
          disabled={busy}
          onClick={() => setDeleteOpen(true)}
        >
          <Trash2Icon data-icon="inline-start" />
          Delete scan
        </Button>
      </div>

      <Card padded className="flex flex-col gap-5">
        <div className="flex flex-col gap-2.5">
          <SectionLabel>Grades</SectionLabel>
          <div className="flex flex-wrap gap-2">
            {GRADE_ORDER.filter((letter) =>
              gradesFromDevices
                ? counts[letter] > 0
                : (entry.grades[letter] ?? 0) > 0
            ).map((letter) => (
              <GradeChip
                key={letter}
                grade={letter}
                size="lg"
                label={`${(gradesFromDevices ? counts[letter] : entry.grades[letter]).toLocaleString()} ${GRADE_INFO[letter].outcome}`}
              />
            ))}
            {!gradesFromDevices &&
            Object.values(entry.grades).every((count) => !count) ? (
              <span className="text-muted-foreground">No grades recorded</span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-col gap-2.5">
          <SectionLabel>Report</SectionLabel>
          <ScanReportButtons scanId={scanId} />
          <p className="text-[15px] text-muted-foreground">
            Grades are shown exactly as they were at scan time.
          </p>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-baseline gap-x-3 px-6 pt-5 pb-4 max-sm:px-4">
          <h2 className="text-xl font-bold">Drives</h2>
          <span className="text-[15px] text-muted-foreground">
            as they were at scan time
          </span>
        </div>
        {entry.devices.length === 0 ? (
          <div className="px-6 pb-6 max-sm:px-4">
            <EmptyState
              title="No drives in this scan"
              description="The bench had no drives plugged in when it was scanned."
            />
          </div>
        ) : (
          <DriveTable devices={entry.devices} />
        )}
      </Card>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
            <AlertDialogDescription className="text-base">
              The saved scan of {bench} from {formatExactTime(entry.scanned_at)}{" "}
              will be deleted. Reports already made from it stay. This can't be
              undone.
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
    </div>
  )
}
