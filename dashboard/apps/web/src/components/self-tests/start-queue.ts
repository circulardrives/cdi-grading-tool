/**
 * Starts self-tests one drive at a time, per bench.
 *
 * The API takes ONE `device` per start request (leaving it out means every
 * drive), and a bench only accepts the next start once the previous one has
 * reached the drive. So each selected drive gets its own request, sent in
 * order; the rest wait. The queue lives outside React so it keeps going if
 * the page is left or the bench picker changes.
 */
import { useSyncExternalStore } from "react"
import { toast } from "sonner"

import { ApiError, getJob, startSelfTest } from "@/lib/api"
import { describeRequestError } from "@/components/ui-cdi"
import {
  StaleBenchApiError,
  startFailureReason,
  type TestType,
} from "@/components/self-tests/self-test-format"

export type QueuedDrive = { testType: TestType; phase: "waiting" | "starting" }

export type BenchQueue = {
  /** Drives waiting for their start request, in order (controller paths). */
  pending: ReadonlyMap<string, QueuedDrive>
  /** Drives whose start failed, with a plain reason. Cleared on the next start. */
  failures: ReadonlyMap<string, string>
  /** Test type we started per drive, for the label until the drive reports it. */
  started: ReadonlyMap<string, TestType>
  /** Last time a start went through (ms), for "keep polling a little longer". */
  lastStartAt: number
}

const EMPTY: BenchQueue = {
  pending: new Map(),
  failures: new Map(),
  started: new Map(),
  lastStartAt: 0,
}

const queues = new Map<string, BenchQueue>()
const draining = new Set<string>()
const listeners = new Set<() => void>()

export function benchKey(machineId: string | null): string {
  return machineId ?? "local"
}

function read(key: string): BenchQueue {
  return queues.get(key) ?? EMPTY
}

function update(key: string, change: (draft: BenchQueue) => BenchQueue) {
  queues.set(key, change(read(key)))
  for (const listener of listeners) {
    listener()
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Queue state for one bench (re-renders on every change). */
export function useBenchQueue(machineId: string | null): BenchQueue {
  const key = benchKey(machineId)
  return useSyncExternalStore(
    subscribe,
    () => read(key),
    () => EMPTY
  )
}

const sleep = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms))

/** Busy (another start or scan on the bench) and saturated answers are retried. */
const RETRY_STATUSES = new Set([409, 503])
const MAX_START_ATTEMPTS = 8
const RETRY_DELAY_MS = 2000
const JOB_POLL_MS = 1000
const JOB_WAIT_MS = 60_000

/** Errors that mean the whole bench is out of reach, not just one drive. */
function isBenchLevel(error: unknown): boolean {
  if (error instanceof StaleBenchApiError) {
    return true
  }
  if (error instanceof ApiError) {
    return [401, 403, 502, 504].includes(error.status)
  }
  return error instanceof TypeError // network failure
}

type StartOutcome = { ok: true } | { ok: false; reason: string }

async function startOne(
  machineId: string | null,
  benchName: string,
  device: string,
  testType: TestType
): Promise<StartOutcome> {
  let job
  for (let attempt = 1; ; attempt += 1) {
    try {
      job = await startSelfTest({
        device,
        test_type: testType,
        wait: false,
        ...(machineId ? { machine_id: machineId } : {}),
      })
      break
    } catch (error) {
      if (
        error instanceof ApiError &&
        RETRY_STATUSES.has(error.status) &&
        attempt < MAX_START_ATTEMPTS
      ) {
        await sleep(RETRY_DELAY_MS)
        continue
      }
      throw error
    }
  }
  if (machineId && job.machine_id === undefined) {
    throw new StaleBenchApiError(benchName)
  }

  // The job finishes as soon as the drive has the start command.
  const deadline = Date.now() + JOB_WAIT_MS
  while (job.status !== "completed" && job.status !== "failed") {
    if (Date.now() > deadline) {
      // Still going; the status poll will show what the drive does.
      return { ok: true }
    }
    await sleep(JOB_POLL_MS)
    job = await getJob(job.job_id, machineId)
  }
  if (job.status === "failed") {
    return { ok: false, reason: startFailureReason(null, job.error) }
  }
  const entry =
    job.result?.devices?.find((d) => d.device === device) ??
    job.result?.devices?.[0]
  if (!entry || entry.started) {
    return { ok: true }
  }
  return { ok: false, reason: startFailureReason(entry.status, entry.error) }
}

