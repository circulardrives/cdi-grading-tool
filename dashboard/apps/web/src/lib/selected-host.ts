import { useSyncExternalStore } from "react"

const STORAGE_KEY = "cdi-selected-host-id"

type Listener = () => void

const listeners = new Set<Listener>()
// Fallback when sessionStorage is unavailable (private mode, blocked storage).
let memoryValue: string | null = null

export function getSelectedHostId(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return memoryValue
  }
}

export function setSelectedHostId(hostId: string | null): void {
  memoryValue = hostId
  try {
    if (hostId) {
      sessionStorage.setItem(STORAGE_KEY, hostId)
    } else {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    /* ignore storage failures */
  }
  for (const listener of listeners) {
    listener()
  }
}

function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/**
 * Active fleet host for this tab (session storage). Every component using the
 * hook re-renders when any page changes the selection.
 */
export function useSelectedHostId(): string | null {
  return useSyncExternalStore(subscribe, getSelectedHostId, () => null)
}
