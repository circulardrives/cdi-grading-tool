/**
 * Layout and display primitives styled per the redesign mockups (gen.py CSS).
 * Built on shadcn where one exists (Card, Empty); plain elements otherwise.
 *
 * - <Card>          white surface, 1px border, 14px radius (no padding; add your own)
 * - <PageSection>   Card with an h2 header row (title · muted description · actions) and a body
 * - <EmptyState>    dashed box with icon, title, one line, optional actions
 * - <StatTile>      small label over a big number (drive panel, overview tiles)
 * - <Pill>          26px rounded status pill with optional dot, in a Tone
 * - <SectionLabel>  13px uppercase label ("WHY B", "HISTORY", "FORMAT")
 * - <Note>          icon + sentence row, in a Tone (reasons, problems, hints)
 */
import type { ComponentProps, ReactNode } from "react"
import { AlertCircleIcon, CheckIcon, InfoIcon } from "lucide-react"

import { Card as ShadcnCard } from "@workspace/ui/components/card"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import { cn } from "@workspace/ui/lib/utils"

import {
  TONE_ICON,
  TONE_PILL,
  TONE_TEXT,
  type Tone,
} from "@/components/ui-cdi/tone"

// ---------------------------------------------------------------------------

/** Bare surface. `padded` adds the standard 24px padding. */
export function Card({
  className,
  padded = false,
  ...props
}: ComponentProps<"div"> & { padded?: boolean }) {
  return (
    <ShadcnCard
      className={cn("gap-0 py-0", padded && "p-6 max-sm:p-4", className)}
      {...props}
    />
  )
}

type PageSectionProps = {
  title: ReactNode
  /** Muted text after the title, e.g. "latest scan of every drive". */
  description?: ReactNode
  /** Right-aligned header content: buttons, an "All drives" link. */
  actions?: ReactNode
  /** Body has no padding (tables that run edge to edge). */
  flush?: boolean
  /** Highlighted border (e.g. "Find benches on the network"). */
  emphasis?: boolean
  className?: string
  bodyClassName?: string
  children?: ReactNode
  id?: string
}

/** A titled card section. Put tables inside with `flush`. */
export function PageSection({
  title,
  description,
  actions,
  flush = false,
  emphasis = false,
  className,
  bodyClassName,
  children,
  id,
}: PageSectionProps) {
  const headingId = id ? `${id}-title` : undefined
  return (
    <Card
      className={cn(emphasis && "border-primary/45", className)}
      aria-labelledby={headingId}
      id={id}
      role="region"
    >
      <div
        className={cn(
          "flex flex-wrap items-center gap-x-3 gap-y-1 px-6 pt-5 max-sm:px-4",
          flush ? "pb-4" : "pb-0"
        )}
      >
        <h2 id={headingId} className="text-xl leading-tight font-bold">
          {title}
        </h2>
        {description ? (
          <span className="text-[15px] text-muted-foreground">
            {description}
          </span>
        ) : null}
        {actions ? (
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {actions}
          </div>
        ) : null}
      </div>
      <div
        className={cn(
          flush ? "" : "flex flex-col gap-4 px-6 pt-4 pb-6 max-sm:px-4",
          bodyClassName
        )}
      >
        {children}
      </div>
    </Card>
  )
}

type EmptyStateProps = {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}

/** Dashed empty box: "No reports yet" + one line + optional buttons. */
export function EmptyState({
  icon,
  title,
  description,
  actions,
  className,
}: EmptyStateProps) {
  return (
    <Empty
      className={cn(
        "rounded-xl border border-dashed border-input px-3 py-9",
        className
      )}
    >
      <EmptyHeader>
        {icon ? (
          <EmptyMedia className="text-muted-foreground [&_svg:not([class*='size-'])]:size-8">
            {icon}
          </EmptyMedia>
        ) : null}
        <EmptyTitle className="text-[17px] font-semibold">{title}</EmptyTitle>
        {description ? (
          <EmptyDescription className="text-[15px] text-muted-foreground">
            {description}
          </EmptyDescription>
        ) : null}
      </EmptyHeader>
      {actions ? (
        <EmptyContent className="flex flex-row flex-wrap justify-center gap-2">
          {actions}
        </EmptyContent>
      ) : null}
    </Empty>
  )
}

type StatTileProps = {
  label: ReactNode
  value: ReactNode
  /** Small line under the value. */
  hint?: ReactNode
  /** "tile" = grey inset box (drive panel); "card" = white bordered card. */
  variant?: "tile" | "card"
  className?: string
}

/** Label over a big number: "Powered on / 40,856 h". */
export function StatTile({
  label,
  value,
  hint,
  variant = "tile",
  className,
}: StatTileProps) {
  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-0.5 rounded-[10px] px-3.5 py-3",
        variant === "tile" ? "bg-muted" : "border bg-card px-5 py-4",
        className
      )}
    >
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-[22px] leading-tight font-bold tabular-nums">
        {value}
      </div>
      {hint ? (
        <div className="text-sm text-muted-foreground">{hint}</div>
      ) : null}
    </div>
  )
}

/** Status pill: "● Online". Pair colour with words; never colour alone. */
export function Pill({
  tone = "info",
  dot = false,
  className,
  children,
}: {
  tone?: Tone
  dot?: boolean
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[26px] w-fit shrink-0 items-center gap-1.5 rounded-full px-2.5 text-sm font-semibold whitespace-nowrap",
        TONE_PILL[tone],
        className
      )}
    >
      {dot ? (
        <span aria-hidden="true" className="size-2 rounded-full bg-current" />
      ) : null}
      {children}
    </span>
  )
}

/** 13px uppercase label above a group ("Why B", "Format"). */
export function SectionLabel({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "text-[13px] font-bold tracking-[0.06em] text-muted-foreground uppercase",
        className
      )}
      {...props}
    />
  )
}

const TONE_DEFAULT_ICON: Record<Tone, ReactNode> = {
  ok: <CheckIcon />,
  bad: <AlertCircleIcon />,
  warn: <AlertCircleIcon />,
  info: <InfoIcon />,
}

/**
 * Icon + sentence. `tone` colours the icon (and the text for bad/warn, as in
 * the problem lines). `neutralText` keeps the text in the body colour.
 */
export function Note({
  tone = "info",
  icon,
  neutralText,
  className,
  children,
}: {
  tone?: Tone
  icon?: ReactNode
  neutralText?: boolean
  className?: string
  children: ReactNode
}) {
  const colourText = !neutralText && (tone === "bad" || tone === "warn")
  return (
    <div
      className={cn(
        "flex items-start gap-2.5 text-base leading-snug",
        colourText && TONE_TEXT[tone],
        className
      )}
    >
      <span
        aria-hidden="true"
        className={cn("mt-0.5 shrink-0 [&_svg]:size-5", TONE_ICON[tone])}
      >
        {icon ?? TONE_DEFAULT_ICON[tone]}
      </span>
      <span className="min-w-0">{children}</span>
    </div>
  )
}
