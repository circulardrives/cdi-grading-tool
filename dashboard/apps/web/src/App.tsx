import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom"

import { Spinner } from "@workspace/ui/components/spinner"

import { AppLayout } from "@/components/app-layout"

const DashboardPage = lazy(() =>
  import("@/pages/dashboard-page").then((m) => ({ default: m.DashboardPage }))
)
const DiscoverPage = lazy(() =>
  import("@/pages/discover-page").then((m) => ({ default: m.DiscoverPage }))
)
const DriveHealthPage = lazy(() =>
  import("@/pages/drive-health-page").then((m) => ({ default: m.DriveHealthPage }))
)
const HistoryPage = lazy(() =>
  import("@/pages/history-page").then((m) => ({ default: m.HistoryPage }))
)
const HostsPage = lazy(() =>
  import("@/pages/hosts-page").then((m) => ({ default: m.HostsPage }))
)
const ReportsPage = lazy(() =>
  import("@/pages/reports-page").then((m) => ({ default: m.ReportsPage }))
)
const ScanPage = lazy(() =>
  import("@/pages/scan-page").then((m) => ({ default: m.ScanPage }))
)
const SelfTestPage = lazy(() =>
  import("@/pages/self-test-page").then((m) => ({ default: m.SelfTestPage }))
)

const pageTitles: Record<string, string> = {
  "/": "Fleet Status",
  "/hosts": "Hosts",
  "/discover": "Discover",
  "/scan": "Scan",
  "/drives": "Drive Health",
  "/history": "Scan History",
  "/reports": "Health Reports",
  "/self-test": "NVMe Self-Test",
}

function PageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner />
    </div>
  )
}

function LayoutShell() {
  const location = useLocation()
  const title = location.pathname.startsWith("/history")
    ? "Scan History"
    : (pageTitles[location.pathname] ?? "CDI Health")

  return <AppLayout title={title} />
}

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<LayoutShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="hosts" element={<HostsPage />} />
            <Route path="discover" element={<DiscoverPage />} />
            <Route path="scan" element={<ScanPage />} />
            <Route path="drives" element={<DriveHealthPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="history/:scanId" element={<HistoryPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="self-test" element={<SelfTestPage />} />
            <Route path="machines" element={<Navigate to="/hosts" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
