/**
 * Benches card: each bench's name, status, a one-line grade tally, and the
 * problem line (with its fix) when something is wrong. Opens Benches.
 */
import { Link } from "react-router-dom"
import { SearchIcon, ServerIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"

import {
  BenchProblemLine,
  BenchStatusPill,
  EmptyState,
  GRADE_ORDER,
  PageSection,
} from "@/components/ui-cdi"
import {
  formatScanTime,
  type OverviewBench,
} from "@/pages/overview/overview-data"

/** "8 drives · 6 A · 2 B · scanned 9:00 AM". */
function benchSummary(bench: OverviewBench): string {
  const parts = [
    bench.driveCount === 1 ? "1 drive" : `${bench.driveCount} drives`,
  ]
  for (const grade of GRADE_ORDER) {
    const count = bench.counts[grade]
    if (count > 0) {
      parts.push(
        grade === "UNGRADED" ? `${count} couldn't grade` : `${count} ${grade}`
      )
    }
  }
  const time = bench.scannedAt ? formatScanTime(bench.scannedAt) : null
  parts.push(time ? `scanned ${time}` : "not scanned yet")
  return parts.join(" · ")
}

export function BenchesCard({
  benches,
  scanning,
  className,
}: {
  benches: OverviewBench[]
  scanning: boolean
  className?: string
}) {
  return (
    <PageSection id="overview-benches" title="Benches" className={className}>
      {benches.length === 0 ? (
        <EmptyState
          icon={<ServerIcon />}
          title="No benches yet"
          description="Add the grading benches on your network to see their drives here."
          actions={
            <Button asChild>
              <Link to="/benches">
                <SearchIcon data-icon="inline-start" />
                Find benches
              </Link>
            </Button>
          }
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {benches.map((bench) => (
            <li key={bench.key}>
              <Link
                to="/benches"
                className="flex flex-col gap-1.5 rounded-xl border px-4 py-3.5 text-foreground outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/40"
              >
                <span className="flex flex-wrap items-center gap-2.5">
                  <span className="min-w-0 truncate text-lg font-bold">
                    {bench.name}
                  </span>
                  <BenchStatusPill status={bench.status} scanning={scanning} />
                </span>
                <span className="text-[15px] text-muted-foreground">
                  {benchSummary(bench)}
                </span>
                <BenchProblemLine
                  name={bench.name}
                  status={bench.status}
                  error={bench.error}
                  noDrives={bench.scannedAt != null && bench.driveCount === 0}
                  className="text-[15px]"
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PageSection>
  )
}
