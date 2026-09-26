/**
 * Drives (/drives): one list of every drive from the latest scans, with a
 * search box (barcode scanners type the serial + Enter), grade/type/bench
 * filters, and a detail panel. Filters live in the URL so Overview can link
 * here: ?grade=B&type=nvme-ssd&bench=<id>&serial=<sn> (serial opens the panel).
 */
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type KeyboardEvent,
} from "react"
import { useSearchParams } from "react-router-dom"
import { HardDriveIcon, RefreshCwIcon, SearchIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@workspace/ui/components/select"
import { Sheet, SheetContent, SheetTitle } from "@workspace/ui/components/sheet"
import { Skeleton } from "@workspace/ui/components/skeleton"
import { cn } from "@workspace/ui/lib/utils"

import {
  BenchProblemLine,
  Card,
  EmptyState,
  GRADE_ORDER,
  GradeChip,
  Note,
  Pill,
  normalizeGrade,
  useBenchNames,
  useBenchScope,
  type GradeLetter,
} from "@/components/ui-cdi"
import { useScanAllStatus } from "@/hooks/use-cdi-queries"
import type { DriveClass } from "@/lib/types"

import { DrivePanel } from "@/pages/drives/drive-panel"
import {
  DRIVE_TYPES,
  driveTypeFromSlug,
  driveTypeSlug,
  gradeRank,
  naturalCompare,
} from "@/pages/drives/drive-format"
import {
  DriveTable,
  type SortKey,
  type SortState,
} from "@/pages/drives/drive-table"
import {
  benchFilterId,
  useDriveRows,
  type DriveRow,
} from "@/pages/drives/use-drive-rows"

const PAGE_SIZE = 200
const ALL = "all"
/** Side panel next to the list from this width; a sheet below it. */
const WIDE_QUERY = "(min-width: 1280px)"

function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query)
      mql.addEventListener("change", onChange)
      return () => mql.removeEventListener("change", onChange)
    },
    () => window.matchMedia(query).matches,
    () => false
  )
}

function gradeParam(value: string | null): GradeLetter | null {
  if (!value) {
    return null
  }
  return value.toLowerCase() === "ungraded" ? "UNGRADED" : normalizeGrade(value)
}

function defaultOrder(a: DriveRow, b: DriveRow): number {
  return (
    naturalCompare(a.benchName, b.benchName) ||
    naturalCompare(a.slot, b.slot) ||
    naturalCompare(a.serial, b.serial)
  )
}

/** Nulls ("not reported") always sort last. */
function compareNumbers(
  a: number | null,
  b: number | null,
  dir: "asc" | "desc"
): number {
  if (a == null || b == null) {
    return a == null ? (b == null ? 0 : 1) : -1
  }
  return dir === "asc" ? a - b : b - a
}

function sortRows(rows: DriveRow[], sort: SortState): DriveRow[] {
  const sorted = rows.slice().sort(defaultOrder)
  if (!sort) {
    return sorted
  }
  return sorted.sort((a, b) => {
    switch (sort.key) {
      case "grade": {
        const diff = gradeRank(a.grade) - gradeRank(b.grade)
        // "desc" = worst first.
        return sort.dir === "asc" ? diff : -diff
      }
      case "hours":
        return compareNumbers(a.hours, b.hours, sort.dir)
      case "writes":
        return compareNumbers(a.writes, b.writes, sort.dir)
    }
  })
}

function matchesSearch(row: DriveRow, query: string): boolean {
  return query.split(/\s+/).every((word) => row.haystack.includes(word))
}

const TRIGGER_CLASS =
  "h-11 gap-2 rounded-[10px] border-input bg-card px-4 text-base font-semibold hover:bg-muted data-[size=default]:h-11"

// ---------------------------------------------------------------------------

