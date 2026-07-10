export const queryKeys = {
  health: ["health"] as const,
  devices: (machineId?: string | null) =>
    ["devices", machineId ?? "local"] as const,
  machines: ["machines"] as const,
  jobs: ["jobs"] as const,
  selfTestStatus: ["self-test-status"] as const,
}
