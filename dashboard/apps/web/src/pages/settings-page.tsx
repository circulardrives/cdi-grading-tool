/**
 * Settings: Demo mode, Theme, About. Pinned at the bottom of the sidebar.
 */
import type { ReactNode } from "react"
import { MonitorIcon, MoonIcon, SunIcon } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { Switch } from "@workspace/ui/components/switch"

import { useMockDataSettings } from "@/components/mock-data-provider"
import { useTheme } from "@/components/theme-provider"
import { Note, PageSection } from "@/components/ui-cdi"
import { useFleetDevicesQuery, useHealthQuery } from "@/hooks/use-cdi-queries"
import { appConfig } from "@/lib/config"

type ThemeChoice = "light" | "dark" | "system"

const THEME_CHOICES: { value: ThemeChoice; label: string; icon: ReactNode }[] =
  [
    { value: "light", label: "Light", icon: <SunIcon aria-hidden="true" /> },
    { value: "dark", label: "Dark", icon: <MoonIcon aria-hidden="true" /> },
    {
      value: "system",
      label: "Match this device",
      icon: <MonitorIcon aria-hidden="true" />,
    },
  ]

const PROFILE_LABEL: Record<string, string> = {
  abcdf: "Letter grades A–F",
  binary: "Pass or fail",
}

function hostLabel(url: string): string {
  try {
    return new URL(url).host || url
  } catch {
    return url.replace(/^https?:\/\//, "")
  }
}

function AboutRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-0.5 border-b py-3 last:border-b-0">
      <dt className="w-56 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 font-semibold">{value}</dd>
    </div>
  )
}

export function SettingsPage() {
  const { useMockData, setUseMockData } = useMockDataSettings()
  const { theme, setTheme } = useTheme()
  const health = useHealthQuery()
  const fleet = useFleetDevicesQuery()

  const profile = fleet.data?.devices.find(
    (device) => device.grading_profile
  )?.grading_profile
  const benchVersion = health.data?.version
  const benchHostname = health.data?.hostname

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <PageSection id="demo-mode" title="Demo mode">
        <div className="flex items-center justify-between gap-6">
          <label htmlFor="demo-mode-switch" className="flex flex-col gap-1">
            <span className="text-[17px] font-semibold">
              Show sample drives
            </span>
            <span className="text-muted-foreground">
              Shows sample drives instead of real benches — for training and
              demos. While it's on, a banner across the top of every page says
              so.
            </span>
          </label>
          <Switch
            id="demo-mode-switch"
            checked={useMockData}
            onCheckedChange={setUseMockData}
            className="scale-125"
          />
        </div>
        {useMockData ? (
          <Note tone="warn">
            Demo mode is on. Scans load sample drives; nothing is read from real
            benches.
          </Note>
        ) : null}
      </PageSection>

      <PageSection id="theme" title="Theme">
        <div
          role="radiogroup"
          aria-label="Theme"
          className="flex flex-wrap gap-2"
        >
          {THEME_CHOICES.map((choice) => (
            <Button
              key={choice.value}
              type="button"
              variant="outline"
              role="radio"
              aria-checked={theme === choice.value}
              className={
                theme === choice.value
                  ? "border-primary/50 bg-accent text-accent-foreground hover:bg-accent"
                  : undefined
              }
              onClick={() => setTheme(choice.value)}
            >
              {choice.icon}
              {choice.label}
            </Button>
          ))}
        </div>
      </PageSection>

      <PageSection id="about" title="About">
        <dl className="flex flex-col">
          <AboutRow label="Dashboard version" value={__APP_VERSION__ || "—"} />
          <AboutRow
            label="This bench"
            value={
              <span className="flex flex-col">
                <span>{benchHostname || "—"}</span>
                <span className="font-mono text-sm font-normal text-muted-foreground">
                  {hostLabel(appConfig.apiHost)}
                </span>
              </span>
            }
          />
          <AboutRow
            label="CDI Health on this bench"
            value={
              health.isLoading
                ? "Checking…"
                : benchVersion
                  ? `Version ${benchVersion}`
                  : "Not answering"
            }
          />
          {profile ? (
            <AboutRow
              label="Grading"
              value={PROFILE_LABEL[profile] ?? profile}
            />
          ) : null}
        </dl>
      </PageSection>
    </div>
  )
}
