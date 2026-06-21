import { useState } from "react"
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

import { PageHeader } from "@/components/page-header"
import { MockDataToggle } from "@/components/mock-data-toggle"
import { createMachine, discoverHosts } from "@/lib/api"
import { appConfig } from "@/lib/config"
import {
  defaultDiscoveredHostName,
  discoveryHealthLabel,
  discoveryHealthVariant,
} from "@/lib/host-utils"
import type { DiscoveredHost } from "@/lib/types"

export function DiscoverPage() {
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

  const runDiscovery = async () => {
    setDiscovering(true)
    setDiscoveredHosts([])
    setDiscoverMeta(null)
    try {
      const result = await discoverHosts({
        ...(discoverSubnet.trim() ? { subnet: discoverSubnet.trim() } : {}),
      })
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
      await createMachine({
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
    try {
      for (const host of pending) {
        const hostname = defaultDiscoveredHostName(host)
        await createMachine({
          name: hostname,
          hostname,
          address: host.address,
        })
        setDiscoveredHosts((current) =>
          current.map((item) =>
            item.address === host.address ? { ...item, already_registered: true } : item
          )
        )
        added += 1
      }
      toast.success(`Added ${added} host(s) to fleet`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Bulk add failed")
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
        description="Scan private subnets for CDI Health APIs on port 8844. Discovery runs from the machine hosting cdi-health-api, not from the browser alone."
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
          When your technician laptop is on a different subnet than the grading hosts, set an
          explicit CIDR below (for example 192.168.0.0/24) or configure{" "}
          <span className="font-mono">VITE_CDI_DISCOVER_SUBNET</span> in{" "}
          <span className="font-mono">.env.local</span>. Leave blank to auto-detect from local
          network interfaces on the API host.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Demo mode</CardTitle>
          <CardDescription>
            Mock data is off by default. Enable it here when you want fixture drives
            instead of live hardware scans.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MockDataToggle id="discover-use-mock-data" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>LAN scan</CardTitle>
          <CardDescription>
            Probes up to 256 addresses per subnet. Results can be added to your fleet registry on
            the Hosts page.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="discover-subnet">Subnet (optional)</FieldLabel>
              <Input
                id="discover-subnet"
                value={discoverSubnet}
                onChange={(e) => setDiscoverSubnet(e.target.value)}
                placeholder="192.168.0.0/24"
                disabled={discovering}
              />
              <FieldDescription>
                Scans up to 256 addresses per subnet. Discovery is rate-limited on the API server.
              </FieldDescription>
            </Field>
          </FieldGroup>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void runDiscovery()} disabled={discovering}>
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
                      <Badge variant={discoveryHealthVariant(host)}>
                        {discoveryHealthLabel(host)}
                      </Badge>
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
                  No hosts responded on port 8844 in the scanned subnet(s). Confirm grading hosts are
                  online and reachable from this API machine.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
