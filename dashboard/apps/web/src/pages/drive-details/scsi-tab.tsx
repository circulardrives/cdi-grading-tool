/**
 * SCSI/SAS tab: the error counter log (read / write / verify), grown
 * defects, non-medium errors, start-stop and load cycles, and the SSD
 * endurance indicator. Field names follow smartctl --json and devices.py.
 */
import { ServerIcon } from "lucide-react"

import { EmptyState } from "@/components/ui-cdi"
import type { DeviceRecord } from "@/lib/types"
import { formatInt, toNumber } from "@/pages/drives/drive-format"

import {
  asRecord,
  celsius,
  checkFromDeductions,
  formatCelsius,
  formatCount,
  numberOf,
  type Obj,
} from "./details-format"
import {
  FieldTable,
  ScrollTable,
  Secondary,
  TableCard,
  Td,
  Th,
  type FieldRow,
} from "./field-table"

const COUNTER_COLUMNS: [string, string, string?][] = [
  ["errors_corrected_by_eccfast", "Fixed by ECC (fast)"],
  ["errors_corrected_by_eccdelayed", "Fixed by ECC (delayed)"],
  ["errors_corrected_by_rereads_rewrites", "Fixed by retry"],
  ["total_errors_corrected", "Total fixed"],
  ["correction_algorithm_invocations", "Correction runs"],
  ["gigabytes_processed", "Data processed", "GB"],
  ["total_uncorrected_errors", "Not fixed"],
]

const OPERATIONS: [string, string][] = [
  ["read", "Read"],
  ["write", "Write"],
  ["verify", "Verify"],
]

/** smartctl's error counter log; devices.py also keeps it as smart_attributes. */
function counterLogOf(device: DeviceRecord): Obj | null {
  return (
    asRecord(asRecord(device.smartctl_json)?.scsi_error_counter_log) ??
    asRecord(device.smart_attributes)
  )
}

function counterValue(value: unknown, unit?: string): string {
  const n = toNumber(value)
  if (n == null) {
    return value == null || value === "" ? "—" : String(value)
  }
  if (unit === "GB") {
    return n >= 1000
      ? `${Number((n / 1000).toFixed(2)).toLocaleString("en-US")} TB`
      : `${Number(n.toFixed(1)).toLocaleString("en-US")} GB`
  }
  return formatInt(n)
}

