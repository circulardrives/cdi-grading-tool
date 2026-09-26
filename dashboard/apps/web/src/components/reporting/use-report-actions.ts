/**
 * Report hooks for the Reports page, Scan history, and a saved scan:
 *
 * - usePdfAvailability()    whether this bench can make PDFs (and a way to learn it can't)
 * - useReportFileActions()  Open (new tab) / Download for a made report, with busy state
 * - useScanReport()         make a report from saved scans, then open or download it
 */
import { useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { useBenchNames } from "@/components/ui-cdi"
import {
  useGenerateReportMutation,
  useHealthQuery,
} from "@/hooks/use-cdi-queries"
import { downloadReportFile, openReportFile } from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"
import {
  deliverReport,
  describeReportError,
  isPdfUnavailableError,
  OLD_API_REPORT_MESSAGE,
  reportFileOf,
  reportIgnoredSource,
  reportReadyMessage,
} from "@/lib/report-utils"
import type { HealthResponse, ReportFormat } from "@/lib/types"

/**
 * PDF needs an extra library on the bench that serves this dashboard. The
 * bench says so in its health answer; a failed PDF report teaches us too.
 */
export function usePdfAvailability() {
  const queryClient = useQueryClient()
  const health = useHealthQuery().data
  return {
    // Unknown (older bench, or a short health answer) counts as available.
    pdfAvailable: health?.weasyprint_available !== false,
    markPdfUnavailable: () =>
      queryClient.setQueryData<HealthResponse>(queryKeys.health, (current) =>
        current
          ? { ...current, weasyprint_available: false }
          : { status: "ok", weasyprint_available: false }
      ),
  }
}

/** Open / Download for one made report file. */
export function useReportFileActions() {
  const [busy, setBusy] = useState<string | null>(null)

  const run = async (
    key: string,
    action: () => Promise<void>,
    failure: string
  ) => {
    setBusy(key)
    try {
      await action()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : failure)
    } finally {
      setBusy(null)
    }
  }

  return {
    open: (filename: string) =>
      run(
        `${filename}:open`,
        () => openReportFile(filename),
        "Couldn't open the report"
      ),
    download: (filename: string) =>
      run(
        `${filename}:download`,
        () => downloadReportFile(filename),
        "Couldn't download the report"
      ),
    isBusy: (filename: string, action: "open" | "download") =>
      busy === `${filename}:${action}`,
  }
}

/**
 * Report from saved scans, opened (PDF, web page) or downloaded
 * (spreadsheet) when ready. Grades stay as they were at scan time.
 */
export function useScanReport() {
  const generate = useGenerateReportMutation()
  const { markPdfUnavailable } = usePdfAvailability()
  const nameOf = useBenchNames()
  const [busyKey, setBusyKey] = useState<string | null>(null)

  const makeReport = async (scanId: string, format: ReportFormat) => {
    setBusyKey(`${scanId}:${format}`)
    try {
      const result = await generate.mutateAsync({
        format,
        source: "history",
        history_ids: [scanId],
      })
      if (reportIgnoredSource("history", result)) {
        toast.warning(OLD_API_REPORT_MESSAGE)
      } else {
        toast.success(
          reportReadyMessage(result, (host) =>
            nameOf(host.machine_id, host.name)
          )
        )
      }
      await deliverReport(reportFileOf(result), format)
    } catch (error) {
      if (format === "pdf" && isPdfUnavailableError(error)) {
        markPdfUnavailable()
      }
      toast.error(describeReportError(error))
    } finally {
      setBusyKey(null)
    }
  }

  return {
    makeReport,
    isBusy: (scanId: string, format?: ReportFormat) =>
      format
        ? busyKey === `${scanId}:${format}`
        : busyKey?.startsWith(`${scanId}:`) === true,
    anyBusy: busyKey != null,
  }
}
