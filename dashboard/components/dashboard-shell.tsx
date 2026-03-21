"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, AlertTriangle, RefreshCcw, ScanLine } from "lucide-react";
import { type ReactNode } from "react";

import { navItems } from "@/components/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDashboard } from "@/components/dashboard-provider";
import { cn } from "@/lib/utils";

function pathIsActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function DashboardShell({ children }: { children: ReactNode }): JSX.Element {
  const pathname = usePathname();
  const { health, scan, selfTestStatus, busy, message, error, setMessage, setError, refreshAll, runScan, useMockData, mockPath } = useDashboard();

  const criticalCount = (scan?.devices ?? []).filter((device) => {
    const score = typeof device.health_score === "number" ? device.health_score : Number(device.health_score ?? 0);
    return Number.isFinite(score) && score < 40;
  }).length;

  const selfTestsInProgress = (selfTestStatus?.devices ?? []).filter((item) => item.in_progress).length;

  const runQuickScan = async (): Promise<void> => {
    await runScan({
      ignore_ata: false,
      ignore_nvme: false,
      ignore_scsi: false
    });
  };

  return (
    <main className="min-h-screen bg-transparent">
      <div className="grid min-h-screen lg:grid-cols-[292px_1fr]">
        <aside className="hidden border-r border-[#3E6071]/25 bg-[#3E6071] text-white lg:flex lg:flex-col">
          <div className="px-5 pb-6 pt-7">
            <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-[#d7ece4]">Technician Console</p>
            <h1 className="mt-3 text-3xl font-semibold" style={{ fontFamily: "var(--font-title)" }}>
              CDI Dashboard
            </h1>
            <p className="mt-3 text-sm text-[#d4e3ea]">Datacenter triage workflow for scan, self-test, and handoff reporting.</p>
          </div>

          <nav className="space-y-1 px-3">
            {navItems.map((item) => {
              const active = pathIsActive(pathname, item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "block rounded-xl border border-transparent px-4 py-3 transition",
                    active ? "border-[#139C7A] bg-[#139C7A] text-white" : "text-[#d8e4ea] hover:border-white/20 hover:bg-white/8"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    <span className="text-sm font-semibold">{item.label}</span>
                  </div>
                  <p className={cn("mt-1 pl-7 text-xs", active ? "text-[#e8fff8]" : "text-[#bdd1db]")}>{item.description}</p>
                </Link>
              );
            })}
          </nav>

          <div className="mt-6 space-y-3 px-5">
            <div className="rounded-xl border border-white/20 bg-black/15 p-3 text-xs text-[#d8e4ea]">
              <p className="font-semibold text-[#edf8f4]">Live Snapshot</p>
              <p className="mt-2">Devices: {scan?.summary.total ?? 0}</p>
              <p>Critical: {criticalCount}</p>
              <p>Self-tests running: {selfTestsInProgress}</p>
              <p>Root: {String(health?.is_root ?? false)}</p>
            </div>

            <div className="rounded-xl border border-white/20 bg-black/15 p-3 text-xs text-[#d8e4ea]">
              <p className="font-semibold text-[#edf8f4]">Runtime Mode</p>
              <p className="mt-1">{useMockData ? "Mock data" : "Live hardware"}</p>
              <p className="break-all text-[#c3d7df]">{useMockData ? mockPath : "Backend commands enabled"}</p>
            </div>
          </div>

          <div className="mt-auto border-t border-white/15 px-5 py-4 text-[11px] text-[#b6cad4]">Circular Drive Initiative</div>
        </aside>

        <section className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-20 border-b border-border/70 bg-background/95 px-4 py-3 backdrop-blur md:px-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-wrap items-center gap-2 lg:hidden">
                {navItems.map((item) => {
                  const active = pathIsActive(pathname, item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "rounded-lg border px-3 py-1.5 text-xs font-semibold",
                        active ? "border-[#139C7A] bg-[#139C7A] text-white" : "border-border bg-white/70 text-foreground"
                      )}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </div>

              <div className="flex items-center gap-2">
                <Badge variant={health?.status === "ok" ? "healthy" : "warning"} className="h-7 px-3">
                  <Activity className="mr-1 h-3.5 w-3.5" />
                  Backend {health?.status ?? "loading"}
                </Badge>
                {criticalCount > 0 && (
                  <Badge variant="failed" className="h-7 px-3">
                    <AlertTriangle className="mr-1 h-3.5 w-3.5" />
                    {criticalCount} critical
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => void refreshAll()} disabled={busy.refresh}>
                  <RefreshCcw className="mr-1.5 h-4 w-4" />
                  Refresh Status
                </Button>
                <Button size="sm" onClick={() => void runQuickScan()} disabled={busy.scan}>
                  <ScanLine className="mr-1.5 h-4 w-4" />
                  Quick Scan
                </Button>
              </div>
            </div>
          </header>

          <div className="flex-1 space-y-4 p-4 pb-10 md:p-6">
            {(message || error) && (
              <div className="space-y-2">
                {message && (
                  <button
                    type="button"
                    onClick={() => setMessage(null)}
                    className="w-full rounded-lg border border-[#139C7A]/35 bg-[#139C7A]/10 px-3 py-2 text-left text-sm text-[#1d5d47]"
                  >
                    {message}
                  </button>
                )}
                {error && (
                  <button
                    type="button"
                    onClick={() => setError(null)}
                    className="w-full rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-left text-sm text-red-900"
                  >
                    {error}
                  </button>
                )}
              </div>
            )}

            {children}
          </div>
        </section>
      </div>
    </main>
  );
}
