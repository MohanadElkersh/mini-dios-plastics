"use client";

import React, { useState } from "react";
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  Clock,
  DollarSign,
  Flame,
  History,
  Play,
  Plus,
  Recycle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Trash2,
  Wrench,
  Zap,
} from "lucide-react";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COLOR_LABELS, CONSTRAINT_LABELS, COPY, STATUS_LABELS } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { PlasticColor, ResinCode } from "@/lib/types";
import { PinScenarioButton } from "./PinScenarioButton";
import { ScenarioComparisonMatrix } from "./ScenarioComparisonMatrix";

type ScenarioTab = "breakdown" | "resin" | "rush" | "pm";

const PLASTIC_COLORS: PlasticColor[] = ["Natural", "White", "Yellow", "Blue", "Red", "Black"];
const RESIN_CODES: ResinCode[] = ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"];

export function TradeoffConsole() {
  const {
    lang,
    currency,
    dataset,
    config,
    setConfig,
    result,
    auditRuns,
    loading,
    runSolve,
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
    loadAuditRunById,
    setCopilotOpen,
  } = useApp();

  const t = COPY[lang];
  const [scTab, setScTab] = useState<ScenarioTab>("breakdown");

  // Breakdown form state
  const [bdPress, setBdPress] = useState("P-500T");
  const [bdStartHr, setBdStartHr] = useState(48);
  const [bdDurHrs, setBdDurHrs] = useState(18);

  // Resin shock form state
  const [rsResin, setRsResin] = useState<ResinCode>("HDPE");
  const [rsCutPct, setRsCutPct] = useState(35);
  const [rsSpikePct, setRsSpikePct] = useState(15);

  // Rush order form state
  const [roCustomer, setRoCustomer] = useState("Urgent GCC Export");
  const [roMold, setRoMold] = useState("M-01");
  const [roResin, setRoResin] = useState<ResinCode>("HDPE");
  const [roColor, setRoColor] = useState<PlasticColor>("White");
  const [roQty, setRoQty] = useState(40000);
  const [roWeightG, setRoWeightG] = useState(2.8);
  const [roDueHr, setRoDueHr] = useState(108);
  const [roExport, setRoExport] = useState(true);

  // Mold PM lock form state
  const [pmMold, setPmMold] = useState("M-01");
  const [pmDurHrs, setPmDurHrs] = useState(8);

  const applyPreset = (w_changeover_scrap: number, w_otif: number, w_energy_cost: number, w_working_capital: number) => {
    const nextCfg = { ...config, w_changeover_scrap, w_otif, w_energy_cost, w_working_capital };
    setConfig(nextCfg);
    void runSolve(nextCfg);
  };

  const handleSlider = (
    key: "w_changeover_scrap" | "w_otif" | "w_energy_cost" | "w_working_capital",
    val: number
  ) => {
    setConfig((prev) => {
      const next = { ...prev, [key]: val };
      if (next.w_changeover_scrap + next.w_otif + next.w_energy_cost + next.w_working_capital === 0) {
        next[key] = 5;
      }
      return next;
    });
  };

  const money = (amount: number) => {
    if (!result) return formatMoney(amount, currency);
    return formatMoney(convertCurrency(amount, result.currency, currency, result.fx_egp_per_sar), currency);
  };

  const sc = result?.scorecard;
  const activeCount =
    config.scenarios.machine_breakdowns.length +
    config.scenarios.resin_shortages.length +
    config.scenarios.mold_pm_locks.length +
    config.scenarios.rush_orders.length +
    (config.scenarios.allow_regrind_override_pct ? 1 : 0);

  return (
    <div className="space-y-6">
      {/* Top 4 Executive KPI Delta Cards */}
      {result && sc ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            testId="kpi-cash-saved"
            icon={<DollarSign className="h-5 w-5" />}
            accent="emerald"
            label={t.kpiCashSaved}
            value={money(sc.cash_savings)}
            badge={`${sc.cash_savings_pct >= 0 ? "-" : "+"}${Math.abs(sc.cash_savings_pct).toFixed(1)}%`}
            sub={`${money(sc.total_cost.baseline)} → ${money(sc.total_cost.optimized)}`}
          />
          <KpiCard
            testId="kpi-scrap-cut"
            icon={<Recycle className="h-5 w-5" />}
            accent="cyan"
            label={t.kpiScrapCut}
            value={`${sc.purge_scrap_kg_saved.toFixed(1)} kg`}
            badge={`${sc.purge_scrap_kg.delta_pct.toFixed(1)}%`}
            sub={`${sc.purge_scrap_kg.baseline.toFixed(1)} → ${sc.purge_scrap_kg.optimized.toFixed(1)} kg`}
          />
          <KpiCard
            testId="kpi-changeover-saved"
            icon={<Clock className="h-5 w-5" />}
            accent="indigo"
            label={t.kpiChangeoverSaved}
            value={`${sc.changeover_hours_saved.toFixed(2)} h`}
            badge={`${sc.changeover_hours.delta_pct.toFixed(1)}%`}
            sub={`${sc.changeover_hours.baseline.toFixed(2)}h → ${sc.changeover_hours.optimized.toFixed(2)}h`}
          />
          <KpiCard
            testId="kpi-otif-solve"
            icon={<Zap className="h-5 w-5" />}
            accent="amber"
            label={t.kpiOtifSolve}
            value={`${result.optimized.kpis.otif_pct.toFixed(1)}% • ${result.solve_time_ms}ms`}
            badge={`${STATUS_LABELS[lang][result.status] ?? result.status} • OEE ${result.optimized.kpis.oee_pct.toFixed(1)}%`}
            sub={`SHA ${result.audit.schedule_sha256.slice(0, 10)}…`}
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-8 text-center">
          <Activity className="mx-auto mb-3 h-8 w-8 text-cyan-400" />
          <p className="text-sm text-slate-300">{t.noResultYet}</p>
        </div>
      )}

      {/* Boardroom Side-by-Side Scenario Comparison Matrix (A vs. B vs. C) */}
      <ScenarioComparisonMatrix />

      {/* Main Controls Grid: 4 Sliders (Left) + Custom Composable Scenario Builder (Right) */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* 4 Executive Sliders */}
        <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5 lg:col-span-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-white">{t.weightsTitle}</h2>
              <p className="text-xs text-slate-400">{t.weightsSubtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              <PinScenarioButton testId="btn-pin-scenario-console" />
              <button
                type="button"
                onClick={() => setCopilotOpen(true)}
                className="inline-flex items-center gap-1 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-2 text-[11px] font-semibold text-cyan-300 hover:bg-cyan-500/20"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{t.copilotButton}</span>
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <WeightSlider
              testId="slider-scrap"
              label={t.wScrap}
              value={config.w_changeover_scrap}
              accent="text-cyan-300"
              onChange={(v) => handleSlider("w_changeover_scrap", v)}
              onCommit={() => void runSolve(config)}
            />
            <WeightSlider
              testId="slider-otif"
              label={t.wOtif}
              value={config.w_otif}
              accent="text-emerald-300"
              onChange={(v) => handleSlider("w_otif", v)}
              onCommit={() => void runSolve(config)}
            />
            <WeightSlider
              testId="slider-energy"
              label={t.wEnergy}
              value={config.w_energy_cost}
              accent="text-amber-300"
              onChange={(v) => handleSlider("w_energy_cost", v)}
              onCommit={() => void runSolve(config)}
            />
            <WeightSlider
              testId="slider-capital"
              label={t.wCapital}
              value={config.w_working_capital}
              accent="text-indigo-300"
              onChange={(v) => handleSlider("w_working_capital", v)}
              onCommit={() => void runSolve(config)}
            />
          </div>

          {/* Strategy Presets */}
          <div className="mt-5 grid grid-cols-2 gap-2 border-t border-slate-800 pt-4">
            <button
              type="button"
              onClick={() => applyPreset(35, 35, 15, 15)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-500/50"
            >
              {t.presetBalanced}
            </button>
            <button
              type="button"
              onClick={() => applyPreset(65, 15, 10, 10)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-cyan-200 hover:border-cyan-500/50"
            >
              {t.presetMinScrap}
            </button>
            <button
              type="button"
              onClick={() => applyPreset(15, 70, 10, 5)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-emerald-200 hover:border-emerald-500/50"
            >
              {t.presetMaxOtif}
            </button>
            <button
              type="button"
              onClick={() => applyPreset(20, 20, 50, 10)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-amber-200 hover:border-amber-500/50"
            >
              {t.presetLowEnergy}
            </button>
          </div>
        </div>

        {/* Custom Composable Scenario Builder Panel */}
        <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5 lg:col-span-7">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-white">{t.scenarioBuilderTitle}</h2>
              <p className="text-xs text-slate-400">{t.scenarioBuilderDesc}</p>
            </div>
            <div className="flex items-center gap-2">
              {activeCount > 0 && (
                <button
                  type="button"
                  data-testid="btn-reset-scenarios"
                  onClick={() => void clearAllScenarios()}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-300 hover:text-white"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>{t.resetScenariosBtn}</span>
                </button>
              )}
              <button
                type="button"
                data-testid="btn-run-scenario-solve"
                disabled={loading}
                onClick={() => void runSolve(config)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5" />
                <span>{t.runOptimize}</span>
              </button>
            </div>
          </div>

          {/* Scenario Type Tabs */}
          <div className="mb-4 flex flex-wrap gap-1.5 border-b border-slate-800 pb-3">
            {(
              [
                { id: "breakdown", label: t.tabBreakdown, icon: <AlertOctagon className="h-3.5 w-3.5" /> },
                { id: "resin", label: t.tabResin, icon: <Flame className="h-3.5 w-3.5" /> },
                { id: "rush", label: t.tabRush, icon: <Plus className="h-3.5 w-3.5" /> },
                { id: "pm", label: t.tabMoldPm, icon: <Wrench className="h-3.5 w-3.5" /> },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                data-testid={`scenario-tab-${tab.id}`}
                onClick={() => setScTab(tab.id)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  scTab === tab.id
                    ? "bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/50"
                    : "bg-slate-900 text-slate-400 hover:text-white"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Tab Forms */}
          {scTab === "breakdown" && (
            <div className="grid gap-3 sm:grid-cols-4">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Press</label>
                <select
                  data-testid="input-bd-press"
                  value={bdPress}
                  onChange={(e) => setBdPress(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                >
                  {(dataset?.presses ?? []).map((p) => (
                    <option key={p.machine_id} value={p.machine_id}>
                      {p.machine_id} ({p.tonnage}T)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Start Hour (0–160)</label>
                <input
                  type="number"
                  min={0}
                  max={160}
                  value={bdStartHr}
                  onChange={(e) => setBdStartHr(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Duration (hrs)</label>
                <input
                  type="number"
                  min={1}
                  max={96}
                  value={bdDurHrs}
                  onChange={(e) => setBdDurHrs(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  data-testid="btn-add-breakdown"
                  onClick={() => addBreakdown({ machine_id: bdPress, start_hr: bdStartHr, duration_hrs: bdDurHrs })}
                  className="w-full rounded-lg border border-rose-500/40 bg-rose-500/15 px-3 py-2 text-xs font-bold text-rose-200 hover:bg-rose-500/25"
                >
                  + {t.addScenarioBtn}
                </button>
              </div>
            </div>
          )}

          {scTab === "resin" && (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-4">
                <div>
                  <label className="mb-1 block text-[11px] text-slate-400">Resin Grade</label>
                  <select
                    value={rsResin}
                    onChange={(e) => setRsResin(e.target.value as ResinCode)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                  >
                    {RESIN_CODES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-slate-400">Stock Cut (%)</label>
                  <input
                    type="number"
                    min={0}
                    max={90}
                    value={rsCutPct}
                    onChange={(e) => setRsCutPct(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-slate-400">Price Spike (%)</label>
                  <input
                    type="number"
                    min={0}
                    max={200}
                    value={rsSpikePct}
                    onChange={(e) => setRsSpikePct(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    type="button"
                    data-testid="btn-add-resin"
                    onClick={() =>
                      addResinShortage({
                        resin_code: rsResin,
                        available_pct_reduction: rsCutPct,
                        virgin_price_spike_pct: rsSpikePct,
                      })
                    }
                    className="w-full rounded-lg border border-amber-500/40 bg-amber-500/15 px-3 py-2 text-xs font-bold text-amber-200 hover:bg-amber-500/25"
                  >
                    + {t.addScenarioBtn}
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs">
                <span className="text-slate-300">{t.regrindOverrideLabel}:</span>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={0}
                    max={40}
                    step={5}
                    value={config.scenarios.allow_regrind_override_pct ?? 0}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      setRegrindOverride(v === 0 ? null : v);
                    }}
                    className="dios-slider w-28"
                  />
                  <span className="w-10 text-end font-mono font-bold text-emerald-300">
                    {config.scenarios.allow_regrind_override_pct ?? 0}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {scTab === "rush" && (
            <div className="grid gap-2.5 sm:grid-cols-4">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Mold</label>
                <select
                  value={roMold}
                  onChange={(e) => setRoMold(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                >
                  {(dataset?.molds ?? []).map((m) => (
                    <option key={m.mold_id} value={m.mold_id}>
                      {m.mold_id} — {m.name.slice(0, 18)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Resin</label>
                <select
                  value={roResin}
                  onChange={(e) => setRoResin(e.target.value as ResinCode)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                >
                  {RESIN_CODES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Plastic Color</label>
                <select
                  value={roColor}
                  onChange={(e) => setRoColor(e.target.value as PlasticColor)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                >
                  {PLASTIC_COLORS.map((c) => (
                    <option key={c} value={c}>
                      {COLOR_LABELS[lang][c]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Qty (pcs)</label>
                <input
                  type="number"
                  min={1000}
                  step={5000}
                  value={roQty}
                  onChange={(e) => setRoQty(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Part Wt (g)</label>
                <input
                  type="number"
                  step={0.5}
                  min={1}
                  value={roWeightG}
                  onChange={(e) => setRoWeightG(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Due Hr (12–168)</label>
                <input
                  type="number"
                  min={12}
                  max={168}
                  value={roDueHr}
                  onChange={(e) => setRoDueHr(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white"
                />
              </div>
              <div className="flex items-end">
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 w-full">
                  <input
                    type="checkbox"
                    checked={roExport}
                    onChange={(e) => setRoExport(e.target.checked)}
                    className="accent-cyan-400"
                  />
                  <span>Export Priority</span>
                </label>
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  data-testid="btn-add-rush"
                  onClick={() => {
                    const idx = config.scenarios.rush_orders.length + 1;
                    addRushOrder({
                      order_id: `RUSH-${String(idx).padStart(2, "0")}`,
                      customer: roCustomer,
                      sku_name: `Rush ${roColor} ${roMold}`,
                      mold_id: roMold,
                      resin_code: roResin,
                      color: roColor,
                      color_rank: PLASTIC_COLORS.indexOf(roColor) + 1,
                      quantity_pcs: roQty,
                      part_weight_g: roWeightG,
                      max_regrind_pct: roExport ? 0 : 15,
                      due_hr: roDueHr,
                      late_penalty_per_hr: roExport ? 720 : 400,
                      is_export: roExport,
                      unit_selling_price: Math.round(Math.max(0.04, roWeightG * 0.011) * 1000) / 1000,
                      discount_pct: 0,
                    });
                  }}
                  className="w-full rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-3 py-1.5 text-xs font-bold text-cyan-200 hover:bg-cyan-500/25"
                >
                  + {t.addScenarioBtn}
                </button>
              </div>
            </div>
          )}

          {scTab === "pm" && (
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">Mold ID</label>
                <select
                  value={pmMold}
                  onChange={(e) => setPmMold(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                >
                  {(dataset?.molds ?? []).map((m) => (
                    <option key={m.mold_id} value={m.mold_id}>
                      {m.mold_id} — {m.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">PM Lock Duration (hrs)</label>
                <input
                  type="number"
                  min={1}
                  max={48}
                  value={pmDurHrs}
                  onChange={(e) => setPmDurHrs(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-white"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  data-testid="btn-add-pm"
                  onClick={() => addMoldPmLock({ mold_id: pmMold, duration_hrs: pmDurHrs })}
                  className="w-full rounded-lg border border-purple-500/40 bg-purple-500/15 px-3 py-2 text-xs font-bold text-purple-200 hover:bg-purple-500/25"
                >
                  + {t.addScenarioBtn}
                </button>
              </div>
            </div>
          )}

          {/* Active Composable Disruptions List */}
          <div className="mt-4 border-t border-slate-800 pt-3">
            <div className="mb-2 text-[11px] font-semibold text-slate-400">
              {t.activeScenariosTitle} ({activeCount})
            </div>
            {activeCount === 0 ? (
              <p className="text-xs text-slate-500">{t.noActiveScenarios}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {config.scenarios.machine_breakdowns.map((bd, i) => (
                  <ScenarioChip
                    key={`bd-${i}`}
                    color="rose"
                    text={`Breakdown: ${bd.machine_id} @ H${bd.start_hr} (${bd.duration_hrs}h)`}
                    onRemove={() => removeBreakdown(i)}
                  />
                ))}
                {config.scenarios.resin_shortages.map((rs, i) => (
                  <ScenarioChip
                    key={`rs-${i}`}
                    color="amber"
                    text={`${rs.resin_code}: -${rs.available_pct_reduction}% stock / +${rs.virgin_price_spike_pct}% price`}
                    onRemove={() => removeResinShortage(i)}
                  />
                ))}
                {config.scenarios.mold_pm_locks.map((lk, i) => (
                  <ScenarioChip
                    key={`pm-${i}`}
                    color="purple"
                    text={`Mold PM: ${lk.mold_id} (${lk.duration_hrs}h)`}
                    onRemove={() => removeMoldPmLock(i)}
                  />
                ))}
                {config.scenarios.rush_orders.map((ro, i) => (
                  <ScenarioChip
                    key={`ro-${i}`}
                    color="cyan"
                    text={`Rush ${ro.order_id}: ${(ro.quantity_pcs / 1000).toFixed(0)}k ${ro.color} ${ro.mold_id} due H${ro.due_hr}`}
                    onRemove={() => removeRushOrder(i)}
                  />
                ))}
                {config.scenarios.allow_regrind_override_pct && (
                  <ScenarioChip
                    color="emerald"
                    text={`Non-Food Regrind Cap: ${config.scenarios.allow_regrind_override_pct}%`}
                    onRemove={() => setRegrindOverride(null)}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row: 6/6 Hard Constraint Verification + Audit Trail */}
      {result && (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5 lg:col-span-7">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">{t.hardConstraintsTitle}</h3>
              </div>
              <span className="rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-bold text-emerald-300">
                {result.audit.constraints_verified.filter((c) => c.passed).length}/6 PASS
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {result.audit.constraints_verified.map((chk) => (
                <div
                  key={chk.id}
                  className="flex items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className={`h-4 w-4 shrink-0 ${chk.passed ? "text-emerald-400" : "text-rose-400"}`} />
                    <span className="text-slate-200">{CONSTRAINT_LABELS[lang][chk.id] ?? chk.name}</span>
                  </div>
                  <span className="font-mono text-[11px] font-bold text-emerald-300">{chk.violations}v</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5 lg:col-span-5">
            <div className="mb-3 flex items-center gap-2">
              <History className="h-4 w-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white">{t.auditHistoryTitle}</h3>
            </div>
            <div className="max-h-56 space-y-2 overflow-y-auto pe-1">
              {auditRuns.slice(0, 8).map((run) => (
                <button
                  key={run.run_id}
                  type="button"
                  onClick={() => void loadAuditRunById(run.run_id)}
                  className="flex w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-start text-xs transition hover:border-cyan-500/40"
                >
                  <div>
                    <div className="font-mono font-bold text-cyan-300">{run.run_id}</div>
                    <div className="text-[11px] text-slate-400">
                      {run.status} • {run.solve_time_ms}ms • OTIF {run.scorecard_summary.otif_pct.toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-end font-mono text-[11px]">
                    <div className="font-bold text-emerald-300">
                      -{run.scorecard_summary.purge_scrap_kg_saved.toFixed(1)} kg
                    </div>
                    <div className="text-slate-400">{run.scorecard_summary.cash_savings_pct.toFixed(1)}% saved</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({
  testId,
  icon,
  accent,
  label,
  value,
  badge,
  sub,
}: {
  testId: string;
  icon: React.ReactNode;
  accent: "emerald" | "cyan" | "indigo" | "amber";
  label: string;
  value: string;
  badge: string;
  sub: string;
}) {
  const accentMap = {
    emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    cyan: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
    indigo: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  };
  return (
    <div data-testid={testId} className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        <span className={`inline-flex h-8 w-8 items-center justify-center rounded-lg border ${accentMap[accent]}`}>
          {icon}
        </span>
      </div>
      <div dir="ltr" className="mt-2 font-mono text-xl font-bold text-white">
        {value}
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 text-[11px]">
        <span className={`rounded-md border px-1.5 py-0.5 font-mono font-bold ${accentMap[accent]}`}>{badge}</span>
        <span dir="ltr" className="truncate font-mono text-slate-400">
          {sub}
        </span>
      </div>
    </div>
  );
}

function WeightSlider({
  testId,
  label,
  value,
  accent,
  onChange,
  onCommit,
}: {
  testId: string;
  label: string;
  value: number;
  accent: string;
  onChange: (v: number) => void;
  onCommit: () => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-200">{label}</span>
        <span dir="ltr" className={`font-mono font-bold ${accent}`}>
          {value}
        </span>
      </div>
      <input
        type="range"
        data-testid={testId}
        min={0}
        max={100}
        step={5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        onMouseUp={onCommit}
        onTouchEnd={onCommit}
        className="dios-slider w-full"
      />
    </div>
  );
}

function ScenarioChip({
  color,
  text,
  onRemove,
}: {
  color: "rose" | "amber" | "purple" | "cyan" | "emerald";
  text: string;
  onRemove: () => void;
}) {
  const cls = {
    rose: "border-rose-500/40 bg-rose-500/15 text-rose-200",
    amber: "border-amber-500/40 bg-amber-500/15 text-amber-200",
    purple: "border-purple-500/40 bg-purple-500/15 text-purple-200",
    cyan: "border-cyan-500/40 bg-cyan-500/15 text-cyan-200",
    emerald: "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
  }[color];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-semibold ${cls}`}>
      <span>{text}</span>
      <button type="button" onClick={onRemove} className="opacity-70 hover:opacity-100">
        <Trash2 className="h-3 w-3" />
      </button>
    </span>
  );
}
