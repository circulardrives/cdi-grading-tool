import { useState } from "react"
import { AlertCircleIcon, CheckCircle2Icon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@workspace/ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@workspace/ui/components/dialog"
import { FieldGroup } from "@workspace/ui/components/field"
import { Spinner } from "@workspace/ui/components/spinner"
import { Switch } from "@workspace/ui/components/switch"

import { AccessTokenField } from "@/components/access-token-field"
import { updateMachine } from "@/lib/api"
import { checkHostConnection, describeRequestError } from "@/lib/host-utils"
import type { Machine } from "@/lib/types"

type NewHostTokensDialogProps = {
  /** Newly added hosts that need an access token; empty closes the dialog. */
  hosts: Machine[]
  onClose: () => void
  /** Called after any token is saved so host lists can refresh. */
  onSaved: () => Promise<unknown> | void
}

/**
 * Asks for access tokens right after hosts are added (e.g. from Discover).
 * Tokens stay in this dialog's state only until saved, then are cleared.
 */
export function NewHostTokensDialog({
  hosts,
  onClose,
  onSaved,
}: NewHostTokensDialogProps) {
  const [tokens, setTokens] = useState<Record<string, string>>({})
  const [sharedToken, setSharedToken] = useState("")
  const [sameForAll, setSameForAll] = useState(true)
  const [saving, setSaving] = useState(false)
  const [problems, setProblems] = useState<Record<string, string>>({})
  const [doneIds, setDoneIds] = useState<Set<string>>(() => new Set())

  const pending = hosts.filter((host) => !doneIds.has(host.id))
  const useShared = sameForAll && pending.length > 1

  const close = () => {
    setTokens({})
    setSharedToken("")
    setProblems({})
    setDoneIds(new Set())
    onClose()
  }

  const tokenFor = (host: Machine) =>
    (useShared ? sharedToken : (tokens[host.id] ?? "")).trim()

  const save = async () => {
    const toSave = pending.filter((host) => tokenFor(host))
    if (toSave.length === 0) {
      toast.message("Paste a token, or choose Skip for now")
      return
    }

    setSaving(true)
    const nextProblems: Record<string, string> = { ...problems }
    const nextDone = new Set(doneIds)
    try {
      for (const host of toSave) {
        try {
          await updateMachine(host.id, { api_token: tokenFor(host) })
          const outcome = await checkHostConnection(host)
          if (!outcome || outcome.ok) {
            nextDone.add(host.id)
            delete nextProblems[host.id]
          } else {
            nextProblems[host.id] = outcome.text
          }
        } catch (err) {
          nextProblems[host.id] = describeRequestError(
            err,
            host.name,
            `Couldn't save the token for ${host.name}`
          )
        }
      }
    } finally {
      // Never keep a submitted token around, even when it was wrong.
      setTokens({})
      setSharedToken("")
      setSaving(false)
      await onSaved()
    }

    setProblems(nextProblems)
    setDoneIds(nextDone)
    const remaining = hosts.filter((host) => !nextDone.has(host.id))
    const savedCount = toSave.filter((host) => nextDone.has(host.id)).length
    if (remaining.length === 0) {
      toast.success(
        `Token saved — ${savedCount} host${savedCount === 1 ? "" : "s"} ready to scan`
      )
      close()
    } else if (savedCount > 0) {
      toast.success(`Token saved for ${savedCount} host${savedCount === 1 ? "" : "s"}`)
    }
  }

  return (
    <Dialog
      open={hosts.length > 0}
      onOpenChange={(open) => {
        if (!open && !saving) {
          close()
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {hosts.length === 1
              ? `Access token for ${hosts[0]?.name}`
              : "Access tokens for new hosts"}
          </DialogTitle>
          <DialogDescription>
            {hosts.length === 1
              ? "This host uses an access token. Add it so the dashboard can scan it."
              : "These hosts use access tokens. Add them so the dashboard can scan them."}
          </DialogDescription>
        </DialogHeader>

        <FieldGroup>
          {pending.length > 1 ? (
            <div className="flex items-center gap-2 text-sm">
              <Switch
                id="new-host-same-token"
                checked={sameForAll}
                onCheckedChange={setSameForAll}
                disabled={saving}
              />
              <label htmlFor="new-host-same-token">
                Same token for all {pending.length} hosts
              </label>
            </div>
          ) : null}

          {useShared ? (
            <AccessTokenField
              id="new-host-shared-token"
              value={sharedToken}
              onChange={setSharedToken}
              disabled={saving}
            />
          ) : (
            pending.map((host) => (
              <AccessTokenField
                key={host.id}
                id={`new-host-token-${host.id}`}
                label={`Access token for ${host.name}`}
                value={tokens[host.id] ?? ""}
                onChange={(value) =>
                  setTokens((current) => ({ ...current, [host.id]: value }))
                }
                disabled={saving}
              />
            ))
          )}

          {hosts.length > 1 || Object.keys(problems).length > 0 ? (
            <ul className="flex flex-col gap-1 text-sm">
              {hosts.map((host) => (
                <li key={host.id} className="flex items-start gap-1.5">
                  {doneIds.has(host.id) ? (
                    <>
                      <CheckCircle2Icon
                        className="text-primary mt-0.5 size-4 shrink-0"
                        aria-hidden
                      />
                      <span>{host.name} — ready to scan</span>
                    </>
                  ) : problems[host.id] ? (
                    <>
                      <AlertCircleIcon
                        className="text-destructive mt-0.5 size-4 shrink-0"
                        aria-hidden
                      />
                      <span className="text-destructive">{problems[host.id]}</span>
                    </>
                  ) : (
                    <span className="text-muted-foreground pl-5.5">
                      {host.name} — waiting for a token
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : null}
        </FieldGroup>

        <DialogFooter>
          <Button variant="outline" onClick={close} disabled={saving}>
            Skip for now
          </Button>
          <Button onClick={() => void save()} disabled={saving}>
            {saving ? <Spinner data-icon="inline-start" /> : null}
            {saving ? "Checking…" : "Save and check"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
