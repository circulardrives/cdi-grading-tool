export const queryKeys = {
  health: ["health"] as const,
  devices: (machineId?: string | null) =>
    ["devices", machineId ?? "local"] as const,
  machines: ["machines"] as const,
  fleetDevices: ["fleet", "devices"] as const,
  historyPages: (machineId?: string | null) =>
    ["history", "pages", machineId ?? "all"] as const,
  historyDetail: (scanId: string) => ["history", "detail", scanId] as const,
  reports: ["reports"] as const,
  // Self-test data is per bench: never mix results from two benches.
  jobs: (machineId?: string | null) => ["jobs", machineId ?? "local"] as const,
  selfTestStatus: (machineId?: string | null) =>
    ["self-test-status", machineId ?? "local"] as const,
}
