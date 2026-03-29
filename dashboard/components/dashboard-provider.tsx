"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactElement,
  type ReactNode
} from "react";

import {
  abortSelfTest,
  generateReport,
  getHealth,
  getJob,
  getJobs,
  getSelfTestStatus,
  scanDevices,
  startSelfTest,
  type HealthResponse,
  type JobResponse,
  type ReportResponse,
  type ScanResponse,
  type SelfTestStatusResponse
} from "@/lib/api";

const mockDataEnabled = process.env.NEXT_PUBLIC_CDI_USE_MOCK_DATA === "1";
const mockDataPath = process.env.NEXT_PUBLIC_CDI_MOCK_DATA_PATH?.trim() || "src/cdi_health/mock_data";

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));
const PREFERENCES_KEY = "cdi-dashboard-preferences-v1";

type ScanPayload = {
  ignore_ata: boolean;
  ignore_nvme: boolean;
  ignore_scsi: boolean;
  device?: string;
  mock_data?: string;
  mock_file?: string;
};

type ReportPayload = {
  format: "html" | "pdf";
  output_file?: string;
  ignore_ata: boolean;
  ignore_nvme: boolean;
  ignore_scsi: boolean;
  device?: string;
  mock_data?: string;
  mock_file?: string;
};

type BusyAction = "boot" | "scan" | "selftest" | "abort" | "report" | "refresh";

export type DashboardPreferences = {
  autoRefreshEnabled: boolean;
  autoRefreshSeconds: number;
  confirmAbort: boolean;
  denseTableRows: boolean;
  defaultIgnoreAta: boolean;
  defaultIgnoreNvme: boolean;
  defaultIgnoreScsi: boolean;
};

const defaultPreferences: DashboardPreferences = {
  autoRefreshEnabled: false,
  autoRefreshSeconds: 30,
  confirmAbort: true,
  denseTableRows: false,
  defaultIgnoreAta: false,
  defaultIgnoreNvme: false,
  defaultIgnoreScsi: false
};

