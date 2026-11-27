import type {
  AuditLogItem,
  AuthStatus,
  BacktestReplayReport,
  CheckpointRestoreResponse,
  CheckpointsListResponse,
  CopilotResult,
  CTPCommitResponse,
  CTPQuoteRequest,
  CTPQuoteResult,
  Currency,
  DecisionCheckpoint,
  FinancialReport,
  GuidedSetupRequest,
  GuidedSetupResponse,
  Lang,
  PlantDataset,
  PlantWorkspace,
  ProductionOrder,
  RiskRadarReport,
  SolveResult,
  SolverConfig,
  ValidationReport,
  WhatsAppDispatchRequest,
  WhatsAppDispatchResponse,
  WorkforceCallout,
  WorkforceResult,
  WorkspaceSummary,
} from "./types";

// Default to same-origin `/api/*` (proxied by Next.js rewrites to BACKEND_INTERNAL_URL)
// so HttpOnly SameSite=Lax auth cookies work seamlessly in both local dev and hosted HTTPS.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/+$/, "");

async function handleJson<T>(res: Response): Promise<T> {
  // Read the response body stream strictly once to avoid
  // "Failed to execute 'text' on 'Response': body stream already read".
  const raw = await res.text();
  let parsed: unknown = undefined;
  if (raw) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = undefined;
    }
  }

  if (!res.ok) {
    let detail = "";
    if (parsed && typeof parsed === "object" && "detail" in parsed) {
      const d = (parsed as { detail: unknown }).detail;
      detail = typeof d === "string" ? d : JSON.stringify(d);
    } else if (parsed !== undefined) {
      detail = typeof parsed === "string" ? parsed : JSON.stringify(parsed);
    } else {
      const trimmed = raw.trim();
      // Avoid dumping raw HTML error pages from Cloudflare/Render into toast notifications
      detail = /^<!DOCTYPE|^<html/i.test(trimmed) ? "" : trimmed.slice(0, 300);
    }

    if (res.status === 502 || res.status === 503 || res.status === 504) {
      const wakeMsg = `Server is waking up (HTTP ${res.status}). Please retry in a few seconds.`;
      throw new Error(detail ? `${wakeMsg} (${detail})` : wakeMsg);
    }

    if (res.status === 508) {
      throw new Error(
        detail ||
          `HTTP 508 Loop Detected — check BACKEND_INTERNAL_URL proxy configuration.`
      );
    }

    throw new Error(detail ? `${detail} (HTTP ${res.status})` : `HTTP ${res.status}`);
  }

  if (parsed !== undefined) {
    return parsed as T;
  }
  throw new Error(`Invalid JSON response from server (HTTP ${res.status})`);
}

// --------------------------------------------------------------------------------------------
// Auth & Hosted Sandbox Endpoints
// --------------------------------------------------------------------------------------------
export async function fetchAuthMe(): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    cache: "no-store",
    credentials: "include",
  });
  return handleJson<AuthStatus>(res);
}

export async function loginWithPasscodeApi(passcode: string): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ passcode, instant_demo: false }),
  });
  return handleJson<AuthStatus>(res);
}

export async function loginInstantDemoApi(): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ passcode: "", instant_demo: true }),
  });
  return handleJson<AuthStatus>(res);
}

export async function logoutApi(): Promise<{ authenticated: boolean; logged_out: boolean }> {
  const res = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  return handleJson(res);
}

export async function resetSandboxApi(): Promise<{
  reset: boolean;
  session_id: string;
  dataset: PlantDataset;
  default_config: SolverConfig;
}> {
  const res = await fetch(`${API_BASE}/api/sandbox/reset`, {
    method: "POST",
    credentials: "include",
  });
  return handleJson(res);
}

// --------------------------------------------------------------------------------------------
// Operational Endpoints
// --------------------------------------------------------------------------------------------
export async function fetchDemoData(): Promise<{ dataset: PlantDataset; default_config: SolverConfig }> {
  const res = await fetch(`${API_BASE}/api/demo-data`, {
    cache: "no-store",
    credentials: "include",
  });
  return handleJson(res);
}

export function getTemplateDownloadUrl(sample = true): string {
  return `${API_BASE}/api/template.xlsx?sample=${sample ? "true" : "false"}`;
}

