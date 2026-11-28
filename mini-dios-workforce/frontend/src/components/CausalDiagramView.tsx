"use client";

import React, { useMemo, useState } from "react";
import {
  ArrowRight,
  Boxes,
  Cpu,
  GitBranch,
  Layers,
  Sliders,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type {
  DIBlueprintResponse,
  DIBlueprintTab,
  DICausalEdge,
  DIDecisionLever,
  DIDecisionOutcome,
  DIIntermediateMetric,
  Lang,
} from "@/lib/types";

const LEVER_LABELS_AR: Record<string, string> = {
  L_W_CHANGEOVER_SCRAP: "وزن أولوية تقليل التبديل وهالك التنظيف",
  L_W_OTIF: "وزن التسليم بالموعد وحماية مواعيد التصدير (OTIF)",
  L_W_ENERGY_COST: "وزن كفاءة استهلاك الكهرباء وتشغيل المكابس",
  L_W_WORKING_CAPITAL: "وزن رأس المال العامل والريجريند ومزامنة الحاويات",
  L_AVOID_PEAK_TARIFF: "تجنب نافذة ذروة الكهرباء (13:00–17:00)",
  L_RAMADAN_SHIFT_MODE: "وضع ورديات رمضان (6 ساعات) وحظر تبديل الإفطار",
  L_AUTONOMOUS_PM_WINDOW: "الجدولة الذاتية العائمة لصيانة القوالب الوقائية",
  L_CONTAINER_SYNC: "مزامنة تجميع حاويات التصدير متعددة الأصناف",
};

const INTERMEDIATE_LABELS_AR: Record<string, string> = {
  I_PURGE_SCRAP_KG: "إجمالي هالك تنظيف الأسطوانات (كجم)",
  I_CHANGEOVER_HOURS: "ساعات توقف تبديل القوالب والخامات",
  I_LATE_ORDER_HOURS: "إجمالي ساعات تأخير الأوامر",
  I_CONTAINER_WAIT_HRS: "ساعات انتظار تجميع حاويات التصدير بالمخزن",
  I_PEAK_WAREHOUSE_TONS: "ذروة تكدس مخزن المنتج التام (طن)",
  I_OVERTIME_LABOR_HOURS: "ساعات العمل الإضافي لعمالة الصالة",
};

const OUTCOME_LABELS_AR: Record<string, string> = {
  O_NET_OPERATING_PROFIT: "صافي الربح التشغيلي الأسبوعي",
  O_TOTAL_WEEKLY_SAVINGS: "إجمالي الوفر الأسبوعي ورفع الهامش مقابل FIFO",
  O_OTIF_SERVICE_LEVEL: "معدل الالتزام بالتسليم في الموعد (OTIF %)",
  O_WORKFORCE_COVERAGE: "تغطية عمالة الورديات المعتمدة (%)",
  O_PLANT_RISK_SCORE: "مؤشر رادار المخاطر التشغيلية للمصنع",
};

const EDGE_MECHANISM_AR: Record<string, string> = {
  CE_01: "رفع وزن الهالك والتبديل يجمّع الألوان من الفاتح للداكن ويوحّد حملات القالب عبر مسارات AddCircuit",
  CE_02: "يقلل عدد مرات فك وتركيب القوالب بالونش عبر الماكينات المتوافقة",
  CE_03: "يمنح أولوية لأوامر التصدير والمواعيد الضيقة على أسرع المكابس",
  CE_04: "يؤجل الصيانة الوقائية غير الطارئة لبعد انتهاء شحنات التصدير العاجلة ضمن رصيد الضربات المتبقي",
  CE_05: "ينسّق لحظة انتهاء الأصناف المشتركة في نفس حاوية التصدير (container_group_id)",
  CE_06: "يفرض غرامة على التخزين المبكر وانتظار الأصناف غير المتزامنة في مخزن المنتج التام",
  CE_07: "يثبّت طول الوردية عند 6 ساعات وسقف الأسبوع عند 36 ساعة مع حظر تبديل القوالب وقت الإفطار",
  CE_08: "الخام البكر المهدر أثناء تنظيف الأسطوانة يقتطع مباشرة من مجمل الربح",
  CE_09: "كل ساعة تبديل يتم توفيرها تخفض تكلفة التوقف وتخفف ضغط فنيي القوالب",
  CE_10: "القضاء على ساعات التأخير يرفع نسبة التسليم بالموعد OTIF ويمنع غرامات العقود",
  CE_11: "غرامات التأخير التعاقدية للشحنات تقتطع مباشرة من صافي الربح التشغيلي",
  CE_12: "انتظار تجميع الحاوية يولّد تكلفة تخزين يومية لكل طن في مخزن المنتج التام",
  CE_13: "ارتفاع أطنان المنتج التام المكدسة يرفع مخاطر ازدحام المخزن",
  CE_14: "توزيع الورديات المتوازن والربط المزدوج للعمالة يغلق فجوات التغطية",
  CE_15: "تزامن اكتمال أصناف الحاوية يمنع تراكم الدفعات المبكرة في مخزن المنتج التام",
};

const PRIMITIVE_TO_DMN: Record<string, string> = {
  TransitionMatrix: "DMN_BARREL_PURGE_TRANSITION",
  SynchronizationGroup: "DMN_MOLD_PM_POLICY",
  CumulativeEnvelope: "DMN_SHIFT_WORKFORCE_HEADCOUNT",
};

interface CausalDiagramViewProps {
  blueprint: DIBlueprintResponse;
  onJumpToTab: (tab: DIBlueprintTab) => void;
}

export function CausalDiagramView({ blueprint, onJumpToTab }: CausalDiagramViewProps) {
  const { lang, currency, config, result } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";

  const cdd = blueprint.layers.layer_5_causal_decision_meta_model;
  const levers = useMemo(() => {
    const raw = cdd?.levers ?? [];
    // Overlay live store config values so user sees real-time toggle/weight state
    return raw.map((lv) => {
      let liveVal = lv.current_value;
      if (lv.lever_id === "L_W_CHANGEOVER_SCRAP") liveVal = config.w_changeover_scrap;
      else if (lv.lever_id === "L_W_OTIF") liveVal = config.w_otif;
      else if (lv.lever_id === "L_W_ENERGY_COST") liveVal = config.w_energy_cost;
      else if (lv.lever_id === "L_W_WORKING_CAPITAL") liveVal = config.w_working_capital;
      else if (lv.lever_id === "L_AVOID_PEAK_TARIFF") liveVal = config.avoid_peak_tariff_hrs;
      else if (lv.lever_id === "L_RAMADAN_SHIFT_MODE") liveVal = config.ramadan_shift_mode;
      else if (lv.lever_id === "L_AUTONOMOUS_PM_WINDOW") liveVal = Boolean(config.autonomous_pm_window);
      else if (lv.lever_id === "L_CONTAINER_SYNC") liveVal = config.container_sync_enabled !== false;
      return { ...lv, current_value: liveVal };
    });
  }, [cdd?.levers, config]);

  const intermediates = useMemo(() => {
    const raw = cdd?.intermediates ?? [];
    if (!result) return raw;
    const bKpi = result.baseline.kpis;
    const oKpi = result.optimized.kpis;
    const wfB = result.workforce?.baseline.kpis;
    const wfO = result.workforce?.optimized.kpis;
    return raw.map((im) => {
      if (im.metric_id === "I_PURGE_SCRAP_KG") {
        return {
          ...im,
          baseline_value: bKpi.purge_scrap_kg,
          optimized_value: oKpi.purge_scrap_kg,
          delta_value: Number((oKpi.purge_scrap_kg - bKpi.purge_scrap_kg).toFixed(2)),
        };
      }
      if (im.metric_id === "I_CHANGEOVER_HOURS") {
        return {
          ...im,
          baseline_value: bKpi.changeover_hours,
          optimized_value: oKpi.changeover_hours,
          delta_value: Number((oKpi.changeover_hours - bKpi.changeover_hours).toFixed(2)),
        };
      }
      if (im.metric_id === "I_LATE_ORDER_HOURS") {
        return {
          ...im,
          baseline_value: bKpi.total_tardiness_hrs,
          optimized_value: oKpi.total_tardiness_hrs,
          delta_value: Number((oKpi.total_tardiness_hrs - bKpi.total_tardiness_hrs).toFixed(2)),
        };
      }
      if (im.metric_id === "I_CONTAINER_WAIT_HRS") {
        const bw = bKpi.container_wait_delay_hrs ?? 0;
        const ow = oKpi.container_wait_delay_hrs ?? 0;
        return {
          ...im,
          baseline_value: bw,
          optimized_value: ow,
          delta_value: Number((ow - bw).toFixed(2)),
        };
      }
      if (im.metric_id === "I_PEAK_WAREHOUSE_TONS") {
        const bt = bKpi.peak_warehouse_tons ?? 0;
        const ot = oKpi.peak_warehouse_tons ?? 0;
        return {
          ...im,
          baseline_value: bt,
          optimized_value: ot,
          delta_value: Number((ot - bt).toFixed(2)),
        };
      }
      if (im.metric_id === "I_OVERTIME_LABOR_HOURS" && wfB && wfO) {
        return {
          ...im,
          baseline_value: wfB.overtime_hours,
          optimized_value: wfO.overtime_hours,
          delta_value: Number((wfO.overtime_hours - wfB.overtime_hours).toFixed(2)),
        };
      }
      return im;
    });
  }, [cdd?.intermediates, result]);

  const outcomes = useMemo(() => {
    const raw = cdd?.outcomes ?? [];
    if (!result) return raw;
    const bFin = result.financials.baseline;
    const oFin = result.financials.optimized;
    const bKpi = result.baseline.kpis;
    const oKpi = result.optimized.kpis;
    const wfB = result.workforce?.baseline.kpis;
    const wfO = result.workforce?.optimized.kpis;
    const riskO = result.risk_radar?.overall_risk_score ?? 0;

    return raw.map((out) => {
      if (out.outcome_id === "O_NET_OPERATING_PROFIT") {
        return {
          ...out,
          baseline_value: bFin.net_operating_profit,
          optimized_value: oFin.net_operating_profit,
          delta_value: Number((oFin.net_operating_profit - bFin.net_operating_profit).toFixed(2)),
          improvement_pct: result.financials.profit_lift_pct,
        };
      }
      if (out.outcome_id === "O_TOTAL_WEEKLY_SAVINGS") {
        return {
          ...out,
          baseline_value: 0,
          optimized_value: result.financials.total_weekly_savings,
          delta_value: result.financials.total_weekly_savings,
          improvement_pct: result.financials.profit_lift_pct,
        };
      }
      if (out.outcome_id === "O_OTIF_SERVICE_LEVEL") {
        return {
          ...out,
          baseline_value: bKpi.otif_pct,
          optimized_value: oKpi.otif_pct,
          delta_value: Number((oKpi.otif_pct - bKpi.otif_pct).toFixed(2)),
        };
      }
      if (out.outcome_id === "O_WORKFORCE_COVERAGE" && wfB && wfO) {
        return {
          ...out,
          baseline_value: wfB.coverage_pct,
          optimized_value: wfO.coverage_pct,
          delta_value: Number((wfO.coverage_pct - wfB.coverage_pct).toFixed(2)),
        };
      }
      if (out.outcome_id === "O_PLANT_RISK_SCORE") {
        const baseR = Math.max(riskO, 35);
        return {
          ...out,
          baseline_value: baseR,
          optimized_value: riskO,
          delta_value: Number((riskO - baseR).toFixed(1)),
        };
      }
      return out;
    });
  }, [cdd?.outcomes, result]);

  const edges = cdd?.causal_edges ?? [];

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("L_W_CHANGEOVER_SCRAP");
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const activeFocusId = hoveredNodeId ?? selectedNodeId;

  // Compute connected nodes & edges for interactive pathway highlighting
  const { activeNodeIds, activeEdgeIds, focusedEdges } = useMemo(() => {
    if (!activeFocusId) {
      return {
        activeNodeIds: new Set<string>(),
        activeEdgeIds: new Set<string>(),
        focusedEdges: edges,
      };
    }
    const nodes = new Set<string>([activeFocusId]);
    const eIds = new Set<string>();

    // Forward 2 hops
    const hop1Targets = new Set<string>();
    for (const e of edges) {
      if (e.source_id === activeFocusId) {
        eIds.add(e.edge_id);
        nodes.add(e.target_id);
        hop1Targets.add(e.target_id);
      }
    }
    for (const e of edges) {
      if (hop1Targets.has(e.source_id)) {
        eIds.add(e.edge_id);
        nodes.add(e.target_id);
      }
    }

    // Backward 2 hops
    const hop1Sources = new Set<string>();
    for (const e of edges) {
      if (e.target_id === activeFocusId) {
        eIds.add(e.edge_id);
        nodes.add(e.source_id);
        hop1Sources.add(e.source_id);
      }
    }
    for (const e of edges) {
      if (hop1Sources.has(e.target_id)) {
        eIds.add(e.edge_id);
        nodes.add(e.source_id);
      }
    }

    const matchedEdges = edges.filter((e) => eIds.has(e.edge_id));
    return { activeNodeIds: nodes, activeEdgeIds: eIds, focusedEdges: matchedEdges };
  }, [activeFocusId, edges]);

  const formatOutcomeValue = (val: number, unit: string) => {
    if (unit === "SAR" || unit === "EGP") {
      const srcCur = result?.currency ?? (unit as "SAR" | "EGP");
      const fx = result?.fx_egp_per_sar ?? config.fx_egp_per_sar ?? 13.0;
      return formatMoney(convertCurrency(val, srcCur, currency, fx), currency);
    }
    if (unit === "%") return `${val.toFixed(1)}%`;
    return `${val.toFixed(1)} ${unit}`;
  };

  // Fixed coordinate space for SVG connector stage (Desktop 3-column layout)
  const leverIndexMap = useMemo(() => new Map(levers.map((l, i) => [l.lever_id, i])), [levers]);
  const interIndexMap = useMemo(() => new Map(intermediates.map((m, i) => [m.metric_id, i])), [intermediates]);
  const outcomeIndexMap = useMemo(() => new Map(outcomes.map((o, i) => [o.outcome_id, i])), [outcomes]);

  const getYPercent = (idx: number, total: number) => {
    if (total <= 1) return 50;
    return ((idx + 0.5) / total) * 100;
  };

  const getEdgeColor = (edge: DICausalEdge, isHighlighted: boolean) => {
    if (!isHighlighted && activeFocusId) return "rgba(71, 85, 105, 0.22)";
    if (edge.polarity === "-") return "#34d399"; // emerald-400 (reduces waste/delay/cost)
    if (edge.polarity === "+") return "#38bdf8"; // cyan-400
    return "#fbbf24"; // amber-400
  };

  return (
    <div data-testid="di-tab-panel-causal" className="space-y-4">
      {/* Top Interactive Hint Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900/75 px-3.5 py-2.5 text-xs">
        <div className="flex items-center gap-2 text-slate-300">
          <GitBranch className="h-4 w-4 shrink-0 text-cyan-400" />
          <span>{t.diClickHint}</span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-3 text-[11px]">
            <span className="inline-flex items-center gap-1.5 text-emerald-300">
              <span className="h-2 w-4 rounded-full bg-emerald-400" />
              {isAr ? "خفض الهالك / التأخير (−)" : "Waste / Risk Reduction (−)"}
            </span>
            <span className="inline-flex items-center gap-1.5 text-cyan-300">
              <span className="h-2 w-4 rounded-full bg-cyan-400" />
              {isAr ? "طردي / مباشر (+)" : "Direct Driver (+)"}
            </span>
          </div>
          {selectedNodeId && (
            <button
              type="button"
              data-testid="btn-causal-clear-selection"
              onClick={() => setSelectedNodeId(null)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-cyan-300 hover:border-cyan-500/50 hover:text-white"
            >
              <X className="h-3 w-3" />
              <span>{t.diClearSelectionBtn}</span>
            </button>
          )}
        </div>
      </div>

      {/* 3-Column Directional Flow Graph (Desktop with SVG Bezier Connectors; Mobile vertical stacked cards) */}
      <div className="relative rounded-2xl border border-slate-800 bg-[#080d1a] p-3.5 sm:p-5">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_64px_minmax(0,1fr)_64px_minmax(0,1fr)] lg:items-stretch lg:gap-0">
          {/* Column 1: Decision Levers & Externals */}
          <div className="flex flex-col justify-between space-y-2.5">
            <div className="mb-1 border-b border-slate-800/90 pb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-cyan-300">
                <Sliders className="h-3.5 w-3.5 shrink-0" />
                <span>{t.diColLeversTitle}</span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">{t.diColLeversSubtitle}</p>
            </div>
            <div className="flex flex-1 flex-col justify-around gap-2">
              {levers.map((lv) => {
                const isSelected = activeFocusId === lv.lever_id;
                const isConnected = !activeFocusId || activeNodeIds.has(lv.lever_id);
                const isBool = typeof lv.current_value === "boolean" || lv.unit === "bool";
                const boolOn = Boolean(lv.current_value);
                return (
                  <button
                    key={lv.lever_id}
                    type="button"
                    data-testid={`causal-lever-${lv.lever_id}`}
                    onClick={() =>
                      setSelectedNodeId((prev) => (prev === lv.lever_id ? null : lv.lever_id))
                    }
                    onMouseEnter={() => setHoveredNodeId(lv.lever_id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className={`group relative w-full rounded-xl border p-2.5 text-start transition ${
                      isSelected
                        ? "border-cyan-400 bg-cyan-500/15 ring-1 ring-cyan-400/50"
                        : isConnected
                        ? "border-slate-700/90 bg-slate-900/90 hover:border-cyan-500/50"
                        : "border-slate-800/60 bg-slate-950/40 opacity-35"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white">
                        {isAr ? LEVER_LABELS_AR[lv.lever_id] ?? lv.name : lv.name}
                      </span>
                      {isBool ? (
                        <span
                          className={`shrink-0 rounded-md px-2 py-0.5 font-mono text-[10px] font-bold ${
                            boolOn
                              ? "bg-emerald-400 text-slate-950"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {boolOn ? t.stateOn : t.stateOff}
                        </span>
                      ) : (
                        <span
                          dir="ltr"
                          className="shrink-0 rounded-md border border-cyan-500/35 bg-cyan-500/15 px-2 py-0.5 font-mono text-[11px] font-bold text-cyan-200"
                        >
                          {String(lv.current_value)}/100
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[10px] text-slate-400">
                      <span dir="ltr" className="font-mono text-slate-500">
                        {lv.lever_id}
                      </span>
                      <span>{lv.category === "operational_toggle" ? (isAr ? "مفتاح تشغيل" : "Mode Toggle") : (isAr ? "وزن هدف" : "Objective Weight")}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* SVG Connector Bridge 1: Levers -> Intermediates (Desktop) */}
          <div className="hidden lg:flex lg:flex-col lg:pt-12">
            <svg
              viewBox="0 0 100 400"
              preserveAspectRatio="none"
              className="h-full w-full overflow-visible"
              aria-hidden="true"
            >
              {edges
                .filter((e) => leverIndexMap.has(e.source_id) && interIndexMap.has(e.target_id))
                .map((e) => {
                  const sIdx = leverIndexMap.get(e.source_id) ?? 0;
                  const tIdx = interIndexMap.get(e.target_id) ?? 0;
                  const y1 = (getYPercent(sIdx, levers.length) / 100) * 400;
                  const y2 = (getYPercent(tIdx, intermediates.length) / 100) * 400;
                  const x1 = isAr ? 100 : 0;
                  const x2 = isAr ? 0 : 100;
                  const cx1 = isAr ? 42 : 58;
                  const cx2 = isAr ? 58 : 42;
                  const isHi = !activeFocusId || activeEdgeIds.has(e.edge_id);
                  const stroke = getEdgeColor(e, isHi);
                  return (
                    <g key={e.edge_id}>
                      <path
                        d={`M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`}
                        fill="none"
                        stroke={stroke}
                        strokeWidth={isHi && activeFocusId ? 2.8 : 1.7}
                        strokeDasharray={e.polarity === "+" ? "none" : "none"}
                      />
                      <circle cx={x2} cy={y2} r={isHi && activeFocusId ? 3.5 : 2.2} fill={stroke} />
                    </g>
                  );
                })}
            </svg>
          </div>

          {/* Column 2: Intermediate Operational Drivers */}
          <div className="flex flex-col justify-between space-y-2.5">
            <div className="mb-1 border-b border-slate-800/90 pb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
                <Cpu className="h-3.5 w-3.5 shrink-0" />
                <span>{t.diColIntermediatesTitle}</span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">{t.diColIntermediatesSubtitle}</p>
            </div>
            <div className="flex flex-1 flex-col justify-around gap-2">
              {intermediates.map((im) => {
                const isSelected = activeFocusId === im.metric_id;
                const isConnected = !activeFocusId || activeNodeIds.has(im.metric_id);
                const improved = im.delta_value <= 0;
                return (
                  <button
                    key={im.metric_id}
                    type="button"
                    data-testid={`causal-intermediate-${im.metric_id}`}
                    onClick={() =>
                      setSelectedNodeId((prev) => (prev === im.metric_id ? null : im.metric_id))
                    }
                    onMouseEnter={() => setHoveredNodeId(im.metric_id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className={`w-full rounded-xl border p-2.5 text-start transition ${
                      isSelected
                        ? "border-amber-400 bg-amber-500/15 ring-1 ring-amber-400/50"
                        : isConnected
                        ? "border-slate-700/90 bg-slate-900/90 hover:border-amber-500/50"
                        : "border-slate-800/60 bg-slate-950/40 opacity-35"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white">
                        {isAr ? INTERMEDIATE_LABELS_AR[im.metric_id] ?? im.name : im.name}
                      </span>
                      <span
                        dir="ltr"
                        className={`shrink-0 rounded-md px-2 py-0.5 font-mono text-[10px] font-bold ${
                          improved
                            ? "border border-emerald-500/35 bg-emerald-500/15 text-emerald-300"
                            : "border border-amber-500/35 bg-amber-500/15 text-amber-200"
                        }`}
                      >
                        {im.delta_value > 0 ? `+${im.delta_value}` : im.delta_value} {im.unit}
                      </span>
                    </div>
                    <div
                      dir="ltr"
                      className="mt-1.5 flex items-center justify-between font-mono text-[11px] text-slate-300"
                    >
                      <span className="text-slate-400">
                        FIFO: {im.baseline_value.toFixed(1)} {im.unit}
                      </span>
                      <ArrowRight className="h-3 w-3 text-slate-500" />
                      <span className="font-bold text-cyan-300">
                        Opt: {im.optimized_value.toFixed(1)} {im.unit}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* SVG Connector Bridge 2: Intermediates -> Outcomes (Desktop) */}
          <div className="hidden lg:flex lg:flex-col lg:pt-12">
            <svg
              viewBox="0 0 100 400"
              preserveAspectRatio="none"
              className="h-full w-full overflow-visible"
              aria-hidden="true"
            >
              {edges
                .filter((e) => interIndexMap.has(e.source_id) && outcomeIndexMap.has(e.target_id))
                .map((e) => {
                  const sIdx = interIndexMap.get(e.source_id) ?? 0;
                  const tIdx = outcomeIndexMap.get(e.target_id) ?? 0;
                  const y1 = (getYPercent(sIdx, intermediates.length) / 100) * 400;
                  const y2 = (getYPercent(tIdx, outcomes.length) / 100) * 400;
                  const x1 = isAr ? 100 : 0;
                  const x2 = isAr ? 0 : 100;
                  const cx1 = isAr ? 42 : 58;
                  const cx2 = isAr ? 58 : 42;
                  const isHi = !activeFocusId || activeEdgeIds.has(e.edge_id);
                  const stroke = getEdgeColor(e, isHi);
                  return (
                    <g key={e.edge_id}>
                      <path
                        d={`M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`}
                        fill="none"
                        stroke={stroke}
                        strokeWidth={isHi && activeFocusId ? 2.8 : 1.7}
                      />
                      <circle cx={x2} cy={y2} r={isHi && activeFocusId ? 3.5 : 2.2} fill={stroke} />
                    </g>
                  );
                })}
            </svg>
          </div>

          {/* Column 3: Business Outcomes */}
          <div className="flex flex-col justify-between space-y-2.5">
            <div className="mb-1 border-b border-slate-800/90 pb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-300">
                <TrendingUp className="h-3.5 w-3.5 shrink-0" />
                <span>{t.diColOutcomesTitle}</span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">{t.diColOutcomesSubtitle}</p>
            </div>
            <div className="flex flex-1 flex-col justify-around gap-2">
              {outcomes.map((out) => {
                const isSelected = activeFocusId === out.outcome_id;
                const isConnected = !activeFocusId || activeNodeIds.has(out.outcome_id);
                const isPositiveGood =
                  (out.direction === "maximize" && out.delta_value >= 0) ||
                  (out.direction === "minimize" && out.delta_value <= 0);
                return (
                  <button
                    key={out.outcome_id}
                    type="button"
                    data-testid={`causal-outcome-${out.outcome_id}`}
                    onClick={() =>
                      setSelectedNodeId((prev) => (prev === out.outcome_id ? null : out.outcome_id))
                    }
                    onMouseEnter={() => setHoveredNodeId(out.outcome_id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className={`w-full rounded-xl border p-2.5 text-start transition ${
                      isSelected
                        ? "border-emerald-400 bg-emerald-500/15 ring-1 ring-emerald-400/50"
                        : isConnected
                        ? "border-slate-700/90 bg-slate-900/90 hover:border-emerald-500/50"
                        : "border-slate-800/60 bg-slate-950/40 opacity-35"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-white">
                        {isAr ? OUTCOME_LABELS_AR[out.outcome_id] ?? out.name : out.name}
                      </span>
                      <span
                        dir="ltr"
                        className={`shrink-0 rounded-md px-2 py-0.5 font-mono text-[11px] font-bold ${
                          isPositiveGood
                            ? "border border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                            : "border border-rose-500/40 bg-rose-500/15 text-rose-300"
                        }`}
                      >
                        {formatOutcomeValue(out.optimized_value, out.unit)}
                      </span>
                    </div>
                    <div
                      dir="ltr"
                      className="mt-1.5 flex items-center justify-between font-mono text-[10px] text-slate-400"
                    >
                      <span>Base: {formatOutcomeValue(out.baseline_value, out.unit)}</span>
                      <span className={isPositiveGood ? "font-bold text-emerald-300" : "text-amber-300"}>
                        Δ {out.delta_value >= 0 ? "+" : ""}
                        {formatOutcomeValue(out.delta_value, out.unit)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Causal Attribution & Governing Rule Inspector Card */}
      <div
        data-testid="causal-attribution-card"
        className="rounded-2xl border border-cyan-500/30 bg-slate-900/90 p-4"
      >
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white">{t.diCausalCardTitle}</h3>
            {activeFocusId && (
              <span
                dir="ltr"
                className="rounded-md border border-cyan-500/40 bg-cyan-500/15 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-200"
              >
                {activeFocusId}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="btn-causal-jump-dmn"
              onClick={() => onJumpToTab("dmn")}
              className="inline-flex items-center gap-1 rounded-lg border border-purple-500/40 bg-purple-500/15 px-2.5 py-1 text-[11px] font-semibold text-purple-200 transition hover:bg-purple-500/25"
            >
              <Layers className="h-3.5 w-3.5 text-purple-300" />
              <span>{t.diJumpToDmnBtn}</span>
            </button>
            <button
              type="button"
              data-testid="btn-causal-jump-uem"
              onClick={() => onJumpToTab("arch_uem")}
              className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-semibold text-emerald-200 transition hover:bg-emerald-500/25"
            >
              <Boxes className="h-3.5 w-3.5 text-emerald-300" />
              <span>{t.diJumpToUemBtn}</span>
            </button>
          </div>
        </div>

        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {focusedEdges.slice(0, 6).map((edge) => {
            const dmnTableId = edge.governed_by_primitive
              ? PRIMITIVE_TO_DMN[edge.governed_by_primitive]
              : undefined;
            return (
              <div
                key={edge.edge_id}
                className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs"
              >
                <div>
                  <div className="flex items-center justify-between gap-1.5">
                    <span dir="ltr" className="font-mono text-[11px] font-bold text-cyan-300">
                      {edge.source_id} → {edge.target_id}
                    </span>
                    <span
                      dir="ltr"
                      className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                        edge.polarity === "-"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : "bg-cyan-500/20 text-cyan-300"
                      }`}
                    >
                      {edge.polarity}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-slate-300">
                    {isAr ? EDGE_MECHANISM_AR[edge.edge_id] ?? edge.mechanism : edge.mechanism}
                  </p>
                </div>

                <div className="mt-2.5 flex flex-wrap items-center justify-between gap-1.5 border-t border-slate-800/80 pt-2 text-[10px]">
                  {edge.governed_by_primitive && (
                    <button
                      type="button"
                      onClick={() => onJumpToTab("arch_uem")}
                      className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono text-emerald-300 hover:border-emerald-500/50"
                    >
                      UEM: {edge.governed_by_primitive}
                    </button>
                  )}
                  {dmnTableId && (
                    <button
                      type="button"
                      onClick={() => onJumpToTab("dmn")}
                      className="rounded border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 font-mono text-purple-200 hover:border-purple-400"
                    >
                      {dmnTableId}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
