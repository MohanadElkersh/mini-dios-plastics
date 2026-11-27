"use client";

import React, { useEffect, useState } from "react";
import {
  Check,
  Copy,
  ExternalLink,
  Loader2,
  MessageSquareShare,
  Users,
  X,
} from "lucide-react";
import { generateWhatsAppDispatchApi } from "@/lib/api";
import { COPY, DAY_NAMES_I18N, SHIFT_LABELS } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { Lang, WhatsAppDispatchResponse } from "@/lib/types";

export function WhatsAppDispatchModal() {
  const {
    lang,
    dataset,
    config,
    result,
    whatsappModalOpen,
    setWhatsappModalOpen,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";

  const [scope, setScope] = useState<"day_shift" | "full_week">("day_shift");
  const [day, setDay] = useState<number>(0);
  const [shift, setShift] = useState<string>("Morning");
  const [msgLang, setMsgLang] = useState<Lang>(lang);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [dispatchData, setDispatchData] = useState<WhatsAppDispatchResponse | null>(null);

  useEffect(() => {
    setMsgLang(lang);
  }, [lang]);

  useEffect(() => {
    if (!whatsappModalOpen || !result) return;
    let active = true;
    setBusy(true);
    void generateWhatsAppDispatchApi({
      scope,
      day,
      shift,
      language: msgLang,
      dataset,
      config,
      result,
    })
      .then((res) => {
        if (active) setDispatchData(res);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [whatsappModalOpen, scope, day, shift, msgLang, dataset, config, result]);

  useEffect(() => {
    if (!whatsappModalOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setWhatsappModalOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [whatsappModalOpen, setWhatsappModalOpen]);

  if (!whatsappModalOpen) return null;

  const shiftNames = result?.workforce?.shift_names ?? ["Morning", "Afternoon", "Night"];
  const dayNames = DAY_NAMES_I18N[lang];
  const shiftLabels = SHIFT_LABELS[lang];

  const handleCopy = async () => {
    if (!dispatchData?.message_text) return;
    try {
      await navigator.clipboard.writeText(dispatchData.message_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback textarea copy
      const ta = document.createElement("textarea");
      ta.value = dispatchData.message_text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div
        className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm"
        onClick={() => setWhatsappModalOpen(false)}
      />

      <div
        data-testid="whatsapp-dispatch-modal"
        className="relative z-10 flex max-h-[90dvh] w-full max-w-2xl flex-col overflow-hidden rounded-t-3xl border border-slate-700/80 bg-[#0b1120] shadow-2xl sm:rounded-2xl"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 py-3.5 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/40 bg-emerald-500/15 text-emerald-300">
              <MessageSquareShare className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-bold text-white sm:text-base">
                {t.whatsappTitle}
              </h2>
              <p className="truncate text-[11px] text-slate-400">
                {t.whatsappSubtitle}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="btn-close-whatsapp-modal"
            onClick={() => setWhatsappModalOpen(false)}
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0 md:p-1.5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          {/* Controls Bar: Scope + Day/Shift + Language */}
          <div className="grid gap-3 rounded-2xl border border-slate-800 bg-[#0f1629] p-3.5 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-[11px] text-slate-400">
                {isAr ? "نطاق الرسالة" : "Dispatch Scope"}
              </label>
              <select
                data-testid="select-whatsapp-scope"
                value={scope}
                onChange={(e) => setScope(e.target.value as "day_shift" | "full_week")}
                className="min-h-[42px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-1.5 text-base font-semibold text-white md:min-h-0 md:text-xs"
              >
                <option value="day_shift">{t.whatsappScopeDayShift}</option>
                <option value="full_week">{t.whatsappScopeWeek}</option>
              </select>
            </div>

            {scope === "day_shift" && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-1 block text-[11px] text-slate-400">
                    {isAr ? "اليوم" : "Day"}
                  </label>
                  <select
                    data-testid="select-whatsapp-day"
                    value={day}
                    onChange={(e) => setDay(Number(e.target.value))}
                    className="min-h-[42px] w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-base text-white md:min-h-0 md:text-xs"
                  >
                    {dayNames.map((dName, idx) => (
                      <option key={idx} value={idx}>
                        {dName}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-slate-400">
                    {isAr ? "الوردية" : "Shift"}
                  </label>
                  <select
                    data-testid="select-whatsapp-shift"
                    value={shift}
                    onChange={(e) => setShift(e.target.value)}
                    className="min-h-[42px] w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-base text-white md:min-h-0 md:text-xs"
                  >
                    {shiftNames.map((s) => (
                      <option key={s} value={s}>
                        {shiftLabels[s] ?? s}
                      </option>
                    ))}
                    <option value="ALL">{isAr ? "كل اليوم" : "All Day"}</option>
                  </select>
                </div>
              </div>
            )}

            <div>
              <label className="mb-1 block text-[11px] text-slate-400">
                {isAr ? "لغة الرسالة" : "Message Language"}
              </label>
              <div className="grid grid-cols-2 gap-1.5 rounded-xl border border-slate-700 bg-slate-950 p-1">
                <button
                  type="button"
                  data-testid="btn-whatsapp-lang-en"
                  onClick={() => setMsgLang("en")}
                  className={`rounded-lg py-1.5 text-xs font-bold transition ${
                    msgLang === "en" ? "bg-cyan-500 text-slate-950" : "text-slate-300 hover:text-white"
                  }`}
                >
                  English
                </button>
                <button
                  type="button"
                  data-testid="btn-whatsapp-lang-ar"
                  onClick={() => setMsgLang("ar")}
                  className={`rounded-lg py-1.5 text-xs font-bold transition ${
                    msgLang === "ar" ? "bg-cyan-500 text-slate-950" : "text-slate-300 hover:text-white"
                  }`}
                >
                  العربية
                </button>
              </div>
            </div>
          </div>

          {/* Preview Box */}
          <div className="rounded-2xl border border-emerald-500/30 bg-[#071318] p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-emerald-300">
              <span className="font-bold">{dispatchData?.window_label}</span>
              {dispatchData && (
                <span className="inline-flex items-center gap-1.5 font-mono">
                  <Users className="h-3.5 w-3.5" />
                  <span>
                    {dispatchData.jobs_included} {isAr ? "أوامر" : "runs"} • {dispatchData.crew_assigned_count}{" "}
                    {isAr ? "طاقم مكلف" : "crew assigned"}
                  </span>
                </span>
              )}
            </div>

            {busy && !dispatchData ? (
              <div className="flex items-center justify-center py-12 text-xs text-slate-400">
                <Loader2 className="me-2 h-4 w-4 animate-spin text-emerald-400" />
                <span>{isAr ? "جاري تجهيز رسالة الوردية..." : "Formatting deterministic shift dispatch..."}</span>
              </div>
            ) : (
              <pre
                dir={msgLang === "ar" ? "rtl" : "ltr"}
                data-testid="whatsapp-dispatch-preview-text"
                className="max-h-[320px] overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/90 p-3.5 font-sans text-xs leading-relaxed text-slate-100"
              >
                {dispatchData?.message_text || ""}
              </pre>
            )}
          </div>
        </div>

        {/* Sticky Footer: Copy for WhatsApp + Share via WhatsApp */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-slate-800 bg-slate-950/90 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
          <button
            type="button"
            onClick={() => setWhatsappModalOpen(false)}
            className="min-h-[44px] rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 md:min-h-0"
          >
            {isAr ? "إغلاق" : "Close"}
          </button>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="btn-whatsapp-copy"
              disabled={!dispatchData}
              onClick={() => void handleCopy()}
              className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/15 px-4 py-2 text-xs font-bold text-cyan-200 transition hover:bg-cyan-500/25 disabled:opacity-50 md:min-h-0"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4 text-cyan-400" />}
              <span>{copied ? t.whatsappCopiedBadge : t.whatsappCopyBtn}</span>
            </button>

            {dispatchData && (
              <a
                href={dispatchData.whatsapp_url}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="btn-whatsapp-share"
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 md:min-h-0"
              >
                <ExternalLink className="h-4 w-4" />
                <span>{t.whatsappShareBtn}</span>
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
