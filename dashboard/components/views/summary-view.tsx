"use client";

import { Activity, AlertTriangle, CheckCircle2, Clock3, HardDrive, ShieldAlert } from "lucide-react";

import { useDashboard } from "@/components/dashboard-provider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { buildErrorSummary, toNum, toText } from "@/lib/drive";

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

export function SummaryView(): JSX.Element {
  const { health, scan, jobs, selfTestStatus, busy } = useDashboard();
  const devices = scan?.devices ?? [];

  const averageScore = devices.length
    ? devices.reduce((acc, item) => acc + (toNum(item.health_score) ?? 0), 0) / devices.length
    : 0;

  const warningCount = devices.filter((device) => {
    const score = toNum(device.health_score);
    return score !== null && score >= 40 && score < 75;
  }).length;

  const criticalCount = devices.filter((device) => {
    const score = toNum(device.health_score);
    return score !== null && score < 40;
  }).length;

  const inProgressCount = (selfTestStatus?.devices ?? []).filter((device) => device.in_progress).length;

  const topRiskDevices = [...devices]
    .sort((a, b) => (toNum(a.health_score) ?? 999) - (toNum(b.health_score) ?? 999))
    .slice(0, 6);

  const missingTools = health?.missing_required_tools ?? [];

  return (
    <div className="space-y-4">
      <section>
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-[#3E6071]">Summary</p>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-title)" }}>
          Fleet Overview
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">Most important signals first: backend readiness, drive risk tiers, and active self-test jobs.</p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Backend</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Activity className="h-5 w-5 text-[#139C7A]" />
              {health?.status ?? "loading"}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">root {String(health?.is_root ?? false)} | token {String(health?.api_token_enabled ?? false)}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Drives</CardDescription>
            <CardTitle className="text-2xl">{scan?.summary.total ?? 0}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Current scanned inventory</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Average Score</CardDescription>
            <CardTitle className="text-2xl text-[#3E6071]">{averageScore.toFixed(1)}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Across scanned drives</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Healthy</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl text-[#3B7351]">
              <CheckCircle2 className="h-5 w-5" />
              {scan?.summary.healthy ?? 0}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Score 75 and above</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>At Risk</CardDescription>
            <CardTitle className="text-2xl text-amber-700">{warningCount}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Score between 40 and 74</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Critical</CardDescription>
            <CardTitle className="text-2xl text-red-700">{criticalCount}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Score below 40</CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.45fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Highest-Risk Drives</CardTitle>
            <CardDescription>Lowest scores and error signatures to prioritize for technician intervention.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Errors</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topRiskDevices.map((device, index) => {
                  const score = toNum(device.health_score);
                  const tone = score === null ? "outline" : score < 40 ? "failed" : score < 75 ? "warning" : "healthy";
                  return (
                    <TableRow key={`${device.dut ?? "device"}-${index}`}>
                      <TableCell className="font-mono text-xs">{toText(device.dut)}</TableCell>
                      <TableCell>{toText(device.model_number)}</TableCell>
                      <TableCell className="font-semibold">{score ?? "-"}</TableCell>
                      <TableCell>
                        <Badge variant={tone}>{toText(device.health_status, "Unknown")}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{buildErrorSummary(device)}</TableCell>
                    </TableRow>
                  );
                })}
                {topRiskDevices.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-sm text-muted-foreground">
                      {busy.boot ? "Loading dashboard data..." : "No devices available in the current scan."}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Clock3 className="h-5 w-5 text-[#3E6071]" />
                Self-Test Activity
              </CardTitle>
              <CardDescription>Live queue status from NVMe self-tests.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="rounded-lg border p-2">
                <p className="font-semibold">Running now</p>
                <p className="text-muted-foreground">{inProgressCount} drive(s)</p>
              </div>
              <div className="rounded-lg border p-2">
                <p className="font-semibold">Queued + historical jobs</p>
                <p className="text-muted-foreground">{jobs.length}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <ShieldAlert className="h-5 w-5 text-[#3E6071]" />
                Backend Readiness
              </CardTitle>
              <CardDescription>Environment checks that block scan or report generation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {missingTools.length === 0 && <p className="text-[#3B7351]">All required CLI tools are detected.</p>}
              {missingTools.length > 0 && (
                <ul className="space-y-2">
                  {missingTools.map((tool) => (
                    <li key={tool} className="rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-red-900">
                      <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
                      {tool}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <HardDrive className="h-5 w-5 text-[#139C7A]" />
                Last Scan Time
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{formatDate(scan?.scanned_at)}</CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
