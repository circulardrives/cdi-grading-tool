/**
 * Shared, pure drive naming and number helpers (no React, no ui-cdi imports,
 * so grade sentences can use them too):
 *
 * - `friendlyModel(device)`   → "KIOXIA CM5" for "KCM5DRUG960G"
 * - `formatCapacity(device)`  → "960 GB", "7.68 TB"
 * - `driveTitle(device)`      → "KIOXIA CM5 960 GB" (skips the size when the model already says it)
 * - `formatPoweredOn(hours)`  → "40,858 h (4 yrs 242 days)", "9,808 h (408 days)", "18 h", "—"
 */
import { getReportCategory } from "@/lib/drive-labels"
import type { DeviceRecord } from "@/lib/types"

// ---------------------------------------------------------------------------
// Numbers
// ---------------------------------------------------------------------------

/** Number from a reported value; null for "Not Reported", "", null. */
export function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value
  }
  if (typeof value === "string") {
    const trimmed = value.replace(/,/g, "").trim()
    const parsed = Number(trimmed)
    return trimmed && Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function formatInt(value: number): string {
  return Math.round(value).toLocaleString("en-US")
}

// ---------------------------------------------------------------------------
// Powered on
// ---------------------------------------------------------------------------

const HOURS_PER_DAY = 24
const DAYS_PER_YEAR = 365

/**
 * Whole years and days in `hours` (365-day years, days rounded down):
 * 40,858 → "4 yrs 242 days", 9,808 → "408 days", 8,760 → "1 yr",
 * 24 → "1 day". Null under one day or when unknown.
 */
export function poweredOnSpan(hours: number | null | undefined): string | null {
  if (hours == null || !Number.isFinite(hours) || hours < HOURS_PER_DAY) {
    return null
  }
  const totalDays = Math.floor(hours / HOURS_PER_DAY)
  const years = Math.floor(totalDays / DAYS_PER_YEAR)
  const days = totalDays - years * DAYS_PER_YEAR
  const parts: string[] = []
  if (years > 0) {
    parts.push(`${formatInt(years)} ${years === 1 ? "yr" : "yrs"}`)
  }
  if (days > 0 || years === 0) {
    parts.push(`${days} ${days === 1 ? "day" : "days"}`)
  }
  return parts.join(" ")
}

/** "40,858 h" — hours alone ("—" when unknown). */
export function formatHours(hours: number | null | undefined): string {
  return hours == null || !Number.isFinite(hours)
    ? "—"
    : `${formatInt(hours)} h`
}

/**
 * Power-on hours with years and days: "40,858 h (4 yrs 242 days)",
 * "9,808 h (408 days)", "18 h"; "—" when unknown.
 */
export function formatPoweredOn(hours: number | null | undefined): string {
  const span = poweredOnSpan(hours)
  return span ? `${formatHours(hours)} (${span})` : formatHours(hours)
}

// ---------------------------------------------------------------------------
// Names
// ---------------------------------------------------------------------------

/** Model-number prefixes → the name printed on the drive's box. */
const MODEL_NAMES: [RegExp, string][] = [
  [/^KCM5/, "KIOXIA CM5"],
  [/^KCM6/, "KIOXIA CM6"],
  [/^KCD8/, "KIOXIA CD8"],
  [/^KCD6/, "KIOXIA CD6"],
  [/^KXG60/, "Toshiba XG6"],
  [/^SSDPF2KX/, "Intel D7-P5520"],
  [/^SSDPF2KE/, "Intel D7-P5620"],
  [/^SSDPE2KX/, "Intel DC P4510"],
  [/^SSDPE2KE/, "Intel DC P4610"],
  [/^SSDPF21Q/, "Intel Optane P5800X"],
  [/^SSDPEK1A/, "Intel Optane P1600X"],
  [/^SSDSC2BA/, "Intel DC S3710"],
  [/^MZQL2/, "Samsung PM9A3"],
  [/^MZQLB/, "Samsung PM983"],
  [/^WDS\d+T?\d*[A-Z]?3XHC/, "WD Red SN700"],
]

const NOT_REPORTED = /^(unknown|not reported|n\/a|none|-+)$/i

/** The value as text, or "" when the drive reports "Not Reported" etc. */
export function reported(value: unknown): string {
  const text = String(value ?? "").trim()
  return NOT_REPORTED.test(text) ? "" : text
}

/** Vendor words some drives put in front of the model number. */
const VENDOR_PREFIX =
  /^(KIOXIA|TOSHIBA|INTEL|SAMSUNG|WDC|WD|SEAGATE|HGST|MICRON|HPE|DELL)\s+/i

/**
 * "KCM5DRUG960G" → "KIOXIA CM5". Falls back to vendor + model as reported,
 * then to the drive type ("SAS HDD") when the drive reports neither.
 */
export function friendlyModel(device: DeviceRecord): string {
  const model = reported(device.model_number)
  const bare = model.replace(VENDOR_PREFIX, "").toUpperCase()
  for (const [pattern, name] of MODEL_NAMES) {
    if (pattern.test(bare)) {
      return name
    }
  }
  const vendor = reported(device.vendor)
  const type = getReportCategory(device)
  if (model) {
    return vendor && !model.toLowerCase().startsWith(vendor.toLowerCase())
      ? `${vendor} ${model}`
      : model
  }
  return vendor ? `${vendor} ${type}` : type
}

/** Model number as reported, or "" when the drive doesn't report one. */
export function modelNumber(device: DeviceRecord): string {
  return reported(device.model_number)
}

export function serialOf(device: DeviceRecord): string {
  return reported(device.serial_number)
}

/** Human capacity in decimal units, as printed on labels: 960 GB, 7.68 TB. */
export function formatCapacity(device: DeviceRecord): string {
  let bytes = toNumber(device.bytes)
  if (!bytes) {
    const gib = toNumber(device.gibibytes)
    bytes = gib ? gib * 1024 ** 3 : null
  }
  if (!bytes || bytes <= 0) {
    return ""
  }
  const tb = bytes / 1e12
  if (tb >= 1) {
    // Two decimals, trailing zeros dropped: 7.68, 3.84, 1.2, 1.
    return `${Number(tb.toFixed(tb >= 10 ? 1 : 2))} TB`
  }
  return `${Math.round(bytes / 1e9)} GB`
}

/** Model names that already carry a size ("870 EVO 500GB", "SDSSDH3 512G"). */
const MODEL_HAS_SIZE = /\d(?:\.\d+)?\s?[GT]B?\b/i

/** True when a model name already says its size ("FADU DELTA U.2 1.92TB"). */
export function nameHasSize(name: string): boolean {
  return MODEL_HAS_SIZE.test(name)
}

/** Capacity to show next to `friendlyModel` — "" when the name says it. */
export function capacityLabel(device: DeviceRecord): string {
  return nameHasSize(friendlyModel(device)) ? "" : formatCapacity(device)
}

/** Friendly name + capacity: "KIOXIA CM5 960 GB", "SAMSUNG SSD 870 EVO 500GB". */
export function driveTitle(device: DeviceRecord): string {
  const name = friendlyModel(device)
  const capacity = capacityLabel(device)
  return capacity ? `${name} ${capacity}` : name
}
