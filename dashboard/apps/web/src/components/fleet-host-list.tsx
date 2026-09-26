import { Button } from "@workspace/ui/components/button"
import { cn } from "@workspace/ui/lib/utils"

import {
  BenchProblemLine,
  BenchStatusPill,
  useBenchNames,
} from "@/components/ui-cdi"
import { formatScannedAgo, formatSummaryCounts } from "@/lib/host-utils"
import type { FleetHost } from "@/lib/types"

type FleetHostListProps = {
  hosts: FleetHost[]
  /** A Scan all benches run is in flight. */
  scanning?: boolean
  /** Show healthy / warn / fail counts per bench. */
  showSummary?: boolean
  /** Drill into one bench (e.g. filter Drives to it). */
  onSelectHost?: (host: FleetHost) => void
  selectLabel?: string
  className?: string
}

function hostKey(host: FleetHost, index: number): string {
  return host.machine_id ?? `${host.name}-${index}`
}

/** Per-bench status tiles: name, status, drive count, last scan, and any problem. */
export function FleetHostList({
  hosts,
  scanning = false,
  showSummary = false,
  onSelectHost,
  selectLabel = "Show only this bench",
  className,
}: FleetHostListProps) {
  const nameOf = useBenchNames()
  if (hosts.length === 0) {
    return null
  }

  return (
    <ul
      className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-3", className)}
      aria-label="Benches"
    >
      {hosts.map((host, index) => {
        const name = nameOf(host.machine_id, host.name)
        return (
          <li
            key={hostKey(host, index)}
            className="flex flex-col gap-1.5 rounded-xl border p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[17px] font-bold">{name}</span>
              <BenchStatusPill status={host.status} scanning={scanning} />
            </div>
            <span className="text-[15px] text-muted-foreground">
              {host.device_count} drive{host.device_count === 1 ? "" : "s"} ·{" "}
              {formatScannedAgo(host.scanned_at)}
            </span>
            {showSummary && host.summary ? (
              <span className="text-[15px] text-muted-foreground">
                {formatSummaryCounts(host.summary)}
              </span>
            ) : null}
            {!scanning ? (
              <BenchProblemLine
                name={name}
                status={host.status}
                error={host.error}
                className="text-[15px]"
              />
            ) : null}
            {onSelectHost && host.machine_id ? (
              <Button
                variant="quiet"
                size="sm"
                className="-ml-3 w-fit"
                onClick={() => onSelectHost(host)}
              >
                {selectLabel}
              </Button>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}
