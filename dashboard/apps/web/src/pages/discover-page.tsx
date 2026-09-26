import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { PlusIcon, RadarIcon, ServerIcon } from "lucide-react"
import { toast } from "sonner"

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
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { Spinner } from "@workspace/ui/components/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { NewHostTokensDialog } from "@/components/new-host-tokens-dialog"
import { PageHeader } from "@/components/page-header"
import { createMachine, discoverHosts } from "@/lib/api"
import { appConfig } from "@/lib/config"
import {
  checkHostConnection,
  defaultDiscoveredHostName,
  discoveredNeedsNoToken,
  discoveryHealthLabel,
  discoveryHealthVariant,
  MAX_DISCOVER_SUBNETS,
  parseSubnetInput,
  shouldPromptForToken,
} from "@/lib/host-utils"
import { useInvalidateCdiQueries } from "@/hooks/use-cdi-queries"
import type { DiscoverRequest, DiscoveredHost, Machine } from "@/lib/types"

type AddedHost = { machine: Machine; discovered: DiscoveredHost }

/**
 * Which newly added hosts to ask for a token: lab-mode hosts never; hosts
 * that report token auth always; unknown hosts only when a check is rejected.
 */
async function hostsNeedingTokens(added: AddedHost[]): Promise<Machine[]> {
  const results = await Promise.all(
    added.map(async ({ machine, discovered }) => {
      const discoveredAuth = discovered.health?.auth_mode ?? null
      if (discoveredAuth === "token") {
        return machine
      }
      // Lab-mode and unknown hosts: a check records status (and auth mode).
      const outcome = await checkHostConnection(machine)
      return shouldPromptForToken(discoveredAuth, outcome?.machine ?? null)
        ? machine
        : null
    })
  )
  return results.filter((machine): machine is Machine => machine != null)
}

