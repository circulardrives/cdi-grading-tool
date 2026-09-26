/**
 * Reports (/reports): New report + Recent reports, with Scan history as a
 * second tab (/reports?tab=history). A saved scan opens at
 * /reports/history/:scanId. /history and /history/:id redirect here.
 * Pieces live in components/reporting/ (a folder named "reports" is gitignored).
 */
import { useParams, useSearchParams } from "react-router-dom"

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"

import { NewReportCard } from "@/components/reporting/new-report-card"
import { RecentReportsCard } from "@/components/reporting/recent-reports-card"
import { SavedScanDetail } from "@/components/reporting/saved-scan-detail"
import { ScanHistoryTab } from "@/components/reporting/scan-history-tab"
import { useBenchScope } from "@/components/ui-cdi"

type ReportsTab = "reports" | "history"

function ReportsTabBody() {
  const { scopeId } = useBenchScope()
  return (
    <div className="grid items-start gap-6 lg:grid-cols-5">
      {/* A new bench scope starts a fresh choice (picked scans are per bench). */}
      <NewReportCard key={scopeId ?? "all"} className="lg:col-span-3" />
      <RecentReportsCard className="lg:col-span-2" />
    </div>
  )
}

export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab: ReportsTab =
    searchParams.get("tab") === "history" ? "history" : "reports"

  return (
    <Tabs
      value={tab}
      onValueChange={(value) =>
        setSearchParams(value === "history" ? { tab: "history" } : {}, {
          replace: true,
        })
      }
      className="flex flex-col gap-6"
    >
      <TabsList className="h-auto! p-1">
        <TabsTrigger value="reports" className="h-11 px-4 text-base">
          Reports
        </TabsTrigger>
        <TabsTrigger value="history" className="h-11 px-4 text-base">
          Scan history
        </TabsTrigger>
      </TabsList>
      <TabsContent value="reports" className="flex flex-col gap-6 text-base">
        <ReportsTabBody />
      </TabsContent>
      <TabsContent value="history" className="flex flex-col gap-6 text-base">
        <ScanHistoryTab />
      </TabsContent>
    </Tabs>
  )
}

/** /reports/history/:scanId — one saved scan. */
export function SavedScanPage() {
  const { scanId = "" } = useParams()
  return <SavedScanDetail key={scanId} scanId={scanId} />
}
