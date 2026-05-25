import { Badge } from "@workspace/ui/components/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { healthBadgeVariant } from "@/lib/health-badges"
import type { DeviceRecord, DriveColumn } from "@/lib/types"

type DriveHealthTableProps = {
  devices: DeviceRecord[]
  columns: DriveColumn[]
}

export function DriveHealthTable({ devices, columns }: DriveHealthTableProps) {
  return (
    <div className="overflow-x-auto rounded-2xl border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column.id} className="whitespace-nowrap">
                {column.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {devices.map((device, index) => (
            <TableRow key={serialKey(device, index)}>
              {columns.map((column) => {
                const value = column.getValue(device)
                const isGradeColumn = column.id === "health_grade"
                const isStatusColumn = column.id === "health_status"

                return (
                  <TableCell
                    key={column.id}
                    className={
                      column.mono
                        ? "max-w-48 truncate font-mono text-xs"
                        : column.id === "deductions"
                          ? "max-w-md text-xs"
                          : "whitespace-nowrap text-sm"
                    }
                    title={String(value)}
                  >
                    {isGradeColumn || isStatusColumn ? (
                      <Badge
                        variant={healthBadgeVariant(
                          device.health_status,
                          device.health_grade
                        )}
                      >
                        {value}
                      </Badge>
                    ) : (
                      value
                    )}
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function serialKey(device: DeviceRecord, index: number): string {
  return String(device.serial_number ?? device.dut ?? `row-${index}`)
}
