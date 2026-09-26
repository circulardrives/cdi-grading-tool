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

/** Pages below a nav item with their own header title (and no scope switcher). */
const SUB_PAGES: { pattern: RegExp; title: string }[] = [
  // /drives/:benchKey/:serial — full-screen drive details.
  { pattern: /^\/drives\/[^/]+\/[^/]+\/?$/, title: "Drive details" },
]

function subPageFor(pathname: string) {
  return SUB_PAGES.find((page) => page.pattern.test(pathname)) ?? null
}

export function pageTitleFor(pathname: string): string {
  return (
    subPageFor(pathname)?.title ?? navItemFor(pathname)?.label ?? "CDI Health"
  )
}

/** Show the "All benches ▾" scope switcher on this path. */
export function pageScopedFor(pathname: string): boolean {
  return !subPageFor(pathname) && (navItemFor(pathname)?.scoped ?? false)
}
