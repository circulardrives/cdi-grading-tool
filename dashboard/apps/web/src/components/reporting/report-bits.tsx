/**
 * Small display pieces shared by Reports, Scan history, and a saved scan:
 *
 * - <When iso />            "12 min ago" with the exact time on hover
 * - <GradeCounts grades />  small GradeChips with counts, best grade first
 */
import { GRADE_ORDER, GradeChip, normalizeGrade } from "@/components/ui-cdi"
import type { GradeLetter } from "@/components/ui-cdi"
import { formatExactTime, formatRelativeTime } from "@/lib/report-utils"

export function When({
  iso,
  exact = false,
  className,
}: {
  iso: string | null | undefined
  /** Show the full date and time instead of "12 min ago". */
  exact?: boolean
  className?: string
}) {
  if (!iso) {
    return <span className={className}>—</span>
  }
  const full = formatExactTime(iso)
  return (
    <time dateTime={iso} title={full} className={className}>
      {exact ? full : formatRelativeTime(iso)}
    </time>
  )
}

/** Grade counts as small chips; a dash when there are none. */
export function GradeCounts({
  grades,
  size = "sm",
  className = "flex flex-wrap items-center gap-1.5",
}: {
  grades: Record<string, number> | null | undefined
  size?: "sm" | "md"
  className?: string
}) {
  const counts = new Map<GradeLetter, number>()
  for (const [key, value] of Object.entries(grades ?? {})) {
    const letter = normalizeGrade(key)
    if (letter && value > 0) {
      counts.set(letter, (counts.get(letter) ?? 0) + value)
    }
  }
  if (counts.size === 0) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <span className={className}>
      {GRADE_ORDER.filter((letter) => counts.has(letter)).map((letter) => (
        <GradeChip
          key={letter}
          grade={letter}
          size={size}
          label={counts.get(letter)}
        />
      ))}
    </span>
  )
}
