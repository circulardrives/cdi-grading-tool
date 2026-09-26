import { useId, useMemo, useState } from "react"
import { ArrowDownIcon, ArrowUpIcon, SearchIcon } from "lucide-react"

import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Switch } from "@workspace/ui/components/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { deviceRowKeys } from "@/lib/drive-labels"
import {
  deviceBadgeVariant,
  isUngradedDevice,
  warningFlags,
} from "@/lib/health-badges"
import type { DeviceRecord, DriveColumn } from "@/lib/types"

type DriveHealthTableProps = {
  devices: DeviceRecord[]
  columns: DriveColumn[]
}

type GradeSort = "none" | "asc" | "desc"

const ARIA_SORT: Record<GradeSort, "none" | "ascending" | "descending"> = {
  none: "none",
  asc: "ascending",
  desc: "descending",
}

const GRADE_ORDER = ["A", "B", "C", "D", "F", "UNGRADED", ""]

const WIDE_TEXT_COLUMNS = new Set([
  "deductions",
  "certification_rationale",
  "fail_reason_codes",
])

function gradeRank(device: DeviceRecord): number {
  const grade = isUngradedDevice(device)
    ? "UNGRADED"
    : (device.health_grade ?? "").toUpperCase()
  const index = GRADE_ORDER.indexOf(grade)
  return index === -1 ? GRADE_ORDER.length : index
}

function isFailureDevice(device: DeviceRecord): boolean {
  if (isUngradedDevice(device)) {
    return false
  }
  const status = (device.health_status ?? "").toLowerCase()
  const grade = (device.health_grade ?? "").toUpperCase()
  return (
    status.includes("fail") ||
    status.includes("critical") ||
    grade === "D" ||
    grade === "F"
  )
}

function matchesSearch(device: DeviceRecord, query: string): boolean {
  if (!query) {
    return true
  }
  const haystack = [
    device.serial_number,
    device.model_number,
    device.dut,
    device.vendor,
    device.machine_name,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
  return haystack.includes(query)
}

export function DriveHealthTable({ devices, columns }: DriveHealthTableProps) {
  const [search, setSearch] = useState("")
  const [failuresOnly, setFailuresOnly] = useState(false)
  const [gradeSort, setGradeSort] = useState<GradeSort>("none")
  const failuresOnlyId = useId()
  const rowKeys = useMemo(() => deviceRowKeys(devices), [devices])

  const filteredDevices = useMemo(() => {
    const query = search.trim().toLowerCase()
    let next = devices.filter((device) => matchesSearch(device, query))
    if (failuresOnly) {
      next = next.filter(isFailureDevice)
    }
    if (gradeSort !== "none") {
      next = [...next].sort((a, b) => {
        const diff = gradeRank(a) - gradeRank(b)
        return gradeSort === "asc" ? diff : -diff
      })
    }
    return next
  }, [devices, search, failuresOnly, gradeSort])

  const cycleGradeSort = () => {
    setGradeSort((current) =>
      current === "none" ? "asc" : current === "asc" ? "desc" : "none"
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1">
          <SearchIcon className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by serial or model…"
            className="pl-8"
            aria-label="Filter drives by serial or model"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={cycleGradeSort}
          aria-label={`Sort by grade ${gradeSort}`}
        >
          Grade
          {gradeSort === "asc" ? (
            <ArrowUpIcon data-icon="inline-end" />
          ) : gradeSort === "desc" ? (
            <ArrowDownIcon data-icon="inline-end" />
          ) : null}
        </Button>
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Switch
            id={failuresOnlyId}
            checked={failuresOnly}
            onCheckedChange={setFailuresOnly}
          />
          <label htmlFor={failuresOnlyId}>Failures only</label>
        </div>
        <span className="text-muted-foreground text-xs">
          {filteredDevices.length} of {devices.length}
        </span>
      </div>

      <div className="overflow-x-auto rounded-2xl border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) =>
                column.id === "health_grade" ? (
                  <TableHead
                    key={column.id}
                    className="whitespace-nowrap"
                    aria-sort={ARIA_SORT[gradeSort]}
                  >
                    <button
                      type="button"
                      onClick={cycleGradeSort}
                      className="inline-flex items-center gap-1 hover:underline"
                    >
                      {column.label}
                      {gradeSort === "asc" ? (
                        <ArrowUpIcon className="size-3" aria-hidden />
                      ) : gradeSort === "desc" ? (
                        <ArrowDownIcon className="size-3" aria-hidden />
                      ) : null}
                    </button>
                  </TableHead>
                ) : (
                  <TableHead key={column.id} className="whitespace-nowrap">
                    {column.label}
                  </TableHead>
                )
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredDevices.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-muted-foreground text-center text-sm"
                >
                  No drives match the current filters.
                </TableCell>
              </TableRow>
            ) : (
              filteredDevices.map((device, index) => (
                <TableRow key={rowKeys.get(device) ?? `row-${index}`}>
                  {columns.map((column) => {
                    const value = column.getValue(device)
                    const isGradeColumn = column.id === "health_grade"
                    const isStatusColumn = column.id === "health_status"
                    const flags =
                      column.id === "warning_flags" ? warningFlags(device) : []

                    return (
                      <TableCell
                        key={column.id}
                        className={
                          column.mono
                            ? "max-w-48 truncate font-mono text-xs"
                            : WIDE_TEXT_COLUMNS.has(column.id)
                              ? "max-w-md text-xs"
                              : "whitespace-nowrap text-sm"
                        }
                        title={String(value)}
                      >
                        {isGradeColumn || isStatusColumn ? (
                          <Badge variant={deviceBadgeVariant(device)}>
                            {value}
                          </Badge>
                        ) : flags.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {flags.map((flag) => (
                              <Badge
                                key={flag}
                                variant="secondary"
                                className="font-mono text-[10px]"
                              >
                                {flag}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          value
                        )}
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
