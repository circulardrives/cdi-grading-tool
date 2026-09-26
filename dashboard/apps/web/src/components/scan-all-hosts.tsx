/**
 * "Scan all benches": the primary action in the header on every page, and
 * the global progress bar under the header while it runs. The in-progress
 * state is shared through the react-query mutation key, so every page sees it.
 */
import { ScanLineIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import { useScanAllBenches, useScanAllStatus } from "@/hooks/use-cdi-queries"
import { formatElapsed } from "@/lib/host-utils"

type ScanAllBenchesButtonProps = {
  size?: "default" | "sm" | "lg"
  disabled?: boolean
  className?: string
  /** Shorter label ("Scan all") for narrow screens. */
  compact?: boolean
}

export function ScanAllBenchesButton({
  size = "default",
  disabled = false,
  className,
  compact = false,
}: ScanAllBenchesButtonProps) {
  const { start, pending } = useScanAllBenches()
  const idleLabel = compact ? "Scan all" : "Scan all benches"

  return (
    <Button
      size={size}
      className={className}
      onClick={start}
      disabled={pending || disabled}
    >
      {pending ? (
        <Spinner
          data-icon="inline-start"
          role="presentation"
          aria-hidden="true"
        />
      ) : (
        <ScanLineIcon data-icon="inline-start" />
      )}
      {pending ? "Scanning…" : idleLabel}
    </Button>
  )
}

/** Progress line shown under the header while every bench is being scanned. */
export function ScanAllProgressBar({
  benchCount,
  thisBenchOnly = false,
  className,
}: {
  benchCount?: number
  /** The run scans only the bench this dashboard runs on. */
  thisBenchOnly?: boolean
  className?: string
}) {
  const { pending, elapsedSeconds } = useScanAllStatus()
  if (!pending) {
    return null
  }
  const benches = thisBenchOnly
    ? "this bench"
    : benchCount && benchCount > 0
      ? `${benchCount} bench${benchCount === 1 ? "" : "es"}`
      : "all benches"

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 bg-accent px-8 py-2.5 text-[15px] text-accent-foreground max-md:px-4",
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Spinner role="presentation" aria-hidden="true" />
      <span>
        <span className="font-semibold">
          Scanning {benches} · {formatElapsed(elapsedSeconds)}
        </span>{" "}
        — this can take a few minutes. Keep working; results appear when it's
        done.
      </span>
    </div>
  )
}

/** @deprecated Old name; the header owns this button now. Pages should not render it. */
export const ScanAllHostsButton = ScanAllBenchesButton

/** @deprecated The shell shows progress globally; pages render nothing here. */
export function ScanAllHostsProgress(_props: { hostCount?: number }) {
  return null
}
