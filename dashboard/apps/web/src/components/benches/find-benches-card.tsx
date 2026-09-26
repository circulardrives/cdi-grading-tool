/**
 * "Find benches on the network": one "Networks to search" field, Search, and
 * a result line. New benches can be added right here; ones that use an access
 * token ask for it inline, lab-mode ones don't.
 */
import { useId, useMemo, useState, type FormEvent } from "react"
import {
  CheckIcon,
  MonitorIcon,
  PlusIcon,
  RadarIcon,
  SearchIcon,
} from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"

import {
  BENCH_INPUT_CLASS,
  loadSavedNetworks,
  MAX_NETWORKS,
  parseNetworks,
  saveNetworks,
} from "@/components/benches/bench-utils"
import { CheckboxRow, TokenInput } from "@/components/benches/token-input"
import {
  BenchLabel,
  benchAddress,
  Note,
  PageSection,
} from "@/components/ui-cdi"
import { useHealthQuery } from "@/hooks/use-cdi-queries"
import { ApiError, createMachine, discoverHosts } from "@/lib/api"
import { appConfig } from "@/lib/config"
import { defaultDiscoveredHostName } from "@/lib/host-utils"
import type { DiscoveredHost, DiscoverRequest, Machine } from "@/lib/types"

type SearchResult = {
  /** CDI Health benches that answered (other devices are left out). */
  found: DiscoveredHost[]
  searched: string[]
  addressesSearched: number
  seconds: number
}

type TokenNeed = "none" | "token" | "unknown"

function tokenNeed(host: DiscoveredHost): TokenNeed {
  const health = host.health
  if (health?.auth_mode === "none") {
    return "none"
  }
  if (health?.auth_mode === "token") {
    return "token"
  }
  if (health && "api_token_enabled" in health) {
    return health.api_token_enabled ? "token" : "none"
  }
  return "unknown"
}

function searchErrorText(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) {
    const wait = /retry in (\d+)/i.exec(error.message)?.[1]
    if (/in progress/i.test(error.message)) {
      return "A search is already running — wait for it to finish."
    }
    return wait
      ? `You searched a moment ago. Try again in ${wait} seconds.`
      : "You searched a moment ago. Try again in a few seconds."
  }
  if (error instanceof ApiError && error.status === 400) {
    const text = error.message
    if (/not allowed|private/i.test(text)) {
      return "Only lab networks can be searched (10.x, 172.16–31.x, 192.168.x)."
    }
    return text.split("\n")[0] ?? text
  }
  if (error instanceof Error && error.message) {
    return `The search didn't finish — ${error.message}. Try again.`
  }
  return "The search didn't finish. Try again."
}

function resultLine(found: number, fresh: number, added: number): string {
  if (found === 0) {
    return ""
  }
  const benches = `${found} bench${found === 1 ? "" : "es"}`
  if (fresh === 0) {
    if (added > 0) {
      return `Found ${benches} — ${added === found ? (found === 1 ? "added" : "all added") : `${added} added, the rest were already here`}.`
    }
    if (found === 1) {
      return "Found 1 bench — already added."
    }
    return `Found ${benches} — ${found === 2 ? "both" : "all"} already added.`
  }
  if (fresh === found) {
    return `Found ${fresh} new bench${fresh === 1 ? "" : "es"}.`
  }
  return `Found ${benches} — ${fresh} new.`
}

