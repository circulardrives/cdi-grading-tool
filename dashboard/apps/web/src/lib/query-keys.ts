export const queryKeys = {
  health: ["health"] as const,
  devices: (machineId?: string | null) =>
    ["devices", machineId ?? "local"] as const,
  machines: ["machines"] as const,
  fleetDevices: ["fleet", "devices"] as const,
  historyPages: (machineId?: string | null) =>
    ["history", "pages", machineId ?? "all"] as const,
  historyDetail: (scanId: string) => ["history", "detail", scanId] as const,
  jobs: ["jobs"] as const,
  selfTestStatus: ["self-test-status"] as const,
}
