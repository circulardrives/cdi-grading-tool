"use client";

import { AlertTriangle, Search, Thermometer, Wrench } from "lucide-react";
import { useEffect, useMemo, useState, type ReactElement } from "react";

import { useDashboard } from "@/components/dashboard-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { buildErrorSummary, getDeductions, healthTone, protocolTone, telemetryRows, toNum, toText } from "@/lib/drive";
import { cn } from "@/lib/utils";

type DeviceSelection = {
  key: string;
  device: Record<string, unknown>;
};

function deviceKey(device: Record<string, unknown>, index: number): string {
  const dut = toText(device.dut, `device-${index}`);
  const serial = toText(device.serial_number, "n/a");
  return `${dut}::${serial}::${index}`;
}

export function DriveHealthView(): ReactElement {
  const { scan, runScan, busy, preferences } = useDashboard();
  const [deviceInput, setDeviceInput] = useState("");
  const [searchText, setSearchText] = useState("");
  const [ignoreAta, setIgnoreAta] = useState(preferences.defaultIgnoreAta);
  const [ignoreNvme, setIgnoreNvme] = useState(preferences.defaultIgnoreNvme);
  const [ignoreScsi, setIgnoreScsi] = useState(preferences.defaultIgnoreScsi);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  useEffect(() => {
    setIgnoreAta(preferences.defaultIgnoreAta);
    setIgnoreNvme(preferences.defaultIgnoreNvme);
    setIgnoreScsi(preferences.defaultIgnoreScsi);
  }, [preferences.defaultIgnoreAta, preferences.defaultIgnoreNvme, preferences.defaultIgnoreScsi]);

  const devices = useMemo<DeviceSelection[]>(() => {
    return (scan?.devices ?? []).map((device, index) => ({
      key: deviceKey(device, index),
      device
    }));
  }, [scan?.devices]);

  const filteredDevices = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) {
      return devices;
    }

    return devices.filter(({ device }) => {
      const text = [
        toText(device.dut),
        toText(device.model_number),
        toText(device.serial_number),
        toText(device.transport_protocol),
        toText(device.health_grade),
        toText(device.health_status)
      ]
        .join(" ")
        .toLowerCase();

      return text.includes(query);
    });
  }, [devices, searchText]);

  useEffect(() => {
    if (filteredDevices.length === 0) {
      setSelectedKey(null);
      return;
    }

    if (!selectedKey || !filteredDevices.some((item) => item.key === selectedKey)) {
      setSelectedKey(filteredDevices[0].key);
    }
  }, [filteredDevices, selectedKey]);

  const focusedKey = hoveredKey ?? selectedKey;
  const focused = filteredDevices.find((item) => item.key === focusedKey) ?? filteredDevices[0] ?? null;
  const focusedDevice = focused?.device ?? null;

  const runFilteredScan = async (): Promise<void> => {
    await runScan({
      ignore_ata: ignoreAta,
      ignore_nvme: ignoreNvme,
      ignore_scsi: ignoreScsi,
      device: deviceInput.trim() || undefined
    });
  };

  const atRiskCount = filteredDevices.filter((item) => {
    const score = toNum(item.device.health_score);
    return score !== null && score >= 40 && score < 75;
  }).length;

  const criticalCount = filteredDevices.filter((item) => {
    const score = toNum(item.device.health_score);
    return score !== null && score < 40;
  }).length;

  const thermalAlerts = filteredDevices.filter((item) => {
    const current = toNum(item.device.current_temperature);
    const maxTemp = toNum(item.device.maximum_temperature);
    return current !== null && maxTemp !== null && current > maxTemp;
  }).length;

  const deductions = focusedDevice ? getDeductions(focusedDevice) : [];

  return (
    <div className="space-y-4">
      <section>
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-[#3E6071]">Drive Health</p>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-title)" }}>
          Inventory + Deep Telemetry
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">Hover any row to instantly preview rich metrics before deciding on test or report actions.</p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Visible Devices</CardDescription>
            <CardTitle className="text-2xl">{filteredDevices.length}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Current table filter</CardContent>
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

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Thermal Alerts</CardDescription>
            <CardTitle className="text-2xl text-[#3E6071]">{thermalAlerts}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Current temp above maximum</CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Scan Controls</CardTitle>
          <CardDescription>Target a specific device path or protocol group for faster triage.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[1.2fr_1fr_auto] md:items-end">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground" htmlFor="scan-device">
              Device Path
            </label>
            <Input
              id="scan-device"
              placeholder="/dev/nvme0 (optional)"
              value={deviceInput}
              onChange={(event) => setDeviceInput(event.target.value)}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input type="checkbox" checked={ignoreAta} onChange={(event) => setIgnoreAta(event.target.checked)} /> Ignore ATA
            </label>
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input type="checkbox" checked={ignoreNvme} onChange={(event) => setIgnoreNvme(event.target.checked)} /> Ignore NVMe
            </label>
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input type="checkbox" checked={ignoreScsi} onChange={(event) => setIgnoreScsi(event.target.checked)} /> Ignore SCSI
            </label>
          </div>

          <Button onClick={() => void runFilteredScan()} disabled={busy.scan}>
            Run Scan
          </Button>
        </CardContent>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Drive Table</CardTitle>
            <CardDescription>Click to pin. Hover to preview instantly in telemetry panel.</CardDescription>
            <div className="relative mt-2 max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="Search model, serial, protocol, grade" value={searchText} onChange={(event) => setSearchText(event.target.value)} />
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Protocol</TableHead>
                  <TableHead>Power Hours</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Errors</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDevices.map((item) => {
                  const score = toNum(item.device.health_score);
                  const active = item.key === focusedKey;

                  return (
                    <TableRow
                      key={item.key}
                      className={cn(active && "bg-[#139C7A]/10")}
                      onMouseEnter={() => setHoveredKey(item.key)}
                      onMouseLeave={() => setHoveredKey(null)}
                      onClick={() => setSelectedKey(item.key)}
                    >
                      <TableCell className={cn("font-mono text-xs", preferences.denseTableRows && "py-2")}>{toText(item.device.dut)}</TableCell>
                      <TableCell className={cn(preferences.denseTableRows && "py-2")}>{toText(item.device.model_number)}</TableCell>
                      <TableCell className={cn(preferences.denseTableRows && "py-2")}>
                        <Badge variant={protocolTone(toText(item.device.transport_protocol))}>{toText(item.device.transport_protocol)}</Badge>
                      </TableCell>
                      <TableCell className={cn(preferences.denseTableRows && "py-2")}>{toText(item.device.power_on_hours)}</TableCell>
                      <TableCell className={cn("font-semibold", preferences.denseTableRows && "py-2")}>{score ?? "-"}</TableCell>
                      <TableCell className={cn("font-mono text-xs", preferences.denseTableRows && "py-2")}>{buildErrorSummary(item.device)}</TableCell>
                      <TableCell className={cn(preferences.denseTableRows && "py-2")}>
                        <Badge variant={healthTone(score ?? undefined)}>{toText(item.device.health_status, "Unknown")}</Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}

                {filteredDevices.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-sm text-muted-foreground">
                      No drives match the current search.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-[#3E6071]" /> Rich Telemetry
            </CardTitle>
            <CardDescription>Live detail panel based on hover/focus state from the drive table.</CardDescription>
          </CardHeader>
          <CardContent>
            {!focusedDevice && <p className="text-sm text-muted-foreground">No drive selected.</p>}

            {focusedDevice && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg border bg-muted/25 p-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Health Score</p>
                    <p className="text-lg font-semibold">{toText(focusedDevice.health_score)}</p>
                  </div>
                  <div className="rounded-lg border bg-muted/25 p-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Grade</p>
                    <p className="text-lg font-semibold">{toText(focusedDevice.health_grade, toText(focusedDevice.cdi_grade))}</p>
                  </div>
                  <div className="rounded-lg border bg-muted/25 p-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Protocol</p>
                    <p className="text-lg font-semibold">{toText(focusedDevice.transport_protocol)}</p>
                  </div>
                </div>

                <div className="grid gap-2 sm:grid-cols-2">
                  {telemetryRows(focusedDevice).map((row) => (
                    <div key={row.label} className="rounded-md border p-2">
                      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{row.label}</p>
                      <p className="font-medium">{row.value}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg border p-3">
                  <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
                    <AlertTriangle className="h-4 w-4 text-[#3E6071]" />
                    Deductions + Alert Logic
                  </p>

                  {deductions.length === 0 && <p className="text-sm text-muted-foreground">No deductions recorded for this drive.</p>}

                  {deductions.length > 0 && (
                    <ul className="space-y-1 text-sm">
                      {deductions.map((entry, index) => (
                        <li key={`${toText(entry.reason)}-${index}`} className="rounded-md border bg-muted/25 px-2 py-1">
                          <span className="font-semibold">{toText(entry.reason, "Unknown issue")}</span>
                          <span className="ml-2">severity {toText(entry.severity, "info")}</span>
                          <span className="ml-2">value {toText(entry.value, "-")}</span>
                          <span className="ml-2">threshold {toText(entry.threshold, "-")}</span>
                          <span className="ml-2">-{toText(entry.points, "-")} pts</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="rounded-lg border border-[#3E6071]/25 bg-[#3E6071]/5 p-3 text-sm">
                  <p className="mb-1 flex items-center gap-2 font-semibold">
                    <Thermometer className="h-4 w-4 text-[#3E6071]" />
                    Thermal Summary
                  </p>
                  <p className="text-muted-foreground">
                    Current {toText(focusedDevice.current_temperature, "-")} C, highest {toText(focusedDevice.highest_temperature, "-")} C, max {toText(focusedDevice.maximum_temperature, "-")} C.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
