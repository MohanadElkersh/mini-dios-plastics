"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Edit3,
  HeartPulse,
  Loader2,
  Moon,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sliders,
  Sparkles,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { convertCurrency, formatMoney, formatNumber } from "@/lib/format";
import {
  DAY_NAMES_I18N,
  SHIFT_LABELS,
  WORKER_ROLE_LABELS,
  WORKER_ROLE_SHORT,
  WORKFORCE_CONSTRAINT_LABELS,
} from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type {
  Currency,
  FactoryWorker,
  PreferredShift,
  WorkerRole,
  WorkerStatus,
} from "@/lib/types";

const ALL_ROLES: WorkerRole[] = [
  "Press_Operator",
  "Mold_Technician",
  "QC_Inspector",
  "Material_Handler",
  "Shift_Supervisor",
];

const ROLE_PREFIX: Record<WorkerRole, string> = {
  Press_Operator: "OP",
  Mold_Technician: "MT",
  QC_Inspector: "QC",
  Material_Handler: "MH",
  Shift_Supervisor: "SV",
};

const ROLE_BADGE_CLASSES: Record<WorkerRole, string> = {
  Press_Operator: "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
  Mold_Technician: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  QC_Inspector: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  Material_Handler: "border-purple-500/30 bg-purple-500/10 text-purple-300",
  Shift_Supervisor: "border-blue-500/30 bg-blue-500/10 text-blue-300",
};

function shiftCellStyle(cell: string): string {
  switch (cell) {
    case "Morning":
      return "border-sky-500/40 bg-sky-500/15 text-sky-200";
    case "Afternoon":
      return "border-amber-500/40 bg-amber-500/15 text-amber-200";
    case "Evening":
      return "border-fuchsia-500/40 bg-fuchsia-500/15 text-fuchsia-200";
    case "Night":
      return "border-indigo-500/40 bg-indigo-500/20 text-indigo-200";
    case "LEAVE":
      return "border-teal-500/35 bg-teal-500/10 text-teal-300";
    case "SICK":
      return "border-rose-500/50 bg-rose-500/20 text-rose-200";
    default:
      return "border-slate-800 bg-slate-900/60 text-slate-500";
  }
}

interface WorkerFormDraft {
  worker_id: string;
  name: string;
  role: WorkerRole;
  certAll: boolean;
  certPresses: string[];
  hourly_rate_display: string;
  overtime_multiplier: string;
  max_weekly_hours: string;
  preferred_shift: PreferredShift;
  approved_leave_days: number[];
  status: WorkerStatus;
}

