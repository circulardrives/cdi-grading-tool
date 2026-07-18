import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  HardDriveIcon,
  PencilIcon,
  PlusIcon,
  RefreshCwIcon,
  ScanSearchIcon,
  ServerIcon,
  Trash2Icon,
} from "lucide-react"
import { toast } from "sonner"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@workspace/ui/components/alert-dialog"
import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@workspace/ui/components/dialog"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import {
  Field,
  FieldGroup,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { Skeleton } from "@workspace/ui/components/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { Textarea } from "@workspace/ui/components/textarea"

import { PageHeader } from "@/components/page-header"
import {
  useInvalidateCdiQueries,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import {
  createMachine,
  deleteMachine,
  updateMachine,
} from "@/lib/api"
import {
  emptyHostForm,
  formatScanSummary,
  machineStatusBadgeVariant,
  type HostFormState,
} from "@/lib/host-utils"
import { getSelectedHostId, setSelectedHostId } from "@/lib/selected-host"
import type { Machine, MachineCreateRequest } from "@/lib/types"

export function HostsPage() {
  const machinesQuery = useMachinesQuery()
  const { invalidateMachines } = useInvalidateCdiQueries()
  const hosts = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const loading = machinesQuery.isLoading
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingHost, setEditingHost] = useState<Machine | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Machine | null>(null)
  const [selectedHostId, setSelectedHostIdState] = useState<string | null>(
    () => getSelectedHostId()
  )
  const [form, setForm] = useState<HostFormState>(emptyHostForm)

  const selectedHost = useMemo(
    () => hosts.find((host) => host.id === selectedHostId) ?? null,
    [hosts, selectedHostId]
  )

  const refresh = async () => {
    const result = await machinesQuery.refetch()
    if (result.error) {
      toast.error(
        result.error instanceof Error
          ? result.error.message
          : "Failed to load hosts"
      )
    }
  }

  const openCreateDialog = () => {
    setEditingHost(null)
    setForm(emptyHostForm)
    setDialogOpen(true)
  }

  const openEditDialog = (host: Machine) => {
    setEditingHost(host)
    setForm({
      name: host.name,
      hostname: host.hostname,
      address: host.address,
      location: host.location,
      notes: host.notes,
    })
    setDialogOpen(true)
  }

  const selectHost = (hostId: string | null) => {
    setSelectedHostIdState(hostId)
    setSelectedHostId(hostId)
  }

  const submitHost = async () => {
    if (!form.name.trim() || !form.hostname.trim()) {
      toast.error("Display name and hostname are required")
      return
    }

    const payload: MachineCreateRequest = {
      name: form.name.trim(),
      hostname: form.hostname.trim(),
      address: form.address.trim(),
      location: form.location.trim(),
      notes: form.notes.trim(),
    }

    try {
      if (editingHost) {
        const updated = await updateMachine(editingHost.id, payload)
        toast.success(`Updated host "${updated.name}"`)
      } else {
        const created = await createMachine(payload)
        selectHost(created.id)
        toast.success(`Added host "${created.name}"`)
      }
      await invalidateMachines()
      setDialogOpen(false)
      setForm(emptyHostForm)
      setEditingHost(null)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save host")
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) {
      return
    }

    try {
      await deleteMachine(deleteTarget.id)
      if (selectedHostId === deleteTarget.id) {
        selectHost(null)
      }
      await invalidateMachines()
      toast.success(`Removed host "${deleteTarget.name}"`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not remove host")
    } finally {
      setDeleteTarget(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Fleet registry"
        title="Hosts"
        description="Register grading hosts in your data center fleet. Select an active host for scan context on Scan and Drive Health."
        actions={
          <>
            <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
              <RefreshCwIcon data-icon="inline-start" />
              Refresh
            </Button>
            <Button onClick={openCreateDialog}>
              <PlusIcon data-icon="inline-start" />
              Add host
            </Button>
          </>
        }
      />

      <Alert>
        <ServerIcon />
        <AlertTitle>Active host context (registry only)</AlertTitle>
        <AlertDescription>
          Selecting a host filters Scan and Drive Health by <span className="font-mono">machine_id</span>{" "}
          against the single configured API. Host addresses are stored for inventory only — they do not
          switch the dashboard to a remote backend yet. Use Discover to find CDI APIs on your LAN.
        </AlertDescription>
      </Alert>

      {selectedHost ? (
        <Card>
          <CardHeader>
            <CardTitle>Selected: {selectedHost.name}</CardTitle>
            <CardDescription>
              {formatScanSummary(selectedHost)}
              {selectedHost.last_scan_at
                ? ` · Last scan ${new Date(selectedHost.last_scan_at).toLocaleString()}`
                : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button asChild>
              <Link to="/scan">
                <ScanSearchIcon data-icon="inline-start" />
                Run scan
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/drives">
                <HardDriveIcon data-icon="inline-start" />
                Drive Health
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Fleet hosts</CardTitle>
          <CardDescription>
            {hosts.length} host(s) in registry · click a name to set active context
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : hosts.length === 0 ? (
            <Empty className="border">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <ServerIcon />
                </EmptyMedia>
                <EmptyTitle>No hosts registered</EmptyTitle>
                <EmptyDescription>
                  Add a grading host manually or use Discover to find CDI APIs on your LAN.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent className="flex flex-wrap gap-2">
                <Button size="sm" onClick={openCreateDialog}>
                  <PlusIcon data-icon="inline-start" />
                  Add host
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link to="/discover">Discover on LAN</Link>
                </Button>
              </EmptyContent>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Host</TableHead>
                  <TableHead>Rack / location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last scan</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hosts.map((host) => {
                  const isSelected = host.id === selectedHostId
                  return (
                    <TableRow
                      key={host.id}
                      data-state={isSelected ? "selected" : undefined}
                      className={isSelected ? "bg-muted/40" : undefined}
                    >
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              className="text-left font-medium hover:underline"
                              onClick={() => selectHost(host.id)}
                            >
                              {host.name}
                            </button>
                            {isSelected ? (
                              <Badge variant="outline">Active</Badge>
                            ) : null}
                          </div>
                          <span className="text-muted-foreground font-mono text-xs">
                            {host.hostname}
                          </span>
                          {host.address ? (
                            <span className="text-muted-foreground font-mono text-xs">
                              {host.address}
                              <span className="ml-1 font-sans">(registry only)</span>
                            </span>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>{host.location || "—"}</TableCell>
                      <TableCell>
                        <Badge variant={machineStatusBadgeVariant(host.status)}>
                          {host.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1 text-sm">
                          <span>
                            {host.last_scan_at
                              ? new Date(host.last_scan_at).toLocaleString()
                              : "Never"}
                          </span>
                          <span className="text-muted-foreground text-xs">
                            {formatScanSummary(host)}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => openEditDialog(host)}
                          >
                            <PencilIcon />
                            <span className="sr-only">Edit {host.name}</span>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setDeleteTarget(host)}
                          >
                            <Trash2Icon />
                            <span className="sr-only">Remove {host.name}</span>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingHost ? "Edit host" : "Add host"}</DialogTitle>
            <DialogDescription>
              Register a grading host in the fleet registry. Address is optional metadata only —
              the dashboard always talks to the configured local API proxy.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="host-name">Display name</FieldLabel>
              <Input
                id="host-name"
                value={form.name}
                onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
                placeholder="Lab Rack A"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="host-hostname">Hostname</FieldLabel>
              <Input
                id="host-hostname"
                value={form.hostname}
                onChange={(e) =>
                  setForm((current) => ({ ...current, hostname: e.target.value }))
                }
                placeholder="grading-01.local"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="host-address">
                Address (registry only)
              </FieldLabel>
              <Input
                id="host-address"
                value={form.address}
                onChange={(e) =>
                  setForm((current) => ({ ...current, address: e.target.value }))
                }
                placeholder="10.0.0.12:8844"
                aria-describedby="host-address-hint"
              />
              <p
                id="host-address-hint"
                className="text-muted-foreground text-xs"
              >
                Stored for inventory. Does not route API calls — selecting this host only
                filters data by machine_id on the configured API.
              </p>
            </Field>
            <Field>
              <FieldLabel htmlFor="host-location">Rack / location</FieldLabel>
              <Input
                id="host-location"
                value={form.location}
                onChange={(e) =>
                  setForm((current) => ({ ...current, location: e.target.value }))
                }
                placeholder="Sacramento · Row 3 · Rack 12"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="host-notes">Notes</FieldLabel>
              <Textarea
                id="host-notes"
                value={form.notes}
                onChange={(e) => setForm((current) => ({ ...current, notes: e.target.value }))}
                placeholder="NVMe backplane, 8-bay"
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submitHost()}>
              {editingHost ? "Save changes" : "Add host"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove host?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget
                ? `This removes "${deleteTarget.name}" from the fleet registry and deletes its cached scan snapshot.`
                : "This action cannot be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => void confirmDelete()}>
              Remove host
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
