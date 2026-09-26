import { ApiError } from "@/lib/api"
import type {
  DiscoveredHost,
  FleetDevicesResponse,
  FleetHost,
  Machine,
  MachineStatus,
  ScanSummary,
} from "@/lib/types"

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

/** Where a technician finds a host's access token on that bench. */
export const ACCESS_TOKEN_HINT_COMMAND = "sudo cat /etc/default/cdi-health-api"

export function machineStatusBadgeVariant(status: MachineStatus | string) {
  if (status === "reachable") {
    return "default" as const
  }
  if (status === "unreachable" || status === "auth_failed") {
    return "destructive" as const
  }
  return "secondary" as const
}

/** Short, plain-language badge text for a host's connection status. */
export function machineStatusLabel(status: MachineStatus | string): string {
  switch (status) {
    case "reachable":
      return "Online"
    case "unreachable":
      return "Can't reach"
    case "auth_failed":
      return "Wrong token"
    case "unknown":
    case "":
      return "Not checked"
    default:
      return status
  }
}

export function hostHasAddress(host: { address?: string | null }): boolean {
  return Boolean(host.address?.trim())
}

function unreachableMessage(name: string): string {
  return `Can't reach ${name} — check it's powered on and on the network`
}

function wrongTokenMessage(name: string): string {
  return `Wrong access token for ${name} — re-enter it in Hosts`
}

/**
 * Turns an API error (detail text, optional HTTP status) for one host into a
 * one-line, actionable message. Falls back to the API's own detail text.
 */
export function describeHostProblem(
  name: string,
  message: string | null | undefined,
  status?: number
): string | null {
  const text = (message ?? "").trim()
  const lower = text.toLowerCase()
  if (
    status === 401 ||
    status === 403 ||
    lower.includes("token") ||
    lower.includes("unauthorized") ||
    lower.includes("forbidden")
  ) {
    return wrongTokenMessage(name)
  }
  if (status === 504 || lower.includes("timed out") || lower.includes("timeout")) {
    return `${name} took too long to answer — try again, or check it isn't overloaded`
  }
  if (status === 409 || lower.includes("busy") || lower.includes("already running")) {
    return `${name} is busy with another scan — try again in a minute`
  }
  if (
    status === 502 ||
    lower.includes("unreachable") ||
    lower.includes("connection refused") ||
    lower.includes("could not connect")
  ) {
    return unreachableMessage(name)
  }
  if (!text) {
    return null
  }
  // Keep it to one line next to the host.
  return text.split("\n")[0] ?? text
}

/** One-line problem for a host from its status and last error, or null when fine. */
export function hostProblemMessage(
  name: string,
  status: MachineStatus | string,
  error?: string | null
): string | null {
  if (error) {
    return describeHostProblem(name, error)
  }
  if (status === "unreachable") {
    return unreachableMessage(name)
  }
  if (status === "auth_failed") {
    return wrongTokenMessage(name)
  }
  return null
}

/** Friendly message for a failed request aimed at one host (scan, check, …). */
export function describeRequestError(
  error: unknown,
  name: string,
  fallback: string
): string {
  if (error instanceof ApiError) {
    return describeHostProblem(name, error.message, error.status) ?? fallback
  }
  if (error instanceof Error) {
    return describeHostProblem(name, error.message) ?? fallback
  }
  return fallback
}

export function fleetHostProblem(host: FleetHost): string | null {
  return hostProblemMessage(host.name, host.status, host.error)
}

/** Summary line after "Scan all hosts"; `ok` is false when any host had a problem. */
export function fleetScanToast(data: FleetDevicesResponse): {
  ok: boolean
  text: string
} {
  const problems = data.hosts
    .map(fleetHostProblem)
    .filter((problem): problem is string => problem != null)
  const hostCount = data.hosts.length
  const driveCount = data.summary.total
  const base = `Scanned ${hostCount} host${hostCount === 1 ? "" : "s"} — ${driveCount} drive${driveCount === 1 ? "" : "s"}`
  if (problems.length === 0) {
    return { ok: true, text: base }
  }
  if (problems.length === 1) {
    return { ok: false, text: `${base}. ${problems[0]}` }
  }
  return {
    ok: false,
    text: `${base}. ${problems.length} hosts had problems — see the host list`,
  }
}

export function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

export function formatScanSummary(machine: Machine): string {
  const summary = machine.last_scan_summary
  if (!summary) {
    return "No scan yet"
  }
  return formatSummaryCounts(summary)
}

/** One-line scan summary; the ungraded count only appears when the API sends it. */
export function formatSummaryCounts(summary: ScanSummary): string {
  const parts = [
    `${summary.total} drives`,
    `${summary.healthy} healthy`,
    `${summary.warning} warn`,
    `${summary.failed} fail`,
  ]
  if (summary.ungraded) {
    parts.push(`${summary.ungraded} ungraded`)
  }
  return parts.join(" · ")
}

export const MAX_DISCOVER_SUBNETS = 4

const SUBNET_PATTERN =
  /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?:\/(\d{1,2}))?$/

/**
 * Parses comma/space separated IPv4 subnets for Discover. Returns the list,
 * or a message a technician can act on. Mirrors the API limits (max 4
 * subnets, /24 or smaller); the API still validates private ranges.
 */
export function parseSubnetInput(
  raw: string
): { subnets: string[]; error: null } | { subnets: null; error: string } {
  const items = raw
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (items.length > MAX_DISCOVER_SUBNETS) {
    return {
      subnets: null,
      error: `Up to ${MAX_DISCOVER_SUBNETS} subnets at a time — you entered ${items.length}`,
    }
  }
  for (const item of items) {
    const match = SUBNET_PATTERN.exec(item)
    const octets = match ? match.slice(1, 5).map(Number) : []
    if (!match || octets.some((octet) => octet > 255)) {
      return {
        subnets: null,
        error: `"${item}" doesn't look like a subnet — use a form like 192.168.0.0/24`,
      }
    }
    const prefix = match[5] == null ? 32 : Number(match[5])
    if (prefix > 32) {
      return {
        subnets: null,
        error: `"${item}" has an invalid size — the number after / must be between 24 and 32`,
      }
    }
    if (prefix < 24) {
      return {
        subnets: null,
        error: `"${item}" is too big to scan — use /24 or smaller (for example ${octets.slice(0, 3).join(".")}.0/24)`,
      }
    }
  }
  return { subnets: items, error: null }
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
