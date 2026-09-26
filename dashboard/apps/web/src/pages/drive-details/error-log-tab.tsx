/**
 * Error log tab: NVMe Error Information log (01h) entries in words, or the
 * ATA SMART error log. Telemetry only — error log entries never change the
 * grade (docs/CDI_HEALTH_SPEC.md).
 */
import { ListChecksIcon } from "lucide-react"

import { EmptyState, Note, Pill } from "@/components/ui-cdi"
import type { DeviceRecord } from "@/lib/types"
import { formatInt, isNvme, toNumber } from "@/pages/drives/drive-format"

import { asArray, asRecord, hex, numberOf, textOf } from "./details-format"
import { ScrollTable, Secondary, TableCard, Td, Th } from "./field-table"

const TELEMETRY_NOTE =
  "Error log entries don't change the grade. Most come from tools probing features the drive doesn't support (“Invalid Field in Command”)."

function NvmeErrorLog({ device }: { device: DeviceRecord }) {
  const log = asRecord(device.nvme_error_information_log) ?? {}
  const entries = asArray(log.table)
    .map((entry) => asRecord(entry) ?? {})
    // Entries with error count 0 are empty slots.
    .filter((entry) => toNumber(entry.error_count) !== 0)
  const lifetime = toNumber(
    asRecord(device.nvme_smart_health_information_log)?.num_err_log_entries
  )
  const summary = [
    lifetime != null
      ? `${formatInt(lifetime)} errors logged over the drive's life`
      : null,
    toNumber(log.size) != null
      ? `log holds ${formatInt(toNumber(log.size) ?? 0)}`
      : null,
    toNumber(log.read) != null
      ? `${formatInt(toNumber(log.read) ?? 0)} read by this scan`
      : null,
  ]
    .filter(Boolean)
    .join(" · ")

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<ListChecksIcon />}
        title={lifetime ? "No entries in this scan" : "No errors logged"}
        description={
          lifetime
            ? `${summary}. The entries weren't saved with this scan. ${TELEMETRY_NOTE}`
            : `The drive's error log is empty. ${TELEMETRY_NOTE}`
        }
      />
    )
  }

  return (
    <TableCard
      title="Error information log"
      description={`NVMe log page 01h · ${summary || `${entries.length} entries`}`}
    >
      <div className="border-b px-6 py-3 max-sm:px-4">
        <Note tone="info">{TELEMETRY_NOTE}</Note>
      </div>
      <ScrollTable label="NVMe error information log">
        <thead>
          <tr>
            <Th className="pl-6" align="right">
              Error #
            </Th>
            <Th>Status</Th>
            <Th>Command</Th>
            <Th align="right">LBA</Th>
            <Th className="pr-6">Namespace</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, index) => {
            const status = asRecord(entry.status_field) ?? {}
            const statusValue = toNumber(status.value)
            const lba = numberOf(entry.lba)
            const nsid = toNumber(entry.nsid)
            const opcode = toNumber(entry.opcode)
            return (
              <tr key={index} className="hover:bg-muted/60">
                <Td align="right" className="pl-6">
                  {formatInt(toNumber(entry.error_count) ?? index + 1)}
                </Td>
                <Td>
                  <div className="font-semibold">
                    {textOf(status) || "Unknown status"}
                  </div>
                  <Secondary className="font-mono text-sm">
                    {[
                      toNumber(status.status_code_type) != null
                        ? `SCT ${hex(toNumber(status.status_code_type) ?? 0)}`
                        : null,
                      toNumber(status.status_code) != null
                        ? `SC ${hex(toNumber(status.status_code) ?? 0)}`
                        : null,
                      statusValue != null ? `raw ${hex(statusValue)}` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </Secondary>
                  {status.do_not_retry === true ? (
                    <Pill tone="info" className="mt-1">
                      Do not retry
                    </Pill>
                  ) : null}
                </Td>
                <Td className="font-mono text-[15px] whitespace-nowrap">
                  {[
                    opcode != null ? `opcode ${hex(opcode)}` : null,
                    toNumber(entry.command_id) != null
                      ? `cmd ${hex(toNumber(entry.command_id) ?? 0)}`
                      : null,
                    toNumber(entry.submission_queue_id) != null
                      ? `queue ${toNumber(entry.submission_queue_id)}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </Td>
                <Td align="right" className="font-mono text-[15px]">
                  {lba != null ? formatInt(lba) : "—"}
                </Td>
                <Td className="pr-6">
                  {nsid == null
                    ? "—"
                    : nsid === 0 || nsid === 0xffffffff
                      ? "Whole drive"
                      : nsid}
                </Td>
              </tr>
            )
          })}
        </tbody>
      </ScrollTable>
    </TableCard>
  )
}

function AtaErrorLog({ device }: { device: DeviceRecord }) {
  const smartctl = asRecord(device.smartctl_json) ?? {}
  const log = asRecord(smartctl.ata_smart_error_log) ?? {}
  const section = asRecord(log.extended) ?? asRecord(log.summary) ?? {}
  const count = toNumber(section.count)
  const entries = asArray(section.table).map((entry) => asRecord(entry) ?? {})
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<ListChecksIcon />}
        title={count ? `${formatInt(count)} errors logged` : "No errors logged"}
        description={
          count
            ? "The drive counted errors but didn't return the entries."
            : "The drive's SMART error log is empty."
        }
      />
    )
  }
  return (
    <TableCard
      title="SMART error log"
      description={`${formatInt(count ?? entries.length)} errors logged · showing the ${entries.length} the drive kept. Telemetry — doesn't change the grade.`}
    >
      <ScrollTable label="ATA SMART error log">
        <thead>
          <tr>
            <Th className="pl-6" align="right">
              Error #
            </Th>
            <Th align="right">Powered on</Th>
            <Th className="pr-6">What happened</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, index) => (
            <tr key={index} className="hover:bg-muted/60">
              <Td align="right" className="pl-6">
                {formatInt(toNumber(entry.error_number) ?? index + 1)}
              </Td>
              <Td align="right" className="whitespace-nowrap">
                {toNumber(entry.lifetime_hours) != null
                  ? `${formatInt(toNumber(entry.lifetime_hours) ?? 0)} h`
                  : "—"}
              </Td>
              <Td className="pr-6">
                {textOf(entry.error_description) ||
                  textOf(asRecord(entry.completion_registers)?.error) ||
                  "—"}
              </Td>
            </tr>
          ))}
        </tbody>
      </ScrollTable>
    </TableCard>
  )
}

export function ErrorLogTab({ device }: { device: DeviceRecord }) {
  return isNvme(device) ? (
    <NvmeErrorLog device={device} />
  ) : (
    <AtaErrorLog device={device} />
  )
}
