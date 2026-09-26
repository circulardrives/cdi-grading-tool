/**
 * Segmented control of benches for the Self-tests page (mockup: pecan09 | pecan10).
 * Real toggle buttons (aria-pressed), 44px tall, keyboard reachable.
 */
import { cn } from "@workspace/ui/lib/utils"

export type BenchOption = {
  /** "local" for this bench, else the bench id. */
  value: string
  machineId: string | null
  name: string
  /** Last known connection status (Machine.status); "" for this bench. */
  status: string
}

export function BenchPicker({
  options,
  value,
  onChange,
}: {
  options: BenchOption[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div
      role="group"
      aria-label="Bench"
      className="flex max-w-full flex-wrap gap-1 rounded-[10px] border border-input bg-card p-1"
    >
      {options.map((option) => {
        const pressed = option.value === value
        const offline =
          option.status === "unreachable" || option.status === "auth_failed"
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={pressed}
            onClick={() => onChange(option.value)}
            className={cn(
              "inline-flex h-11 min-w-11 items-center gap-2 rounded-lg px-4 text-base font-semibold transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/40",
              pressed
                ? "bg-accent text-accent-foreground"
                : "text-foreground hover:bg-muted"
            )}
          >
            {option.name}
            {offline ? (
              <span className="text-sm font-medium text-tone-bad-fg">
                · {option.status === "auth_failed" ? "needs token" : "offline"}
              </span>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}
