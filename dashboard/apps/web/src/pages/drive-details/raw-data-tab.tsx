/**
 * Raw data tab: the whole device record (or just the smartctl output) as
 * pretty-printed JSON, with a line filter, Copy, and Download .json.
 */
import { useId, useMemo, useState, type ReactNode } from "react"
import { CopyIcon, DownloadIcon, SearchIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { cn } from "@workspace/ui/lib/utils"

import type { DeviceRecord } from "@/lib/types"

import { copyText } from "./copy-text"
import { asRecord } from "./details-format"
import { TableCard } from "./field-table"

type Source = "record" | "smartctl"

function highlight(line: string, query: string): ReactNode {
  if (!query) {
    return line
  }
  const lower = line.toLowerCase()
  const parts: ReactNode[] = []
  let start = 0
  let index = lower.indexOf(query)
  while (index !== -1) {
    parts.push(line.slice(start, index))
    parts.push(
      <mark
        key={index}
        className="rounded-sm bg-tone-warn-bg px-0.5 text-tone-warn-fg"
      >
        {line.slice(index, index + query.length)}
      </mark>
    )
    start = index + query.length
    index = lower.indexOf(query, start)
  }
  parts.push(line.slice(start))
  return parts
}

export function RawDataTab({
  device,
  fileName,
}: {
  device: DeviceRecord
  /** Download name without extension: "<serial>-<bench>-<date>". */
  fileName: string
}) {
  const smartctl = asRecord(device.smartctl_json)
  const [source, setSource] = useState<Source>("record")
  const [query, setQuery] = useState("")
  const filterId = useId()

  const json = useMemo(
    () =>
      JSON.stringify(
        source === "smartctl" && smartctl ? smartctl : device,
        null,
        2
      ),
    [device, smartctl, source]
  )
  const lines = useMemo(() => json.split("\n"), [json])
  const needle = query.trim().toLowerCase()
  const shown = useMemo(
    () =>
      lines
        .map((text, index) => ({ text, number: index + 1 }))
        .filter((line) => !needle || line.text.toLowerCase().includes(needle)),
    [lines, needle]
  )
  const gutter = String(lines.length).length

  const download = () => {
    const blob = new Blob([json], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `${fileName}${source === "smartctl" ? "-smartctl" : ""}.json`
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  const sourceButton = (value: Source, label: string) => (
    <button
      type="button"
      aria-pressed={source === value}
      onClick={() => setSource(value)}
      className={cn(
        "inline-flex h-11 items-center rounded-full px-4 text-base font-semibold text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/40",
        source === value && "bg-card text-foreground shadow-sm"
      )}
    >
      {label}
    </button>
  )

  return (
    <TableCard
      title="Raw data"
      description={`Everything the scan saved for this drive, as JSON · ${lines.length.toLocaleString("en-US")} lines.`}
      actions={
        <>
          <Button
            variant="outline"
            onClick={() =>
              void copyText(
                json,
                source === "smartctl" ? "smartctl output" : "device record"
              )
            }
          >
            <CopyIcon data-icon="inline-start" />
            Copy
          </Button>
          <Button variant="outline" onClick={download}>
            <DownloadIcon data-icon="inline-start" />
            Download .json
          </Button>
        </>
      }
    >
      <div className="flex flex-wrap items-center gap-3 border-b px-6 py-3 max-sm:px-4">
        {smartctl ? (
          <div
            role="group"
            aria-label="Show"
            className="inline-flex rounded-full bg-muted p-1"
          >
            {sourceButton("record", "Device record")}
            {sourceButton("smartctl", "smartctl output")}
          </div>
        ) : null}
        <label
          htmlFor={filterId}
          className="flex h-11 min-w-56 flex-[1_1_16rem] items-center gap-2.5 rounded-[10px] border border-input bg-card px-3.5 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/40"
        >
          <SearchIcon
            aria-hidden="true"
            className="size-5 shrink-0 text-muted-foreground"
          />
          <span className="sr-only">Filter lines</span>
          <input
            id={filterId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter lines — e.g. temperature, spare, 197"
            autoComplete="off"
            spellCheck={false}
            className="h-full min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
          />
        </label>
        {needle ? (
          <span
            className="text-[15px] text-muted-foreground"
            aria-live="polite"
          >
            {shown.length.toLocaleString("en-US")} matching line
            {shown.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <div
        role="region"
        aria-label="JSON"
        tabIndex={0}
        className="max-h-[70vh] overflow-auto bg-muted/40 py-3 font-mono text-[15px] leading-6 outline-none focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:ring-inset"
      >
        {shown.length === 0 ? (
          <p className="px-6 font-sans text-base text-muted-foreground">
            No lines contain “{query.trim()}”.
          </p>
        ) : (
          <pre className="min-w-fit px-6 max-sm:px-4">
            {shown.map((line) => (
              <div key={line.number} className="flex whitespace-pre">
                <span
                  aria-hidden="true"
                  className="mr-4 shrink-0 text-right text-muted-foreground select-none"
                  style={{ width: `${gutter}ch` }}
                >
                  {line.number}
                </span>
                <span>{highlight(line.text, needle)}</span>
              </div>
            ))}
          </pre>
        )}
      </div>
    </TableCard>
  )
}
