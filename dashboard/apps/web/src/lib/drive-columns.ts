import type { DeviceRecord, DriveClass, DriveColumn } from "@/lib/types"

export function serialLabel(device: DeviceRecord): string {
  const serial = String(device.serial_number ?? "").trim()
  return serial || "—"
}

export function formatCapacity(device: DeviceRecord): string {
  if (device.gibibytes != null) {
    return `${device.gibibytes} GiB`
  }
  if (device.capacity != null && device.capacity !== "") {
    return String(device.capacity)
  }
  if (device.bytes != null && device.bytes !== "") {
    return String(device.bytes)
  }
  return "—"
}

export function formatDeductionsShort(device: DeviceRecord): string {
  const deductions = device.health_deductions ?? device.deductions
  if (!deductions?.length) {
    return "—"
  }

  return deductions
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      const reason = entry.reason ?? "Deduction"
      const points =
        entry.points != null ? ` [-${entry.points}]` : ""
      if (entry.threshold != null && entry.value != null) {
        return `${reason}: ${entry.value} (threshold: ${entry.threshold})${points}`
      }
      return `${reason}${points}`
    })
    .join(" | ")
}

function field(device: DeviceRecord, key: keyof DeviceRecord): string {
  const value = device[key]
  if (value == null || value === "") {
    return "—"
  }
  return String(value)
}

export function formatInterfaceLink(device: DeviceRecord): string {
  const value = device.interface_link
  if (value == null || value === "") {
    return "—"
  }
  if (typeof value === "string") {
    return value
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>
    if (typeof record.name === "string" && record.name.trim()) {
      return record.name.trim()
    }
    if (typeof record.value === "string" && record.value.trim()) {
      return record.value.trim()
    }
    const parts = Object.entries(record)
      .filter(([, entry]) => entry != null && entry !== "")
      .slice(0, 3)
      .map(([key, entry]) => `${key}: ${entry}`)
    return parts.length ? parts.join(", ") : "—"
  }
  return String(value)
}

function pendingSectors(device: DeviceRecord): string {
  if (device.pending_sectors != null) {
    return String(device.pending_sectors)
  }
  if (device.pending_reallocated_sectors != null) {
    return String(device.pending_reallocated_sectors)
  }
  return "—"
}

function smartAttributesSummary(device: DeviceRecord): string {
  const attrs = device.smart_attributes
  if (!attrs) {
    return "—"
  }
  if (Array.isArray(attrs)) {
    return `${attrs.length} attribute(s)`
  }
  return "Available"
}

function nvmeLogField(device: DeviceRecord, key: string): string {
  const log = device.nvme_smart_health_information_log
  if (!log || log[key] == null) {
    return "—"
  }
  return String(log[key])
}

const gradingColumns: DriveColumn[] = [
  {
    id: "health_score",
    label: "Health score",
    getValue: (device) => device.health_score ?? "—",
  },
  {
    id: "health_grade",
    label: "Grade",
    getValue: (device) => device.health_grade ?? "—",
  },
  {
    id: "health_status",
    label: "Health status",
    getValue: (device) => device.health_status ?? "—",
  },
  {
    id: "is_certified",
    label: "CDI certified",
    getValue: (device) => (device.is_certified ? "Yes" : "No"),
  },
  {
    id: "deductions",
    label: "Deductions",
    getValue: formatDeductionsShort,
  },
]

const baseDetailedColumns: DriveColumn[] = [
  {
    id: "serial",
    label: "Serial",
    mono: true,
    getValue: serialLabel,
  },
  {
    id: "model",
    label: "Model",
    getValue: (device) => field(device, "model_number"),
  },
  {
    id: "vendor",
    label: "Vendor",
    getValue: (device) => field(device, "vendor"),
  },
  {
    id: "protocol",
    label: "Protocol",
    getValue: (device) => field(device, "transport_protocol"),
  },
  {
    id: "interface",
    label: "Interface",
    getValue: formatInterfaceLink,
  },
  {
    id: "transport_version",
    label: "Transport",
    getValue: (device) => field(device, "transport_version"),
  },
  {
    id: "transport_revision",
    label: "Transport revision",
    getValue: (device) => field(device, "transport_revision"),
  },
  {
    id: "media",
    label: "Media",
    getValue: (device) => field(device, "media_type"),
  },
  {
    id: "capacity",
    label: "Capacity",
    getValue: formatCapacity,
  },
  {
    id: "firmware",
    label: "Firmware",
    getValue: (device) => field(device, "firmware_revision"),
  },
  {
    id: "form_factor",
    label: "Form factor",
    getValue: (device) => field(device, "form_factor"),
  },
  {
    id: "rotation_rate",
    label: "Rotation rate",
    getValue: (device) => field(device, "rotation_rate"),
  },
  {
    id: "smart_status",
    label: "SMART status",
    getValue: (device) => field(device, "smart_status"),
  },
  {
    id: "power_on_hours",
    label: "Power-on hours",
    getValue: (device) => field(device, "power_on_hours"),
  },
  {
    id: "power_cycles",
    label: "Power cycles",
    getValue: (device) => field(device, "power_cycle_count"),
  },
  {
    id: "load_cycles",
    label: "Load cycles",
    getValue: (device) => field(device, "load_cycle_count"),
  },
  {
    id: "start_stop_count",
    label: "Start/stop count",
    getValue: (device) => field(device, "start_stop_count"),
  },
  {
    id: "temperature",
    label: "Temp °C",
    getValue: (device) => field(device, "current_temperature"),
  },
  {
    id: "highest_temperature",
    label: "Peak temp °C",
    getValue: (device) => field(device, "highest_temperature"),
  },
  {
    id: "maximum_temperature",
    label: "Max rated °C",
    getValue: (device) => field(device, "maximum_temperature"),
  },
]

