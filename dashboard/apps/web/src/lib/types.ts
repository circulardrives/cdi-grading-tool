export type ScoreDeduction = {
  reason?: string
  points?: number
  severity?: string
  field?: string
  value?: unknown
  threshold?: unknown
}

export type ScanSummary = {
  total: number
  healthy: number
  warning: number
  failed: number
}

export type DeviceRecord = {
  dut?: string
  serial_number?: string
  model_number?: string
  vendor?: string
  transport_protocol?: string
  media_type?: string
  interface_link?: string | Record<string, unknown>
  transport_version?: string
  transport_revision?: string
  report_category?: string
  gibibytes?: number
  capacity?: number | string
  bytes?: number | string
  firmware_revision?: string
  form_factor?: string
  rotation_rate?: string | number
  smart_status?: string
  power_on_hours?: number | string
  power_cycle_count?: number | string
  load_cycle_count?: number | string
  start_stop_count?: number | string
  current_temperature?: number | string
  highest_temperature?: number | string
  maximum_temperature?: number | string
  reallocated_sectors?: number | string
  pending_sectors?: number | string
  pending_reallocated_sectors?: number | string
  uncorrectable_errors?: number | string
  offline_uncorrectable_sectors?: number | string
  non_medium_errors?: number | string
  grown_defects?: number | string
  percentage_used?: number | string
  available_spare?: number | string
  critical_warning?: number | string
  media_errors?: number | string
  data_written_tb?: number | string
  nvme_self_test_failed_count?: number | string
  ssd_percentage_used_endurance?: number | string
  health_score?: number
  health_grade?: string
  health_status?: string
  is_certified?: boolean
  deductions?: ScoreDeduction[]
  health_deductions?: ScoreDeduction[]
  smart_attributes?: unknown
  nvme_smart_health_information_log?: Record<string, unknown>
  ocp_smart_log?: Record<string, unknown>
}

export type ScanResponse = {
  scanned_at: string
  summary: ScanSummary
  devices: DeviceRecord[]
}

export type HealthResponse = {
  status: string
  is_root: boolean
  allow_non_root_mode: boolean
  api_token_enabled: boolean
  missing_required_tools: string[]
  weasyprint_available: boolean
  message?: string | null
}

export type ScanRequest = {
  ignore_ata?: boolean
  ignore_nvme?: boolean
  ignore_scsi?: boolean
  device?: string
  config?: string
  mock_data?: string
  mock_file?: string
  machine_id?: string
}

export type ReportRequest = {
  format: "html" | "pdf" | "csv"
  output_file?: string
  ignore_ata?: boolean
  ignore_nvme?: boolean
  ignore_scsi?: boolean
  device?: string
  config?: string
  mock_data?: string
  mock_file?: string
}

export type ReportResponse = {
  generated_at: string
  output_file: string
  filename: string
  format: "html" | "pdf" | "csv"
  devices_count: number
}

export type ReportHistoryEntry = ReportResponse & {
  id: string
}

export type ManualMachine = {
  id: string
  name: string
  hostname: string
  location: string
  notes: string
  createdAt: string
}

export type MachineScanSummary = {
  total: number
  healthy: number
  warning: number
  failed: number
}

export type Machine = {
  id: string
  name: string
  hostname: string
  address: string
  location: string
  notes: string
  status: "unknown" | "reachable" | "unreachable"
  last_seen_at?: string | null
  last_scan_at?: string | null
  last_scan_status?: "success" | "failed" | null
  last_scan_summary?: MachineScanSummary | null
  created_at: string
  updated_at: string
}

export type MachineCreateRequest = {
  name: string
  hostname: string
  address?: string
  location?: string
  notes?: string
}

export type MachineUpdateRequest = Partial<MachineCreateRequest> & {
  status?: Machine["status"]
}

export type DriveClass =
  | "SATA HDD"
  | "SAS HDD"
  | "SATA SSD"
  | "SAS SSD"
  | "NVMe SSD"
  | "Other"

export type DriveViewMode = "simple" | "detailed"

export type DriveColumn = {
  id: string
  label: string
  getValue: (device: DeviceRecord) => string | number
  mono?: boolean
}

export type SelfTestStartRequest = {
  device?: string
  test_type?: "short" | "extended"
  wait?: boolean
  poll_interval_seconds?: number
  timeout_seconds?: number
}

export type SelfTestResultEntry = {
  result_code?: number
  result?: string
  test_type_code?: number
  test_type?: string
  completion_time?: number
}

export type SelfTestDeviceStatus = {
  device?: string
  supported?: boolean
  status?: string
  in_progress?: boolean
  passed?: boolean
  failed?: boolean
  aborted?: boolean
  started?: boolean
  completed?: boolean
  test_type?: string
  error?: string | null
  last_test_date?: string | null
  progress_percent?: number | null
  current_completion?: number | null
  current_operation?: string | number | null
  latest_result?: SelfTestResultEntry | null
  recent_results?: SelfTestResultEntry[]
  logs_message?: string | null
}

export type SelfTestStatusResponse = {
  devices: SelfTestDeviceStatus[]
  total: number
}

export type JobResponse = {
  job_id: string
  job_type: string
  status: string
  payload: Record<string, unknown>
  created_at: string
  updated_at: string
  started_at?: string | null
  completed_at?: string | null
  result?: {
    devices?: SelfTestDeviceStatus[]
    summary?: Record<string, number>
  } | null
  error?: string | null
}

export type DiscoverRequest = {
  subnet?: string
  subnets?: string[]
  port?: number
  timeout_seconds?: number
  probe_token?: string
}

export type DiscoveredHost = {
  address: string
  ip: string
  port: number
  hostname?: string | null
  health?: HealthResponse | null
  cdi_api: boolean
  already_registered: boolean
}

export type DiscoverResponse = {
  scanned_subnets: string[]
  port: number
  hosts_scanned: number
  open_ports: number
  found: DiscoveredHost[]
  duration_ms: number
}
