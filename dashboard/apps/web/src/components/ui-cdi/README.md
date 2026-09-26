# ui-cdi — shared pieces for the redesigned pages

Import everything from `@/components/ui-cdi`. Mockups: `redesign/project/*.dc.html`
(visual spec: the CSS block in `gen.py`). Tokens live in
`packages/ui/src/styles/globals.css` and work in light and dark mode.

## The shell already does this — pages don't

`components/app-layout.tsx` renders the sidebar, the header (page title,
"All benches (N) ▾" scope switcher on Overview/Drives/Reports, "Last scan … · …",
**Scan all benches**), the Demo mode banner, and the scan progress bar. Pages
render **no** h1, eyebrow, page-level scan button, or scan progress.

- Scope: `const { scopeId, scopedBench, benches } = useBenchScope()` — `scopeId`
  null = all benches. Filter your data by it (fleet rows carry `machine_id`).
- Scan: `useScanAllBenches()` / `useScanAllStatus()` from `hooks/use-cdi-queries`
  if a page needs to know a scan is running (e.g. to show `Scanning…` pills).
- Demo mode: `useMockDataSettings().useMockData`; toggled only in Settings.

## Components

| Export | Use |
| --- | --- |
| `GradeChip({ grade, size?: "sm"\|"md"\|"lg", showWord?: "outcome"\|"quality"\|"both"\|false, label? })` | Letter disc + word. `label` replaces the word (counts: `<GradeChip grade="A" label="11" />`). Accepts `"UNGRADED"`, `"U"`, `"?"`; null → "—". |
| `gradeOf(device)` | `"A"…"F"`, `"UNGRADED"` (via `grading_status`/`final_grade`), or null. |
| `gradeOutcome(g)` / `gradeQuality(g)` / `GRADE_INFO[g]` | "Reuse" / "Good" / `{symbol, outcome, quality, legend, description}`. |
| `gradeReason(device)` | One plain sentence for non-A grades (age cap, spare, writes, defects, self-tests, failed checks, couldn't grade). Null for a clean A. |
| `driveNote(device)` | Note from warning flags for any grade ("Readiness check not supported by this firmware — health data is fine"). |
| `warningFlagText(flag)` / `ungradedReasonText(code)` | Plain words for one warning flag / couldn't-grade code, or null. |

Drive names and hours live in `lib/drive-names.ts` (pure, shared): `friendlyModel`,
`formatCapacity`, `driveTitle` ("KIOXIA CM5 960 GB"), `formatPoweredOn(hours)`
("40,858 h (4 yrs 242 days)"; `poweredOnSpan` for the years/days part alone).
Link to a drive's full-screen page with `driveDetailsHref(row)` from
`pages/drive-details/drive-details-href.ts` (`/drives/:benchKey/:serial?dev=<slot>`).
| `countByGrade(devices)` | `{A, B, C, D, F, UNGRADED}` counts. |
| `benchName(machine)` / `benchAddress(machine)` | Bench's own hostname (`remote_hostname`), else name, else address / "10.100.10.57". |
| `useBenchNames()` | `(machineId, fallback) => name` for drive rows and fleet hosts; `machineId` null = this bench (its `/health` hostname). |
| `BenchLabel({ machine })` | Bold name with the IP small underneath. |
| `BenchStatusPill({ status, scanning? })` | Online / Scanning… / Can't reach / Needs access token / Unknown. |
| `BenchProblemLine({ name, status, error?, noDrives? })` | One actionable line, or nothing. `benchProblem()` is the pure version. |
| `useLastScan()` | `{ at, label }` ("both benches"), scope-aware. |
| `PageIntro({ children, actions })` | Muted 17px sentence left, page actions right (first row of a page). |
| `PageHeadline({ title, subtitle })` | Big 40px answer ("14 drives on 2 benches"). |
| `PageSection({ title, description?, actions?, flush?, emphasis? })` | Titled card. `flush` for edge-to-edge tables. |
| `Card({ padded? })` | Bare surface (white, 1px border, 14px radius). Alias it if you also import shadcn `Card`. |
| `EmptyState({ icon, title, description?, actions? })` | Dashed empty box. |
| `StatTile({ label, value, hint?, variant?: "tile"\|"card" })` | "Powered on / 40,856 h". |
| `Pill({ tone, dot? })`, `Note({ tone, icon? })`, `SectionLabel` | Status pill, icon + sentence, 13px uppercase label. Tones: `ok` `bad` `warn` `info`. |

## Vocabulary (user-facing copy)

Say **bench, drive, scan, self-test, report, access token, writes used, spare,
powered on**. Never: host, machine, API, local API, registry, fleet, endpoint,
env var, file path, `machine_id`, mock (say "Demo mode" / "sample drives").
Grades are always letter + word: A Reuse, B Reuse, C Reuse limited,
D Advisory, F Do not reuse, ? Couldn't grade. Problems say what to do next.

## Layout conventions

- Page body: the shell pads 28px × 32px (16px on phones) and stacks children
  with a 24px gap. Return a fragment or `flex flex-col gap-6`; don't add outer padding.
- Sections: `PageSection` / `Card`, 24px inner padding, h2 20px bold, muted 15px description.
- Grids: `grid gap-6 lg:grid-cols-3` (span 2 + 1 as in Overview); collapse to one column below `lg`.
- Text ≥16px for content; 15px muted secondary; 13px uppercase only for labels/table heads.
- Touch: buttons are 44px (`Button` default). `size="sm"` (36px) only inside dense rows;
  `variant="quiet"` for row actions (Scan, Edit); `variant="outline"` for secondary.
- Tables: shadcn `Table` is already styled (13px uppercase heads, 56px rows, 16px text).
  Put it in `PageSection flush` or `Card className="overflow-hidden"`. Selected row:
  `data-state="selected"`. Serials/addresses: `font-mono text-[15px]`. Numbers right-aligned.
- Colour: only tokens (`bg-card`, `text-muted-foreground`, `bg-tone-bad-bg`, `text-link`, `bg-row-selected`,
  `bg-grade-b-bg`…). Never colour alone — always a word or letter too.

## What each page agent replaces

once nothing imports it).

