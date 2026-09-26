/**
 * Access token inputs for the Benches page. Tokens are write-only: they live
 * in the parent's state until saved, then the parent clears them.
 *
 * - <TokenInput>        password field + "On the bench: sudo cat …" hint
 * - <CheckboxRow>       44px checkbox with a real label ("This bench uses an access token")
 */
import { useId, type ReactNode } from "react"

import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { cn } from "@workspace/ui/lib/utils"

import { BENCH_INPUT_CLASS } from "@/components/benches/bench-utils"
import { ACCESS_TOKEN_HINT_COMMAND } from "@/lib/host-utils"

export function TokenHint({ id }: { id?: string }) {
  return (
    <FieldDescription id={id} className="text-[15px]">
      On the bench:{" "}
      <span className="font-mono text-foreground">
        {ACCESS_TOKEN_HINT_COMMAND}
      </span>
    </FieldDescription>
  )
}

export function TokenInput({
  value,
  onChange,
  label = "Access token",
  placeholder = "Paste the bench's access token",
  error,
  disabled,
  autoFocus,
  className,
}: {
  value: string
  onChange: (value: string) => void
  label?: ReactNode
  placeholder?: string
  error?: string | null
  disabled?: boolean
  autoFocus?: boolean
  className?: string
}) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  return (
    <Field className={className} data-invalid={error ? true : undefined}>
      <FieldLabel htmlFor={id} className="text-[15px] font-semibold">
        {label}
      </FieldLabel>
      <Input
        id={id}
        type="password"
        // Keep browsers from offering to save or fill a login password here.
        autoComplete="new-password"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${errorId} ${hintId}` : hintId}
        className={cn(BENCH_INPUT_CLASS, "font-mono")}
      />
      {error ? <FieldError id={errorId}>{error}</FieldError> : null}
      <TokenHint id={hintId} />
    </Field>
  )
}

export function CheckboxRow({
  checked,
  onChange,
  children,
  description,
  disabled,
  name,
  type = "checkbox",
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  children: ReactNode
  description?: ReactNode
  disabled?: boolean
  /** For radio groups. */
  name?: string
  type?: "checkbox" | "radio"
}) {
  const id = useId()
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex min-h-11 cursor-pointer items-start gap-3 py-2.5 text-base",
        disabled && "cursor-not-allowed opacity-60"
      )}
    >
      <input
        id={id}
        type={type}
        name={name}
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 size-5 shrink-0 cursor-pointer accent-primary"
      />
      <span className="flex flex-col gap-0.5">
        <span className="font-semibold">{children}</span>
        {description ? (
          <span className="text-[15px] text-muted-foreground">
            {description}
          </span>
        ) : null}
      </span>
    </label>
  )
}