const hddHealthColumns: DriveColumn[] = [
  {
    id: "reallocated_sectors",
    label: "Reallocated sectors",
    getValue: (device) => field(device, "reallocated_sectors"),
  },
  {
    id: "pending_sectors",
    label: "Pending sectors",
    getValue: pendingSectors,
  },
  {
    id: "uncorrectable_errors",
    label: "Uncorrectable errors",
    getValue: (device) => field(device, "uncorrectable_errors"),
  },
  {
    id: "offline_uncorrectable",
    label: "Offline uncorrectable",
    getValue: (device) => field(device, "offline_uncorrectable_sectors"),
  },
  {
    id: "non_medium_errors",
    label: "Non-medium errors",
    getValue: (device) => field(device, "non_medium_errors"),
  },
]

const sasHealthColumns: DriveColumn[] = [
  {
    id: "grown_defects",
    label: "Grown defects",
    getValue: (device) => field(device, "grown_defects"),
  },
  ...hddHealthColumns.filter((column) => column.id !== "reallocated_sectors"),
]

const ataSsdColumns: DriveColumn[] = [
  {
    id: "ssd_percentage_used",
    label: "Percent used",
    getValue: (device) => field(device, "ssd_percentage_used_endurance"),
  },
  ...hddHealthColumns,
]

const nvmeSummaryColumns: DriveColumn[] = [
  {
    id: "percentage_used",
    label: "Percent used",
    getValue: (device) => field(device, "percentage_used"),
  },
  {
    id: "available_spare",
    label: "Avail spare %",
    getValue: (device) => field(device, "available_spare"),
  },
  {
    id: "critical_warning",
    label: "Critical warning",
    getValue: (device) => field(device, "critical_warning"),
  },
  {
    id: "media_errors",
    label: "Media errors",
    getValue: (device) => field(device, "media_errors"),
  },
  {
    id: "data_written_tb",
    label: "Data written (TB)",
    getValue: (device) => field(device, "data_written_tb"),
  },
  {
    id: "nvme_self_test_failed_count",
    label: "Self-test fails",
    getValue: (device) => field(device, "nvme_self_test_failed_count"),
  },
]

const nvmeExtendedColumns: DriveColumn[] = [
  {
    id: "nvme_data_units_read",
    label: "Data units read",
    getValue: (device) => nvmeLogField(device, "data_units_read"),
  },
  {
    id: "nvme_data_units_written",
    label: "Data units written",
    getValue: (device) => nvmeLogField(device, "data_units_written"),
  },
  {
    id: "nvme_host_reads",
    label: "Host reads",
    getValue: (device) => nvmeLogField(device, "host_reads"),
  },
  {
    id: "nvme_host_writes",
    label: "Host writes",
    getValue: (device) => nvmeLogField(device, "host_writes"),
  },
  {
    id: "nvme_power_cycles",
    label: "NVMe power cycles",
    getValue: (device) => nvmeLogField(device, "power_cycles"),
  },
  {
    id: "nvme_poh",
    label: "NVMe POH",
    getValue: (device) => nvmeLogField(device, "power_on_hours"),
  },
  {
    id: "unsafe_shutdowns",
    label: "Unsafe shutdowns",
    getValue: (device) => nvmeLogField(device, "unsafe_shutdowns"),
  },
  {
    id: "error_log_entries",
    label: "Error log entries",
    getValue: (device) => nvmeLogField(device, "num_err_log_entries"),
  },
  {
    id: "nvme_controller_busy",
    label: "Controller busy (min)",
    getValue: (device) => nvmeLogField(device, "controller_busy_time"),
  },
  {
    id: "nvme_warning_temp_time",
    label: "Warning temp time",
    getValue: (device) => nvmeLogField(device, "warning_temp_time"),
  },
  {
    id: "nvme_critical_temp_time",
    label: "Critical temp time",
    getValue: (device) => nvmeLogField(device, "critical_comp_temp_time"),
  },
]
const smartJsonColumn: DriveColumn = {
  id: "smart_attributes_json",
  label: "SMART attributes (JSON)",
  getValue: smartAttributesSummary,
}

