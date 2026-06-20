const STORAGE_KEY = "cdi-selected-host-id"

export function getSelectedHostId(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function setSelectedHostId(hostId: string | null): void {
  try {
    if (hostId) {
      sessionStorage.setItem(STORAGE_KEY, hostId)
    } else {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    /* ignore storage failures */
  }
}
