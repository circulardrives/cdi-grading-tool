import { useCallback, useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  HardDriveIcon,
  PencilIcon,
  PlusIcon,
  RefreshCwIcon,
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
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { Switch } from "@workspace/ui/components/switch"
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
  createMachine,
  deleteMachine,
  listMachines,
  scanDevices,
  updateMachine,
} from "@/lib/api"
import { appConfig } from "@/lib/config"
import { getSelectedHostId, setSelectedHostId } from "@/lib/selected-host"
import type { Machine, MachineCreateRequest } from "@/lib/types"

type HostFormState = {
  name: string
  hostname: string
  address: string
  location: string
  notes: string
}

const emptyForm: HostFormState = {
  name: "",
  hostname: "",
  address: "",
  location: "",
  notes: "",
}

function statusBadgeVariant(status: Machine["status"]) {
  if (status === "reachable") {
    return "default" as const
  }
  if (status === "unreachable") {
    return "destructive" as const
  }
  return "secondary" as const
}

function formatScanSummary(machine: Machine): string {
  const summary = machine.last_scan_summary
  if (!summary) {
    return "No scan yet"
  }
  return `${summary.total} drives · ${summary.healthy} healthy · ${summary.warning} warn · ${summary.failed} fail`
}

export function MachinesPage() {
  const [hosts, setHosts] = useState<Machine[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingHost, setEditingHost] = useState<Machine | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Machine | null>(null)
  const [selectedHostId, setSelectedHostIdState] = useState<string | null>(
    () => getSelectedHostId()
  )
  const [ignoreAta, setIgnoreAta] = useState(false)
  const [ignoreNvme, setIgnoreNvme] = useState(false)
  const [ignoreScsi, setIgnoreScsi] = useState(false)
  const [form, setForm] = useState<HostFormState>(emptyForm)

  const selectedHost = useMemo(
    () => hosts.find((host) => host.id === selectedHostId) ?? null,
    [hosts, selectedHostId]
  )

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const result = await listMachines()
      setHosts(result)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load hosts")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const openCreateDialog = () => {
    setEditingHost(null)
    setForm(emptyForm)
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
        setHosts((current) =>
          current.map((host) => (host.id === updated.id ? updated : host))
        )
        toast.success(`Updated host "${updated.name}"`)
      } else {
        const created = await createMachine(payload)
        setHosts((current) => [created, ...current])
        selectHost(created.id)
        toast.success(`Added host "${created.name}"`)
      }
      setDialogOpen(false)
      setForm(emptyForm)
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
      setHosts((current) => current.filter((host) => host.id !== deleteTarget.id))
      if (selectedHostId === deleteTarget.id) {
        selectHost(null)
      }
      toast.success(`Removed host "${deleteTarget.name}"`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not remove host")
    } finally {
      setDeleteTarget(null)
    }
  }

  const runScan = async () => {
    if (!selectedHostId) {
      toast.error("Select a host before running a scan")
      return
    }

    setScanning(true)
    try {
      const result = await scanDevices({
        ignore_ata: ignoreAta,
        ignore_nvme: ignoreNvme,
        ignore_scsi: ignoreScsi,
        machine_id: selectedHostId,
        ...(appConfig.useMockData ? { mock_data: appConfig.mockDataPath } : {}),
      })
      await refresh()
      toast.success(
        `Scan complete for ${selectedHost?.name ?? "host"} — ${result.summary.total} drive(s)`
      )
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Scan failed")
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Fleet registry"
        title="Hosts & Scans"
        description="Register grading hosts in your data center fleet. v1 scans run against this local CDI API; the address field prepares for remote agents on each host."
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
        <AlertTitle>Local scan mode (v1)</AlertTitle>
        <AlertDescription>
          Scans execute on the machine running <span className="font-mono">cdi-health-api</span>.
          Register each rack host here, associate scans with a host, and use Drive Health to review
          drives for the selected host context. Remote scan agents via the address field are planned
          for a later release.
        </AlertDescription>
      </Alert>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Fleet hosts</CardTitle>
            <CardDescription>
              {hosts.length} host(s) in registry · select one for scan context
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
                    Add a grading host before associating scans with your fleet.
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent>
                  <Button size="sm" onClick={openCreateDialog}>
                    <PlusIcon data-icon="inline-start" />
                    Add host
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
                                <Badge variant="outline">Selected</Badge>
                              ) : null}
                            </div>
                            <span className="text-muted-foreground font-mono text-xs">
                              {host.hostname}
                            </span>
                            {host.address ? (
                              <span className="text-muted-foreground font-mono text-xs">
                                {host.address}
                              </span>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell>{host.location || "—"}</TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(host.status)}>
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

        <Card>
          <CardHeader>
            <CardTitle>Scan controls</CardTitle>
            <CardDescription>
              {selectedHost
                ? `Run a local scan for ${selectedHost.name}`
                : "Select a host from the fleet list first"}
              {appConfig.useMockData ? " · mock data mode" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FieldGroup>
              <Field orientation="horizontal">
                <Switch checked={ignoreAta} onCheckedChange={setIgnoreAta} />
                <FieldLabel>Ignore ATA/SATA</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch checked={ignoreNvme} onCheckedChange={setIgnoreNvme} />
                <FieldLabel>Ignore NVMe</FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch checked={ignoreScsi} onCheckedChange={setIgnoreScsi} />
                <FieldLabel>Ignore SCSI/SAS</FieldLabel>
              </Field>
            </FieldGroup>
            <FieldDescription>
              The scan is stored against the selected host and can be viewed on Drive Health.
            </FieldDescription>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => void runScan()}
                disabled={scanning || !selectedHostId}
              >
                <HardDriveIcon data-icon="inline-start" />
                {scanning ? "Scanning…" : "Scan for selected host"}
              </Button>
              <Button variant="outline" asChild disabled={!selectedHostId}>
                <Link to="/drives">View drives</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingHost ? "Edit host" : "Add host"}</DialogTitle>
            <DialogDescription>
              Register a grading host in your fleet. Use address for a future remote CDI API
              endpoint (IP or host:port).
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
              <FieldLabel htmlFor="host-address">Address (optional)</FieldLabel>
              <Input
                id="host-address"
                value={form.address}
                onChange={(e) =>
                  setForm((current) => ({ ...current, address: e.target.value }))
                }
                placeholder="10.0.0.12:8844"
              />
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
