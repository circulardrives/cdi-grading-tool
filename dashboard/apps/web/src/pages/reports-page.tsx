/**
 * Reports (/reports): new report + recent reports, with Scan history as a
 * second tab (/reports?tab=history). A saved scan opens at
 * /reports/history/:scanId. /history and /history/:id redirect here.
 * PLACEHOLDER bodies — the pre-redesign Reports and History pages render
 * inside the tabs until the Reports page agent replaces them (see
 * components/ui-cdi/README.md and the Reports mockup).
 */
import { useParams, useSearchParams } from "react-router-dom"

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"

import { HistoryPage } from "@/pages/legacy/history-page"
import { ReportsPage as LegacyReportsPage } from "@/pages/legacy/reports-page"

type ReportsTab = "reports" | "history"

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
      <TabsList className="h-12! p-1">
        <TabsTrigger value="reports" className="h-10 px-4 text-base">
          Reports
        </TabsTrigger>
        <TabsTrigger value="history" className="h-10 px-4 text-base">
          Scan history
        </TabsTrigger>
      </TabsList>
      <TabsContent value="reports" className="flex flex-col gap-6 text-base">
        <LegacyReportsPage />
      </TabsContent>
      <TabsContent value="history" className="flex flex-col gap-6 text-base">
        <HistoryPage />
      </TabsContent>
    </Tabs>
  )
}

/** /reports/history/:scanId — one saved scan (legacy History detail for now). */
export function SavedScanPage() {
  const { scanId } = useParams()
  return <HistoryPage key={scanId} />
}