export function DrivesPage() {
  const [params, setParams] = useSearchParams()
  const { scopeId } = useBenchScope()
  const nameOf = useBenchNames()
  const scan = useScanAllStatus()
  const { rows, hosts, isLoading, error, refetch } = useDriveRows()

  const [query, setQuery] = useState("")
  const [sort, setSort] = useState<SortState>(null)
  const [limit, setLimit] = useState(PAGE_SIZE)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [scanMiss, setScanMiss] = useState<string | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const searchId = useId()
  const titleId = useId()
  const wide = useMediaQuery(WIDE_QUERY)

  const grade = gradeParam(params.get("grade"))
  const type = driveTypeFromSlug(params.get("type"))
  const benchParam = scopeId ? null : params.get("bench")
  const serialParam = params.get("serial")?.trim() || null

  useEffect(() => {
    searchRef.current?.focus()
  }, [])

  const setParam = useCallback(
    (name: string, value: string | null) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          if (value) {
            next.set(name, value)
          } else {
            next.delete(name)
          }
          return next
        },
        { replace: true }
      )
    },
    [setParams]
  )

  // Bench filter (header scope already applied in useDriveRows).
  const benchRows = useMemo(
    () =>
      benchParam
        ? rows.filter((row) => benchFilterId(row.benchId) === benchParam)
        : rows,
    [rows, benchParam]
  )

  const benchOptions = useMemo(() => {
    const seen = new Map<string, string>()
    for (const row of rows) {
      seen.set(benchFilterId(row.benchId), row.benchName)
    }
    return [...seen.entries()].sort((a, b) => naturalCompare(a[1], b[1]))
  }, [rows])

  const normalizedQuery = query.trim().toLowerCase()
  const visible = useMemo(() => {
    const filtered = benchRows.filter(
      (row) =>
        (!grade || row.grade === grade) &&
        (!type || row.type === type) &&
        (!normalizedQuery || matchesSearch(row, normalizedQuery))
    )
    return sortRows(filtered, sort)
  }, [benchRows, grade, type, normalizedQuery, sort])

  const typeCounts = useMemo(() => {
    const counts = new Map<DriveClass, number>()
    for (const row of visible) {
      counts.set(row.type, (counts.get(row.type) ?? 0) + 1)
    }
    return [...DRIVE_TYPES, "Other" as DriveClass]
      .map((t) => [t, counts.get(t) ?? 0] as const)
      .filter(([, count]) => count > 0)
  }, [visible])

  // Selection: a row key, pinned to ?serial= so links and reloads reopen it.
  const selected = useMemo(() => {
    if (serialParam) {
      const wanted = serialParam.toLowerCase()
      return (
        benchRows.find(
          (row) =>
            row.key === selectedKey && row.serial.toLowerCase() === wanted
        ) ??
        benchRows.find((row) => row.serial.toLowerCase() === wanted) ??
        null
      )
    }
    return (
      benchRows.find((row) => row.key === selectedKey && !row.serial) ?? null
    )
  }, [benchRows, selectedKey, serialParam])

  const selectRow = useCallback(
    (row: DriveRow) => {
      setSelectedKey(row.key)
      setScanMiss(null)
      setParam("serial", row.serial || null)
    },
    [setParam]
  )

  const closePanel = useCallback(() => {
    setSelectedKey(null)
    setParam("serial", null)
  }, [setParam])

  // Bring the open drive into view (deep links, barcode scans).
  const selectedKeyShown = selected?.key ?? null
  useEffect(() => {
    if (!selectedKeyShown) {
      return
    }
    const rowEl = [
      ...document.querySelectorAll<HTMLElement>("[data-row-key]"),
    ].find((el) => el.dataset.rowKey === selectedKeyShown)
    rowEl?.scrollIntoView({ block: "nearest" })
  }, [selectedKeyShown])

  const onSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter" || !normalizedQuery) {
      return
    }
    event.preventDefault()
    const exact = benchRows.filter(
      (row) => row.serial.toLowerCase() === normalizedQuery
    )
    const match =
      exact.length === 1 ? exact[0] : visible.length === 1 ? visible[0] : null
    if (match) {
      selectRow(match)
      // The next scan replaces this one.
      event.currentTarget.select()
    } else if (visible.length === 0) {
      setScanMiss(query.trim())
    }
  }

  const onSort = (key: SortKey) => {
    setSort((current) => {
      if (current?.key !== key) {
        return { key, dir: "desc" }
      }
      return current.dir === "desc" ? { key, dir: "asc" } : null
    })
  }

  const filtersOn = Boolean(grade || type || benchParam || normalizedQuery)
  const clearFilters = () => {
    setQuery("")
    setScanMiss(null)
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const name of ["grade", "type", "bench"]) {
          next.delete(name)
        }
        return next
      },
      { replace: true }
    )
    searchRef.current?.focus()
  }

  const shown = visible.slice(0, limit)
  const problemHosts = hosts.filter((host) => host.error)
  const serialNotFound =
    serialParam && !isLoading && !error && rows.length > 0 && !selected

  // -------------------------------------------------------------------------

  const toolbar = (
    <div className="flex flex-wrap items-center gap-3">
      <label
        htmlFor={searchId}
        className="flex h-12 min-w-64 flex-[1_1_16rem] items-center gap-2.5 rounded-[10px] border border-input bg-card px-3.5 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/40"
      >
        <SearchIcon
          aria-hidden="true"
          className="size-5 shrink-0 text-muted-foreground"
        />
        <span className="sr-only">Search drives</span>
        <input
          id={searchId}
          ref={searchRef}
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setScanMiss(null)
            setLimit(PAGE_SIZE)
          }}
          onKeyDown={onSearchKeyDown}
          placeholder="Search serial or model — or scan a barcode"
          autoComplete="off"
          spellCheck={false}
          className="h-full min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
        />
      </label>

      <Select
        value={grade ?? ALL}
        onValueChange={(value) =>
          setParam("grade", value === ALL ? null : value)
        }
      >
        <SelectTrigger aria-label="Grade" className={TRIGGER_CLASS}>
          <span className="text-muted-foreground">Grade:</span>
          <SelectValue />
        </SelectTrigger>
        <SelectContent position="popper" align="start">
          <SelectItem value={ALL} className="min-h-11 text-base">
            All
          </SelectItem>
          {GRADE_ORDER.map((letter) => (
            <SelectItem
              key={letter}
              value={letter}
              className="min-h-11 text-base"
            >
              <GradeChip grade={letter} size="sm" />
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={type ? driveTypeSlug(type) : ALL}
        onValueChange={(value) =>
          setParam("type", value === ALL ? null : value)
        }
      >
        <SelectTrigger aria-label="Drive type" className={TRIGGER_CLASS}>
          <span className="text-muted-foreground">Type:</span>
          <SelectValue />
        </SelectTrigger>
        <SelectContent position="popper" align="start">
          <SelectItem value={ALL} className="min-h-11 text-base">
            All
          </SelectItem>
          {DRIVE_TYPES.map((t) => (
            <SelectItem
              key={t}
              value={driveTypeSlug(t)}
              className="min-h-11 text-base"
            >
              {t}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {!scopeId && (benchOptions.length > 1 || benchParam) ? (
        <Select
          value={benchParam ?? ALL}
          onValueChange={(value) =>
            setParam("bench", value === ALL ? null : value)
          }
        >
          <SelectTrigger aria-label="Bench" className={TRIGGER_CLASS}>
            <span className="text-muted-foreground">Bench:</span>
            <SelectValue />
          </SelectTrigger>
          <SelectContent position="popper" align="start">
            <SelectItem value={ALL} className="min-h-11 text-base">
              All
            </SelectItem>
            {benchOptions.map(([id, name]) => (
              <SelectItem key={id} value={id} className="min-h-11 text-base">
                {name}
              </SelectItem>
            ))}
            {benchParam && !benchOptions.some(([id]) => id === benchParam) ? (
              <SelectItem value={benchParam} className="min-h-11 text-base">
                {nameOf(benchParam === "local" ? null : benchParam)}
              </SelectItem>
            ) : null}
          </SelectContent>
        </Select>
      ) : null}
    </div>
  )

  const summary =
    rows.length > 0 ? (
      <div
        className="flex flex-wrap items-center gap-2"
        aria-live="polite"
        aria-atomic="true"
      >
        <span className="text-[15px] text-muted-foreground">
          {filtersOn
            ? `${visible.length} of ${rows.length} drives`
            : `${visible.length} drive${visible.length === 1 ? "" : "s"}`}
        </span>
        {typeCounts.map(([t, count]) => (
          <span key={t} className="contents">
            <span aria-hidden="true" className="text-muted-foreground">
              ·
            </span>
            <Pill tone="info">
              {t} {count}
            </Pill>
          </span>
        ))}
        {filtersOn ? (
          <Button variant="quiet" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
      </div>
    ) : null

  let body
  if (isLoading) {
    body = (
      <Card className="flex flex-col gap-3 p-6" aria-busy="true">
        <span className="sr-only">Loading drives…</span>
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-10 w-full" />
        ))}
      </Card>
    )
  } else if (error && rows.length === 0) {
    body = (
      <Card padded className="flex flex-col items-start gap-3">
        <Note tone="bad">
          Couldn't load drives — check this bench is running, then try again.
        </Note>
        <Button variant="outline" onClick={refetch}>
          <RefreshCwIcon data-icon="inline-start" />
          Try again
        </Button>
      </Card>
    )
  } else if (rows.length === 0) {
    body = (
      <EmptyState
        icon={<HardDriveIcon />}
        title={scan.pending ? "Scanning…" : "No drives yet"}
        description={
          scan.pending
            ? "Drives show up here when the scan finishes."
            : "Press Scan all benches at the top right to grade the drives plugged into your benches."
        }
      />
    )
  } else if (visible.length === 0) {
    body = (
      <EmptyState
        icon={<SearchIcon />}
        title="No drives match"
        description={
          normalizedQuery
            ? `Nothing matches “${query.trim()}”${grade || type || benchParam ? " with these filters" : ""}. Check the serial, or clear the filters.`
            : "No drives match these filters."
        }
        actions={
          <Button variant="outline" onClick={clearFilters}>
            Clear filters
          </Button>
        }
      />
    )
  } else {
    body = (
      <Card className="overflow-hidden">
        <DriveTable
          rows={shown}
          selectedKey={selected?.key ?? null}
          onSelect={selectRow}
          sort={sort}
          onSort={onSort}
          compact={wide && Boolean(selected)}
        />
        {visible.length > shown.length ? (
          <div className="flex items-center justify-center gap-3 border-t px-6 py-3">
            <span className="text-[15px] text-muted-foreground">
              Showing {shown.length} of {visible.length}
            </span>
            <Button
              variant="outline"
              onClick={() => setLimit((value) => value + PAGE_SIZE)}
            >
              Show more
            </Button>
          </div>
        ) : null}
      </Card>
    )
  }

  const panel = selected ? (
    <DrivePanel
      key={selected.key}
      row={selected}
      onClose={closePanel}
      titleId={titleId}
      className="h-full"
    />
  ) : null

  return (
    <div className="flex min-w-0 gap-6">
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        {toolbar}
        {scanMiss ? (
          <Note tone="warn">
            No drive with serial “{scanMiss}” in the latest scans — check the
            label, or scan the bench it's plugged into.
          </Note>
        ) : null}
        {serialNotFound ? (
          <Note tone="warn">
            No drive with serial “{serialParam}” in the latest scans
            {benchParam || scopeId ? " of this bench" : ""}.{" "}
            <button
              type="button"
              className="font-semibold text-link underline underline-offset-4"
              onClick={closePanel}
            >
              Dismiss
            </button>
          </Note>
        ) : null}
        {problemHosts.map((host) => (
          <BenchProblemLine
            key={host.machine_id ?? "local"}
            name={nameOf(host.machine_id, host.name)}
            status={host.status}
            error={host.error}
          />
        ))}
        {summary}
        {body}
      </div>

      {wide ? (
        panel ? (
          <aside
            aria-labelledby={titleId}
            className={cn(
              "sticky top-[5.5rem] flex max-h-[calc(100svh-7rem)] w-[420px] shrink-0 flex-col self-start overflow-hidden rounded-[14px] border bg-card shadow-[0_12px_32px_rgba(22,33,29,0.10)]"
            )}
          >
            {panel}
          </aside>
        ) : null
      ) : (
        <Sheet
          open={Boolean(selected)}
          onOpenChange={(open) => {
            if (!open) {
              closePanel()
            }
          }}
        >
          <SheetContent
            side="right"
            showCloseButton={false}
            aria-describedby={undefined}
            className="gap-0 bg-card p-0 text-base data-[side=right]:w-full data-[side=right]:sm:max-w-[440px]"
          >
            <SheetTitle className="sr-only">Drive details</SheetTitle>
            {panel}
          </SheetContent>
        </Sheet>
      )}
    </div>
  )
}
