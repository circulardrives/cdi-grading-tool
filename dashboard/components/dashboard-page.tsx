"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FileText,
  HardDrive,
  LayoutDashboard,
  PlayCircle,
  RefreshCcw,
  Search,
  Settings2,
  ShieldCheck,
  ShieldX,
  Thermometer,
  Wrench
} from "lucide-react";

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
import { cn } from "@/lib/utils";

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));
const useMockData = process.env.NEXT_PUBLIC_CDI_USE_MOCK_DATA === "1";
const mockDataPath = process.env.NEXT_PUBLIC_CDI_MOCK_DATA_PATH?.trim() || "src/cdi_health/mock_data";

function toNum(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function toText(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  if (typeof value === "string" && value.trim() === "") {
    return fallback;
  }
  return String(value);
}

function formatNumber(value: unknown, suffix = "", digits = 0): string {
  const numeric = toNum(value);
  if (numeric === null) {
    return "-";
  }
  return `${numeric.toFixed(digits)}${suffix}`;
}

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

function protocolTone(protocol: string): "healthy" | "warning" | "outline" {
  const upper = protocol.toUpperCase();
  if (upper === "NVME") {
    return "healthy";
  }
  if (upper === "SCSI") {
    return "warning";
  }
  return "outline";
}

function getDeductions(device: DeviceRecord): Array<Record<string, unknown>> {
  const raw = device.deductions;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((item): item is Record<string, unknown> => !!item && typeof item === "object");
}

function telemetryRows(device: DeviceRecord): Array<{ label: string; value: string }> {
  return [
    { label: "Device", value: toText(device.dut) },
    { label: "Model", value: toText(device.model_number) },
    { label: "Serial", value: toText(device.serial_number) },
    { label: "Protocol", value: toText(device.transport_protocol) },
    { label: "Firmware", value: toText(device.firmware_revision) },
    { label: "Capacity", value: `${formatNumber(device.gibibytes, " GiB", 1)} / ${formatNumber(device.terabytes, " TB", 2)}` },
    { label: "Power-On Hours", value: toText(device.power_on_hours) },
    { label: "Power Cycles", value: formatNumber(device.power_cycle_count) },
    { label: "Start/Stop", value: formatNumber(device.start_stop_count) },
    { label: "Load Cycles", value: formatNumber(device.load_cycle_count) },
    { label: "SMART Status", value: toText(device.smart_status, "Unknown") },
    { label: "CDI Grade", value: `${toText(device.health_grade, toText(device.cdi_grade, "-"))} (${toText(device.health_status)})` },
    { label: "Certified", value: toText(device.is_certified ?? device.cdi_certified, "false") },
    { label: "Reallocated", value: formatNumber(device.reallocated_sectors) },
    { label: "Pending", value: formatNumber(device.pending_sectors) },
    { label: "Offline Uncorrectable", value: formatNumber(device.offline_uncorrectable_sectors) },
    { label: "Media Errors", value: formatNumber(device.media_errors) },
    { label: "Critical Warning", value: formatNumber(device.critical_warning) },
    { label: "Percent Used", value: formatNumber(device.percentage_used, "%") },
    { label: "Data Written", value: formatNumber(device.data_written_tb, " TB", 2) },
    { label: "Current Temp", value: formatNumber(device.current_temperature, " C") },
    { label: "Highest Temp", value: formatNumber(device.highest_temperature, " C") },
    { label: "Max Temp", value: formatNumber(device.maximum_temperature, " C") },
    { label: "Self-Test Failures", value: formatNumber(device.nvme_self_test_failed_count) }
  ];
}

const sidebarLinks = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Drive Inventory", icon: HardDrive },
  { label: "Self-Test Ops", icon: PlayCircle },
  { label: "Reports", icon: FileText },
  { label: "Diagnostics", icon: Settings2 }
];

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
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

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
      if (data.devices.length > 0) {
        setSelectedIndex(0);
      }
      setMessage(`Scan completed: ${data.summary.total} device(s)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setBusyAction(null);
    }
  }, [deviceFilter, ignoreAta, ignoreNvme, ignoreScsi]);

  const pollJobUntilDone = useCallback(
    async (jobId: string) => {
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
    },
    [refreshJobs, refreshSelfTestStatus]
  );

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

  const devices = scan?.devices ?? [];
  const focusedDevice = (hoveredIndex !== null ? devices[hoveredIndex] : devices[selectedIndex]) ?? null;
  const deductions = focusedDevice ? getDeductions(focusedDevice) : [];
  const criticalCount = devices.filter((d) => (d.health_score ?? 0) < 40).length;
  const atRiskCount = devices.filter((d) => {
    const score = d.health_score ?? 0;
    return score >= 40 && score < 75;
  }).length;
  const averageScore = devices.length
    ? devices.reduce((acc, item) => acc + (toNum(item.health_score) ?? 0), 0) / devices.length
    : 0;
  const thermalAlertCount = devices.filter((d) => {
    const current = toNum(d.current_temperature);
    const maxTemp = toNum(d.maximum_temperature);
    return current !== null && maxTemp !== null && current > maxTemp;
  }).length;

  const lastJob = useMemo(() => jobs[0] ?? null, [jobs]);

  return (
    <main className="min-h-screen bg-transparent">
      <div className="grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="hidden border-r border-[#3E6071]/15 bg-[#3E6071]/95 px-4 py-6 text-white lg:flex lg:flex-col">
          <div className="mb-8">
            <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#c5dfd5]">CDI Ops</p>
            <h1 className="mt-2 text-2xl font-semibold">Technician Panel</h1>
            <p className="mt-2 text-sm text-[#d7e2ea]">Drive grading and recovery workflow</p>
          </div>

          <nav className="space-y-1">
            {sidebarLinks.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  type="button"
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition",
                    item.active ? "bg-[#139C7A] text-white" : "text-[#d7e2ea] hover:bg-white/10"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="mt-8 space-y-3 rounded-xl border border-white/20 bg-black/10 p-3 text-sm">
            <p className="font-semibold text-[#def2e9]">System Snapshot</p>
            <p>Total devices: {scan?.summary.total ?? 0}</p>
            <p>At risk: {atRiskCount}</p>
            <p>Critical: {criticalCount}</p>
            <p>Thermal alerts: {thermalAlertCount}</p>
            <p>Mode: {useMockData ? "Mock" : "Real"}</p>
          </div>

          <div className="mt-auto rounded-xl border border-white/20 bg-black/10 p-3 text-xs text-[#d7e2ea]">
            {useMockData ? `Mock path: ${mockDataPath}` : "Real hardware mode"}
          </div>
        </aside>

        <section className="p-4 pb-12 md:p-6 lg:p-8">
          <header className="mb-6 rounded-2xl border border-border bg-white/85 p-4 shadow-sm backdrop-blur md:p-6">
            <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-[#3E6071]">Circular Drive Initiative</p>
                <h2 className="mt-1 text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-title)" }}>
                  Dashboard 01: Device Command Center
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">Hover any drive row for richer telemetry in the deep-inspection panel.</p>
              </div>

              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={() => void runScan()} disabled={busyAction === "scan"}>
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>
              </div>
            </div>

            <div className="grid gap-2 md:grid-cols-[1fr_auto]">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="Filter by device path (example: /dev/nvme0)"
                  value={deviceFilter}
                  onChange={(e) => setDeviceFilter(e.target.value)}
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 rounded-md border bg-white px-2 py-1 text-sm">
                  <input type="checkbox" checked={ignoreAta} onChange={(e) => setIgnoreAta(e.target.checked)} /> ATA
                </label>
                <label className="flex items-center gap-2 rounded-md border bg-white px-2 py-1 text-sm">
                  <input type="checkbox" checked={ignoreNvme} onChange={(e) => setIgnoreNvme(e.target.checked)} /> NVMe
                </label>
                <label className="flex items-center gap-2 rounded-md border bg-white px-2 py-1 text-sm">
                  <input type="checkbox" checked={ignoreScsi} onChange={(e) => setIgnoreScsi(e.target.checked)} /> SCSI
                </label>
              </div>
            </div>
          </header>

          {(message || error) && (
            <div className="mb-4 space-y-2">
              {message && <p className="rounded-md border border-[#139C7A]/30 bg-[#139C7A]/10 px-3 py-2 text-sm text-[#3B7351]">{message}</p>}
              {error && <p className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>}
            </div>
          )}

          <section className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
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
              <CardContent className="text-xs text-muted-foreground">Current inventory snapshot</CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Average Score</CardDescription>
                <CardTitle className="text-2xl text-[#3E6071]">{averageScore.toFixed(1)}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">Across scanned devices</CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>At Risk</CardDescription>
                <CardTitle className="text-2xl text-amber-700">{atRiskCount}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">Score 40-74</CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Critical</CardDescription>
                <CardTitle className="text-2xl text-red-700">{criticalCount}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">Score below 40</CardContent>
            </Card>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl">
                  <HardDrive className="h-5 w-5 text-[#3B7351]" />
                  Drive Inventory
                </CardTitle>
                <CardDescription>Hover to inspect. Click to pin a drive in telemetry panel.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Device</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Protocol</TableHead>
                      <TableHead>POH</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Grade</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {devices.map((device, index) => {
                      const isFocused = index === (hoveredIndex ?? selectedIndex);
                      const score = toNum(device.health_score) ?? 0;
                      return (
                        <TableRow
                          key={`${device.dut ?? "dev"}-${index}`}
                          className={cn(isFocused && "bg-[#139C7A]/8")}
                          onMouseEnter={() => setHoveredIndex(index)}
                          onMouseLeave={() => setHoveredIndex(null)}
                          onClick={() => setSelectedIndex(index)}
                        >
                          <TableCell className="font-mono text-xs">{toText(device.dut)}</TableCell>
                          <TableCell>{toText(device.model_number)}</TableCell>
                          <TableCell>
                            <Badge variant={protocolTone(toText(device.transport_protocol))}>{toText(device.transport_protocol)}</Badge>
                          </TableCell>
                          <TableCell>{toText(device.power_on_hours)}</TableCell>
                          <TableCell className="font-semibold">{score || "-"}</TableCell>
                          <TableCell>{toText(device.health_grade, toText(device.cdi_grade, "-"))}</TableCell>
                          <TableCell>
                            <Badge variant={healthVariant(score)}>{toText(device.health_status, "Unknown")}</Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                {devices.length === 0 && <p className="mt-3 text-sm text-muted-foreground">No devices available in current scan.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl">
                  <Wrench className="h-5 w-5 text-[#3E6071]" />
                  Rich Telemetry (Hover)
                </CardTitle>
                <CardDescription>Detailed stats update as you move across drives.</CardDescription>
              </CardHeader>
              <CardContent>
                {!focusedDevice && <p className="text-sm text-muted-foreground">No drive selected.</p>}
                {focusedDevice && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-2">
                      <div className="rounded-md border bg-muted/30 p-2">
                        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Health</p>
                        <p className="text-lg font-semibold">{toText(focusedDevice.health_score, "-")}</p>
                      </div>
                      <div className="rounded-md border bg-muted/30 p-2">
                        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Grade</p>
                        <p className="text-lg font-semibold">{toText(focusedDevice.health_grade, toText(focusedDevice.cdi_grade, "-"))}</p>
                      </div>
                      <div className="rounded-md border bg-muted/30 p-2">
                        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Protocol</p>
                        <p className="text-lg font-semibold">{toText(focusedDevice.transport_protocol)}</p>
                      </div>
                    </div>

                    <div className="grid gap-2 sm:grid-cols-2">
                      {telemetryRows(focusedDevice).map((row) => (
                        <div key={row.label} className="rounded-md border p-2">
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{row.label}</p>
                          <p className="font-medium text-foreground">{row.value}</p>
                        </div>
                      ))}
                    </div>

                    <div className="rounded-md border p-3">
                      <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
                        <AlertTriangle className="h-4 w-4 text-[#3E6071]" />
                        Deductions and Alerts
                      </p>
                      {deductions.length === 0 && <p className="text-sm text-muted-foreground">No deductions recorded for this drive.</p>}
                      {deductions.length > 0 && (
                        <ul className="space-y-1 text-sm">
                          {deductions.map((deduction, idx) => {
                            const reason = toText(deduction.reason, "Unknown issue");
                            const points = toText(deduction.points, "-");
                            const severity = toText(deduction.severity, "info");
                            const value = toText(deduction.value, "-");
                            const threshold = toText(deduction.threshold, "-");
                            return (
                              <li key={`${reason}-${idx}`} className="rounded-md border bg-muted/20 px-2 py-1">
                                <span className="font-semibold">{reason}</span> ({severity})
                                <span className="ml-1">value {value}, threshold {threshold}, -{points} pts</span>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <PlayCircle className="h-5 w-5 text-[#139C7A]" />
                  Self-Test Operations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Input placeholder="/dev/nvme0 (blank means all supported)" value={selfTestDevice} onChange={(e) => setSelfTestDevice(e.target.value)} />

                <div className="grid grid-cols-3 gap-2">
                  <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                    <input type="radio" checked={selfTestType === "short"} onChange={() => setSelfTestType("short")} /> Short
                  </label>
                  <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                    <input type="radio" checked={selfTestType === "extended"} onChange={() => setSelfTestType("extended")} /> Extended
                  </label>
                  <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                    <input type="checkbox" checked={selfTestWait} onChange={(e) => setSelfTestWait(e.target.checked)} /> Wait
                  </label>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void runSelfTest()} disabled={busyAction === "selftest"}>Start</Button>
                  <Button variant="outline" onClick={() => void refreshSelfTestStatus()}>Status</Button>
                  <Button variant="danger" onClick={() => void runAbort()} disabled={busyAction === "abort"}>Abort</Button>
                </div>

                {lastJob && (
                  <p className="rounded-md border border-border bg-muted/40 p-2 font-mono text-xs text-muted-foreground">
                    Last job {lastJob.job_id} ({lastJob.status})
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileText className="h-5 w-5 text-[#3E6071]" />
                  Report Export
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                    <input type="radio" checked={reportFormat === "html"} onChange={() => setReportFormat("html")} /> HTML
                  </label>
                  <label className="flex items-center gap-2 rounded-md border p-2 text-sm">
                    <input type="radio" checked={reportFormat === "pdf"} onChange={() => setReportFormat("pdf")} /> PDF
                  </label>
                </div>

                <Input placeholder="/var/tmp/cdi-report.html" value={reportOutput} onChange={(e) => setReportOutput(e.target.value)} />
                <Button onClick={() => void runReport()} disabled={busyAction === "report"}>Generate Report</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Thermometer className="h-5 w-5 text-[#3E6071]" />
                  Live Alerts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="rounded-md border p-2">
                  <p className="font-semibold">Thermal overruns</p>
                  <p className="text-muted-foreground">{thermalAlertCount} drive(s)</p>
                </div>
                <div className="rounded-md border p-2">
                  <p className="font-semibold">Failed health score</p>
                  <p className="text-muted-foreground">{criticalCount} drive(s)</p>
                </div>
                <div className="rounded-md border p-2">
                  <p className="font-semibold">Certification candidates</p>
                  <p className="text-muted-foreground">{scan?.summary.healthy ?? 0} drive(s)</p>
                </div>

                <div className="space-y-2 pt-2">
                  {(selfTestStatus?.devices ?? []).slice(0, 4).map((entry) => (
                    <div key={entry.device} className="flex items-center justify-between rounded-md border p-2">
                      <span className="font-mono text-xs">{entry.device}</span>
                      <Badge variant={entry.failed ? "failed" : entry.in_progress ? "warning" : entry.passed ? "healthy" : "outline"}>
                        {entry.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </section>

          <section className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-[#139C7A]/30 bg-[#139C7A]/10 p-3 text-sm text-[#3B7351]">
              <p className="mb-1 flex items-center gap-2 font-semibold">
                <ShieldCheck className="h-4 w-4" />
                Reuse Ready
              </p>
              <p>{scan?.summary.healthy ?? 0} drives currently pass CDI thresholds.</p>
            </div>
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="mb-1 flex items-center gap-2 font-semibold">
                <AlertTriangle className="h-4 w-4" />
                Technician Review
              </p>
              <p>{atRiskCount} drives in warning range need verification.</p>
            </div>
            <div className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              <p className="mb-1 flex items-center gap-2 font-semibold">
                <ShieldX className="h-4 w-4" />
                Failed Inventory
              </p>
              <p>{criticalCount} drives have critical health scores.</p>
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
