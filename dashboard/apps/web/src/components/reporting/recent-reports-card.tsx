/**
 * Reports › Recent reports: reports made on this dashboard, newest first,
 * with Open (new tab) and Download.
 */
import { useState } from "react"
import { Link } from "react-router-dom"
import { DownloadIcon, ExternalLinkIcon, FileTextIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Spinner } from "@workspace/ui/components/spinner"

import { When } from "@/components/reporting/report-bits"
import { useReportFileActions } from "@/components/reporting/use-report-actions"
import {
  EmptyState,
  Note,
  PageSection,
  useBenchNames,
} from "@/components/ui-cdi"
import { useReportsQuery } from "@/hooks/use-cdi-queries"
import {
  describeReportError,
  formatDrives,
  formatRelativeTime,
  REPORT_FORMAT_SHORT,
} from "@/lib/report-utils"
import type { ReportHost, ReportListEntry } from "@/lib/types"

/** Rows shown before "Show all". */
const FIRST_ROWS = 6
const MAX_NAMED_BENCHES = 3

function ReportRow({
  entry,
  benchesOf,
}: {
  entry: ReportListEntry
  benchesOf: (hosts: ReportHost[] | null | undefined) => string
}) {
  const actions = useReportFileActions()
  const { filename } = entry
  const what = `${REPORT_FORMAT_SHORT[entry.format]} report from ${formatRelativeTime(entry.generated_at)}`
  const benches = benchesOf(entry.hosts)

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border py-3 first:pt-0 last:border-0 last:pb-0">
      <div className="flex min-w-0 flex-1 basis-48 flex-col gap-0.5">
        <span className="flex flex-wrap items-baseline gap-x-2">
          <span className="font-semibold">
            {REPORT_FORMAT_SHORT[entry.format]}
          </span>
          <span className="text-muted-foreground">·</span>
          <span>{formatDrives(entry.devices_count)}</span>
          <When
            iso={entry.generated_at}
            className="text-[15px] text-muted-foreground"
          />
        </span>
        <span className="truncate text-[15px] text-muted-foreground">
          {benches || "Benches not recorded"}
        </span>
      </div>
      <div className="flex gap-1">
        {entry.format !== "csv" ? (
          <Button
            variant="quiet"
            aria-label={`Open the ${what} in a new tab`}
            disabled={actions.isBusy(filename, "open")}
            aria-busy={actions.isBusy(filename, "open")}
            onClick={() => void actions.open(filename)}
          >
            {actions.isBusy(filename, "open") ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <ExternalLinkIcon data-icon="inline-start" />
            )}
            Open
          </Button>
        ) : null}
        <Button
          variant="quiet"
          aria-label={`Download the ${what}`}
          disabled={actions.isBusy(filename, "download")}
          aria-busy={actions.isBusy(filename, "download")}
          onClick={() => void actions.download(filename)}
        >
          {actions.isBusy(filename, "download") ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <DownloadIcon data-icon="inline-start" />
          )}
          Download
        </Button>
      </div>
    </li>
  )
}

export function RecentReportsCard({ className }: { className?: string }) {
  const reportsQuery = useReportsQuery()
  const nameOf = useBenchNames()
  const [showAll, setShowAll] = useState(false)

  const reports = reportsQuery.data?.reports ?? []
  const sharedList = reportsQuery.data?.savedOnServer ?? true
  const shown = showAll ? reports : reports.slice(0, FIRST_ROWS)

  const benchesOf = (hosts: ReportHost[] | null | undefined) => {
    const names = (hosts ?? []).map((host) =>
      nameOf(host.machine_id, host.name)
    )
    if (names.length <= MAX_NAMED_BENCHES) {
      return names.join(", ")
    }
    return `${names.slice(0, MAX_NAMED_BENCHES).join(", ")} +${names.length - MAX_NAMED_BENCHES} more`
  }

  let body
  if (reportsQuery.isLoading) {
    body = (
      <div className="flex flex-col gap-3" aria-busy="true">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
        <span className="sr-only">Loading recent reports…</span>
      </div>
    )
  } else if (reportsQuery.error) {
    body = (
      <Note tone="bad">
        Couldn't load recent reports — {describeReportError(reportsQuery.error)}
        .{" "}
        <button
          type="button"
          className="font-semibold text-link underline underline-offset-4"
          onClick={() => void reportsQuery.refetch()}
        >
          Try again
        </button>
      </Note>
    )
  } else if (reports.length === 0) {
    body = (
      <EmptyState
        icon={<FileTextIcon />}
        title="No reports yet"
        description="Reports you create appear here for everyone using this dashboard."
      />
    )
  } else {
    body = (
      <>
        <ul className="flex flex-col" aria-label="Recent reports">
          {shown.map((entry, index) => (
            <ReportRow
              key={`${entry.filename}-${index}`}
              entry={entry}
              benchesOf={benchesOf}
            />
          ))}
        </ul>
        {reports.length > FIRST_ROWS ? (
          <div>
            <Button variant="outline" onClick={() => setShowAll((v) => !v)}>
              {showAll ? "Show fewer" : `Show all ${reports.length} reports`}
            </Button>
          </div>
        ) : null}
        {!sharedList ? (
          <p className="text-[15px] text-muted-foreground">
            Only you can see these. Update CDI Health on this bench so everyone
            using this dashboard sees the same reports.
          </p>
        ) : null}
      </>
    )
  }

  return (
    <PageSection
      id="recent-reports"
      title="Recent reports"
      className={className}
    >
      {body}
      <Link
        to="/reports?tab=history"
        className="flex min-h-11 w-fit items-center text-base font-semibold text-link underline-offset-4 hover:text-link-hover hover:underline"
      >
        Scan history
      </Link>
    </PageSection>
  )
}
