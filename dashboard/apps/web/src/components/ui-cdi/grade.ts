/**
 * Grade vocabulary and "why this grade" sentences (pure, no React).
 *
 * - `gradeOf(device)`       → "A" | "B" | "C" | "D" | "F" | "UNGRADED" | null
 * - `gradeOutcome(grade)`   → "Reuse", "Reuse, limited", "Advisory", "Do not reuse", "Couldn't grade"
 * - `gradeQuality(grade)`   → "Excellent", "Good", "Fair", "Advisory", "Failed", "Couldn't grade"
 * - `gradeReason(device)`   → one plain sentence for non-A grades (null for a clean A)
 * - `driveNote(device)`     → informational note for any grade (e.g. readiness check unsupported)
 *
 * Field names follow src/cdi_health/classes/scoring.py (HealthScore.to_dict)
 * and revert.py (warning_flags, ungraded_reasons, fail_reason_codes).
 */
import { isUngradedDevice } from "@/lib/health-badges"
import type { DeviceRecord, ScoreDeduction } from "@/lib/types"

export type GradeLetter = "A" | "B" | "C" | "D" | "F" | "UNGRADED"

export const GRADE_ORDER: GradeLetter[] = ["A", "B", "C", "D", "F", "UNGRADED"]

type GradeInfo = {
  /** Letter shown in the disc ("?" for ungraded). */
  symbol: string
  outcome: string
  quality: string
  /** Legend line, e.g. "Excellent — reuse". */
  legend: string
  /** Longer explanation for help text / tooltips. */
  description: string
}

export const GRADE_INFO: Record<GradeLetter, GradeInfo> = {
  A: {
    symbol: "A",
    outcome: "Reuse",
    quality: "Excellent",
    legend: "Excellent — reuse",
    description: "Excellent. Certified for reuse.",
  },
  B: {
    symbol: "B",
    outcome: "Reuse",
    quality: "Good",
    legend: "Good — reuse",
    description: "Good. Certified for reuse.",
  },
  C: {
    symbol: "C",
    outcome: "Reuse, limited",
    quality: "Fair",
    legend: "Fair — reuse, limited",
    description:
      "Fair. Certified for non-critical use (for example, past rated writes).",
  },
  D: {
    symbol: "D",
    outcome: "Advisory",
    quality: "Advisory",
    legend: "Advisory",
    description: "Limited reuse. Not fully certified.",
  },
  F: {
    symbol: "F",
    outcome: "Do not reuse",
    quality: "Failed",
    legend: "Do not reuse",
    description: "Failed a hard check. Not certified.",
  },
  UNGRADED: {
    symbol: "?",
    outcome: "Couldn't grade",
    quality: "Couldn't grade",
    legend: "Couldn't grade",
    description: "Locked, unreadable, or behind a USB/RAID adapter.",
  },
}

/** Normalises any grade-ish string ("a", "Ungraded", "U", "?") to a GradeLetter. */
export function normalizeGrade(
  value: string | null | undefined
): GradeLetter | null {
  const raw = (value ?? "").trim().toUpperCase()
  if (raw === "A" || raw === "B" || raw === "C" || raw === "D" || raw === "F") {
    return raw
  }
  if (raw === "UNGRADED" || raw === "U" || raw === "?") {
    return "UNGRADED"
  }
  return null
}

/** The drive's grade, honouring grading_status/final_grade for UNGRADED drives. */
export function gradeOf(device: DeviceRecord): GradeLetter | null {
  if (isUngradedDevice(device)) {
    return "UNGRADED"
  }
  return (
    normalizeGrade(device.health_grade) ?? normalizeGrade(device.final_grade)
  )
}

export function gradeOutcome(grade: string | null | undefined): string {
  const letter = normalizeGrade(grade)
  return letter ? GRADE_INFO[letter].outcome : "Not graded yet"
}

export function gradeQuality(grade: string | null | undefined): string {
  const letter = normalizeGrade(grade)
  return letter ? GRADE_INFO[letter].quality : "Not graded yet"
}

