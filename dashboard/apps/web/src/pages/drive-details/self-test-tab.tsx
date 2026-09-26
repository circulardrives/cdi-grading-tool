/**
 * Self-test log tab: the drive's own self-test history in plain words —
 * NVMe Device Self-test log (06h), ATA SMART self-test log, or SCSI
 * self-test results — plus how the history counts toward the grade.
 */
import { ActivityIcon } from "lucide-react"
import { Link } from "react-router-dom"

import { Button } from "@workspace/ui/components/button"

import { EmptyState, Note, Pill, type Tone } from "@/components/ui-cdi"
import { formatPoweredOn } from "@/lib/drive-names"
import type { DeviceRecord } from "@/lib/types"
import { formatInt, isNvme, toNumber } from "@/pages/drives/drive-format"

import { asArray, asRecord, numberOf, textOf, type Obj } from "./details-format"
import { ScrollTable, Secondary, TableCard, Td, Th } from "./field-table"

type Result = { tone: Tone; text: string }

type TestRow = {
  type: string
  result: Result
  /** Spec wording, shown small. */
  detail: string
  hours: number | null
  where: string | null
}

// NVMe Device Self-test log (06h) result codes.
const NVME_RESULTS: Record<number, Result> = {
  0: { tone: "ok", text: "Passed" },
  1: { tone: "info", text: "Aborted — stopped by a command" },
  2: { tone: "info", text: "Aborted — controller reset" },
  3: { tone: "info", text: "Aborted — namespace removed" },
  4: { tone: "info", text: "Aborted — drive was formatted" },
  5: { tone: "bad", text: "Failed — fatal or unknown error" },
  6: { tone: "bad", text: "Failed — a test segment failed" },
  7: { tone: "bad", text: "Failed — test segments failed" },
  8: { tone: "info", text: "Aborted — unknown reason" },
  9: { tone: "info", text: "Aborted — sanitize started" },
}

const NVME_TYPES: Record<number, string> = {
  1: "Short",
  2: "Extended",
  14: "Vendor specific",
}

function nvmeRows(device: DeviceRecord): TestRow[] {
  const log = asRecord(device.nvme_self_test_log) ?? {}
  const entries = [...asArray(log.table), ...asArray(log.entries)]
  const list = entries.length ? entries : asArray(device.nvme_self_test_history)
  return list
    .map((entry) => asRecord(entry) ?? {})
    .map((item): TestRow | null => {
      const code =
        numberOf(item.self_test_result) ?? toNumber(item.result) ?? null
      if (code === 15) {
        return null
      }
      const typeCode = numberOf(item.self_test_code) ?? toNumber(item.test_type)
      const lba = numberOf(item.lba)
      const segment = toNumber(item.segment)
      const where = [
        segment != null && (code === 6 || code === 7)
          ? `segment ${segment}`
          : null,
        lba != null ? `LBA ${formatInt(lba)}` : null,
      ]
        .filter(Boolean)
        .join(" · ")
      return {
        type:
          (typeCode != null ? NVME_TYPES[typeCode] : null) ??
          (textOf(item.self_test_code) || textOf(item.test_type) || "—"),
        result: (code != null ? NVME_RESULTS[code] : null) ?? {
          tone: "info",
          text: textOf(item.self_test_result) || `Result ${code ?? "?"}`,
        },
        detail: textOf(item.self_test_result),
        hours: toNumber(item.power_on_hours),
        where: where || null,
      }
    })
    .filter((row): row is TestRow => row != null)
}

/** ATA self-test status: high nibble of the status byte (smartctl `status.value`). */
function ataResult(status: Obj): Result {
  if (status.passed === true) {
    return { tone: "ok", text: "Passed" }
  }
  const value = toNumber(status.value)
  const nibble = value == null ? null : value >> 4
  if (nibble === 15) {
    return { tone: "info", text: "In progress" }
  }
  if (nibble === 1 || nibble === 2) {
    return {
      tone: "info",
      text: nibble === 1 ? "Aborted — stopped by the host" : "Aborted — reset",
    }
  }
  if (nibble === 0) {
    return { tone: "ok", text: "Passed" }
  }
  return { tone: "bad", text: "Failed" }
}

function ataRows(device: DeviceRecord): TestRow[] {
  const smartctl = asRecord(device.smartctl_json) ?? {}
  const log = asRecord(smartctl.ata_smart_self_test_log) ?? {}
  const table = [
    ...asArray(asRecord(log.extended)?.table),
    ...asArray(asRecord(log.standard)?.table),
  ]
  const list = table.length ? table : asArray(device.smart_self_tests)
  return list.map((entry) => {
    const item = asRecord(entry) ?? {}
    const status = asRecord(item.status) ?? {}
    const lba = numberOf(item.lba)
    const remaining = toNumber(status.remaining_percent)
    return {
      type: textOf(item.type) || "—",
      result: ataResult(status),
      detail: [textOf(status), remaining ? `${remaining}% remaining` : null]
        .filter(Boolean)
        .join(" · "),
      hours: toNumber(item.lifetime_hours),
      where: lba != null ? `First error at LBA ${formatInt(lba)}` : null,
    }
  })
}

