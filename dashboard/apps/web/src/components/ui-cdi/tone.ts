/**
 * Status tones shared by pills, problem lines, and notes.
 * ok = green (A colours), bad = red (F), warn = amber (C), info = grey (ungraded).
 * Class names map to the --tone-* tokens in packages/ui globals.css.
 */
export type Tone = "ok" | "bad" | "warn" | "info"

/** Background + text for a pill or chip in this tone. */
export const TONE_PILL: Record<Tone, string> = {
  ok: "bg-tone-ok-bg text-tone-ok-fg",
  bad: "bg-tone-bad-bg text-tone-bad-fg",
  warn: "bg-tone-warn-bg text-tone-warn-fg",
  info: "bg-tone-info-bg text-tone-info-fg",
}

/** Text colour for a sentence in this tone (AA on card and page backgrounds). */
export const TONE_TEXT: Record<Tone, string> = {
  ok: "text-tone-ok-fg",
  bad: "text-tone-bad-fg",
  warn: "text-tone-warn-fg",
  info: "text-tone-info-fg",
}

/** Icon colour (the stronger "solid" shade). */
export const TONE_ICON: Record<Tone, string> = {
  ok: "text-tone-ok-solid",
  bad: "text-tone-bad-solid",
  warn: "text-tone-warn-solid",
  info: "text-tone-info-solid",
}