function ErrorCounterLog({ log }: { log: Obj }) {
  const operations = OPERATIONS.filter(([key]) => asRecord(log[key]))
  if (operations.length === 0) {
    return null
  }
  return (
    <TableCard
      title="Error counter log"
      description="Errors the drive fixed and couldn't fix, per operation. “Not fixed” adds up to the uncorrected errors CDI grades on."
    >
      <ScrollTable label="SCSI error counter log">
        <thead>
          <tr>
            <Th className="pl-6">Operation</Th>
            {COUNTER_COLUMNS.map(([key, label], index) => (
              <Th
                key={key}
                align="right"
                className={index === COUNTER_COLUMNS.length - 1 ? "pr-6" : ""}
              >
                {label}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {operations.map(([key, label]) => {
            const row = asRecord(log[key]) ?? {}
            const uncorrected = toNumber(row.total_uncorrected_errors)
            return (
              <tr key={key} className="hover:bg-muted/60">
                <Td className="pl-6 font-semibold">{label}</Td>
                {COUNTER_COLUMNS.map(([column, , unit], index) => (
                  <Td
                    key={column}
                    align="right"
                    className={
                      index === COUNTER_COLUMNS.length - 1
                        ? "pr-6 font-semibold"
                        : ""
                    }
                  >
                    {counterValue(row[column], unit)}
                    {column === "total_uncorrected_errors" &&
                    uncorrected != null &&
                    uncorrected > 0 ? (
                      <Secondary>needs a look</Secondary>
                    ) : null}
                  </Td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </ScrollTable>
    </TableCard>
  )
}

function readingRows(device: DeviceRecord): FieldRow[] {
  const smartctl = asRecord(device.smartctl_json) ?? {}
  const log = counterLogOf(device) ?? {}
  const rows: FieldRow[] = []

  const grown =
    toNumber(smartctl.scsi_grown_defect_list) ??
    toNumber(device.grown_defects) ??
    toNumber(device.reallocated_sectors)
  rows.push({
    key: "grown",
    label: "Grown defects",
    spec: "scsi_grown_defect_list · Grown Defect List",
    meaning: "Sectors the drive has remapped since leaving the factory.",
    value: formatCount(grown),
    check: checkFromDeductions(
      device,
      ["grown_defects", "reallocated_sectors"],
      grown,
      "A 0 · B 1–9 · C 10–50 · D 51–100 · F over 100"
    ),
  })

  const uncorrected = OPERATIONS.map(([key]) =>
    toNumber(asRecord(log[key])?.total_uncorrected_errors)
  ).filter((value): value is number => value != null)
  const totalUncorrected = uncorrected.length
    ? uncorrected.reduce((sum, value) => sum + value, 0)
    : toNumber(device.uncorrectable_errors)
  rows.push({
    key: "uncorrected",
    label: "Uncorrected errors (read + write + verify)",
    spec: "scsi_error_counter_log.*.total_uncorrected_errors",
    meaning: "Errors the drive couldn't fix, across all operations.",
    value: formatCount(totalUncorrected),
    check: checkFromDeductions(
      device,
      ["uncorrected_errors", "uncorrectable_errors"],
      totalUncorrected,
      "A 0 · B 1–5 · C 6–25 · D 26–100 · F over 100"
    ),
  })

  const nonMedium =
    toNumber(smartctl.scsi_nonmedium_error_count) ??
    toNumber(smartctl.non_medium_error_count) ??
    numberOf(asRecord(smartctl.scsi_nonmedium_error)?.count) ??
    toNumber(device.non_medium_errors)
  rows.push({
    key: "non-medium",
    label: "Non-medium errors",
    spec: "Non-Medium Error Count",
    meaning:
      "Errors not caused by the platters or flash (link, firmware, power).",
    value: formatCount(nonMedium),
  })

  const startStop = asRecord(smartctl.scsi_start_stop_cycle_counter) ?? {}
  const cycles = toNumber(startStop.accumulated_start_stop_cycles)
  const cyclesRated = toNumber(
    startStop.specified_cycle_count_over_device_lifetime
  )
  if (cycles != null || cyclesRated != null) {
    rows.push({
      key: "start-stop",
      label: "Start-stop cycles",
      spec: "Start-Stop Cycle Counter",
      value: `${formatCount(cycles)} of ${formatCount(cyclesRated)} rated`,
      exact:
        cycles != null && cyclesRated
          ? `${Math.round((cycles / cyclesRated) * 100)}% of rated cycles`
          : undefined,
    })
  }
  const loads = toNumber(startStop.accumulated_load_unload_cycles)
  const loadsRated = toNumber(
    startStop.specified_load_unload_count_over_device_lifetime
  )
  if (loads != null || loadsRated != null) {
    rows.push({
      key: "load-unload",
      label: "Load/unload cycles",
      spec: "Start-Stop Cycle Counter (load/unload)",
      value: `${formatCount(loads)} of ${formatCount(loadsRated)} rated`,
      exact:
        loads != null && loadsRated
          ? `${Math.round((loads / loadsRated) * 100)}% of rated cycles`
          : undefined,
    })
  }

  const endurance =
    toNumber(smartctl.scsi_percentage_used_endurance_indicator) ??
    toNumber(device.ssd_percentage_used_endurance)
  if (endurance != null) {
    const ssd = String(device.media_type ?? "").toUpperCase() === "SSD"
    rows.push({
      key: "endurance",
      label: "Writes used (endurance indicator)",
      spec: "Percentage Used Endurance Indicator",
      meaning: "Share of rated write endurance used (SSDs).",
      value: `${formatInt(endurance)}%`,
      check: ssd
        ? checkFromDeductions(
            device,
            ["ssd_percentage_used_endurance"],
            endurance,
            "100% or more lowers the grade"
          )
        : null,
      note: ssd ? undefined : "No — not graded on hard drives",
    })
  }

  const temperature = asRecord(smartctl.temperature) ?? {}
  const now = celsius(temperature.current ?? device.current_temperature)
  const trip = celsius(temperature.drive_trip)
  if (now != null || trip != null) {
    rows.push({
      key: "temperature",
      label: "Temperature now",
      value: formatCelsius(now),
      exact: trip != null ? `Drive trip point ${trip} °C` : undefined,
      check: checkFromDeductions(
        device,
        ["current_temperature"],
        now,
        trip != null ? `Fails above ${trip} °C` : undefined
      ),
    })
  }
  return rows
}

export function ScsiTab({ device }: { device: DeviceRecord }) {
  const smartctl = asRecord(device.smartctl_json)
  const log = counterLogOf(device)
  const rows = readingRows(device)
  if (!smartctl && rows.every((row) => row.value === "—")) {
    return (
      <EmptyState
        icon={<ServerIcon />}
        title="No SCSI logs in this scan"
        description="The drive didn't return its error counters. Check the Raw data tab."
      />
    )
  }
  return (
    <div className="flex flex-col gap-6">
      <TableCard
        title="SAS health"
        description="Defects, errors and wear. Rows with a bar count toward the grade."
      >
        <FieldTable label="SAS health readings" rows={rows} />
      </TableCard>
      {log ? <ErrorCounterLog log={log} /> : null}
    </div>
  )
}