export function WorkforceView() {
  const {
    lang,
    currency,
    dataset,
    config,
    result,
    loading,
    workforceLoading,
    upsertWorker,
    deleteWorker,
    duplicateWorker,
    toggleWorkerSick,
    toggleWorkerLeaveDay,
    updateWorkforceConfig,
    reOptimizeShifts,
    runSolve,
  } = useApp();

  const isAr = lang === "ar";
  const dayNames = DAY_NAMES_I18N[lang];
  const roleLabels = WORKER_ROLE_LABELS[lang];
  const roleShort = WORKER_ROLE_SHORT[lang];
  const shiftLabels = SHIFT_LABELS[lang];
  const whcLabels = WORKFORCE_CONSTRAINT_LABELS[lang];

  const fx = config.fx_egp_per_sar;
  const wfCfg = config.workforce;
  const wf = result?.workforce ?? null;
  const wfCurrency: Currency = wf?.currency ?? result?.currency ?? currency;
  const workers = useMemo(() => dataset?.workers ?? [], [dataset?.workers]);
  const presses = useMemo(() => dataset?.presses ?? [], [dataset?.presses]);

  // Sub-panel UI state
  const [rosterRoleFilter, setRosterRoleFilter] = useState<"ALL" | WorkerRole>("ALL");
  const [rosterPlanMode, setRosterPlanMode] = useState<"optimized" | "baseline">("optimized");
  const [chartRoleFilter, setChartRoleFilter] = useState<"ALL" | WorkerRole>("ALL");
  const [chartGroupMode, setChartGroupMode] = useState<"day" | "slot">("slot");
  const [dirSearch, setDirSearch] = useState("");
  const [dirRoleFilter, setDirRoleFilter] = useState<"ALL" | WorkerRole>("ALL");
  const [hasPendingEdits, setHasPendingEdits] = useState(false);

  // Inline Add / Edit worker form state
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingOriginalId, setEditingOriginalId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [draft, setDraft] = useState<WorkerFormDraft>({
    worker_id: "OP-15",
    name: "",
    role: "Press_Operator",
    certAll: true,
    certPresses: [],
    hourly_rate_display: "20",
    overtime_multiplier: "1.5",
    max_weekly_hours: "48",
    preferred_shift: "Any",
    approved_leave_days: [],
    status: "active",
  });

  const fmtMoney = (amount: number, fromCur: Currency = wfCurrency) =>
    formatMoney(convertCurrency(amount, fromCur, currency, fx), currency);

  const fmtSarRate = (sarRate: number) => {
    const val = convertCurrency(sarRate, "SAR", currency, fx);
    return `${currency} ${val.toFixed(val >= 100 ? 0 : 1)}/h`;
  };

  // Counts from live dataset workers
  const activeCount = useMemo(() => workers.filter((w) => w.status === "active").length, [workers]);
  const sickCount = useMemo(() => workers.filter((w) => w.status === "sick").length, [workers]);
  const onLeaveCount = useMemo(() => workers.filter((w) => w.status === "on_leave").length, [workers]);

  // Quick disruption chips: all Mold Techs + Shift Supervisors + any sick workers + first 3 operators
  const quickDisruptionWorkers = useMemo(() => {
    const picked: FactoryWorker[] = [];
    const seen = new Set<string>();
    const add = (w: FactoryWorker) => {
      if (!seen.has(w.worker_id)) {
        seen.add(w.worker_id);
        picked.push(w);
      }
    };
    workers.filter((w) => w.status === "sick").forEach(add);
    workers.filter((w) => w.role === "Mold_Technician").forEach(add);
    workers.filter((w) => w.role === "Shift_Supervisor").forEach(add);
    workers.filter((w) => w.role === "Press_Operator").slice(0, 3).forEach(add);
    return picked;
  }, [workers]);

  // Sub-Panel A: Filtered roster rows
  const activePlan = wf ? (rosterPlanMode === "optimized" ? wf.optimized : wf.baseline) : null;
  const workersById = useMemo(() => new Map(workers.map((w) => [w.worker_id, w])), [workers]);

  const filteredRosterRows = useMemo(() => {
    const rows = activePlan?.rosters ?? [];
    if (rosterRoleFilter === "ALL") return rows;
    return rows.filter((r) => r.role === rosterRoleFilter);
  }, [activePlan?.rosters, rosterRoleFilter]);

  // Sub-Panel B: Demand vs. Scheduled Coverage Chart data
  const chartData = useMemo(() => {
    if (!wf) return [];
    const demand = wf.optimized.demand.filter(
      (c) => chartRoleFilter === "ALL" || c.role === chartRoleFilter
    );

    if (chartGroupMode === "day") {
      return dayNames.map((dLabel, dIdx) => {
        const dayCells = demand.filter((c) => c.day === dIdx);
        const required = dayCells.reduce((acc, c) => acc + c.required, 0);
        const scheduled = dayCells.reduce((acc, c) => acc + c.scheduled, 0);
        const gap = dayCells.reduce((acc, c) => acc + Math.max(0, c.required - c.scheduled), 0);
        const moldEvents = dayCells.filter((c) => c.mold_change).length;
        const reasons = Array.from(new Set(dayCells.flatMap((c) => c.reasons))).slice(0, 4);
        return {
          label: dLabel,
          required,
          scheduled,
          gap,
          understaffed: gap > 0,
          moldEvents,
          reasons,
        };
      });
    }

    // By Shift Slot (only slots with demand > 0 or scheduled > 0)
    const slotOrder = new Map(wf.shift_names.map((s, idx) => [s, idx]));
    const slotMap = new Map<
      string,
      {
        sortKey: number;
        label: string;
        required: number;
        scheduled: number;
        gap: number;
        moldEvents: number;
        reasons: Set<string>;
      }
    >();

    for (const cell of demand) {
      const sIdx = slotOrder.get(cell.shift) ?? 0;
      const key = `${cell.day}-${sIdx}`;
      const shortShift = isAr
        ? (shiftLabels[cell.shift] ?? cell.shift).slice(0, 4)
        : cell.shift.slice(0, 3);
      if (!slotMap.has(key)) {
        slotMap.set(key, {
          sortKey: cell.day * 10 + sIdx,
          label: `${dayNames[cell.day]} ${shortShift}`,
          required: 0,
          scheduled: 0,
          gap: 0,
          moldEvents: 0,
          reasons: new Set<string>(),
        });
      }
      const bucket = slotMap.get(key)!;
      bucket.required += cell.required;
      bucket.scheduled += cell.scheduled;
      bucket.gap += Math.max(0, cell.required - cell.scheduled);
      if (cell.mold_change) bucket.moldEvents += 1;
      for (const r of cell.reasons) bucket.reasons.add(r);
    }

    return Array.from(slotMap.values())
      .sort((a, b) => a.sortKey - b.sortKey)
      .map((b) => ({
        label: b.label,
        required: b.required,
        scheduled: b.scheduled,
        gap: b.gap,
        understaffed: b.gap > 0,
        moldEvents: b.moldEvents,
        reasons: Array.from(b.reasons).slice(0, 4),
      }));
  }, [wf, chartRoleFilter, chartGroupMode, dayNames, isAr, shiftLabels]);

  const understaffedBottlenecks = useMemo(() => {
    if (!wf) return [];
    return wf.optimized.demand
      .filter((c) => c.required > c.scheduled || c.uncertified_presses.length > 0)
      .sort((a, b) => b.required - b.scheduled - (a.required - a.scheduled))
      .slice(0, 8);
  }, [wf]);

  // Sub-Panel C: Filtered directory workers
  const filteredDirectory = useMemo(() => {
    const q = dirSearch.trim().toLowerCase();
    return workers.filter((w) => {
      if (dirRoleFilter !== "ALL" && w.role !== dirRoleFilter) return false;
      if (!q) return true;
      return (
        w.worker_id.toLowerCase().includes(q) ||
        w.name.toLowerCase().includes(q) ||
        roleLabels[w.role].toLowerCase().includes(q)
      );
    });
  }, [workers, dirSearch, dirRoleFilter, roleLabels]);

  // Helpers to open Add / Edit form
  const nextWorkerIdForRole = (role: WorkerRole): string => {
    const prefix = ROLE_PREFIX[role];
    const used = new Set(workers.map((w) => w.worker_id));
    let n = workers.filter((w) => w.role === role).length + 1;
    let candidate = `${prefix}-${String(n).padStart(2, "0")}`;
    while (used.has(candidate)) {
      n += 1;
      candidate = `${prefix}-${String(n).padStart(2, "0")}`;
    }
    return candidate;
  };

  const openAddWorker = () => {
    const defaultRole: WorkerRole = "Press_Operator";
    const defaultSar = 20;
    const displayRate = convertCurrency(defaultSar, "SAR", currency, fx);
    setEditingOriginalId(null);
    setFormError(null);
    setDraft({
      worker_id: nextWorkerIdForRole(defaultRole),
      name: "",
      role: defaultRole,
      certAll: true,
      certPresses: presses.map((p) => p.machine_id),
      hourly_rate_display: String(Math.round(displayRate * 10) / 10),
      overtime_multiplier: "1.5",
      max_weekly_hours: "48",
      preferred_shift: "Any",
      approved_leave_days: [],
      status: "active",
    });
    setEditorOpen(true);
  };

  const openEditWorker = (w: FactoryWorker) => {
    const displayRate = convertCurrency(w.hourly_rate, "SAR", currency, fx);
    setEditingOriginalId(w.worker_id);
    setFormError(null);
    setDraft({
      worker_id: w.worker_id,
      name: w.name,
      role: w.role,
      certAll: w.certified_machine_ids === "ALL",
      certPresses:
        w.certified_machine_ids === "ALL"
          ? presses.map((p) => p.machine_id)
          : [...w.certified_machine_ids],
      hourly_rate_display: String(Math.round(displayRate * 10) / 10),
      overtime_multiplier: String(w.overtime_multiplier),
      max_weekly_hours: String(w.max_weekly_hours),
      preferred_shift: w.preferred_shift,
      approved_leave_days: [...w.approved_leave_days],
      status: w.status,
    });
    setEditorOpen(true);
  };

  const handleSaveWorker = (e: React.FormEvent) => {
    e.preventDefault();
    const wid = draft.worker_id.trim().toUpperCase();
    const name = draft.name.trim();
    if (!wid || !name) {
      setFormError(isAr ? "يرجى إدخال رمز العامل واسمه." : "Worker ID and Name are required.");
      return;
    }
    if (
      wid !== editingOriginalId &&
      workers.some((w) => w.worker_id.toUpperCase() === wid)
    ) {
      setFormError(
        isAr ? `الرمز ${wid} مستخدم بالفعل.` : `Worker ID "${wid}" already exists.`
      );
      return;
    }
    const rateNum = Number(draft.hourly_rate_display);
    const otNum = Number(draft.overtime_multiplier);
    const maxHrsNum = Number(draft.max_weekly_hours);
    if (Number.isNaN(rateNum) || rateNum <= 0) {
      setFormError(isAr ? "الأجر بالساعة يجب أن يكون أكبر من 0." : "Hourly rate must be > 0.");
      return;
    }
    const sarRate = Math.max(1, Math.round(convertCurrency(rateNum, currency, "SAR", fx) * 100) / 100);
    const worker: FactoryWorker = {
      worker_id: wid,
      name,
      role: draft.role,
      certified_machine_ids:
        draft.certAll || draft.certPresses.length === 0 ? "ALL" : [...draft.certPresses],
      hourly_rate: sarRate,
      overtime_multiplier: Number.isNaN(otNum) ? 1.5 : Math.max(1, Math.min(4, otNum)),
      max_weekly_hours: Number.isNaN(maxHrsNum) ? 48 : Math.max(8, Math.min(84, maxHrsNum)),
      preferred_shift: draft.preferred_shift,
      approved_leave_days: [...draft.approved_leave_days].sort((a, b) => a - b),
      status: draft.status,
    };
    upsertWorker(worker, editingOriginalId ?? undefined);
    setHasPendingEdits(true);
    setEditorOpen(false);
    setEditingOriginalId(null);
    setFormError(null);
  };

  const handleWeightSlider = (
    key: "w_labor_cost" | "w_coverage" | "w_fairness",
    val: number
  ) => {
    const clamped = Math.max(0, Math.min(100, val));
    const next = { ...wfCfg, [key]: clamped };
    if (next.w_labor_cost + next.w_coverage + next.w_fairness === 0) {
      next[key] = 5;
    }
    updateWorkforceConfig({ [key]: next[key] });
    setHasPendingEdits(true);
  };

  const handleReOptimize = async () => {
    await reOptimizeShifts();
    setHasPendingEdits(false);
  };

  const handleToggleSick = (wid: string) => {
    toggleWorkerSick(wid);
    setHasPendingEdits(true);
  };

  const handleToggleLeave = (wid: string, day: number) => {
    toggleWorkerLeaveDay(wid, day);
    setHasPendingEdits(true);
  };

  const handleDeleteWorker = (wid: string) => {
    deleteWorker(wid);
    setHasPendingEdits(true);
  };

  const handleDuplicateWorker = (wid: string) => {
    duplicateWorker(wid);
    setHasPendingEdits(true);
  };

  // Empty state if workspace has 0 workers
  if (!dataset) {
    return (
      <div className="flex min-h-[360px] flex-col items-center justify-center rounded-2xl border border-slate-800 bg-[#0f1629] p-8 text-center">
        <Loader2 className="mb-3 h-7 w-7 animate-spin text-cyan-400" />
        <p className="text-sm font-semibold text-white">
          {isAr ? "جاري تحميل بيانات القوى العاملة..." : "Loading factory workforce workspace..."}
        </p>
      </div>
    );
  }

  const optKpis = wf?.optimized.kpis ?? null;
  const baseKpis = wf?.baseline.kpis ?? null;
  const totalAvailableCapHrs = workers
    .filter((w) => w.status === "active")
    .reduce((acc, w) => acc + Math.min(w.max_weekly_hours, config.ramadan_shift_mode ? 36 : 84), 0);
  const utilizationPct =
    optKpis && totalAvailableCapHrs > 0
      ? Math.round((optKpis.total_hours / totalAvailableCapHrs) * 100)
      : 0;

  return (
    <div className="space-y-6" data-testid="workforce-view">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-[#0f1629] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/20 to-indigo-500/20 border border-cyan-500/30 text-cyan-300">
            <Users className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-bold text-white">
                {isAr
                  ? "إدارة القوى العاملة وجدولة الورديات (CP-SAT)"
                  : "Factory Workforce Management & Shift Scheduling"}
              </h2>
              {config.ramadan_shift_mode && (
                <span
                  data-testid="wf-ramadan-badge"
                  className="inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/15 px-2.5 py-0.5 text-[11px] font-bold text-amber-200"
                >
                  <Moon className="h-3 w-3" />
                  {isAr ? "رمضان: 4×6 ساعات • حد 36 ساعة/أسبوع" : "Ramadan: 4×6h Shifts • 36h/wk Cap"}
                </span>
              )}
              {hasPendingEdits && (
                <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/40 bg-cyan-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-cyan-200">
                  <Sparkles className="h-3 w-3" />
                  {isAr
                    ? "تعديلات جديدة — اضغط إعادة تحسين الورديات"
                    : "Pending edits — click Re-Optimize Shifts"}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {isAr
                ? "مرتبط حتمياً بمخطط جانت للمكابس (تبويب 4) وقائمة الأرباح والوفورات (تبويب 5) بدون أي ملفات خارجية."
                : "Deterministically coupled to Press Gantt demand (Tab 4) and synced live with Executive P&L (Tab 5). 100% in-dashboard."}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {wf && (
            <span className="hidden rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 font-mono text-[11px] text-slate-300 sm:inline-flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              {wf.status} • {wf.solve_time_ms} ms • {wf.shift_hours}h/shift
            </span>
          )}
          <button
            type="button"
            data-testid="btn-reoptimize-shifts"
            disabled={workforceLoading || loading || workers.length === 0}
            onClick={() => void handleReOptimize()}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {workforceLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            <span>
              {workforceLoading
                ? isAr
                  ? "جاري تحسين الورديات..."
                  : "Optimizing Shifts..."
                : isAr
                ? "إعادة تحسين الورديات"
                : "Re-Optimize Shifts"}
            </span>
          </button>
        </div>
      </div>

      {/* 1. Top 5 Workforce KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* KPI 1: Active Staff & Utilization */}
        <div
          data-testid="kpi-wf-staff"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "الكادر النشط والاستغلال" : "Active Staff & Utilization"}</span>
            <Users className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-xl font-bold text-white">
              {isAr ? `${activeCount} نشط | ${sickCount} مرضي` : `${activeCount} Active | ${sickCount} Sick`}
            </span>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
            <span>
              {isAr ? `إجمالي: ${workers.length}` : `Total: ${workers.length}`}
              {onLeaveCount > 0 ? (isAr ? ` • ${onLeaveCount} إجازة` : ` • ${onLeaveCount} Leave`) : ""}
            </span>
            <span className="font-mono font-semibold text-cyan-300">
              {utilizationPct}% {isAr ? "استغلال" : "util."}
            </span>
          </div>
        </div>

        {/* KPI 2: Weekly Labor & Overtime Saved */}
        <div
          data-testid="kpi-wf-savings"
          className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/15 via-[#0f1629] to-cyan-500/10 p-4 shadow-lg shadow-emerald-500/10"
        >
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-300">
            <span>{isAr ? "وفر العمالة والإضافي أسبوعياً" : "Weekly Labor & OT Saved"}</span>
            <Sparkles className="h-4 w-4 text-emerald-300" />
          </div>
          <div className="mt-2 font-mono text-2xl font-extrabold text-emerald-300" dir="ltr">
            {wf ? fmtMoney(wf.labor_cost_saved) : "—"}
          </div>
          <div className="mt-1.5 text-[11px] text-emerald-200/80" dir="ltr">
            {optKpis && baseKpis
              ? `${fmtMoney(baseKpis.total_labor_cost)} → ${fmtMoney(optKpis.total_labor_cost)}`
              : isAr
              ? "مقابل التدوير الثابت"
              : "vs. Static Rotation"}
          </div>
        </div>

        {/* KPI 3: Overtime Hours Reduced */}
        <div
          data-testid="kpi-wf-overtime"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "خفض ساعات العمل الإضافي" : "Overtime Hours Reduced"}</span>
            <Clock className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2" dir="ltr">
            <span className="font-mono text-2xl font-bold text-amber-300">
              {wf ? `-${formatNumber(wf.overtime_hours_cut, 0)}h` : "—"}
            </span>
          </div>
          <div className="mt-1.5 text-[11px] text-slate-400" dir="ltr">
            {optKpis && baseKpis
              ? `${formatNumber(baseKpis.overtime_hours, 0)}h → ${formatNumber(optKpis.overtime_hours, 0)}h ${
                  isAr ? "إضافي" : "OT"
                }`
              : "—"}
          </div>
        </div>

        {/* KPI 4: Shift & Changeover Coverage % */}
        <div
          data-testid="kpi-wf-coverage"
          className={`rounded-2xl border p-4 shadow-lg ${
            optKpis && optKpis.understaffed_slots > 0
              ? "border-amber-500/40 bg-amber-500/10"
              : "border-slate-800 bg-[#0f1629]"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "تغطية الورديات وتبديل القوالب" : "Shift & Changeover Coverage"}</span>
            {optKpis && optKpis.understaffed_slots > 0 ? (
              <AlertTriangle className="h-4 w-4 text-amber-400" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            )}
          </div>
          <div className="mt-2 flex items-baseline gap-2" dir="ltr">
            <span className="font-mono text-2xl font-bold text-white">
              {optKpis ? `${optKpis.coverage_pct.toFixed(1)}%` : "—"}
            </span>
            {optKpis && (
              <span
                className={`rounded-md px-1.5 py-0.5 font-mono text-[11px] font-bold ${
                  optKpis.changeover_readiness_pct >= 100
                    ? "bg-emerald-500/15 text-emerald-300"
                    : "bg-rose-500/20 text-rose-200"
                }`}
              >
                {isAr ? "قوالب" : "Mold"} {optKpis.changeover_readiness_pct.toFixed(0)}%
              </span>
            )}
          </div>
          <div className="mt-1.5 truncate text-[11px] text-slate-300">
            {optKpis?.worst_slot
              ? `${isAr ? "عجز:" : "Gap:"} ${optKpis.worst_slot}`
              : isAr
              ? "جميع الورديات مغطاة بالكامل"
              : "Zero understaffed shift slots"}
          </div>
        </div>

        {/* KPI 5: Compliance & Fairness */}
        <div
          data-testid="kpi-wf-compliance"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "الالتزام والعدالة" : "Compliance & Fairness"}</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <span
              className={`rounded-lg px-2 py-0.5 text-xs font-bold ${
                !wf || wf.all_hard_constraints_passed
                  ? "bg-emerald-500/15 text-emerald-300"
                  : "bg-rose-500/20 text-rose-200"
              }`}
            >
              {!wf || wf.all_hard_constraints_passed
                ? isAr
                  ? "100% التزام الراحة"
                  : "100% Rest-Rule Compliant"
                : `${optKpis?.violations ?? 0} Violations`}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
            <span>{isAr ? "تطابق تفضيلات الورديات:" : "Preference match:"}</span>
            <span className="font-mono font-bold text-cyan-300">
              {optKpis ? `${optKpis.preference_match_pct.toFixed(1)}%` : "—"}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Interactive Workforce Controls & Quick Disruption Strip */}
      <div className="grid gap-4 lg:grid-cols-12">
        {/* Controls Panel */}
        <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5 lg:col-span-7">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white">
                {isAr ? "أوزان وقواعد جدولة الورديات" : "Workforce Optimization Weights & Labor Rules"}
              </h3>
            </div>
            <span className="text-[11px] text-slate-400">
              {isAr ? "قواعد CP-SAT الصارمة (5/5)" : "OR-Tools CP-SAT Live Controls"}
            </span>
          </div>

          {/* 3 Live Sliders */}
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-slate-300">
                  {isAr ? "تكلفة العمالة والإضافي" : "Labor & Overtime Cost"}
                </span>
                <span className="font-mono font-bold text-cyan-300">{wfCfg.w_labor_cost}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                data-testid="slider-wf-cost"
                value={wfCfg.w_labor_cost}
                onChange={(e) => handleWeightSlider("w_labor_cost", Number(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-slate-300">
                  {isAr ? "تغطية الورديات" : "Shift Coverage"}
                </span>
                <span className="font-mono font-bold text-emerald-300">{wfCfg.w_coverage}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                data-testid="slider-wf-coverage"
                value={wfCfg.w_coverage}
                onChange={(e) => handleWeightSlider("w_coverage", Number(e.target.value))}
                className="w-full accent-emerald-400"
              />
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-slate-300">
                  {isAr ? "عدالة وتفضيلات العمال" : "Worker Fairness"}
                </span>
                <span className="font-mono font-bold text-amber-300">{wfCfg.w_fairness}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                data-testid="slider-wf-fairness"
                value={wfCfg.w_fairness}
                onChange={(e) => handleWeightSlider("w_fairness", Number(e.target.value))}
                className="w-full accent-amber-400"
              />
            </div>
          </div>

          {/* Numeric Physics Inputs */}
          <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-slate-800/80 pt-3.5">
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <span>{isAr ? "ماكينات لكل مشغل:" : "Presses / Operator:"}</span>
              <input
                type="number"
                min={1}
                max={4}
                data-testid="input-presses-per-operator"
                value={wfCfg.presses_per_operator}
                onChange={(e) => {
                  const v = Math.max(1, Math.min(4, Math.round(Number(e.target.value) || 1)));
                  updateWorkforceConfig({ presses_per_operator: v });
                  setHasPendingEdits(true);
                }}
                dir="ltr"
                className="w-16 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-center font-mono text-xs font-bold text-cyan-300 focus:border-cyan-500 focus:outline-none"
              />
            </label>

            <label className="flex items-center gap-2 text-xs text-slate-300">
              <span>{isAr ? "الحد الأدنى للراحة (ساعة):" : "Min Rest Hours:"}</span>
              <input
                type="number"
                min={0}
                max={16}
                data-testid="input-min-rest-hours"
                value={wfCfg.min_rest_hours}
                onChange={(e) => {
                  const v = Math.max(0, Math.min(16, Math.round(Number(e.target.value) || 0)));
                  updateWorkforceConfig({ min_rest_hours: v });
                  setHasPendingEdits(true);
                }}
                dir="ltr"
                className="w-16 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-center font-mono text-xs font-bold text-emerald-300 focus:border-emerald-500 focus:outline-none"
              />
            </label>

            <label className="flex items-center gap-2 text-xs text-slate-300">
              <span>{isAr ? "أيام راحة متتالية:" : "Min Days Off:"}</span>
              <select
                data-testid="select-min-days-off"
                value={wfCfg.min_consecutive_days_off}
                onChange={(e) => {
                  updateWorkforceConfig({ min_consecutive_days_off: Number(e.target.value) });
                  setHasPendingEdits(true);
                }}
                className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 font-mono text-xs font-bold text-amber-300 focus:border-amber-500 focus:outline-none"
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
              </select>
            </label>
          </div>
        </div>

        {/* Quick Disruption Strip */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-[#0f1629] p-5 lg:col-span-5">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HeartPulse className="h-4 w-4 text-rose-400" />
                <h3 className="text-sm font-bold text-white">
                  {isAr ? "اختبار الغياب والمرضي الفوري" : "Quick Callout / Sick Disruption Strip"}
                </h3>
              </div>
              <span className="text-[11px] text-slate-400">
                {isAr ? "اضغط للتبديل نشط / مرضي" : "Click to toggle Active / Sick"}
              </span>
            </div>
            <p className="mb-3 text-[11px] text-slate-400">
              {isAr
                ? "اختبر غياب فنيي القوالب أو المشغلين فوراً ثم اضغط إعادة تحسين الورديات لمشاهدة التوازن التلقائي."
                : "Mark key Mold Technicians or Operators Sick with one click, then press Re-Optimize Shifts to watch CP-SAT rebalance."}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {quickDisruptionWorkers.map((w) => {
                const isSick = w.status === "sick";
                return (
                  <button
                    key={w.worker_id}
                    type="button"
                    data-testid={`quick-sick-${w.worker_id}`}
                    onClick={() => handleToggleSick(w.worker_id)}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition ${
                      isSick
                        ? "border-rose-500/60 bg-rose-500/20 text-rose-200"
                        : "border-slate-700 bg-slate-900 text-slate-300 hover:border-cyan-500/50 hover:text-white"
                    }`}
                  >
                    <span className="font-mono text-[10px] opacity-80">{w.worker_id}</span>
                    <span>{w.name.split(" ")[0]}</span>
                    <span
                      className={`rounded px-1 py-0.5 text-[9px] font-bold uppercase ${
                        isSick ? "bg-rose-500 text-white" : "bg-emerald-500/20 text-emerald-300"
                      }`}
                    >
                      {isSick ? (isAr ? "مرضي" : "SICK") : isAr ? "نشط" : "OK"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 5 Hard Constraints Verification Strip */}
          {wf && (
            <div className="mt-4 flex flex-wrap gap-1.5 border-t border-slate-800/80 pt-3">
              {wf.constraints_verified.map((c) => (
                <span
                  key={c.id}
                  title={whcLabels[c.id] ?? c.name}
                  className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-semibold ${
                    c.passed
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                      : "border-rose-500/40 bg-rose-500/15 text-rose-200"
                  }`}
                >
                  {c.passed ? <Check className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                  <span>{c.id}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* No solved workforce yet notice */}
      {!wf && workers.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-5 py-4">
          <p className="text-xs text-cyan-100">
            {isAr
              ? "اضغط إعادة تحسين الورديات لبناء جدول الورديات الحتمي بناءً على مخطط المكابس."
              : "Press Re-Optimize Shifts (or Run CP-SAT) to generate the press-coupled 7-day shift roster."}
          </p>
          <button
            type="button"
            onClick={() => void (result ? handleReOptimize() : runSolve())}
            className="rounded-lg bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-400"
          >
            {isAr ? "تشغيل الجدولة الآن" : "Generate Shift Roster"}
          </button>
        </div>
      )}

      {/* 3. Sub-Panel A — Weekly Shift Roster Matrix */}
      {wf && activePlan && (
        <div
          data-testid="workforce-roster-matrix"
          className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629]"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-5 py-3.5">
            <div>
              <div className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">
                  {isAr
                    ? "أ. مصفوفة ورديات الأسبوع (العامل × الأيام)"
                    : "A. Weekly Shift Roster Matrix (Worker × Sun–Sat)"}
                </h3>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                {wf.shift_names.map((sn) => (
                  <span
                    key={sn}
                    className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${shiftCellStyle(sn)}`}
                  >
                    <span>{shiftLabels[sn] ?? sn}</span>
                    <span dir="ltr" className="font-mono opacity-80">
                      {wf.shift_windows[sn]}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Optimized vs Baseline switcher */}
              <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5 text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => setRosterPlanMode("optimized")}
                  className={`rounded-md px-2.5 py-1 transition ${
                    rosterPlanMode === "optimized"
                      ? "bg-cyan-500 text-slate-950"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {isAr ? "محسّن CP-SAT" : "CP-SAT Optimized"}
                </button>
                <button
                  type="button"
                  onClick={() => setRosterPlanMode("baseline")}
                  className={`rounded-md px-2.5 py-1 transition ${
                    rosterPlanMode === "baseline"
                      ? "bg-slate-700 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {isAr ? "تدوير ثابت" : "Static Rotation"}
                </button>
              </div>
            </div>
          </div>

          {/* Role Filter Bar */}
          <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800/70 bg-slate-900/40 px-5 py-2.5">
            <button
              type="button"
              data-testid="roster-filter-ALL"
              onClick={() => setRosterRoleFilter("ALL")}
              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                rosterRoleFilter === "ALL"
                  ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/40"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {isAr ? `الكل (${activePlan.rosters.length})` : `All (${activePlan.rosters.length})`}
            </button>
            {ALL_ROLES.map((r) => {
              const cnt = activePlan.rosters.filter((row) => row.role === r).length;
              return (
                <button
                  key={r}
                  type="button"
                  data-testid={`roster-filter-${r}`}
                  onClick={() => setRosterRoleFilter(r)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                    rosterRoleFilter === r
                      ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/40"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                  }`}
                >
                  {roleShort[r]} ({cnt})
                </button>
              );
            })}
          </div>

          {/* Matrix Table */}
          <div className="max-h-[430px] overflow-auto">
            <table className="w-full text-start text-xs">
              <thead className="sticky top-0 z-10 bg-slate-900 text-[11px] uppercase text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 text-start">{isAr ? "العامل" : "Worker"}</th>
                  <th className="px-3 py-2.5 text-start">{isAr ? "الدور" : "Role"}</th>
                  {dayNames.map((d) => (
                    <th key={d} className="px-2 py-2.5 text-center">
                      {d}
                    </th>
                  ))}
                  <th className="px-3 py-2.5 text-end">{isAr ? "الساعات" : "Hrs"}</th>
                  <th className="px-3 py-2.5 text-end">{isAr ? "إضافي" : "OT"}</th>
                  <th className="px-4 py-2.5 text-end">{isAr ? "التكلفة" : "Cost"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {filteredRosterRows.map((row) => {
                  const liveW = workersById.get(row.worker_id);
                  return (
                    <tr
                      key={row.worker_id}
                      data-testid={`roster-row-${row.worker_id}`}
                      className="hover:bg-slate-900/50"
                    >
                      <td className="whitespace-nowrap px-4 py-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] font-bold text-cyan-300">
                            {row.worker_id}
                          </span>
                          <span className="font-medium text-white">{row.name}</span>
                          {liveW && liveW.status === "sick" && !row.cells.every((c) => c === "SICK") && (
                            <span className="rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] font-bold text-rose-300">
                              {isAr ? "مرضي (بانتظار إعادة التحسين)" : "SICK (pending)"}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2">
                        <span
                          className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-semibold ${ROLE_BADGE_CLASSES[row.role]}`}
                        >
                          {roleLabels[row.role]}
                        </span>
                      </td>
                      {row.cells.map((cell, idx) => (
                        <td key={idx} className="px-1.5 py-2 text-center">
                          <span
                            className={`inline-block min-w-[66px] rounded-md border px-1.5 py-0.5 text-[10px] font-bold ${shiftCellStyle(cell)}`}
                          >
                            {shiftLabels[cell] ?? cell}
                          </span>
                        </td>
                      ))}
                      <td className="px-3 py-2 text-end font-mono font-bold text-slate-200" dir="ltr">
                        {row.weekly_hours}h
                      </td>
                      <td className="px-3 py-2 text-end font-mono" dir="ltr">
                        {row.overtime_hours > 0 ? (
                          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-300">
                            +{row.overtime_hours}h
                          </span>
                        ) : (
                          <span className="text-slate-600">0h</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-end font-mono text-slate-300" dir="ltr">
                        {fmtMoney(row.labor_cost)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. Sub-Panel B — Press-Driven Staffing Demand vs. Scheduled Coverage Chart */}
      {wf && (
        <div
          data-testid="workforce-demand-chart"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-5"
        >
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">
                  {isAr
                    ? "ب. الطلب المشتق من المكابس مقابل التغطية المجدولة"
                    : "B. Press-Driven Staffing Demand vs. Scheduled Coverage"}
                </h3>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">
                {isAr
                  ? "الطلب محسوب تلقائياً من المكابس النشطة وتبديلات القوالب وتجفيف PET/ABS في مخطط جانت. الأعمدة الوردية تشير لعجز تغطية."
                  : "Required floor headcount is derived directly from active presses, mold swaps, PM blocks & PET/ABS drying in Tab 4. Rose bars flag understaffed slots."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                data-testid="chart-role-select"
                value={chartRoleFilter}
                onChange={(e) => setChartRoleFilter(e.target.value as "ALL" | WorkerRole)}
                className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-200 focus:border-cyan-500 focus:outline-none"
              >
                <option value="ALL">{isAr ? "جميع الأدوار" : "All Roles"}</option>
                {ALL_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {roleLabels[r]}
                  </option>
                ))}
              </select>

              <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5 text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => setChartGroupMode("slot")}
                  className={`rounded-md px-2.5 py-1 transition ${
                    chartGroupMode === "slot"
                      ? "bg-cyan-500 text-slate-950"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {isAr ? "حسب الوردية" : "By Shift Slot"}
                </button>
                <button
                  type="button"
                  onClick={() => setChartGroupMode("day")}
                  className={`rounded-md px-2.5 py-1 transition ${
                    chartGroupMode === "day"
                      ? "bg-cyan-500 text-slate-950"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {isAr ? "حسب اليوم" : "By Day"}
                </button>
              </div>
            </div>
          </div>

          <div dir="ltr" className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="label"
                  stroke="#94a3b8"
                  fontSize={10}
                  interval={0}
                  angle={chartGroupMode === "slot" ? -30 : 0}
                  textAnchor={chartGroupMode === "slot" ? "end" : "middle"}
                  height={chartGroupMode === "slot" ? 48 : 28}
                />
                <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const item = payload[0]?.payload as {
                      required: number;
                      scheduled: number;
                      gap: number;
                      reasons: string[];
                    };
                    return (
                      <div className="max-w-xs rounded-xl border border-slate-700 bg-[#0b1120] p-3 text-xs text-slate-100 shadow-xl">
                        <div className="mb-1.5 font-bold text-white">{label}</div>
                        <div className="flex items-center justify-between gap-4">
                          <span className="text-slate-400">
                            {isAr ? "المطلوب:" : "Required:"}
                          </span>
                          <span className="font-mono font-bold text-slate-200">{item.required}</span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span className="text-slate-400">
                            {isAr ? "المجدول:" : "Scheduled:"}
                          </span>
                          <span
                            className={`font-mono font-bold ${
                              item.gap > 0 ? "text-rose-400" : "text-cyan-300"
                            }`}
                          >
                            {item.scheduled}
                          </span>
                        </div>
                        {item.gap > 0 && (
                          <div className="mt-1 font-semibold text-rose-300">
                            {isAr ? `عجز: -${item.gap}` : `Shortfall: -${item.gap}`}
                          </div>
                        )}
                        {item.reasons.length > 0 && (
                          <div className="mt-2 border-t border-slate-800 pt-1.5 text-[10px] text-slate-400">
                            {item.reasons.map((r, i) => (
                              <div key={i}>• {r}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Bar
                  dataKey="required"
                  name={isAr ? "العدد المطلوب" : "Required Headcount"}
                  fill="#475569"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="scheduled"
                  name={isAr ? "المجدول فعلياً" : "Scheduled Workers"}
                  fill="#22d3ee"
                  radius={[4, 4, 0, 0]}
                >
                  {chartData.map((entry, idx) => (
                    <Cell key={`bar-${idx}`} fill={entry.understaffed ? "#f43f5e" : "#22d3ee"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Bottleneck understaffed slots callout */}
          {understaffedBottlenecks.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-800/80 pt-3">
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-300">
                <AlertTriangle className="h-3.5 w-3.5" />
                {isAr ? "ورديات بها عجز تغطية:" : "Bottleneck Understaffed Slots:"}
              </span>
              {understaffedBottlenecks.map((c, idx) => (
                <span
                  key={`${c.day}-${c.shift}-${c.role}-${idx}`}
                  className="rounded-lg border border-rose-500/35 bg-rose-500/10 px-2 py-0.5 text-[11px] text-rose-200"
                >
                  {dayNames[c.day]} {shiftLabels[c.shift] ?? c.shift} • {roleLabels[c.role]} ({c.scheduled}/
                  {c.required})
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 5. Sub-Panel C — Worker Directory & Inline CRUD Editor */}
      <div
        data-testid="workforce-directory"
        className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629]"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-5 py-3.5">
          <div>
            <div className="flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white">
                {isAr
                  ? "ج. دليل العمال والمحرر المباشر (إضافة / تعديل / إجازات / مرضي)"
                  : "C. Worker Directory & Inline CRUD Editor"}
              </h3>
            </div>
            <p className="mt-0.5 text-[11px] text-slate-400">
              {isAr
                ? "اضغط على أيام الأسبوع لتفعيل الإجازات المعتمدة، أو بدّل الحالة بين نشط/مرضي. كل تعديل يُحفظ تلقائياً في مساحة العمل."
                : "Click day pills to toggle Approved Leave Days or flip Active/Sick status. Every edit auto-saves to the active Plant Workspace."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute start-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                data-testid="input-search-workers"
                value={dirSearch}
                onChange={(e) => setDirSearch(e.target.value)}
                placeholder={isAr ? "بحث بالاسم أو الرمز..." : "Search worker ID or name..."}
                className="rounded-xl border border-slate-700 bg-slate-900 py-1.5 pe-3 ps-8 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <select
              value={dirRoleFilter}
              onChange={(e) => setDirRoleFilter(e.target.value as "ALL" | WorkerRole)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              <option value="ALL">{isAr ? "كل الأدوار" : "All Roles"}</option>
              {ALL_ROLES.map((r) => (
                <option key={r} value={r}>
                  {roleLabels[r]}
                </option>
              ))}
            </select>

            <button
              type="button"
              data-testid="btn-add-worker"
              onClick={openAddWorker}
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-400"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>{isAr ? "إضافة عامل" : "Add Worker"}</span>
            </button>
          </div>
        </div>

        {/* Inline Add / Edit Form Drawer */}
        {editorOpen && (
          <form
            onSubmit={handleSaveWorker}
            data-testid="worker-editor-form"
            className="border-b border-cyan-500/30 bg-slate-900/90 p-5"
          >
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-cyan-300">
                <UserPlus className="h-4 w-4" />
                <span>
                  {editingOriginalId
                    ? isAr
                      ? `تعديل العامل ${editingOriginalId}`
                      : `Edit Worker ${editingOriginalId}`
                    : isAr
                    ? "إضافة عامل جديد للمصنع"
                    : "Add New Factory Worker"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setEditorOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {formError && (
              <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/15 px-3 py-2 text-xs text-rose-200">
                {formError}
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">{isAr ? "رمز العامل" : "Worker ID"}</span>
                <input
                  type="text"
                  required
                  data-testid="worker-form-id"
                  value={draft.worker_id}
                  onChange={(e) => setDraft({ ...draft, worker_id: e.target.value })}
                  dir="ltr"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-white focus:border-cyan-500 focus:outline-none"
                />
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">{isAr ? "الاسم الكامل" : "Full Name"}</span>
                <input
                  type="text"
                  required
                  data-testid="worker-form-name"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  placeholder={isAr ? "مثال: محمد علي" : "e.g. Mohamed Ali"}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                />
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">{isAr ? "الدور الوظيفي" : "Role"}</span>
                <select
                  data-testid="worker-form-role"
                  value={draft.role}
                  onChange={(e) => {
                    const nextRole = e.target.value as WorkerRole;
                    setDraft((prev) => ({
                      ...prev,
                      role: nextRole,
                      worker_id: editingOriginalId ? prev.worker_id : nextWorkerIdForRole(nextRole),
                    }));
                  }}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                >
                  {ALL_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {roleLabels[r]}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">
                  {isAr ? "الوردية المفضلة" : "Preferred Shift"}
                </span>
                <select
                  data-testid="worker-form-pref"
                  value={draft.preferred_shift}
                  onChange={(e) =>
                    setDraft({ ...draft, preferred_shift: e.target.value as PreferredShift })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                >
                  {(["Any", "Morning", "Afternoon", "Night"] as const).map((sh) => (
                    <option key={sh} value={sh}>
                      {shiftLabels[sh]}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">
                  {isAr ? `الأجر بالساعة (${currency})` : `Hourly Rate (${currency})`}
                </span>
                <input
                  type="number"
                  min={1}
                  step={0.5}
                  required
                  data-testid="worker-form-rate"
                  value={draft.hourly_rate_display}
                  onChange={(e) => setDraft({ ...draft, hourly_rate_display: e.target.value })}
                  dir="ltr"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-white focus:border-cyan-500 focus:outline-none"
                />
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">
                  {isAr ? "مضاعف الإضافي" : "OT Multiplier"}
                </span>
                <input
                  type="number"
                  min={1}
                  max={4}
                  step={0.1}
                  data-testid="worker-form-ot"
                  value={draft.overtime_multiplier}
                  onChange={(e) => setDraft({ ...draft, overtime_multiplier: e.target.value })}
                  dir="ltr"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-white focus:border-cyan-500 focus:outline-none"
                />
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">
                  {isAr ? "سقف الساعات الأسبوعي" : "Max Weekly Hours"}
                </span>
                <input
                  type="number"
                  min={8}
                  max={84}
                  step={2}
                  data-testid="worker-form-maxhrs"
                  value={draft.max_weekly_hours}
                  onChange={(e) => setDraft({ ...draft, max_weekly_hours: e.target.value })}
                  dir="ltr"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-white focus:border-cyan-500 focus:outline-none"
                />
              </label>

              <label className="block text-xs">
                <span className="mb-1 block text-slate-400">{isAr ? "الحالة" : "Status"}</span>
                <select
                  data-testid="worker-form-status"
                  value={draft.status}
                  onChange={(e) => setDraft({ ...draft, status: e.target.value as WorkerStatus })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="active">{isAr ? "نشط" : "Active"}</option>
                  <option value="sick">{isAr ? "مرضي" : "Sick"}</option>
                  <option value="on_leave">{isAr ? "إجازة" : "On Leave"}</option>
                </select>
              </label>
            </div>

            {/* Certified Presses & Approved Leave Days */}
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <span className="mb-1.5 block text-xs text-slate-400">
                  {isAr ? "شهادات المكابس المؤهل لها" : "Certified Presses"}
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setDraft((p) => ({ ...p, certAll: !p.certAll }))}
                    className={`rounded-md border px-2 py-1 text-[11px] font-bold transition ${
                      draft.certAll
                        ? "border-cyan-500/60 bg-cyan-500/20 text-cyan-200"
                        : "border-slate-700 bg-slate-950 text-slate-400"
                    }`}
                  >
                    ALL
                  </button>
                  {!draft.certAll &&
                    presses.map((p) => {
                      const on = draft.certPresses.includes(p.machine_id);
                      return (
                        <button
                          key={p.machine_id}
                          type="button"
                          onClick={() =>
                            setDraft((prev) => ({
                              ...prev,
                              certPresses: on
                                ? prev.certPresses.filter((id) => id !== p.machine_id)
                                : [...prev.certPresses, p.machine_id],
                            }))
                          }
                          className={`rounded-md border px-2 py-1 font-mono text-[11px] font-semibold transition ${
                            on
                              ? "border-emerald-500/60 bg-emerald-500/20 text-emerald-200"
                              : "border-slate-700 bg-slate-950 text-slate-400"
                          }`}
                        >
                          {p.machine_id}
                        </button>
                      );
                    })}
                </div>
              </div>

              <div>
                <span className="mb-1.5 block text-xs text-slate-400">
                  {isAr ? "أيام الإجازة المعتمدة" : "Approved Leave Days"}
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {dayNames.map((dLabel, dIdx) => {
                    const on = draft.approved_leave_days.includes(dIdx);
                    return (
                      <button
                        key={dIdx}
                        type="button"
                        onClick={() =>
                          setDraft((prev) => ({
                            ...prev,
                            approved_leave_days: on
                              ? prev.approved_leave_days.filter((x) => x !== dIdx)
                              : [...prev.approved_leave_days, dIdx].sort((a, b) => a - b),
                          }))
                        }
                        className={`rounded-md border px-2 py-1 text-[11px] font-semibold transition ${
                          on
                            ? "border-teal-400/60 bg-teal-500/25 text-teal-200"
                            : "border-slate-700 bg-slate-950 text-slate-400"
                        }`}
                      >
                        {dLabel}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditorOpen(false)}
                className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700"
              >
                {isAr ? "إلغاء" : "Cancel"}
              </button>
              <button
                type="submit"
                data-testid="worker-form-submit"
                className="rounded-lg bg-cyan-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-400"
              >
                {editingOriginalId
                  ? isAr
                    ? "حفظ التعديل"
                    : "Save Worker"
                  : isAr
                  ? "إضافة للقائمة"
                  : "Add Worker"}
              </button>
            </div>
          </form>
        )}

        {/* Directory Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-start text-xs">
            <thead className="bg-slate-900/70 text-[11px] uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3 text-start">{isAr ? "الرمز والاسم" : "Worker"}</th>
                <th className="px-3 py-3 text-start">{isAr ? "الدور" : "Role"}</th>
                <th className="px-3 py-3 text-start">{isAr ? "المكابس المؤهل لها" : "Certified Presses"}</th>
                <th className="px-3 py-3 text-end">{isAr ? "الأجر / الحد" : "Rate / Cap"}</th>
                <th className="px-3 py-3 text-center">{isAr ? "التفضيل" : "Pref"}</th>
                <th className="px-3 py-3 text-center">
                  {isAr ? "أيام الإجازة (اضغط للتبديل)" : "Approved Leave Days"}
                </th>
                <th className="px-3 py-3 text-center">{isAr ? "الحالة" : "Status"}</th>
                <th className="px-4 py-3 text-end">{isAr ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredDirectory.map((w) => {
                const isSick = w.status === "sick";
                return (
                  <tr
                    key={w.worker_id}
                    data-testid={`worker-dir-row-${w.worker_id}`}
                    className={`hover:bg-slate-900/40 ${isSick ? "bg-rose-950/20" : ""}`}
                  >
                    <td className="whitespace-nowrap px-4 py-2.5">
                      <div className="font-mono text-[11px] font-bold text-cyan-300">{w.worker_id}</div>
                      <div className="font-semibold text-white">{w.name}</div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5">
                      <span
                        className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-semibold ${ROLE_BADGE_CLASSES[w.role]}`}
                      >
                        {roleLabels[w.role]}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      {w.certified_machine_ids === "ALL" ? (
                        <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-200">
                          ALL
                        </span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {w.certified_machine_ids.map((mid) => (
                            <span
                              key={mid}
                              className="rounded bg-slate-800/90 px-1.5 py-0.5 font-mono text-[10px] text-slate-300"
                            >
                              {mid}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-end font-mono" dir="ltr">
                      <div className="font-bold text-white">{fmtSarRate(w.hourly_rate)}</div>
                      <div className="text-[10px] text-slate-400">
                        max {w.max_weekly_hours}h • {w.overtime_multiplier}x OT
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-300">
                        {shiftLabels[w.preferred_shift]}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center justify-center gap-1">
                        {dayNames.map((dLabel, dIdx) => {
                          const onLeave = w.approved_leave_days.includes(dIdx);
                          return (
                            <button
                              key={dIdx}
                              type="button"
                              data-testid={`btn-leave-${w.worker_id}-${dIdx}`}
                              onClick={() => handleToggleLeave(w.worker_id, dIdx)}
                              title={
                                isAr
                                  ? `تبديل إجازة ${dLabel}`
                                  : `Toggle approved leave on ${dLabel}`
                              }
                              className={`rounded border px-1.5 py-0.5 text-[10px] font-bold transition ${
                                onLeave
                                  ? "border-teal-400/60 bg-teal-500/25 text-teal-200"
                                  : "border-slate-800 bg-slate-900/70 text-slate-500 hover:border-slate-600 hover:text-slate-300"
                              }`}
                            >
                              {isAr ? dLabel.slice(0, 2) : dLabel.slice(0, 2)}
                            </button>
                          );
                        })}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center">
                      <button
                        type="button"
                        data-testid={`btn-toggle-sick-${w.worker_id}`}
                        onClick={() => handleToggleSick(w.worker_id)}
                        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-bold transition ${
                          isSick
                            ? "border-rose-500/60 bg-rose-500/20 text-rose-200 hover:bg-rose-500/30"
                            : w.status === "on_leave"
                            ? "border-teal-500/50 bg-teal-500/15 text-teal-200 hover:bg-teal-500/25"
                            : "border-emerald-500/40 bg-emerald-500/15 text-emerald-300 hover:bg-rose-500/15 hover:border-rose-500/40 hover:text-rose-200"
                        }`}
                      >
                        {isSick
                          ? isAr
                            ? "مرضي ↺ نشط"
                            : "Sick → Active"
                          : w.status === "on_leave"
                          ? isAr
                            ? "إجازة"
                            : "On Leave"
                          : isAr
                          ? "نشط → مرضي"
                          : "Active → Sick"}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-end">
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          data-testid={`btn-edit-worker-${w.worker_id}`}
                          onClick={() => openEditWorker(w)}
                          title={isAr ? "تعديل" : "Edit"}
                          className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 transition hover:border-cyan-500 hover:text-cyan-300"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          data-testid={`btn-dup-worker-${w.worker_id}`}
                          onClick={() => handleDuplicateWorker(w.worker_id)}
                          title={isAr ? "نسخ" : "Duplicate"}
                          className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-300 transition hover:border-cyan-500 hover:text-cyan-300"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          data-testid={`btn-del-worker-${w.worker_id}`}
                          onClick={() => handleDeleteWorker(w.worker_id)}
                          title={isAr ? "حذف" : "Delete"}
                          className="rounded-lg border border-slate-700 bg-slate-800 p-1.5 text-slate-400 transition hover:border-rose-500/60 hover:text-rose-300"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredDirectory.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-xs text-slate-400">
                    {isAr
                      ? "لا يوجد عمال مطابقون لبحثك. اضغط 'إضافة عامل' لإضافة الكادر."
                      : "No workers match your filter. Click '+ Add Worker' to add floor staff."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