const ocpSummaryColumn: DriveColumn = {
  id: "ocp_summary",
  label: "OCP C0h summary",
  getValue: (device) =>
    device.ocp_smart_log ? `${Object.keys(device.ocp_smart_log).length} field(s)` : "—",
}

function simpleKeyColumns(category: DriveClass): DriveColumn[] {
  switch (category) {
    case "SATA HDD":
      return [
        {
          id: "reallocated_sectors",
          label: "Reallocated",
          getValue: (device) => field(device, "reallocated_sectors"),
        },
        {
          id: "pending_sectors",
          label: "Pending",
          getValue: pendingSectors,
        },
        {
          id: "temperature",
          label: "Temp °C",
          getValue: (device) => field(device, "current_temperature"),
        },
      ]
    case "SAS HDD":
      return [
        {
          id: "grown_defects",
          label: "Grown defects",
          getValue: (device) => field(device, "grown_defects"),
        },
        {
          id: "uncorrectable_errors",
          label: "Uncorrectable",
          getValue: (device) => field(device, "uncorrectable_errors"),
        },
        {
          id: "temperature",
          label: "Temp °C",
          getValue: (device) => field(device, "current_temperature"),
        },
      ]
    case "SATA SSD":
      return [
        {
          id: "ssd_percentage_used",
          label: "Percent used",
          getValue: (device) => field(device, "ssd_percentage_used_endurance"),
        },
        {
          id: "offline_uncorrectable",
          label: "Offline uncorr.",
          getValue: (device) => field(device, "offline_uncorrectable_sectors"),
        },
        {
          id: "temperature",
          label: "Temp °C",
          getValue: (device) => field(device, "current_temperature"),
        },
      ]
    case "SAS SSD":
      return [
        {
          id: "ssd_percentage_used",
          label: "Percent used",
          getValue: (device) => field(device, "ssd_percentage_used_endurance"),
        },
        {
          id: "uncorrectable_errors",
          label: "Uncorrectable",
          getValue: (device) => field(device, "uncorrectable_errors"),
        },
        {
          id: "temperature",
          label: "Temp °C",
          getValue: (device) => field(device, "current_temperature"),
        },
      ]
    case "NVMe SSD":
      return [
        {
          id: "percentage_used",
          label: "Percent used",
          getValue: (device) => field(device, "percentage_used"),
        },
        {
          id: "critical_warning",
          label: "Crit. warning",
          getValue: (device) => field(device, "critical_warning"),
        },
        {
          id: "media_errors",
          label: "Media errors",
          getValue: (device) => field(device, "media_errors"),
        },
      ]
    default:
      return [
        {
          id: "smart_status",
          label: "SMART status",
          getValue: (device) => field(device, "smart_status"),
        },
        {
          id: "temperature",
          label: "Temp °C",
          getValue: (device) => field(device, "current_temperature"),
        },
      ]
  }
}

export function getSimpleColumns(category: DriveClass): DriveColumn[] {
  return [
    {
      id: "serial",
      label: "Serial",
      mono: true,
      getValue: serialLabel,
    },
    {
      id: "model",
      label: "Model",
      getValue: (device) => field(device, "model_number"),
    },
    {
      id: "health_score",
      label: "Score",
      getValue: (device) => device.health_score ?? "—",
    },
    {
      id: "health_grade",
      label: "Grade",
      getValue: (device) => device.health_grade ?? "—",
    },
    {
      id: "health_status",
      label: "Status",
      getValue: (device) => device.health_status ?? "—",
    },
    ...simpleKeyColumns(category),
    {
      id: "deductions",
      label: "Deductions",
      getValue: formatDeductionsShort,
    },
  ]
}

export function getDetailedColumns(category: DriveClass): DriveColumn[] {
  switch (category) {
    case "NVMe SSD":
      return [
        ...baseDetailedColumns,
        ...nvmeSummaryColumns,
        ...nvmeExtendedColumns,
        ocpSummaryColumn,
        ...gradingColumns,
      ]
    case "SATA HDD":
      return [
        ...baseDetailedColumns,
        ...hddHealthColumns,
        smartJsonColumn,
        ...gradingColumns,
      ]
    case "SAS HDD":
      return [
        ...baseDetailedColumns,
        ...sasHealthColumns,
        smartJsonColumn,
        ...gradingColumns,
      ]
    case "SATA SSD":
      return [
        ...baseDetailedColumns,
        ...ataSsdColumns,
        smartJsonColumn,
        ...gradingColumns,
      ]
    case "SAS SSD":
      return [
        ...baseDetailedColumns,
        ...sasHealthColumns,
        smartJsonColumn,
        ...gradingColumns,
      ]
    default:
      return [
        ...baseDetailedColumns,
        ...hddHealthColumns,
        ...nvmeSummaryColumns,
        smartJsonColumn,
        ocpSummaryColumn,
        ...gradingColumns,
      ]
  }
}
