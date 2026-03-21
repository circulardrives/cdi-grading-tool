import type { ReactNode } from "react";

import { DashboardProvider } from "@/components/dashboard-provider";
import { DashboardShell } from "@/components/dashboard-shell";

export default function ConsoleLayout({ children }: { children: ReactNode }): JSX.Element {
  return (
    <DashboardProvider>
      <DashboardShell>{children}</DashboardShell>
    </DashboardProvider>
  );
}
