/**
 * SMART attributes tab (ATA/SATA): the full attribute table with the rows
 * that feed grading marked, plus the ATA Device Statistics log when present.
 * Attribute → grading mapping follows src/cdi_health/classes/devices.py.
 */
import { ListIcon } from "lucide-react"

import { EmptyState, Pill } from "@/components/ui-cdi"
import type { DeviceRecord } from "@/lib/types"
import { formatInt, toNumber } from "@/pages/drives/drive-format"
import { cn } from "@workspace/ui/lib/utils"

import {
  asArray,
  asRecord,
  checkFromDeductions,
  textOf,
  type GradeCheck,
  type Obj,
} from "./details-format"
import {
  CheckCell,
  ScrollTable,
  Secondary,
  TableCard,
  Td,
  Th,
} from "./field-table"

/** Plain names for common ATA attribute IDs. */
const ATTRIBUTE_NAMES: Record<number, string> = {
  1: "Read error rate",
  2: "Throughput performance",
  3: "Spin-up time",
  4: "Start/stop count",
  5: "Reallocated sectors",
  7: "Seek error rate",
  8: "Seek time performance",
  9: "Powered on (hours)",
  10: "Spin-up retries",
  11: "Calibration retries",
  12: "Power cycles",
  13: "Soft read error rate",
  22: "Helium level",
  160: "Uncorrectable sectors (read/write)",
  161: "Valid spare blocks",
  163: "Initial bad blocks",
  164: "Total erase count",
  165: "Maximum erase count",
  166: "Minimum erase count",
  167: "Average erase count",
  168: "Max erase count (rated)",
  169: "Remaining life",
  170: "Reserved blocks",
  171: "Program failures",
  172: "Erase failures",
  173: "Wear levelling count",
  174: "Unexpected power losses",
  175: "Power-loss protection failures",
  176: "Erase failures (chip)",
  177: "Wear levelling count",
  178: "Used reserved blocks (chip)",
  179: "Used reserved blocks",
  180: "Unused reserved blocks",
  181: "Program failures",
  182: "Erase failures",
  183: "Runtime bad blocks / SATA downshifts",
  184: "End-to-end errors",
  187: "Reported uncorrectable errors",
  188: "Command timeouts",
  189: "High-fly writes",
  190: "Airflow temperature",
  191: "Shock events",
  192: "Power-off retracts",
  193: "Load/unload cycles",
  194: "Temperature",
  195: "ECC recoveries",
  196: "Reallocation events",
  197: "Sectors waiting to be reallocated",
  198: "Offline uncorrectable sectors",
  199: "Cable (UDMA CRC) errors",
  200: "Write error rate",
  202: "Percent life used",
  206: "Flying height",
  210: "RAID recovery failures",
  220: "Disk shift",
  222: "Loaded hours",
  223: "Load/unload retries",
  224: "Load friction",
  225: "Load/unload cycles",
  226: "Load-in time",
  230: "Drive life protection / wear",
  231: "SSD life left",
  232: "Available reserved space",
  233: "Media wearout indicator",
  234: "Average erase count",
  235: "Good block count / power-fail backup",
  240: "Head flying hours",
  241: "Total data written (LBAs)",
  242: "Total data read (LBAs)",
  243: "Total data written (LBAs, high)",
  244: "Average erase count",
  245: "Remaining life",
  246: "Total host sector writes",
  247: "Host program page count",
  248: "Background program page count",
  249: "Total NAND writes",
  250: "Read error retries",
  251: "Minimum spares remaining",
  252: "Newly added bad blocks",
  254: "Free-fall events",
}

/** Wear attributes CDI may read "writes used" from, in devices.py priority. */
const WEAR_IDS = [233, 230, 231, 177, 169, 202]

type Attribute = {
  id: number | null
  name: string
  value: number | null
  worst: number | null
  thresh: number | null
  raw: string
  prefail: boolean | null
  flags: string
  whenFailed: string
}

