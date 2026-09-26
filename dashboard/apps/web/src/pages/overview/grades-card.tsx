/**
 * Grades card: one stacked bar of the latest grade of every drive, and a
 * legend of GradeChips with counts. Each grade opens Drives filtered to it.
 */
import { Link } from "react-router-dom"
import { HardDriveIcon } from "lucide-react"

import { cn } from "@workspace/ui/lib/utils"

import {
  EmptyState,
  GRADE_INFO,
  GRADE_ORDER,
  GradeChip,
  PageSection,
  type GradeLetter,
} from "@/components/ui-cdi"

const BAR_TONE: Record<GradeLetter, string> = {
  A: "bg-grade-a-solid text-grade-a-solid-fg",
  B: "bg-grade-b-solid text-grade-b-solid-fg",
  C: "bg-grade-c-solid text-grade-c-solid-fg",
  D: "bg-grade-d-solid text-grade-d-solid-fg",
  F: "bg-grade-f-solid text-grade-f-solid-fg",
  UNGRADED: "bg-grade-u-solid text-grade-u-solid-fg",
}

/** Drives page filtered to one grade (and the scoped bench, if any). */
function drivesByGradeHref(grade: GradeLetter, benchId: string | null): string {
  const params = new URLSearchParams({ grade })
  if (benchId) {
    params.set("bench", benchId)
  }
  return `/drives?${params.toString()}`
}

function driveWord(count: number): string {
  return count === 1 ? "1 drive" : `${count} drives`
}

function spokenGrade(grade: GradeLetter): string {
  const info = GRADE_INFO[grade]
  return grade === "UNGRADED"
    ? "couldn't be graded"
    : `graded ${grade}, ${info.legend.toLowerCase()}`
}

export function GradesCard({
  counts,
  benchId,
  className,
}: {
  counts: Record<GradeLetter, number>
  benchId: string | null
  className?: string
}) {
  const total = GRADE_ORDER.reduce((sum, grade) => sum + counts[grade], 0)

  return (
    <PageSection
      id="overview-grades"
      title="Grades"
      description="latest scan of every drive"
      className={className}
    >
      {total === 0 ? (
        <EmptyState
          icon={<HardDriveIcon />}
          title="No grades yet"
          description="Grades show here after the first scan of your benches."
        />
      ) : (
        <>
          {/* The bar is a mouse shortcut; the legend below carries the same
              links for keyboard and screen-reader users. */}
          <div
            className="flex h-11 overflow-hidden rounded-[10px]"
            aria-hidden="true"
          >
            {GRADE_ORDER.filter((grade) => counts[grade] > 0).map((grade) => {
              const count = counts[grade]
              const share = (count / total) * 100
              const symbol = GRADE_INFO[grade].symbol
              return (
                <Link
                  key={grade}
                  tabIndex={-1}
                  to={drivesByGradeHref(grade, benchId)}
                  style={{ width: `${share}%` }}
                  className={cn(
                    "flex min-w-2 items-center justify-center overflow-hidden text-[15px] font-bold whitespace-nowrap tabular-nums transition-[filter] hover:brightness-110",
                    BAR_TONE[grade]
                  )}
                  title={`${symbol} · ${driveWord(count)} — show them`}
                >
                  <span>
                    {share >= 9
                      ? `${symbol} · ${count}`
                      : share >= 4
                        ? symbol
                        : ""}
                  </span>
                </Link>
              )
            })}
          </div>

          <ul className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2 xl:grid-cols-3">
            {GRADE_ORDER.map((grade) => {
              const count = counts[grade]
              const content = (
                <>
                  <GradeChip grade={grade} label={count} />
                  <span className="text-muted-foreground">
                    {GRADE_INFO[grade].legend}
                  </span>
                </>
              )
              return (
                <li key={grade}>
                  {count > 0 ? (
                    <Link
                      to={drivesByGradeHref(grade, benchId)}
                      className="-mx-2 flex min-h-11 items-center gap-2.5 rounded-[10px] px-2 outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/40"
                      aria-label={`${driveWord(count)} ${spokenGrade(grade)} — show them`}
                    >
                      {content}
                    </Link>
                  ) : (
                    <div className="flex min-h-11 items-center gap-2.5">
                      {content}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </PageSection>
  )
}
