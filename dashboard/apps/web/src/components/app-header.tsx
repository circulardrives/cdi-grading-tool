/**
 * Page header on every page: sidebar toggle, page title, optional
 * "All benches (N) ▾" scope switcher, "Last scan … · …", and the primary
 * "Scan all benches" button. The Demo mode banner sits above it and the
 * scan progress bar right under it; all three stay stuck to the top.
 */
import { CheckIcon, ChevronDownIcon, ServerIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@workspace/ui/components/dropdown-menu"
import { SidebarTrigger } from "@workspace/ui/components/sidebar"

import { DemoModeBanner } from "@/components/demo-mode-banner"
import {
  ScanAllBenchesButton,
  ScanAllProgressBar,
} from "@/components/scan-all-hosts"
import { benchAddress, benchName } from "@/components/ui-cdi/bench"
import {
  useFleetDevicesQuery,
  useScanAllBenches,
} from "@/hooks/use-cdi-queries"
import { useBenchScope, useLastScan } from "@/components/ui-cdi/use-benches"

function formatScanTime(at: Date, now = new Date()): string {
  const sameDay = at.toDateString() === now.toDateString()
  const time = at.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  if (sameDay) {
    return time
  }
  return `${at.toLocaleDateString([], { month: "short", day: "numeric" })}, ${time}`
}

function ScopeSwitcher() {
  const { scopeId, setScope, scopedBench, benches } = useBenchScope()
  // "All" also covers the bench this dashboard runs on once it has drives, so
  // the count matches the Overview headline ("14 drives on 3 benches").
  const thisBenchHasDrives = (useFleetDevicesQuery().data?.hosts ?? []).some(
    (host) => host.machine_id === null && host.device_count > 0
  )
  if (benches.length === 0) {
    return null
  }
  const allCount = benches.length + (thisBenchHasDrives ? 1 : 0)
  const label = scopedBench
    ? benchName(scopedBench)
    : `All benches (${allCount})`

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="max-w-64"
          aria-label={`Showing ${label}. Change bench`}
        >
          <ServerIcon data-icon="inline-start" aria-hidden="true" />
          <span className="truncate">{label}</span>
          <ChevronDownIcon data-icon="inline-end" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="min-w-64">
        <DropdownMenuLabel>Show drives from</DropdownMenuLabel>
        <DropdownMenuItem
          className="min-h-11 text-base"
          onSelect={() => setScope(null)}
        >
          <CheckIcon
            aria-hidden="true"
            className={scopeId ? "invisible" : undefined}
          />
          All benches ({allCount})
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {benches.map((bench) => (
          <DropdownMenuItem
            key={bench.id}
            className="min-h-11 text-base"
            onSelect={() => setScope(bench.id)}
          >
            <CheckIcon
              aria-hidden="true"
              className={scopeId === bench.id ? undefined : "invisible"}
            />
            <span className="flex min-w-0 flex-col leading-tight">
              <span className="truncate font-semibold">{benchName(bench)}</span>
              <span className="truncate font-mono text-sm text-muted-foreground">
                {benchAddress(bench)}
              </span>
            </span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function LastScanLine() {
  const { at, label } = useLastScan()
  if (!at) {
    return null
  }
  return (
    <span className="text-[15px] whitespace-nowrap text-muted-foreground max-lg:hidden">
      Last scan {formatScanTime(at)}
      {label ? ` · ${label}` : ""}
    </span>
  )
}

export function AppHeader({
  title,
  showScope,
}: {
  title: string
  showScope: boolean
}) {
  const { benches } = useBenchScope()
  const { scansThisBenchOnly } = useScanAllBenches()

  return (
    <div className="sticky top-0 z-20 border-b bg-card">
      <DemoModeBanner />
      <header className="flex min-h-[76px] flex-wrap items-center gap-x-4 gap-y-2 px-8 py-3 max-md:min-h-16 max-md:gap-x-2 max-md:px-4">
        <SidebarTrigger
          className="-ml-2 size-11 xl:hidden"
          aria-label="Show or hide navigation"
        />
        <h1 className="text-[26px] leading-tight font-bold max-md:text-[22px]">
          {title}
        </h1>
        {showScope ? <ScopeSwitcher /> : null}
        <div className="flex-1" />
        <LastScanLine />
        <ScanAllBenchesButton className="max-sm:hidden" />
        <ScanAllBenchesButton className="sm:hidden" compact />
      </header>
      <ScanAllProgressBar
        benchCount={benches.length || undefined}
        thisBenchOnly={scansThisBenchOnly}
      />
    </div>
  )
}
