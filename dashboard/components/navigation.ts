import { FileText, HardDrive, LayoutDashboard, PlayCircle, Settings2, type LucideIcon } from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
};

export const navItems: NavItem[] = [
  {
    href: "/summary",
    label: "Summary",
    icon: LayoutDashboard,
    description: "Fleet snapshot, status, and active incidents"
  },
  {
    href: "/drive-health",
    label: "Drive Health",
    icon: HardDrive,
    description: "Scan inventory and inspect drive-level telemetry"
  },
  {
    href: "/self-test",
    label: "Self-Test",
    icon: PlayCircle,
    description: "Launch NVMe tests, monitor state, and abort jobs"
  },
  {
    href: "/reports",
    label: "Reports",
    icon: FileText,
    description: "Generate technician handoff reports"
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings2,
    description: "Configure dashboard behavior and runtime defaults"
  }
];
