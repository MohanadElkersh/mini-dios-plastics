"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  deleteWorkspaceApi,
  exportBriefExcel,
  exportDatasetExcel,
  fetchAuditLog,
  fetchAuditRun,
  fetchAuthMe,
  fetchDemoData,
  fetchWorkspaces,
  getWorkspaceApi,
  loginInstantDemoApi,
  loginWithPasscodeApi,
  logoutApi,
  resetSandboxApi,
  saveWorkspaceApi,
  solvePlantScheduleApi,
  solveWorkforceApi,
  validateExcelFile,
  validatePlantJson,
} from "./api";
import type {
  AuditLogItem,
  AuthStatus,
  Currency,
  FactoryWorker,
  Lang,
  MachineBreakdown,
  Mold,
  MoldPmLock,
  PinnedScenario,
  PinnedSlotId,
  PlantDataset,
  PlantPhysicsConfig,
  PlantWorkspace,
  PressMachine,
  ProductionOrder,
  ResinCode,
  ResinShortage,
  ResinStock,
  ScenarioDisruptions,
  SolveResult,
  SolverConfig,
  ValidationReport,
  ViewTab,
  WorkforceConfig,
  WorkspaceSummary,
} from "./types";

export type QuickModalType = "press" | "mold" | "resin" | "order" | "physics";
export type StudioSubTab = "presses" | "molds" | "resins" | "orders" | "physics";

const STUDIO_STORAGE_KEY = "mini_dios_plastics_studio_v1";
const PINNED_STORAGE_KEY = "mini_dios_plastics_pinned_v1";
const PIN_SLOTS: PinnedSlotId[] = ["A", "B", "C"];

function storageKeyForSession(base: string, sessionId?: string | null): string {
  if (!sessionId || sessionId === "local") return base;
  return `${base}_${sessionId}`;
}

function deriveScenarioLabel(cfg: SolverConfig, lang: Lang): string {
  const sc = cfg.scenarios;
  const isAr = lang === "ar";
  if (sc.machine_breakdowns.length > 0) {
    const bd = sc.machine_breakdowns[0];
    return isAr
      ? `عطل ${bd.machine_id} (${bd.duration_hrs}س)`
      : `${bd.machine_id} Down ${bd.duration_hrs}h`;
  }
  if (sc.resin_shortages.length > 0) {
    const rs = sc.resin_shortages[0];
    return isAr
      ? `صدمة خام ${rs.resin_code}`
      : `${rs.resin_code} Supply Shock`;
  }
  if (sc.rush_orders.length > 0) {
    return isAr
      ? `أمر عاجل (+${sc.rush_orders.length})`
      : `Rush Order (+${sc.rush_orders.length})`;
  }
  if (sc.mold_pm_locks.length > 0) {
    return isAr
      ? `صيانة ${sc.mold_pm_locks[0].mold_id}`
      : `Mold ${sc.mold_pm_locks[0].mold_id} PM Lock`;
  }
  if (cfg.w_changeover_scrap >= 55) {
    return isAr ? "أقل هالك وتنظيف" : "Min Purge & Scrap";
  }
  if (cfg.w_otif >= 55) {
    return isAr ? "صفر تأخير تصدير" : "Max Export OTIF";
  }
  if (cfg.w_energy_cost >= 45) {
    return isAr ? "توفير الكهرباء" : "Low Energy Cost";
  }
  if (cfg.ramadan_shift_mode) {
    return isAr ? "خطة ورديات رمضان 6س" : "Ramadan 6h Plan";
  }
  if (cfg.avoid_peak_tariff_hrs) {
    return isAr ? "تجنب ذروة الكهرباء" : "Peak Tariff Avoid";
  }
  return isAr ? "الخطة المتوازنة" : "Balanced Plan";
}

const EMPTY_SCENARIOS: ScenarioDisruptions = {
  machine_breakdowns: [],
  resin_shortages: [],
  mold_pm_locks: [],
  rush_orders: [],
  allow_regrind_override_pct: null,
};

export const DEFAULT_PHYSICS: PlantPhysicsConfig = {
  horizon_hrs: 168,
  light_to_dark_purge_mins: 25,
  light_to_dark_purge_kg: 4.0,
  dark_to_light_purge_mins: 135,
  dark_to_light_purge_kg: 32.0,
  incompatible_resin_purge_mins: 180,
  incompatible_resin_purge_kg: 48.0,
  energy_tariff_per_kwh: 0.32,
  peak_tariff_multiplier: 1.4,
  peak_start_hr: 13,
  peak_end_hr: 17,
  holding_cost_per_kg_per_day: 0.05,
  ramadan_shift_hours: 6,
  max_solve_seconds: 5.0,
  weekly_fixed_overhead: 18500,
  scrap_regrind_recovery_pct: 10,
  annual_operating_weeks: 50,
};

export const DEFAULT_WORKFORCE: WorkforceConfig = {
  shift_length_hrs: 8,
  standard_weekly_hours: 40,
  min_rest_hours: 11,
  min_consecutive_days_off: 1,
  presses_per_operator: 2,
  w_labor_cost: 50,
  w_coverage: 35,
  w_fairness: 15,
};

const DEFAULT_CONFIG: SolverConfig = {
  w_changeover_scrap: 35,
  w_otif: 35,
  w_energy_cost: 15,
  w_working_capital: 15,
  currency: "SAR",
  fx_egp_per_sar: 13.0,
  energy_tariff_per_kwh: 0.32,
  avoid_peak_tariff_hrs: false,
  ramadan_shift_mode: false,
  autonomous_pm_window: false,
  max_solve_seconds: 5.0,
  random_seed: 42,
  num_workers: 8,
  physics: DEFAULT_PHYSICS,
  workforce: DEFAULT_WORKFORCE,
  scenarios: EMPTY_SCENARIOS,
};

