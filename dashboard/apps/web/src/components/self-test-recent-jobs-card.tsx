import { Badge } from "@workspace/ui/components/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@workspace/ui/components/table"

import { statusBadgeVariant } from "@/lib/health-badges"
import { summarizeJob } from "@/lib/self-test-utils"
import type { JobResponse } from "@/lib/types"

type SelfTestRecentJobsCardProps = {
  jobs: JobResponse[]
}

export function SelfTestRecentJobsCard({ jobs }: SelfTestRecentJobsCardProps) {
  if (jobs.length === 0) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent self-test jobs</CardTitle>
        <CardDescription>
          In-memory job history from GET /api/v1/jobs on this API process.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Job</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Summary</TableHead>
              <TableHead>Test type</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.job_id}>
                <TableCell className="font-mono text-xs">
                  {job.job_id.slice(0, 8)}
                </TableCell>
                <TableCell className="text-sm">
                  {job.created_at ? new Date(job.created_at).toLocaleString() : "—"}
                </TableCell>
                <TableCell>
                  <Badge variant={statusBadgeVariant(job.status)}>{job.status}</Badge>
                </TableCell>
                <TableCell className="text-sm">{summarizeJob(job)}</TableCell>
                <TableCell>
                  {(job.payload?.test_type as string | undefined) ?? "short"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