function attributesOf(device: DeviceRecord): Attribute[] {
  const fromRecord = asArray(device.smart_attributes)
  const smartctl = asRecord((device as Obj).smartctl_json)
  const list =
    fromRecord.length > 0
      ? fromRecord
      : asArray(asRecord(smartctl?.ata_smart_attributes)?.table)
  return list.map((entry) => {
    const item = asRecord(entry) ?? {}
    const flags = asRecord(item.flags)
    return {
      id: toNumber(item.id),
      name: String(item.name ?? ""),
      value: toNumber(item.value),
      worst: toNumber(item.worst),
      thresh: toNumber(item.thresh),
      raw: textOf(item.raw),
      prefail: flags ? Boolean(flags.prefailure) : null,
      flags: String(flags?.string ?? "").trim(),
      whenFailed: String(item.when_failed ?? "").trim(),
    }
  })
}

function hasDeviceStatWear(device: DeviceRecord): boolean {
  const stats = asRecord(
    asRecord((device as Obj).smartctl_json)?.ata_device_statistics
  )
  return asArray(stats?.pages).some((page) =>
    asArray(asRecord(page)?.table).some((entry) =>
      /percentage used endurance/i.test(String(asRecord(entry)?.name ?? ""))
    )
  )
}

/** How this attribute feeds the grade, if it does. */
function gradeUse(
  device: DeviceRecord,
  attr: Attribute,
  wearSource: number | null
): { check: GradeCheck; note: string } | null {
  switch (attr.id) {
    case 5:
      return {
        note: "Reallocated sectors",
        check: checkFromDeductions(device, ["reallocated_sectors"], attr.raw),
      }
    case 197:
      return {
        note: "Pending sectors",
        check: checkFromDeductions(device, ["pending_sectors"], attr.raw),
      }
    case 198:
      return {
        note: "Uncorrectable errors",
        check: checkFromDeductions(device, ["uncorrectable_errors"], attr.raw),
      }
    case 232:
      return {
        note: "Spare (reserved space)",
        check: checkFromDeductions(
          device,
          ["available_reserved_space"],
          attr.value
        ),
      }
    default:
      if (attr.id != null && attr.id === wearSource) {
        return {
          note: "Writes used",
          check: checkFromDeductions(
            device,
            ["ssd_percentage_used_endurance"],
            attr.value
          ),
        }
      }
      return null
  }
}

function failedText(whenFailed: string): string | null {
  if (!whenFailed || whenFailed === "-") {
    return null
  }
  if (whenFailed === "now") {
    return "Failing now"
  }
  if (whenFailed === "past") {
    return "Failed in the past"
  }
  return whenFailed
}

function DeviceStatistics({ device }: { device: DeviceRecord }) {
  const stats = asRecord(
    asRecord((device as Obj).smartctl_json)?.ata_device_statistics
  )
  const pages = asArray(stats?.pages)
    .map((page) => asRecord(page))
    .filter((page): page is Obj => Boolean(page))
  if (pages.length === 0) {
    return null
  }
  return (
    <TableCard
      title="Device statistics"
      description="ATA Device Statistics log (GP log 04h) — telemetry, grouped by page."
    >
      <ScrollTable label="ATA device statistics">
        <thead>
          <tr>
            <Th className="pl-6">Statistic</Th>
            <Th align="right" className="pr-6">
              Value
            </Th>
          </tr>
        </thead>
        {pages.map((page, pageIndex) => (
          <tbody key={`${String(page.number)}-${pageIndex}`}>
            <tr>
              <th
                scope="rowgroup"
                colSpan={2}
                className="border-b bg-muted px-6 py-2 text-left text-[15px] font-bold"
              >
                {String(page.name ?? `Page ${String(page.number ?? "")}`)}
              </th>
            </tr>
            {asArray(page.table).map((entry, index) => {
              const item = asRecord(entry) ?? {}
              const flags = asRecord(item.flags)
              const valid = flags ? flags.valid !== false : true
              const normalized = Boolean(flags?.normalized)
              return (
                <tr
                  key={`${String(item.offset)}-${index}`}
                  className="hover:bg-muted/60"
                >
                  <Td className="pl-6">
                    {String(item.name ?? "")}
                    {normalized ? (
                      <Secondary>Normalized value</Secondary>
                    ) : null}
                  </Td>
                  <Td align="right" className="pr-6">
                    {valid ? (
                      toNumber(item.value) != null ? (
                        formatInt(toNumber(item.value) ?? 0)
                      ) : (
                        String(item.value ?? "—")
                      )
                    ) : (
                      <span className="text-muted-foreground">Not valid</span>
                    )}
                  </Td>
                </tr>
              )
            })}
          </tbody>
        ))}
      </ScrollTable>
    </TableCard>
  )
}

