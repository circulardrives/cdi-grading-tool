/**
 * Navigation and page titles for the app shell (sidebar + header).
 * Old paths (/hosts, /discover, /scan, /history, /self-test) redirect in App.tsx.
 */
import {
  ActivityIcon,
  FileTextIcon,
  HardDriveIcon,
  LayoutGridIcon,
  ServerIcon,
  SettingsIcon,
  type LucideIcon,
} from "lucide-react"

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  /** Show the "All benches ▾" scope switcher in the header on this page. */
  scoped: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", icon: LayoutGridIcon, scoped: true },
  { to: "/drives", label: "Drives", icon: HardDriveIcon, scoped: true },
  { to: "/benches", label: "Benches", icon: ServerIcon, scoped: false },
  { to: "/self-tests", label: "Self-tests", icon: ActivityIcon, scoped: false },
  { to: "/reports", label: "Reports", icon: FileTextIcon, scoped: true },
]

export const SETTINGS_ITEM: NavItem = {
  to: "/settings",
  label: "Settings",
  icon: SettingsIcon,
  scoped: false,
}

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (item.to === "/") {
    return pathname === "/"
  }
  return pathname === item.to || pathname.startsWith(`${item.to}/`)
}

/** The nav item for a path (Reports for /reports/history/:id, …). */
export function navItemFor(pathname: string): NavItem | null {
  return (
    [...NAV_ITEMS, SETTINGS_ITEM].find((item) =>
      isNavItemActive(item, pathname)
    ) ?? null
  )
}

export function pageTitleFor(pathname: string): string {
  return navItemFor(pathname)?.label ?? "CDI Health"
}
