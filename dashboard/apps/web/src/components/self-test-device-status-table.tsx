import { BanIcon, TestTubeDiagonalIcon } from "lucide-react"

import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@workspace/ui/components/empty"
import { Spinner } from "@workspace/ui/components/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { statusBadgeVariant } from "@/lib/health-badges"
import {
  formatResultCode,
  formatResultLabel,
  formatStatus,
} from "@/lib/self-test-utils"
import type { SelfTestDeviceStatus } from "@/lib/types"

type SelfTestDeviceStatusTableProps = {
  devices: SelfTestDeviceStatus[]
  loading: boolean
  abortingDevice: string | null
  onAbort: (devicePath: string) => void
}

export function SelfTestDeviceStatusTable({
  devices,
  loading,
  abortingDevice,
  onAbort,
}: SelfTestDeviceStatusTableProps) {
  if (loading) {
    return (
      <div className="flex flex-col gap-2">
        <Spinner />
      </div>
    )
  }

  if (devices.length === 0) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <TestTubeDiagonalIcon />
          </EmptyMedia>
          <EmptyTitle>No NVMe self-test targets</EmptyTitle>
          <EmptyDescription>
            Run a scan on Drive Health first, or connect NVMe drives that support
            nvme-cli self-test on this host.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Device</TableHead>
          <TableHead>Supported</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Result</TableHead>
          <TableHead>Code</TableHead>
          <TableHead>Last test</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {devices.map((entry) => {
          const devicePath = entry.device ?? "—"
          const statusLabel = formatStatus(entry)
          return (
            <TableRow key={devicePath}>
              <TableCell className="font-mono text-xs">{devicePath}</TableCell>
              <TableCell>
                <Badge variant={entry.supported ? "outline" : "secondary"}>
                  {entry.supported ? "Yes" : "No"}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={statusBadgeVariant(statusLabel)}>{statusLabel}</Badge>
                {entry.error ? (
                  <p className="text-muted-foreground mt-1 text-xs">{entry.error}</p>
                ) : null}
              </TableCell>
              <TableCell>
                {entry.latest_result || entry.passed || entry.failed || entry.aborted ? (
                  <Badge variant={statusBadgeVariant(formatResultLabel(entry))}>
                    {formatResultLabel(entry)}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {formatResultCode(entry)}
              </TableCell>
              <TableCell className="text-sm">
                {entry.last_test_date
                  ? new Date(entry.last_test_date).toLocaleString()
                  : entry.latest_result?.test_type
                    ? `${entry.latest_result.test_type} (log)`
                    : "—"}
              </TableCell>
              <TableCell className="text-right">
                {entry.in_progress && entry.device ? (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={abortingDevice === entry.device}
                    onClick={() => onAbort(entry.device!)}
                  >
                    {abortingDevice === entry.device ? (
                      <Spinner data-icon="inline-start" />
                    ) : (
                      <BanIcon data-icon="inline-start" />
                    )}
                    Abort
                  </Button>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
