"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Boxes,
  Cpu,
  Download,
  GitBranch,
  Layers,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Table2,
  Workflow,
  X,
} from "lucide-react";
import { downloadDiBlueprintArtifact } from "@/lib/api";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { DIBlueprintTab } from "@/lib/types";
import { ArchOntologyView } from "./ArchOntologyView";
import { BPMNFlowView } from "./BPMNFlowView";
import { CausalDiagramView } from "./CausalDiagramView";
import { DMNInspectorView } from "./DMNInspectorView";

export function DIBlueprintModal() {
  const {
    lang,
    activeEngine,
    diBlueprintModalOpen,
    setDiBlueprintModalOpen,
    diBlueprintTab,
    setDiBlueprintTab,
    diBlueprintData,
    diBlueprintLoading,
    diBlueprintError,
    refreshDiBlueprint,
  } = useApp();

  const t = COPY[lang];
  const isUemActive = activeEngine === "uem_di_v1";
  const [downloadingFmt, setDownloadingFmt] = useState<string | null>(null);

  useEffect(() => {
    if (!diBlueprintModalOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDiBlueprintModalOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [diBlueprintModalOpen, setDiBlueprintModalOpen]);

  if (!diBlueprintModalOpen) return null;

  const handleDownload = async (fmt: "json" | "bpmn_xml" | "dmn_xml") => {
    if (downloadingFmt) return;
    setDownloadingFmt(fmt);
    try {
      await downloadDiBlueprintArtifact(fmt);
    } finally {
      setDownloadingFmt(null);
    }
  };

  const subTabs: { id: DIBlueprintTab; label: string; icon: React.ReactNode }[] = [
    { id: "causal", label: t.diTabCausal, icon: <GitBranch className="h-3.5 w-3.5 shrink-0" /> },
    { id: "dmn", label: t.diTabDmn, icon: <Table2 className="h-3.5 w-3.5 shrink-0" /> },
    { id: "bpmn", label: t.diTabBpmn, icon: <Workflow className="h-3.5 w-3.5 shrink-0" /> },
    { id: "arch_uem", label: t.diTabArchUem, icon: <Boxes className="h-3.5 w-3.5 shrink-0" /> },
  ];

  return (
    <div
      data-testid="di-blueprint-modal"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm sm:items-center sm:p-4"
    >
      <div
        className="fixed inset-0"
        onClick={() => setDiBlueprintModalOpen(false)}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={t.diModalTitle}
        className="relative z-10 flex h-[94dvh] w-full max-w-[1360px] flex-col overflow-hidden rounded-t-3xl border-t border-slate-700/80 bg-[#060a14] shadow-2xl sm:h-[90dvh] sm:rounded-2xl sm:border"
      >
        {/* Top Modal Header + Persistent Export Bar */}
        <div className="border-b border-slate-800 bg-[#090f1e] px-4 py-3 sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-500/15 text-cyan-300">
                <Layers className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="truncate text-sm font-bold text-white sm:text-base">
                    {t.diModalTitle}
                  </h2>
                  <span
                    data-testid="di-modal-engine-badge"
                    dir="ltr"
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-bold ${
                      isUemActive
                        ? "border-emerald-500/45 bg-emerald-500/15 text-emerald-200"
                        : "border-amber-500/45 bg-amber-500/15 text-amber-200"
                    }`}
                  >
                    <Cpu className="h-3 w-3 shrink-0" />
                    <span>{activeEngine}</span>
                  </span>
                </div>
                <p className="hidden truncate text-xs text-slate-400 sm:block">
                  {t.diModalSubtitle}
                </p>
              </div>
            </div>

            {/* Persistent Export & Refresh Bar */}
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <button
                type="button"
                data-testid="btn-di-refresh"
                disabled={diBlueprintLoading}
                onClick={() => void refreshDiBlueprint(true)}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-white disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 text-cyan-400 ${diBlueprintLoading ? "animate-spin" : ""}`} />
                <span className="hidden md:inline">{t.diRefreshBtn}</span>
              </button>

              <button
                type="button"
                data-testid="btn-di-download-json"
                disabled={downloadingFmt !== null}
                onClick={() => void handleDownload("json")}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-1.5 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/20 disabled:opacity-50"
              >
                {downloadingFmt === "json" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Download className="h-3.5 w-3.5 text-cyan-400" />
                )}
                <span>{t.diDownloadJsonBtn}</span>
              </button>

              <button
                type="button"
                data-testid="btn-di-download-bpmn"
                disabled={downloadingFmt !== null}
                onClick={() => void handleDownload("bpmn_xml")}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1.5 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/20 disabled:opacity-50"
              >
                {downloadingFmt === "bpmn_xml" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Download className="h-3.5 w-3.5 text-emerald-400" />
                )}
                <span>{t.diDownloadBpmnBtn}</span>
              </button>

              <button
                type="button"
                data-testid="btn-di-download-dmn"
                disabled={downloadingFmt !== null}
                onClick={() => void handleDownload("dmn_xml")}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-500/10 px-2.5 py-1.5 text-xs font-semibold text-purple-200 transition hover:bg-purple-500/20 disabled:opacity-50"
              >
                {downloadingFmt === "dmn_xml" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Download className="h-3.5 w-3.5 text-purple-400" />
                )}
                <span>{t.diDownloadDmnBtn}</span>
              </button>

              <button
                type="button"
                data-testid="btn-close-di-modal"
                onClick={() => setDiBlueprintModalOpen(false)}
                className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-xl border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-rose-500/50 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Engine Status Notice + 4 Sub-Tab Bar */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2.5">
            <div className="no-scrollbar flex min-w-0 flex-1 flex-nowrap items-center gap-1.5 overflow-x-auto whitespace-nowrap">
              {subTabs.map((tab) => {
                const active = diBlueprintTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    data-testid={`di-subtab-${tab.id}`}
                    onClick={() => setDiBlueprintTab(tab.id)}
                    className={`inline-flex min-h-[38px] shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                      active
                        ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                        : "border border-slate-800 bg-slate-900/90 text-slate-300 hover:border-slate-700 hover:text-white"
                    }`}
                  >
                    {tab.icon}
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            <div
              data-testid="di-engine-mode-notice"
              className={`hidden items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] xl:inline-flex ${
                isUemActive
                  ? "border-emerald-500/35 bg-emerald-500/10 text-emerald-200"
                  : "border-amber-500/35 bg-amber-500/10 text-amber-200"
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
              <span>{isUemActive ? t.diUemEngineActiveNotice : t.diLegacyEngineNotice}</span>
            </div>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {!isUemActive && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-amber-500/35 bg-amber-500/10 px-3.5 py-2 text-xs text-amber-200 xl:hidden">
              <ShieldCheck className="h-4 w-4 shrink-0 text-amber-400" />
              <span>{t.diLegacyEngineNotice}</span>
            </div>
          )}

          {diBlueprintError && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 px-4 py-3 text-xs text-rose-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{diBlueprintError}</span>
            </div>
          )}

          {diBlueprintLoading && !diBlueprintData ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3 text-slate-300">
              <Loader2 className="h-7 w-7 animate-spin text-cyan-400" />
              <span className="text-xs font-semibold">
                {lang === "ar"
                  ? "جارٍ تحميل مخطط ذكاء القرار ذي الـ 5 طبقات..."
                  : "Compiling 5-Layer Decision Intelligence & 6-Primitive UEM Blueprint..."}
              </span>
            </div>
          ) : diBlueprintData ? (
            <>
              {diBlueprintTab === "causal" && (
                <CausalDiagramView
                  blueprint={diBlueprintData}
                  onJumpToTab={(target) => setDiBlueprintTab(target)}
                />
              )}
              {diBlueprintTab === "dmn" && <DMNInspectorView blueprint={diBlueprintData} />}
              {diBlueprintTab === "bpmn" && <BPMNFlowView blueprint={diBlueprintData} />}
              {diBlueprintTab === "arch_uem" && <ArchOntologyView blueprint={diBlueprintData} />}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
