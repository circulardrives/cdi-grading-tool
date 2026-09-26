/**
 * Pure helpers for the Benches page: network input, addresses, access and
 * last-scan wording, and the rows of the bench table.
 */
import {
  benchAddress,
  benchName,
  countByGrade,
  fleetHostName,
  type GradeLetter,
} from "@/components/ui-cdi"
import { hostHasAddress } from "@/lib/host-utils"
import type {
  FleetDevicesResponse,
  FleetHost,
  Machine,
  MachineStatus,
} from "@/lib/types"

/** Inputs sized like the mockup: 48px tall, 10px radius, 16px text. */
export const BENCH_INPUT_CLASS =
  "h-12 rounded-[10px] border-input bg-card px-3.5 text-base md:text-base"

// ---------------------------------------------------------------------------
// Networks to search
// ---------------------------------------------------------------------------

export const MAX_NETWORKS = 4

const NETWORK_PATTERN =
  /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?:\/(\d{1,2}))?$/

/**
 * Parses "192.168.0.0/24, 192.168.1.0/24" (commas or spaces). Blank means
 * "the network this dashboard is on". Returns a message a technician can act
 * on when something is off. The limits match what the search allows: up to 4
 * networks, each /24 or smaller.
 */
export function parseNetworks(
  raw: string
): { networks: string[]; error: null } | { networks: null; error: string } {
  const items = raw
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (items.length > MAX_NETWORKS) {
    return {
      networks: null,
      error: `Search up to ${MAX_NETWORKS} networks at a time — you entered ${items.length}.`,
    }
  }
  for (const item of items) {
    const match = NETWORK_PATTERN.exec(item)
    const octets = match ? match.slice(1, 5).map(Number) : []
    if (!match || octets.some((octet) => octet > 255)) {
      return {
        networks: null,
        error: `“${item}” doesn't look like a network. Write it like 192.168.0.0/24.`,
      }
    }
    const size = match[5] == null ? 32 : Number(match[5])
    if (size > 32) {
      return {
        networks: null,
        error: `“${item}” — the number after / must be between 24 and 32.`,
      }
    }
    if (size < 24) {
      return {
        networks: null,
        error: `“${item}” is too big to search. Use /24 or smaller, like ${octets.slice(0, 3).join(".")}.0/24.`,
      }
    }
  }
  return { networks: items, error: null }
}

const NETWORKS_STORAGE_KEY = "cdi-benches-networks"

/** Last "Networks to search" value in this browser ("" when none). */
export function loadSavedNetworks(fallback: string): string {
  try {
    return localStorage.getItem(NETWORKS_STORAGE_KEY) ?? fallback
  } catch {
    return fallback
  }
}

export function saveNetworks(value: string): void {
  try {
    if (value.trim()) {
      localStorage.setItem(NETWORKS_STORAGE_KEY, value.trim())
    } else {
      localStorage.removeItem(NETWORKS_STORAGE_KEY)
    }
  } catch {
    /* storage may be blocked; the field still works */
  }
}

// ---------------------------------------------------------------------------
// Bench address (Add by address)
// ---------------------------------------------------------------------------

const ADDRESS_PATTERN =
  /^(?:\d{1,3}(?:\.\d{1,3}){3}|[A-Za-z0-9](?:[A-Za-z0-9-]{0,62})(?:\.[A-Za-z0-9-]{1,63})*)(?::(\d{1,5}))?$/

/**
 * Cleans an address typed by a technician ("http://10.0.0.5:8844/" →
 * "10.0.0.5:8844"). Returns an error message when it can't be a bench address.
 */
export function parseBenchAddress(
  raw: string
): { address: string; error: null } | { address: null; error: string } {
  const address = raw
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/\/+$/, "")
  if (!address) {
    return { address: null, error: "Enter the bench's IP address." }
  }
  const match = ADDRESS_PATTERN.exec(address)
  const port = match?.[1] == null ? null : Number(match[1])
  const ipOctets = /^\d{1,3}(?:\.\d{1,3}){3}/.test(address)
    ? address.split(":")[0]!.split(".").map(Number)
    : []
  if (
    !match ||
    ipOctets.some((octet) => octet > 255) ||
    (port != null && (port < 1 || port > 65535))
  ) {
    return {
      address: null,
      error:
        "That isn't an address. Write it like 192.168.0.21 or 192.168.0.21:8844.",
    }
  }
  return { address, error: null }
}

// ---------------------------------------------------------------------------
// Access (token) wording
// ---------------------------------------------------------------------------

export type BenchAccess =
  | "none_needed"
  | "token_set"
  | "needs_token"
  | "unknown"

