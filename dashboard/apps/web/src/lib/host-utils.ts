import type { DiscoveredHost, Machine } from "@/lib/types"

export type HostFormState = {
  name: string
  hostname: string
  address: string
  location: string
  notes: string
}

export const emptyHostForm: HostFormState = {
  name: "",
  hostname: "",
  address: "",
  location: "",
  notes: "",
}

export function machineStatusBadgeVariant(status: Machine["status"]) {
  if (status === "reachable") {
    return "default" as const
  }
  if (status === "unreachable") {
    return "destructive" as const
  }
  return "secondary" as const
}

export function formatScanSummary(machine: Machine): string {
  const summary = machine.last_scan_summary
  if (!summary) {
    return "No scan yet"
  }
  return `${summary.total} drives · ${summary.healthy} healthy · ${summary.warning} warn · ${summary.failed} fail`
}

export function defaultDiscoveredHostName(host: DiscoveredHost): string {
  return host.hostname?.trim() || host.ip
}

export function discoveryHealthLabel(host: DiscoveredHost): string {
  if (!host.health) {
    return "Port open"
  }
  if (host.cdi_api) {
    return host.health.is_root ? "CDI API (root)" : "CDI API"
  }
  return host.health.status ?? "Unknown"
}

export function discoveryHealthVariant(host: DiscoveredHost) {
  if (host.cdi_api) {
    return "default" as const
  }
  if (host.health) {
    return "secondary" as const
  }
  return "outline" as const
}
