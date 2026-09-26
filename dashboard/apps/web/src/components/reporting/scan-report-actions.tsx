/**
 * "Report" actions for one saved scan: a menu for Scan history rows and a
 * button row for the saved scan page. PDF / Web page open in a new tab;
 * Spreadsheet downloads.
 */
import {
  ChevronDownIcon,
  DownloadIcon,
  ExternalLinkIcon,
  FileTextIcon,
} from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@workspace/ui/components/dropdown-menu"
import { Spinner } from "@workspace/ui/components/spinner"

import {
  usePdfAvailability,
  useScanReport,
} from "@/components/reporting/use-report-actions"
import {
  PDF_UNAVAILABLE_MESSAGE,
  REPORT_FORMAT_LABEL,
  REPORT_FORMAT_SHORT,
  REPORT_FORMATS,
} from "@/lib/report-utils"
import type { ReportFormat } from "@/lib/types"

const FORMAT_ICON: Record<ReportFormat, typeof FileTextIcon> = {
  pdf: FileTextIcon,
  html: ExternalLinkIcon,
  csv: DownloadIcon,
}

/** Row menu: Report ▾ → PDF / Web page / Spreadsheet. */
export function ScanReportMenu({
  scanId,
  label,
}: {
  scanId: string
  /** Accessible name, e.g. "Report on bench-01, 9:00 AM". */
  label: string
}) {
  const { makeReport, isBusy } = useScanReport()
  const { pdfAvailable } = usePdfAvailability()
  const busy = isBusy(scanId)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="quiet"
          disabled={busy}
          aria-busy={busy}
          aria-label={label}
        >
          {busy ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <FileTextIcon data-icon="inline-start" />
          )}
          {busy ? "Making report…" : "Report"}
          <ChevronDownIcon data-icon="inline-end" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        {REPORT_FORMATS.map((format) => {
          const Icon = FORMAT_ICON[format]
          const unavailable = format === "pdf" && !pdfAvailable
          return (
            <DropdownMenuItem
              key={format}
              className="min-h-11 text-base"
              disabled={unavailable}
              onSelect={() => void makeReport(scanId, format)}
            >
              <Icon />
              <span className="flex flex-col">
                {REPORT_FORMAT_SHORT[format]}
                {unavailable ? (
                  <span className="text-sm text-muted-foreground">
                    Not available on this bench
                  </span>
                ) : null}
              </span>
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/** Saved scan page: one button per format. */
export function ScanReportButtons({
  scanId,
  disabled = false,
}: {
  scanId: string
  disabled?: boolean
}) {
  const { makeReport, isBusy, anyBusy } = useScanReport()
  const { pdfAvailable } = usePdfAvailability()
  const formats = REPORT_FORMATS.filter(
    (format) => format !== "pdf" || pdfAvailable
  )

  return (
    <div className="flex flex-col gap-2">
      <div
        role="group"
        aria-label="Make a report from this scan"
        className="flex flex-wrap gap-2"
      >
        {formats.map((format, index) => {
          const Icon = FORMAT_ICON[format]
          const busy = isBusy(scanId, format)
          return (
            <Button
              key={format}
              variant={index === 0 ? "default" : "outline"}
              disabled={disabled || anyBusy}
              aria-busy={busy}
              onClick={() => void makeReport(scanId, format)}
            >
              {busy ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <Icon data-icon="inline-start" />
              )}
              {REPORT_FORMAT_LABEL[format]}
            </Button>
          )
        })}
      </div>
      {!pdfAvailable ? (
        <p className="text-[15px] text-muted-foreground">
          {PDF_UNAVAILABLE_MESSAGE}
        </p>
      ) : null}
    </div>
  )
}
