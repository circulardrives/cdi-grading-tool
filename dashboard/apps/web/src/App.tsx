import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom"

import { AppLayout } from "@/components/app-layout"
import { DashboardPage } from "@/pages/dashboard-page"
import { DriveHealthPage } from "@/pages/drive-health-page"
import { MachinesPage } from "@/pages/machines-page"
import { ReportsPage } from "@/pages/reports-page"
import { SelfTestPage } from "@/pages/self-test-page"

const pageTitles: Record<string, string> = {
  "/": "Fleet Status",
  "/drives": "Drive Health",
  "/machines": "Hosts & Scans",
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
          <Route path="drives" element={<DriveHealthPage />} />
          <Route path="machines" element={<MachinesPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="self-test" element={<SelfTestPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
