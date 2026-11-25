"use client";

import React, { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Layers,
  Maximize2,
  Minimize2,
  Recycle,
} from "lucide-react";
import { RiskRadarPanel } from "@/components/RiskRadarPanel";
import { ScheduleExportMenu } from "@/components/ScheduleExportMenu";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { COLOR_LABELS, COPY, DAY_NAMES_I18N } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { GanttBlock, PlasticColor } from "@/lib/types";

const PLASTIC_BLOCK_STYLE: Record<PlasticColor, { bg: string; text: string; border: string; swatch: string }> = {
  Natural: { bg: "bg-slate-200/90", text: "text-slate-900", border: "border-slate-300", swatch: "#e2e8f0" },
  White: { bg: "bg-white", text: "text-slate-950", border: "border-slate-300", swatch: "#ffffff" },
  Yellow: { bg: "bg-yellow-400", text: "text-slate-950", border: "border-yellow-300", swatch: "#facc15" },
  Blue: { bg: "bg-blue-500", text: "text-white", border: "border-blue-400", swatch: "#3b82f6" },
  Red: { bg: "bg-red-500", text: "text-white", border: "border-red-400", swatch: "#ef4444" },
  Black: { bg: "bg-zinc-900", text: "text-zinc-100", border: "border-zinc-500", swatch: "#18181b" },
};