function normalizeConfig(raw?: Partial<SolverConfig> | null): SolverConfig {
  const physics: PlantPhysicsConfig = {
    ...DEFAULT_PHYSICS,
    ...(raw?.physics ?? {}),
  };
  const workforce: WorkforceConfig = {
    ...DEFAULT_WORKFORCE,
    ...(raw?.workforce ?? {}),
  };
  if (raw?.energy_tariff_per_kwh !== undefined && raw?.physics?.energy_tariff_per_kwh === undefined) {
    physics.energy_tariff_per_kwh = raw.energy_tariff_per_kwh;
  }
  if (raw?.max_solve_seconds !== undefined && raw?.physics?.max_solve_seconds === undefined) {
    physics.max_solve_seconds = Math.min(30, Math.max(1, raw.max_solve_seconds));
  }
  return {
    ...DEFAULT_CONFIG,
    ...(raw ?? {}),
    energy_tariff_per_kwh: physics.energy_tariff_per_kwh,
    max_solve_seconds: physics.max_solve_seconds,
    physics,
    workforce,
    scenarios: {
      ...EMPTY_SCENARIOS,
      ...(raw?.scenarios ?? {}),
    },
  };
}

function countDatasetAndPhysicsDiffs(
  ds: PlantDataset | null,
  cfg: SolverConfig,
  baseDs: PlantDataset | null,
  baseCfg: SolverConfig
): number {
  if (!ds || !baseDs) return 0;
  let diffs = 0;

  const diffByKey = <T,>(curr: T[], base: T[], getKey: (item: T) => string) => {
    const bMap = new Map(base.map((item) => [getKey(item), JSON.stringify(item)]));
    const cMap = new Map(curr.map((item) => [getKey(item), JSON.stringify(item)]));
    for (const [k, v] of cMap.entries()) {
      if (bMap.get(k) !== v) diffs += 1;
    }
    for (const k of bMap.keys()) {
      if (!cMap.has(k)) diffs += 1;
    }
  };

  diffByKey(ds.presses, baseDs.presses, (p) => p.machine_id);
  diffByKey(ds.molds, baseDs.molds, (m) => m.mold_id);
  diffByKey(ds.resins, baseDs.resins, (r) => r.resin_code);
  diffByKey(ds.orders, baseDs.orders, (o) => o.order_id);
  diffByKey(ds.workers ?? [], baseDs.workers ?? [], (w) => w.worker_id);

  (Object.keys(DEFAULT_PHYSICS) as (keyof PlantPhysicsConfig)[]).forEach((k) => {
    if (cfg.physics[k] !== baseCfg.physics[k]) diffs += 1;
  });
  if (cfg.fx_egp_per_sar !== baseCfg.fx_egp_per_sar) diffs += 1;

  return diffs;
}

