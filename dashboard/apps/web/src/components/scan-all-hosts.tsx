import { ScanSearchIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Spinner } from "@workspace/ui/components/spinner"

import {
  useScanAllHostsMutation,
  useScanAllStatus,
} from "@/hooks/use-cdi-queries"
import { formatElapsed } from "@/lib/host-utils"

type ScanAllHostsButtonProps = {
  size?: "default" | "sm" | "lg"
  disabled?: boolean
}

/** The main "Scan all hosts" action; shares its in-progress state across pages. */
export function ScanAllHostsButton({
  size = "default",
  disabled = false,
}: ScanAllHostsButtonProps) {
  const scanAll = useScanAllHostsMutation()
  const { pending } = useScanAllStatus()

  return (
    <Button
      size={size}
      onClick={() => scanAll.mutate()}
      disabled={pending || disabled}
    >
      {pending ? (
        <Spinner data-icon="inline-start" />
      ) : (
        <ScanSearchIcon data-icon="inline-start" />
      )}
      {pending ? "Scanning all hosts…" : "Scan all hosts"}
    </Button>
  )
}

/** Progress line shown while every host is being scanned. */
export function ScanAllHostsProgress({ hostCount }: { hostCount?: number }) {
  const { pending, elapsedSeconds } = useScanAllStatus()
  if (!pending) {
    return null
  }
  const hosts =
    hostCount && hostCount > 0
      ? `${hostCount} host${hostCount === 1 ? "" : "s"}`
      : "all hosts"

  return (
    <div
      className="text-muted-foreground flex items-center gap-2 text-sm"
      role="status"
      aria-live="polite"
    >
      <Spinner />
      <span>
        Scanning {hosts} · {formatElapsed(elapsedSeconds)} elapsed. This can take a few
        minutes — you can keep using the dashboard, results appear here when done.
      </span>
    </div>
  )
}
