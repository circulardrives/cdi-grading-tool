/**
 * App shell: sidebar + (header with demo banner and scan progress, page). Page padding is 28px 32px
 * on desktop and 16px on phones; sections are 24px apart (see ui-cdi/README.md).
 */
import { useState, type CSSProperties } from "react"
import { Outlet, useLocation } from "react-router-dom"

import { SidebarInset, SidebarProvider } from "@workspace/ui/components/sidebar"
import { TooltipProvider } from "@workspace/ui/components/tooltip"

import { AppHeader } from "@/components/app-header"
import { navItemFor, pageTitleFor } from "@/components/app-routes"
import { AppSidebar } from "@/components/app-sidebar"

/** Tablets and small laptops start with the sidebar collapsed to icons. */
const COLLAPSE_QUERY = "(max-width: 1199px)"

function startsCollapsed(): boolean {
  try {
    return window.matchMedia(COLLAPSE_QUERY).matches
  } catch {
    return false
  }
}

export function AppLayout() {
  const location = useLocation()
  const [open, setOpen] = useState(() => !startsCollapsed())
  const title = pageTitleFor(location.pathname)
  const showScope = navItemFor(location.pathname)?.scoped ?? false

  return (
    <TooltipProvider>
      <SidebarProvider
        open={open}
        onOpenChange={setOpen}
        style={
          {
            "--sidebar-width": "14.5rem",
            "--sidebar-width-icon": "3.75rem",
          } as CSSProperties
        }
      >
        <AppSidebar />
        <SidebarInset className="min-w-0">
          <AppHeader title={title} showScope={showScope} />
          {/* SidebarInset is the <main> landmark; this is the page body. */}
          <div
            id="page"
            className="flex min-w-0 flex-1 flex-col gap-6 px-8 py-7 max-md:px-4 max-md:py-4"
          >
            <Outlet />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
