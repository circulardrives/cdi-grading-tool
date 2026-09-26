/**
 * Bench naming, status, and one-line problem messages (pure, no React).
 * This is the single home for bench error → message wording; lib/host-utils.ts
 * re-exports the older names for pages that still import them.
 *
 * - `benchName(machine)`        → "pecan09-101h" (bench's own hostname, else name, else address)
 * - `benchAddress(machine)`     → "10.100.10.57" (shown small under the name)
 * - `fleetHostName(host, …)`    → name for a FleetHost row (the dashboard's own bench too)
 * - `benchStatus(status, …)`    → "online" | "scanning" | "unreachable" | "needs_token" | "unknown"
 * - `benchProblem(name, …)`     → { tone, text } one actionable line, or null when fine
 */
import { ApiError } from "@/lib/api"
import type { Tone } from "@/components/ui-cdi/tone"
import type { FleetHost, Machine, MachineStatus } from "@/lib/types"

/** What benchName needs; works for Machine rows and form drafts. */
export type BenchNameSource = {
  name?: string | null
  address?: string | null
  hostname?: string | null
  /** Hostname the bench reported about itself (newer benches, after a check). */
  remote_hostname?: string | null
}

const DEFAULT_PORT_SUFFIX = /:8844$/
const IPV4 = /^\d{1,3}(?:\.\d{1,3}){3}$/

/** "http://10.0.0.5:8844/" → "10.0.0.5"; keeps non-default ports. */
export function benchAddress(
  machine: Pick<BenchNameSource, "address"> | null | undefined
): string {
  return (machine?.address ?? "")
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/\/+$/, "")
    .replace(DEFAULT_PORT_SUFFIX, "")
}

function shortHostname(value: string): string {
  const trimmed = value.trim()
  // "pecan09-101h.lab.example" → "pecan09-101h"; never shorten an IP.
  if (!trimmed || IPV4.test(trimmed)) {
    return trimmed
  }
  return trimmed.split(".")[0] || trimmed
}

/**
 * Display name for a bench: the hostname the bench reports about itself
 * (rack suffixes like "-101h" kept), else the name it was added with, else its
 * address. Use `benchAddress` for the small IP line under it.
 */
export function benchName(machine: BenchNameSource | null | undefined): string {
  const reported = shortHostname(machine?.remote_hostname ?? "")
  if (reported) {
    return reported
  }
  const name = (machine?.name ?? "").trim()
  if (name) {
    return name
  }
  return (
    benchAddress(machine) ||
    shortHostname(machine?.hostname ?? "") ||
    "Unnamed bench"
  )
}

/**
 * Name for a row of GET /fleet/devices. `machines` lets registered benches use
 * their reported hostname; the dashboard's own bench (machine_id null) uses
 * `thisBenchName` (health.hostname) or "This bench".
 */
export function fleetHostName(
  host: Pick<FleetHost, "machine_id" | "name" | "address">,
  machines?: Machine[] | null,
  thisBenchName?: string | null
): string {
  if (!host.machine_id) {
    return shortHostname(thisBenchName ?? "") || "This bench"
  }
  const machine = machines?.find((m) => m.id === host.machine_id)
  return benchName(machine ?? { name: host.name, address: host.address })
}

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

export type BenchStatus =
  | "online"
  | "scanning"
  | "unreachable"
  | "needs_token"
  | "unknown"

export const BENCH_STATUS_LABEL: Record<BenchStatus, string> = {
  online: "Online",
  scanning: "Scanning…",
  unreachable: "Can't reach",
  needs_token: "Needs access token",
  unknown: "Unknown",
}

export const BENCH_STATUS_TONE: Record<BenchStatus, Tone> = {
  online: "ok",
  scanning: "info",
  unreachable: "bad",
  needs_token: "warn",
  unknown: "info",
}

