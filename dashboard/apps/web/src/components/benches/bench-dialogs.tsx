/**
 * Dialogs on the Benches page:
 *
 * - <AddBenchDialog>     Address, optional Name / Rack or location, optional access token
 * - <EditBenchDialog>    name, address, rack or location, notes, access token (set / replace / clear)
 * - <RemoveBenchDialog>  confirm, naming the bench
 */
import { useId, useState, type FormEvent, type ReactNode } from "react"
import { Trash2Icon } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@workspace/ui/components/alert-dialog"
import { Button } from "@workspace/ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@workspace/ui/components/dialog"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Input } from "@workspace/ui/components/input"
import { Spinner } from "@workspace/ui/components/spinner"
import { Textarea } from "@workspace/ui/components/textarea"
import { cn } from "@workspace/ui/lib/utils"

import {
  BENCH_INPUT_CLASS,
  parseBenchAddress,
} from "@/components/benches/bench-utils"
import { CheckboxRow, TokenInput } from "@/components/benches/token-input"
import { benchAddress, benchName, Note } from "@/components/ui-cdi"
import { createMachine, updateMachine } from "@/lib/api"
import type { Machine, MachineUpdateRequest } from "@/lib/types"

function errorText(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) {
    const text = error.message.trim().split("\n")[0] ?? ""
    if (/already|exists|duplicate/i.test(text)) {
      return "A bench with this address is already added."
    }
    if (/private network/i.test(text)) {
      return "That address isn't on the lab network. Use the bench's local IP address."
    }
    return text
  }
  return fallback
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  description,
  error,
  mono,
  disabled,
  autoFocus,
  optional,
}: {
  label: ReactNode
  value: string
  onChange: (value: string) => void
  placeholder?: string
  description?: ReactNode
  error?: string | null
  mono?: boolean
  disabled?: boolean
  autoFocus?: boolean
  optional?: boolean
}) {
  const id = useId()
  const describedBy = [
    error ? `${id}-error` : null,
    description ? `${id}-hint` : null,
  ]
    .filter(Boolean)
    .join(" ")
  return (
    <Field data-invalid={error ? true : undefined}>
      <FieldLabel htmlFor={id} className="text-[15px] font-semibold">
        {label}
        {optional ? (
          <span className="font-normal text-muted-foreground">(optional)</span>
        ) : null}
      </FieldLabel>
      <Input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        spellCheck={false}
        autoComplete="off"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className={cn(BENCH_INPUT_CLASS, mono && "font-mono")}
      />
      {error ? <FieldError id={`${id}-error`}>{error}</FieldError> : null}
      {description ? (
        <FieldDescription id={`${id}-hint`} className="text-[15px]">
          {description}
        </FieldDescription>
      ) : null}
    </Field>
  )
}

// ---------------------------------------------------------------------------
// Add by address
// ---------------------------------------------------------------------------

