/**
 * The "Self-test" cell of a drive row: progress while running, the last
 * result in plain words otherwise.
 */
import { CheckIcon, XIcon } from "lucide-react"

import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import { Pill } from "@/components/ui-cdi"
import {
  entryType,
  formatTestedAgo,
  latestResult,
  resultKind,
  resultReason,
  runningPercent,
  runningType,
  type DriveRow,
  type TestType,
} from "@/components/self-tests/self-test-format"
import type { QueuedDrive } from "@/components/self-tests/start-queue"

const TYPE_WORD: Record<TestType, string> = {
  short: "Short test",
  extended: "Extended test",
}

type Props = {
  row: DriveRow
  queued?: QueuedDrive
  startFailure?: string
  startedType?: TestType
  stopping?: boolean
}

export function SelfTestStatus({
  row,
  queued,
  startFailure,
  startedType,
  stopping,
}: Props) {
  const entry = row.status

  if (queued?.phase === "waiting") {
    return <Pill tone="info">Waiting</Pill>
  }
  if (queued?.phase === "starting") {
    return (
      <Pill tone="info">
        <Spinner className="size-3.5" aria-hidden="true" />
        Starting…
      </Pill>
    )
  }

  if (entry?.in_progress) {
    const type = runningType(entry, startedType)
    const percent = runningPercent(entry)
    const label = `${type ? TYPE_WORD[type] : "Self-test"}${percent != null ? ` · ${percent}%` : " · running"}`
    return (
      <div className="flex items-center gap-2.5">
        <div
          role="progressbar"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent ?? undefined}
          className="h-2 w-[140px] shrink-0 overflow-hidden rounded-full bg-border max-lg:w-24"
        >
          <div
            className={cn(
              "h-2 rounded-full bg-primary transition-[width] duration-700",
              percent == null && "w-1/3 animate-pulse"
            )}
            style={percent != null ? { width: `${percent}%` } : undefined}
          />
        </div>
        <span>{stopping ? "Stopping…" : label}</span>
      </div>
    )
  }

  if (startFailure) {
    return (
      <span className="whitespace-normal text-tone-bad-fg">{startFailure}</span>
    )
  }

  if (!entry) {
    return <span className="text-muted-foreground">—</span>
  }
  if (entry.supported === false) {
    return (
      <span className="text-muted-foreground">Doesn't support self-tests</span>
    )
  }

  const latest = latestResult(entry)
  if (!latest) {
    if (entry.error) {
      return (
        <span className="text-tone-warn-fg">Couldn't read the test result</span>
      )
    }
    return <span className="text-muted-foreground">Not run yet</span>
  }

  const kind = resultKind(latest)
  const type = entryType(latest)
  const ago = formatTestedAgo(entry.last_test_date)
  const details = [type, ago].filter(Boolean).join(" · ")

  if (kind === "failed") {
    const reason = resultReason(latest)
    return (
      <div className="leading-[34px] whitespace-normal">
        <span className="mr-2 inline-flex h-[30px] items-center gap-2 rounded-full bg-tone-bad-bg pr-3 pl-1 align-middle text-[15px] leading-none font-bold text-tone-bad-fg">
          <span
            aria-hidden="true"
            className="inline-flex size-6 items-center justify-center rounded-full bg-grade-f-solid text-grade-f-solid-fg"
          >
            <XIcon className="size-4" strokeWidth={3} />
          </span>
          Failed
        </span>
        <span className="font-semibold text-tone-bad-fg">
          {reason ? `— ${reason}` : null}
          {details ? (
            <span className="font-normal text-muted-foreground">
              {reason ? " · " : ""}
              {details}
            </span>
          ) : null}
        </span>
      </div>
    )
  }

  if (kind === "passed") {
    return (
      <span className="inline-flex items-center gap-2">
        <CheckIcon
          aria-hidden="true"
          className="size-5 text-tone-ok-solid"
          strokeWidth={2.5}
        />
        <span>
          <span className="font-semibold text-tone-ok-fg">Passed</span>
          {details ? (
            <span className="text-muted-foreground"> · {details}</span>
          ) : null}
        </span>
      </span>
    )
  }

  if (kind === "aborted") {
    const reason = resultReason(latest)
    return (
      <span className="inline-flex flex-wrap items-center gap-2 whitespace-normal">
        <Pill tone="warn">Aborted</Pill>
        <span className="text-muted-foreground">
          {[reason, details].filter(Boolean).join(" · ")}
        </span>
      </span>
    )
  }

  return <span className="text-muted-foreground">Not run yet</span>
}