/** Maps Machine.status (and an in-flight scan) to the five bench states. */
export function benchStatus(
  status: MachineStatus | string | null | undefined,
  options: { scanning?: boolean } = {}
): BenchStatus {
  if (options.scanning) {
    return "scanning"
  }
  switch (status) {
    case "reachable":
      return "online"
    case "unreachable":
      return "unreachable"
    case "auth_failed":
      return "needs_token"
    default:
      return "unknown"
  }
}

/** Short badge text for a Machine.status. */
export function machineStatusLabel(status: MachineStatus | string): string {
  return BENCH_STATUS_LABEL[benchStatus(status)]
}

// ---------------------------------------------------------------------------
// Problems: one line that says what to do next
// ---------------------------------------------------------------------------

export type BenchProblem = { tone: Exclude<Tone, "ok">; text: string }

export function unreachableMessage(name: string): string {
  return `Can't reach ${name} — check it's powered on and on the network`
}

export function needsTokenMessage(name: string): string {
  return `${name} needs its access token — enter it in Benches › Edit`
}

export function noDrivesMessage(name: string): string {
  return `No drives found on ${name} — check drives are seated, then scan again`
}

/**
 * Turns an error (detail text, optional HTTP status) for one bench into a
 * one-line, actionable problem. Falls back to the first line of the detail.
 */
export function benchProblemFromError(
  name: string,
  message: string | null | undefined,
  status?: number
): BenchProblem | null {
  const text = (message ?? "").trim()
  const lower = text.toLowerCase()
  if (
    status === 401 ||
    status === 403 ||
    lower.includes("token") ||
    lower.includes("unauthorized") ||
    lower.includes("forbidden")
  ) {
    return { tone: "warn", text: needsTokenMessage(name) }
  }
  if (
    status === 504 ||
    lower.includes("timed out") ||
    lower.includes("timeout")
  ) {
    return {
      tone: "warn",
      text: `${name} took too long to answer — try again, or check it isn't overloaded`,
    }
  }
  if (
    status === 409 ||
    lower.includes("busy") ||
    lower.includes("already running")
  ) {
    return {
      tone: "info",
      text: `${name} is busy with another scan — try again in a minute`,
    }
  }
  if (
    status === 502 ||
    lower.includes("unreachable") ||
    lower.includes("connection refused") ||
    lower.includes("could not connect")
  ) {
    return { tone: "bad", text: unreachableMessage(name) }
  }
  if (!text) {
    return null
  }
  return { tone: "bad", text: text.split("\n")[0] ?? text }
}

/**
 * One-line problem for a bench from its status, last error, and (optionally)
 * whether its last scan found no drives. Null when there is nothing to fix.
 */
export function benchProblem(
  name: string,
  status: MachineStatus | string | null | undefined,
  options: { error?: string | null; noDrives?: boolean } = {}
): BenchProblem | null {
  if (options.error) {
    return benchProblemFromError(name, options.error)
  }
  if (status === "unreachable") {
    return { tone: "bad", text: unreachableMessage(name) }
  }
  if (status === "auth_failed") {
    return { tone: "warn", text: needsTokenMessage(name) }
  }
  if (options.noDrives) {
    return { tone: "info", text: noDrivesMessage(name) }
  }
  return null
}

/** String form of `benchProblemFromError` (older call sites). */
export function describeHostProblem(
  name: string,
  message: string | null | undefined,
  status?: number
): string | null {
  return benchProblemFromError(name, message, status)?.text ?? null
}

/** String form of `benchProblem` without the no-drives case (older call sites). */
export function hostProblemMessage(
  name: string,
  status: MachineStatus | string,
  error?: string | null
): string | null {
  return benchProblem(name, status, { error })?.text ?? null
}

/** Friendly message for a failed request aimed at one bench (scan, check, …). */
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

export function fleetHostProblem(
  host: FleetHost,
  machines?: Machine[] | null,
  thisBenchName?: string | null
): string | null {
  return hostProblemMessage(
    fleetHostName(host, machines, thisBenchName),
    host.status,
    host.error
  )
}
