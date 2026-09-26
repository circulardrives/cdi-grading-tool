/**
 * Drive details (/drives/:benchKey/:serial?dev=<slot>&tab=<tab>): one drive
 * full screen — why its grade, every parsed log (NVMe health log 02h, OCP
 * C0h, ATA SMART attributes, SCSI counters, self-tests, errors) and the raw
 * JSON. Tabs follow the drive's protocol; ?tab= keeps the open one.
 * benchKey is the machine id, or "local" for this bench (as ?bench= on Drives).
 */
import { useCallback } from "react"
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom"
import { ArrowLeftIcon, HardDriveIcon, RefreshCwIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Skeleton } from "@workspace/ui/components/skeleton"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@workspace/ui/components/tabs"

import { Card, EmptyState, Note } from "@/components/ui-cdi"
import type { DeviceRecord } from "@/lib/types"
import { isNvme } from "@/pages/drives/drive-format"
import { benchFilterId } from "@/pages/drives/use-drive-rows"

import { dateStamp, fileSlug } from "@/pages/drive-details/details-format"
import { DriveHeader } from "@/pages/drive-details/drive-header"
import {
  NO_SERIAL,
  type DriveDetailsState,
  type DriveTab,
} from "@/pages/drive-details/drive-details-href"
import { ErrorLogTab } from "@/pages/drive-details/error-log-tab"
import { HealthLogTab } from "@/pages/drive-details/health-log-tab"
import { OcpTab } from "@/pages/drive-details/ocp-tab"
import { RawDataTab } from "@/pages/drive-details/raw-data-tab"
import { ScsiTab } from "@/pages/drive-details/scsi-tab"
import { SelfTestTab } from "@/pages/drive-details/self-test-tab"
import { SmartAttributesTab } from "@/pages/drive-details/smart-attributes-tab"
import { SummaryTab } from "@/pages/drive-details/summary-tab"
import { useDriveRecord } from "@/pages/drive-details/use-drive-record"

const TAB_LABELS: Record<DriveTab, string> = {
  summary: "Summary",
  health: "Health log",
  smart: "SMART attributes",
  scsi: "SCSI/SAS",
  ocp: "OCP C0h",
  "self-tests": "Self-test log",
  errors: "Error log",
  raw: "Raw data",
}

/** The tabs that make sense for this kind of drive. */
function tabsFor(device: DeviceRecord): DriveTab[] {
  const protocol = String(device.transport_protocol ?? "").toUpperCase()
  if (isNvme(device)) {
    return ["summary", "health", "ocp", "self-tests", "errors", "raw"]
  }
  if (protocol === "SCSI") {
    return ["summary", "scsi", "self-tests", "raw"]
  }
  if (protocol === "ATA" || Array.isArray(device.smart_attributes)) {
    return ["summary", "smart", "self-tests", "errors", "raw"]
  }
  return ["summary", "raw"]
}

function BackLink({ to }: { to: string }) {
  return (
    <Button variant="quiet" asChild className="-ml-3 w-fit">
      <Link to={to}>
        <ArrowLeftIcon data-icon="inline-start" />
        Drives
      </Link>
    </Button>
  )
}

