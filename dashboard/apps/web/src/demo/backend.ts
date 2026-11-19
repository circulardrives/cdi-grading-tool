/**
 * In-browser stand-in for the CDI Health API, used only by the static demo
 * build (VITE_DEMO=1; lib/api.ts imports it lazily). Answers every endpoint
 * the dashboard calls from sample data in ./data, which
 * scripts/generate_demo_data.py makes by running repo fixtures through the
 * real grader. Nothing leaves the browser.
 *
 * Play state (benches added or removed) lives in sessionStorage, so the demo
 * can be poked at and resets when the tab closes; scans, reports and
 * self-tests live in memory and reset on reload.
 */
import filesRaw from "./data/files.json?raw"
import fleetRaw from "./data/fleet.json?raw"
import healthRaw from "./data/health.json?raw"
import historyRaw from "./data/history.json?raw"
import machinesRaw from "./data/machines.json?raw"
import reportsRaw from "./data/reports.json?raw"
import selftestsRaw from "./data/selftests.json?raw"

import type {
  DeviceRecord,
  DiscoverRequest,
  DiscoverResponse,
  FleetDevicesResponse,
  FleetHost,
  HealthResponse,
  HistoryDetail,
  HistorySummary,
  JobResponse,
  Machine,
  MachineCreateRequest,
  MachineUpdateRequest,
  ReportListEntry,
  ReportRequest,
  ScanResponse,
  ScanSummary,
  SelfTestDeviceStatus,
  SelfTestResultEntry,
  SelfTestStartRequest,
  SelfTestStatusResponse,
} from "@/lib/types"

// ---------------------------------------------------------------------------
// Sample data
// ---------------------------------------------------------------------------

type FilesIndex = {
  generated_at: string
  /** machine id (or "all") → drive-list CSV file */
  drives_csv: Record<string, string>
  /** machine id (or "fleet") → { html, csv } report file */
  reports: Record<string, Record<string, string>>
}

/** Timestamp fields shifted so the sample scans look recent. */
const TIME_KEYS = new Set([
  "scanned_at",
  "created_at",
  "updated_at",
  "last_seen_at",
  "last_scan_at",
  "generated_at",
  "scan_timestamp",
])

const files = JSON.parse(filesRaw) as FilesIndex
/** The data was generated "at" files.generated_at; make that "now". */
const SHIFT_MS = Date.now() - Date.parse(files.generated_at)

function shiftTimes<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => shiftTimes(item)) as T
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value)) {
      if (TIME_KEYS.has(key) && typeof item === "string") {
        const time = Date.parse(item)
        out[key] = Number.isNaN(time)
          ? item
          : new Date(time + SHIFT_MS).toISOString()
      } else {
        out[key] = shiftTimes(item)
      }
    }
    return out as T
  }
  return value
}

function load<T>(raw: string): T {
  return shiftTimes(JSON.parse(raw) as T)
}

const health = load<HealthResponse>(healthRaw)
const seedMachines = load<{ machines: Machine[] }>(machinesRaw).machines
const seedFleet = load<FleetDevicesResponse>(fleetRaw)
const seedHistory = load<{
  summaries: HistorySummary[]
  details: Record<string, HistoryDetail>
}>(historyRaw)
const seedReports = load<{ reports: ReportListEntry[] }>(reportsRaw).reports
const seedSelfTests = JSON.parse(selftestsRaw) as {
  benches: Record<string, SelfTestStatusResponse>
}

/** Report / CSV files, loaded only when opened or downloaded. */
const fileLoaders = import.meta.glob<string>("./data/files/*", {
  query: "?raw",
  import: "default",
})

const VERSION = health.version ?? ""
const API_PORT = 8844
/** Fields left out of saved scans (history), like the generator does. */
const HISTORY_DROP_FIELDS = [
  "smartctl_json",
  "smart_attributes",
  "smart_self_tests",
  "nvme_self_test_log",
  "nvme_self_test_history",
  "nvme_error_information_log",
  "nvme_namespaces",
  "ocp_smart_log",
]

