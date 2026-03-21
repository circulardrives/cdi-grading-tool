export type HealthResponse = {
  status: string;
  is_root: boolean;
  allow_non_root_mode: boolean;
  api_token_enabled: boolean;
  missing_required_tools: string[];
  message?: string | null;
};

export type ScanSummary = {
  total: number;
  healthy: number;
  warning: number;
  failed: number;
};

export type ScanResponse = {
  scanned_at: string;
  summary: ScanSummary;
  devices: DeviceRecord[];
};

export type DeviceRecord = {
  dut?: string;
  model_number?: string;
  serial_number?: string;
  transport_protocol?: string;
  gibibytes?: number;
  power_on_hours?: number | string;
  health_score?: number;
  health_grade?: string;
  health_status?: string;
  percentage_used?: number;
  media_errors?: number;
  critical_warning?: number;
  [key: string]: unknown;
};

export type SelfTestStartPayload = {
  device?: string | null;
  test_type: "short" | "extended";
  wait: boolean;
  poll_interval_seconds: number;
  timeout_seconds: number;
};

export type JobResponse = {
  job_id: string;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed";
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
};

export type SelfTestStatusResponse = {
  total: number;
  devices: Array<{
    device: string;
    supported: boolean;
    status: string;
    in_progress: boolean;
    passed: boolean;
    failed: boolean;
    aborted: boolean;
    last_test_date?: string | null;
    error?: string | null;
  }>;
};

export type ReportResponse = {
  generated_at: string;
  output_file: string;
  format: "html" | "pdf";
  devices_count: number;
};

async function cdiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/cdi${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `CDI API request failed (${response.status})`);
  }

  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return cdiRequest<HealthResponse>("/api/v1/health", { method: "GET" });
}

export function scanDevices(payload: {
  ignore_ata: boolean;
  ignore_nvme: boolean;
  ignore_scsi: boolean;
  device?: string;
  mock_data?: string;
  mock_file?: string;
}): Promise<ScanResponse> {
  return cdiRequest<ScanResponse>("/api/v1/scan", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function startSelfTest(payload: SelfTestStartPayload): Promise<JobResponse> {
  return cdiRequest<JobResponse>("/api/v1/selftests", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getJob(jobId: string): Promise<JobResponse> {
  return cdiRequest<JobResponse>(`/api/v1/jobs/${jobId}`, { method: "GET" });
}

export function getJobs(): Promise<JobResponse[]> {
  return cdiRequest<JobResponse[]>("/api/v1/jobs", { method: "GET" });
}

export function getSelfTestStatus(device?: string): Promise<SelfTestStatusResponse> {
  const qs = device ? `?device=${encodeURIComponent(device)}` : "";
  return cdiRequest<SelfTestStatusResponse>(`/api/v1/selftests/status${qs}`, { method: "GET" });
}

export function abortSelfTest(device: string): Promise<{ device: string; aborted: boolean }> {
  return cdiRequest<{ device: string; aborted: boolean }>("/api/v1/selftests/abort", {
    method: "POST",
    body: JSON.stringify({ device })
  });
}

export function generateReport(payload: {
  format: "html" | "pdf";
  output_file?: string;
  ignore_ata: boolean;
  ignore_nvme: boolean;
  ignore_scsi: boolean;
  device?: string;
  mock_data?: string;
  mock_file?: string;
}): Promise<ReportResponse> {
  return cdiRequest<ReportResponse>("/api/v1/reports", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