export function AddBenchDialog({
  open,
  onOpenChange,
  onAdded,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Called with the new bench; the page then runs a connection check. */
  onAdded: (machine: Machine) => void
}) {
  const [address, setAddress] = useState("")
  const [name, setName] = useState("")
  const [location, setLocation] = useState("")
  const [usesToken, setUsesToken] = useState(false)
  const [token, setToken] = useState("")
  const [addressError, setAddressError] = useState<string | null>(null)
  const [tokenError, setTokenError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const reset = () => {
    setAddress("")
    setName("")
    setLocation("")
    setUsesToken(false)
    setToken("")
    setAddressError(null)
    setTokenError(null)
    setSaveError(null)
  }

  const setOpen = (next: boolean) => {
    if (saving) {
      return
    }
    if (!next) {
      reset()
    }
    onOpenChange(next)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const parsed = parseBenchAddress(address)
    setAddressError(parsed.error)
    const trimmedToken = token.trim()
    const missingToken = usesToken && !trimmedToken
    setTokenError(
      missingToken
        ? "Paste the access token, or untick “This bench uses an access token”."
        : null
    )
    if (parsed.error != null || missingToken) {
      return
    }

    const label = name.trim() || benchAddress({ address: parsed.address })
    setSaving(true)
    setSaveError(null)
    try {
      const machine = await createMachine({
        name: label,
        hostname: label,
        address: parsed.address,
        location: location.trim(),
        ...(usesToken ? { api_token: trimmedToken } : {}),
      })
      reset()
      onOpenChange(false)
      onAdded(machine)
    } catch (error) {
      setSaveError(errorText(error, "Couldn't add the bench — try again."))
    } finally {
      // Never keep a submitted token around.
      setToken("")
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={(event) => void submit(event)} noValidate>
          <DialogHeader>
            <DialogTitle className="text-xl">
              Add a bench by address
            </DialogTitle>
            <DialogDescription className="text-[15px]">
              After you add it, the dashboard checks the connection and picks up
              the bench&apos;s own name.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-5">
            <TextField
              label="Address (IP or IP:port)"
              value={address}
              onChange={(value) => {
                setAddress(value)
                setAddressError(null)
              }}
              placeholder="10.100.10.57"
              error={addressError}
              mono
              disabled={saving}
              autoFocus
            />
            <TextField
              label="Name"
              optional
              value={name}
              onChange={setName}
              placeholder="pecan09"
              description="Only used if the bench doesn't report its own name."
              disabled={saving}
            />
            <TextField
              label="Rack or location"
              optional
              value={location}
              onChange={setLocation}
              placeholder="Row 3 · Rack 12"
              disabled={saving}
            />
            <div className="flex flex-col gap-2">
              <CheckboxRow
                checked={usesToken}
                onChange={(checked) => {
                  setUsesToken(checked)
                  setTokenError(null)
                  if (!checked) {
                    setToken("")
                  }
                }}
                disabled={saving}
              >
                This bench uses an access token
              </CheckboxRow>
              {usesToken ? (
                <TokenInput
                  value={token}
                  onChange={(value) => {
                    setToken(value)
                    setTokenError(null)
                  }}
                  error={tokenError}
                  disabled={saving}
                />
              ) : null}
            </div>
            {saveError ? <Note tone="bad">{saveError}</Note> : null}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner data-icon="inline-start" /> : null}
              {saving ? "Adding…" : "Add bench"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Edit
// ---------------------------------------------------------------------------

type TokenChoice = "keep" | "replace" | "clear"

export function EditBenchDialog({
  machine,
  onClose,
  onSaved,
  onRemove,
}: {
  /** The bench being edited; null closes the dialog. */
  machine: Machine | null
  onClose: () => void
  /** Called after saving; the page then runs a connection check. */
  onSaved: (machine: Machine) => void
  onRemove: (machine: Machine) => void
}) {
  return (
    <Dialog
      open={machine != null}
      onOpenChange={(open) => {
        if (!open) {
          onClose()
        }
      }}
    >
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-lg">
        {machine ? (
          // Keyed so the form starts fresh for each bench.
          <EditBenchForm
            key={machine.id}
            machine={machine}
            onClose={onClose}
            onSaved={onSaved}
            onRemove={onRemove}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function EditBenchForm({
  machine,
  onClose,
  onSaved,
  onRemove,
}: {
  machine: Machine
  onClose: () => void
  onSaved: (machine: Machine) => void
  onRemove: (machine: Machine) => void
}) {
  const displayName = benchName(machine)
  const [name, setName] = useState(machine.name)
  const [address, setAddress] = useState(machine.address)
  const [location, setLocation] = useState(machine.location)
  const [notes, setNotes] = useState(machine.notes)
  const hasToken = Boolean(machine.has_api_token)
  // A saved token that was turned down: start on "Replace it".
  const [tokenChoice, setTokenChoice] = useState<TokenChoice>(
    hasToken && machine.status === "auth_failed" ? "replace" : "keep"
  )
  // A bench that turned the token down needs one: open the field right away.
  const needsToken =
    machine.status === "auth_failed" || machine.remote_auth === "token"
  const [usesToken, setUsesToken] = useState(needsToken)
  const [token, setToken] = useState("")
  const [addressError, setAddressError] = useState<string | null>(null)
  const [tokenError, setTokenError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const notesId = useId()

  const wantsNewToken = hasToken ? tokenChoice === "replace" : usesToken

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const parsed = parseBenchAddress(address)
    setAddressError(parsed.error)
    const trimmedToken = token.trim()
    const missingToken = wantsNewToken && !trimmedToken
    setTokenError(missingToken ? "Paste the new access token." : null)
    if (parsed.error != null || missingToken) {
      return
    }

    const payload: MachineUpdateRequest = {
      name: name.trim() || benchAddress({ address: parsed.address }),
      address: parsed.address,
      location: location.trim(),
      notes: notes.trim(),
    }
    if (wantsNewToken) {
      payload.api_token = trimmedToken
    } else if (hasToken && tokenChoice === "clear") {
      payload.api_token = ""
    }

    setSaving(true)
    setSaveError(null)
    try {
      const saved = await updateMachine(machine.id, payload)
      onClose()
      onSaved(saved)
    } catch (error) {
      setSaveError(
        errorText(error, `Couldn't save ${displayName} — try again.`)
      )
    } finally {
      setToken("")
      setSaving(false)
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} noValidate>
      <DialogHeader>
        <DialogTitle className="text-xl">Edit {displayName}</DialogTitle>
        <DialogDescription className="text-[15px]">
          {machine.remote_hostname
            ? `The bench calls itself ${displayName}, so that's the name shown everywhere.`
            : "Change how the dashboard reaches this bench."}
        </DialogDescription>
      </DialogHeader>
      <div className="flex flex-col gap-4 py-5">
        <TextField
          label="Name"
          value={name}
          onChange={setName}
          description="Only used if the bench doesn't report its own name."
          disabled={saving}
        />
        <TextField
          label="Address (IP or IP:port)"
          value={address}
          onChange={(value) => {
            setAddress(value)
            setAddressError(null)
          }}
          error={addressError}
          mono
          disabled={saving}
        />
        <TextField
          label="Rack or location"
          optional
          value={location}
          onChange={setLocation}
          placeholder="Row 3 · Rack 12"
          disabled={saving}
        />
        <Field>
          <FieldLabel htmlFor={notesId} className="text-[15px] font-semibold">
            Notes
            <span className="font-normal text-muted-foreground">
              (optional)
            </span>
          </FieldLabel>
          <Textarea
            id={notesId}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="8-bay NVMe backplane"
            disabled={saving}
            className="min-h-20 rounded-[10px] border-input bg-card px-3.5 py-2.5 text-base md:text-base"
          />
        </Field>

        <fieldset className="flex flex-col gap-1">
          <legend className="mb-1 text-[15px] font-semibold">
            Access token
          </legend>
          {hasToken ? (
            <>
              <CheckboxRow
                type="radio"
                name={`token-${machine.id}`}
                checked={tokenChoice === "keep"}
                onChange={() => setTokenChoice("keep")}
                disabled={saving}
              >
                Keep the saved token
              </CheckboxRow>
              <CheckboxRow
                type="radio"
                name={`token-${machine.id}`}
                checked={tokenChoice === "replace"}
                onChange={() => setTokenChoice("replace")}
                disabled={saving}
              >
                Replace it with a new token
              </CheckboxRow>
              {tokenChoice === "replace" ? (
                <TokenInput
                  label="New token"
                  autoFocus={machine.status === "auth_failed"}
                  value={token}
                  onChange={(value) => {
                    setToken(value)
                    setTokenError(null)
                  }}
                  error={tokenError}
                  disabled={saving}
                  className="mb-2 pl-8"
                />
              ) : null}
              <CheckboxRow
                type="radio"
                name={`token-${machine.id}`}
                checked={tokenChoice === "clear"}
                onChange={() => setTokenChoice("clear")}
                description="For benches that no longer use one."
                disabled={saving}
              >
                Remove the saved token
              </CheckboxRow>
            </>
          ) : (
            <>
              <CheckboxRow
                checked={usesToken}
                onChange={(checked) => {
                  setUsesToken(checked)
                  setTokenError(null)
                  if (!checked) {
                    setToken("")
                  }
                }}
                description={
                  machine.remote_auth === "none"
                    ? "The last check found this bench doesn't need one."
                    : undefined
                }
                disabled={saving}
              >
                This bench uses an access token
              </CheckboxRow>
              {usesToken ? (
                <TokenInput
                  label="Token"
                  value={token}
                  onChange={(value) => {
                    setToken(value)
                    setTokenError(null)
                  }}
                  error={tokenError}
                  disabled={saving}
                  autoFocus={needsToken}
                />
              ) : null}
            </>
          )}
        </fieldset>
        {saveError ? <Note tone="bad">{saveError}</Note> : null}
      </div>
      <DialogFooter className="gap-2 sm:justify-between">
        <Button
          type="button"
          variant="destructive"
          onClick={() => onRemove(machine)}
          disabled={saving}
        >
          <Trash2Icon data-icon="inline-start" aria-hidden="true" />
          Remove bench
        </Button>
        <div className="flex flex-col-reverse gap-2 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? <Spinner data-icon="inline-start" /> : null}
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </DialogFooter>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Remove
// ---------------------------------------------------------------------------

export function RemoveBenchDialog({
  machine,
  removing,
  onCancel,
  onConfirm,
}: {
  machine: Machine | null
  removing: boolean
  onCancel: () => void
  onConfirm: (machine: Machine) => void
}) {
  const name = machine ? benchName(machine) : "this bench"
  return (
    <AlertDialog
      open={machine != null}
      onOpenChange={(open) => {
        if (!open && !removing) {
          onCancel()
        }
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="text-xl">
            Remove {name}?
          </AlertDialogTitle>
          <AlertDialogDescription className="text-base">
            The dashboard stops scanning {name}. Its saved scans stay in Reports
            › Scan history, and nothing changes on the bench itself — you can
            add it again later.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={removing}>Keep {name}</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={removing}
            onClick={(event) => {
              // Stay open until the removal finishes.
              event.preventDefault()
              if (machine) {
                onConfirm(machine)
              }
            }}
          >
            {removing ? <Spinner data-icon="inline-start" /> : null}
            Remove {name}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
