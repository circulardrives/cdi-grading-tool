/**
 * Sidebar: CDI mark + "CDI Health / Circular Drive Initiative", the five
 * page links, and Settings pinned at the bottom. Collapses to icons on
 * tablets (toggle in the header) and becomes a sheet on phones.
 */
import { Link, useLocation } from "react-router-dom"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@workspace/ui/components/sidebar"
import { cn } from "@workspace/ui/lib/utils"

import {
  isNavItemActive,
  NAV_ITEMS,
  SETTINGS_ITEM,
  type NavItem,
} from "@/components/app-routes"
import { CdiLogoMark } from "@/components/cdi-logo"

// 44px rows, 16px text (mockup .nav a). The collapsed icon rail keeps 44px too.
const NAV_BUTTON =
  "h-11 gap-3 rounded-[10px] px-3.5 text-base font-medium text-sidebar-foreground [&_svg]:size-5 group-data-[collapsible=icon]:size-11! group-data-[collapsible=icon]:p-3! data-active:bg-sidebar-accent data-active:font-bold data-active:text-sidebar-accent-foreground"

function NavLink({ item }: { item: NavItem }) {
  const location = useLocation()
  const { isMobile, setOpenMobile } = useSidebar()
  const active = isNavItemActive(item, location.pathname)

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        asChild
        isActive={active}
        tooltip={item.label}
        className={NAV_BUTTON}
      >
        <Link
          to={item.to}
          aria-current={active ? "page" : undefined}
          onClick={() => {
            if (isMobile) {
              setOpenMobile(false)
            }
          }}
        >
          <item.icon aria-hidden="true" />
          <span>{item.label}</span>
        </Link>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon" className="border-sidebar-border">
      <SidebarHeader className="px-3.5 pt-5 pb-2 group-data-[collapsible=icon]:px-2">
        <Link
          to="/"
          className={cn(
            "flex items-center gap-2.5 rounded-[10px] px-1.5 py-1 text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/40",
            "group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
          )}
          aria-label="CDI Health — Overview"
        >
          <CdiLogoMark
            className="size-[34px]"
            aria-hidden="true"
            role="presentation"
          />
          <span className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-[17px] font-extrabold">CDI Health</span>
            <span className="text-[13px] text-muted-foreground">
              Circular Drive Initiative
            </span>
          </span>
        </Link>
      </SidebarHeader>

      <SidebarContent className="px-3.5 pt-4 group-data-[collapsible=icon]:px-2">
        <nav aria-label="Main">
          <SidebarMenu className="gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} item={item} />
            ))}
          </SidebarMenu>
        </nav>
      </SidebarContent>

      <SidebarFooter className="px-3.5 pb-5 group-data-[collapsible=icon]:px-2">
        <SidebarMenu>
          <NavLink item={SETTINGS_ITEM} />
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
