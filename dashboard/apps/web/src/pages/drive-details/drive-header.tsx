/**
 * Drive details header block: big grade, name · capacity, identity lines,
 * and the page actions (Run self-test, Scan report, Copy serial).
 */
import { Link } from "react-router-dom"
import { ActivityIcon, CopyIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"

import { Card, GradeChip } from "@/components/ui-cdi"
import {
  formatInt,
  isNvme,
  reported,
  toNumber,
} from "@/pages/drives/drive-format"
import { ReportButton } from "@/pages/drives/drive-panel"
import type { DriveRow } from "@/pages/drives/use-drive-rows"

import { copyText } from "./copy-text"
import { formatWhen } from "./details-format"

export function DriveHeader({
  row,
  selfTestHref,
}: {
  row: DriveRow
  selfTestHref: string | null
}) {
  const { device, grade } = row
  const firmware = reported(device.firmware_revision)
  const score = toNumber(device.health_score)
  const identity = [
    row.serial || "No serial reported",
    row.model && row.model !== row.name ? row.model : null,
    firmware ? `firmware ${firmware}` : null,
  ].filter(Boolean)
  const where = [
    row.benchName,
    device.dut,
    row.type,
    row.scannedAt ? `scanned ${formatWhen(row.scannedAt)}` : null,
  ].filter(Boolean)

  return (
    <Card padded className="flex-row flex-wrap items-start gap-x-8 gap-y-5">
      <div className="flex min-w-0 flex-[1_1_28rem] flex-col gap-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <GradeChip
            grade={grade}
            size="lg"
            showWord="both"
            className="h-12 gap-3 pr-5 pl-1.5 text-xl [&>span:first-child]:size-9 [&>span:first-child]:text-xl"
          />
          {score != null ? (
            <span className="text-[17px] text-muted-foreground tabular-nums">
              Health score{" "}
              <span className="font-semibold text-foreground">
                {formatInt(score)}
              </span>{" "}
              / 100
            </span>
          ) : null}
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <h2 className="text-[28px] leading-tight font-bold break-words max-sm:text-2xl">
            {row.name}
            {row.capacity ? (
              <span className="text-muted-foreground"> · {row.capacity}</span>
            ) : null}
          </h2>
          <p className="font-mono text-base break-all">
            {identity.join(" · ")}
          </p>
          <p className="text-base text-muted-foreground">{where.join(" · ")}</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {isNvme(device) && selfTestHref ? (
          <Button variant="outline" asChild>
            <Link to={selfTestHref}>
              <ActivityIcon data-icon="inline-start" />
              Run self-test
            </Link>
          </Button>
        ) : null}
        <ReportButton row={row} />
        {row.serial ? (
          <Button
            variant="outline"
            onClick={() => void copyText(row.serial, "serial")}
          >
            <CopyIcon data-icon="inline-start" />
            Copy serial
          </Button>
        ) : null}
      </div>
    </Card>
  )
}
