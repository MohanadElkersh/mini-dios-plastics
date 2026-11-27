"use client";

import React, { useEffect, useState } from "react";
import { createRealtimeClient, type SealedLiveQuery } from "@neon/realtime/client";
import {
  CheckCircle2,
  Clock,
  Database,
  History,
  Loader2,
  Plus,
  Radio,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { DecisionCheckpoint } from "@/lib/types";

export function DecisionCheckpointsDrawer() {
  const {
    lang,
    currency,
    config,
    checkpoints,
    storageBackend,
    checkpointsDrawerOpen,
    setCheckpointsDrawerOpen,
    refreshCheckpoints,
    saveManualCheckpoint,
    restoreCheckpoint,
    checkpointToast,
    clearCheckpointToast,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [savingManual, setSavingManual] = useState(false);
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const [neonFunctionReply, setNeonFunctionReply] = useState<string | null>(null);

  useEffect(() => {
    if (checkpointsDrawerOpen) {
      void refreshCheckpoints(true);
    }
  }, [checkpointsDrawerOpen, refreshCheckpoints]);

  // Wire Neon Realtime (@neon/realtime/client) + Neon Functions & Services status when drawer is open
  useEffect(() => {
    if (!checkpointsDrawerOpen) return;
    let cancelled = false;
    let closeClient: (() => void) | null = null;

    async function connectNeonRealtimeAndStatus() {
      try {
        const [rtResp, stResp] = await Promise.all([
          fetch("/api/neon/realtime", { cache: "no-store" }),
          fetch("/api/neon/frontend-status", { cache: "no-store" }),
        ]);
        if (cancelled) return;

        if (stResp.ok) {
          const stData = (await stResp.json()) as {
            services?: { functions?: { body?: string } };
          };
          const fnBody = stData?.services?.functions?.body;
          if (fnBody) setNeonFunctionReply(fnBody.trim());
        }

        if (rtResp.ok) {
          const rtData = (await rtResp.json()) as {
            ok?: boolean;
            realtimeUrl?: string;
            sealedQuery?: SealedLiveQuery<Record<string, unknown>>;
          };
          if (rtData.ok && rtData.realtimeUrl && rtData.sealedQuery) {
            const client = createRealtimeClient({ url: rtData.realtimeUrl });
            const sub = client.subscribe(rtData.sealedQuery);
            const offChange = sub.onChange((snapshot) => {
              if (!cancelled && snapshot.status === "live") {
                setRealtimeConnected(true);
              }
            });
            setRealtimeConnected(true);
            closeClient = () => {
              offChange();
              sub.unsubscribe();
              client.close();
            };
          }
        }
      } catch {
        // Ignore network errors in offline mode
      }
    }

    void connectNeonRealtimeAndStatus();
    return () => {
      cancelled = true;
      if (closeClient) closeClient();
    };
  }, [checkpointsDrawerOpen]);

  useEffect(() => {
    if (!checkpointsDrawerOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCheckpointsDrawerOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [checkpointsDrawerOpen, setCheckpointsDrawerOpen]);

  if (!checkpointsDrawerOpen) return null;

  const fx = config.fx_egp_per_sar ?? 13.0;
  const fmtSavings = (cp: DecisionCheckpoint) =>
    formatMoney(convertCurrency(cp.weekly_savings, cp.currency || "SAR", currency, fx), currency);

  const triggerBadge = (src: string) => {
    switch (src) {
      case "copilot":
        return {
          label: t.checkpointTriggerCopilot,
          cls: "border-cyan-500/40 bg-cyan-500/15 text-cyan-200",
          icon: <Sparkles className="h-3 w-3 text-cyan-400" />,
        };
      case "ctp_commit":
        return {
          label: t.checkpointTriggerCtp,
          cls: "border-amber-500/40 bg-amber-500/15 text-amber-200",
          icon: <Zap className="h-3 w-3 text-amber-400" />,
        };
      case "manual":
        return {
          label: t.checkpointTriggerManual,
          cls: "border-indigo-500/40 bg-indigo-500/15 text-indigo-200",
          icon: <History className="h-3 w-3 text-indigo-400" />,
        };
      default:
        return {
          label: t.checkpointTriggerWorkspace,
          cls: "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
          icon: <Database className="h-3 w-3 text-emerald-400" />,
        };
    }
  };

  const handleSaveNow = async () => {
    setSavingManual(true);
    try {
      await saveManualCheckpoint();
    } finally {
      setSavingManual(false);
    }
  };

  const handleRestore = async (cpId: string) => {
    setRestoringId(cpId);
    try {
      await restoreCheckpoint(cpId);
    } finally {
      setRestoringId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={() => setCheckpointsDrawerOpen(false)}
      />

      {/* Slide-Over Panel */}
      <div
        data-testid="decision-checkpoints-drawer"
        className="relative z-10 flex h-dvh w-full max-w-xl flex-col border-s border-slate-700/80 bg-[#0b1120] shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 py-3.5 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-500/15 text-cyan-300">
              <History className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="truncate text-sm font-bold text-white sm:text-base">
                  {t.checkpointsTitle}
                </h2>
                <span
                  data-testid="checkpoints-storage-badge"
                  className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] font-bold ${
                    storageBackend === "postgres"
                      ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                      : "border-cyan-500/40 bg-cyan-500/15 text-cyan-300"
                  }`}
                >
                  <Database className="h-2.5 w-2.5" />
                  <span>
                    {storageBackend === "postgres"
                      ? t.checkpointStoragePostgres
                      : t.checkpointStorageSqlite}
                  </span>
                </span>
              </div>
              <p className="truncate text-[11px] text-slate-400">
                {t.checkpointsSubtitle}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="btn-close-checkpoints-drawer"
            onClick={() => setCheckpointsDrawerOpen(false)}
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0 md:p-1.5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Action Sub-Header */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 bg-[#0f1629] px-4 py-3 sm:px-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">
              {checkpoints.length} {isAr ? "نقطة قرار محفوظة (بحد أقصى 25)" : "Saved Checkpoints (Max 25)"}
            </span>
            {realtimeConnected && (
              <span
                data-testid="neon-realtime-badge"
                className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-300"
              >
                <Radio className="h-2.5 w-2.5 text-emerald-400" />
                <span>Neon Realtime</span>
              </span>
            )}
            {neonFunctionReply && (
              <span
                data-testid="neon-function-badge"
                title={neonFunctionReply}
                className="inline-flex items-center gap-1 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-cyan-300"
              >
                <Zap className="h-2.5 w-2.5 text-cyan-400" />
                <span>Neon Fn: OK</span>
              </span>
            )}
          </div>
          <button
            type="button"
            data-testid="btn-save-manual-checkpoint"
            disabled={savingManual}
            onClick={() => void handleSaveNow()}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/15 px-3 py-1.5 text-xs font-bold text-cyan-200 transition hover:bg-cyan-500/25 disabled:opacity-50 md:min-h-0"
          >
            {savingManual ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            <span>{t.checkpointSaveNowBtn}</span>
          </button>
        </div>

        {/* Toast confirmation inside drawer */}
        {checkpointToast && (
          <div
            data-testid="checkpoint-toast-banner"
            className="mx-4 mt-3 flex items-center justify-between gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/15 px-3.5 py-2.5 text-xs font-semibold text-emerald-200 sm:mx-6"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>{checkpointToast}</span>
            </div>
            <button
              type="button"
              onClick={clearCheckpointToast}
              className="text-emerald-300 hover:text-white"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Checkpoint List */}
        <div className="flex-1 space-y-3 overflow-y-auto p-4 sm:p-6">
          {checkpoints.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400">
              {isAr
                ? "لا توجد نقاط قرار مسجلة بعد. اضغط حفظ نقطة قرار حالية أو طبق سيناريو في المساعد."
                : "No decision checkpoints recorded yet. Click '+ Save Current Checkpoint' or apply a Copilot scenario."}
            </div>
          ) : (
            checkpoints.map((cp) => {
              const badge = triggerBadge(cp.trigger_source);
              const isRestoring = restoringId === cp.id;
              return (
                <div
                  key={cp.id}
                  data-testid={`checkpoint-card-${cp.id}`}
                  className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 transition hover:border-slate-700"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-0.5 text-[11px] font-bold ${badge.cls}`}
                    >
                      {badge.icon}
                      <span>{badge.label}</span>
                    </span>
                    <span dir="ltr" className="inline-flex items-center gap-1 font-mono text-[11px] text-slate-400">
                      <Clock className="h-3 w-3 text-slate-500" />
                      <span>{new Date(cp.created_at).toLocaleString()}</span>
                    </span>
                  </div>

                  <div className="mt-2.5 text-xs font-bold text-white">
                    {isAr ? cp.title_ar || cp.title_en : cp.title_en}
                  </div>

                  {/* Snapshot Metrics Strip */}
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-3">
                    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
                      <span
                        dir="ltr"
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950/80 px-2 py-1 text-slate-200"
                      >
                        <ShieldAlert className="h-3 w-3 text-amber-400" />
                        <span>Risk: {cp.risk_score}/100</span>
                      </span>
                      <span
                        dir="ltr"
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950/80 px-2 py-1 text-emerald-300"
                      >
                        <TrendingUp className="h-3 w-3 text-emerald-400" />
                        <span>{fmtSavings(cp)}/wk</span>
                      </span>
                      <span
                        dir="ltr"
                        className="rounded-lg border border-slate-800 bg-slate-950/80 px-2 py-1 text-cyan-300"
                      >
                        OTIF {cp.otif_pct.toFixed(0)}%
                      </span>
                      {cp.orders_count ? (
                        <span className="rounded-lg border border-slate-800 bg-slate-950/80 px-2 py-1 text-slate-300">
                          {cp.orders_count} {isAr ? "أمر" : "orders"}
                        </span>
                      ) : null}
                    </div>

                    <button
                      type="button"
                      data-testid={`btn-restore-checkpoint-${cp.id}`}
                      disabled={restoringId !== null}
                      onClick={() => void handleRestore(cp.id)}
                      className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50 md:min-h-0"
                    >
                      {isRestoring ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RotateCcw className="h-3.5 w-3.5" />
                      )}
                      <span>{isRestoring ? t.checkpointRestoringBtn : t.checkpointRestoreBtn}</span>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="flex shrink-0 items-center justify-between border-t border-slate-800 bg-slate-950/90 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
          <span className="text-[11px] text-slate-400">
            {isAr
              ? "معزول لكل جلسة عميل • استرجاع فوري لكامل اللوحة"
              : "Sandbox-isolated • 1-click atomic rollback across Tabs 1–6"}
          </span>
          <button
            type="button"
            onClick={() => setCheckpointsDrawerOpen(false)}
            className="min-h-[44px] rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 md:min-h-0"
          >
            {isAr ? "إغلاق" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
