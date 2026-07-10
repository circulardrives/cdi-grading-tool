import { Link, useLocation } from "react-router-dom"
import {
  FileOutputIcon,
  HardDriveIcon,
  LayoutDashboardIcon,
  RadarIcon,
  ScanSearchIcon,
  ServerIcon,
  TestTubeDiagonalIcon,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@workspace/ui/components/sidebar"
import { Badge } from "@workspace/ui/components/badge"

import { CdiLogo, CdiLogoMark } from "@/components/cdi-logo"
import { useMockDataSettings } from "@/components/mock-data-provider"
import { appConfig } from "@/lib/config"

function formatApiHostLabel(apiHost: string): string {
  try {
    const url = new URL(apiHost)
    return url.host || apiHost.replace(/^https?:\/\//, "")
  } catch {
    return apiHost.replace(/^https?:\/\//, "")
  }
}

function isLocalApiHost(apiHost: string): boolean {
  const host = formatApiHostLabel(apiHost).toLowerCase()
  return (
    host.startsWith("127.0.0.1") ||
    host.startsWith("localhost") ||
    host.startsWith("[::1]")
  )
}

const navItems = [
  {
    to: "/",
    label: "Fleet Status",
    icon: LayoutDashboardIcon,
    description: "Host readiness and fleet counts",
  },
  {
    to: "/hosts",
    label: "Hosts",
    icon: ServerIcon,
    description: "Fleet registry and active host context",
  },
  {
    to: "/discover",
    label: "Discover",
    icon: RadarIcon,
    description: "Find CDI APIs on your LAN",
  },
  {
    to: "/scan",
    label: "Scan",
    icon: ScanSearchIcon,
    description: "Run drive grading scans",
  },
  {
    to: "/drives",
    label: "Drive Health",
    icon: HardDriveIcon,
    description: "Simple and detailed drive tables",
  },
  {
    to: "/reports",
    label: "Health Reports",
    icon: FileOutputIcon,
    description: "Generate offline HTML, PDF, or CSV",
  },
  {
    to: "/self-test",
    label: "NVMe Self-Test",
    icon: TestTubeDiagonalIcon,
    description: "Run and monitor NVMe device self-tests",
  },
] as const

export function AppSidebar() {
  const location = useLocation()
  const { useMockData } = useMockDataSettings()
  const apiHostLabel = formatApiHostLabel(appConfig.apiHost)
  const localApi = isLocalApiHost(appConfig.apiHost)

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader className="border-b border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              asChild
              tooltip="Circular Drive Initiative"
              className="!h-auto min-h-[6.5rem] py-3 [&_svg]:!size-auto"
            >
              <Link
                to="/"
                className="group-data-[collapsible=icon]:justify-center"
              >
                <CdiLogoMark className="hidden size-8 group-data-[collapsible=icon]:block" />
                <CdiLogo className="max-h-[96px] group-data-[collapsible=icon]:hidden" />
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Operations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const active =
                  item.to === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(item.to)

                return (
                  <SidebarMenuItem key={item.to}>
                    <SidebarMenuButton
                      isActive={active}
                      tooltip={item.description}
                      asChild
                    >
                      <Link to={item.to}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="flex flex-col gap-2 px-2 py-1">
          <div className="text-muted-foreground flex min-w-0 items-center gap-2 text-xs">
            <Badge variant="outline">{localApi ? "Local API" : "API host"}</Badge>
            <span className="truncate font-mono" title={appConfig.apiHost}>
              {apiHostLabel}
            </span>
          </div>
          {useMockData ? (
            <Badge variant="secondary" className="w-fit">
              Mock scan data
            </Badge>
          ) : null}
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
