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

import { useSavedScanReport } from "@/hooks/use-cdi-queries"

/** Compact "Report" menu for one saved scan (History list rows). */
export function SavedScanReportMenu({ scanId }: { scanId: string }) {
  const { makeReport, isBusy } = useSavedScanReport()
  const busy = isBusy(scanId)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={busy} aria-busy={busy}>
          {busy ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <FileTextIcon data-icon="inline-start" />
          )}
          {busy ? "Making report…" : "Report"}
          <ChevronDownIcon data-icon="inline-end" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => void makeReport(scanId, "html")}>
          <ExternalLinkIcon />
          Open HTML report
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void makeReport(scanId, "csv")}>
          <DownloadIcon />
          Download CSV
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/** "HTML report" / "CSV report" buttons for one saved scan (scan detail view). */
export function SavedScanReportButtons({
  scanId,
  disabled = false,
}: {
  scanId: string
  disabled?: boolean
}) {
  const { makeReport, isBusy, anyBusy } = useSavedScanReport()

  return (
    <>
      <Button
        variant="outline"
        disabled={disabled || anyBusy}
        aria-busy={isBusy(scanId, "html")}
        onClick={() => void makeReport(scanId, "html")}
      >
        {isBusy(scanId, "html") ? <Spinner /> : <ExternalLinkIcon />}
        HTML report
      </Button>
      <Button
        variant="outline"
        disabled={disabled || anyBusy}
        aria-busy={isBusy(scanId, "csv")}
        onClick={() => void makeReport(scanId, "csv")}
      >
        {isBusy(scanId, "csv") ? <Spinner /> : <DownloadIcon />}
        CSV report
      </Button>
    </>
  )
}
