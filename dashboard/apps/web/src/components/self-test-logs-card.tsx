import { TestTubeDiagonalIcon } from "lucide-react"

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
import { Separator } from "@workspace/ui/components/separator"
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
  describeMissingLogs,
  hasLogData,
  logEntriesForDevice,
  lookupSerial,
} from "@/lib/self-test-utils"
import type { SelfTestDeviceStatus } from "@/lib/types"

type SelfTestLogsCardProps = {
  devices: SelfTestDeviceStatus[]
  serialByController: Map<string, string>
}

export function SelfTestLogsCard({
  devices,
  serialByController,
}: SelfTestLogsCardProps) {
  if (devices.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Self-test logs</CardTitle>
        <CardDescription>
          Raw entries from NVMe Device Self-test Log (Log Page 0x06) via{" "}
          <span className="font-mono">GET /api/v1/selftests/status</span>.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {devices.map((entry, index) => {
          const devicePath = entry.device ?? "—"
          const logEntries = logEntriesForDevice(entry)
          return (
            <div key={`logs-${devicePath}`} className="flex flex-col gap-3">
              {index > 0 ? <Separator /> : null}
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-mono text-xs font-medium">{devicePath}</p>
                <Badge variant="outline">
                  {lookupSerial(devicePath, serialByController)}
                </Badge>
                {entry.in_progress ? (
                  <Badge variant="secondary">in progress</Badge>
                ) : hasLogData(entry) ? (
                  <Badge variant="outline">log available</Badge>
                ) : (
                  <Badge variant="secondary">no log entries</Badge>
                )}
              </div>
              {entry.current_operation ? (
                <p className="text-muted-foreground text-xs">
                  Current operation: {String(entry.current_operation)}
                  {entry.current_completion != null
                    ? ` · ${entry.current_completion}% complete`
                    : entry.progress_percent != null
                      ? ` · ${entry.progress_percent}% complete`
                      : null}
                </p>
              ) : null}
              {logEntries.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Test type</TableHead>
                      <TableHead>Type code</TableHead>
                      <TableHead>Completion time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logEntries.map((result, logIndex) => (
                      <TableRow key={`${devicePath}-log-${logIndex}`}>
                        <TableCell className="font-mono text-xs">{logIndex}</TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(result.result ?? "")}>
                            {result.result ?? "—"}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {result.result_code ?? "—"}
                        </TableCell>
                        <TableCell>{result.test_type ?? "—"}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {result.test_type_code ?? "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {result.completion_time ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <Empty className="border">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <TestTubeDiagonalIcon />
                    </EmptyMedia>
                    <EmptyTitle>No log entries yet</EmptyTitle>
                    <EmptyDescription>{describeMissingLogs(entry)}</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