export async function validatePlantJson(
  dataset: PlantDataset,
  config?: SolverConfig
): Promise<{ dataset: PlantDataset; report: ValidationReport }> {
  const res = await fetch(`${API_BASE}/api/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ dataset, config }),
  });
  return handleJson(res);
}

export async function validateExcelFile(
  file: File,
  config?: SolverConfig
): Promise<{ dataset: PlantDataset; report: ValidationReport }> {
  const form = new FormData();
  form.append("file", file);
  if (config) {
    form.append("config", JSON.stringify(config));
  }
  const res = await fetch(`${API_BASE}/api/validate`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  return handleJson(res);
}

export async function solvePlantScheduleApi(
  dataset: PlantDataset | null,
  config: SolverConfig
): Promise<SolveResult> {
  const res = await fetch(`${API_BASE}/api/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ dataset, config }),
  });
  return handleJson(res);
}

export async function solveWorkforceApi(
  dataset: PlantDataset,
  config: SolverConfig,
  result?: SolveResult | null,
  workerCallouts?: WorkforceCallout[]
): Promise<{ workforce: WorkforceResult | null; financials: FinancialReport; risk_radar?: RiskRadarReport | null }> {
  const res = await fetch(`${API_BASE}/api/workforce/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      dataset,
      config,
      result: result ?? undefined,
      worker_callouts: workerCallouts ?? [],
    }),
  });
  return handleJson(res);
}

export async function exportDatasetExcel(dataset: PlantDataset): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export-dataset.xlsx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(dataset),
  });
  if (!res.ok) {
    throw new Error(`Dataset export failed (HTTP ${res.status})`);
  }
  return res.blob();
}

export async function exportBriefExcel(
  runId: string | null,
  currency: Currency,
  result?: SolveResult | null,
  dataset?: PlantDataset | null,
  config?: SolverConfig | null
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export-brief.xlsx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      run_id: runId,
      result: result ?? undefined,
      dataset: dataset ?? undefined,
      config: config ?? undefined,
      currency,
    }),
  });
  if (!res.ok) {
    throw new Error(`Export failed (HTTP ${res.status})`);
  }
  return res.blob();
}

export async function fetchAuditLog(limit = 20): Promise<AuditLogItem[]> {
  const res = await fetch(`${API_BASE}/api/audit-log?limit=${limit}`, {
    cache: "no-store",
    credentials: "include",
  });
  const data = await handleJson<{ runs: AuditLogItem[] }>(res);
  return data.runs;
}

export async function fetchAuditRun(runId: string): Promise<SolveResult> {
  const res = await fetch(`${API_BASE}/api/audit-log/${runId}`, {
    cache: "no-store",
    credentials: "include",
  });
  return handleJson(res);
}

export async function askCopilotApi(
  prompt: string,
  dataset?: PlantDataset | null,
  config?: SolverConfig | null,
  currentResult?: SolveResult | null,
  language: Lang = "en"
): Promise<CopilotResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25000);

  try {
    const res = await fetch(`${API_BASE}/api/copilot/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        prompt,
        dataset,
        config,
        current_result: currentResult,
        language,
      }),
      signal: controller.signal,
    });
    return await handleJson<CopilotResult>(res);
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Copilot request timed out after 25 seconds. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchWorkspaces(): Promise<WorkspaceSummary[]> {
  const res = await fetch(`${API_BASE}/api/workspaces`, {
    cache: "no-store",
    credentials: "include",
  });
  const data = await handleJson<{ workspaces: WorkspaceSummary[] }>(res);
  return data.workspaces;
}

export async function saveWorkspaceApi(payload: {
  workspace_id: string;
  name: string;
  dataset: PlantDataset;
  config?: SolverConfig;
}): Promise<PlantWorkspace> {
  const res = await fetch(`${API_BASE}/api/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleJson<PlantWorkspace>(res);
}

export async function getWorkspaceApi(workspaceId: string): Promise<PlantWorkspace> {
  const res = await fetch(`${API_BASE}/api/workspaces/${encodeURIComponent(workspaceId)}`, {
    cache: "no-store",
    credentials: "include",
  });
  return handleJson<PlantWorkspace>(res);
}

export async function deleteWorkspaceApi(
  workspaceId: string
): Promise<{ deleted: boolean; workspace_id: string }> {
  const res = await fetch(`${API_BASE}/api/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: "DELETE",
    credentials: "include",
  });
  return handleJson<{ deleted: boolean; workspace_id: string }>(res);
}

