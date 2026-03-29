"use client";

import { Cpu, Gauge, ShieldCheck, SlidersHorizontal } from "lucide-react";
import type { ReactElement } from "react";

import { useDashboard } from "@/components/dashboard-provider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function SettingsView(): ReactElement {
  const { health, useMockData, mockPath, preferences, updatePreferences } = useDashboard();

  return (
    <div className="space-y-4">
      <section>
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-[#3E6071]">Settings</p>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-title)" }}>
          Technician Preferences
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">Tune default behavior for scan filters, table density, confirmations, and status refresh cadence.</p>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SlidersHorizontal className="h-5 w-5 text-[#139C7A]" />
              Console Behavior
            </CardTitle>
            <CardDescription>Saved in browser local storage for this workstation.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.autoRefreshEnabled}
                onChange={(event) => updatePreferences({ autoRefreshEnabled: event.target.checked })}
              />
              Auto-refresh health/jobs/status
            </label>

            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground" htmlFor="auto-refresh-seconds">
                Auto-refresh Interval (seconds)
              </label>
              <Input
                id="auto-refresh-seconds"
                type="number"
                min={15}
                step={5}
                value={String(preferences.autoRefreshSeconds)}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  updatePreferences({ autoRefreshSeconds: Number.isFinite(value) ? Math.max(15, value) : 30 });
                }}
              />
            </div>

            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.confirmAbort}
                onChange={(event) => updatePreferences({ confirmAbort: event.target.checked })}
              />
              Confirm before sending abort command
            </label>

            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.denseTableRows}
                onChange={(event) => updatePreferences({ denseTableRows: event.target.checked })}
              />
              Dense drive table rows
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5 text-[#3E6071]" />
              Runtime Environment
            </CardTitle>
            <CardDescription>Backend and mode values detected at startup.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              <span className="font-semibold">Mode:</span> {useMockData ? "Mock data" : "Live hardware"}
            </p>
            <p>
              <span className="font-semibold">Mock path:</span> {mockPath}
            </p>
            <p>
              <span className="font-semibold">Backend status:</span> {health?.status ?? "loading"}
            </p>
            <p>
              <span className="font-semibold">Running as root:</span> {String(health?.is_root ?? false)}
            </p>
            <p>
              <span className="font-semibold">API token required:</span> {String(health?.api_token_enabled ?? false)}
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShieldCheck className="h-5 w-5 text-[#3E6071]" />
              Default Scan Exclusions
            </CardTitle>
            <CardDescription>Applied as starting values in Drive Health and Reports pages.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.defaultIgnoreAta}
                onChange={(event) => updatePreferences({ defaultIgnoreAta: event.target.checked })}
              />
              Ignore ATA by default
            </label>
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.defaultIgnoreNvme}
                onChange={(event) => updatePreferences({ defaultIgnoreNvme: event.target.checked })}
              />
              Ignore NVMe by default
            </label>
            <label className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.defaultIgnoreScsi}
                onChange={(event) => updatePreferences({ defaultIgnoreScsi: event.target.checked })}
              />
              Ignore SCSI by default
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Cpu className="h-5 w-5 text-[#3E6071]" />
              Required Tools
            </CardTitle>
            <CardDescription>Missing CLI tooling appears here and on the Summary page.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(health?.missing_required_tools ?? []).length === 0 && <p className="text-[#3B7351]">No missing tools detected.</p>}
            {(health?.missing_required_tools ?? []).map((tool) => (
              <p key={tool} className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-red-900">
                {tool}
              </p>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
