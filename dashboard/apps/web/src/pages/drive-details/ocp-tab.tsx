/**
 * OCP C0h tab: the SMART / Health Information Extended log, grouped for
 * techs, with the fields CDI grades on checked against their limits.
 */
import { FileSearchIcon } from "lucide-react"

import { EmptyState, Note } from "@/components/ui-cdi"
import type { DeviceRecord } from "@/lib/types"

import { asRecord } from "./details-format"
import { FieldTable, TableCard } from "./field-table"
import { OCP_GROUPS, ocpRows } from "./ocp-fields"

export function OcpTab({ device }: { device: DeviceRecord }) {
  const log = asRecord(device.ocp_smart_log)
  if (!log || Object.keys(log).length === 0) {
    return (
      <EmptyState
        icon={<FileSearchIcon />}
        title="This drive doesn't provide the OCP extended log"
        description="Only datacenter NVMe drives that follow the OCP spec report log C0h. Grading uses the standard health log instead — nothing is missing."
      />
    )
  }

  const rows = ocpRows(device, log)
  const graded = rows.filter((row) => row.check)
  const failing = graded.filter((row) => row.check?.status === "fail").length
  const warning = graded.filter((row) => row.check?.status === "warn").length

  return (
    <div className="flex flex-col gap-6">
      <Note
        tone={failing ? "bad" : warning ? "warn" : "ok"}
        neutralText={!failing && !warning}
      >
        {failing
          ? `${failing} OCP check${failing === 1 ? "" : "s"} failed`
          : warning
            ? `${warning} OCP check${warning === 1 ? "" : "s"} need${warning === 1 ? "s" : ""} a look`
            : `All ${graded.length} OCP checks pass`}{" "}
        — {rows.length} fields from log C0h (OCP Datacenter NVMe SSD spec v2.7
        §4.8.6). Rows with a bar count toward the grade.
      </Note>
      {OCP_GROUPS.map((group) => {
        const groupRows = rows.filter((row) => row.group === group)
        if (groupRows.length === 0) {
          return null
        }
        return (
          <TableCard
            key={group}
            title={group}
            description={
              group === "Other fields"
                ? "Fields this drive reports that aren't in the v2.7 table."
                : undefined
            }
          >
            <FieldTable label={`OCP C0h — ${group}`} rows={groupRows} />
          </TableCard>
        )
      })}
    </div>
  )
}