// ---------------------------------------------------------------------------
// Demo benches (keyed by address, so a removed bench can be added back)
// ---------------------------------------------------------------------------

type DemoBench = {
  /** Machine id in the sample data (keys the files index). */
  seedId: string
  name: string
  address: string
  scannedAt: string
  devices: DeviceRecord[]
  selfTest: SelfTestStatusResponse
}

function normalizeAddress(address: string | null | undefined): string {
  return String(address ?? "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/\/+$/, "")
    .replace(/:8844$/, "")
}

const benches = new Map<string, DemoBench>()
for (const machine of seedMachines) {
  const host = seedFleet.hosts.find((h) => h.machine_id === machine.id)
  benches.set(normalizeAddress(machine.address), {
    seedId: machine.id,
    name: machine.name,
    address: machine.address,
    scannedAt: host?.scanned_at ?? new Date().toISOString(),
    devices: seedFleet.devices
      .filter((device) => device.machine_id === machine.id)
      .map(
        ({ machine_id: _m, machine_name: _n, host_address: _a, ...rest }) =>
          rest
      ),
    selfTest: seedSelfTests.benches[machine.id] ?? {
      devices: [],
      total: 0,
    },
  })
}

function benchFor(machine: Machine | null | undefined): DemoBench | null {
  return machine
    ? (benches.get(normalizeAddress(machine.address)) ?? null)
    : null
}

// ---------------------------------------------------------------------------
// Registered benches (sessionStorage)
// ---------------------------------------------------------------------------

const MACHINES_KEY = "cdi-demo-machines"

function loadMachines(): Machine[] {
  try {
    const stored = sessionStorage.getItem(MACHINES_KEY)
    if (stored) {
      const parsed = JSON.parse(stored) as unknown
      if (Array.isArray(parsed)) {
        return parsed as Machine[]
      }
    }
  } catch {
    /* storage blocked or corrupt: start from the sample benches */
  }
  return seedMachines.map((machine) => ({ ...machine }))
}

let machines = loadMachines()

function saveMachines(): void {
  try {
    sessionStorage.setItem(MACHINES_KEY, JSON.stringify(machines))
  } catch {
    /* ignore storage failures; the demo keeps working in memory */
  }
}

function machineById(id: string | null | undefined): Machine | null {
  return id ? (machines.find((machine) => machine.id === id) ?? null) : null
}

function sortedMachines(): Machine[] {
  return [...machines].sort((a, b) =>
    a.name.toLowerCase().localeCompare(b.name.toLowerCase())
  )
}

function nowIso(): string {
  return new Date().toISOString()
}

function randomHex(length: number): string {
  let out = ""
  while (out.length < length) {
    out += Math.floor(Math.random() * 16).toString(16)
  }
  return out
}

// ---------------------------------------------------------------------------
// Scans, fleet, history
// ---------------------------------------------------------------------------

const SUMMARY_KEYS = [
  "total",
  "healthy",
  "warning",
  "failed",
  "ungraded",
] as const

/** Same buckets as the API's summary (ReportGenerator._score_bucket). */
function bucketOf(device: DeviceRecord): (typeof SUMMARY_KEYS)[number] {
  const score = Number(device.health_score)
  if (
    device.grading_status === "UNGRADED" ||
    device.health_score == null ||
    !Number.isFinite(score)
  ) {
    return "ungraded"
  }
  if (score >= 75) {
    return "healthy"
  }
  return score >= 40 ? "warning" : "failed"
}

function summarize(devices: DeviceRecord[]): ScanSummary {
  const summary: ScanSummary = {
    total: devices.length,
    healthy: 0,
    warning: 0,
    failed: 0,
    ungraded: 0,
  }
  for (const device of devices) {
    summary[bucketOf(device)] = (summary[bucketOf(device)] ?? 0) + 1
  }
  return summary
}

function scanResponseFor(machine: Machine, bench: DemoBench): ScanResponse {
  return {
    scanned_at: bench.scannedAt,
    summary: summarize(bench.devices),
    devices: bench.devices,
    machine_id: machine.id,
    executed_on: "remote",
    remote_address: machine.address,
  }
}

/** The bench serving this dashboard has no drives in the demo. */
function emptyLocalScan(): ScanResponse {
  return {
    scanned_at: nowIso(),
    summary: summarize([]),
    devices: [],
    machine_id: null,
    executed_on: "local",
  }
}

let historySummaries: HistorySummary[] = [...seedHistory.summaries]
const historyDetails = new Map<string, HistoryDetail>(
  Object.entries(seedHistory.details)
)

function gradeCounts(devices: DeviceRecord[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const device of devices) {
    const grade = String(device.health_grade ?? "?").toUpperCase()
    counts[grade] = (counts[grade] ?? 0) + 1
  }
  return Object.fromEntries(
    Object.entries(counts).sort(([a], [b]) => a.localeCompare(b))
  )
}

function recordHistory(machine: Machine, bench: DemoBench): void {
  const stamp = bench.scannedAt
    .replace(/[-:]/g, "")
    .replace("T", "-")
    .slice(0, 15)
  const devices = bench.devices.map((device) => {
    const slim: Record<string, unknown> = { ...device }
    for (const field of HISTORY_DROP_FIELDS) {
      delete slim[field]
    }
    return slim as DeviceRecord
  })
  const summary: HistorySummary = {
    id: `${stamp}-${randomHex(8)}`,
    scanned_at: bench.scannedAt,
    created_at: bench.scannedAt,
    machine_id: machine.id,
    mock: false,
    device_count: devices.length,
    summary: summarize(devices),
    grades: gradeCounts(devices),
  }
  historySummaries = [summary, ...historySummaries]
  historyDetails.set(summary.id, { ...summary, devices })
}

/** A fresh "scan" of a demo bench: same drives, new timestamps. */
function rescan(machine: Machine, bench: DemoBench): void {
  const scannedAt = nowIso()
  bench.scannedAt = scannedAt
  bench.devices = bench.devices.map((device) => ({
    ...device,
    scan_timestamp: scannedAt,
  }))
  updateMachine(machine.id, {
    status: "reachable",
    last_seen_at: scannedAt,
    last_scan_at: scannedAt,
    last_scan_status: "success",
    last_scan_summary: summarize(bench.devices),
  })
  recordHistory(machine, bench)
}

function unreachable(machine: Machine): string {
  return `Host '${machine.name}' is unreachable at ${machine.address}`
}

function fleetResponse(
  errors: Record<string, string> = {}
): FleetDevicesResponse {
  const hosts: FleetHost[] = []
  const devices: FleetDevicesResponse["devices"] = []
  const totals = summarize([])
  for (const machine of machines.filter((m) => m.address.trim())) {
    const bench = benchFor(machine)
    const host: FleetHost = {
      machine_id: machine.id,
      name: machine.name,
      address: machine.address,
      status: machine.status,
      scanned_at: null,
      summary: null,
      device_count: 0,
      error: errors[machine.id] ?? null,
      executed_on: "remote",
    }
    // A bench added back after removal has no saved scan until it is scanned.
    if (bench && machine.last_scan_at) {
      const summary = summarize(bench.devices)
      host.scanned_at = bench.scannedAt
      host.summary = summary
      host.device_count = bench.devices.length
      for (const key of SUMMARY_KEYS) {
        totals[key] = (totals[key] ?? 0) + (summary[key] ?? 0)
      }
      for (const device of bench.devices) {
        devices.push({
          ...device,
          machine_id: machine.id,
          machine_name: machine.name,
          host_address: machine.address,
        })
      }
    }
    hosts.push(host)
  }
  return { hosts, devices, summary: totals, generated_at: nowIso() }
}

// ---------------------------------------------------------------------------
// Machines
// ---------------------------------------------------------------------------

function updateMachine(id: string, patch: Partial<Machine>): Machine | null {
  let updated: Machine | null = null
  machines = machines.map((machine) => {
    if (machine.id !== id) {
      return machine
    }
    updated = { ...machine, ...patch, updated_at: nowIso() }
    return updated
  })
  saveMachines()
  return updated
}

function createMachine(body: MachineCreateRequest): Machine {
  const now = nowIso()
  const machine: Machine = {
    id: crypto.randomUUID(),
    name: body.name.trim(),
    hostname: body.hostname.trim(),
    address: (body.address ?? "").trim(),
    location: (body.location ?? "").trim(),
    notes: (body.notes ?? "").trim(),
    status: "unknown",
    has_api_token: Boolean(body.api_token?.trim()),
    remote_version: null,
    remote_hostname: null,
    remote_auth: null,
    last_seen_at: null,
    last_scan_at: null,
    last_scan_status: null,
    last_scan_summary: null,
    created_at: now,
    updated_at: now,
  }
  machines = [...machines, machine]
  saveMachines()
  return machine
}

function checkMachine(machine: Machine) {
  const bench = benchFor(machine)
  if (!bench) {
    return {
      machine: updateMachine(machine.id, { status: "unreachable" }) ?? machine,
      health: null,
      error: unreachable(machine),
    }
  }
  const remoteHealth: HealthResponse = {
    status: "ok",
    version: VERSION,
    hostname: bench.name,
    auth_mode: "none",
  }
  const updated = updateMachine(machine.id, {
    status: "reachable",
    last_seen_at: nowIso(),
    remote_version: VERSION,
    remote_hostname: bench.name,
    remote_auth: "none",
  })
  return { machine: updated ?? machine, health: remoteHealth, error: null }
}

function discover(body: DiscoverRequest): DiscoverResponse {
  const subnets = body.subnets?.length
    ? body.subnets
    : body.subnet
      ? [body.subnet]
      : ["192.168.10.0/24"]
  const registered = new Set(machines.map((m) => normalizeAddress(m.address)))
  const found = [...benches.entries()].map(([key, bench]) => {
    const ip = key.split(":")[0] ?? key
    return {
      address: bench.address,
      ip,
      port: API_PORT,
      hostname: bench.name,
      health: {
        status: "ok",
        version: VERSION,
        hostname: bench.name,
        auth_mode: "none" as const,
      },
      cdi_api: true,
      already_registered: registered.has(key),
    }
  })
  return {
    scanned_subnets: subnets,
    port: body.port ?? API_PORT,
    hosts_scanned: 254 * subnets.length,
    open_ports: found.length,
    found,
    duration_ms: 1400,
  }
}

// ---------------------------------------------------------------------------
// Reports and files
// ---------------------------------------------------------------------------

let reports: ReportListEntry[] = [...seedReports]
/** Report filename → sample file behind it. */
const reportFiles = new Map<string, string>(
  seedReports.map((entry) => [entry.filename, entry.filename])
)

function reportStamp(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

function makeReport(body: ReportRequest): Response {
  const format = body.format
  if (format === "pdf") {
    return error(
      400,
      "PDF generation requires WeasyPrint, which the online demo doesn't include"
    )
  }
  let hosts: ReportListEntry["hosts"] = []
  let seedKey = "fleet"
  if (body.source === "history") {
    const ids = [...new Set(body.history_ids ?? [])]
    if (ids.length === 0) {
      return error(400, "history_ids is required for source=history")
    }
    const scans: HistoryDetail[] = []
    for (const id of ids) {
      const detail = historyDetails.get(id)
      if (!detail) {
        return error(404, `Scan history entry not found: ${id.slice(0, 64)}`)
      }
      scans.push(detail)
    }
    hosts = scans.map((scan) => ({
      name: machineById(scan.machine_id)?.name ?? "Removed bench",
      machine_id: scan.machine_id ?? null,
      scanned_at: scan.scanned_at,
      device_count: scan.devices.length,
    }))
    const benchIds = new Set(
      scans.map(
        (scan) => benchFor(machineById(scan.machine_id))?.seedId ?? "fleet"
      )
    )
    seedKey = benchIds.size === 1 ? [...benchIds][0]! : "fleet"
  } else {
    const fleet = fleetResponse()
    if (fleet.devices.length === 0) {
      return error(
        400,
        "No saved scans to report on — run Scan all hosts first"
      )
    }
    hosts = fleet.hosts
      .filter((host) => host.scanned_at)
      .map((host) => ({
        name: host.name,
        machine_id: host.machine_id,
        scanned_at: host.scanned_at,
        device_count: host.device_count,
      }))
  }
  const sample =
    files.reports[seedKey]?.[format] ?? files.reports.fleet?.[format]
  if (!sample) {
    return error(400, "Unsupported report format")
  }
  const filename = `cdi-report-${reportStamp()}-${randomHex(4)}.${format}`
  reportFiles.set(filename, sample)
  const generatedAt = nowIso()
  const devicesCount = hosts.reduce((sum, host) => sum + host.device_count, 0)
  const entry: ReportListEntry = {
    filename,
    format,
    generated_at: generatedAt,
    source: body.source ?? "scan",
    devices_count: devicesCount,
    hosts,
  }
  reports = [entry, ...reports]
  return json({
    ...entry,
    output_file: `/demo/${filename}`,
  })
}

const MEDIA_TYPES: Record<string, string> = {
  html: "text/html; charset=utf-8",
  csv: "text/csv; charset=utf-8",
}

async function fileResponse(
  sample: string,
  filename: string,
  download: boolean
): Promise<Response> {
  const loader = fileLoaders[`./data/files/${sample}`]
  if (!loader) {
    return error(404, `Report not found: ${filename}`)
  }
  const text = await loader()
  const extension = filename.split(".").pop() ?? ""
  return new Response(text, {
    status: 200,
    headers: {
      "Content-Type": MEDIA_TYPES[extension] ?? "application/octet-stream",
      "Content-Disposition": `${download ? "attachment" : "inline"}; filename="${filename}"`,
    },
  })
}

async function drivesCsv(machineId: string | null): Promise<Response> {
  let sample: string | undefined
  let scope = "all-benches"
  if (machineId) {
    const machine = machineById(machineId)
    const bench = benchFor(machine)
    if (!machine || !bench || !machine.last_scan_at) {
      return error(404, "Bench not found or not scanned yet")
    }
    sample = files.drives_csv[bench.seedId]
    scope = machine.name.replace(/[^A-Za-z0-9._-]+/g, "-")
  } else {
    sample = files.drives_csv.all
  }
  if (!sample) {
    return error(404, "Bench not found or not scanned yet")
  }
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, "0")
  const stamp = `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}-${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}`
  return fileResponse(sample, `cdi-drives-${scope}-${stamp}.csv`, true)
}

// ---------------------------------------------------------------------------
// Self-tests: a test runs for a fixed time, then passes
// ---------------------------------------------------------------------------

const TEST_DURATION_MS = { short: 20_000, extended: 45_000 } as const

type RunningTest = {
  machineId: string
  device: string
  testType: "short" | "extended"
  startedAt: number
}

const running = new Map<string, RunningTest>()
const jobs: JobResponse[] = []

function testKey(machineId: string, device: string): string {
  return `${machineId}|${device}`
}

function powerOnHours(bench: DemoBench, device: string): number {
  const record = bench.devices.find((d) => d.dut === device)
  const hours = Number(record?.power_on_hours)
  return Number.isFinite(hours) ? hours : 0
}

function logEntry(
  testType: "short" | "extended",
  resultCode: number,
  hours: number
): SelfTestResultEntry {
  return {
    result_code: resultCode,
    result: resultCode === 0 ? "Success" : "Aborted: Device Self-test command",
    test_type_code: testType === "short" ? 1 : 2,
    test_type: testType === "short" ? "Short" : "Extended",
    completion_time: hours,
  }
}

/** Write a finished (or aborted) test into the bench's self-test log. */
function finishTest(
  bench: DemoBench,
  test: RunningTest,
  aborted: boolean
): void {
  const entry = logEntry(
    test.testType,
    aborted ? 1 : 0,
    powerOnHours(bench, test.device)
  )
  bench.selfTest = {
    ...bench.selfTest,
    devices: bench.selfTest.devices.map((row) =>
      row.device === test.device
        ? {
            ...row,
            status: "No self-test in progress",
            in_progress: false,
            passed: !aborted,
            failed: false,
            aborted,
            last_test_date: new Date(
              aborted
                ? Date.now()
                : test.startedAt + TEST_DURATION_MS[test.testType]
            ).toISOString(),
            latest_result: entry,
            recent_results: [entry, ...(row.recent_results ?? [])].slice(0, 5),
            current_completion: 0,
            current_operation: "No self-test in progress",
            logs_message: null,
          }
        : row
    ),
  }
  running.delete(testKey(test.machineId, test.device))
}

function selfTestStatus(
  machine: Machine,
  bench: DemoBench,
  device: string | null
): SelfTestStatusResponse {
  const now = Date.now()
  for (const test of [...running.values()]) {
    if (
      test.machineId === machine.id &&
      now - test.startedAt >= TEST_DURATION_MS[test.testType]
    ) {
      finishTest(bench, test, false)
    }
  }
  const rows: SelfTestDeviceStatus[] = bench.selfTest.devices
    .filter((row) => !device || row.device === device)
    .map((row) => {
      const test = running.get(testKey(machine.id, row.device ?? ""))
      if (!test) {
        return row
      }
      const percent = Math.min(
        99,
        Math.floor(
          ((now - test.startedAt) / TEST_DURATION_MS[test.testType]) * 100
        )
      )
      const kind = test.testType === "short" ? "Short" : "Extended"
      return {
        ...row,
        status: `Self-test in progress (${percent}%)`,
        in_progress: true,
        passed: false,
        failed: false,
        aborted: false,
        progress_percent: percent,
        current_completion: percent,
        current_operation: `${kind} self-test in progress`,
        logs_message: null,
      }
    })
  return { devices: rows, total: rows.length, machine_id: machine.id }
}

function startSelfTest(
  machine: Machine,
  bench: DemoBench,
  body: SelfTestStartRequest
): JobResponse {
  const testType = body.test_type ?? "short"
  const targets = bench.selfTest.devices
    .map((row) => row.device ?? "")
    .filter((device) => !body.device || device === body.device)
  const now = nowIso()
  const results: SelfTestDeviceStatus[] = targets.map((device) => {
    const key = testKey(machine.id, device)
    const already = running.has(key)
    if (!already) {
      running.set(key, {
        machineId: machine.id,
        device,
        testType,
        startedAt: Date.now(),
      })
    }
    return {
      device,
      test_type: testType,
      supported: true,
      started: true,
      in_progress: true,
      completed: false,
      passed: false,
      failed: false,
      aborted: false,
      status: already ? "already_running" : "started",
      error: null,
      last_test_date: null,
    }
  })
  const job: JobResponse = {
    job_id: crypto.randomUUID(),
    job_type: "selftest",
    status: "completed",
    payload: { ...body },
    created_at: now,
    updated_at: now,
    started_at: now,
    completed_at: now,
    result: {
      devices: results,
      summary: {
        total: results.length,
        started: results.length,
        completed: 0,
        failed_to_start: 0,
      },
    },
    error: null,
    machine_id: machine.id,
  }
  jobs.unshift(job)
  return job
}

// ---------------------------------------------------------------------------
// HTTP plumbing
// ---------------------------------------------------------------------------

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

function error(status: number, detail: string): Response {
  return json({ detail }, status)
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function readBody<T>(init?: RequestInit): Promise<T> {
  if (typeof init?.body !== "string" || !init.body) {
    return {} as T
  }
  try {
    return JSON.parse(init.body) as T
  } catch {
    return {} as T
  }
}

/** Resolves the bench a request names; `null` machine = the dashboard's own bench. */
function remoteBench(
  machineId: string | null
): { machine: Machine; bench: DemoBench } | Response | null {
  if (!machineId) {
    return null
  }
  const machine = machineById(machineId)
  if (!machine) {
    return error(404, "Machine not found")
  }
  const bench = benchFor(machine)
  if (!bench) {
    updateMachine(machine.id, { status: "unreachable" })
    return error(502, unreachable(machine))
  }
  return { machine, bench }
}

async function route(
  method: string,
  path: string,
  query: URLSearchParams,
  init?: RequestInit
): Promise<Response> {
  const segments = path.split("/").filter(Boolean).map(decodeURIComponent)
  const machineParam = query.get("machine_id")

  // --- health, machines, discovery -----------------------------------------
  if (path === "/health") {
    return json(health)
  }
  if (path === "/machines") {
    if (method === "POST") {
      return json(createMachine(await readBody<MachineCreateRequest>(init)))
    }
    return json(sortedMachines())
  }
  if (segments[0] === "machines" && segments[1]) {
    const machine = machineById(segments[1])
    if (!machine) {
      return error(404, "Machine not found")
    }
    if (segments[2] === "check" && method === "POST") {
      await sleep(600)
      return json(checkMachine(machine))
    }
    if (method === "PATCH") {
      const body = await readBody<MachineUpdateRequest>(init)
      const patch: Partial<Machine> = {}
      for (const field of [
        "name",
        "hostname",
        "address",
        "location",
        "notes",
        "status",
      ] as const) {
        const value = body[field]
        if (typeof value === "string") {
          ;(patch as Record<string, string>)[field] = value.trim()
        }
      }
      if (body.api_token != null) {
        patch.has_api_token = Boolean(body.api_token.trim())
      }
      return json(updateMachine(machine.id, patch))
    }
    if (method === "DELETE") {
      machines = machines.filter((m) => m.id !== machine.id)
      saveMachines()
      return json({ deleted: true })
    }
    return json(machine)
  }
  if (path === "/discover") {
    await sleep(1400)
    return json(
      discover(method === "POST" ? await readBody<DiscoverRequest>(init) : {})
    )
  }

  // --- drives and scans -----------------------------------------------------
  if (path === "/fleet/devices") {
    return json(fleetResponse())
  }
  if (path === "/fleet/devices.csv") {
    return drivesCsv(
      machineParam && machineParam !== "local" ? machineParam : null
    )
  }
  if (path === "/fleet/scan" && method === "POST") {
    await sleep(2500)
    const errors: Record<string, string> = {}
    for (const machine of machines.filter((m) => m.address.trim())) {
      const bench = benchFor(machine)
      if (bench) {
        rescan(machine, bench)
      } else {
        updateMachine(machine.id, { status: "unreachable" })
        errors[machine.id] = unreachable(machine)
      }
    }
    return json(fleetResponse(errors))
  }
  if (path === "/devices" || (path === "/scan" && method === "POST")) {
    const machineId =
      path === "/scan"
        ? ((await readBody<{ machine_id?: string }>(init)).machine_id ?? null)
        : machineParam
    const target = remoteBench(machineId)
    if (target instanceof Response) {
      return target
    }
    if (!target) {
      return json(emptyLocalScan())
    }
    if (path === "/scan" || query.get("refresh") === "true") {
      await sleep(2000)
      rescan(target.machine, target.bench)
    } else if (!target.machine.last_scan_at) {
      return error(404, "No scan cached for this host")
    }
    return json(
      scanResponseFor(
        machineById(target.machine.id) ?? target.machine,
        target.bench
      )
    )
  }

  // --- history --------------------------------------------------------------
  if (path === "/history") {
    if (method === "DELETE") {
      const deleted = historySummaries.length
      historySummaries = []
      historyDetails.clear()
      return json({ deleted })
    }
    const limit = Math.min(
      Math.max(Number(query.get("limit") ?? 100) || 100, 1),
      500
    )
    const offset = Math.max(Number(query.get("offset") ?? 0) || 0, 0)
    const rows = historySummaries.filter(
      (entry) => !machineParam || entry.machine_id === machineParam
    )
    return json(rows.slice(offset, offset + limit))
  }
  if (segments[0] === "history" && segments[1]) {
    const id = segments[1]
    const detail = historyDetails.get(id)
    if (!detail) {
      return error(404, "Scan history entry not found")
    }
    if (method === "DELETE") {
      historyDetails.delete(id)
      historySummaries = historySummaries.filter((entry) => entry.id !== id)
      return json({ deleted: true, id })
    }
    return json(detail)
  }

  // --- reports --------------------------------------------------------------
  if (path === "/reports") {
    if (method === "POST") {
      await sleep(900)
      return makeReport(await readBody<ReportRequest>(init))
    }
    return json(reports)
  }
  if (segments[0] === "reports" && segments[1]) {
    const filename = segments[1]
    const sample = reportFiles.get(filename)
    if (!sample) {
      return error(404, `Report not found: ${filename}`)
    }
    return fileResponse(sample, filename, query.get("download") === "true")
  }

  // --- self-tests and jobs ----------------------------------------------------
  if (path === "/selftests" && method === "POST") {
    const body = await readBody<SelfTestStartRequest>(init)
    const target = remoteBench(body.machine_id ?? null)
    if (target instanceof Response) {
      return target
    }
    if (!target) {
      return error(400, "No NVMe drives on this bench")
    }
    return json(startSelfTest(target.machine, target.bench, body))
  }
  if (path === "/selftests/status") {
    const target = remoteBench(machineParam)
    if (target instanceof Response) {
      return target
    }
    if (!target) {
      return json({ devices: [], total: 0, machine_id: null })
    }
    return json(
      selfTestStatus(target.machine, target.bench, query.get("device"))
    )
  }
  if (path === "/selftests/abort" && method === "POST") {
    const body = await readBody<{ device?: string; machine_id?: string }>(init)
    const target = remoteBench(body.machine_id ?? null)
    if (target instanceof Response) {
      return target
    }
    const test = target
      ? running.get(testKey(target.machine.id, body.device ?? ""))
      : undefined
    if (!target || !test) {
      return error(400, "Abort failed")
    }
    finishTest(target.bench, test, true)
    return json({
      device: body.device,
      aborted: true,
      machine_id: target.machine.id,
    })
  }
  if (path === "/jobs") {
    return json(
      jobs.filter((job) => (job.machine_id ?? null) === (machineParam ?? null))
    )
  }
  if (segments[0] === "jobs" && segments[1]) {
    const job = jobs.find((entry) => entry.job_id === segments[1])
    return job ? json(job) : error(404, "Job not found")
  }

  return error(404, "Not Found")
}

/**
 * `fetch` replacement for API calls in the demo build. Accepts the same
 * arguments lib/api.ts passes to `fetch` (paths under the API base URL).
 */
export async function demoFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const url = new URL(
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url,
    window.location.origin
  )
  const method = (init?.method ?? "GET").toUpperCase()
  const match = /\/api\/v1(\/.*)$/.exec(url.pathname)
  if (!match) {
    return error(404, "Not Found")
  }
  // A beat of latency so loading states look like the real thing.
  await sleep(120)
  return route(method, match[1] ?? "/", url.searchParams, init)
}
