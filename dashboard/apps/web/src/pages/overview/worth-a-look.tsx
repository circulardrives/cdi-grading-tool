/**
 * "Worth a look": drives that aren't an A, or carry a note, worst first, each
 * with one sentence saying why. A row opens that drive on the Drives page.
 */
import type { MouseEvent } from "react"
import { Link, useNavigate } from "react-router-dom"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { GradeChip, Note, PageSection } from "@/components/ui-cdi"
import { driveTitle } from "@/lib/drive-names"
import {
  slotOf,
  whyLines,
  type OverviewDrive,
} from "@/pages/overview/overview-data"

/** Rows shown before pointing at the full Drives list. */
const ROW_LIMIT = 20

function driveHref(drive: OverviewDrive): string | null {
  const serial = (drive.device.serial_number ?? "").trim()
  return serial ? `/drives?${new URLSearchParams({ serial }).toString()}` : null
}

function describe(drives: OverviewDrive[]): string {
  const failed = drives.filter((d) => d.grade === "F").length
  const count = drives.length === 1 ? "1 drive" : `${drives.length} drives`
  const fail =
    failed === 0
      ? "none failed"
      : failed === 1
        ? "1 failed"
        : `${failed} failed`
  return `${count} — ${fail}; these explain why a grade isn't A`
}

export function WorthALook({
  drives,
  totalDrives,
}: {
  drives: OverviewDrive[]
  totalDrives: number
}) {
  const navigate = useNavigate()
  const shown = drives.slice(0, ROW_LIMIT)

  const openRow = (event: MouseEvent, href: string | null) => {
    // Let the drive link (and text selection) handle themselves.
    if (!href || (event.target as HTMLElement).closest("a")) {
      return
    }
    if (window.getSelection()?.toString()) {
      return
    }
    navigate(href)
  }

  const allDrives = (
    <Link
      to="/drives"
      className="inline-flex min-h-11 items-center font-semibold text-link hover:text-link-hover hover:underline"
    >
      All drives
    </Link>
  )

  if (drives.length === 0) {
    return (
      <PageSection id="overview-look" title="Worth a look" actions={allDrives}>
        <Note tone="ok" neutralText>
          Nothing needs a look — every drive graded A.
        </Note>
      </PageSection>
    )
  }

  return (
    <PageSection
      id="overview-look"
      title="Worth a look"
      description={describe(drives)}
      actions={allDrives}
      flush
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-6">Grade</TableHead>
            <TableHead>Drive</TableHead>
            <TableHead className="hidden lg:table-cell">Bench</TableHead>
            <TableHead className="pr-6">Why</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {shown.map((drive) => {
            const href = driveHref(drive)
            const title = driveTitle(drive.device)
            const serial = (drive.device.serial_number ?? "").trim()
            const slot = slotOf(drive.device)
            const { reason, note } = whyLines(drive)
            const benchSlot = slot
              ? `${drive.benchName} · ${slot}`
              : drive.benchName
            return (
              <TableRow
                key={drive.key}
                className={href ? "cursor-pointer" : undefined}
                onClick={(event) => openRow(event, href)}
              >
                <TableCell className="pl-6">
                  <GradeChip grade={drive.grade} />
                </TableCell>
                <TableCell className="whitespace-normal">
                  {href ? (
                    <Link
                      to={href}
                      className="font-semibold text-foreground underline-offset-4 outline-none hover:underline focus-visible:underline focus-visible:ring-3 focus-visible:ring-ring/40"
                    >
                      {title}
                    </Link>
                  ) : (
                    <span className="font-semibold">{title}</span>
                  )}{" "}
                  {serial ? (
                    <span className="font-mono text-sm whitespace-nowrap text-muted-foreground">
                      {serial}
                    </span>
                  ) : null}
                  {/* Narrow screens: bench and slot move under the drive. */}
                  <div className="text-[15px] text-muted-foreground lg:hidden">
                    {benchSlot}
                  </div>
                </TableCell>
                <TableCell className="hidden whitespace-nowrap lg:table-cell">
                  {drive.benchName}
                  {slot ? (
                    <span className="text-muted-foreground"> · {slot}</span>
                  ) : null}
                </TableCell>
                <TableCell className="min-w-[200px] pr-6 whitespace-normal">
                  {reason ? <div>{reason}</div> : null}
                  {note ? (
                    <div
                      className={
                        reason ? "text-[15px] text-muted-foreground" : undefined
                      }
                    >
                      Note: {note.charAt(0).toLowerCase() + note.slice(1)}
                    </div>
                  ) : null}
                  {!reason && !note ? (
                    <span className="text-muted-foreground">—</span>
                  ) : null}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {drives.length > shown.length ? (
        <div className="border-t px-6 py-3 text-[15px] text-muted-foreground max-sm:px-4">
          Showing the {shown.length} most important of {drives.length} (
          {totalDrives} drives in total).{" "}
          <Link
            to="/drives"
            className="font-semibold text-link hover:text-link-hover hover:underline"
          >
            See every drive
          </Link>
        </div>
      ) : null}
    </PageSection>
  )
}
