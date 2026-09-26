import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  AlertCircleIcon,
  HardDriveIcon,
  PencilIcon,
  PlugZapIcon,
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
import { Spinner } from "@workspace/ui/components/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"
import { Textarea } from "@workspace/ui/components/textarea"

import { AccessTokenField } from "@/components/access-token-field"
import { PageHeader } from "@/components/page-header"
import {
  useInvalidateCdiQueries,
  useMachinesQuery,
} from "@/hooks/use-cdi-queries"
import { createMachine, deleteMachine, updateMachine } from "@/lib/api"
import {
  checkHostConnection,
  emptyHostForm,
  formatScanSummary,
  hostHasAddress,
  hostNeedsNoToken,
  hostProblemMessage,
  machineStatusBadgeVariant,
  machineStatusLabel,
  type HostFormState,
} from "@/lib/host-utils"
import { setSelectedHostId, useSelectedHostId } from "@/lib/selected-host"
import type { Machine, MachineCreateRequest } from "@/lib/types"

export function HostsPage() {
  const machinesQuery = useMachinesQuery()
  const { invalidateMachines } = useInvalidateCdiQueries()
  const hosts = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data])
  const loading = machinesQuery.isLoading
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingHost, setEditingHost] = useState<Machine | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Machine | null>(null)
  const selectedHostId = useSelectedHostId()
  const [form, setForm] = useState<HostFormState>(emptyHostForm)
  // Write-only: held only until the host is saved, then cleared.
  const [apiToken, setApiToken] = useState("")
  const [clearToken, setClearToken] = useState(false)
  const [saving, setSaving] = useState(false)
  const [checkingIds, setCheckingIds] = useState<Set<string>>(() => new Set())
  // Problems from the last check that the host's status alone may not explain.
  const [checkProblems, setCheckProblems] = useState<Record<string, string>>({})

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

  const resetTokenState = () => {
    setApiToken("")
    setClearToken(false)
  }

  const setDialog = (open: boolean) => {
    setDialogOpen(open)
    if (!open) {
      resetTokenState()
    }
  }

  const openCreateDialog = () => {
    setEditingHost(null)
    setForm(emptyHostForm)
    resetTokenState()
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
    resetTokenState()
    setDialogOpen(true)
  }

  const selectHost = (hostId: string | null) => {
    setSelectedHostId(hostId)
  }

  /** Checks one host; returns false when the API cannot run checks. */
  const checkHost = async (
    host: Pick<Machine, "id" | "name">,
    prefix = ""
  ): Promise<boolean> => {
    setCheckingIds((current) => new Set(current).add(host.id))
    try {
      const outcome = await checkHostConnection(host)
      if (!outcome) {
        return false
      }
      setCheckProblems((current) => {
        const next = { ...current }
        if (outcome.ok) {
          delete next[host.id]
        } else {
          next[host.id] = outcome.text
        }
        return next
      })
      const text = prefix ? `${prefix} — ${outcome.text}` : outcome.text
      if (outcome.ok) {
        toast.success(text)
      } else {
        toast.warning(text)
      }
      return true
    } finally {
      setCheckingIds((current) => {
        const next = new Set(current)
        next.delete(host.id)
        return next
      })
      await invalidateMachines()
    }
  }

  const runCheck = async (host: Machine) => {
    const supported = await checkHost(host)
    if (!supported) {
      toast.message("Connection checks need a newer CDI Health on this bench")
    }
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
    const token = apiToken.trim()
    if (editingHost && clearToken) {
      payload.api_token = ""
    } else if (token) {
      payload.api_token = token
    }

    setSaving(true)
    try {
      const saved = editingHost
        ? await updateMachine(editingHost.id, payload)
        : await createMachine(payload)
      if (!editingHost) {
        selectHost(saved.id)
      }
      setDialogOpen(false)
      setForm(emptyHostForm)
      setEditingHost(null)
      resetTokenState()
      await invalidateMachines()

      const verb = editingHost ? "Saved" : "Added"
      // Confirm the address and token actually work, in the same message.
      const checked = hostHasAddress(saved)
        ? await checkHost(saved, `${verb} ${saved.name}`)
        : false
      if (!checked) {
        toast.success(`${verb} ${saved.name}`)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save host")
    } finally {
      setSaving(false)
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
        eyebrow="Fleet"
        title="Hosts"
        description="The grading benches in your fleet. Scans for a host run on that host itself, so every host needs an address — and its access token, if it uses one."
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => void refresh()}
              disabled={loading}
            >
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
              <Link to="/">
                <ScanSearchIcon data-icon="inline-start" />
                Scan {selectedHost.name}
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
            {hosts.length} host(s) · click a name to use it on Scan and Drive
            Health
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
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
                <EmptyTitle>No hosts yet</EmptyTitle>
                <EmptyDescription>
                  Add a grading bench by hand, or use Discover to find benches
                  on your network.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent className="flex flex-wrap gap-2">
                <Button size="sm" onClick={openCreateDialog}>
                  <PlusIcon data-icon="inline-start" />
                  Add host
                </Button>
                <Button size="sm" variant="outline" asChild>
                  <Link to="/benches">Discover on LAN</Link>
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
                  const checking = checkingIds.has(host.id)
                  const problem =
                    checkProblems[host.id] ??
                    hostProblemMessage(host.name, host.status)
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
                          <span className="font-mono text-xs text-muted-foreground">
                            {host.hostname}
                          </span>
                          {hostHasAddress(host) ? (
                            <span className="font-mono text-xs text-muted-foreground">
                              {host.address}
                            </span>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>{host.location || "—"}</TableCell>
                      <TableCell className="whitespace-normal">
                        <div className="flex max-w-xs flex-col gap-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {hostHasAddress(host) ? (
                              <Badge
                                variant={machineStatusBadgeVariant(host.status)}
                              >
                                {machineStatusLabel(host.status)}
                              </Badge>
                            ) : (
                              <Badge variant="outline">This bench</Badge>
                            )}
                            {host.has_api_token ? (
                              <Badge variant="outline">Token set</Badge>
                            ) : hostNeedsNoToken(host) ? (
                              <span className="text-xs text-muted-foreground">
                                No token needed
                              </span>
                            ) : null}
                          </div>
                          {host.remote_version ? (
                            <span className="text-xs text-muted-foreground">
                              CDI Health v{host.remote_version}
                            </span>
                          ) : null}
                          {problem ? (
                            <span className="flex items-start gap-1 text-xs text-destructive">
                              <AlertCircleIcon
                                className="mt-px size-3.5 shrink-0"
                                aria-hidden
                              />
                              {problem}
                            </span>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1 text-sm">
                          <span>
                            {host.last_scan_at
                              ? new Date(host.last_scan_at).toLocaleString()
                              : "Never"}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatScanSummary(host)}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          {hostHasAddress(host) ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => void runCheck(host)}
                              disabled={checking}
                            >
                              {checking ? (
                                <Spinner data-icon="inline-start" />
                              ) : (
                                <PlugZapIcon data-icon="inline-start" />
                              )}
                              {checking ? "Checking…" : "Check connection"}
                            </Button>
                          ) : null}
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
          <p className="text-xs text-muted-foreground">
            Benches in lab mode don&apos;t use access tokens.
          </p>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingHost ? "Edit host" : "Add host"}</DialogTitle>
            <DialogDescription>
              Scans for this host run on the host itself, at the address below.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="host-name">Display name</FieldLabel>
              <Input
                id="host-name"
                value={form.name}
                onChange={(e) =>
                  setForm((current) => ({ ...current, name: e.target.value }))
                }
                placeholder="pecan09"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="host-hostname">Hostname</FieldLabel>
              <Input
                id="host-hostname"
                value={form.hostname}
                onChange={(e) =>
                  setForm((current) => ({
                    ...current,
                    hostname: e.target.value,
                  }))
                }
                placeholder="pecan09.local"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="host-address">Address</FieldLabel>
              <Input
                id="host-address"
                value={form.address}
                onChange={(e) =>
                  setForm((current) => ({
                    ...current,
                    address: e.target.value,
                  }))
                }
                placeholder="10.0.0.12:8844"
              />
              <FieldDescription>
                IP or hostname and port of the host. Leave blank only for the
                bench running this dashboard.
              </FieldDescription>
            </Field>
            <AccessTokenField
              id="host-api-token"
              value={apiToken}
              onChange={setApiToken}
              hasToken={Boolean(editingHost?.has_api_token)}
              clearable={Boolean(editingHost)}
              clear={clearToken}
              onClearChange={setClearToken}
              noTokenNeeded={hostNeedsNoToken(editingHost)}
              disabled={saving}
            />
            <Field>
              <FieldLabel htmlFor="host-location">Rack / location</FieldLabel>
              <Input
                id="host-location"
                value={form.location}
                onChange={(e) =>
                  setForm((current) => ({
                    ...current,
                    location: e.target.value,
                  }))
                }
                placeholder="Sacramento · Row 3 · Rack 12"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="host-notes">Notes</FieldLabel>
              <Textarea
                id="host-notes"
                value={form.notes}
                onChange={(e) =>
                  setForm((current) => ({ ...current, notes: e.target.value }))
                }
                placeholder="NVMe backplane, 8-bay"
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submitHost()} disabled={saving}>
              {saving ? <Spinner data-icon="inline-start" /> : null}
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
                ? `This removes "${deleteTarget.name}" from your hosts and deletes its latest saved scan.`
                : "This action cannot be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => void confirmDelete()}
            >
              Remove host
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
