/**
 * Self-tests (/self-tests): pick a bench, pick drives, start a short or
 * extended self-test, watch it, stop it. /self-test redirects here.
 *
 * URL: ?bench=<bench id | local> picks the bench, ?serial=<sn> preselects a drive.
 */
import { useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { ActivityIcon, RefreshCwIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Skeleton } from "@workspace/ui/components/skeleton"

import { useMockDataSettings } from "@/components/mock-data-provider"
import {
  BenchPicker,
  type BenchOption,
} from "@/components/self-tests/bench-picker"
import { DriveList } from "@/components/self-tests/drive-list"
import { RecentResults } from "@/components/self-tests/recent-results"
import { hasStaleSelfTestApi } from "@/components/self-tests/self-test-format"
import {
  BenchProblemLine,
  EmptyState,
  Note,
  benchName,
  useBenchScope,
} from "@/components/ui-cdi"
import { useFleetDevicesQuery, useMachinesQuery } from "@/hooks/use-cdi-queries"
import { useSelfTestBench } from "@/hooks/use-self-test-polling"

const THIS_BENCH = "local"

/** Benches with an address, then "This bench" when it has drives (or is the only one). */
function useBenchOptions() {
  const { benches, scopeId, isLoading } = useBenchScope()
  const fleet = useFleetDevicesQuery()
  const machines = useMachinesQuery()

  const options = useMemo<BenchOption[]>(() => {
    const remote: BenchOption[] = benches.map((machine) => ({
      value: machine.id,
      machineId: machine.id,
      name: benchName(machine),
      status: machine.status,
    }))
    const thisBench = fleet.data?.hosts.find((host) => !host.machine_id)
    const thisBenchHasDrives = (thisBench?.device_count ?? 0) > 0
    if (thisBenchHasDrives || remote.length === 0) {
      remote.push({
        value: THIS_BENCH,
        machineId: null,
        name: "This bench",
        status: "",
      })
    }
    return remote
  }, [benches, fleet.data])

  return {
    options,
    scopeId,
    fleetDevices: fleet.data?.devices ?? [],
    loading: isLoading || fleet.isPending,
    // The dashboard's own service didn't answer (e.g. restarting): say so
    // instead of showing a skeleton forever or an empty "This bench".
    unreachable:
      (fleet.isError && !fleet.data) || (machines.isError && !machines.data),
    retry: () => {
      void fleet.refetch()
      void machines.refetch()
    },
  }
}

export function SelfTestsPage() {
  const [params, setParams] = useSearchParams()
  const { options, scopeId, fleetDevices, loading, unreachable, retry } =
    useBenchOptions()
  const serialParam = params.get("serial")?.trim() || null
  const benchParam = params.get("bench")

  const valid = (value: string | null | undefined) =>
    value ? options.some((option) => option.value === value) : false

  const current = valid(benchParam) ? benchParam : null

  // Pick a default once the bench list is in, and write it to the URL so it
  // doesn't jump when a bench's status changes under a running test.
  useEffect(() => {
    if (loading || current) {
      return
    }
    const fromSerial = serialParam
      ? fleetDevices.find((device) => device.serial_number === serialParam)
      : undefined
    const serialBench = fromSerial
      ? (fromSerial.machine_id ?? THIS_BENCH)
      : null
    const online = options.find((option) => option.status === "reachable")
    const choice =
      (valid(serialBench) && serialBench) ||
      (valid(scopeId) && scopeId) ||
      online?.value ||
      options[0]?.value
    if (!choice) {
      return
    }
    const next = new URLSearchParams(params)
    next.set("bench", choice)
    setParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, current, options, scopeId, serialParam, fleetDevices])

  const pick = (value: string) => {
    if (value === current) {
      return
    }
    setParams({ bench: value }, { replace: true })
  }

  const bench = options.find((option) => option.value === current) ?? null

  if (unreachable) {
    return (
      <EmptyState
        icon={<ActivityIcon aria-hidden="true" />}
        title="Can't load benches right now"
        description="The dashboard's service didn't answer. It may be restarting — try again in a moment."
        actions={
          <Button variant="outline" onClick={retry}>
            <RefreshCwIcon data-icon="inline-start" aria-hidden="true" />
            Try again
          </Button>
        }
      />
    )
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        {bench ? (
          <BenchPicker options={options} value={bench.value} onChange={pick} />
        ) : (
          <Skeleton className="h-[54px] w-64 rounded-[10px]" />
        )}
        <p className="text-base text-muted-foreground">
          Tests run on the bench and keep going if you close this page.
        </p>
      </div>

      {bench ? (
        // Keyed by bench: switching bench starts from a clean selection.
        <BenchSelfTests
          key={bench.value}
          machineId={bench.machineId}
          name={bench.machineId ? bench.name : "this bench"}
          status={bench.status}
          preselectSerial={serialParam}
        />
      ) : (
        <Skeleton className="h-72 w-full rounded-[14px]" />
      )}
    </>
  )
}

function BenchSelfTests({
  machineId,
  name,
  status,
  preselectSerial,
}: {
  machineId: string | null
  name: string
  status: string
  preselectSerial: string | null
}) {
  const { useMockData } = useMockDataSettings()
  const {
    drives,
    statusDevices,
    loading,
    error,
    retry,
    retrying,
    scanMissing,
    scanLoading,
    queue,
    start,
    stop,
    stopping,
  } = useSelfTestBench({ machineId, benchName: name })
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const { rows, otherDrives, unnamed } = drives

  // ?serial=<sn> preselects that drive once its row shows up.
  const preselected = useRef(false)
  useEffect(() => {
    if (
      preselected.current ||
      !preselectSerial ||
      scanLoading ||
      rows.length === 0
    ) {
      return
    }
    preselected.current = true
    const row = rows.find(
      (candidate) =>
        candidate.serial === preselectSerial && !candidate.unavailable
    )
    if (row) {
      setSelected(new Set([row.device]))
    }
  }, [rows, preselectSerial, scanLoading])

  const stale = statusDevices ? hasStaleSelfTestApi(statusDevices) : false
  // The saved scan has NVMe drives but the bench lists none for self-tests.
  const seesNone = !error && statusDevices?.length === 0 && rows.length > 0
  const showEmpty = !loading && !error && rows.length === 0
  const showList = loading || rows.length > 0

  return (
    <>
      {error ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <BenchProblemLine name={name} status={status} error={error} />
          <Button
            variant="outline"
            size="sm"
            onClick={() => void retry()}
            disabled={retrying}
          >
            <RefreshCwIcon data-icon="inline-start" aria-hidden="true" />
            {retrying ? "Trying…" : "Try again"}
          </Button>
        </div>
      ) : null}

      {stale ? (
        <Note tone="warn">
          CDI Health on {name} is out of date, so test results don't show here —
          update it on that bench.
        </Note>
      ) : null}

      {seesNone ? (
        <Note tone="warn">
          {machineId ? name : "This bench"} doesn't see any NVMe drives to test
          right now. Check the drives are seated and the NVMe tools are
          installed there, then scan again.
        </Note>
      ) : null}

      {useMockData ? (
        <Note tone="info">
          Demo mode is on. Self-tests still run on the bench's real drives.
        </Note>
      ) : null}

      {showEmpty ? (
        <EmptyState
          icon={<ActivityIcon />}
          title={`No NVMe drives on ${name}`}
          description="Plug NVMe drives in, then scan the bench. Self-tests run on NVMe drives for now."
        />
      ) : null}

      {showList ? (
        <DriveList
          benchName={name}
          rows={rows}
          loading={loading}
          blocked={Boolean(error)}
          selected={selected}
          onSelectedChange={setSelected}
          queue={queue}
          stopping={stopping}
          onStart={start}
          onStop={(devices) => void stop(devices)}
        />
      ) : null}

      {!loading && unnamed > 0 ? (
        <Note tone="info">
          {scanMissing
            ? `Scan ${name} to see serial numbers and drive names.`
            : `Some drives have no serial number yet — scan ${name} again to fill them in.`}
        </Note>
      ) : null}

      <RecentResults rows={rows} />

      <p className="text-[15px] text-muted-foreground">
        NVMe drives only for now.
        {otherDrives > 0
          ? ` ${otherDrives === 1 ? "1 SATA or SAS drive" : `${otherDrives} SATA and SAS drives`} on ${name} ${otherDrives === 1 ? "isn't" : "aren't"} listed.`
          : ""}{" "}
        SATA and SAS self-tests are planned.
      </p>
    </>
  )
}
