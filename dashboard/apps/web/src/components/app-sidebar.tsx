import { Link, useLocation } from "react-router-dom"
import {
  FileOutputIcon,
  HardDriveIcon,
  LayoutDashboardIcon,
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

import { appConfig } from "@/lib/config"

import { CdiLogo, CdiLogoMark } from "@/components/cdi-logo"

const navItems = [
  {
    to: "/",
    label: "Fleet Status",
    icon: LayoutDashboardIcon,
    description: "Host readiness and fleet counts",
  },
  {
    to: "/drives",
    label: "Drive Health",
    icon: HardDriveIcon,
    description: "Simple and detailed drive tables",
  },
  {
    to: "/machines",
    label: "Hosts & Scans",
    icon: ServerIcon,
    description: "Register racks and run drive scans",
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

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader className="border-b border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild tooltip="Circular Drive Initiative">
              <Link
                to="/"
                className="group-data-[collapsible=icon]:justify-center"
              >
                <CdiLogoMark className="hidden group-data-[collapsible=icon]:block" />
                <CdiLogo className="max-w-[180px] group-data-[collapsible=icon]:hidden" />
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
            <Badge variant="outline">Local API</Badge>
            <span className="truncate font-mono">127.0.0.1:8844</span>
          </div>
          {appConfig.useMockData ? (
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
