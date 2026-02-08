"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, CheckCircle2, FileText, Gauge, PlayCircle, RefreshCcw, ShieldAlert } from "lucide-react";

import {
  abortSelfTest,
  generateReport,
  getHealth,
  getJob,
  getJobs,
  getSelfTestStatus,
  scanDevices,
  startSelfTest,
  type DeviceRecord,
  type HealthResponse,
  type JobResponse,
  type ScanResponse,
  type SelfTestStatusResponse
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));
const useMockData = process.env.NEXT_PUBLIC_CDI_USE_MOCK_DATA === "1";
const mockDataPath = process.env.NEXT_PUBLIC_CDI_MOCK_DATA_PATH?.trim() || "src/cdi_health/mock_data";

function healthVariant(score?: number): "healthy" | "warning" | "failed" | "outline" {
  if (score === undefined || score === null) {
    return "outline";
  }
  if (score >= 75) {
    return "healthy";
  }
  if (score >= 40) {
    return "warning";
  }
  return "failed";
}

export function DashboardPage(): JSX.Element {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [selfTestStatus, setSelfTestStatus] = useState<SelfTestStatusResponse | null>(null);

  const [deviceFilter, setDeviceFilter] = useState("");
  const [ignoreAta, setIgnoreAta] = useState(false);
  const [ignoreNvme, setIgnoreNvme] = useState(false);
  const [ignoreScsi, setIgnoreScsi] = useState(false);

  const [selfTestDevice, setSelfTestDevice] = useState("");
  const [selfTestType, setSelfTestType] = useState<"short" | "extended">("short");
  const [selfTestWait, setSelfTestWait] = useState(false);

  const [reportFormat, setReportFormat] = useState<"html" | "pdf">("html");
  const [reportOutput, setReportOutput] = useState("");

  const [busyAction, setBusyAction] = useState<"scan" | "selftest" | "report" | "abort" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshHealth = useCallback(async () => {
    const data = await getHealth();
    setHealth(data);
  }, []);

  const refreshJobs = useCallback(async () => {
    const data = await getJobs();
    setJobs(data);
  }, []);

  const refreshSelfTestStatus = useCallback(async () => {
    const data = await getSelfTestStatus();
    setSelfTestStatus(data);
  }, []);

  const runScan = useCallback(async () => {
    setBusyAction("scan");
    setError(null);
    setMessage(null);
    try {
      const data = await scanDevices({
        ignore_ata: ignoreAta,
        ignore_nvme: ignoreNvme,
        ignore_scsi: ignoreScsi,
        device: deviceFilter.trim() || undefined,
        mock_data: useMockData ? mockDataPath : undefined
      });
      setScan(data);
      setMessage(`Scan completed: ${data.summary.total} device(s)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setBusyAction(null);
    }
  }, [deviceFilter, ignoreAta, ignoreNvme, ignoreScsi]);

  const pollJobUntilDone = useCallback(async (jobId: string) => {
    for (let i = 0; i < 180; i += 1) {
      const job = await getJob(jobId);
      if (job.status === "completed" || job.status === "failed") {
        await refreshJobs();
        await refreshSelfTestStatus();
        if (job.status === "completed") {
          setMessage(`Self-test job ${jobId} completed`);
        } else {
          setError(job.error ?? `Self-test job ${jobId} failed`);
        }
        return;
      }
      await sleep(2000);
    }
    setError(`Timed out waiting for job ${jobId}`);
  }, [refreshJobs, refreshSelfTestStatus]);

  const runSelfTest = useCallback(async () => {
    setBusyAction("selftest");
    setError(null);
    setMessage(null);
    try {
      const job = await startSelfTest({
        device: selfTestDevice.trim() || null,
        test_type: selfTestType,
        wait: selfTestWait,
        poll_interval_seconds: 30,
        timeout_seconds: 14400
      });
      setMessage(`Self-test queued: ${job.job_id}`);
      await refreshJobs();
      void pollJobUntilDone(job.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Self-test start failed");
    } finally {
      setBusyAction(null);
    }
  }, [pollJobUntilDone, refreshJobs, selfTestDevice, selfTestType, selfTestWait]);

  const runAbort = useCallback(async () => {
    if (!selfTestDevice.trim()) {
      setError("Provide an NVMe device path to abort (example: /dev/nvme0)");
      return;
    }

    setBusyAction("abort");
    setError(null);
    setMessage(null);
    try {
      await abortSelfTest(selfTestDevice.trim());
      setMessage(`Abort sent to ${selfTestDevice.trim()}`);
      await refreshSelfTestStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Abort failed");
    } finally {
      setBusyAction(null);
    }
  }, [refreshSelfTestStatus, selfTestDevice]);

  const runReport = useCallback(async () => {
    setBusyAction("report");
    setError(null);
    setMessage(null);
    try {
      const result = await generateReport({
        format: reportFormat,
        output_file: reportOutput.trim() || undefined,
        ignore_ata: ignoreAta,
        ignore_nvme: ignoreNvme,
        ignore_scsi: ignoreScsi,
        device: deviceFilter.trim() || undefined,
        mock_data: useMockData ? mockDataPath : undefined
      });
      setMessage(`Report generated: ${result.output_file}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setBusyAction(null);
    }
  }, [deviceFilter, ignoreAta, ignoreNvme, ignoreScsi, reportFormat, reportOutput]);

  useEffect(() => {
    const bootstrap = async (): Promise<void> => {
      setBusyAction("scan");
      try {
        await Promise.all([refreshHealth(), refreshJobs(), refreshSelfTestStatus()]);
        const data = await scanDevices({
          ignore_ata: false,
          ignore_nvme: false,
          ignore_scsi: false,
          mock_data: useMockData ? mockDataPath : undefined
        });
        setScan(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Initial load failed");
      } finally {
        setBusyAction(null);
      }
    };

    void bootstrap();
  }, [refreshHealth, refreshJobs, refreshSelfTestStatus]);

  const lastJob = useMemo(() => jobs[0] ?? null, [jobs]);
  const devices = scan?.devices ?? [];

  return (
    <main className="mx-auto max-w-7xl p-4 pb-12 md:p-8">
      <header className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-muted-foreground">Technician Console</p>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl" style={{ fontFamily: "var(--font-title)" }}>
            CDI Health Dashboard
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Local drive triage for scan, NVMe self-test, and report generation.
          </p>
          {useMockData && (
            <p className="mt-1 font-mono text-xs uppercase tracking-wide text-amber-700">
              mock mode: {mockDataPath}
            </p>
          )}
        </div>

        <Button variant="outline" onClick={() => void runScan()} disabled={busyAction === "scan"}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          Refresh Scan
        </Button>
      </header>

      {(message || error) && (
        <div className="mb-6">
          {message && <p className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{message}</p>}
          {error && <p className="mt-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>}
        </div>
      )}

      <section className="metric-grid mb-6">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Backend Status</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Activity className="h-5 w-5" />
              {health?.status ?? "loading"}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            root: {String(health?.is_root ?? false)}
            <br />
            token: {String(health?.api_token_enabled ?? false)}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Devices</CardDescription>
            <CardTitle className="text-2xl">{scan?.summary.total ?? 0}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Scanned from local host</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Healthy</CardDescription>
            <CardTitle className="text-2xl text-emerald-700">{scan?.summary.healthy ?? 0}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Score 75 and above</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Warnings + Failures</CardDescription>
            <CardTitle className="text-2xl text-amber-700">{(scan?.summary.warning ?? 0) + (scan?.summary.failed ?? 0)}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Requires technician review</CardContent>
        </Card>
      </section>

      <section className="panel-grid mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Gauge className="h-5 w-5" />
              Scan Controls
            </CardTitle>
            <CardDescription>Filter protocol classes and optional single-device scan.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Device Path</label>
              <Input placeholder="/dev/nvme0 (optional)" value={deviceFilter} onChange={(e) => setDeviceFilter(e.target.value)} />
            </div>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="checkbox" checked={ignoreAta} onChange={(e) => setIgnoreAta(e.target.checked)} /> Ignore ATA
              </label>
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="checkbox" checked={ignoreNvme} onChange={(e) => setIgnoreNvme(e.target.checked)} /> Ignore NVMe
              </label>
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="checkbox" checked={ignoreScsi} onChange={(e) => setIgnoreScsi(e.target.checked)} /> Ignore SCSI
              </label>
            </div>

            <Button onClick={() => void runScan()} disabled={busyAction === "scan"}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Run Scan
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <PlayCircle className="h-5 w-5" />
              NVMe Self-Test
            </CardTitle>
            <CardDescription>Start short/extended tests and monitor async jobs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">NVMe Device</label>
              <Input placeholder="/dev/nvme0 (blank means all supported)" value={selfTestDevice} onChange={(e) => setSelfTestDevice(e.target.value)} />
            </div>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="radio" checked={selfTestType === "short"} onChange={() => setSelfTestType("short")} /> Short
              </label>
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="radio" checked={selfTestType === "extended"} onChange={() => setSelfTestType("extended")} /> Extended
              </label>
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="checkbox" checked={selfTestWait} onChange={(e) => setSelfTestWait(e.target.checked)} /> Wait Mode
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void runSelfTest()} disabled={busyAction === "selftest"}>
                Start Test
              </Button>
              <Button variant="outline" onClick={() => void refreshSelfTestStatus()}>
                Status
              </Button>
              <Button variant="danger" onClick={() => void runAbort()} disabled={busyAction === "abort"}>
                Abort
              </Button>
            </div>

            {lastJob && (
              <p className="text-sm text-muted-foreground">
                Last job: <span className="font-mono">{lastJob.job_id}</span> ({lastJob.status})
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="panel-grid mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <FileText className="h-5 w-5" />
              Report Export
            </CardTitle>
            <CardDescription>Create HTML/PDF snapshots for technician handoff.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="radio" checked={reportFormat === "html"} onChange={() => setReportFormat("html")} /> HTML
              </label>
              <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                <input type="radio" checked={reportFormat === "pdf"} onChange={() => setReportFormat("pdf")} /> PDF
              </label>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Output Path (Optional)</label>
              <Input placeholder="/var/tmp/cdi-report.html" value={reportOutput} onChange={(e) => setReportOutput(e.target.value)} />
            </div>

            <Button onClick={() => void runReport()} disabled={busyAction === "report"}>Generate Report</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <ShieldAlert className="h-5 w-5" />
              Self-Test Status
            </CardTitle>
            <CardDescription>Current operation state across NVMe devices.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(selfTestStatus?.devices ?? []).slice(0, 6).map((entry) => (
              <div key={entry.device} className="flex items-center justify-between rounded-md border p-2">
                <span className="font-mono text-xs">{entry.device}</span>
                <Badge variant={entry.failed ? "failed" : entry.in_progress ? "warning" : entry.passed ? "healthy" : "outline"}>
                  {entry.status}
                </Badge>
              </div>
            ))}
            {(!selfTestStatus || selfTestStatus.devices.length === 0) && (
              <p className="text-muted-foreground">No self-test status entries yet.</p>
            )}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Drive Health Table</CardTitle>
          <CardDescription>Top-level technician view of current grading results.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Device</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Protocol</TableHead>
                <TableHead>Size (GiB)</TableHead>
                <TableHead>POH</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Grade</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.map((device: DeviceRecord, index: number) => (
                <TableRow key={`${device.dut ?? "dev"}-${index}`}>
                  <TableCell className="font-mono text-xs">{String(device.dut ?? "-")}</TableCell>
                  <TableCell>{String(device.model_number ?? "-")}</TableCell>
                  <TableCell>{String(device.transport_protocol ?? "-")}</TableCell>
                  <TableCell>{typeof device.gibibytes === "number" ? device.gibibytes.toFixed(1) : "-"}</TableCell>
                  <TableCell>{String(device.power_on_hours ?? "-")}</TableCell>
                  <TableCell>{device.health_score ?? "-"}</TableCell>
                  <TableCell>{String(device.health_grade ?? "-")}</TableCell>
                  <TableCell>
                    <Badge variant={healthVariant(device.health_score)}>{String(device.health_status ?? "Unknown")}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {devices.length === 0 && <p className="mt-3 text-sm text-muted-foreground">No devices available in current scan.</p>}
        </CardContent>
      </Card>
    </main>
  );
}
