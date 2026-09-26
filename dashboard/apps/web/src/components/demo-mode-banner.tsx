/**
 * Full-width banner across the top of every page while Demo mode (sample
 * drives instead of real benches) is on. Turned on/off in Settings.
 */
import { FlaskConicalIcon } from "lucide-react"

import { useMockDataSettings } from "@/components/mock-data-provider"

export function DemoModeBanner() {
  const { useMockData, setUseMockData } = useMockDataSettings()
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
