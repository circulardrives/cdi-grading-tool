import type { ReactNode } from "react"

import { Badge } from "@workspace/ui/components/badge"

type PageHeaderProps = {
  eyebrow: string
  title: string
  description: string
  actions?: ReactNode
  badge?: string
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  badge,
}: PageHeaderProps) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-muted-foreground font-mono text-xs uppercase tracking-[0.28em]">
          {eyebrow}
        </p>
        {badge ? <Badge variant="outline">{badge}</Badge> : null}
      </div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-3xl">
          <h1 className="font-heading text-3xl font-semibold tracking-tight">
            {title}
          </h1>
          <p className="text-muted-foreground mt-1 text-sm">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </section>
  )
}