type StartOptions = {
  machineId: string | null
  benchName: string
  devices: string[]
  testType: TestType
  /** Called after each drive, so the page can refresh the bench's status. */
  onProgress?: () => void
}

/** Queue a test on each drive and start them one by one. */
export function queueSelfTests({
  machineId,
  benchName,
  devices,
  testType,
  onProgress,
}: StartOptions) {
  const key = benchKey(machineId)
  update(key, (queue) => {
    const pending = new Map(queue.pending)
    const failures = new Map(queue.failures)
    for (const device of devices) {
      if (!pending.has(device)) {
        pending.set(device, { testType, phase: "waiting" })
      }
      failures.delete(device)
    }
    return { ...queue, pending, failures }
  })
  if (!draining.has(key)) {
    void drain(key, machineId, benchName, onProgress)
  }
}

async function drain(
  key: string,
  machineId: string | null,
  benchName: string,
  onProgress?: () => void
) {
  draining.add(key)
  const counts = { short: 0, extended: 0 }
  let failed = 0
  let benchError: string | null = null
  try {
    for (;;) {
      const next = read(key).pending.entries().next()
      if (next.done) {
        break
      }
      const [device, { testType }] = next.value
      update(key, (queue) => {
        const pending = new Map(queue.pending)
        pending.set(device, { testType, phase: "starting" })
        return { ...queue, pending }
      })

      let outcome: StartOutcome
      try {
        outcome = await startOne(machineId, benchName, device, testType)
      } catch (error) {
        const reason =
          error instanceof StaleBenchApiError
            ? error.message
            : describeRequestError(
                error,
                benchName,
                `Couldn't reach ${benchName} to start the test — try again`
              )
        outcome = { ok: false, reason }
        if (isBenchLevel(error)) {
          benchError = reason
        }
      }

      // A bench we can't reach fails everything still waiting, with the same line.
      const abandoned = benchError
        ? [...read(key).pending.keys()].filter((other) => other !== device)
        : []
      failed += abandoned.length
      update(key, (queue) => {
        const pending = new Map(queue.pending)
        const failures = new Map(queue.failures)
        const started = new Map(queue.started)
        pending.delete(device)
        if (outcome.ok) {
          started.set(device, testType)
        } else {
          failures.set(device, outcome.reason)
        }
        for (const other of abandoned) {
          pending.delete(other)
          failures.set(other, benchError ?? "")
        }
        return {
          pending,
          failures,
          started,
          lastStartAt: outcome.ok ? Date.now() : queue.lastStartAt,
        }
      })
      if (outcome.ok) {
        counts[testType] += 1
      } else {
        failed += 1
      }
      onProgress?.()
    }
  } finally {
    draining.delete(key)
  }

  const startedTotal = counts.short + counts.extended
  const kind =
    counts.extended === 0
      ? "Short test"
      : counts.short === 0
        ? "Extended test"
        : "Self-test"
  const drives = (n: number) => `${n} drive${n === 1 ? "" : "s"}`
  if (benchError && startedTotal === 0) {
    toast.error(benchError)
  } else if (failed === 0) {
    toast.success(`${kind} started on ${drives(startedTotal)} on ${benchName}`)
  } else if (startedTotal === 0) {
    toast.error(
      `Couldn't start the test on ${failed === 1 ? "the drive" : drives(failed)} on ${benchName} — see the drive list`
    )
  } else {
    toast.warning(
      `${kind} started on ${startedTotal} of ${drives(startedTotal + failed)} on ${benchName} — ${failed} couldn't start`
    )
  }
}