interface AppState {
  lang: Lang;
  setLang: (l: Lang) => void;
  currency: Currency;
  setCurrency: (c: Currency) => void;
  activeView: ViewTab;
  setActiveView: (v: ViewTab) => void;
  dataset: PlantDataset | null;
  validation: ValidationReport | null;
  config: SolverConfig;
  setConfig: React.Dispatch<React.SetStateAction<SolverConfig>>;
  result: SolveResult | null;
  setResult: React.Dispatch<React.SetStateAction<SolveResult | null>>;
  setValidation: React.Dispatch<React.SetStateAction<ValidationReport | null>>;
  auditRuns: AuditLogItem[];
  refreshAudit: () => Promise<void>;
  loading: boolean;
  exporting: boolean;
  error: string | null;
  clearError: () => void;
  copilotOpen: boolean;
  setCopilotOpen: (open: boolean) => void;
  copilotDraftPrompt: string | null;
  setCopilotDraftPrompt: (prompt: string | null) => void;
  openCopilotWithPrompt: (prompt: string) => void;
  modifiedCount: number;
  loadDemo: (autoSolve?: boolean) => Promise<void>;
  uploadWorkbook: (file: File) => Promise<void>;
  runSolve: (overrideConfig?: SolverConfig, overrideDataset?: PlantDataset | null) => Promise<SolveResult | null>;
  validateAndSolveToView: (targetView?: ViewTab) => Promise<void>;
  toggleRamadanMode: () => Promise<void>;
  togglePeakTariffMode: () => Promise<void>;
  toggleAutonomousPmMode: () => Promise<void>;
  addBreakdown: (bd: MachineBreakdown) => void;
  removeBreakdown: (idx: number) => void;
  addResinShortage: (rs: ResinShortage) => void;
  removeResinShortage: (idx: number) => void;
  addMoldPmLock: (lk: MoldPmLock) => void;
  removeMoldPmLock: (idx: number) => void;
  addRushOrder: (ro: ProductionOrder) => void;
  removeRushOrder: (idx: number) => void;
  setRegrindOverride: (pct: number | null) => void;
  clearAllScenarios: () => Promise<void>;
  applyCopilotScenario: (nextCfg: SolverConfig, nextRes?: SolveResult | null) => void;
  exportExecutiveBrief: () => Promise<void>;
  exportStudioDataset: () => Promise<void>;
  loadAuditRunById: (runId: string) => Promise<void>;
  // Workspaces & Hub actions
  workspaces: WorkspaceSummary[];
  activeWorkspaceId: string;
  loadWorkspaces: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  saveCurrentWorkspaceAs: (name: string) => Promise<void>;
  deleteWorkspace: (workspaceId: string) => Promise<void>;
  createNewBlankPlant: () => void;
  resetCurrentPlantToDemo: () => Promise<void>;
  resetMoldShots: (moldId: string) => void;
  // In-Dashboard Executive Brief Modal
  briefModalOpen: boolean;
  setBriefModalOpen: (open: boolean) => void;
  // Quick-Add / Quick-Edit Modal state
  activeQuickModal: QuickModalType | null;
  quickModalItem: any;
  openQuickModal: (type: QuickModalType, item?: any) => void;
  closeQuickModal: () => void;
  // Studio Sub-Tab navigation
  studioSubTab: StudioSubTab;
  setStudioSubTab: (tab: StudioSubTab) => void;
  navigateToStudioSubTab: (tab: StudioSubTab) => void;
  // Studio CRUD & Profile actions
  upsertPress: (press: PressMachine, originalId?: string) => void;
  deletePress: (machineId: string) => void;
  upsertMold: (mold: Mold, originalId?: string) => void;
  deleteMold: (moldId: string) => void;
  upsertResin: (resin: ResinStock, originalCode?: string) => void;
  deleteResin: (resinCode: ResinCode) => void;
  upsertOrder: (order: ProductionOrder, originalId?: string) => void;
  deleteOrder: (orderId: string) => void;
  updatePhysics: (patch: Partial<PlantPhysicsConfig>) => void;
  importStudioProfile: (profile: { dataset: PlantDataset; config?: Partial<SolverConfig> }) => Promise<void>;
  // Tab 6 Workforce & Shifts actions
  workforceLoading: boolean;
  upsertWorker: (worker: FactoryWorker, originalId?: string) => void;
  deleteWorker: (workerId: string) => void;
  duplicateWorker: (workerId: string) => void;
  toggleWorkerSick: (workerId: string) => void;
  toggleWorkerLeaveDay: (workerId: string, day: number) => void;
  updateWorkforceConfig: (patch: Partial<WorkforceConfig>) => void;
  reOptimizeShifts: (overrideConfig?: SolverConfig, overrideDataset?: PlantDataset | null) => Promise<void>;
  // Part 1: Boardroom Pin & Compare (A / B / C)
  pinnedScenarios: PinnedScenario[];
  pinScenario: (opts?: {
    label?: string;
    replaceSlot?: PinnedSlotId;
    config?: SolverConfig;
    result?: SolveResult;
    dataset?: PlantDataset;
  }) => PinnedSlotId | null;
  renamePinnedScenario: (slot: PinnedSlotId, label: string) => void;
  removePinnedScenario: (slot: PinnedSlotId) => void;
  clearPinnedScenarios: () => void;
  promotePinnedScenario: (slot: PinnedSlotId) => void;
  // Part 2: Hosted Demo Auth Gate & Session Sandbox
  auth: AuthStatus;
  authChecked: boolean;
  loginWithPasscode: (passcode: string) => Promise<void>;
  loginInstantDemo: () => Promise<void>;
  logout: () => Promise<void>;
  resetHostedSandbox: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  const [currency, setCurrencyState] = useState<Currency>("SAR");
  const [activeView, setActiveView] = useState<ViewTab>("scope");
  const [dataset, setDataset] = useState<PlantDataset | null>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [config, setConfig] = useState<SolverConfig>(DEFAULT_CONFIG);
  const [result, setResult] = useState<SolveResult | null>(null);
  const [auditRuns, setAuditRuns] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [workforceLoading, setWorkforceLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotDraftPrompt, setCopilotDraftPrompt] = useState<string | null>(null);
  const openCopilotWithPrompt = useCallback((prompt: string) => {
    setCopilotDraftPrompt(prompt);
    setCopilotOpen(true);
  }, []);
  const [baselineSnapshot, setBaselineSnapshot] = useState<{
    dataset: PlantDataset | null;
    config: SolverConfig;
  }>({ dataset: null, config: DEFAULT_CONFIG });

  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([
    {
      workspace_id: "default",
      name: "Delta & Riyadh Polymer Packaging Plant",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string>("default");
  const [briefModalOpen, setBriefModalOpen] = useState(false);
  const [activeQuickModal, setActiveQuickModal] = useState<QuickModalType | null>(null);
  const [quickModalItem, setQuickModalItem] = useState<any>(null);
  const [studioSubTab, setStudioSubTab] = useState<StudioSubTab>("presses");
  const [pinnedScenarios, setPinnedScenarios] = useState<PinnedScenario[]>([]);
  const [auth, setAuth] = useState<AuthStatus>({
    auth_enabled: false,
    authenticated: false,
    client_label: null,
    session_id: null,
    instant_demo_enabled: false,
  });
  const [authChecked, setAuthChecked] = useState(false);

  const initializedRef = useRef(false);
  const readyForPersistRef = useRef(false);
  const workspaceSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const setCurrency = useCallback((nextCur: Currency) => {
    setCurrencyState(nextCur);
    setConfig((prev) => ({ ...prev, currency: nextCur }));
  }, []);

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);

  const refreshAudit = useCallback(async () => {
    try {
      const runs = await fetchAuditLog(15);
      setAuditRuns(runs);
    } catch {
      // Non-fatal while backend warms up
    }
  }, []);

  const runSolve = useCallback(
    async (overrideConfig?: SolverConfig, overrideDataset?: PlantDataset | null): Promise<SolveResult | null> => {
      const cfg = normalizeConfig(overrideConfig ?? config);
      const ds = overrideDataset !== undefined ? overrideDataset : dataset;
      setLoading(true);
      setError(null);
      try {
        const res = await solvePlantScheduleApi(ds, { ...cfg, currency });
        setResult(res);
        setValidation(res.validation);
        await refreshAudit();
        return res;
      } catch (err) {
        setError(err instanceof Error ? err.message : "CP-SAT optimization failed");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [config, currency, dataset, refreshAudit]
  );

  const loadDemo = useCallback(
    async (autoSolve = true) => {
      setLoading(true);
      setError(null);
      try {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(storageKeyForSession(STUDIO_STORAGE_KEY, sessionIdRef.current));
        }
        const { dataset: demoDs, default_config } = await fetchDemoData();
        const nextCfg = normalizeConfig({ ...default_config, currency });
        setDataset(demoDs);
        setConfig(nextCfg);
        setBaselineSnapshot({ dataset: demoDs, config: nextCfg });
        if (autoSolve) {
          const solved = await solvePlantScheduleApi(demoDs, nextCfg);
          setResult(solved);
          setValidation(solved.validation);
        } else {
          const { report } = await validatePlantJson(demoDs, nextCfg);
          setValidation(report);
        }
        readyForPersistRef.current = true;
        await refreshAudit();
        void loadWorkspaces();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load demo plant dataset");
      } finally {
        setLoading(false);
      }
    },
    [currency, refreshAudit]
  );

  const bootstrapSessionData = useCallback(
    async (sid: string | null) => {
      sessionIdRef.current = sid;

      // Restore pinned scenarios for this session
      if (typeof window !== "undefined") {
        try {
          const rawPinned = window.localStorage.getItem(storageKeyForSession(PINNED_STORAGE_KEY, sid));
          if (rawPinned) {
            const parsedPinned = JSON.parse(rawPinned);
            if (Array.isArray(parsedPinned)) {
              setPinnedScenarios(parsedPinned.slice(0, 3) as PinnedScenario[]);
            }
          } else {
            setPinnedScenarios([]);
          }
        } catch {
          setPinnedScenarios([]);
        }
      }

      let saved: { dataset: PlantDataset; config: SolverConfig } | null = null;
      if (typeof window !== "undefined") {
        try {
          const raw = window.localStorage.getItem(storageKeyForSession(STUDIO_STORAGE_KEY, sid));
          if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed?.dataset?.presses && parsed?.dataset?.molds && parsed?.dataset?.resins && parsed?.dataset?.orders) {
              saved = {
                dataset: parsed.dataset as PlantDataset,
                config: normalizeConfig(parsed.config),
              };
            }
          }
        } catch {
          saved = null;
        }
      }

      if (!saved) {
        await loadDemo(true);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        let restoredDs = saved.dataset;
        try {
          const { dataset: demoDs, default_config } = await fetchDemoData();
          setBaselineSnapshot({ dataset: demoDs, config: normalizeConfig(default_config) });
          if (restoredDs.workers === undefined && restoredDs.name === demoDs.name && demoDs.workers) {
            restoredDs = { ...restoredDs, workers: demoDs.workers };
          }
        } catch {
          // Non-fatal
        }

        setDataset(restoredDs);
        setConfig(saved.config);
        setCurrencyState(saved.config.currency);
        const { report } = await validatePlantJson(restoredDs, saved.config);
        setValidation(report);
        if (report.ready) {
          const solved = await solvePlantScheduleApi(restoredDs, saved.config);
          setResult(solved);
          setValidation(solved.validation);
        }
        readyForPersistRef.current = true;
        await refreshAudit();
        void loadWorkspaces();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to restore saved Studio plant state");
      } finally {
        setLoading(false);
      }
    },
    [loadDemo, refreshAudit]
  );

  // Initial mount: check auth status first, then bootstrap workspace if authorized
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const init = async () => {
      try {
        const status = await fetchAuthMe();
        setAuth(status);
        setAuthChecked(true);
        if (!status.auth_enabled || status.authenticated) {
          await bootstrapSessionData(status.session_id);
        }
      } catch {
        // Backend warming up or unreachable in local dev; fallback to open bootstrap
        setAuth({
          auth_enabled: false,
          authenticated: true,
          client_label: "Local Plant",
          session_id: "local",
          instant_demo_enabled: false,
        });
        setAuthChecked(true);
        await bootstrapSessionData("local");
      }
    };

    void init();
  }, [bootstrapSessionData]);

  // Persist Studio edits to localStorage (scoped per session)
  useEffect(() => {
    if (!readyForPersistRef.current || !dataset || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        storageKeyForSession(STUDIO_STORAGE_KEY, sessionIdRef.current),
        JSON.stringify({ dataset, config })
      );
    } catch {
      // Ignore storage quota errors
    }
  }, [dataset, config]);

  // Persist pinned scenarios to localStorage (scoped per session)
  useEffect(() => {
    if (!authChecked || typeof window === "undefined") return;
    if (auth.auth_enabled && !auth.authenticated) return;
    try {
      window.localStorage.setItem(
        storageKeyForSession(PINNED_STORAGE_KEY, sessionIdRef.current),
        JSON.stringify(pinnedScenarios)
      );
    } catch {
      // Ignore storage quota errors
    }
  }, [pinnedScenarios, authChecked, auth.auth_enabled, auth.authenticated]);

  // Debounced live pre-solve validation whenever Studio dataset or physics/config changes
  useEffect(() => {
    if (!readyForPersistRef.current || !dataset) return;
    const timer = setTimeout(() => {
      void validatePlantJson(dataset, config)
        .then(({ report }) => setValidation(report))
        .catch(() => {});
    }, 250);
    return () => clearTimeout(timer);
  }, [dataset, config]);

  const validateAndSolveToView = useCallback(
    async (targetView: ViewTab = "gantt") => {
      if (!dataset) return;
      setLoading(true);
      setError(null);
      try {
        const cfg = normalizeConfig({ ...config, currency });
        const { report } = await validatePlantJson(dataset, cfg);
        setValidation(report);
        if (!report.ready) {
          setError(
            lang === "ar"
              ? `يوجد ${report.error_count} خطأ يمنع التشغيل — راجع شريط التشخيص أدناه.`
              : `Pre-solve validation found ${report.error_count} blocking error(s). Fix them before solving.`
          );
          return;
        }
        const res = await solvePlantScheduleApi(dataset, cfg);
        setResult(res);
        setValidation(res.validation);
        setActiveView(targetView);
        await refreshAudit();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Validation / Optimization failed");
      } finally {
        setLoading(false);
      }
    },
    [config, currency, dataset, lang, refreshAudit]
  );

  const uploadWorkbook = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const { dataset: parsed, report } = await validateExcelFile(file, config);
        setDataset(parsed);
        setBaselineSnapshot({ dataset: parsed, config });
        setValidation(report);
        setResult(null);
        readyForPersistRef.current = true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Excel workbook validation failed");
      } finally {
        setLoading(false);
      }
    },
    [config]
  );

  const toggleRamadanMode = useCallback(async () => {
    const nextCfg: SolverConfig = { ...config, ramadan_shift_mode: !config.ramadan_shift_mode };
    setConfig(nextCfg);
    if (dataset) {
      await runSolve(nextCfg, dataset);
    }
  }, [config, dataset, runSolve]);

  const togglePeakTariffMode = useCallback(async () => {
    const nextCfg: SolverConfig = { ...config, avoid_peak_tariff_hrs: !config.avoid_peak_tariff_hrs };
    setConfig(nextCfg);
    if (dataset) {
      await runSolve(nextCfg, dataset);
    }
  }, [config, dataset, runSolve]);

  const toggleAutonomousPmMode = useCallback(async () => {
    const nextCfg: SolverConfig = { ...config, autonomous_pm_window: !config.autonomous_pm_window };
    setConfig(nextCfg);
    if (dataset) {
      await runSolve(nextCfg, dataset);
    }
  }, [config, dataset, runSolve]);

  const addBreakdown = useCallback((bd: MachineBreakdown) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        machine_breakdowns: [...prev.scenarios.machine_breakdowns, bd],
      },
    }));
  }, []);

  const removeBreakdown = useCallback((idx: number) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        machine_breakdowns: prev.scenarios.machine_breakdowns.filter((_, i) => i !== idx),
      },
    }));
  }, []);

  const addResinShortage = useCallback((rs: ResinShortage) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        resin_shortages: [
          ...prev.scenarios.resin_shortages.filter((x) => x.resin_code !== rs.resin_code),
          rs,
        ],
      },
    }));
  }, []);

  const removeResinShortage = useCallback((idx: number) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        resin_shortages: prev.scenarios.resin_shortages.filter((_, i) => i !== idx),
      },
    }));
  }, []);

  const addMoldPmLock = useCallback((lk: MoldPmLock) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        mold_pm_locks: [
          ...prev.scenarios.mold_pm_locks.filter((x) => x.mold_id !== lk.mold_id),
          lk,
        ],
      },
    }));
  }, []);

  const removeMoldPmLock = useCallback((idx: number) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        mold_pm_locks: prev.scenarios.mold_pm_locks.filter((_, i) => i !== idx),
      },
    }));
  }, []);

  const addRushOrder = useCallback((ro: ProductionOrder) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        rush_orders: [...prev.scenarios.rush_orders, ro],
      },
    }));
  }, []);

  const removeRushOrder = useCallback((idx: number) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        rush_orders: prev.scenarios.rush_orders.filter((_, i) => i !== idx),
      },
    }));
  }, []);

  const setRegrindOverride = useCallback((pct: number | null) => {
    setConfig((prev) => ({
      ...prev,
      scenarios: {
        ...prev.scenarios,
        allow_regrind_override_pct: pct,
      },
    }));
  }, []);

  const clearAllScenarios = useCallback(async () => {
    const nextCfg: SolverConfig = { ...config, scenarios: EMPTY_SCENARIOS };
    setConfig(nextCfg);
    if (dataset) {
      await runSolve(nextCfg, dataset);
    }
  }, [config, dataset, runSolve]);

  const applyCopilotScenario = useCallback(
    (nextCfg: SolverConfig, nextRes?: SolveResult | null) => {
      const normalized = normalizeConfig({ ...nextCfg, currency });
      setConfig(normalized);
      if (nextRes) {
        setResult(nextRes);
        setValidation(nextRes.validation);
        void refreshAudit();
      } else {
        void runSolve(normalized);
      }
    },
    [currency, refreshAudit, runSolve]
  );

  const exportExecutiveBrief = useCallback(async () => {
    if (!result) return;
    setExporting(true);
    setError(null);
    try {
      const blob = await exportBriefExcel(result.run_id, currency, result, dataset, { ...config, currency });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mini_dios_plastics_brief_${result.run_id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export executive brief");
    } finally {
      setExporting(false);
    }
  }, [config, currency, dataset, result]);

  const exportStudioDataset = useCallback(async () => {
    if (!dataset) return;
    setExporting(true);
    setError(null);
    try {
      const blob = await exportDatasetExcel(dataset);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mini_dios_plastics_plant_data.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export dataset workbook");
    } finally {
      setExporting(false);
    }
  }, [dataset]);

  const loadAuditRunById = useCallback(async (runId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAuditRun(runId);
      setResult(res);
      setConfig(normalizeConfig(res.audit.config));
      setValidation(res.validation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit run");
    } finally {
      setLoading(false);
    }
  }, []);

  // ---- Studio CRUD Operations -----------------------------------------------------------
  const upsertPress = useCallback((press: PressMachine, originalId?: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      const targetKey = originalId ?? press.machine_id;
      const exists = prev.presses.some((p) => p.machine_id === targetKey);
      const presses = exists
        ? prev.presses.map((p) => (p.machine_id === targetKey ? press : p))
        : [...prev.presses, press];
      const molds =
        originalId && originalId !== press.machine_id
          ? prev.molds.map((m) => ({
              ...m,
              compatible_machines: m.compatible_machines.map((mid) =>
                mid === originalId ? press.machine_id : mid
              ),
            }))
          : prev.molds;
      return { ...prev, presses, molds };
    });
  }, []);

  const deletePress = useCallback((machineId: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        presses: prev.presses.filter((p) => p.machine_id !== machineId),
        molds: prev.molds.map((m) => ({
          ...m,
          compatible_machines: m.compatible_machines.filter((mid) => mid !== machineId),
        })),
      };
    });
  }, []);

  const upsertMold = useCallback((mold: Mold, originalId?: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      const targetKey = originalId ?? mold.mold_id;
      const exists = prev.molds.some((m) => m.mold_id === targetKey);
      const molds = exists
        ? prev.molds.map((m) => (m.mold_id === targetKey ? mold : m))
        : [...prev.molds, mold];
      const orders =
        originalId && originalId !== mold.mold_id
          ? prev.orders.map((o) => (o.mold_id === originalId ? { ...o, mold_id: mold.mold_id } : o))
          : prev.orders;
      return { ...prev, molds, orders };
    });
  }, []);

  const deleteMold = useCallback((moldId: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        molds: prev.molds.filter((m) => m.mold_id !== moldId),
      };
    });
  }, []);

  const upsertResin = useCallback((resin: ResinStock, originalCode?: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      const targetKey = originalCode ?? resin.resin_code;
      const exists = prev.resins.some((r) => r.resin_code === targetKey);
      const resins = exists
        ? prev.resins.map((r) => (r.resin_code === targetKey ? resin : r))
        : [...prev.resins, resin];
      const orders =
        originalCode && originalCode !== resin.resin_code
          ? prev.orders.map((o) => (o.resin_code === originalCode ? { ...o, resin_code: resin.resin_code } : o))
          : prev.orders;
      return { ...prev, resins, orders };
    });
  }, []);

  const deleteResin = useCallback((resinCode: ResinCode) => {
    setDataset((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        resins: prev.resins.filter((r) => r.resin_code !== resinCode),
      };
    });
  }, []);

  const upsertOrder = useCallback((order: ProductionOrder, originalId?: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      const targetKey = originalId ?? order.order_id;
      const exists = prev.orders.some((o) => o.order_id === targetKey);
      const orders = exists
        ? prev.orders.map((o) => (o.order_id === targetKey ? order : o))
        : [...prev.orders, order];
      return { ...prev, orders };
    });
  }, []);

  const deleteOrder = useCallback((orderId: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        orders: prev.orders.filter((o) => o.order_id !== orderId),
      };
    });
  }, []);

  const updatePhysics = useCallback((patch: Partial<PlantPhysicsConfig>) => {
    setConfig((prev) => {
      const nextPhysics: PlantPhysicsConfig = { ...prev.physics, ...patch };
      return {
        ...prev,
        energy_tariff_per_kwh: nextPhysics.energy_tariff_per_kwh,
        max_solve_seconds: nextPhysics.max_solve_seconds,
        physics: nextPhysics,
      };
    });
  }, []);

  // ---- Tab 6: Floor Workforce CRUD + Auto-Save to Active Workspace + Quick Re-Solve ------
  const scheduleWorkspaceAutoSave = useCallback(
    (nextDs: PlantDataset, nextCfg: SolverConfig) => {
      if (!readyForPersistRef.current) return;
      if (workspaceSaveTimerRef.current) {
        clearTimeout(workspaceSaveTimerRef.current);
      }
      const wsId = activeWorkspaceId || "default";
      workspaceSaveTimerRef.current = setTimeout(() => {
        void saveWorkspaceApi({
          workspace_id: wsId,
          name: nextDs.name,
          dataset: nextDs,
          config: nextCfg,
        }).catch(() => {
          // Non-fatal; localStorage already holds the latest state
        });
      }, 800);
    },
    [activeWorkspaceId]
  );

  useEffect(() => {
    return () => {
      if (workspaceSaveTimerRef.current) clearTimeout(workspaceSaveTimerRef.current);
    };
  }, []);

  const upsertWorker = useCallback(
    (worker: FactoryWorker, originalId?: string) => {
      setDataset((prev) => {
        if (!prev) return prev;
        const curr = prev.workers ?? [];
        const targetKey = originalId ?? worker.worker_id;
        const exists = curr.some((w) => w.worker_id === targetKey);
        const workers = exists
          ? curr.map((w) => (w.worker_id === targetKey ? worker : w))
          : [...curr, worker];
        const nextDs = { ...prev, workers };
        scheduleWorkspaceAutoSave(nextDs, config);
        return nextDs;
      });
    },
    [config, scheduleWorkspaceAutoSave]
  );

  const deleteWorker = useCallback(
    (workerId: string) => {
      setDataset((prev) => {
        if (!prev) return prev;
        const workers = (prev.workers ?? []).filter((w) => w.worker_id !== workerId);
        const nextDs = { ...prev, workers };
        scheduleWorkspaceAutoSave(nextDs, config);
        return nextDs;
      });
    },
    [config, scheduleWorkspaceAutoSave]
  );

  const duplicateWorker = useCallback(
    (workerId: string) => {
      setDataset((prev) => {
        if (!prev) return prev;
        const curr = prev.workers ?? [];
        const src = curr.find((w) => w.worker_id === workerId);
        if (!src) return prev;
        const existingIds = new Set(curr.map((w) => w.worker_id));
        const prefix = src.worker_id.split("-")[0] || "WK";
        let n = curr.length + 1;
        let nextId = `${prefix}-${String(n).padStart(2, "0")}`;
        while (existingIds.has(nextId)) {
          n += 1;
          nextId = `${prefix}-${String(n).padStart(2, "0")}`;
        }
        const clone: FactoryWorker = {
          ...src,
          worker_id: nextId,
          name: `${src.name} (Copy)`,
          approved_leave_days: [...src.approved_leave_days],
          certified_machine_ids:
            src.certified_machine_ids === "ALL" ? "ALL" : [...src.certified_machine_ids],
        };
        const nextDs = { ...prev, workers: [...curr, clone] };
        scheduleWorkspaceAutoSave(nextDs, config);
        return nextDs;
      });
    },
    [config, scheduleWorkspaceAutoSave]
  );

  const toggleWorkerSick = useCallback(
    (workerId: string) => {
      setDataset((prev) => {
        if (!prev) return prev;
        const workers = (prev.workers ?? []).map((w) =>
          w.worker_id === workerId
            ? { ...w, status: (w.status === "sick" ? "active" : "sick") as FactoryWorker["status"] }
            : w
        );
        const nextDs = { ...prev, workers };
        scheduleWorkspaceAutoSave(nextDs, config);
        return nextDs;
      });
    },
    [config, scheduleWorkspaceAutoSave]
  );

  const toggleWorkerLeaveDay = useCallback(
    (workerId: string, day: number) => {
      setDataset((prev) => {
        if (!prev) return prev;
        const workers = (prev.workers ?? []).map((w) => {
          if (w.worker_id !== workerId) return w;
          const has = w.approved_leave_days.includes(day);
          const nextDays = has
            ? w.approved_leave_days.filter((d) => d !== day)
            : [...w.approved_leave_days, day].sort((a, b) => a - b);
          return { ...w, approved_leave_days: nextDays };
        });
        const nextDs = { ...prev, workers };
        scheduleWorkspaceAutoSave(nextDs, config);
        return nextDs;
      });
    },
    [config, scheduleWorkspaceAutoSave]
  );

  const updateWorkforceConfig = useCallback(
    (patch: Partial<WorkforceConfig>) => {
      setConfig((prev) => {
        const nextCfg: SolverConfig = {
          ...prev,
          workforce: { ...prev.workforce, ...patch },
        };
        if (dataset) {
          scheduleWorkspaceAutoSave(dataset, nextCfg);
        }
        return nextCfg;
      });
    },
    [dataset, scheduleWorkspaceAutoSave]
  );

  const reOptimizeShifts = useCallback(
    async (overrideConfig?: SolverConfig, overrideDataset?: PlantDataset | null) => {
      const ds = overrideDataset !== undefined ? overrideDataset : dataset;
      if (!ds) return;
      const cfg = normalizeConfig({ ...(overrideConfig ?? config), currency });
      setWorkforceLoading(true);
      setError(null);
      try {
        if (!result) {
          const solved = await solvePlantScheduleApi(ds, cfg);
          setResult(solved);
          setValidation(solved.validation);
          return;
        }
        const { workforce, financials, risk_radar } = await solveWorkforceApi(ds, cfg, result);
        setResult((prev) =>
          prev
            ? {
                ...prev,
                workforce,
                financials,
                ...(risk_radar !== undefined ? { risk_radar } : {}),
              }
            : prev
        );
        // Also refresh validation summary counts
        validatePlantJson(ds, cfg)
          .then(({ report }) => setValidation(report))
          .catch(() => {});
      } catch (err) {
        setError(err instanceof Error ? err.message : "Workforce shift optimization failed");
      } finally {
        setWorkforceLoading(false);
      }
    },
    [config, currency, dataset, result]
  );

  const importStudioProfile = useCallback(
    async (profile: { dataset: PlantDataset; config?: Partial<SolverConfig> }) => {
      setLoading(true);
      setError(null);
      try {
        const nextCfg = normalizeConfig(profile.config ?? config);
        setDataset(profile.dataset);
        setConfig(nextCfg);
        setCurrencyState(nextCfg.currency);
        const { report } = await validatePlantJson(profile.dataset, nextCfg);
        setValidation(report);
        readyForPersistRef.current = true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to import Studio profile JSON");
      } finally {
        setLoading(false);
      }
    },
    [config]
  );

  const resetMoldShots = useCallback((moldId: string) => {
    setDataset((prev) => {
      if (!prev) return prev;
      const molds = prev.molds.map((m) =>
        m.mold_id === moldId ? { ...m, current_shots: 0 } : m
      );
      const nextDs = { ...prev, molds };
      validatePlantJson(nextDs, config)
        .then(({ report }) => setValidation(report))
        .catch(() => {});
      return nextDs;
    });
  }, [config]);

  const navigateToStudioSubTab = useCallback((sub: StudioSubTab) => {
    setStudioSubTab(sub);
    setActiveView("studio");
  }, []);

  const openQuickModal = useCallback((type: QuickModalType, item?: any) => {
    setActiveQuickModal(type);
    setQuickModalItem(item ?? null);
  }, []);

  const closeQuickModal = useCallback(() => {
    setActiveQuickModal(null);
    setQuickModalItem(null);
  }, []);

  const loadWorkspaces = useCallback(async () => {
    try {
      const list = await fetchWorkspaces();
      if (list && list.length > 0) {
        setWorkspaces(list);
      }
    } catch {
      // Backend warming up or offline
    }
  }, []);

  const switchWorkspace = useCallback(
    async (wsId: string) => {
      setLoading(true);
      setError(null);
      try {
        const ws = await getWorkspaceApi(wsId);
        const nextCfg = normalizeConfig(ws.config);
        setDataset(ws.dataset);
        setConfig(nextCfg);
        setCurrencyState(nextCfg.currency);
        setActiveWorkspaceId(ws.workspace_id);
        const { report } = await validatePlantJson(ws.dataset, nextCfg);
        setValidation(report);
        if (report.ready) {
          const solved = await solvePlantScheduleApi(ws.dataset, nextCfg);
          setResult(solved);
          setValidation(solved.validation);
        } else {
          setResult(null);
        }
        readyForPersistRef.current = true;
        await refreshAudit();
      } catch (err) {
        setError(err instanceof Error ? err.message : `Failed to switch to workspace ${wsId}`);
      } finally {
        setLoading(false);
      }
    },
    [refreshAudit]
  );

  const saveCurrentWorkspaceAs = useCallback(
    async (name: string) => {
      if (!dataset) return;
      setLoading(true);
      setError(null);
      try {
        const wsId = `ws-${Date.now()}`;
        await saveWorkspaceApi({
          workspace_id: wsId,
          name: name.trim() || `Custom Plant ${new Date().toLocaleDateString()}`,
          dataset,
          config,
        });
        setActiveWorkspaceId(wsId);
        await loadWorkspaces();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to save workspace");
      } finally {
        setLoading(false);
      }
    },
    [dataset, config, loadWorkspaces]
  );

  const deleteWorkspace = useCallback(
    async (wsId: string) => {
      setLoading(true);
      setError(null);
      try {
        await deleteWorkspaceApi(wsId);
        if (activeWorkspaceId === wsId) {
          await switchWorkspace("default");
        }
        await loadWorkspaces();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete workspace");
      } finally {
        setLoading(false);
      }
    },
    [activeWorkspaceId, loadWorkspaces, switchWorkspace]
  );

  const createNewBlankPlant = useCallback(() => {
    const blankId = `blank-${Date.now()}`;
    const blankDs: PlantDataset = {
      name: "New Blank Plant",
      presses: [],
      molds: [],
      resins: [],
      orders: [],
      workers: [],
    };
    const nextCfg = normalizeConfig({ ...DEFAULT_CONFIG, currency });
    setDataset(blankDs);
    setConfig(nextCfg);
    setActiveWorkspaceId(blankId);
    setValidation({
      ready: false,
      error_count: 1,
      warning_count: 0,
      info_count: 0,
      issues: [
        {
          code: "V-BLANK",
          severity: "error",
          message: "No presses or molds configured yet. Use '+ Add Press' or '+ Add Mold' to start.",
          entity_type: "plant",
          entity_id: null,
        },
      ],
      summary: {
        dataset_name: blankDs.name,
        presses_total: 0,
        presses_active: 0,
        molds_total: 0,
        molds_needing_pm: 0,
        resins_total: 0,
        orders_total: 0,
        export_orders: 0,
        total_production_hrs: 0,
        available_press_hrs: 0,
        plant_load_pct: 0,
        resin_balance: [],
        mold_health: [],
        workers_total: 0,
        workers_active: 0,
        workers_sick: 0,
        workers_on_leave: 0,
      },
    });
    setResult(null);
    readyForPersistRef.current = true;
  }, [currency]);

  const resetCurrentPlantToDemo = useCallback(async () => {
    await loadDemo(true);
    setActiveWorkspaceId("default");
    await loadWorkspaces();
  }, [loadDemo, loadWorkspaces]);

  // ---- Part 1: Boardroom Pin & Compare (A / B / C) --------------------------------------
  const pinScenario = useCallback(
    (opts?: {
      label?: string;
      replaceSlot?: PinnedSlotId;
      config?: SolverConfig;
      result?: SolveResult;
      dataset?: PlantDataset;
    }): PinnedSlotId | null => {
      const targetResult = opts?.result ?? result;
      const targetDataset = opts?.dataset ?? dataset;
      const targetConfig = normalizeConfig(opts?.config ?? config);
      if (!targetResult || !targetDataset) return null;

      let chosenSlot: PinnedSlotId | null = opts?.replaceSlot ?? null;
      setPinnedScenarios((prev) => {
        const usedSlots = new Set(prev.map((p) => p.slot));
        const slot: PinnedSlotId =
          opts?.replaceSlot ?? PIN_SLOTS.find((s) => !usedSlots.has(s)) ?? "C";
        chosenSlot = slot;

        const cleanLabel = (opts?.label || deriveScenarioLabel(targetConfig, lang)).trim();
        const snapshot: PinnedScenario = {
          id: `pin_${slot}_${Date.now()}`,
          slot,
          label: cleanLabel || `Scenario ${slot}`,
          createdAt: new Date().toISOString(),
          dataset: JSON.parse(JSON.stringify(targetDataset)) as PlantDataset,
          solverConfig: JSON.parse(JSON.stringify(targetConfig)) as SolverConfig,
          result: JSON.parse(JSON.stringify(targetResult)) as SolveResult,
        };

        const filtered = prev.filter((p) => p.slot !== slot);
        return [...filtered, snapshot].sort(
          (a, b) => PIN_SLOTS.indexOf(a.slot) - PIN_SLOTS.indexOf(b.slot)
        );
      });
      return chosenSlot;
    },
    [config, dataset, lang, result]
  );

  const renamePinnedScenario = useCallback((slot: PinnedSlotId, label: string) => {
    const trimmed = label.trim();
    if (!trimmed) return;
    setPinnedScenarios((prev) =>
      prev.map((p) => (p.slot === slot ? { ...p, label: trimmed } : p))
    );
  }, []);

  const removePinnedScenario = useCallback((slot: PinnedSlotId) => {
    setPinnedScenarios((prev) => prev.filter((p) => p.slot !== slot));
  }, []);

  const clearPinnedScenarios = useCallback(() => {
    setPinnedScenarios([]);
  }, []);

  const promotePinnedScenario = useCallback(
    (slot: PinnedSlotId) => {
      const target = pinnedScenarios.find((p) => p.slot === slot);
      if (!target) return;
      const restoredDataset = JSON.parse(JSON.stringify(target.dataset)) as PlantDataset;
      const restoredConfig = normalizeConfig({
        ...(JSON.parse(JSON.stringify(target.solverConfig)) as SolverConfig),
        currency,
      });
      const restoredResult = JSON.parse(JSON.stringify(target.result)) as SolveResult;
      setDataset(restoredDataset);
      setConfig(restoredConfig);
      setResult(restoredResult);
      setValidation(restoredResult.validation);
      setError(null);
    },
    [currency, pinnedScenarios]
  );

  // ---- Part 2: Hosted Demo Auth Gate & Session Sandbox ----------------------------------
  const loginWithPasscode = useCallback(
    async (passcode: string) => {
      const status = await loginWithPasscodeApi(passcode);
      setAuth(status);
      setAuthChecked(true);
      readyForPersistRef.current = false;
      await bootstrapSessionData(status.session_id);
    },
    [bootstrapSessionData]
  );

  const loginInstantDemo = useCallback(async () => {
    const status = await loginInstantDemoApi();
    setAuth(status);
    setAuthChecked(true);
    readyForPersistRef.current = false;
    await bootstrapSessionData(status.session_id);
  }, [bootstrapSessionData]);

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } catch {
      // Clear local client state regardless
    }
    readyForPersistRef.current = false;
    sessionIdRef.current = null;
    setDataset(null);
    setResult(null);
    setValidation(null);
    setPinnedScenarios([]);
    setCopilotOpen(false);
    setBriefModalOpen(false);
    setActiveView("scope");
    setAuth((prev) => ({
      ...prev,
      authenticated: false,
      client_label: null,
      session_id: null,
    }));
  }, []);

  const resetHostedSandbox = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await resetSandboxApi();
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(storageKeyForSession(STUDIO_STORAGE_KEY, sessionIdRef.current));
        window.localStorage.removeItem(storageKeyForSession(PINNED_STORAGE_KEY, sessionIdRef.current));
      }
      setPinnedScenarios([]);
      const nextCfg = normalizeConfig({ ...res.default_config, currency });
      setDataset(res.dataset);
      setConfig(nextCfg);
      setBaselineSnapshot({ dataset: res.dataset, config: nextCfg });
      setActiveWorkspaceId("default");
      const solved = await solvePlantScheduleApi(res.dataset, nextCfg);
      setResult(solved);
      setValidation(solved.validation);
      readyForPersistRef.current = true;
      await refreshAudit();
      await loadWorkspaces();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset demo sandbox");
    } finally {
      setLoading(false);
    }
  }, [currency, loadWorkspaces, refreshAudit]);

  const modifiedCount = useMemo(
    () => countDatasetAndPhysicsDiffs(dataset, config, baselineSnapshot.dataset, baselineSnapshot.config),
    [dataset, config, baselineSnapshot]
  );

  return (
    <AppContext.Provider
      value={{
        lang,
        setLang,
        currency,
        setCurrency,
        activeView,
        setActiveView,
        dataset,
        validation,
        config,
        setConfig,
        result,
        setResult,
        setValidation,
        auditRuns,
        refreshAudit,
        loading,
        exporting,
        error,
        clearError: () => setError(null),
        copilotOpen,
        setCopilotOpen,
        copilotDraftPrompt,
        setCopilotDraftPrompt,
        openCopilotWithPrompt,
        modifiedCount,
        loadDemo,
        uploadWorkbook,
        runSolve,
        validateAndSolveToView,
        toggleRamadanMode,
        togglePeakTariffMode,
        toggleAutonomousPmMode,
        addBreakdown,
        removeBreakdown,
        addResinShortage,
        removeResinShortage,
        addMoldPmLock,
        removeMoldPmLock,
        addRushOrder,
        removeRushOrder,
        setRegrindOverride,
        clearAllScenarios,
        applyCopilotScenario,
        exportExecutiveBrief,
        exportStudioDataset,
        loadAuditRunById,
        workspaces,
        activeWorkspaceId,
        loadWorkspaces,
        switchWorkspace,
        saveCurrentWorkspaceAs,
        deleteWorkspace,
        createNewBlankPlant,
        resetCurrentPlantToDemo,
        resetMoldShots,
        briefModalOpen,
        setBriefModalOpen,
        activeQuickModal,
        quickModalItem,
        openQuickModal,
        closeQuickModal,
        studioSubTab,
        setStudioSubTab,
        navigateToStudioSubTab,
        upsertPress,
        deletePress,
        upsertMold,
        deleteMold,
        upsertResin,
        deleteResin,
        upsertOrder,
        deleteOrder,
        updatePhysics,
        importStudioProfile,
        workforceLoading,
        upsertWorker,
        deleteWorker,
        duplicateWorker,
        toggleWorkerSick,
        toggleWorkerLeaveDay,
        updateWorkforceConfig,
        reOptimizeShifts,
        pinnedScenarios,
        pinScenario,
        renamePinnedScenario,
        removePinnedScenario,
        clearPinnedScenarios,
        promotePinnedScenario,
        auth,
        authChecked,
        loginWithPasscode,
        loginInstantDemo,
        logout,
        resetHostedSandbox,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
