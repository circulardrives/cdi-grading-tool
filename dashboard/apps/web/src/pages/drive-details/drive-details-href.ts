/**
 * Links to the drive details page:
 *   /drives/:benchKey/:serial?dev=<slot>&tab=<tab>
 * benchKey is the bench's machine id, or "local" for the bench this dashboard
 * runs on (same values as the Drives list's ?bench= filter). `dev` picks the
 * right drive when two on one bench report the same serial. Drives that
 * report no serial use "-".
 */
import { benchFilterId, THIS_BENCH_ID } from "@/pages/drives/use-drive-rows"

export const NO_SERIAL = "-"

export type DriveTab =
  | "summary"
  | "health"
  | "smart"
  | "scsi"
  | "ocp"
  | "self-tests"
  | "errors"
  | "raw"

export function driveDetailsHref(
  drive: { benchId: string | null; serial: string; slot: string },
  tab?: DriveTab
): string {
  const path = `/drives/${encodeURIComponent(benchFilterId(drive.benchId))}/${encodeURIComponent(drive.serial || NO_SERIAL)}`
  const params = new URLSearchParams()
  if (drive.slot) {
    params.set("dev", drive.slot)
  }
  if (tab && tab !== "summary") {
    params.set("tab", tab)
  }
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

/** Route param → registered bench id, or null for this bench. */
export function benchIdFromKey(benchKey: string): string | null {
  return benchKey === THIS_BENCH_ID ? null : benchKey
}

/** Router state the Drives list passes so "← Drives" restores its filters. */
export type DriveDetailsState = { fromDrives?: string }