export const BENCH_ACCESS_LABEL: Record<BenchAccess, string> = {
  none_needed: "No token needed",
  token_set: "Token set",
  needs_token: "Needs access token",
  unknown: "Not known yet",
}

export function benchAccess(
  machine: Pick<Machine, "status" | "has_api_token" | "remote_auth">
): BenchAccess {
  if (machine.status === "auth_failed") {
    return "needs_token"
  }
  if (machine.has_api_token) {
    return "token_set"
  }
  if (machine.remote_auth === "none") {
    return "none_needed"
  }
  if (machine.remote_auth === "token") {
    return "needs_token"
  }
  return "unknown"
}

// ---------------------------------------------------------------------------
// Time
// ---------------------------------------------------------------------------

/** "Just now", "12 min ago", "3 h ago", "Yesterday, 9:00 AM", "Sep 24, 9:00 AM". */
export function formatRelativeScan(
  iso: string | null | undefined,
  now = Date.now()
): string | null {
  if (!iso) {
    return null
  }
  const time = Date.parse(iso)
  if (Number.isNaN(time)) {
    return null
  }
  const minutes = Math.round((now - time) / 60_000)
  if (minutes < 1) {
    return "Just now"
  }
  if (minutes < 60) {
    return `${minutes} min ago`
  }
  const hours = Math.round(minutes / 60)
  if (hours < 12) {
    return `${hours} h ago`
  }
  const at = new Date(time)
  const clock = at.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  })
  const today = new Date(now)
  if (at.toDateString() === today.toDateString()) {
    return `Today, ${clock}`
  }
  const yesterday = new Date(now - 86_400_000)
  if (at.toDateString() === yesterday.toDateString()) {
    return `Yesterday, ${clock}`
  }
  return `${at.toLocaleDateString([], { month: "short", day: "numeric" })}, ${clock}`
}

export function formatElapsedSeconds(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

// ---------------------------------------------------------------------------
// Table rows
// ---------------------------------------------------------------------------

export type BenchRow = {
  /** Stable key: the bench id, or "this-bench". */
  key: string
  /** Registered bench; null for the bench this dashboard runs on. */
  machine: Machine | null
  name: string
  /** Small line under the name (IP, or "This bench"). */
  address: string
  status: MachineStatus | string
  /** Drives in its latest scan, or null when it hasn't been scanned. */
  driveCount: number | null
  grades: Record<GradeLetter, number> | null
  lastScanAt: string | null
  /** Error from the last scan of all benches, if any. */
  fleetError: string | null
}

function fleetHostFor(
  fleet: FleetDevicesResponse | null | undefined,
  machineId: string | null
): FleetHost | null {
  return fleet?.hosts.find((host) => host.machine_id === machineId) ?? null
}

function gradesFor(
  fleet: FleetDevicesResponse | null | undefined,
  machineId: string | null
): Record<GradeLetter, number> | null {
  if (!fleet) {
    return null
  }
  return countByGrade(
    fleet.devices.filter((device) => device.machine_id === machineId)
  )
}

/**
 * The bench this dashboard runs on (when its last scan found drives), then
 * every registered bench by name.
 */
export function buildBenchRows(
  machines: Machine[],
  fleet: FleetDevicesResponse | null | undefined,
  thisBenchHostname: string | null | undefined
): BenchRow[] {
  const rows: BenchRow[] = []

  const local = fleetHostFor(fleet, null)
  if (local) {
    rows.push({
      key: "this-bench",
      machine: null,
      name: fleetHostName(local, machines, thisBenchHostname),
      address: "This bench",
      status: local.status,
      driveCount: local.scanned_at ? local.device_count : null,
      grades: gradesFor(fleet, null),
      lastScanAt: local.scanned_at,
      fleetError: local.error,
    })
  }

  const sorted = machines
    .slice()
    .sort((a, b) => benchName(a).localeCompare(benchName(b)))
  for (const machine of sorted) {
    const host = fleetHostFor(fleet, machine.id)
    const scannedAt = host?.scanned_at ?? machine.last_scan_at ?? null
    const driveCount = host?.scanned_at
      ? host.device_count
      : (machine.last_scan_summary?.total ?? null)
    rows.push({
      key: machine.id,
      machine,
      name: benchName(machine),
      address: hostHasAddress(machine) ? benchAddress(machine) : "",
      status: machine.status,
      driveCount: scannedAt ? driveCount : null,
      grades: host?.scanned_at ? gradesFor(fleet, machine.id) : null,
      lastScanAt: scannedAt,
      fleetError: host?.error ?? null,
    })
  }
  return rows
}