const SCSI_RESULTS: Record<number, Result> = {
  0: { tone: "ok", text: "Passed" },
  1: { tone: "info", text: "Aborted — stopped by a command" },
  2: { tone: "info", text: "Aborted — reset" },
  3: { tone: "bad", text: "Failed — unknown error" },
  4: { tone: "bad", text: "Failed — a test segment failed" },
  5: { tone: "bad", text: "Failed — a test segment failed" },
  6: { tone: "bad", text: "Failed — a test segment failed" },
  7: { tone: "bad", text: "Failed — a test segment failed" },
  15: { tone: "info", text: "In progress" },
}

function scsiRows(device: DeviceRecord): TestRow[] {
  const smartctl = asRecord(device.smartctl_json) ?? {}
  const fromJson = Object.entries(smartctl)
    .filter(([key]) => /^scsi_self_test_\d+$/.test(key))
    .sort(([a], [b]) => a.localeCompare(b, "en", { numeric: true }))
    .map(([, value]) => value)
  const list = fromJson.length ? fromJson : asArray(device.smart_self_tests)
  return list.map((entry) => {
    const item = asRecord(entry) ?? {}
    const code = numberOf(item.result)
    const segment = numberOf(item.failed_segment)
    const lba = numberOf(item.lba_first_failure)
    return {
      type: textOf(item.code) || "—",
      result: (code != null ? SCSI_RESULTS[code] : null) ?? {
        tone: "info",
        text: textOf(item.result) || "—",
      },
      detail: textOf(item.result),
      hours: toNumber(asRecord(item.power_on_time)?.hours),
      where:
        [
          segment != null ? `segment ${segment}` : null,
          lba != null ? `LBA ${formatInt(lba)}` : null,
        ]
          .filter(Boolean)
          .join(" · ") || null,
    }
  })
}

function currentOperation(device: DeviceRecord): string | null {
  const log = asRecord(device.nvme_self_test_log)
  const op = asRecord(log?.current_self_test_operation)
  const value = toNumber(op?.value)
  if (!op || value == null || value === 0) {
    return null
  }
  const completion = toNumber(
    asRecord(log?.current_self_test_completion)?.value ??
      log?.current_self_test_completion
  )
  return `${textOf(op) || "Self-test running"}${completion != null ? ` — ${completion}% done` : ""}`
}

export function SelfTestTab({
  device,
  selfTestHref,
}: {
  device: DeviceRecord
  selfTestHref: string | null
}) {
  const protocol = String(device.transport_protocol ?? "").toUpperCase()
  const rows = isNvme(device)
    ? nvmeRows(device)
    : protocol === "SCSI"
      ? scsiRows(device)
      : ataRows(device)
  const running = currentOperation(device)
  const history = device.attribute_grades?.self_test_history as
    | Record<string, unknown>
    | undefined
  const failures = rows.filter((row) => row.result.tone === "bad").length

  const action = selfTestHref ? (
    <Button variant="outline" asChild>
      <Link to={selfTestHref}>
        <ActivityIcon data-icon="inline-start" />
        Run self-test
      </Link>
    </Button>
  ) : null

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<ActivityIcon />}
        title={running ?? "No self-tests logged"}
        description={
          typeof device.smart_self_tests === "string"
            ? `The drive says: ${device.smart_self_tests}.`
            : "The drive has no self-test results saved. Run one to check the media end to end."
        }
        actions={action}
      />
    )
  }

  return (
    <TableCard
      title="Self-test log"
      description={`${rows.length} result${rows.length === 1 ? "" : "s"}, newest first${failures ? ` · ${failures} failed` : ""}.`}
      actions={action}
    >
      <div className="flex flex-col gap-2 border-b px-6 py-3 max-sm:px-4">
        {running ? <Note tone="info">{running}</Note> : null}
        <Note tone={failures ? "warn" : "ok"} neutralText={!failures}>
          {failures
            ? device.grading_profile === "binary"
              ? "Any failed self-test fails the drive."
              : "Failed self-tests lower the grade: one old failure → C, one recent or two old → D, two recent → F."
            : "No failed self-tests — aborted tests don't count against the drive."}
          {history
            ? ` Graded history: ${formatInt(toNumber(history.recent_failures) ?? 0)} recent, ${formatInt(toNumber(history.old_failures) ?? 0)} older failures.`
            : ""}
        </Note>
      </div>
      <ScrollTable label="Self-test log">
        <thead>
          <tr>
            <Th className="pl-6">Result</Th>
            <Th>Test</Th>
            <Th align="right">Powered on at completion</Th>
            <Th className="pr-6">Failing area</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="hover:bg-muted/60">
              <Td className="pl-6">
                <Pill tone={row.result.tone}>{row.result.text}</Pill>
                {row.detail && row.detail !== row.result.text ? (
                  <Secondary className="mt-1">{row.detail}</Secondary>
                ) : null}
              </Td>
              <Td>{row.type}</Td>
              <Td align="right" className="whitespace-nowrap">
                {formatPoweredOn(row.hours)}
              </Td>
              <Td className="pr-6">
                {row.where ?? <span className="text-muted-foreground">—</span>}
              </Td>
            </tr>
          ))}
        </tbody>
      </ScrollTable>
    </TableCard>
  )
}
