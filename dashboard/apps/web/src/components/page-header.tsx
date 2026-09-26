/**
 * @deprecated Legacy pages only. The app header now shows the page title, so
 * this renders just the description and actions (as PageIntro). New pages use
 * PageIntro from "@/components/ui-cdi" directly.
 */
import type { ReactNode } from "react"

import { PageIntro } from "@/components/ui-cdi/page-layout"

type PageHeaderProps = {
  /** Ignored: the shell header owns page titles. */
  eyebrow?: string
  /** Ignored: the shell header owns page titles. */
  title?: string
  description?: ReactNode
  actions?: ReactNode
  /** Ignored. */
  badge?: string
}

export function PageHeader({ description, actions }: PageHeaderProps) {
  return <PageIntro actions={actions}>{description}</PageIntro>
}
