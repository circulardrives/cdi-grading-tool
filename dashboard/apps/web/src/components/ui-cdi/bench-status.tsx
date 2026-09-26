/**
 * Bench display components.
 *
 * - <BenchStatusPill status={machine.status} scanning={…} />   ● Online / Scanning… / Can't reach / Needs access token / Unknown
 * - <BenchProblemLine name={benchName(m)} status={m.status} error={…} />   one actionable line, or nothing
 * - <BenchLabel machine={m} />   bold bench name with the IP small underneath
 */
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import {
  BENCH_STATUS_LABEL,
  BENCH_STATUS_TONE,
  benchAddress,
  benchName,
  benchProblem,
  benchStatus,
  type BenchNameSource,
} from "@/components/ui-cdi/bench"
import { Note, Pill } from "@/components/ui-cdi/primitives"
import type { MachineStatus } from "@/lib/types"

export function BenchStatusPill({
  status,
  scanning = false,
  className,
}: {
  status: MachineStatus | string | null | undefined
  /** A scan of this bench (or Scan all benches) is running. */
  scanning?: boolean
  className?: string
}) {
  const state = benchStatus(status, { scanning })
  return (
    <Pill
      tone={BENCH_STATUS_TONE[state]}
      dot={state !== "scanning"}
      className={className}
    >
      {state === "scanning" ? (
        <Spinner className="size-3.5" role="presentation" aria-hidden="true" />
      ) : null}
      {BENCH_STATUS_LABEL[state]}
    </Pill>
  )
}

/**
 * One line that says what to do next, next to the bench it's about. Renders
 * nothing when the bench is fine. Pass `noDrives` when its last scan found no
 * drives.
 */
export function BenchProblemLine({
  name,
  status,
  error,
  noDrives,
  className,
}: {
  name: string
  status: MachineStatus | string | null | undefined
  error?: string | null
  noDrives?: boolean
  className?: string
}) {
  const problem = benchProblem(name, status, { error, noDrives })
  if (!problem) {
    return null
  }
  return (
    <Note tone={problem.tone} className={className}>
      {problem.text}
    </Note>
  )
}

/** Bench name (bold) with its address small and monospaced underneath. */
export function BenchLabel({
  machine,
  className,
  showAddress = true,
}: {
  machine: BenchNameSource
  className?: string
  showAddress?: boolean
}) {
  const name = benchName(machine)
  const address = benchAddress(machine)
  return (
    <div className={cn("flex min-w-0 flex-col leading-tight", className)}>
      <span className="truncate text-[17px] font-bold">{name}</span>
      {showAddress && address && address !== name ? (
        <span className="truncate font-mono text-sm text-muted-foreground">
          {address}
        </span>
      ) : null}
    </div>
  )
}
