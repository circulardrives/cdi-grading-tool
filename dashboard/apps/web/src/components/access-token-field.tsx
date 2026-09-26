import { useId } from "react"

import { Field, FieldDescription, FieldLabel } from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { Switch } from "@workspace/ui/components/switch"

import { ACCESS_TOKEN_HINT_COMMAND } from "@/lib/host-utils"

type AccessTokenFieldProps = {
  value: string
  onChange: (value: string) => void
  /** The host already has a token stored; blank keeps it. */
  hasToken?: boolean
  /** Offer a "Clear token" switch (edit only). */
  clearable?: boolean
  clear?: boolean
  onClearChange?: (clear: boolean) => void
  /** The host runs in lab mode without tokens; show a neutral note. */
  noTokenNeeded?: boolean
  label?: string
  disabled?: boolean
  id?: string
}

/**
 * Write-only access token input. The value lives only in the parent's state
 * until saved; callers must reset it after submit.
 */
export function AccessTokenField({
  value,
  onChange,
  hasToken = false,
  clearable = false,
  clear = false,
  onClearChange,
  noTokenNeeded = false,
  label = "Access token",
  disabled = false,
  id,
}: AccessTokenFieldProps) {
  const generatedId = useId()
  const inputId = id ?? `access-token-${generatedId}`
  const clearId = `${inputId}-clear`
  const hintId = `${inputId}-hint`

  return (
    <Field>
      <FieldLabel htmlFor={inputId}>{label}</FieldLabel>
      <Input
        id={inputId}
        type="password"
        // Stop browsers offering to save or autofill a login password here.
        autoComplete="new-password"
        spellCheck={false}
        value={clear ? "" : value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={
          hasToken ? "Leave blank to keep current" : "Paste the host's token"
        }
        disabled={disabled || clear}
        aria-describedby={hintId}
      />
      <FieldDescription id={hintId}>
        {noTokenNeeded
          ? "No token needed — this host runs in lab mode. You can still set one here. "
          : null}
        On the host, run{" "}
        <span className="font-mono">{ACCESS_TOKEN_HINT_COMMAND}</span> and copy the
        value after <span className="font-mono">CDI_HEALTH_API_TOKEN=</span>
        {noTokenNeeded ? "." : ". Leave blank if the host doesn't use one."}
      </FieldDescription>
      {clearable && hasToken ? (
        <div className="flex items-center gap-2 text-sm">
          <Switch
            id={clearId}
            checked={clear}
            onCheckedChange={(checked) => {
              onClearChange?.(checked)
              if (checked) {
                onChange("")
              }
            }}
            disabled={disabled}
          />
          <label htmlFor={clearId}>Clear saved token</label>
        </div>
      ) : null}
    </Field>
  )
}