// --------------------------------------------------------------------------------------------
// v1.3 Decision Intelligence Upgrade Endpoints (Backtest, Guided Onboarding, Integration Exports)
// --------------------------------------------------------------------------------------------
export function getBacktestTemplateUrl(format: "csv" | "xlsx" = "csv"): string {
  return `${API_BASE}/api/backtest/template?format=${format}`;
}

export async function runBacktestSampleApi(
  currency: Currency,
  dataset?: PlantDataset | null,
  config?: SolverConfig | null
): Promise<BacktestReplayReport> {
  const res = await fetch(`${API_BASE}/api/backtest/replay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      mode: "sample_30day_log",
      currency,
      dataset: dataset ?? undefined,
      config: config ?? undefined,
    }),
  });
  return handleJson<BacktestReplayReport>(res);
}

export async function uploadBacktestFileApi(
  file: File,
  currency: Currency,
  dataset?: PlantDataset | null,
  config?: SolverConfig | null
): Promise<BacktestReplayReport> {
  const form = new FormData();
  form.append("file", file);
  form.append("currency", currency);
  if (dataset) {
    form.append("dataset", JSON.stringify(dataset));
  }
  if (config) {
    form.append("config", JSON.stringify(config));
  }
  const res = await fetch(`${API_BASE}/api/backtest/replay`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  return handleJson<BacktestReplayReport>(res);
}

export async function generateGuidedWorkspaceApi(
  payload: GuidedSetupRequest
): Promise<GuidedSetupResponse> {
  const res = await fetch(`${API_BASE}/api/onboarding/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleJson<GuidedSetupResponse>(res);
}

export async function downloadIntegrationExportApi(
  format: "xlsx" | "csv" | "json",
  runId?: string | null,
  currency?: Currency
): Promise<Blob> {
  const endpoint =
    format === "xlsx"
      ? "schedule.xlsx"
      : format === "csv"
        ? "schedule.csv"
        : "erp-payload.json";
  const params = new URLSearchParams();
  if (runId) params.set("run_id", runId);
  if (currency) params.set("currency", currency);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const res = await fetch(`${API_BASE}/api/export/${endpoint}${qs}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Export ${endpoint} failed (HTTP ${res.status})`);
  }
  return res.blob();
}

// --------------------------------------------------------------------------------------------
// v1.4 Persistence Checkpoints, CTP Rush-Order Quoter & WhatsApp Shift Dispatch Endpoints
// --------------------------------------------------------------------------------------------
export async function fetchCheckpointsApi(seedIfEmpty = true): Promise<CheckpointsListResponse> {
  const res = await fetch(
    `${API_BASE}/api/checkpoints?limit=25&seed_if_empty=${seedIfEmpty ? "true" : "false"}`,
    {
      cache: "no-store",
      credentials: "include",
    }
  );
  return handleJson<CheckpointsListResponse>(res);
}

export async function createCheckpointApi(payload: {
  trigger_source: string;
  title_en: string;
  title_ar: string;
  dataset?: PlantDataset | null;
  config?: SolverConfig | null;
  result?: SolveResult | null;
}): Promise<{
  storage_backend: "postgres" | "sqlite_fallback";
  checkpoint: DecisionCheckpoint;
  checkpoints: DecisionCheckpoint[];
}> {
  const res = await fetch(`${API_BASE}/api/checkpoints`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleJson(res);
}

export async function restoreCheckpointApi(
  checkpointId: string
): Promise<CheckpointRestoreResponse> {
  const res = await fetch(
    `${API_BASE}/api/checkpoints/${encodeURIComponent(checkpointId)}/restore`,
    {
      method: "POST",
      credentials: "include",
    }
  );
  return handleJson<CheckpointRestoreResponse>(res);
}

export async function quoteCtpRushOrderApi(
  payload: CTPQuoteRequest
): Promise<CTPQuoteResult> {
  const res = await fetch(`${API_BASE}/api/quote/ctp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleJson<CTPQuoteResult>(res);
}

export async function commitCtpRushOrderApi(payload: {
  candidate_order: ProductionOrder;
  dataset?: PlantDataset | null;
  config?: SolverConfig | null;
  workspace_id?: string;
}): Promise<CTPCommitResponse> {
  const res = await fetch(`${API_BASE}/api/quote/ctp/commit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleJson<CTPCommitResponse>(res);
}

export async function generateWhatsAppDispatchApi(
  payload: WhatsAppDispatchRequest
): Promise<WhatsAppDispatchResponse> {
  const res = await fetch(`${API_BASE}/api/dispatch/whatsapp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleJson<WhatsAppDispatchResponse>(res);
}
