const apiBaseUrl = import.meta.env.VITE_CDI_API_BASE_URL ?? "/api/cdi"
const mockDataPath =
  import.meta.env.VITE_CDI_MOCK_DATA_PATH ?? "src/cdi_health/mock_data"
const apiHost =
  import.meta.env.VITE_CDI_API_PROXY_TARGET ?? "http://127.0.0.1:8844"
const discoverSubnet = import.meta.env.VITE_CDI_DISCOVER_SUBNET ?? ""

export const appConfig = {
  apiBaseUrl,
  mockDataPath,
  apiHost,
  discoverSubnet,
} as const