export function ProductionGanttView() {
  const { lang, config, result } = useApp();
  const t = COPY[lang];
  const days = DAY_NAMES_I18N[lang];
  const [planMode, setPlanMode] = useState<"optimized" | "baseline">("optimized");
  const [zoomDetailed, setZoomDetailed] = useState(false);
  const [hovered, setHovered] = useState<GanttBlock | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<GanttBlock | null>(null);

  const activeBlock = hovered ?? selectedBlock;

  const plan = result ? (planMode === "optimized" ? result.optimized : result.baseline) : null;
  const baseHorizonMins = (config.physics?.horizon_hrs ?? 168) * 60;

  const horizonMins = useMemo(() => {
    if (!plan) return baseHorizonMins;
    const maxEnd = plan.gantt_blocks.reduce((acc, b) => Math.max(acc, b.end_min), baseHorizonMins);
    return Math.max(baseHorizonMins, Math.ceil(maxEnd / 1440) * 1440);
  }, [plan, baseHorizonMins]);

  const totalDays = Math.round(horizonMins / 1440);

  const resinChartData = useMemo(() => {
    if (!result) return [];
    const baseByCode = new Map(result.baseline.resin_usage.map((r) => [r.resin_code, r]));
    return result.optimized.resin_usage.map((r) => {
      const b = baseByCode.get(r.resin_code);
      return {
        resin: r.resin_code,
        Virgin: r.virgin_used_kg,
        Regrind: r.regrind_used_kg,
        OptScrap: r.purge_scrap_kg,
        FifoScrap: b ? b.purge_scrap_kg : 0,
      };
    });
  }, [result]);

  if (!result || !plan) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-10 text-center">
        <Activity className="mx-auto mb-3 h-8 w-8 text-cyan-400" />
        <p className="text-sm text-slate-300">{t.noResultYet}</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-full min-w-0 space-y-6">
      {/* Compact Proactive Risk Radar Strip */}
      <RiskRadarPanel compact />

      {/* Press-by-Press Production Gantt Card */}
      <div className="dios-card w-full max-w-full min-w-0 overflow-hidden rounded-2xl p-5">
        <div className="mb-4 flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-white">{t.ganttTitle}</h2>
            <p className="mt-0.5 text-xs text-slate-400">{t.ganttSubtitle}</p>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <ScheduleExportMenu compact testIdPrefix="gantt-top-export" />
            <button
              type="button"
              data-testid="gantt-zoom-toggle"
              onClick={() => setZoomDetailed((z) => !z)}
              className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-white md:min-h-0"
            >
              {zoomDetailed ? <Minimize2 className="h-3.5 w-3.5 shrink-0 text-cyan-400" /> : <Maximize2 className="h-3.5 w-3.5 shrink-0 text-cyan-400" />}
              <span>{zoomDetailed ? t.ganttZoomFit : t.ganttZoomDetailed}</span>
            </button>
            <div className="inline-flex min-h-[44px] max-w-full flex-wrap items-center gap-1 rounded-xl border border-slate-700 bg-slate-900 p-1 text-xs font-semibold md:min-h-0">
              <button
                type="button"
                data-testid="gantt-mode-optimized"
                onClick={() => setPlanMode("optimized")}
                className={`min-h-[36px] rounded-lg px-2.5 py-1 transition sm:px-3 md:min-h-0 ${
                  planMode === "optimized" ? "bg-cyan-500 text-slate-950" : "text-slate-400 hover:text-white"
                }`}
              >
                {t.showOptimized} ({result.optimized.kpis.purge_scrap_kg.toFixed(0)} kg)
              </button>
              <button
                type="button"
                data-testid="gantt-mode-baseline"
                onClick={() => setPlanMode("baseline")}
                className={`min-h-[36px] rounded-lg px-2.5 py-1 transition sm:px-3 md:min-h-0 ${
                  planMode === "baseline" ? "bg-amber-500 text-slate-950" : "text-slate-400 hover:text-white"
                }`}
              >
                {t.showBaseline} ({result.baseline.kpis.purge_scrap_kg.toFixed(0)} kg)
              </button>
            </div>
          </div>
        </div>

        {/* Visual Plastic Color & Hatch Legend */}
        <div className="mb-4 flex flex-wrap items-center gap-2.5 text-[11px] text-slate-300">
          {(["Natural", "White", "Yellow", "Blue", "Red", "Black"] as PlasticColor[]).map((col, idx) => (
            <span
              key={col}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900/70 px-2 py-1"
            >
              <span
                className="h-3 w-3 rounded-sm border border-slate-500"
                style={{ backgroundColor: PLASTIC_BLOCK_STYLE[col].swatch }}
              />
              <span>
                {idx + 1}. {COLOR_LABELS[lang][col]}
              </span>
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/40 bg-slate-900/70 px-2 py-1 text-amber-200">
            <span className="hatch-changeover h-3 w-4 rounded-sm border border-amber-400" />
            <span>Changeover / Purge</span>
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border border-rose-500/40 bg-slate-900/70 px-2 py-1 text-rose-200">
            <span className="hatch-breakdown h-3 w-4 rounded-sm border border-rose-400" />
            <span>Breakdown / Maint</span>
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border border-purple-500/40 bg-slate-900/70 px-2 py-1 text-purple-200">
            <span className="hatch-pm h-3 w-4 rounded-sm border border-purple-400" />
            <span>Mold PM Block</span>
          </span>
          {config.avoid_peak_tariff_hrs && (
            <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/35 bg-amber-500/10 px-2 py-1 text-amber-200">
              <span className="band-peak-tariff h-3 w-4 rounded-sm" />
              <span>{t.ganttPeakBand}</span>
            </span>
          )}
          {config.ramadan_shift_mode && (
            <span className="inline-flex items-center gap-1.5 rounded-md border border-indigo-400/35 bg-indigo-500/10 px-2 py-1 text-indigo-200">
              <span className="band-ramadan-iftar h-3 w-4 rounded-sm" />
              <span>{t.ganttIftarBand}</span>
            </span>
          )}
        </div>

        {/* Mobile-only Scroll & Tap Hint */}
        <div
          data-testid="gantt-mobile-swipe-hint"
          className="mb-2 flex items-center justify-between text-[11px] font-medium text-cyan-300 lg:hidden"
        >
          <span>{lang === "ar" ? "اضغط على أي أمر لعرض التفاصيل" : "Tap any block to inspect"}</span>
          <span>{t.ganttSwipeHint}</span>
        </div>

        {/* Horizontal Timeline Container (always LTR time axis so Sun -> Sat reads cleanly) */}
        <div dir="ltr" className="w-full max-w-full min-w-0 overflow-x-auto touch-pan-x pb-2" data-testid="press-gantt-chart">
          <div className={zoomDetailed ? "w-full min-w-[1680px]" : "w-full min-w-[920px]"}>
            {/* Day Scale Header */}
            <div className="mb-2 flex items-center">
              <div className="sticky start-0 z-20 w-32 shrink-0 bg-[#0d1526]/95 pe-2 text-[11px] font-semibold text-slate-400 backdrop-blur-sm sm:w-44">
                Press / OEE
              </div>
              <div className="relative flex flex-1 border-b border-slate-800 pb-1.5 text-[11px] font-mono text-slate-400">
                {Array.from({ length: totalDays }).map((_, d) => (
                  <div
                    key={d}
                    style={{ width: `${100 / totalDays}%` }}
                    className="border-s border-slate-800/80 ps-1.5"
                  >
                    {days[d % 7]} <span className="text-slate-500">H{d * 24}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Press Rows */}
            <div className="space-y-2.5">
              {plan.press_summaries.map((ps) => {
                const blocks = plan.gantt_blocks.filter(
                  (b) => b.machine_id === ps.machine_id && b.block_type !== "mold_pm"
                );
                return (
                  <div
                    key={ps.machine_id}
                    data-testid={`gantt-row-${ps.machine_id}`}
                    className="flex items-center gap-2"
                  >
                    {/* Sticky Inline-Start Press Label */}
                    <div className="sticky start-0 z-20 w-32 shrink-0 rounded-xl border border-slate-800 bg-slate-900/95 px-2 py-2 shadow-md backdrop-blur-sm sm:w-44 sm:px-2.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono font-bold text-cyan-300">{ps.machine_id}</span>
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-emerald-300">
                          {ps.oee_pct.toFixed(0)}% OEE
                        </span>
                      </div>
                      <div className="mt-0.5 truncate text-[10px] text-slate-400">
                        {ps.tonnage}T • {ps.jobs_count} jobs • {ps.purge_scrap_kg.toFixed(0)}kg scrap
                      </div>
                    </div>

                    {/* Timeline Track */}
                    <div className="relative h-12 flex-1 overflow-hidden rounded-xl border border-slate-800/90 bg-slate-950/90">
                      {/* Day gridlines */}
                      {Array.from({ length: totalDays }).map((_, d) => (
                        <div
                          key={d}
                          style={{ left: `${(d / totalDays) * 100}%` }}
                          className="pointer-events-none absolute inset-y-0 border-s border-slate-800/60"
                        />
                      ))}

                      {/* Shaded Peak Tariff (13:00-17:00) & Ramadan Iftar (18:00-20:00) Overlay Bands */}
                      {config.avoid_peak_tariff_hrs &&
                        Array.from({ length: totalDays }).map((_, d) => {
                          const pStart = d * 1440 + (config.physics?.peak_start_hr ?? 13) * 60;
                          const pEnd = d * 1440 + (config.physics?.peak_end_hr ?? 17) * 60;
                          if (pStart >= horizonMins) return null;
                          return (
                            <div
                              key={`pk-${d}`}
                              style={{
                                left: `${(pStart / horizonMins) * 100}%`,
                                width: `${((Math.min(pEnd, horizonMins) - pStart) / horizonMins) * 100}%`,
                              }}
                              className="band-peak-tariff pointer-events-none absolute inset-y-0"
                            />
                          );
                        })}
                      {config.ramadan_shift_mode &&
                        Array.from({ length: totalDays }).map((_, d) => {
                          const rStart = d * 1440 + 18 * 60;
                          const rEnd = d * 1440 + 20 * 60;
                          if (rStart >= horizonMins) return null;
                          return (
                            <div
                              key={`rm-${d}`}
                              style={{
                                left: `${(rStart / horizonMins) * 100}%`,
                                width: `${((Math.min(rEnd, horizonMins) - rStart) / horizonMins) * 100}%`,
                              }}
                              className="band-ramadan-iftar pointer-events-none absolute inset-y-0"
                            />
                          );
                        })}

                      {/* Render Blocks */}
                      {blocks.map((b) => {
                        const leftPct = (b.start_min / horizonMins) * 100;
                        const widthPct = Math.max(0.6, ((b.end_min - b.start_min) / horizonMins) * 100);
                        const isSelected = selectedBlock?.block_id === b.block_id;

                        if (b.block_type === "production" && b.color) {
                          const st = PLASTIC_BLOCK_STYLE[b.color];
                          return (
                            <button
                              type="button"
                              key={b.block_id}
                              data-testid={`gantt-block-${b.block_id}`}
                              onClick={() => setSelectedBlock((prev) => (prev?.block_id === b.block_id ? null : b))}
                              onMouseEnter={() => setHovered(b)}
                              onMouseLeave={() => setHovered(null)}
                              style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                              className={`absolute top-1.5 bottom-1.5 flex cursor-pointer items-center overflow-hidden rounded-md border px-1.5 text-[10px] font-bold shadow-sm transition hover:z-20 hover:ring-2 hover:ring-cyan-400 ${st.bg} ${st.text} ${st.border} ${
                                isSelected ? "z-20 ring-2 ring-cyan-400" : ""
                              }`}
                            >
                              <span className="truncate">
                                {b.order_id} • {b.mold_id}
                              </span>
                            </button>
                          );
                        }

                        const hatchCls =
                          b.block_type === "changeover"
                            ? "hatch-changeover border-amber-400/80 text-amber-100 z-10"
                            : b.block_type === "mold_pm"
                              ? "hatch-pm border-purple-400/80 text-purple-100 z-10"
                              : "hatch-breakdown border-rose-400/80 text-rose-100 z-10";

                        return (
                          <button
                            type="button"
                            key={b.block_id}
                            data-testid={`gantt-block-${b.block_id}`}
                            onClick={() => setSelectedBlock((prev) => (prev?.block_id === b.block_id ? null : b))}
                            onMouseEnter={() => setHovered(b)}
                            onMouseLeave={() => setHovered(null)}
                            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                            className={`absolute top-1.5 bottom-1.5 flex cursor-pointer items-center justify-center overflow-hidden rounded-sm border text-[9px] font-bold ${hatchCls} ${
                              isSelected ? "z-20 ring-2 ring-cyan-400" : ""
                            }`}
                          >
                            {widthPct > 3 && <span className="truncate px-1">{b.block_type.toUpperCase()}</span>}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}

              {/* Dedicated Toolroom / Mold PM Row (non-overlapping with press production rows) */}
              {plan.gantt_blocks.some((b) => b.block_type === "mold_pm") && (
                <div data-testid="gantt-row-TOOLROOM" className="flex items-center gap-2 pt-1">
                  <div className="sticky start-0 z-20 w-32 shrink-0 rounded-xl border border-purple-500/40 bg-[#130d26]/95 px-2 py-2 shadow-md backdrop-blur-sm sm:w-44 sm:px-2.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-bold text-purple-300">TOOLROOM</span>
                      <span className="rounded bg-purple-500/20 px-1.5 py-0.5 font-mono text-[10px] text-purple-200">
                        HC6 PM
                      </span>
                    </div>
                    <div className="mt-0.5 truncate text-[10px] text-purple-200/80">
                      {planMode === "optimized" && config.autonomous_pm_window
                        ? t.autoPmModeTag
                        : t.staticPmModeTag}
                    </div>
                  </div>
                  <div className="relative h-10 flex-1 overflow-hidden rounded-xl border border-purple-500/30 bg-slate-950/90">
                    {Array.from({ length: totalDays }).map((_, d) => (
                      <div
                        key={d}
                        style={{ left: `${(d / totalDays) * 100}%` }}
                        className="pointer-events-none absolute inset-y-0 border-s border-slate-800/60"
                      />
                    ))}
                    {plan.gantt_blocks
                      .filter((b) => b.block_type === "mold_pm")
                      .map((b) => {
                        const leftPct = (b.start_min / horizonMins) * 100;
                        const widthPct = Math.max(2.5, ((b.end_min - b.start_min) / horizonMins) * 100);
                        const isSelected = selectedBlock?.block_id === b.block_id;
                        return (
                          <button
                            type="button"
                            key={b.block_id}
                            data-testid={`gantt-block-${b.block_id}`}
                            onClick={() => setSelectedBlock((prev) => (prev?.block_id === b.block_id ? null : b))}
                            onMouseEnter={() => setHovered(b)}
                            onMouseLeave={() => setHovered(null)}
                            style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                            className={`hatch-pm absolute top-1.5 bottom-1.5 flex cursor-pointer items-center justify-center overflow-hidden rounded-md border border-purple-400 px-1.5 text-[10px] font-bold text-purple-100 ${
                              isSelected ? "z-20 ring-2 ring-cyan-400" : ""
                            }`}
                          >
                            <span className="truncate">{b.mold_id} PM</span>
                          </button>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Interactive Tap / Hover Inspector Card */}
        <div
          data-testid="gantt-inspect-card"
          className="mt-3 min-h-[44px] rounded-xl border border-slate-800 bg-slate-950/80 px-3.5 py-2.5 text-xs text-slate-300"
        >
          {activeBlock ? (
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:flex-wrap sm:items-center">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded bg-cyan-500/20 px-2 py-0.5 font-mono font-bold text-cyan-300">
                  {activeBlock.machine_id}
                </span>
                <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] font-bold uppercase text-slate-300">
                  {activeBlock.block_type}
                </span>
                <span className="font-semibold text-white">{activeBlock.label}</span>
                {activeBlock.mold_id && (
                  <span className="rounded bg-indigo-500/15 px-1.5 py-0.5 font-mono text-[11px] text-indigo-200">
                    {activeBlock.mold_id}
                  </span>
                )}
                {activeBlock.resin_code && (
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-slate-200">
                    {activeBlock.resin_code} • {activeBlock.color ? COLOR_LABELS[lang][activeBlock.color] : ""}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div dir="ltr" className="font-mono text-[11px] text-slate-300">
                  H{(activeBlock.start_min / 60).toFixed(1)} → H{(activeBlock.end_min / 60).toFixed(1)} (
                  {((activeBlock.end_min - activeBlock.start_min) / 60).toFixed(1)}h)
                  {activeBlock.purge_scrap_kg > 0 && ` • Purge: ${activeBlock.purge_scrap_kg} kg`}
                  {activeBlock.tardiness_hrs > 0 && ` • Late: +${activeBlock.tardiness_hrs}h`}
                </div>
                {selectedBlock && (
                  <button
                    type="button"
                    data-testid="gantt-clear-inspect"
                    onClick={() => setSelectedBlock(null)}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-[10px] font-semibold text-slate-300 hover:text-white"
                  >
                    {lang === "ar" ? "إغلاق" : "Clear"}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <span className="text-slate-500">{t.ganttTapHint}</span>
          )}
        </div>
      </div>

      {/* Charts Row: Resin Consumption & FIFO vs CP-SAT Purge Scrap Comparison */}
      <div className="grid w-full max-w-full min-w-0 gap-6 lg:grid-cols-2">
        <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
          <div className="mb-4 flex items-center gap-2">
            <Layers className="h-4 w-4 shrink-0 text-cyan-400" />
            <h3 className="truncate text-sm font-bold text-white">{t.resinChartTitle}</h3>
          </div>
          <div className="h-64 w-full min-w-0" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={resinChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="resin" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: 10, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Virgin" name="Virgin Used (kg)" stackId="a" fill="#22d3ee" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Regrind" name="Regrind Used (kg)" stackId="a" fill="#34d399" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
          <div className="mb-4 flex items-center gap-2">
            <Recycle className="h-4 w-4 shrink-0 text-emerald-400" />
            <h3 className="truncate text-sm font-bold text-white">{t.scrapCompareTitle}</h3>
          </div>
          <div className="h-64 w-full min-w-0" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={resinChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="resin" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: 10, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="FifoScrap" name="Naive FIFO Scrap (kg)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="OptScrap" name="CP-SAT Optimized Scrap (kg)" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Detailed Press Execution Sequence Table */}
      <div className="w-full max-w-full min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
        <div className="mb-3 flex min-w-0 flex-wrap items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <BarChart3 className="h-4 w-4 shrink-0 text-indigo-400" />
            <h3 className="truncate text-sm font-bold text-white">{t.sequenceTableTitle}</h3>
          </div>
          <ScheduleExportMenu testIdPrefix="gantt-export" />
        </div>
        <div className="w-full max-w-full min-w-0 overflow-x-auto touch-pan-x">
          <table className="w-full min-w-[680px] text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="sticky start-0 z-10 bg-[#0f1629]/95 px-2.5 py-2 text-start">Press</th>
                <th className="px-2 py-2 text-start">Order</th>
                <th className="px-2 py-2 text-start">Mold</th>
                <th className="px-2 py-2 text-start">Resin</th>
                <th className="px-2 py-2 text-start">Color</th>
                <th className="px-2 py-2 text-start">Transition</th>
                <th className="px-2 py-2 text-end">Setup</th>
                <th className="px-2 py-2 text-end">Purge kg</th>
                <th className="px-2 py-2 text-end">Window (Hr)</th>
                <th className="px-2 py-2 text-end">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {plan.jobs.map((j) => {
                const st = PLASTIC_BLOCK_STYLE[j.color];
                return (
                  <tr key={j.order_id} className="hover:bg-slate-900/50">
                    <td className="sticky start-0 z-10 bg-[#0f1629]/95 px-2.5 py-2 font-mono font-bold text-cyan-300">
                      {j.machine_id}
                    </td>
                    <td className="px-2 py-2">
                      <div className="font-semibold text-white">{j.order_id}</div>
                      <div className="text-[11px] text-slate-400">{j.sku_name}</div>
                    </td>
                    <td className="px-2 py-2 font-mono text-slate-300">{j.mold_id}</td>
                    <td className="px-2 py-2 font-mono text-slate-200">{j.resin_code}</td>
                    <td className="px-2 py-2">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-bold ${st.bg} ${st.text} ${st.border}`}
                      >
                        {COLOR_LABELS[lang][j.color]}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-[11px] text-slate-300">
                      {j.transition_type.replaceAll("_", " ")}
                    </td>
                    <td dir="ltr" className="px-2 py-2 text-end font-mono text-amber-300">
                      {j.setup_mins}m
                    </td>
                    <td dir="ltr" className="px-2 py-2 text-end font-mono text-slate-200">
                      {j.purge_scrap_kg.toFixed(1)}
                    </td>
                    <td dir="ltr" className="px-2 py-2 text-end font-mono text-slate-400">
                      {j.scheduled ? `H${(j.start_min / 60).toFixed(1)}–H${(j.end_min / 60).toFixed(1)}` : "—"}
                    </td>
                    <td className="px-2 py-2 text-end">
                      {!j.scheduled ? (
                        <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 px-2 py-0.5 text-[10px] font-bold text-rose-300">
                          <AlertTriangle className="h-3 w-3" /> Unscheduled
                        </span>
                      ) : j.tardiness_hrs > 0 ? (
                        <span className="rounded bg-amber-500/20 px-2 py-0.5 font-mono text-[10px] font-bold text-amber-300">
                          +{j.tardiness_hrs.toFixed(1)}h Late
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                          <CheckCircle2 className="h-3 w-3" /> On-Time
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
