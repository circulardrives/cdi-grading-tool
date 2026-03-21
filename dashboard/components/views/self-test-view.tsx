"use client";

import { Activity, Ban, PlayCircle } from "lucide-react";
import { useMemo, useState } from "react";

import { useDashboard } from "@/components/dashboard-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toText } from "@/lib/drive";

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

export function SelfTestView(): JSX.Element {
  const { jobs, selfTestStatus, runSelfTest, runAbort, refreshSelfTestStatus, refreshJobs, busy, preferences } = useDashboard();
  const [device, setDevice] = useState("");
  const [testType, setTestType] = useState<"short" | "extended">("short");
  const [wait, setWait] = useState(false);

  const inProgressCount = (selfTestStatus?.devices ?? []).filter((entry) => entry.in_progress).length;

  const sortedStatus = useMemo(() => {
    return [...(selfTestStatus?.devices ?? [])].sort((a, b) => a.device.localeCompare(b.device));
  }, [selfTestStatus?.devices]);

  const submitSelfTest = async (): Promise<void> => {
    await runSelfTest({
      device: device.trim() || null,
      test_type: testType,
      wait
    });
  };

  const submitAbort = async (): Promise<void> => {
    if (!device.trim()) {
      return;
    }

    if (preferences.confirmAbort && typeof window !== "undefined") {
      const shouldAbort = window.confirm(`Abort self-test for ${device.trim()}?`);
      if (!shouldAbort) {
        return;
      }
    }

    await runAbort(device.trim());
  };

  return (
    <div className="space-y-4">
      <section>
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-[#3E6071]">Self-Test</p>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-title)" }}>
          NVMe Test Operations
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">Run short or extended tests, monitor state transitions, and abort specific devices when needed.</p>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5 text-[#139C7A]" />
              Start Test
            </CardTitle>
            <CardDescription>Blank device path runs across all supported NVMe devices.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground" htmlFor="self-test-device">
                NVMe Device
              </label>
              <Input
                id="self-test-device"
                placeholder="/dev/nvme0 (optional)"
                value={device}
                onChange={(event) => setDevice(event.target.value)}
              />
            </div>

            <div className="grid grid-cols-3 gap-2">
              <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <input type="radio" checked={testType === "short"} onChange={() => setTestType("short")} /> Short
              </label>
              <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <input type="radio" checked={testType === "extended"} onChange={() => setTestType("extended")} /> Extended
              </label>
              <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <input type="checkbox" checked={wait} onChange={(event) => setWait(event.target.checked)} /> Wait
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void submitSelfTest()} disabled={busy.selftest}>
                Start Test
              </Button>
              <Button variant="outline" onClick={() => void refreshSelfTestStatus()} disabled={busy.refresh}>
                Check Status
              </Button>
              <Button variant="danger" onClick={() => void submitAbort()} disabled={busy.abort || device.trim() === ""}>
                <Ban className="mr-1.5 h-4 w-4" />
                Abort
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5 text-[#3E6071]" />
              Queue Snapshot
            </CardTitle>
            <CardDescription>Overview of in-flight and completed self-test jobs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="rounded-lg border p-2">
              <p className="font-semibold">In Progress</p>
              <p className="text-muted-foreground">{inProgressCount} device(s)</p>
            </div>
            <div className="rounded-lg border p-2">
              <p className="font-semibold">Recorded jobs</p>
              <p className="text-muted-foreground">{jobs.length}</p>
            </div>
            <Button variant="outline" onClick={() => void refreshJobs()} disabled={busy.refresh}>
              Refresh Jobs
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Device Status</CardTitle>
            <CardDescription>Current self-test state for each NVMe drive.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Supported</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>In Progress</TableHead>
                  <TableHead>Last Test</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedStatus.map((entry) => (
                  <TableRow key={entry.device}>
                    <TableCell className="font-mono text-xs">{entry.device}</TableCell>
                    <TableCell>{entry.supported ? "Yes" : "No"}</TableCell>
                    <TableCell>
                      <Badge variant={entry.failed ? "failed" : entry.in_progress ? "warning" : entry.passed ? "healthy" : "outline"}>
                        {entry.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{entry.in_progress ? "true" : "false"}</TableCell>
                    <TableCell>{formatDate(entry.last_test_date)}</TableCell>
                  </TableRow>
                ))}
                {sortedStatus.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-sm text-muted-foreground">
                      No self-test status entries yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Jobs</CardTitle>
            <CardDescription>Latest self-test and report job timeline.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.slice(0, 8).map((job) => (
                  <TableRow key={job.job_id}>
                    <TableCell className="font-mono text-xs">{job.job_id}</TableCell>
                    <TableCell>{job.job_type}</TableCell>
                    <TableCell>
                      <Badge variant={job.status === "completed" ? "healthy" : job.status === "failed" ? "failed" : "warning"}>{job.status}</Badge>
                    </TableCell>
                    <TableCell>{formatDate(job.updated_at)}</TableCell>
                  </TableRow>
                ))}

                {jobs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-sm text-muted-foreground">
                      {toText(selfTestStatus?.total, "0")} status rows loaded, but no jobs recorded yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
