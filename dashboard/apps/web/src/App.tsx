import { lazy, Suspense } from "react"
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useParams,
} from "react-router-dom"

import { Spinner } from "@workspace/ui/components/spinner"

import { AppLayout } from "@/components/app-layout"

const OverviewPage = lazy(() =>
  import("@/pages/overview-page").then((m) => ({ default: m.OverviewPage }))
)
const DrivesPage = lazy(() =>
  import("@/pages/drives-page").then((m) => ({ default: m.DrivesPage }))
)
const DriveDetailsPage = lazy(() =>
  import("@/pages/drive-details-page").then((m) => ({
    default: m.DriveDetailsPage,
  }))
)
const BenchesPage = lazy(() =>
  import("@/pages/benches-page").then((m) => ({ default: m.BenchesPage }))
)
const SelfTestsPage = lazy(() =>
  import("@/pages/self-tests-page").then((m) => ({
    default: m.SelfTestsPage,
  }))
)
const ReportsPage = lazy(() =>
  import("@/pages/reports-page").then((m) => ({ default: m.ReportsPage }))
)
const SavedScanPage = lazy(() =>
  import("@/pages/reports-page").then((m) => ({ default: m.SavedScanPage }))
)
const SettingsPage = lazy(() =>
  import("@/pages/settings-page").then((m) => ({ default: m.SettingsPage }))
)

function PageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner />
    </div>
  )
}

/** /history/:scanId → /reports/history/:scanId */
function SavedScanRedirect() {
  const { scanId = "" } = useParams()
  return (
    <Navigate to={`/reports/history/${encodeURIComponent(scanId)}`} replace />
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<PageFallback />}>
                <OverviewPage />
              </Suspense>
            }
          />
          <Route
            path="drives"
            element={
              <Suspense fallback={<PageFallback />}>
                <DrivesPage />
              </Suspense>
            }
          />
          <Route
            path="drives/:benchKey/:serial"
            element={
              <Suspense fallback={<PageFallback />}>
                <DriveDetailsPage />
              </Suspense>
            }
          />
          <Route
            path="benches"
            element={
              <Suspense fallback={<PageFallback />}>
                <BenchesPage />
              </Suspense>
            }
          />
          <Route
            path="self-tests"
            element={
              <Suspense fallback={<PageFallback />}>
                <SelfTestsPage />
              </Suspense>
            }
          />
          <Route
            path="reports"
            element={
              <Suspense fallback={<PageFallback />}>
                <ReportsPage />
              </Suspense>
            }
          />
          <Route
            path="reports/history/:scanId"
            element={
              <Suspense fallback={<PageFallback />}>
                <SavedScanPage />
              </Suspense>
            }
          />
          <Route
            path="settings"
            element={
              <Suspense fallback={<PageFallback />}>
                <SettingsPage />
              </Suspense>
            }
          />

          {/* Old paths from before the redesign. */}
          <Route path="hosts" element={<Navigate to="/benches" replace />} />
          <Route path="machines" element={<Navigate to="/benches" replace />} />
          <Route path="discover" element={<Navigate to="/benches" replace />} />
          <Route path="scan" element={<Navigate to="/" replace />} />
          <Route
            path="history"
            element={<Navigate to="/reports?tab=history" replace />}
          />
          <Route path="history/:scanId" element={<SavedScanRedirect />} />
          <Route
            path="self-test"
            element={<Navigate to="/self-tests" replace />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