export function SmartAttributesTab({ device }: { device: DeviceRecord }) {
  const attributes = attributesOf(device)
  if (attributes.length === 0) {
    return (
      <EmptyState
        icon={<ListIcon />}
        title="No SMART attributes in this scan"
        description="The drive didn't report an attribute table. Check the Raw data tab."
      />
    )
  }
  const ids = new Set(attributes.map((attr) => attr.id))
  const wearSource = hasDeviceStatWear(device)
    ? null
    : (WEAR_IDS.find((id) => ids.has(id)) ?? null)

  return (
    <div className="flex flex-col gap-6">
      <TableCard
        title="SMART attributes"
        description={`${attributes.length} attributes. Now / worst / limit are the drive's normalized scores (higher is better; at or below the limit means failing). Rows with a bar feed the grade.`}
      >
        <ScrollTable label="SMART attributes">
          <thead>
            <tr>
              <Th className="pl-6" align="right">
                ID
              </Th>
              <Th className="min-w-56">Attribute</Th>
              <Th align="right">Now</Th>
              <Th align="right">Worst</Th>
              <Th align="right">Limit</Th>
              <Th align="right">Raw value</Th>
              <Th>Type</Th>
              <Th>Failed</Th>
              <Th className="min-w-44 pr-6">Counts toward grade</Th>
            </tr>
          </thead>
          <tbody>
            {attributes.map((attr, index) => {
              const use = gradeUse(device, attr, wearSource)
              const failed = failedText(attr.whenFailed)
              const atLimit =
                attr.value != null &&
                attr.thresh != null &&
                attr.thresh > 0 &&
                attr.value <= attr.thresh
              return (
                <tr
                  key={`${attr.id}-${index}`}
                  className={cn(
                    "hover:bg-muted/60",
                    use &&
                      "[&>td:first-child]:shadow-[inset_4px_0_0_var(--primary)]"
                  )}
                >
                  <Td align="right" className="pl-6 font-mono text-[15px]">
                    {attr.id ?? "—"}
                  </Td>
                  <Td>
                    <div className="font-semibold">
                      {(attr.id != null && ATTRIBUTE_NAMES[attr.id]) ||
                        attr.name.replace(/_/g, " ") ||
                        "Unknown"}
                    </div>
                    <Secondary className="font-mono text-sm">
                      {attr.name || "—"}
                    </Secondary>
                  </Td>
                  <Td align="right">{attr.value ?? "—"}</Td>
                  <Td align="right">{attr.worst ?? "—"}</Td>
                  <Td align="right">{attr.thresh ?? "—"}</Td>
                  <Td align="right" className="font-mono text-[15px] break-all">
                    {attr.raw || "—"}
                  </Td>
                  <Td className="whitespace-nowrap">
                    {attr.prefail == null
                      ? "—"
                      : attr.prefail
                        ? "Pre-fail"
                        : "Old age"}
                    {attr.flags ? (
                      <Secondary className="font-mono text-sm">
                        {attr.flags}
                      </Secondary>
                    ) : null}
                  </Td>
                  <Td className="whitespace-nowrap">
                    {failed ? (
                      <Pill tone={attr.whenFailed === "now" ? "bad" : "warn"}>
                        {failed}
                      </Pill>
                    ) : atLimit ? (
                      <Pill tone="bad">At limit</Pill>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </Td>
                  <Td className="pr-6">
                    <CheckCell check={use?.check ?? null} note={use?.note} />
                  </Td>
                </tr>
              )
            })}
          </tbody>
        </ScrollTable>
      </TableCard>
      <DeviceStatistics device={device} />
    </div>
  )
}
