"use client";

import React, { useState } from "react";
import {
  ArrowUpRight,
  Award,
  Check,
  ChevronDown,
  ChevronUp,
  Edit3,
  Layers,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { Currency, PinnedScenario, PinnedSlotId } from "@/lib/types";

interface MetricRowSpec {
  id: string;
  label: string;
  direction: "higher" | "lower" | "none";
  getValue: (snap: PinnedScenario, targetCurrency: Currency) => number | null;
  renderPrimary: (snap: PinnedScenario, targetCurrency: Currency) => string;
  renderSecondary?: (snap: PinnedScenario, targetCurrency: Currency) => string;
  formatDelta?: (delta: number, targetCurrency: Currency) => string;
}

function toDisplayMoney(snap: PinnedScenario, amount: number, targetCurrency: Currency): number {
  return convertCurrency(amount, snap.result.currency, targetCurrency, snap.result.fx_egp_per_sar);
}

function formatSignedMoney(delta: number, currency: Currency): string {
  if (Math.abs(delta) < 0.5) return "0";
  const sign = delta > 0 ? "+" : "-";
  return `${sign}${formatMoney(Math.abs(delta), currency)}`;
}

function formatSignedNumber(delta: number, suffix: string, decimals = 1): string {
  if (Math.abs(delta) < 0.05) return `0${suffix}`;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(decimals)}${suffix}`;
}

export function ScenarioComparisonMatrix() {
  const {
    lang,
    currency,
    result,
    pinnedScenarios,
    renamePinnedScenario,
    removePinnedScenario,
    clearPinnedScenarios,
    promotePinnedScenario,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";
  const [collapsed, setCollapsed] = useState(false);
  const [editingSlot, setEditingSlot] = useState<PinnedSlotId | null>(null);
  const [draftLabel, setDraftLabel] = useState("");

  if (pinnedScenarios.length === 0) return null;

  const anchor = pinnedScenarios[0];

  const rows: MetricRowSpec[] = [
    {
      id: "net_profit",
      label: t.compareRowNetProfit,
      direction: "higher",
      getValue: (s, cur) => {
        const fin = s.result.financials?.optimized;
        return fin ? toDisplayMoney(s, fin.net_operating_profit, cur) : null;
      },
      renderPrimary: (s, cur) => {
        const fin = s.result.financials?.optimized;
        return fin ? formatMoney(toDisplayMoney(s, fin.net_operating_profit, cur), cur) : "—";
      },
      renderSecondary: (s) => {
        const fin = s.result.financials?.optimized;
        return fin ? `${fin.net_margin_pct.toFixed(1)}% ${isAr ? "هامش صافي" : "net margin"}` : "";
      },
      formatDelta: (d, cur) => formatSignedMoney(d, cur),
    },
    {
      id: "weekly_savings",
      label: t.compareRowWeeklySavings,
      direction: "higher",
      getValue: (s, cur) => toDisplayMoney(s, s.result.scorecard.cash_savings, cur),
      renderPrimary: (s, cur) =>
        formatMoney(toDisplayMoney(s, s.result.scorecard.cash_savings, cur), cur),
      renderSecondary: (s, cur) => {
        const ann = s.result.financials?.annual_projected_savings;
        if (ann !== undefined) {
          return `${formatMoney(toDisplayMoney(s, ann, cur), cur)}/${isAr ? "سنة" : "yr"}`;
        }
        return `${s.result.scorecard.cash_savings_pct.toFixed(1)}% vs FIFO`;
      },
      formatDelta: (d, cur) => formatSignedMoney(d, cur),
    },
    {
      id: "otif",
      label: t.compareRowOtif,
      direction: "higher",
      getValue: (s) => s.result.optimized.kpis.otif_pct,
      renderPrimary: (s) => `${s.result.optimized.kpis.otif_pct.toFixed(1)}%`,
      renderSecondary: (s) =>
        `${s.result.optimized.kpis.late_orders} ${t.compareLateOrders}`,
      formatDelta: (d) => formatSignedNumber(d, "%", 1),
    },
    {
      id: "purge_scrap",
      label: t.compareRowScrap,
      direction: "lower",
      getValue: (s) => s.result.optimized.kpis.purge_scrap_kg,
      renderPrimary: (s) => `${s.result.optimized.kpis.purge_scrap_kg.toFixed(1)} kg`,
      renderSecondary: (s) =>
        `${s.result.optimized.kpis.changeover_hours.toFixed(2)}h ${isAr ? "تبديل" : "changeover"}`,
      formatDelta: (d) => formatSignedNumber(d, " kg", 1),
    },
    {
      id: "labor_cost",
      label: t.compareRowLabor,
      direction: "lower",
      getValue: (s, cur) => {
        const labor =
          s.result.financials?.optimized.direct_labor_and_overtime_cost ??
          s.result.workforce?.optimized.kpis.total_labor_cost ??
          null;
        return labor !== null ? toDisplayMoney(s, labor, cur) : null;
      },
      renderPrimary: (s, cur) => {
        const labor =
          s.result.financials?.optimized.direct_labor_and_overtime_cost ??
          s.result.workforce?.optimized.kpis.total_labor_cost ??
          null;
        return labor !== null ? formatMoney(toDisplayMoney(s, labor, cur), cur) : "—";
      },
      renderSecondary: (s) => {
        const ot = s.result.workforce?.optimized.kpis.overtime_hours;
        return ot !== undefined ? `${ot.toFixed(1)} ${t.compareOvertimeHrs}` : "";
      },
      formatDelta: (d, cur) => formatSignedMoney(d, cur),
    },
    {
      id: "risk_radar",
      label: t.compareRowRisk,
      direction: "lower",
      getValue: (s, cur) => {
        const rr = s.result.risk_radar;
        return rr ? toDisplayMoney(s, rr.total_financial_exposure, cur) : null;
      },
      renderPrimary: (s, cur) => {
        const rr = s.result.risk_radar;
        return rr ? formatMoney(toDisplayMoney(s, rr.total_financial_exposure, cur), cur) : "—";
      },
      renderSecondary: (s) => {
        const rr = s.result.risk_radar;
        if (!rr) return "";
        const hi = rr.critical_count + rr.elevated_count;
        return `${hi} ${t.compareActiveAlerts} • ${isAr ? "مؤشر" : "Score"} ${rr.overall_risk_score}`;
      },
      formatDelta: (d, cur) => formatSignedMoney(d, cur),
    },
  ];

  const renderTogglesSummary = (snap: PinnedScenario): string[] => {
    const cfg = snap.solverConfig;
    const sc = cfg.scenarios;
    const tags: string[] = [];
    if (cfg.ramadan_shift_mode) tags.push(isAr ? "رمضان 6س" : "Ramadan 6h");
    if (cfg.avoid_peak_tariff_hrs) tags.push(isAr ? "تجنب الذروة" : "Peak Tariff Avoid");
    if (cfg.autonomous_pm_window) tags.push(isAr ? "صيانة ذاتية" : "Auto PM");
    if (sc.machine_breakdowns.length > 0) {
      tags.push(
        ...sc.machine_breakdowns.map((b) =>
          isAr ? `عطل ${b.machine_id} (${b.duration_hrs}س)` : `${b.machine_id} -${b.duration_hrs}h`
        )
      );
    }
    if (sc.resin_shortages.length > 0) {
      tags.push(
        ...sc.resin_shortages.map((r) => `${r.resin_code} -${r.available_pct_reduction}%`)
      );
    }
    if (sc.rush_orders.length > 0) {
      tags.push(isAr ? `+${sc.rush_orders.length} أمر عاجل` : `+${sc.rush_orders.length} Rush`);
    }
    if (sc.mold_pm_locks.length > 0) {
      tags.push(...sc.mold_pm_locks.map((m) => `PM ${m.mold_id}`));
    }
    return tags;
  };

  const commitRename = (slot: PinnedSlotId) => {
    if (draftLabel.trim()) {
      renamePinnedScenario(slot, draftLabel);
    }
    setEditingSlot(null);
    setDraftLabel("");
  };

  return (
    <section
      data-testid="scenario-comparison-matrix"
      className="rounded-2xl border border-cyan-500/30 bg-gradient-to-b from-[#0f172a] to-[#0b1120] p-4 shadow-xl shadow-black/30"
    >
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-300">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">{t.compareMatrixTitle}</h3>
              <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-300">
                {pinnedScenarios.length}/3
              </span>
            </div>
            <p className="text-[11px] text-slate-400">{t.compareMatrixSubtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="btn-clear-pinned"
            onClick={clearPinnedScenarios}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:border-rose-500/50 hover:text-rose-200"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>{t.compareClearAllBtn}</span>
          </button>
          <button
            type="button"
            data-testid="btn-toggle-compare-collapse"
            onClick={() => setCollapsed((c) => !c)}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-200 transition hover:border-slate-600"
          >
            {collapsed ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="mt-4 space-y-3">
          {pinnedScenarios.length === 1 && (
            <div className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              <Sparkles className="h-4 w-4 shrink-0 text-amber-300" />
              <span>{t.comparePinSecondHint}</span>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="w-56 px-3 py-3 text-start text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    {isAr ? "المؤشر التنفيذي" : "Executive KPI"}
                  </th>
                  {pinnedScenarios.map((snap, idx) => {
                    const isActive = result?.run_id === snap.result.run_id;
                    const isEditing = editingSlot === snap.slot;
                    return (
                      <th
                        key={snap.id}
                        data-testid={`compare-col-${snap.slot}`}
                        className="px-3 py-3 text-start align-top"
                      >
                        <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-2.5">
                          <div className="mb-1.5 flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-cyan-500/20 font-mono text-[11px] font-bold text-cyan-300">
                                {snap.slot}
                              </span>
                              {idx === 0 && (
                                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-semibold text-slate-300">
                                  {t.compareAnchorBadge}
                                </span>
                              )}
                              {isActive && (
                                <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
                                  {t.comparePromotedBadge}
                                </span>
                              )}
                            </div>
                            <button
                              type="button"
                              data-testid={`btn-remove-pin-${snap.slot}`}
                              onClick={() => removePinnedScenario(snap.slot)}
                              className="text-slate-500 transition hover:text-rose-300"
                              title={isAr ? "حذف" : "Remove"}
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          {/* Editable Label */}
                          {isEditing ? (
                            <div className="mb-2 flex items-center gap-1">
                              <input
                                type="text"
                                data-testid={`input-rename-pin-${snap.slot}`}
                                value={draftLabel}
                                onChange={(e) => setDraftLabel(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") commitRename(snap.slot);
                                  if (e.key === "Escape") setEditingSlot(null);
                                }}
                                autoFocus
                                className="w-full rounded border border-cyan-500/60 bg-slate-950 px-2 py-1 text-xs font-semibold text-white focus:outline-none"
                              />
                              <button
                                type="button"
                                onClick={() => commitRename(snap.slot)}
                                className="rounded bg-cyan-500 p-1 text-slate-950 hover:bg-cyan-400"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ) : (
                            <div className="mb-2 flex items-center justify-between gap-1">
                              <span
                                data-testid={`label-pin-${snap.slot}`}
                                className="truncate text-xs font-bold text-white"
                              >
                                {snap.label}
                              </span>
                              <button
                                type="button"
                                data-testid={`btn-rename-pin-${snap.slot}`}
                                onClick={() => {
                                  setEditingSlot(snap.slot);
                                  setDraftLabel(snap.label);
                                }}
                                className="shrink-0 text-slate-500 hover:text-cyan-300"
                                title={t.compareRenameHint}
                              >
                                <Edit3 className="h-3 w-3" />
                              </button>
                            </div>
                          )}

                          {/* Promote to Active Plan CTA */}
                          <button
                            type="button"
                            data-testid={`btn-promote-pin-${snap.slot}`}
                            onClick={() => promotePinnedScenario(snap.slot)}
                            className={`inline-flex w-full items-center justify-center gap-1 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition ${
                              isActive
                                ? "border border-emerald-500/40 bg-emerald-500/15 text-emerald-200"
                                : "border border-cyan-500/40 bg-cyan-500/15 text-cyan-200 hover:bg-cyan-500 hover:text-slate-950"
                            }`}
                          >
                            <ArrowUpRight className="h-3.5 w-3.5" />
                            <span>{t.comparePromoteBtn}</span>
                          </button>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-800/70">
                {rows.map((row) => {
                  const vals = pinnedScenarios.map((s) => row.getValue(s, currency));
                  const validNums = vals.filter((v): v is number => v !== null);
                  let bestVal: number | null = null;
                  if (pinnedScenarios.length >= 2 && validNums.length >= 2) {
                    bestVal =
                      row.direction === "higher"
                        ? Math.max(...validNums)
                        : row.direction === "lower"
                        ? Math.min(...validNums)
                        : null;
                  }
                  const anchorVal = row.getValue(anchor, currency);

                  return (
                    <tr key={row.id} className="hover:bg-slate-900/40">
                      <td className="px-3 py-3 font-medium text-slate-300">{row.label}</td>
                      {pinnedScenarios.map((snap, idx) => {
                        const v = vals[idx];
                        const isBest =
                          bestVal !== null &&
                          v !== null &&
                          Math.abs(v - bestVal) < 1e-4 &&
                          validNums.some((other) => Math.abs(other - bestVal!) > 1e-4);

                        const delta =
                          idx > 0 && v !== null && anchorVal !== null ? v - anchorVal : null;
                        const deltaIsGood =
                          delta !== null && Math.abs(delta) > 0.05
                            ? row.direction === "higher"
                              ? delta > 0
                              : delta < 0
                            : null;

                        return (
                          <td
                            key={`${row.id}_${snap.id}`}
                            data-testid={`compare-cell-${row.id}-${snap.slot}`}
                            className="px-3 py-3 align-top"
                          >
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span
                                className={`font-mono text-xs font-bold ${
                                  isBest ? "text-emerald-300" : "text-white"
                                }`}
                              >
                                {row.renderPrimary(snap, currency)}
                              </span>
                              {isBest && (
                                <span
                                  data-testid={`compare-best-${row.id}-${snap.slot}`}
                                  className="inline-flex items-center gap-0.5 rounded-full border border-emerald-400/40 bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase text-emerald-300"
                                >
                                  <Award className="h-2.5 w-2.5" />
                                  {t.compareBestBadge}
                                </span>
                              )}
                            </div>

                            {row.renderSecondary && (
                              <div className="mt-0.5 font-mono text-[10px] text-slate-400">
                                {row.renderSecondary(snap, currency)}
                              </div>
                            )}

                            {delta !== null && row.formatDelta && (
                              <div
                                className={`mt-1 font-mono text-[10px] font-semibold ${
                                  deltaIsGood === null
                                    ? "text-slate-500"
                                    : deltaIsGood
                                    ? "text-emerald-400"
                                    : "text-rose-400"
                                }`}
                              >
                                {isAr ? "مقابل A: " : "vs A: "}
                                {row.formatDelta(delta, currency)}
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}

                {/* Active Disruptions & Toggles Summary Row */}
                <tr className="hover:bg-slate-900/40">
                  <td className="px-3 py-3 font-medium text-slate-300">{t.compareRowToggles}</td>
                  {pinnedScenarios.map((snap) => {
                    const tags = renderTogglesSummary(snap);
                    return (
                      <td key={`toggles_${snap.id}`} className="px-3 py-3 align-top">
                        {tags.length === 0 ? (
                          <span className="rounded bg-slate-800/80 px-2 py-0.5 text-[10px] text-slate-400">
                            {t.compareNoDisruptions}
                          </span>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {tags.map((tag, i) => (
                              <span
                                key={i}
                                className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-200"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
