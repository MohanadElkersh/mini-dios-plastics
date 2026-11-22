"use client";

import React from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Cpu,
  Factory,
  Layers,
  Loader2,
  Package,
  Play,
  RotateCcw,
  Sliders,
} from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { StudioSubTab } from "@/lib/store";
import { MoldsEditor } from "./studio/MoldsEditor";
import { OrdersEditor } from "./studio/OrdersEditor";
import { PhysicsEditor } from "./studio/PhysicsEditor";
import { PressesEditor } from "./studio/PressesEditor";
import { ResinsEditor } from "./studio/ResinsEditor";

export function DataStudioView() {
  const {
    lang,
    dataset,
    validation,
    loading,
    modifiedCount,
    resetCurrentPlantToDemo,
    validateAndSolveToView,
    studioSubTab,
    setStudioSubTab,
  } = useApp();

  const t = COPY[lang];

  const subTabs: { id: StudioSubTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "presses", label: t.studioSubPresses, icon: <Factory className="h-3.5 w-3.5" />, count: dataset?.presses.length },
    { id: "molds", label: t.studioSubMolds, icon: <Layers className="h-3.5 w-3.5" />, count: dataset?.molds.length },
    { id: "resins", label: t.studioSubResins, icon: <Package className="h-3.5 w-3.5" />, count: dataset?.resins.length },
    { id: "orders", label: t.studioSubOrders, icon: <ClipboardList className="h-3.5 w-3.5" />, count: dataset?.orders.length },
    { id: "physics", label: t.studioSubPhysics, icon: <Sliders className="h-3.5 w-3.5" /> },
  ];

  const errCount = validation?.error_count ?? 0;
  const warnCount = validation?.warning_count ?? 0;
  const isReady = validation ? validation.ready : true;

  return (
    <div className="space-y-5 pb-20">
      {/* Studio Sticky Action Bar */}
      <div
        data-testid="studio-action-bar"
        className="sticky top-[106px] z-20 rounded-2xl border border-slate-800 bg-[#0b1120]/95 p-4 shadow-xl backdrop-blur"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-bold text-white">{t.studioTitle}</h2>
              {/* Modified Items Badge */}
              <span
                data-testid="studio-modified-badge"
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  modifiedCount > 0
                    ? "border border-amber-400/50 bg-amber-500/20 text-amber-200"
                    : "border border-slate-700 bg-slate-800 text-slate-300"
                }`}
              >
                {modifiedCount > 0 ? `${modifiedCount} ${t.studioModifiedBadge}` : t.studioSyncedBadge}
              </span>

              {/* Live Pre-Solve Anomaly Status Pill */}
              {validation && (
                <span
                  data-testid="studio-validation-pill"
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                    errCount > 0
                      ? "border border-rose-500/50 bg-rose-500/20 text-rose-200"
                      : warnCount > 0
                        ? "border border-amber-500/40 bg-amber-500/15 text-amber-200"
                        : "border border-emerald-500/40 bg-emerald-500/15 text-emerald-200"
                  }`}
                >
                  {errCount > 0 ? <AlertCircle className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
                  <span>
                    {errCount === 0 && warnCount === 0
                      ? "Ready"
                      : `${warnCount} Warnings / ${errCount} Errors`}
                  </span>
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-400">{t.studioSubtitle}</p>
          </div>

          {/* Action Buttons (Zero File Transfers) */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="btn-reset-demo"
              disabled={loading}
              onClick={() => void resetCurrentPlantToDemo()}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-rose-500/50 hover:text-rose-200 disabled:opacity-40"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>{t.studioResetDemo}</span>
            </button>

            <button
              type="button"
              data-testid="btn-studio-validate-solve"
              disabled={loading || !dataset || !isReady}
              onClick={() => void validateAndSolveToView("gantt")}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              <span>{loading ? t.solving : t.studioValidateSolve}</span>
            </button>
          </div>
        </div>

        {/* 5 Studio Sub-Tabs */}
        <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-slate-800/80 pt-3">
          {subTabs.map((st) => {
            const active = studioSubTab === st.id;
            return (
              <button
                key={st.id}
                type="button"
                data-testid={`studio-subtab-${st.id}`}
                onClick={() => setStudioSubTab(st.id)}
                className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                  active
                    ? "bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/50"
                    : "bg-slate-900/70 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                {st.icon}
                <span>{st.label}</span>
                {st.count !== undefined && (
                  <span className="rounded-md bg-slate-950/70 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                    {st.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Live Blocking Errors Banner if any */}
      {validation && validation.issues.some((i) => i.severity === "error") && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-xs text-rose-100">
          <div className="mb-1.5 flex items-center gap-2 font-bold text-rose-200">
            <AlertCircle className="h-4 w-4" />
            <span>Pre-Solve Blocking Errors ({validation.error_count})</span>
          </div>
          <ul className="space-y-1 text-[11px]">
            {validation.issues
              .filter((i) => i.severity === "error")
              .map((i, idx) => (
                <li key={idx}>
                  <span className="font-mono font-bold">[{i.code}]</span> {i.message}
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Active Sub-Tab Body */}
      {studioSubTab === "presses" && <PressesEditor />}
      {studioSubTab === "molds" && <MoldsEditor />}
      {studioSubTab === "resins" && <ResinsEditor />}
      {studioSubTab === "orders" && <OrdersEditor />}
      {studioSubTab === "physics" && <PhysicsEditor />}
    </div>
  );
}