export function DriveDetailsPage() {
  const { benchKey = "", serial = "" } = useParams()
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const state = (location.state ?? null) as DriveDetailsState | null
  const dev = params.get("dev")
  const { row, sameSerial, isLoading, error, refetch } = useDriveRecord(
    benchKey,
    serial,
    dev
  )

  const backHref =
    state?.fromDrives ??
    (serial && serial !== NO_SERIAL
      ? `/drives?${new URLSearchParams({ serial }).toString()}`
      : "/drives")

  const setTab = useCallback(
    (tab: string) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          if (tab === "summary") {
            next.delete("tab")
          } else {
            next.set("tab", tab)
          }
          return next
        },
        // Keep the router state so "← Drives" still restores the list.
        { replace: true, state: location.state }
      )
    },
    [setParams, location.state]
  )

  if (isLoading) {
    return (
      <>
        <BackLink to={backHref} />
        <Card padded className="flex flex-col gap-3" aria-busy="true">
          <span className="sr-only">Loading drive…</span>
          <Skeleton className="h-12 w-60" />
          <Skeleton className="h-8 w-96 max-w-full" />
          <Skeleton className="h-5 w-80 max-w-full" />
        </Card>
        <Skeleton className="h-12 w-full max-w-2xl" />
        <Skeleton className="h-80 w-full" />
      </>
    )
  }

  if (!row) {
    return (
      <>
        <BackLink to={backHref} />
        {error ? (
          <Card padded className="flex flex-col items-start gap-3">
            <Note tone="bad">
              Couldn't load drives — check this bench is running, then try
              again.
            </Note>
            <Button variant="outline" onClick={refetch}>
              <RefreshCwIcon data-icon="inline-start" />
              Try again
            </Button>
          </Card>
        ) : (
          <EmptyState
            icon={<HardDriveIcon />}
            title="This drive isn't in the latest scan"
            description={`No drive with serial “${serial === NO_SERIAL ? "none" : serial}” in the latest scan of this bench. It may have been unplugged — scan the bench again, or find it in Reports › Scan history.`}
            actions={
              <Button variant="outline" asChild>
                <Link to="/drives">All drives</Link>
              </Button>
            }
          />
        )}
      </>
    )
  }

  const { device } = row
  const tabs = tabsFor(device)
  const requested = params.get("tab") as DriveTab | null
  const tab: DriveTab =
    requested && tabs.includes(requested) ? requested : "summary"
  const selfTestHref = `/self-tests?${new URLSearchParams({
    bench: benchFilterId(row.benchId),
    ...(row.serial ? { serial: row.serial } : {}),
  }).toString()}`
  const fileName = [
    fileSlug(row.serial || "no-serial"),
    fileSlug(row.benchName),
    dateStamp(row.scannedAt),
  ].join("-")

  return (
    <>
      <BackLink to={backHref} />
      <DriveHeader row={row} selfTestHref={selfTestHref} />
      {sameSerial > 0 ? (
        <Note tone="warn">
          {sameSerial === 1
            ? "Another drive on this bench reports"
            : `${sameSerial} other drives on this bench report`}{" "}
          the same serial — showing the one in {row.slot || "the first slot"}.
        </Note>
      ) : null}

      <Tabs value={tab} onValueChange={setTab} className="gap-6">
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <TabsList
            aria-label="Drive details"
            className="h-auto! w-max justify-start p-1"
          >
            {tabs.map((value) => (
              <TabsTrigger
                key={value}
                value={value}
                className="h-11 flex-none px-4 text-base"
              >
                {TAB_LABELS[value]}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="summary" className="text-base">
          <SummaryTab row={row} />
        </TabsContent>
        {tabs.includes("health") ? (
          <TabsContent value="health" className="text-base">
            <HealthLogTab device={device} />
          </TabsContent>
        ) : null}
        {tabs.includes("smart") ? (
          <TabsContent value="smart" className="text-base">
            <SmartAttributesTab device={device} />
          </TabsContent>
        ) : null}
        {tabs.includes("scsi") ? (
          <TabsContent value="scsi" className="text-base">
            <ScsiTab device={device} />
          </TabsContent>
        ) : null}
        {tabs.includes("ocp") ? (
          <TabsContent value="ocp" className="text-base">
            <OcpTab device={device} />
          </TabsContent>
        ) : null}
        <TabsContent value="self-tests" className="text-base">
          <SelfTestTab
            device={device}
            selfTestHref={isNvme(device) ? selfTestHref : null}
          />
        </TabsContent>
        {tabs.includes("errors") ? (
          <TabsContent value="errors" className="text-base">
            <ErrorLogTab device={device} />
          </TabsContent>
        ) : null}
        <TabsContent value="raw" className="text-base">
          <RawDataTab device={device} fileName={fileName} />
        </TabsContent>
      </Tabs>
    </>
  )
}
