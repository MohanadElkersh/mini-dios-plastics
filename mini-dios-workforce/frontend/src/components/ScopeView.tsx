"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Database,
  Droplet,
  Edit3,
  Factory,
  Flame,
  Info,
  Layers,
  Package,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Sliders,
  Trash2,
  Wrench,
  XCircle,
  Zap,
} from "lucide-react";
import { RiskRadarPanel } from "@/components/RiskRadarPanel";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

export function ScopeView() {
  const {
    lang,
    dataset,
    validation,
    loading,
    workspaces,
    activeWorkspaceId,
    switchWorkspace,
    saveCurrentWorkspaceAs,
    deleteWorkspace,
    createNewBlankPlant,
    resetCurrentPlantToDemo,
    resetMoldShots,
    openQuickModal,
    navigateToStudioSubTab,
    runSolve,
    setActiveView,
  } = useApp();

  const t = COPY[lang];
  const summary = validation?.summary;

  const [saveAsModalOpen, setSaveAsModalOpen] = useState(false);
  const [saveAsName, setSaveAsName] = useState("");
  const [resetFeedback, setResetFeedback] = useState<string | null>(null);

  const handleSaveAsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!saveAsName.trim()) return;
    void saveCurrentWorkspaceAs(saveAsName.trim());
    setSaveAsModalOpen(false);
    setSaveAsName("");
  };

  const handleResetMold = (moldId: string) => {
    resetMoldShots(moldId);
    setResetFeedback(`${moldId}: ${t.pmResetSuccess}`);
    setTimeout(() => setResetFeedback(null), 3500);
  };

  return (
    <div className="space-y-6">
      {/* Reset Feedback Notification */}
      {resetFeedback && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/50 bg-emerald-500/15 px-4 py-2 text-xs font-semibold text-emerald-200 shadow-lg shadow-emerald-950/20">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span>{resetFeedback}</span>
        </div>
      )}

      {/* Top Row: Two-Panel Control Bar (Workspaces Hub + Quick-Add Hub) */}
      <div className="grid gap-4 lg:grid-cols-12">
        {/* Panel A: Saved Plant Workspaces (Zero Files Needed) */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-[#0f1629] p-4 lg:col-span-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-cyan-400" />
                <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  {t.workspaceHubTitle}
                </h2>
              </div>
              <span className="rounded-full bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 text-[10px] font-mono text-cyan-300">
                {workspaces.length} Plants
              </span>
            </div>

            <div className="mt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              {/* Workspace Selector */}
              <select
                data-testid="select-workspace"
                value={activeWorkspaceId}
                onChange={(e) => void switchWorkspace(e.target.value)}
                className="min-h-[44px] flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base font-semibold text-slate-200 focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
              >
                {workspaces.map((w) => (
                  <option key={w.workspace_id} value={w.workspace_id}>
                    {w.name} {w.workspace_id === "default" ? "★" : ""}
                  </option>
                ))}
              </select>

              <button
                type="button"
                data-testid="btn-save-as-plant"
                onClick={() => {
                  setSaveAsName(`${dataset?.name ?? "Plant"} (Copy)`);
                  setSaveAsModalOpen(true);
                }}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-slate-600 hover:bg-slate-800 md:min-h-0"
              >
                <Save className="h-3.5 w-3.5 text-cyan-400" />
                <span>{t.saveAsNewPlant}</span>
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-3">
            <button
              type="button"
              data-testid="btn-new-blank-plant"
              onClick={createNewBlankPlant}
              className="inline-flex min-h-[44px] items-center gap-1 text-xs font-semibold text-cyan-400 transition hover:text-cyan-300 md:min-h-0 md:text-[11px]"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>{t.newBlankPlant}</span>
            </button>

            <div className="flex items-center gap-3">
              <button
                type="button"
                data-testid="btn-reset-demo"
                onClick={() => void resetCurrentPlantToDemo()}
                className="inline-flex min-h-[44px] items-center gap-1 text-xs text-slate-400 transition hover:text-slate-200 md:min-h-0 md:text-[11px]"
              >
                <RotateCcw className="h-3 w-3" />
                <span>{t.resetDemoPlant}</span>
              </button>

              {activeWorkspaceId !== "default" && (
                <button
                  type="button"
                  data-testid="btn-delete-plant"
                  onClick={() => {
                    if (window.confirm(t.confirmDeletePlant)) {
                      void deleteWorkspace(activeWorkspaceId);
                    }
                  }}
                  className="inline-flex min-h-[44px] items-center gap-1 text-xs text-rose-400 transition hover:text-rose-300 md:min-h-0 md:text-[11px]"
                >
                  <Trash2 className="h-3 w-3" />
                  <span>{t.deletePlant}</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Panel B: Instant Quick-Add Actions */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-[#0f1629] p-4 lg:col-span-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Sliders className="h-4 w-4 text-emerald-400" />
              <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                {t.quickAddHubTitle}
              </h2>
            </div>
            <p className="text-[11px] text-slate-400">
              Add factory assets or tweak simulation physics directly without leaving Tab 1.
            </p>

            {/* Quick-Add Buttons Grid */}
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <button
                type="button"
                data-testid="btn-quick-add-press"
                onClick={() => openQuickModal("press")}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-2.5 py-2 text-xs font-medium text-slate-200 transition hover:border-cyan-500/60 hover:bg-slate-800 md:min-h-0"
              >
                <Plus className="h-3.5 w-3.5 text-cyan-400" />
                <span>{t.studioAddPress}</span>
              </button>

              <button
                type="button"
                data-testid="btn-quick-add-mold"
                onClick={() => openQuickModal("mold")}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-2.5 py-2 text-xs font-medium text-slate-200 transition hover:border-cyan-500/60 hover:bg-slate-800 md:min-h-0"
              >
                <Plus className="h-3.5 w-3.5 text-cyan-400" />
                <span>{t.studioAddMold}</span>
              </button>

              <button
                type="button"
                data-testid="btn-quick-add-resin"
                onClick={() => openQuickModal("resin")}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-2.5 py-2 text-xs font-medium text-slate-200 transition hover:border-cyan-500/60 hover:bg-slate-800 md:min-h-0"
              >
                <Plus className="h-3.5 w-3.5 text-cyan-400" />
                <span>{t.studioAddResin}</span>
              </button>

              <button
                type="button"
                data-testid="btn-quick-add-order"
                onClick={() => openQuickModal("order")}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-2.5 py-2 text-xs font-medium text-slate-200 transition hover:border-cyan-500/60 hover:bg-slate-800 md:min-h-0"
              >
                <Plus className="h-3.5 w-3.5 text-cyan-400" />
                <span>{t.studioAddOrder}</span>
              </button>
            </div>
          </div>

          <div className="mt-3 border-t border-slate-800/80 pt-3">
            <button
              type="button"
              data-testid="btn-quick-edit-physics"
              onClick={() => openQuickModal("physics")}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-bold text-cyan-300 transition hover:bg-cyan-500/20 md:min-h-0"
            >
              <Zap className="h-3.5 w-3.5" />
              <span>{t.editPhysicsBtn}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Save As New Plant Modal */}
      {saveAsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setSaveAsModalOpen(false)} />
          <div className="relative z-10 flex max-h-[90dvh] w-full max-w-md flex-col rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl">
            <h3 className="text-sm font-bold text-slate-100">{t.saveAsNewPlant}</h3>
            <p className="mt-1 text-xs text-slate-400">{t.promptPlantName}</p>
            <form onSubmit={handleSaveAsSubmit} className="mt-4 space-y-3">
              <input
                type="text"
                required
                autoFocus
                value={saveAsName}
                onChange={(e) => setSaveAsName(e.target.value)}
                className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base text-slate-200 focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
              />
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSaveAsModalOpen(false)}
                  className="min-h-[44px] rounded-lg bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 md:min-h-0"
                >
                  {t.studioCancel}
                </button>
                <button
                  type="submit"
                  data-testid="btn-confirm-save-as"
                  className="min-h-[44px] rounded-lg bg-cyan-500 px-4 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 md:min-h-0"
                >
                  {t.studioSave}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Clickable KPI Summary Strip (Navigates to Studio Sub-Tabs & Tab 6 Workforce) */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <ClickableStatPill
            label={lang === "ar" ? "الماكينات النشطة" : "Active Presses"}
            value={`${summary.presses_active} / ${summary.presses_total}`}
            testId="stat-pill-presses"
            onClick={() => navigateToStudioSubTab("presses")}
          />
          <ClickableStatPill
            label={lang === "ar" ? "القوالب الفيزيائية" : "Physical Molds"}
            value={`${summary.molds_total} (${summary.molds_needing_pm} PM)`}
            highlight={summary.molds_needing_pm > 0}
            testId="stat-pill-molds"
            onClick={() => navigateToStudioSubTab("molds")}
          />
          <ClickableStatPill
            label={lang === "ar" ? "درجات الخامات" : "Resin Grades"}
            value={String(summary.resins_total)}
            testId="stat-pill-resins"
            onClick={() => navigateToStudioSubTab("resins")}
          />
          <ClickableStatPill
            label={lang === "ar" ? "الأوامر الأسبوعية" : "Weekly Orders"}
            value={`${summary.orders_total} (${summary.export_orders} Export)`}
            testId="stat-pill-orders"
            onClick={() => navigateToStudioSubTab("orders")}
          />
          <ClickableStatPill
            label={lang === "ar" ? "حمل المصنع" : "Plant Load"}
            value={`${summary.plant_load_pct}% (${summary.total_production_hrs}h)`}
            testId="stat-pill-physics"
            onClick={() => navigateToStudioSubTab("physics")}
          />
          <ClickableStatPill
            label={lang === "ar" ? "القوى العاملة" : "Floor Workforce"}
            value={(() => {
              const workers = dataset?.workers ?? [];
              const activeCount = summary.workers_active ?? workers.filter((w) => w.status === "active").length;
              const sickCount = summary.workers_sick ?? workers.filter((w) => w.status === "sick").length;
              return lang === "ar"
                ? `${activeCount} نشط | ${sickCount} مرضي`
                : `${activeCount} Active | ${sickCount} Sick`;
            })()}
            highlight={(summary.workers_sick ?? 0) > 0}
            testId="stat-pill-workforce"
            onClick={() => setActiveView("workforce")}
          />
        </div>
      )}

      {/* Proactive Delay & Bottleneck Risk Radar */}
      <RiskRadarPanel />

      {/* Middle Row: Resin Stock vs Demand + Mold Shot-Count Health */}
      {summary && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Inline-Editable Resin Inventory vs. Weekly Demand */}
          <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Package className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">{t.resinReadiness}</h3>
              </div>
              <span className="text-[11px] text-slate-400">Virgin + Usable Regrind (kg)</span>
            </div>
            <div className="space-y-3.5">
              {summary.resin_balance.map((rb) => {
                const cap = rb.virgin_available_kg + rb.usable_regrind_kg;
                const pct = Math.min(100, Math.round((rb.demand_kg / Math.max(cap, 1)) * 100));
                const isDeficit = rb.deficit_kg > 0;
                const matchingResin = dataset?.resins.find((r) => r.resin_code === rb.resin_code);

                return (
                  <div key={rb.resin_code} className="space-y-1.5 rounded-xl border border-slate-800/60 bg-slate-900/40 p-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-slate-800 px-2 py-0.5 font-mono font-bold text-cyan-300">
                          {rb.resin_code}
                        </span>
                        {rb.drying_lead_time_hrs > 0 && (
                          <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
                            <Flame className="h-3 w-3" />
                            Dry {rb.drying_lead_time_hrs}h • {rb.barrel_temp_c}°C
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span dir="ltr" className="font-mono text-[11px] text-slate-300">
                          {rb.demand_kg.toLocaleString()} / {cap.toLocaleString()} kg ({rb.utilization_pct}%)
                        </span>
                        {matchingResin && (
                          <button
                            type="button"
                            data-testid={`btn-edit-resin-${rb.resin_code}`}
                            onClick={() => openQuickModal("resin", matchingResin)}
                            title={t.editResinInline}
                            className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 transition hover:border-cyan-500 hover:text-cyan-300 md:min-h-0 md:min-w-0 md:p-1"
                          >
                            <Edit3 className="h-3.5 w-3.5 md:h-3 md:w-3" />
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className={`h-full rounded-full transition-all ${
                          isDeficit
                            ? "bg-rose-500"
                            : pct > 80
                              ? "bg-amber-400"
                              : "bg-gradient-to-r from-cyan-500 to-emerald-400"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    {isDeficit && (
                      <div className="text-[11px] font-semibold text-rose-300">
                        Deficit: -{rb.deficit_kg.toLocaleString()} kg (CP-SAT will prioritize export/high-penalty runs)
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Inline-Editable Mold Shot-Count Maintenance Health */}
          <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wrench className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-bold text-white">{t.moldHealthTitle}</h3>
              </div>
              <span className="text-[11px] text-slate-400">HC6 PM Threshold ≥ 95%</span>
            </div>
            <div className="max-h-[340px] space-y-2.5 overflow-y-auto pe-1">
              {summary.mold_health.map((mh) => {
                const matchingMold = dataset?.molds.find((m) => m.mold_id === mh.mold_id);
                return (
                  <div
                    key={mh.mold_id}
                    className={`rounded-xl border px-3 py-2.5 text-xs ${
                      mh.needs_pm
                        ? "border-amber-500/50 bg-amber-500/10"
                        : "border-slate-800 bg-slate-900/60"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="font-mono font-bold text-white">{mh.mold_id}</span>
                        <span className="truncate text-slate-300">{mh.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5 sm:gap-2">
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] font-bold ${
                            mh.needs_pm
                              ? "bg-amber-400 text-slate-950"
                              : "bg-slate-800 text-emerald-300"
                          }`}
                        >
                          {mh.shot_utilization_pct.toFixed(1)}% {mh.needs_pm ? "• PM REQUIRED" : "OK"}
                        </span>

                        {/* One-click PM Reset Button */}
                        <button
                          type="button"
                          data-testid={`btn-log-pm-${mh.mold_id}`}
                          onClick={() => handleResetMold(mh.mold_id)}
                          title={t.logPmResetShots}
                          className={`inline-flex min-h-[36px] items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-bold transition md:min-h-0 md:px-2 md:py-0.5 ${
                            mh.needs_pm
                              ? "border border-amber-400 bg-amber-400/20 text-amber-200 hover:bg-amber-400/30"
                              : "border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                          }`}
                        >
                          <RefreshCw className="h-3 w-3 md:h-2.5 md:w-2.5" />
                          <span>PM</span>
                        </button>

                        {/* Mold Edit Button */}
                        {matchingMold && (
                          <button
                            type="button"
                            data-testid={`btn-edit-mold-${mh.mold_id}`}
                            onClick={() => openQuickModal("mold", matchingMold)}
                            title={t.editMoldInline}
                            className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 transition hover:border-cyan-500 hover:text-cyan-300 md:min-h-0 md:min-w-0 md:p-1"
                          >
                            <Edit3 className="h-3.5 w-3.5 md:h-3 md:w-3" />
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
                      <span>
                        {mh.cavities} cav • {mh.cycle_time_sec}s • {mh.is_hot_runner ? "Hot-Runner" : "Cold-Runner"}
                      </span>
                      <span dir="ltr" className="font-mono">
                        {mh.current_shots.toLocaleString()} / {mh.maintenance_interval_shots.toLocaleString()} shots
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Pre-Solve Plant Anomaly Diagnostics */}
      {validation && (
        <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <h3 className="text-sm font-bold text-white">{t.diagnosticsTitle}</h3>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  validation.ready
                    ? "border border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                    : "border border-rose-500/40 bg-rose-500/15 text-rose-300"
                }`}
              >
                {validation.ready ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                {validation.ready ? t.readyBadge : t.blockedBadge}
              </span>
            </div>
            <button
              type="button"
              data-testid="btn-proceed-optimize"
              disabled={!validation.ready || loading}
              onClick={() => {
                setActiveView("console");
                void runSolve();
              }}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-40 sm:w-auto md:min-h-0"
            >
              <Play className="h-3.5 w-3.5" />
              <span>{t.proceedToOptimize}</span>
            </button>
          </div>

          {validation.issues.length === 0 ? (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-200">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>{t.noAnomalies}</span>
            </div>
          ) : (
            <div className="space-y-2">
              {validation.issues.map((issue, i) => (
                <div
                  key={`${issue.code}-${i}`}
                  className={`flex items-start gap-2.5 rounded-xl border p-3 text-xs ${
                    issue.severity === "error"
                      ? "border-rose-500/40 bg-rose-500/10 text-rose-100"
                      : issue.severity === "warning"
                        ? "border-amber-500/40 bg-amber-500/10 text-amber-100"
                        : "border-cyan-500/30 bg-cyan-500/10 text-cyan-100"
                  }`}
                >
                  {issue.severity === "error" ? (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  ) : issue.severity === "warning" ? (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                  ) : (
                    <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
                  )}
                  <div>
                    <span className="font-mono text-[11px] font-bold opacity-80">[{issue.code}]</span>{" "}
                    <span>{issue.message}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Press Fleet Cards */}
      {dataset && (
        <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Factory className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white">{t.pressFleetTitle}</h3>
            </div>
            <button
              type="button"
              onClick={() => navigateToStudioSubTab("presses")}
              className="inline-flex min-h-[44px] items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300 md:min-h-0 md:text-[11px]"
            >
              <span>{t.studioSubPresses}</span>
              <ArrowRight className="h-3 w-3 rtl:rotate-180" />
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {dataset.presses.map((p) => (
              <div
                key={p.machine_id}
                onClick={() => openQuickModal("press", p)}
                className="cursor-pointer rounded-xl border border-slate-800 bg-slate-900/70 p-3.5 text-xs hover:border-cyan-500/50 hover:bg-slate-900 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-cyan-300 group-hover:text-cyan-200">{p.machine_id}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-300">
                    {p.tonnage}T • {p.process_type}
                  </span>
                </div>
                <div className="mt-1 font-semibold text-white">{p.name}</div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                  <span>{p.supports_hot_runner ? "Hot-Runner Ready" : "Cold-Runner Only"}</span>
                  <span dir="ltr" className="font-mono">
                    {p.hourly_energy_kwh} kWh/h
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ClickableStatPill({
  label,
  value,
  testId,
  highlight = false,
  onClick,
}: {
  label: string;
  value: string;
  testId: string;
  highlight?: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      data-testid={testId}
      className={`cursor-pointer rounded-xl border px-3.5 py-3 transition-all hover:border-cyan-500/60 hover:bg-slate-900 group ${
        highlight ? "border-amber-500/40 bg-amber-500/10" : "border-slate-800 bg-[#0f1629]"
      }`}
    >
      <div className="flex items-center justify-between text-[11px] text-slate-400">
        <span>{label}</span>
        <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-400 rtl:rotate-180" />
      </div>
      <div className={`mt-1 text-sm font-bold ${highlight ? "text-amber-300" : "text-white"}`}>
        {value}
      </div>
    </div>
  );
}
