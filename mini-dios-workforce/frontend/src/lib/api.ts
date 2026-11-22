import type {
  AuditLogItem,
  AuthStatus,
  CopilotResult,
  Currency,
  FinancialReport,
  Lang,
  PlantDataset,
  PlantWorkspace,
  RiskRadarReport,
  SolveResult,
  SolverConfig,
  ValidationReport,
  WorkforceCallout,
  WorkforceResult,
  WorkspaceSummary,
} from "./types";

// Default to same-origin `/api/*` (proxied by Next.js rewrites to BACKEND_INTERNAL_URL)
// so HttpOnly SameSite=Lax auth cookies work seamlessly in both local dev and hosted HTTPS.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/+$/, "");

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || JSON.stringify(err);
    } catch {
      msg = await res.text();
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
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
