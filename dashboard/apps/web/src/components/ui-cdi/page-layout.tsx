/**
 * Page-level layout helpers. The app shell already renders the page title,
 * scope switcher, last scan, and "Scan all benches" — pages never repeat them.
 *
 * - <PageIntro actions={<Button …/>}>One sentence about this page.</PageIntro>
 *     muted 17px line on the left, page actions on the right (mockup Benches row)
 * - <PageHeadline title="14 drives on 2 benches" subtitle="All 14 certified…" />
 *     the big at-a-glance answer at the top of Overview-style pages
 */
import type { ReactNode } from "react"

import { cn } from "@workspace/ui/lib/utils"

export function PageIntro({
  children,
  actions,
  className,
}: {
  children?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex flex-wrap items-center gap-3", className)}>
      {children ? (
        <p className="max-w-3xl min-w-0 flex-1 text-[17px] text-muted-foreground">
          {children}
        </p>
      ) : (
        <div className="flex-1" />
      )}
      {actions ? (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  )
}

export function PageHeadline({
  title,
  subtitle,
  className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <p className="text-[40px] leading-none font-extrabold tracking-tight max-sm:text-3xl">
        {title}
      </p>
      {subtitle ? (
        <p className="text-lg text-muted-foreground">{subtitle}</p>
      ) : null}
    </div>
  )
}