export function FindBenchesCard({
  onAdded,
}: {
  /** New benches, right after they're added (the page checks each one). */
  onAdded: (machines: Machine[]) => void
}) {
  const inputId = useId()
  const hintId = `${inputId}-hint`
  const [networks, setNetworks] = useState(() =>
    loadSavedNetworks(appConfig.discoverSubnet)
  )
  const [touched, setTouched] = useState(false)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [tokens, setTokens] = useState<Record<string, string>>({})
  const [usesToken, setUsesToken] = useState<Record<string, boolean>>({})
  const [adding, setAdding] = useState<Set<string>>(() => new Set())
  const [added, setAdded] = useState<Set<string>>(() => new Set())
  const [addErrors, setAddErrors] = useState<Record<string, string>>({})

  const parsed = useMemo(() => parseNetworks(networks), [networks])
  const inputError = touched ? parsed.error : null

  // The bench this dashboard runs on answers too; it is never added as a bench.
  const ownInstanceId = useHealthQuery().data?.instance_id ?? null
  const isThisBench = (host: DiscoveredHost) =>
    Boolean(host.is_this_bench) ||
    (ownInstanceId != null && host.health?.instance_id === ownInstanceId)
  const thisBench = (result?.found ?? []).filter(isThisBench)
  const others = (result?.found ?? []).filter((host) => !isThisBench(host))
  const fresh = others.filter((host) => !host.already_registered)
  const pending = fresh.filter((host) => !added.has(host.address))

  const search = async (event: FormEvent) => {
    event.preventDefault()
    setTouched(true)
    if (parsed.error != null) {
      return
    }
    const list = parsed.networks
    const body: DiscoverRequest =
      list.length > 1
        ? { subnets: list }
        : list.length === 1
          ? { subnet: list[0] }
          : {}
    setSearching(true)
    setSearchError(null)
    setResult(null)
    setTokens({})
    setUsesToken({})
    setAdded(new Set())
    setAddErrors({})
    try {
      const response = await discoverHosts(body)
      saveNetworks(networks)
      setResult({
        found: response.found.filter((host) => host.cdi_api),
        searched: response.scanned_subnets,
        addressesSearched: response.hosts_scanned,
        seconds: Math.max(1, Math.round(response.duration_ms / 1000)),
      })
    } catch (error) {
      setSearchError(searchErrorText(error))
    } finally {
      setSearching(false)
    }
  }

  const addHosts = async (hosts: DiscoveredHost[]) => {
    const addresses = hosts.map((host) => host.address)
    setAdding((current) => new Set([...current, ...addresses]))
    const created: Machine[] = []
    for (const host of hosts) {
      const name = defaultDiscoveredHostName(host)
      const need = tokenNeed(host)
      const token = (tokens[host.address] ?? "").trim()
      const sendToken =
        token &&
        (need === "token" || (need === "unknown" && usesToken[host.address]))
      try {
        const machine = await createMachine({
          name,
          hostname: host.health?.hostname?.trim() || host.hostname || name,
          address: host.address,
          ...(sendToken ? { api_token: token } : {}),
        })
        created.push(machine)
        setAdded((current) => new Set(current).add(host.address))
        setAddErrors((current) => {
          const next = { ...current }
          delete next[host.address]
          return next
        })
      } catch (error) {
        const message = error instanceof Error ? error.message : ""
        const text = /this bench itself/i.test(message)
          ? `${name} is this bench — the dashboard is running here.`
          : /already|exists|duplicate/i.test(message)
            ? `${name} is already added.`
            : `Couldn't add ${name} — try again.`
        setAddErrors((current) => ({ ...current, [host.address]: text }))
      }
    }
    // Tokens are write-only: drop them once sent.
    setTokens((current) => {
      const next = { ...current }
      for (const address of addresses) {
        delete next[address]
      }
      return next
    })
    setAdding((current) => {
      const next = new Set(current)
      for (const address of addresses) {
        next.delete(address)
      }
      return next
    })
    if (created.length > 0) {
      onAdded(created)
    }
  }

  const busy = searching || adding.size > 0
  const line = result
    ? others.length === 0
      ? "Only this bench answered — the dashboard is running here."
      : resultLine(others.length, pending.length, added.size)
    : ""

  return (
    <PageSection
      id="find-benches"
      emphasis
      title={
        <span className="flex items-center gap-2.5">
          <RadarIcon className="size-[22px] text-primary" aria-hidden="true" />
          Find benches on the network
        </span>
      }
    >
      <form
        onSubmit={(event) => void search(event)}
        noValidate
        className="flex flex-col gap-2"
      >
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-[min(100%,16rem)] flex-1 flex-col gap-1.5">
            <label htmlFor={inputId} className="text-[15px] font-semibold">
              Networks to search
            </label>
            <Input
              id={inputId}
              value={networks}
              onChange={(event) => setNetworks(event.target.value)}
              onBlur={() => setTouched(true)}
              placeholder="For example 192.168.0.0/24, 192.168.1.0/24"
              spellCheck={false}
              autoComplete="off"
              disabled={searching}
              aria-invalid={inputError ? true : undefined}
              aria-describedby={hintId}
              className={cn(BENCH_INPUT_CLASS, "font-mono text-[15px]")}
            />
          </div>
          <Button type="submit" disabled={busy} className="h-12 min-w-28">
            {searching ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <SearchIcon data-icon="inline-start" aria-hidden="true" />
            )}
            {searching ? "Searching…" : "Search"}
          </Button>
        </div>
        <p
          id={hintId}
          className={cn(
            "text-[15px]",
            inputError ? "text-destructive" : "text-muted-foreground"
          )}
        >
          {inputError ??
            `Up to ${MAX_NETWORKS} networks, separated by commas or spaces. Leave it blank to search the network this dashboard is on.`}
        </p>
      </form>

      <div aria-live="polite" className="flex flex-col gap-3 empty:hidden">
        {searching ? (
          <Note tone="info" icon={<Spinner />}>
            Looking for benches — this takes a few seconds.
          </Note>
        ) : null}
        {searchError ? <Note tone="bad">{searchError}</Note> : null}
        {result && result.found.length === 0 ? (
          <Note tone="warn">
            No benches answered on{" "}
            {result.searched.join(", ") || "this network"}. Check they&apos;re
            powered on and on this network, or search another one.
          </Note>
        ) : null}
        {result && result.found.length > 0 ? (
          <Note tone={pending.length > 0 ? "info" : "ok"} neutralText>
            {line}
          </Note>
        ) : null}
      </div>

      {result && (fresh.length > 0 || thisBench.length > 0) ? (
        <ul className="flex flex-col divide-y rounded-[10px] border">
          {thisBench.map((host) => (
            <li
              key={host.address}
              className="flex items-center gap-3 px-4 py-3"
            >
              <BenchLabel
                className="flex-1"
                machine={{
                  name: defaultDiscoveredHostName(host),
                  address: benchAddress({ address: host.address }),
                }}
              />
              <span className="inline-flex items-center gap-2 text-[15px] text-muted-foreground">
                <MonitorIcon className="size-5" aria-hidden="true" />
                This bench (the dashboard is running here)
              </span>
            </li>
          ))}
          {fresh.map((host) => {
            const need = tokenNeed(host)
            const name = defaultDiscoveredHostName(host)
            const isAdding = adding.has(host.address)
            const isAdded = added.has(host.address)
            const wantsToken =
              need === "token" ||
              (need === "unknown" && usesToken[host.address])
            return (
              <li
                key={host.address}
                className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-start"
              >
                <div className="flex min-w-40 flex-1 flex-col gap-2">
                  <BenchLabel
                    machine={{
                      name,
                      address: benchAddress({ address: host.address }),
                    }}
                  />
                  {isAdded ? null : need === "none" ? (
                    <span className="text-[15px] text-muted-foreground">
                      No token needed
                    </span>
                  ) : need === "unknown" ? (
                    <CheckboxRow
                      checked={Boolean(usesToken[host.address])}
                      onChange={(checked) =>
                        setUsesToken((current) => ({
                          ...current,
                          [host.address]: checked,
                        }))
                      }
                      disabled={isAdding}
                    >
                      This bench uses an access token
                    </CheckboxRow>
                  ) : null}
                  {!isAdded && wantsToken ? (
                    <TokenInput
                      label={`Access token for ${name}`}
                      value={tokens[host.address] ?? ""}
                      onChange={(value) =>
                        setTokens((current) => ({
                          ...current,
                          [host.address]: value,
                        }))
                      }
                      disabled={isAdding}
                      className="max-w-md"
                    />
                  ) : null}
                  {addErrors[host.address] ? (
                    <Note tone="bad">{addErrors[host.address]}</Note>
                  ) : null}
                </div>
                <div className="flex shrink-0 items-center sm:pt-0.5">
                  {isAdded ? (
                    <span className="inline-flex h-11 items-center gap-2 font-semibold text-tone-ok-fg">
                      <CheckIcon className="size-5" aria-hidden="true" />
                      Added
                    </span>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={() => void addHosts([host])}
                      disabled={isAdding || searching}
                      aria-label={`Add ${name}`}
                    >
                      {isAdding ? (
                        <Spinner data-icon="inline-start" />
                      ) : (
                        <PlusIcon data-icon="inline-start" aria-hidden="true" />
                      )}
                      {isAdding ? "Adding…" : "Add"}
                    </Button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      ) : null}

      {pending.length > 1 ? (
        <div>
          <Button onClick={() => void addHosts(pending)} disabled={busy}>
            {adding.size > 0 ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <PlusIcon data-icon="inline-start" aria-hidden="true" />
            )}
            Add all {pending.length}
          </Button>
        </div>
      ) : null}

      {result && result.found.length > 0 ? (
        <p className="text-[15px] text-muted-foreground">
          Searched {result.searched.join(", ")} ·{" "}
          {result.addressesSearched.toLocaleString()} addresses in{" "}
          {result.seconds} s
        </p>
      ) : null}
    </PageSection>
  )
}
