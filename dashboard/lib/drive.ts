export type BadgeTone = "healthy" | "warning" | "failed" | "outline";

export function toNum(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function toText(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  if (typeof value === "string" && value.trim() === "") {
    return fallback;
  }
  return String(value);
}

export function formatNumber(value: unknown, suffix = "", digits = 0): string {
  const numeric = toNum(value);
  if (numeric === null) {
    return "-";
  }
  return `${numeric.toFixed(digits)}${suffix}`;
}

export function healthTone(score?: number): BadgeTone {
  if (score === undefined || score === null) {
    return "outline";
  }
  if (score >= 75) {
    return "healthy";
  }
  if (score >= 40) {
    return "warning";
  }
  return "failed";
}

export function protocolTone(protocol: string): BadgeTone {
  const upper = protocol.toUpperCase();
  if (upper === "NVME") {
    return "healthy";
  }
  if (upper === "SCSI") {
    return "warning";
  }
  return "outline";
}

export function getDeductions(device: Record<string, unknown>): Array<Record<string, unknown>> {
  const raw = device.deductions;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((item): item is Record<string, unknown> => !!item && typeof item === "object");
}

export function buildErrorSummary(device: Record<string, unknown>): string {
  const reallocated = toNum(device.reallocated_sectors) ?? 0;
  const pending = toNum(device.pending_sectors) ?? 0;
  const offline = toNum(device.offline_uncorrectable_sectors) ?? 0;
  const media = toNum(device.media_errors) ?? 0;
  const parts: string[] = [];

  if (reallocated > 0) {
    parts.push(`R:${reallocated}`);
  }
  if (pending > 0) {
    parts.push(`P:${pending}`);
  }
  if (offline > 0) {
    parts.push(`U:${offline}`);
  }
  if (media > 0) {
    parts.push(`M:${media}`);
  }

  return parts.length > 0 ? parts.join(", ") : "0";
}

export function telemetryRows(device: Record<string, unknown>): Array<{ label: string; value: string }> {
  return [
    { label: "Device", value: toText(device.dut) },
    { label: "Model", value: toText(device.model_number) },
    { label: "Serial", value: toText(device.serial_number) },
    { label: "Protocol", value: toText(device.transport_protocol) },
    { label: "Firmware", value: toText(device.firmware_revision) },
    { label: "Capacity", value: `${formatNumber(device.gibibytes, " GiB", 1)} / ${formatNumber(device.terabytes, " TB", 2)}` },
    { label: "Power-On Hours", value: toText(device.power_on_hours) },
    { label: "Power Cycles", value: formatNumber(device.power_cycle_count) },
    { label: "SMART Status", value: toText(device.smart_status, "Unknown") },
    { label: "Health Score", value: toText(device.health_score) },
    { label: "Health Grade", value: toText(device.health_grade, toText(device.cdi_grade)) },
    { label: "Certified", value: toText(device.is_certified ?? device.cdi_certified, "false") },
    { label: "Reallocated", value: formatNumber(device.reallocated_sectors) },
    { label: "Pending", value: formatNumber(device.pending_sectors) },
    { label: "Offline Uncorrectable", value: formatNumber(device.offline_uncorrectable_sectors) },
    { label: "Media Errors", value: formatNumber(device.media_errors) },
    { label: "Critical Warning", value: formatNumber(device.critical_warning) },
    { label: "Percent Used", value: formatNumber(device.percentage_used, "%") },
    { label: "Data Written", value: formatNumber(device.data_written_tb, " TB", 2) },
    { label: "Current Temp", value: formatNumber(device.current_temperature, " C") },
    { label: "Highest Temp", value: formatNumber(device.highest_temperature, " C") },
    { label: "Max Temp", value: formatNumber(device.maximum_temperature, " C") },
    { label: "Self-Test Failures", value: formatNumber(device.nvme_self_test_failed_count) }
  ];
}