/** Counts drives per grade (unknown grades are skipped). */
export function countByGrade(
  devices: DeviceRecord[]
): Record<GradeLetter, number> {
  const counts: Record<GradeLetter, number> = {
    A: 0,
    B: 0,
    C: 0,
    D: 0,
    F: 0,
    UNGRADED: 0,
  }
  for (const device of devices) {
    const grade = gradeOf(device)
    if (grade) {
      counts[grade] += 1
    }
  }
  return counts
}

// ---------------------------------------------------------------------------
// Why this grade
// ---------------------------------------------------------------------------

/** Default §5 age-cap table (config/thresholds.yaml grading.age_cap). */
const AGE_CAP_HOURS: Record<string, Partial<Record<GradeLetter, number>>> = {
  enterprise: { B: 40000, C: 60000 },
  consumer: { B: 20000, D: 60000 },
}

const RANK: Record<string, number> = { A: 0, B: 1, C: 2, D: 3, F: 4 }

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value
  }
  if (typeof value === "string") {
    const parsed = Number(value.replace(/,/g, "").trim())
    return value.trim() && Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function formatCount(value: number): string {
  return Math.round(value).toLocaleString("en-US")
}

function plural(count: number, one: string, many = `${one}s`): string {
  return `${formatCount(count)} ${count === 1 ? one : many}`
}

const UNGRADED_REASON_TEXT: Record<string, string> = {
  SECURITY_LOCKED: "Drive is security-locked — unlock it, then scan again",
  SMART_UNREADABLE: "Couldn't read the drive's health data",
  USB_PASSTHROUGH_FAILURE:
    "Behind a USB adapter that hides health data — connect it directly",
  RAID_PASSTHROUGH_FAILURE:
    "Behind a RAID controller that hides health data — connect it directly",
  DEVICE_OPEN_FAILURE:
    "Couldn't open the drive — check it's seated, then scan again",
  DEVICE_TIMEOUT: "Drive stopped answering during the scan — scan again",
  UNSUPPORTED_PROTOCOL: "This kind of drive can't be graded yet",
}

const FLAG_TEXT: Record<string, string> = {
  TUR_NOT_READY:
    "Readiness check not supported by this firmware — health data is fine",
  TUR_UNAVAILABLE:
    "Readiness check couldn't run on this bench — health data is fine",
  MISSING_DEFECT_DATA: "Drive doesn't report its defect counters",
  ENDURANCE_EXCEEDED: "Past rated writes",
  POH_NOT_REPORTED: "Drive doesn't report its power-on hours",
  SMART_RESET_SUSPECTED:
    "Health counters look reset — treat the history with care",
  DUPLICATE_SERIAL: "Same serial as another drive — check the label",
}

/** Plain words for a failed hard check, keyed by deduction `field`. */
const FAIL_FIELD_TEXT: Record<string, string> = {
  smart_status: "Drive reports its own health check failed",
  state: "Drive didn't respond",
  grown_defects: "Too many grown defects",
  reallocated_sectors: "Too many reallocated sectors",
  pending_sectors: "Too many sectors waiting to be reallocated",
  uncorrectable_errors: "Too many uncorrectable errors",
  uncorrected_errors: "Too many uncorrected read/write errors",
  smart_self_tests: "Failed a recent self-test",
  nvme_self_test: "Failed a recent self-test",
  self_test_history: "Failed recent self-tests",
  critical_warning: "Drive raised a critical warning",
  endurance_group_critical_warning_summary: "Drive raised a critical warning",
  media_errors: "Drive reports media errors",
  current_temperature: "Running too hot",
  highest_temperature: "Has run hotter than its rated maximum",
  critical_comp_time: "Has spent time above its critical temperature",
  ssd_percentage_used_endurance: "Far past rated writes",
  percentage_used: "Far past rated writes",
  available_spare: "Spare space below the drive's own limit",
  available_reserved_space: "Spare space below the drive's own limit",
}

/** Same, keyed by §13 fail reason code (older payloads without deductions). */
const FAIL_CODE_TEXT: Record<string, string> = {
  "F-SMART-FAIL": FAIL_FIELD_TEXT.smart_status,
  "F-NO-RESPONSE": FAIL_FIELD_TEXT.state,
  "F-GROWN-DEFECTS": FAIL_FIELD_TEXT.grown_defects,
  "F-REALLOCATED-SECTORS": FAIL_FIELD_TEXT.reallocated_sectors,
  "F-PENDING-SECTORS": FAIL_FIELD_TEXT.pending_sectors,
  "F-UNCORRECTED-ERRORS": FAIL_FIELD_TEXT.uncorrectable_errors,
  "F-SELF-TEST": FAIL_FIELD_TEXT.smart_self_tests,
  "F-NVME-CRITICAL-WARNING": FAIL_FIELD_TEXT.critical_warning,
  "F-MEDIA-ERRORS": FAIL_FIELD_TEXT.media_errors,
  "F-TEMPERATURE": "Temperature out of range",
  "F-ENDURANCE": FAIL_FIELD_TEXT.percentage_used,
  "F-SPARE-BLOCKS": FAIL_FIELD_TEXT.available_spare,
}

function deductionsOf(device: DeviceRecord): ScoreDeduction[] {
  return device.health_deductions ?? device.deductions ?? []
}

function ageSentence(device: DeviceRecord, cap: GradeLetter): string {
  const hours = toNumber(device.power_on_hours)
  const driveClass = (device.drive_class ?? "").toLowerCase()
  const table = AGE_CAP_HOURS[driveClass]
  // The table lists the hours above which each grade caps; the cap grade's own
  // threshold is what this drive went past.
  const limit = table?.[cap]
  const hoursText =
    hours != null
      ? `Powered on ${formatCount(hours)} hours`
      : "High power-on hours"
  if (limit != null && driveClass) {
    return `${hoursText} — ${driveClass} drives over ${formatCount(limit)} hours can't grade higher than ${cap}`
  }
  return `${hoursText} — too many hours to grade higher than ${cap}`
}

function attributeSentence(
  key: string,
  info: { value?: unknown; [extra: string]: unknown }
): string | null {
  const value = toNumber(info.value)
  switch (key) {
    case "available_spare":
    case "available_reserved_space":
      return value != null
        ? `Spare down to ${formatCount(value)}%`
        : "Spare space is low"
    case "endurance":
      return value != null
        ? `Past rated writes (${formatCount(value)}% used)`
        : FLAG_TEXT.ENDURANCE_EXCEEDED
    case "reallocated_sectors":
      return value != null
        ? `${plural(value, "reallocated sector")}`
        : "Has reallocated sectors"
    case "pending_sectors":
      return value != null
        ? `${plural(value, "sector")} waiting to be reallocated`
        : "Has sectors waiting to be reallocated"
    case "uncorrectable_errors":
    case "uncorrected_errors":
      return value != null
        ? `${plural(value, "uncorrectable error")}`
        : "Has uncorrectable errors"
    case "grown_defects":
      return value != null
        ? `${plural(value, "grown defect")}`
        : "Has grown defects"
    case "self_test_history": {
      const recent = toNumber(info.recent_failures) ?? 0
      const older = toNumber(info.old_failures) ?? 0
      const total = recent + older || value || 0
      if (recent > 0) {
        return `Failed ${plural(recent, "recent self-test")}`
      }
      return total > 0
        ? `Failed ${plural(total, "earlier self-test")}`
        : "Has failed self-tests"
    }
    case "missing_defect_data":
      return FLAG_TEXT.MISSING_DEFECT_DATA
    default:
      return null
  }
}

function ungradedSentence(device: DeviceRecord): string {
  for (const code of device.ungraded_reasons ?? []) {
    const text = UNGRADED_REASON_TEXT[String(code).trim().toUpperCase()]
    if (text) {
      return text
    }
  }
  return "Couldn't read enough health data to grade this drive"
}

function failSentence(device: DeviceRecord): string {
  const critical = deductionsOf(device).find((d) => d.severity === "critical")
  if (critical?.field && FAIL_FIELD_TEXT[critical.field]) {
    return FAIL_FIELD_TEXT[critical.field]
  }
  for (const code of device.fail_reason_codes ?? []) {
    const text = FAIL_CODE_TEXT[String(code).trim().toUpperCase()]
    if (text) {
      return text
    }
  }
  const gate = critical?.reason ?? device.fail_gates?.[0]
  if (gate) {
    const known = FAIL_REASON_PATTERNS.find(([pattern]) => pattern.test(gate))
    if (known) {
      return known[1]
    }
    // Scoring reasons are already short English ("Temperature critical").
    return gate.replace(/\s+-\s+Drive is failing$/i, "")
  }
  return "Failed a hard health check"
}

/** fail_gates are deduction reason strings; map the common ones to plain words. */
const FAIL_REASON_PATTERNS: [RegExp, string][] = [
  [/smart status/i, FAIL_FIELD_TEXT.smart_status],
  [/media error/i, FAIL_FIELD_TEXT.media_errors],
  [/self-test/i, FAIL_FIELD_TEXT.smart_self_tests],
  [/spare|reserved space/i, FAIL_FIELD_TEXT.available_spare],
  [/reallocated/i, FAIL_FIELD_TEXT.reallocated_sectors],
  [/pending/i, FAIL_FIELD_TEXT.pending_sectors],
  [/grown defect/i, FAIL_FIELD_TEXT.grown_defects],
  [/uncorrect/i, FAIL_FIELD_TEXT.uncorrectable_errors],
  [/critical warning/i, FAIL_FIELD_TEXT.critical_warning],
  [/percentage used|endurance/i, FAIL_FIELD_TEXT.percentage_used],
]

/**
 * One plain sentence explaining a non-A grade, built from existing fields.
 * Returns null for an A with nothing to say. Order: couldn't grade → failed
 * check → age cap → worst attribute → multi-factor → first warning flag.
 */
export function gradeReason(device: DeviceRecord): string | null {
  const grade = gradeOf(device)
  if (grade === "UNGRADED") {
    return ungradedSentence(device)
  }
  if (grade === "F") {
    return failSentence(device)
  }
  if (grade == null || grade === "A") {
    return null
  }

  const age = normalizeGrade(device.age_cap_grade)
  if (age && age !== "UNGRADED" && age !== "A" && RANK[age] >= RANK[grade]) {
    return ageSentence(device, age)
  }

  const attributes = Object.entries(device.attribute_grades ?? {})
    .map(([key, info]) => ({
      key,
      info,
      rank: RANK[normalizeGrade(info?.grade) ?? "A"] ?? 0,
    }))
    .filter((entry) => entry.rank > 0)
    .sort((a, b) => b.rank - a.rank)
  const worst = attributes[0]
  if (worst && worst.rank >= RANK[grade]) {
    const text = attributeSentence(
      worst.key,
      worst.info as Record<string, unknown>
    )
    if (text) {
      return text
    }
  }
  if (device.multi_factor_applied) {
    return "Several readings are borderline, which lowers the grade one step"
  }
  if (worst) {
    const text = attributeSentence(
      worst.key,
      worst.info as Record<string, unknown>
    )
    if (text) {
      return text
    }
  }

  const flagged = driveNote(device)
  if (flagged) {
    return flagged
  }
  const deduction = deductionsOf(device).find(
    (d) => d.severity === "warning" && d.reason
  )
  return deduction?.reason ?? null
}

/**
 * Informational note from warning flags, for any grade (e.g. an A whose
 * firmware can't answer the readiness check). Null when there is none.
 */
export function driveNote(device: DeviceRecord): string | null {
  for (const flag of device.warning_flags ?? []) {
    const text = FLAG_TEXT[String(flag).trim().toUpperCase()]
    if (text) {
      return text
    }
  }
  return null
}