export function DiscoverPage() {
  const { invalidateMachines } = useInvalidateCdiQueries()
  const [discovering, setDiscovering] = useState(false)
  const [discoverSubnet, setDiscoverSubnet] = useState(appConfig.discoverSubnet)
  const [discoveredHosts, setDiscoveredHosts] = useState<DiscoveredHost[]>([])
  const [discoverMeta, setDiscoverMeta] = useState<{
    scannedSubnets: string[]
    hostsScanned: number
    durationMs: number
  } | null>(null)
  const [addingDiscovered, setAddingDiscovered] = useState<string | null>(null)
  const [bulkAdding, setBulkAdding] = useState(false)
  const [tokenPromptHosts, setTokenPromptHosts] = useState<Machine[]>([])

  const parsedSubnets = useMemo(() => parseSubnetInput(discoverSubnet), [discoverSubnet])

  /** After adding hosts, go straight to asking for tokens where needed. */
  const promptForTokens = async (added: AddedHost[]) => {
    if (added.length === 0) {
      return
    }
    const needTokens = await hostsNeedingTokens(added)
    await invalidateMachines()
    if (needTokens.length > 0) {
      setTokenPromptHosts(needTokens)
    }
  }

  const runDiscovery = async () => {
    if (parsedSubnets.error != null) {
      toast.error(parsedSubnets.error)
      return
    }
    const subnets = parsedSubnets.subnets
    const body: DiscoverRequest =
      subnets.length > 1
        ? { subnets }
        : subnets.length === 1
          ? { subnet: subnets[0] }
          : {}

    setDiscovering(true)
    setDiscoveredHosts([])
    setDiscoverMeta(null)
    try {
      const result = await discoverHosts(body)
      setDiscoveredHosts(result.found)
      setDiscoverMeta({
        scannedSubnets: result.scanned_subnets,
        hostsScanned: result.hosts_scanned,
        durationMs: result.duration_ms,
      })
      const newHosts = result.found.filter((host) => !host.already_registered)
      toast.success(
        `Discovery complete — ${result.found.length} API(s) on port ${result.port}, ${newHosts.length} new`
      )
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "LAN discovery failed")
    } finally {
      setDiscovering(false)
    }
  }

  const addDiscoveredHost = async (host: DiscoveredHost) => {
    setAddingDiscovered(host.address)
    try {
      const hostname = defaultDiscoveredHostName(host)
      const machine = await createMachine({
        name: hostname,
        hostname,
        address: host.address,
      })
      setDiscoveredHosts((current) =>
        current.map((item) =>
          item.address === host.address ? { ...item, already_registered: true } : item
        )
      )
      toast.success(`Added ${hostname} to fleet`)
      await invalidateMachines()
      await promptForTokens([{ machine, discovered: host }])
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not add host")
    } finally {
      setAddingDiscovered(null)
    }
  }

  const addAllDiscovered = async () => {
    const pending = discoveredHosts.filter((host) => !host.already_registered)
    if (pending.length === 0) {
      toast.message("No new hosts to add")
      return
    }

    setBulkAdding(true)
    let added = 0
    let skipped = 0
    let failed = 0
    const addedHosts: AddedHost[] = []
    try {
      for (const host of pending) {
        const hostname = defaultDiscoveredHostName(host)
        try {
          const machine = await createMachine({
            name: hostname,
            hostname,
            address: host.address,
          })
          addedHosts.push({ machine, discovered: host })
          setDiscoveredHosts((current) =>
            current.map((item) =>
              item.address === host.address
                ? { ...item, already_registered: true }
                : item
            )
          )
          added += 1
        } catch (err) {
          const message = err instanceof Error ? err.message : ""
          if (
            message.toLowerCase().includes("already") ||
            message.toLowerCase().includes("exists") ||
            message.toLowerCase().includes("duplicate")
          ) {
            skipped += 1
            setDiscoveredHosts((current) =>
              current.map((item) =>
                item.address === host.address
                  ? { ...item, already_registered: true }
                  : item
              )
            )
          } else {
            failed += 1
          }
        }
      }
      if (failed === 0 && skipped === 0) {
        toast.success(`Added ${added} host(s) to fleet`)
      } else {
        toast.message(
          `Bulk add finished — ${added} added, ${skipped} skipped, ${failed} failed`
        )
      }
      if (added > 0 || skipped > 0) {
        await invalidateMachines()
      }
      await promptForTokens(addedHosts)
    } finally {
      setBulkAdding(false)
    }
  }

  const pendingDiscoveryCount = discoveredHosts.filter((host) => !host.already_registered).length

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Network discovery"
        title="Discover"
        description="Find grading benches on your network (port 8844). The search runs from this bench, not from your browser."
        actions={
          <Button onClick={() => void runDiscovery()} disabled={discovering}>
            {discovering ? <Spinner data-icon="inline-start" /> : <RadarIcon data-icon="inline-start" />}
            {discovering ? "Discovering…" : "Discover on LAN"}
          </Button>
        }
      />

      <Alert>
        <RadarIcon />
        <AlertTitle>Cross-subnet discovery</AlertTitle>
        <AlertDescription>
          If the grading hosts are on a different subnet than this bench, list their subnets
          below (for example 192.168.0.0/24, 10.0.1.0/24), or set{" "}
          <span className="font-mono">VITE_CDI_DISCOVER_SUBNET</span> in{" "}
          <span className="font-mono">.env.local</span>. Leave blank to search this bench&apos;s
          own network.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>LAN scan</CardTitle>
          <CardDescription>
            Checks up to 256 addresses per subnet. Add what it finds to your hosts — you&apos;ll be
            asked for an access token if a host uses one.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="discover-subnet">Subnets (optional)</FieldLabel>
              <Input
                id="discover-subnet"
                value={discoverSubnet}
                onChange={(e) => setDiscoverSubnet(e.target.value)}
                placeholder="192.168.0.0/24, 10.0.1.0/24"
                disabled={discovering}
                aria-invalid={parsedSubnets.error != null}
              />
              {parsedSubnets.error != null ? (
                <FieldError>{parsedSubnets.error}</FieldError>
              ) : (
                <FieldDescription>
                  Up to {MAX_DISCOVER_SUBNETS} subnets, separated by commas or spaces, each /24 or
                  smaller. You can run a search about every 10 seconds.
                </FieldDescription>
              )}
            </Field>
          </FieldGroup>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => void runDiscovery()}
              disabled={discovering || parsedSubnets.error != null}
            >
              {discovering ? <Spinner data-icon="inline-start" /> : <RadarIcon data-icon="inline-start" />}
              {discovering ? "Scanning LAN…" : "Start discovery"}
            </Button>
            {discoveredHosts.length > 0 ? (
              <Button
                variant="outline"
                onClick={() => void addAllDiscovered()}
                disabled={bulkAdding || pendingDiscoveryCount === 0}
              >
                {bulkAdding ? <Spinner data-icon="inline-start" /> : <PlusIcon data-icon="inline-start" />}
                {bulkAdding
                  ? "Adding hosts…"
                  : `Add ${pendingDiscoveryCount} new to fleet`}
              </Button>
            ) : null}
            <Button variant="outline" asChild>
              <Link to="/hosts">
                <ServerIcon data-icon="inline-start" />
                View fleet
              </Link>
            </Button>
          </div>

          {discovering ? (
            <div className="text-muted-foreground flex items-center gap-2 text-sm">
              <Spinner />
              Probing local subnet(s) for CDI APIs…
            </div>
          ) : null}

          {discoverMeta ? (
            <p className="text-muted-foreground text-sm">
              Scanned {discoverMeta.scannedSubnets.join(", ")} · {discoverMeta.hostsScanned} host(s)
              · {discoverMeta.durationMs} ms
            </p>
          ) : null}

          {discoveredHosts.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Address</TableHead>
                  <TableHead>Hostname</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {discoveredHosts.map((host) => (
                  <TableRow key={host.address}>
                    <TableCell className="font-mono text-xs">{host.address}</TableCell>
                    <TableCell>{host.hostname ?? "—"}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={discoveryHealthVariant(host)}>
                          {discoveryHealthLabel(host)}
                        </Badge>
                        {discoveredNeedsNoToken(host) ? (
                          <span className="text-muted-foreground text-xs">
                            No token needed
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {host.already_registered ? (
                        <Badge variant="outline">In fleet</Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={addingDiscovered === host.address || bulkAdding}
                          onClick={() => void addDiscoveredHost(host)}
                        >
                          {addingDiscovered === host.address ? (
                            <Spinner data-icon="inline-start" />
                          ) : (
                            <PlusIcon data-icon="inline-start" />
                          )}
                          Add to fleet
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : discoverMeta && !discovering ? (
            <Empty className="border">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <RadarIcon />
                </EmptyMedia>
                <EmptyTitle>No CDI APIs found</EmptyTitle>
                <EmptyDescription>
                  No hosts answered on port 8844 in the searched subnet(s). Check the grading hosts are
                  powered on and on the same network as this bench.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : null}
        </CardContent>
      </Card>
      <NewHostTokensDialog
        hosts={tokenPromptHosts}
        onClose={() => setTokenPromptHosts([])}
        onSaved={invalidateMachines}
      />
    </div>
  )
}
