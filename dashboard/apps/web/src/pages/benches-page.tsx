/**
 * Benches (/benches): find benches on the network and manage them in one
 * place (mockup Benches.dc.html). /hosts and /discover redirect here.
 *
 * Rows: the bench this dashboard runs on (when its last scan found drives),
 * then every added bench. Each row can be scanned on its own, checked, and
 * edited; problems show as one line under the row.
 */
import { useCallback, useMemo, useState } from "react"
import { useMutationState } from "@tanstack/react-query"
import { PlusIcon, RefreshCwIcon, ServerIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@workspace/ui/components/button"

import {
  AddBenchDialog,
  EditBenchDialog,
  RemoveBenchDialog,
} from "@/components/benches/bench-dialogs"
import {
  BenchTable,
  type BenchRowState,
} from "@/components/benches/bench-table"
import { buildBenchRows, type BenchRow } from "@/components/benches/bench-utils"
import { FindBenchesCard } from "@/components/benches/find-benches-card"
import {
  useBenchProblems,
  useCheckBench,
  useNow,
  useScanBench,
} from "@/components/benches/use-bench-actions"
import {
  benchName,
  Card,
  EmptyState,
  Note,
  PageIntro,
  useBenchScope,
} from "@/components/ui-cdi"
import {
  useFleetDevicesQuery,
  useHealthQuery,
  useInvalidateCdiQueries,
  useMachinesQuery,
  useScanThisBenchMutation,
} from "@/hooks/use-cdi-queries"
import { deleteMachine } from "@/lib/api"
import { hostHasAddress } from "@/lib/host-utils"
import type { Machine } from "@/lib/types"

// Mutation keys of "Scan all benches" (hooks/use-cdi-queries.ts), so rows can
// tell a scan of every bench from a scan of this bench alone.
const FLEET_SCAN_KEY = ["scan-all", "fleet"] as const
const THIS_BENCH_SCAN_KEY = ["scan-all", "this-bench"] as const

function usePendingSince(mutationKey: readonly string[]): number | null {
  const since = useMutationState({
    filters: { mutationKey: [...mutationKey], status: "pending" },
    select: (mutation) => mutation.state.submittedAt,
  })
  return since.length > 0 ? since[since.length - 1]! : null
}

export function BenchesPage() {
  const machinesQuery = useMachinesQuery()
  const fleetQuery = useFleetDevicesQuery()
  const thisBenchHostname = useHealthQuery().data?.hostname ?? null
  const { invalidateMachines } = useInvalidateCdiQueries()
  const { scopeId, setScope } = useBenchScope()

  const { problems, setProblem } = useBenchProblems()
  const { check, isChecking } = useCheckBench(setProblem)
  const { scan, scanningSince } = useScanBench(setProblem)
  const scanThisBench = useScanThisBenchMutation()

  const fleetScanSince = usePendingSince(FLEET_SCAN_KEY)
  const thisBenchScanSince = usePendingSince(THIS_BENCH_SCAN_KEY)

  const [addOpen, setAddOpen] = useState(false)
  const [editing, setEditing] = useState<Machine | null>(null)
  const [removing, setRemoving] = useState<Machine | null>(null)
  const [removeBusy, setRemoveBusy] = useState(false)

  const rows = useMemo(
    () =>
      buildBenchRows(
        machinesQuery.data ?? [],
        fleetQuery.data,
        thisBenchHostname
      ),
    [machinesQuery.data, fleetQuery.data, thisBenchHostname]
  )

  const anyScanRunning =
    fleetScanSince != null ||
    thisBenchScanSince != null ||
    rows.some((row) => row.machine && scanningSince(row.machine.id) != null)
  // Tick every second while a scan runs (elapsed timer), else every minute.
  const now = useNow(anyScanRunning ? 1000 : 60_000)

  const stateOf = useCallback(
    (row: BenchRow): BenchRowState => {
      if (!row.machine) {
        return {
          scanning: thisBenchScanSince != null,
          scanSince: thisBenchScanSince,
          checking: false,
          problem: null,
        }
      }
      const own = scanningSince(row.machine.id)
      const inFleetScan = fleetScanSince != null && hostHasAddress(row.machine)
      return {
        scanning: own != null || inFleetScan,
        scanSince: own ?? (inFleetScan ? fleetScanSince : null),
        checking: isChecking(row.machine.id),
        problem: problems[row.machine.id] ?? null,
      }
    },
    [fleetScanSince, thisBenchScanSince, scanningSince, isChecking, problems]
  )

  const onScan = (row: BenchRow) => {
    if (row.machine) {
      scan(row.machine)
    } else {
      scanThisBench.mutate()
    }
  }

  /** After adding: check each bench so its own name and token needs show up. */
  const checkAdded = async (machines: Machine[]) => {
    const reachable = machines.filter(hostHasAddress)
    if (reachable.length === 1) {
      await check(reachable[0]!, { prefix: "Bench added" })
      return
    }
    const results = await Promise.all(
      reachable.map((machine) => check(machine, { silent: true }))
    )
    const count = machines.length
    const bad = results.filter((result) => result && !result.ok)
    if (bad.length === 0) {
      toast.success(`Added ${count} benches`)
    } else if (bad.length === 1) {
      toast.warning(`Added ${count} benches — ${bad[0]!.text}`)
    } else {
      toast.warning(
        `Added ${count} benches — ${bad.length} need attention, see the list`
      )
    }
  }

  const onSaved = async (machine: Machine) => {
    if (hostHasAddress(machine)) {
      await check(machine, { prefix: "Saved" })
    } else {
      await invalidateMachines()
      toast.success(`Saved ${benchName(machine)}`)
    }
  }

  const confirmRemove = async (machine: Machine) => {
    const name = benchName(machine)
    setRemoveBusy(true)
    try {
      await deleteMachine(machine.id)
      if (scopeId === machine.id) {
        setScope(null)
      }
      setProblem(machine.id, null)
      await invalidateMachines()
      toast.success(`Removed ${name}`)
      setRemoving(null)
    } catch (error) {
      toast.error(
        error instanceof Error && error.message
          ? `Couldn't remove ${name} — ${error.message}`
          : `Couldn't remove ${name} — try again`
      )
    } finally {
      setRemoveBusy(false)
    }
  }

  const loading = machinesQuery.isLoading
  const loadError = machinesQuery.error && !machinesQuery.data

  return (
    <>
      <PageIntro
        className="justify-between"
        actions={
          <Button variant="outline" onClick={() => setAddOpen(true)}>
            <PlusIcon data-icon="inline-start" aria-hidden="true" />
            Add by address
          </Button>
        }
      >
        The machines that grade drives. The dashboard scans each bench over the
        network.
      </PageIntro>

      <FindBenchesCard onAdded={(machines) => void checkAdded(machines)} />

      {loadError ? (
        <Card padded className="flex flex-col items-start gap-3">
          <Note tone="bad">
            Couldn&apos;t load the benches. Check this computer is still
            connected to the bench running the dashboard, then try again.
          </Note>
          <Button
            variant="outline"
            onClick={() => void machinesQuery.refetch()}
            disabled={machinesQuery.isFetching}
          >
            <RefreshCwIcon data-icon="inline-start" aria-hidden="true" />
            Try again
          </Button>
        </Card>
      ) : !loading && rows.length === 0 ? (
        <EmptyState
          icon={<ServerIcon />}
          title="No benches yet"
          description="Search the network above, or add a bench by its address."
          actions={
            <Button onClick={() => setAddOpen(true)}>
              <PlusIcon data-icon="inline-start" aria-hidden="true" />
              Add by address
            </Button>
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <BenchTable
            rows={rows}
            loading={loading}
            now={now}
            stateOf={stateOf}
            scanAllRunning={fleetScanSince != null}
            onScan={onScan}
            onCheck={(machine) => void check(machine)}
            onEdit={setEditing}
          />
        </Card>
      )}

      <Note
        tone="info"
        neutralText
        className="text-[15px] text-muted-foreground"
      >
        Bench names come from each bench itself. Rack and location are optional
        — add them under Edit.
      </Note>

      <AddBenchDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onAdded={(machine) => void checkAdded([machine])}
      />
      <EditBenchDialog
        machine={editing}
        onClose={() => setEditing(null)}
        onSaved={(machine) => void onSaved(machine)}
        onRemove={(machine) => {
          setEditing(null)
          setRemoving(machine)
        }}
      />
      <RemoveBenchDialog
        machine={removing}
        removing={removeBusy}
        onCancel={() => setRemoving(null)}
        onConfirm={(machine) => void confirmRemove(machine)}
      />
    </>
  )
}
