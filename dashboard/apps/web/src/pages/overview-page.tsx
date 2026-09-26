/**
 * Overview (/): "what's on my benches and what should I do with it".
 * Headline + status line, the grade bar, bench cards, and "Worth a look".
 * Everything follows the header scope switcher (all benches or one bench).
 */
import { RefreshCwIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Skeleton } from "@workspace/ui/components/skeleton"

import { Card, Note, PageHeadline } from "@/components/ui-cdi"
import { BenchesCard } from "@/pages/overview/benches-card"
import { GradesCard } from "@/pages/overview/grades-card"
import {
  headline,
  statusLine,
  useOverviewData,
  worthALook,
} from "@/pages/overview/overview-data"
import { WorthALook } from "@/pages/overview/worth-a-look"

function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <span className="sr-only">Loading the latest scans…</span>
      <div className="flex flex-col gap-2.5">
        <Skeleton className="h-10 w-80 max-w-full" />
        <Skeleton className="h-6 w-[32rem] max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-56 rounded-xl lg:col-span-2" />
        <Skeleton className="h-56 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

export function OverviewPage() {
  const data = useOverviewData()

  if (data.isLoading) {
    return <OverviewSkeleton />
  }

  if (data.error && data.drives.length === 0 && data.benches.length === 0) {
    return (
      <Card padded className="flex flex-col items-start gap-4">
        <Note tone="bad">
          Couldn&apos;t load the latest scans — check this dashboard is still
          connected, then try again.
        </Note>
        <Button variant="outline" onClick={data.retry}>
          <RefreshCwIcon data-icon="inline-start" />
          Try again
        </Button>
      </Card>
    )
  }

  const look = worthALook(data.drives)

  return (
    <div className="flex flex-col gap-6">
      <PageHeadline
        title={headline(data.drives.length, data.benches, data.scopeName)}
        subtitle={statusLine(data.counts, data.benches)}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <GradesCard
          counts={data.counts}
          benchId={data.scopeId}
          className="lg:col-span-2"
        />
        <BenchesCard benches={data.benches} scanning={data.scanning} />
      </div>
      {data.drives.length > 0 ? (
        <WorthALook drives={look} totalDrives={data.drives.length} />
      ) : null}
    </div>
  )
}
