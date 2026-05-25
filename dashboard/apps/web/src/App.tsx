import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom"

import { AppLayout } from "@/components/app-layout"
import { DashboardPage } from "@/pages/dashboard-page"
import { DiscoverPage } from "@/pages/discover-page"
import { DriveHealthPage } from "@/pages/drive-health-page"
import { HostsPage } from "@/pages/hosts-page"
import { ReportsPage } from "@/pages/reports-page"
import { ScanPage } from "@/pages/scan-page"
import { SelfTestPage } from "@/pages/self-test-page"

const pageTitles: Record<string, string> = {
  "/": "Fleet Status",
  "/hosts": "Hosts",
  "/discover": "Discover",
  "/scan": "Scan",
  "/drives": "Drive Health",
  "/reports": "Health Reports",
  "/self-test": "NVMe Self-Test",
}

function LayoutShell() {
  const location = useLocation()
  const title = pageTitles[location.pathname] ?? "CDI Health"

  return <AppLayout title={title} />
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<LayoutShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="hosts" element={<HostsPage />} />
          <Route path="discover" element={<DiscoverPage />} />
          <Route path="scan" element={<ScanPage />} />
          <Route path="drives" element={<DriveHealthPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="self-test" element={<SelfTestPage />} />
          <Route path="machines" element={<Navigate to="/hosts" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