type DashboardContextValue = {
  health: HealthResponse | null;
  scan: ScanResponse | null;
  jobs: JobResponse[];
  selfTestStatus: SelfTestStatusResponse | null;
  latestReport: ReportResponse | null;
  reportHistory: ReportResponse[];
  message: string | null;
  error: string | null;
  busy: Record<BusyAction, boolean>;
  preferences: DashboardPreferences;
  useMockData: boolean;
  mockPath: string;
  setMessage: (message: string | null) => void;
  setError: (error: string | null) => void;
  updatePreferences: (patch: Partial<DashboardPreferences>) => void;
  refreshHealth: () => Promise<HealthResponse>;
  refreshJobs: () => Promise<JobResponse[]>;
  refreshSelfTestStatus: () => Promise<SelfTestStatusResponse>;
  refreshAll: () => Promise<void>;
  runScan: (payload: ScanPayload) => Promise<ScanResponse>;
  runSelfTest: (payload: { device?: string | null; test_type: "short" | "extended"; wait: boolean }) => Promise<JobResponse>;
  runAbort: (device: string) => Promise<void>;
  runReport: (payload: ReportPayload) => Promise<ReportResponse>;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

function toErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function applyMockDataToScan(payload: ScanPayload): ScanPayload {
  if (mockDataEnabled && !payload.mock_data && !payload.mock_file) {
    return { ...payload, mock_data: mockDataPath };
  }
  return payload;
}

function applyMockDataToReport(payload: ReportPayload): ReportPayload {
  if (mockDataEnabled && !payload.mock_data && !payload.mock_file) {
    return { ...payload, mock_data: mockDataPath };
  }
  return payload;
}

export function DashboardProvider({ children }: { children: ReactNode }): ReactElement {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [selfTestStatus, setSelfTestStatus] = useState<SelfTestStatusResponse | null>(null);
  const [latestReport, setLatestReport] = useState<ReportResponse | null>(null);
  const [reportHistory, setReportHistory] = useState<ReportResponse[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<BusyAction, boolean>>({
    boot: false,
    scan: false,
    selftest: false,
    abort: false,
    report: false,
    refresh: false
  });
  const [preferences, setPreferences] = useState<DashboardPreferences>(defaultPreferences);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    try {
      const raw = window.localStorage.getItem(PREFERENCES_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as Partial<DashboardPreferences>;
      setPreferences((prev) => ({ ...prev, ...parsed }));
    } catch {
      // Ignore malformed local storage payloads.
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
  }, [preferences]);

  const updateBusy = useCallback((action: BusyAction, value: boolean) => {
    setBusy((prev) => ({ ...prev, [action]: value }));
  }, []);

  const refreshHealth = useCallback(async (): Promise<HealthResponse> => {
    const data = await getHealth();
    setHealth(data);
    return data;
  }, []);

  const refreshJobs = useCallback(async (): Promise<JobResponse[]> => {
    const data = await getJobs();
    setJobs(data);
    return data;
  }, []);

  const refreshSelfTestStatus = useCallback(async (): Promise<SelfTestStatusResponse> => {
    const data = await getSelfTestStatus();
    setSelfTestStatus(data);
    return data;
  }, []);

  const refreshAll = useCallback(async (): Promise<void> => {
    updateBusy("refresh", true);
    setError(null);
    try {
      await Promise.all([refreshHealth(), refreshJobs(), refreshSelfTestStatus()]);
      setMessage("Status refreshed");
    } catch (err) {
      setError(toErrorMessage(err, "Unable to refresh status"));
    } finally {
      updateBusy("refresh", false);
    }
  }, [refreshHealth, refreshJobs, refreshSelfTestStatus, updateBusy]);

  const runScan = useCallback(async (payload: ScanPayload): Promise<ScanResponse> => {
    updateBusy("scan", true);
    setError(null);
    setMessage(null);
    try {
      const data = await scanDevices(applyMockDataToScan(payload));
      setScan(data);
      setMessage(`Scan completed for ${data.summary.total} device(s)`);
      return data;
    } catch (err) {
      const messageText = toErrorMessage(err, "Scan failed");
      setError(messageText);
      throw new Error(messageText);
    } finally {
      updateBusy("scan", false);
    }
  }, [updateBusy]);

  const pollSelfTestJob = useCallback(
    async (jobId: string): Promise<void> => {
      for (let attempt = 0; attempt < 180; attempt += 1) {
        const job = await getJob(jobId);
        if (job.status === "completed" || job.status === "failed") {
          await Promise.all([refreshJobs(), refreshSelfTestStatus()]);
          if (job.status === "completed") {
            setMessage(`Self-test ${jobId} completed`);
          } else {
            setError(job.error ?? `Self-test ${jobId} failed`);
          }
          return;
        }
        await sleep(2000);
      }
      setError(`Timed out waiting for self-test ${jobId}`);
    },
    [refreshJobs, refreshSelfTestStatus]
  );

  const runSelfTest = useCallback(
    async (payload: { device?: string | null; test_type: "short" | "extended"; wait: boolean }): Promise<JobResponse> => {
      updateBusy("selftest", true);
      setError(null);
      setMessage(null);
      try {
        const job = await startSelfTest({
          device: payload.device && payload.device.trim() !== "" ? payload.device : null,
          test_type: payload.test_type,
          wait: payload.wait,
          poll_interval_seconds: 30,
          timeout_seconds: 14400
        });

        setMessage(`Self-test queued: ${job.job_id}`);
        await Promise.all([refreshJobs(), refreshSelfTestStatus()]);
        void pollSelfTestJob(job.job_id);
        return job;
      } catch (err) {
        const messageText = toErrorMessage(err, "Unable to start self-test");
        setError(messageText);
        throw new Error(messageText);
      } finally {
        updateBusy("selftest", false);
      }
    },
    [pollSelfTestJob, refreshJobs, refreshSelfTestStatus, updateBusy]
  );

  const runAbort = useCallback(
    async (device: string): Promise<void> => {
      updateBusy("abort", true);
      setError(null);
      setMessage(null);
      try {
        await abortSelfTest(device);
        setMessage(`Abort signal sent for ${device}`);
        await refreshSelfTestStatus();
      } catch (err) {
        const messageText = toErrorMessage(err, "Unable to abort self-test");
        setError(messageText);
        throw new Error(messageText);
      } finally {
        updateBusy("abort", false);
      }
    },
    [refreshSelfTestStatus, updateBusy]
  );

  const runReport = useCallback(async (payload: ReportPayload): Promise<ReportResponse> => {
    updateBusy("report", true);
    setError(null);
    setMessage(null);
    try {
      const report = await generateReport(applyMockDataToReport(payload));
      setLatestReport(report);
      setReportHistory((prev) => [report, ...prev].slice(0, 20));
      setMessage(`Report generated: ${report.output_file}`);
      return report;
    } catch (err) {
      const messageText = toErrorMessage(err, "Report generation failed");
      setError(messageText);
      throw new Error(messageText);
    } finally {
      updateBusy("report", false);
    }
  }, [updateBusy]);

  const updatePreferences = useCallback((patch: Partial<DashboardPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...patch }));
  }, []);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async (): Promise<void> => {
      updateBusy("boot", true);
      setError(null);
      try {
        const [healthData, jobsData, statusData, scanData] = await Promise.all([
          getHealth(),
          getJobs(),
          getSelfTestStatus(),
          scanDevices(
            applyMockDataToScan({
              ignore_ata: preferences.defaultIgnoreAta,
              ignore_nvme: preferences.defaultIgnoreNvme,
              ignore_scsi: preferences.defaultIgnoreScsi
            })
          )
        ]);

        if (cancelled) {
          return;
        }

        setHealth(healthData);
        setJobs(jobsData);
        setSelfTestStatus(statusData);
        setScan(scanData);
      } catch (err) {
        if (!cancelled) {
          setError(toErrorMessage(err, "Initial dashboard load failed"));
        }
      } finally {
        if (!cancelled) {
          updateBusy("boot", false);
        }
      }
    };

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [preferences.defaultIgnoreAta, preferences.defaultIgnoreNvme, preferences.defaultIgnoreScsi, updateBusy]);

  useEffect(() => {
    if (!preferences.autoRefreshEnabled) {
      return;
    }

    const seconds = Math.max(15, Number(preferences.autoRefreshSeconds) || 30);
    const timer = window.setInterval(() => {
      void Promise.all([refreshHealth(), refreshJobs(), refreshSelfTestStatus()]);
    }, seconds * 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [preferences.autoRefreshEnabled, preferences.autoRefreshSeconds, refreshHealth, refreshJobs, refreshSelfTestStatus]);

  const value = useMemo<DashboardContextValue>(
    () => ({
      health,
      scan,
      jobs,
      selfTestStatus,
      latestReport,
      reportHistory,
      message,
      error,
      busy,
      preferences,
      useMockData: mockDataEnabled,
      mockPath: mockDataPath,
      setMessage,
      setError,
      updatePreferences,
      refreshHealth,
      refreshJobs,
      refreshSelfTestStatus,
      refreshAll,
      runScan,
      runSelfTest,
      runAbort,
      runReport
    }),
    [
      health,
      scan,
      jobs,
      selfTestStatus,
      latestReport,
      reportHistory,
      message,
      error,
      busy,
      preferences,
      updatePreferences,
      refreshHealth,
      refreshJobs,
      refreshSelfTestStatus,
      refreshAll,
      runScan,
      runSelfTest,
      runAbort,
      runReport
    ]
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
}
