import { appConfig } from "@/lib/config"
import type {
  DiscoverRequest,
  DiscoverResponse,
  HealthResponse,
  JobResponse,
  Machine,
  MachineCreateRequest,
  MachineUpdateRequest,
  ReportRequest,
  ReportResponse,
  ScanRequest,
  ScanResponse,
  SelfTestStartRequest,
  SelfTestStatusResponse,
} from "@/lib/types"

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

function formatValidationLocation(loc: unknown): string {
  if (!Array.isArray(loc)) {
    return ""
  }
  const parts = loc
    .filter((part) => part !== "body" && part !== "query" && part !== "path")
    .map(String)
  return parts.length > 0 ? parts.join(".") : ""
}

function normalizeErrorDetail(detail: unknown): string | null {
  if (detail == null) {
    return null
  }
  if (typeof detail === "string") {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") {
          return item
        }
        if (item && typeof item === "object") {
          const entry = item as { msg?: unknown; loc?: unknown; message?: unknown }
          const msg =
            typeof entry.msg === "string"
              ? entry.msg
              : typeof entry.message === "string"
                ? entry.message
                : null
          if (!msg) {
            return null
          }
          const location = formatValidationLocation(entry.loc)
          return location ? `${location}: ${msg}` : msg
        }
        return null
      })
      .filter((msg): msg is string => Boolean(msg))
    return messages.length > 0 ? messages.join("; ") : null
  }
  if (typeof detail === "object") {
    const entry = detail as { msg?: unknown; message?: unknown }
    if (typeof entry.msg === "string") {
      return entry.msg
    }
    if (typeof entry.message === "string") {
      return entry.message
    }
    try {
      return JSON.stringify(detail)
    } catch {
      return null
    }
  }
  return String(detail)
}

async function parseErrorMessage(response: Response): Promise<string> {
  let message = `Request failed (${response.status})`
  try {
    const payload: { detail?: unknown } = await response.json()
    const normalized = normalizeErrorDetail(payload.detail)
    if (normalized) {
      message = normalized
    }
  } catch {
    /* ignore non-json errors */
  }
  return message
}

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("Accept", "application/json")

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  if (appConfig.apiToken) {
    headers.set("X-API-Token", appConfig.apiToken)
  }

  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    throw new ApiError(await parseErrorMessage(response), response.status)
  }

  const data: T = await response.json()
  return data
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health")
}

export function getDevices(
  refresh = false,
  machineId?: string | null
): Promise<ScanResponse> {
  const params = new URLSearchParams()
  if (refresh) {
    params.set("refresh", "true")
  }
  if (machineId) {
    params.set("machine_id", machineId)
  }
  const query = params.toString() ? `?${params.toString()}` : ""
  return request<ScanResponse>(`/api/v1/devices${query}`)
}

export function scanDevices(body: ScanRequest): Promise<ScanResponse> {
  return request<ScanResponse>("/api/v1/scan", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function generateReport(body: ReportRequest): Promise<ReportResponse> {
  return request<ReportResponse>("/api/v1/reports", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function startSelfTest(
  body: SelfTestStartRequest
): Promise<JobResponse> {
  return request<JobResponse>("/api/v1/selftests", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function getSelfTestStatus(
  device?: string
): Promise<SelfTestStatusResponse> {
  const query = device ? `?device=${encodeURIComponent(device)}` : ""
  return request<SelfTestStatusResponse>(`/api/v1/selftests/status${query}`)
}

export function abortSelfTest(
  device: string
): Promise<{ device: string; aborted: boolean }> {
  return request<{ device: string; aborted: boolean }>(
    "/api/v1/selftests/abort",
    {
      method: "POST",
      body: JSON.stringify({ device }),
    }
  )
}

export function getJob(jobId: string): Promise<JobResponse> {
  return request<JobResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}`)
}

export function listJobs(): Promise<JobResponse[]> {
  return request<JobResponse[]>("/api/v1/jobs")
}

export function listMachines(): Promise<Machine[]> {
  return request<Machine[]>("/api/v1/machines")
}

export function createMachine(body: MachineCreateRequest): Promise<Machine> {
  return request<Machine>("/api/v1/machines", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateMachine(
  machineId: string,
  body: MachineUpdateRequest
): Promise<Machine> {
  return request<Machine>(`/api/v1/machines/${encodeURIComponent(machineId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function deleteMachine(machineId: string): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(
    `/api/v1/machines/${encodeURIComponent(machineId)}`,
    { method: "DELETE" }
  )
}

export function discoverHosts(body: DiscoverRequest = {}): Promise<DiscoverResponse> {
  return request<DiscoverResponse>("/api/v1/discover", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function reportFilename(outputFile: string): string {
  const parts = outputFile.split(/[/\\]/)
  return parts[parts.length - 1] || outputFile
}

async function fetchReportBlob(
  filename: string,
  download = false
): Promise<Blob> {
  const query = download ? "?download=true" : ""
  const headers = new Headers()
  headers.set("Accept", "*/*")

  if (appConfig.apiToken) {
    headers.set("X-API-Token", appConfig.apiToken)
  }

  const response = await fetch(
    `${appConfig.apiBaseUrl}/api/v1/reports/${encodeURIComponent(filename)}${query}`,
    { headers }
  )

  if (!response.ok) {
    throw new ApiError(await parseErrorMessage(response), response.status)
  }

  return response.blob()
}

export async function openReportFile(filename: string): Promise<void> {
  const blob = await fetchReportBlob(filename, false)
  const url = URL.createObjectURL(blob)
  window.open(url, "_blank", "noopener,noreferrer")
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

export async function downloadReportFile(filename: string): Promise<void> {
  const blob = await fetchReportBlob(filename, true)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export { ApiError }
