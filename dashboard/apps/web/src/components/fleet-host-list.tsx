import { AlertCircleIcon } from "lucide-react"

import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import {
  fleetHostProblem,
  formatScannedAgo,
  formatSummaryCounts,
  machineStatusBadgeVariant,
  machineStatusLabel,
} from "@/lib/host-utils"
import type { FleetHost } from "@/lib/types"

type FleetHostListProps = {
  hosts: FleetHost[]
  /** A Scan all hosts run is in flight. */
  scanning?: boolean
  /** Show healthy / warn / fail counts per host. */
  showSummary?: boolean
  /** Drill into one host (e.g. filter Drive Health to it). */
  onSelectHost?: (host: FleetHost) => void
  selectLabel?: string
  className?: string
}

function hostKey(host: FleetHost, index: number): string {
  return host.machine_id ?? `${host.name}-${index}`
}

/** Per-host status tiles: name, status, drive count, last scan, and any problem. */
export function FleetHostList({
  hosts,
  scanning = false,
  showSummary = false,
  onSelectHost,
  selectLabel = "Show only this host",
  className,
}: FleetHostListProps) {
  if (hosts.length === 0) {
    return null
  }

  return (
    <ul
      className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-3", className)}
      aria-label="Hosts"
    >
      {hosts.map((host, index) => {
        const problem = fleetHostProblem(host)
        return (
          <li
            key={hostKey(host, index)}
            className={cn(
              "flex flex-col gap-1.5 rounded-2xl border p-3",
              problem ? "border-destructive/40" : undefined
            )}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium">{host.name}</span>
              {scanning ? (
                <Badge variant="secondary">
                  <Spinner />
                  Scanning
                </Badge>
              ) : (
                <Badge variant={machineStatusBadgeVariant(host.status)}>
                  {machineStatusLabel(host.status)}
                </Badge>
              )}
            </div>
            <span className="text-muted-foreground text-xs">
              {host.device_count} drive{host.device_count === 1 ? "" : "s"} ·{" "}
              {formatScannedAgo(host.scanned_at)}
            </span>
            {showSummary && host.summary ? (
              <span className="text-muted-foreground text-xs">
                {formatSummaryCounts(host.summary)}
              </span>
            ) : null}
            {problem && !scanning ? (
              <p className="text-destructive flex items-start gap-1.5 text-xs">
                <AlertCircleIcon className="mt-px size-3.5 shrink-0" aria-hidden />
                <span>{problem}</span>
              </p>
            ) : null}
            {onSelectHost && host.machine_id ? (
              <Button
                variant="ghost"
                size="xs"
                className="-ml-2 w-fit"
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
