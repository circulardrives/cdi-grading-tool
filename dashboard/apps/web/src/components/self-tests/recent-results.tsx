/**
 * Recent results: one compact line per drive (last few self-tests it
 * recorded), with the drive's own test log behind "Show test log".
 */
import { useState } from "react"
import { ChevronDownIcon, ChevronUpIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { cn } from "@workspace/ui/lib/utils"

import { PageSection } from "@/components/ui-cdi"
import {
  entryType,
  resultKind,
  resultReason,
  type DriveRow,
  type ResultKind,
} from "@/components/self-tests/self-test-format"
import type { SelfTestResultEntry } from "@/lib/types"

const KIND_WORD: Record<ResultKind, string> = {
  passed: "Passed",
  failed: "Failed",
  aborted: "Aborted",
}

const KIND_CLASS: Record<ResultKind, string> = {
  passed: "text-tone-ok-fg",
  failed: "font-bold text-tone-bad-fg",
  aborted: "text-tone-warn-fg",
}

function entriesOf(row: DriveRow): SelfTestResultEntry[] {
  const status = row.status
  if (!status) {
    return []
  }
  if ((status.recent_results?.length ?? 0) > 0) {
    return status.recent_results ?? []
  }
  return status.latest_result ? [status.latest_result] : []
}

function summarize(entries: SelfTestResultEntry[]): string {
  const counts: Record<ResultKind, number> = {
    passed: 0,
    failed: 0,
    aborted: 0,
  }
  for (const entry of entries) {
    const kind = resultKind(entry)
    if (kind) {
      counts[kind] += 1
    }
  }
  const parts = (Object.keys(counts) as ResultKind[])
    .filter((kind) => counts[kind] > 0)
    .map((kind) => `${counts[kind]} ${KIND_WORD[kind].toLowerCase()}`)
  if (entries.length === 1) {
    const kind = resultKind(entries[0])
    return kind
      ? `Last test ${KIND_WORD[kind].toLowerCase()}`
      : "Last test: no result"
  }
  return `Last ${entries.length} tests: ${parts.join(", ") || "no result"}`
}

function TestLog({
  entries,
  id,
}: {
  entries: SelfTestResultEntry[]
  id: string
}) {
  return (
    <div id={id} className="overflow-x-auto rounded-[10px] bg-muted px-4 py-3">
      <table className="w-full text-[15px]">
        <thead>
          <tr className="text-left text-[13px] font-bold tracking-[0.04em] text-muted-foreground uppercase">
            <th className="py-1.5 pr-4">Test</th>
            <th className="py-1.5 pr-4">Result</th>
            <th className="py-1.5 pr-4">Drive says</th>
            <th className="py-1.5 text-right">At powered-on hour</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, index) => {
            const kind = resultKind(entry)
            const type = entryType(entry)
            const reason = resultReason(entry)
            return (
              <tr key={index} className="border-t border-border align-top">
                <td className="py-2 pr-4 whitespace-nowrap">
                  {type === "extended"
                    ? "Extended"
                    : type === "short"
                      ? "Short"
                      : "Other"}
                </td>
                <td className="py-2 pr-4">
                  {kind ? (
                    <span className={KIND_CLASS[kind]}>{KIND_WORD[kind]}</span>
                  ) : (
                    "—"
                  )}
                  {reason && kind !== "passed" ? (
                    <span className="text-muted-foreground"> — {reason}</span>
                  ) : null}
                </td>
                <td className="py-2 pr-4 font-mono text-sm">
                  {entry.result ?? "—"}
                  {entry.result_code != null
                    ? ` (code ${entry.result_code})`
                    : ""}
                </td>
                <td className="py-2 text-right tabular-nums">
                  {entry.completion_time
                    ? `${entry.completion_time.toLocaleString()} h`
                    : "—"}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function RecentResults({ rows }: { rows: DriveRow[] }) {
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set())
  const withResults = rows
    .map((row) => ({ row, entries: entriesOf(row) }))
    .filter((item) => item.entries.length > 0)

  if (withResults.length === 0) {
    return null
  }

  const toggle = (device: string) => {
    const next = new Set(open)
    if (next.has(device)) {
      next.delete(device)
    } else {
      next.add(device)
    }
    setOpen(next)
  }

  return (
    <PageSection
      id="recent-self-test-results"
      title="Recent results"
      description="the last few self-tests each drive recorded"
      bodyClassName="gap-0 pt-2"
    >
      <ul className="flex flex-col">
        {withResults.map(({ row, entries }) => {
          const isOpen = open.has(row.device)
          const logId = `self-test-log-${row.slot}`
          const failedAny = entries.some(
            (entry) => resultKind(entry) === "failed"
          )
          return (
            <li
              key={row.device}
              className="flex flex-col gap-2 border-b py-2 last:border-b-0"
            >
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="min-w-44 font-mono text-[15px]">
                  {row.serial || row.slot}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="font-semibold">{row.title}</span>{" "}
                  <span
                    className={cn(
                      failedAny ? "text-tone-bad-fg" : "text-muted-foreground"
                    )}
                  >
                    · {summarize(entries)}
                  </span>
                </span>
                <Button
                  variant="quiet"
                  aria-expanded={isOpen}
                  aria-controls={logId}
                  onClick={() => toggle(row.device)}
                >
                  {isOpen ? "Hide test log" : "Show test log"}
                  {isOpen ? (
                    <ChevronUpIcon data-icon="inline-end" aria-hidden="true" />
                  ) : (
                    <ChevronDownIcon
                      data-icon="inline-end"
                      aria-hidden="true"
                    />
                  )}
                </Button>
              </div>
              {isOpen ? <TestLog entries={entries} id={logId} /> : null}
            </li>
          )
        })}
      </ul>
    </PageSection>
  )
}
