"use client";

import { FileText, FileType2, FolderOutput, Printer } from "lucide-react";
import { useEffect, useState, type ReactElement } from "react";

import { useDashboard } from "@/components/dashboard-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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

export function ReportsView(): ReactElement {
  const { scan, latestReport, reportHistory, runReport, busy, preferences } = useDashboard();
  const [format, setFormat] = useState<"html" | "pdf">("html");
  const [outputPath, setOutputPath] = useState("");
  const [device, setDevice] = useState("");
  const [ignoreAta, setIgnoreAta] = useState(preferences.defaultIgnoreAta);
  const [ignoreNvme, setIgnoreNvme] = useState(preferences.defaultIgnoreNvme);
  const [ignoreScsi, setIgnoreScsi] = useState(preferences.defaultIgnoreScsi);

  useEffect(() => {
    setIgnoreAta(preferences.defaultIgnoreAta);
    setIgnoreNvme(preferences.defaultIgnoreNvme);
    setIgnoreScsi(preferences.defaultIgnoreScsi);
  }, [preferences.defaultIgnoreAta, preferences.defaultIgnoreNvme, preferences.defaultIgnoreScsi]);

  const submitReport = async (): Promise<void> => {
    await runReport({
      format,
      output_file: outputPath.trim() || undefined,
      ignore_ata: ignoreAta,
      ignore_nvme: ignoreNvme,
      ignore_scsi: ignoreScsi,
      device: device.trim() || undefined
    });
  };

  return (
    <div className="space-y-4">
      <section>
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-[#3E6071]">Reports</p>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-title)" }}>
          Technician Handoff Exports
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">Generate HTML or PDF snapshots that summarize the same telemetry shown in the console.</p>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Printer className="h-5 w-5 text-[#139C7A]" />
              Generate Report
            </CardTitle>
            <CardDescription>Use filters to generate a full-fleet report or a single-drive report.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <input type="radio" checked={format === "html"} onChange={() => setFormat("html")} /> HTML
              </label>
              <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <input type="radio" checked={format === "pdf"} onChange={() => setFormat("pdf")} /> PDF
              </label>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground" htmlFor="report-device">
                Optional Device Path
              </label>
              <Input id="report-device" placeholder="/dev/nvme0 (optional)" value={device} onChange={(event) => setDevice(event.target.value)} />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground" htmlFor="report-output">
                Output File
              </label>
              <Input
                id="report-output"
                placeholder={format === "html" ? "/var/tmp/cdi-report.html" : "/var/tmp/cdi-report.pdf"}
                value={outputPath}
                onChange={(event) => setOutputPath(event.target.value)}
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

            <Button onClick={() => void submitReport()} disabled={busy.report}>Generate Report</Button>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-[#3E6071]" />
                Current Scan Snapshot
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="rounded-lg border p-2">
                <p className="font-semibold">Total devices</p>
                <p className="text-muted-foreground">{scan?.summary.total ?? 0}</p>
              </div>
              <div className="rounded-lg border p-2">
                <p className="font-semibold">Healthy</p>
                <p className="text-muted-foreground">{scan?.summary.healthy ?? 0}</p>
              </div>
              <div className="rounded-lg border p-2">
                <p className="font-semibold">Warning + failed</p>
                <p className="text-muted-foreground">{(scan?.summary.warning ?? 0) + (scan?.summary.failed ?? 0)}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FolderOutput className="h-5 w-5 text-[#3E6071]" />
                Latest Output
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="font-semibold">File:</span> {latestReport?.output_file ?? "-"}
              </p>
              <p>
                <span className="font-semibold">Format:</span> {latestReport?.format ?? "-"}
              </p>
              <p>
                <span className="font-semibold">Devices:</span> {latestReport?.devices_count ?? "-"}
              </p>
              <p>
                <span className="font-semibold">Generated:</span> {formatDate(latestReport?.generated_at)}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileType2 className="h-5 w-5 text-[#3E6071]" />
            Report History (Session)
          </CardTitle>
          <CardDescription>Most recent generated artifacts from this dashboard session.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Generated</TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Devices</TableHead>
                <TableHead>Output File</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reportHistory.map((entry, index) => (
                <TableRow key={`${entry.generated_at}-${index}`}>
                  <TableCell>{formatDate(entry.generated_at)}</TableCell>
                  <TableCell>{entry.format.toUpperCase()}</TableCell>
                  <TableCell>{entry.devices_count}</TableCell>
                  <TableCell className="font-mono text-xs">{entry.output_file}</TableCell>
                </TableRow>
              ))}

              {reportHistory.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-sm text-muted-foreground">
                    No reports generated yet in this session.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
