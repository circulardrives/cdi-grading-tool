import { CheckCircle2Icon, TestTubeDiagonalIcon } from "lucide-react"

import { Badge } from "@workspace/ui/components/badge"
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
  formatTestType,
  lookupSerial,
  summarizeJob,
} from "@/lib/self-test-utils"
import type { JobResponse, SelfTestDeviceStatus } from "@/lib/types"

type SelfTestResultsCardProps = {
  job: JobResponse
  resultDevices: SelfTestDeviceStatus[]
  hasResultDetails: boolean
  serialByController: Map<string, string>
}

export function SelfTestResultsCard({
  job,
  resultDevices,
  hasResultDetails,
  serialByController,
}: SelfTestResultsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle2Icon className="text-primary" />
          Latest run results
        </CardTitle>
        <CardDescription>
          Job {job.job_id.slice(0, 8)} ·{" "}
          {job.completed_at
            ? new Date(job.completed_at).toLocaleString()
            : "just now"}{" "}
          · {summarizeJob(job)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasResultDetails ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Device</TableHead>
                <TableHead>Serial</TableHead>
                <TableHead>Test type</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {resultDevices.map((entry) => {
                const devicePath = entry.device ?? "—"
                const statusLabel = formatStatus(entry)
                return (
                  <TableRow key={`result-${devicePath}`}>
                    <TableCell className="font-mono text-xs">{devicePath}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {lookupSerial(devicePath, serialByController)}
                    </TableCell>
                    <TableCell>{formatTestType(entry)}</TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(formatResultLabel(entry))}>
                        {formatResultLabel(entry)}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatResultCode(entry)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(statusLabel)}>
                        {statusLabel}
                      </Badge>
                      {entry.error ? (
                        <p className="text-muted-foreground mt-1 text-xs">{entry.error}</p>
                      ) : null}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        ) : (
          <Empty className="border">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <TestTubeDiagonalIcon />
              </EmptyMedia>
              <EmptyTitle>No result payload yet</EmptyTitle>
              <EmptyDescription>
                The job finished but the API did not return per-device self-test log
                entries. Refresh status after the drive completes its NVMe self-test.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </CardContent>
    </Card>
  )
}
