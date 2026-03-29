import type { ReactElement, ReactNode } from "react";

import { DashboardProvider } from "@/components/dashboard-provider";
import { DashboardShell } from "@/components/dashboard-shell";

export default function ConsoleLayout({ children }: { children: ReactNode }): ReactElement {
  return (
    <DashboardProvider>
      <DashboardShell>{children}</DashboardShell>
    </DashboardProvider>
  );
}
