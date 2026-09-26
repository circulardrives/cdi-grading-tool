/**
 * Tables for the drive details page. Headers stay put while the body
 * scrolls (the scroll box is keyboard-focusable), rows are 16px text, and
 * fields CDI grades on carry a status pill and their limit.
 */
import type { ComponentProps, ReactNode } from "react"

import { cn } from "@workspace/ui/lib/utils"

import { Card, Pill } from "@/components/ui-cdi"

import type { GradeCheck, Status } from "./details-format"

// ---------------------------------------------------------------------------
// Scrolling table with sticky header
// ---------------------------------------------------------------------------

export function ScrollTable({
  label,
  children,
  className,
}: {
  /** Accessible name of the scroll region and caption of the table. */
  label: string
  children: ReactNode
  className?: string
}) {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className={cn(
        "max-h-[min(72vh,760px)] overflow-auto outline-none focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:ring-inset",
        className
      )}
    >
      <table className="w-full border-separate border-spacing-0 text-base [&_tbody_tr:last-child>td]:border-b-0">
        <caption className="sr-only">{label}</caption>
        {children}
      </table>
    </div>
  )
}

export function Th({
  className,
  align = "left",
  ...props
}: ComponentProps<"th"> & { align?: "left" | "right" }) {
  return (
    <th
      scope="col"
      className={cn(
        "sticky top-0 z-10 h-11 border-b bg-card px-4 text-[13px] font-bold tracking-[0.04em] whitespace-nowrap text-muted-foreground uppercase",
        align === "right" ? "text-right" : "text-left",
        className
      )}
      {...props}
    />
  )
}

export function Td({
  className,
  align = "left",
  ...props
}: ComponentProps<"td"> & { align?: "left" | "right" }) {
  return (
    <td
      className={cn(
        "border-b px-4 py-3 align-top",
        align === "right" && "text-right tabular-nums",
        className
      )}
      {...props}
    />
  )
}

/** Muted secondary line under a cell's main text. */
export function Secondary({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn("text-[15px] break-words text-muted-foreground", className)}
      {...props}
    />
  )
}

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

const STATUS_PILL: Record<
  Status,
  { tone: "ok" | "warn" | "bad"; text: string }
> = {
  ok: { tone: "ok", text: "OK" },
  warn: { tone: "warn", text: "Warning" },
  fail: { tone: "bad", text: "Fails" },
}

export function StatusPill({ status }: { status: Status }) {
  const { tone, text } = STATUS_PILL[status]
  return (
    <Pill tone={tone} dot>
      {text}
    </Pill>
  )
}

/** "Counts toward grade" cell: status + limit, or "No — telemetry". */
export function CheckCell({
  check,
  note,
}: {
  check?: GradeCheck | null
  note?: ReactNode
}) {
  if (!check) {
    return (
      <span className="text-muted-foreground">{note ?? "No — telemetry"}</span>
    )
  }
  return (
    <div className="flex flex-col items-start gap-1">
      {check.status ? (
        <StatusPill status={check.status} />
      ) : (
        <span className="font-semibold">Yes — not reported</span>
      )}
      {check.limit ? <Secondary>{check.limit}</Secondary> : null}
      {check.detail && check.status !== "ok" ? (
        <Secondary>{check.detail}</Secondary>
      ) : null}
      {note ? <Secondary>{note}</Secondary> : null}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Field table (label · value · counts toward grade)
// ---------------------------------------------------------------------------

export type FieldRow = {
  key: string
  /** Plain label ("Spare"). */
  label: ReactNode
  /** Spec name / requirement ID, shown small ("Available Spare (AVSP)"). */
  spec?: ReactNode
  /** One-line meaning. */
  meaning?: ReactNode
  value: ReactNode
  /** Exact value or unit working, shown small under the value. */
  exact?: ReactNode
  /** Tooltip on the value (exact 128-bit counters). */
  valueTitle?: string
  /** Set for fields CDI grades on; leave out for telemetry. */
  check?: GradeCheck | null
  /** Replaces "No — telemetry" (or adds a line under the status). */
  note?: ReactNode
}

export function FieldTable({
  label,
  rows,
  fieldHeader = "Field",
}: {
  label: string
  rows: FieldRow[]
  fieldHeader?: string
}) {
  return (
    <ScrollTable label={label}>
      <thead>
        <tr>
          <Th className="w-[42%] min-w-56">{fieldHeader}</Th>
          <Th className="min-w-44">Value</Th>
          <Th className="min-w-48">Counts toward grade</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.key}
            className={cn(
              "hover:bg-muted/60",
              row.check &&
                "[&>td:first-child]:shadow-[inset_4px_0_0_var(--primary)]"
            )}
          >
            <Td>
              <div className="font-semibold">{row.label}</div>
              {row.meaning ? <Secondary>{row.meaning}</Secondary> : null}
              {row.spec ? (
                <Secondary className="font-mono text-sm">{row.spec}</Secondary>
              ) : null}
            </Td>
            <Td>
              <div
                className="font-semibold break-words tabular-nums"
                title={row.valueTitle}
              >
                {row.value}
              </div>
              {row.exact ? (
                <Secondary className="tabular-nums">{row.exact}</Secondary>
              ) : null}
            </Td>
            <Td>
              <CheckCell check={row.check} note={row.note} />
            </Td>
          </tr>
        ))}
      </tbody>
    </ScrollTable>
  )
}

/** Titled card holding one table edge to edge. */
export function TableCard({
  title,
  description,
  actions,
  children,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-1 border-b px-6 py-4 max-sm:px-4">
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <h3 className="text-xl leading-tight font-bold">{title}</h3>
          {description ? (
            <p className="text-[15px] text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
      {children}
    </Card>
  )
}
