/* eslint-disable react-refresh/only-export-components */
import * as React from "react"

import { appConfig } from "@/lib/config"

const STORAGE_KEY = "cdi-use-mock-data"

type MockDataSettingsState = {
  useMockData: boolean
  setUseMockData: (enabled: boolean) => void
  mockDataPath: string
}

const MockDataSettingsContext = React.createContext<
  MockDataSettingsState | undefined
>(undefined)

function readStoredMockData(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1"
  } catch {
    return false
  }
}

function writeStoredMockData(enabled: boolean): void {
  try {
    if (enabled) {
      localStorage.setItem(STORAGE_KEY, "1")
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    /* ignore storage failures */
  }
}

export function MockDataProvider({ children }: { children: React.ReactNode }) {
  const [useMockData, setUseMockDataState] = React.useState(readStoredMockData)

  const setUseMockData = React.useCallback((enabled: boolean) => {
    writeStoredMockData(enabled)
    setUseMockDataState(enabled)
  }, [])

  React.useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.storageArea !== localStorage || event.key !== STORAGE_KEY) {
        return
      }

      setUseMockDataState(event.newValue === "1")
    }

    window.addEventListener("storage", handleStorageChange)

    return () => {
      window.removeEventListener("storage", handleStorageChange)
    }
  }, [])

  const value = React.useMemo(
    () => ({
      useMockData,
      setUseMockData,
      mockDataPath: appConfig.mockDataPath,
    }),
    [useMockData, setUseMockData]
  )

  return (
    <MockDataSettingsContext.Provider value={value}>
      {children}
    </MockDataSettingsContext.Provider>
  )
}

export function useMockDataSettings() {
  const context = React.useContext(MockDataSettingsContext)

  if (context === undefined) {
    throw new Error("useMockDataSettings must be used within a MockDataProvider")
  }

  return context
}

export function mockDataRequestFields(useMockData: boolean, mockDataPath: string) {
  return useMockData ? { mock_data: mockDataPath } : {}
}
