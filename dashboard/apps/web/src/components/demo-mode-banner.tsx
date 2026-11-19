/**
 * Full-width banner across the top of every page while Demo mode (sample
 * drives instead of real benches) is on. Turned on/off in Settings.
 *
 * The static public demo build (VITE_DEMO=1) always shows its own banner
 * instead, linking to the project.
 */
import { ExternalLinkIcon, FlaskConicalIcon } from "lucide-react"

import { useMockDataSettings } from "@/components/mock-data-provider"

const PROJECT_URL = "https://github.com/circulardrives/cdi-grading-tool"

function StaticDemoBanner() {
  return (
    <div
      role="status"
      className="flex min-h-11 flex-wrap items-center justify-center gap-x-3 gap-y-0.5 bg-banner-demo px-4 py-1.5 text-base font-semibold text-banner-demo-fg"
    >
      <FlaskConicalIcon
        className="size-5 shrink-0 max-sm:hidden"
        aria-hidden="true"
      />
      <span className="min-w-0">Demo — sample drives, not real benches</span>
      <span aria-hidden="true" className="max-sm:hidden">
        ·
      </span>
      <a
        href={PROJECT_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-md px-2 underline underline-offset-4 outline-none hover:no-underline focus-visible:ring-3 focus-visible:ring-current/50"
      >
        Get CDI Health on GitHub
        <ExternalLinkIcon className="size-4" aria-hidden="true" />
      </a>
    </div>
  )
}

export function DemoModeBanner() {
  const { useMockData, setUseMockData } = useMockDataSettings()
  if (__CDI_DEMO__) {
    return <StaticDemoBanner />
  }
  if (!useMockData) {
    return null
  }
  return (
    <div
      role="status"
      className="flex min-h-11 items-center justify-center gap-3 bg-banner-demo px-4 py-1.5 text-base font-semibold text-banner-demo-fg"
    >
      <FlaskConicalIcon
        className="size-5 shrink-0 max-sm:hidden"
        aria-hidden="true"
      />
      <span className="min-w-0">
        Demo mode — showing sample drives, not real benches
      </span>
      <span aria-hidden="true" className="max-sm:hidden">
        ·
      </span>
      <button
        type="button"
        onClick={() => setUseMockData(false)}
        className="min-h-9 shrink-0 rounded-md px-2 underline underline-offset-4 outline-none hover:no-underline focus-visible:ring-3 focus-visible:ring-current/50"
      >
        Turn off
      </button>
    </div>
  )
}
