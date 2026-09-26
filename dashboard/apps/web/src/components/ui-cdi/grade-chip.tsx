/**
 * GradeChip — the grade letter in a coloured disc plus a word, never colour alone.
 *
 *   <GradeChip grade="B" />                  → (B) Reuse
 *   <GradeChip grade="B" showWord="quality"/> → (B) Good
 *   <GradeChip grade="A" label="11" />        → (A) 11      (counts in legends/bench rows)
 *   <GradeChip grade="UNGRADED" size="lg" />  → (?) Couldn't grade
 *   <GradeChip grade={gradeOf(device)} />     → from a DeviceRecord
 *
 * Screen readers hear "Grade B: Reuse". Colours come from the --grade-* tokens.
 */
import type { ReactNode } from "react"

import { cn } from "@workspace/ui/lib/utils"

import {
  GRADE_INFO,
  normalizeGrade,
  type GradeLetter,
} from "@/components/ui-cdi/grade"

const CHIP_TONE: Record<GradeLetter, string> = {
  A: "bg-grade-a-bg text-grade-a-fg",
  B: "bg-grade-b-bg text-grade-b-fg",
  C: "bg-grade-c-bg text-grade-c-fg",
  D: "bg-grade-d-bg text-grade-d-fg",
  F: "bg-grade-f-bg text-grade-f-fg",
  UNGRADED: "bg-grade-u-bg text-grade-u-fg",
}

const DISC_TONE: Record<GradeLetter, string> = {
  A: "bg-grade-a-solid text-grade-a-solid-fg",
  B: "bg-grade-b-solid text-grade-b-solid-fg",
  C: "bg-grade-c-solid text-grade-c-solid-fg",
  D: "bg-grade-d-solid text-grade-d-solid-fg",
  F: "bg-grade-f-solid text-grade-f-solid-fg",
  UNGRADED: "bg-grade-u-solid text-grade-u-solid-fg",
}

const SIZE = {
  sm: {
    chip: "h-6 gap-1.5 pr-2 pl-0.5 text-sm",
    disc: "size-5 text-xs",
  },
  md: {
    chip: "h-[30px] gap-2 pr-3 pl-1 text-[15px]",
    disc: "size-6 text-sm",
  },
  lg: {
    chip: "h-9 gap-2.5 pr-3.5 pl-1 text-[17px]",
    disc: "size-[30px] text-base",
  },
} as const

export type GradeChipProps = {
  /** "A".."F", "UNGRADED" (also accepts "U", "?", lower case); null shows a neutral "—". */
  grade: GradeLetter | string | null | undefined
  size?: keyof typeof SIZE
  /**
   * Word after the disc: "outcome" (default, e.g. "Reuse"), "quality"
   * ("Good"), "both" ("Reuse — Good"), or false for the disc only.
   * `true` means "outcome".
   */
  showWord?: boolean | "outcome" | "quality" | "both"
  /** Replaces the word, e.g. a count ("11"). */
  label?: ReactNode
  className?: string
}

export function GradeChip({
  grade,
  size = "md",
  showWord = "outcome",
  label,
  className,
}: GradeChipProps) {
  const letter = normalizeGrade(grade)
  const sizes = SIZE[size]

  if (!letter) {
    return (
      <span
        className={cn(
          "inline-flex items-center font-semibold whitespace-nowrap text-muted-foreground",
          className
        )}
      >
        <span aria-hidden="true">—</span>
        <span className="sr-only">Not graded yet</span>
      </span>
    )
  }

  const info = GRADE_INFO[letter]
  const mode = showWord === true ? "outcome" : showWord
  let word: ReactNode = null
  if (label != null) {
    word = label
  } else if (mode === "outcome") {
    word = info.outcome
  } else if (mode === "quality") {
    word = info.quality
  } else if (mode === "both") {
    word =
      info.outcome === info.quality
        ? info.outcome
        : `${info.outcome} — ${info.quality}`
  }
  const spoken = letter === "UNGRADED" ? "No grade" : `Grade ${letter}`

  return (
    <span
      className={cn(
        "inline-flex w-fit shrink-0 items-center rounded-full font-semibold whitespace-nowrap",
        word == null && "p-0.5",
        CHIP_TONE[letter],
        word != null && sizes.chip,
        className
      )}
      title={`${spoken}: ${info.description}`}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-full leading-none font-extrabold",
          DISC_TONE[letter],
          sizes.disc
        )}
      >
        {info.symbol}
      </span>
      <span className="sr-only">
        {spoken}
        {word != null ? ": " : ""}
      </span>
      {word}
    </span>
  )
}
