/**
 * One-tap light/dark switch for the header. It flips whatever is showing
 * right now (following the system counts as its current look); the full
 * Light / Dark / Match system choice lives in Settings.
 */
import { MoonIcon, SunIcon } from "lucide-react"
import { useSyncExternalStore } from "react"

import { Button } from "@workspace/ui/components/button"

import { useTheme } from "@/components/theme-provider"

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  })
  return () => observer.disconnect()
}

function isDarkNow() {
  return document.documentElement.classList.contains("dark")
}

export function ThemeSwitch() {
  const { setTheme } = useTheme()
  const dark = useSyncExternalStore(subscribe, isDarkNow, () => false)
  const label = dark ? "Switch to light mode" : "Switch to dark mode"

  return (
    <Button
      variant="ghost"
      size="icon"
      className="size-11"
      aria-label={label}
      title={label}
      onClick={() => setTheme(dark ? "light" : "dark")}
    >
      {dark ? <SunIcon aria-hidden="true" /> : <MoonIcon aria-hidden="true" />}
    </Button>
  )
}
