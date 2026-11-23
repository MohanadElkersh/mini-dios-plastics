"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Factory,
  Globe,
  KeyRound,
  Loader2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

const ALLOW_INSTANT_DEMO_ENV =
  (process.env.NEXT_PUBLIC_ALLOW_INSTANT_DEMO || "").toLowerCase() === "true";

export function LoginGate() {
  const { lang, setLang, auth, loginWithPasscode, loginInstantDemo } = useApp();
  const t = COPY[lang];

  const [passcode, setPasscode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const showGuidedDemo = ALLOW_INSTANT_DEMO_ENV || auth.instant_demo_enabled;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcode.trim() || submitting) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await loginWithPasscode(passcode.trim());
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : lang === "ar"
          ? "رمز الدخول غير صحيح."
          : "Invalid access code."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleInstantDemo = async () => {
    if (submitting) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await loginInstantDemo();
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : lang === "ar"
          ? "تعذر بدء العرض التفاعلي."
          : "Unable to start guided demo."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="login-gate"
      className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden bg-[#060a13] px-4 py-6 text-slate-100 sm:py-10"
    >
      {/* Subtle Industrial Grid & Radial Glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(34,211,238,0.12),transparent_55%),radial-gradient(ellipse_at_bottom_right,rgba(37,99,235,0.10),transparent_50%)]"
      />

      {/* Top-Right Language Switcher */}
      <div className="absolute end-4 top-4 z-10 sm:end-5 sm:top-5">
        <button
          type="button"
          data-testid="login-lang-toggle"
          onClick={() => setLang(lang === "en" ? "ar" : "en")}
          className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-700/80 bg-slate-900/90 px-3.5 py-2 text-xs font-semibold text-slate-200 shadow-lg transition hover:border-cyan-500/50 hover:text-white"
        >
          <Globe className="h-4 w-4 text-cyan-400" />
          <span>{lang === "en" ? "العربية" : "English"}</span>
        </button>
      </div>

      {/* Main Executive Card */}
      <div className="relative z-10 mt-8 w-full max-w-md rounded-3xl border border-slate-800/90 bg-[#0c1324]/95 p-5 shadow-2xl shadow-black/70 backdrop-blur sm:mt-0 sm:p-7">
        {/* Brand Header */}
        <div className="mb-5 flex flex-col items-center text-center sm:mb-6">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-lg shadow-cyan-500/25 sm:mb-4 sm:h-14 sm:w-14">
            <Factory className="h-6 w-6 sm:h-7 sm:w-7" />
          </div>
          <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-0.5 text-[11px] font-semibold text-cyan-300">
            <ShieldCheck className="h-3.5 w-3.5" />
            OR-Tools CP-SAT
          </span>
          <h1 className="text-lg font-bold tracking-tight text-white sm:text-xl">{t.loginTitle}</h1>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{t.loginSubtitle}</p>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div
            data-testid="login-error"
            className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 px-3.5 py-2.5 text-xs text-rose-200"
          >
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-300" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Passcode Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="dios-access-code"
              className="mb-1.5 block text-xs font-semibold text-slate-300"
            >
              {t.loginCodeLabel}
            </label>
            <div className="relative" dir="ltr">
              <KeyRound className="pointer-events-none absolute start-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                id="dios-access-code"
                data-testid="login-passcode-input"
                type="password"
                dir="ltr"
                autoComplete="current-password"
                value={passcode}
                onChange={(e) => setPasscode(e.target.value)}
                placeholder={t.loginCodePlaceholder}
                disabled={submitting}
                className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950/90 py-2.5 pe-3.5 ps-10 text-base text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 disabled:opacity-50 md:text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            data-testid="login-submit-btn"
            disabled={!passcode.trim() || submitting}
            className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:from-cyan-300 hover:to-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>{t.loginVerifying}</span>
              </>
            ) : (
              <>
                <span>{t.loginSubmitBtn}</span>
                <ArrowRight className="h-4 w-4 rtl:rotate-180" />
              </>
            )}
          </button>
        </form>

        {/* Optional Guided Demo Button */}
        {showGuidedDemo && (
          <div className="mt-3">
            <button
              type="button"
              data-testid="login-guided-demo-btn"
              disabled={submitting}
              onClick={() => void handleInstantDemo()}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-cyan-200 transition hover:border-cyan-500/50 hover:bg-cyan-500/10 disabled:opacity-40"
            >
              <Sparkles className="h-4 w-4 text-cyan-400" />
              <span>{t.loginGuidedDemoBtn}</span>
            </button>
          </div>
        )}

        {/* Industrial Trust Strip */}
        <div className="mt-5 border-t border-slate-800/80 pt-4 text-center sm:mt-6">
          <p className="text-[11px] font-semibold text-cyan-300/90">{t.loginTrustStrip}</p>
          <p className="mt-1 text-[10px] text-slate-500">{t.loginFooterNote}</p>
        </div>
      </div>
    </div>
  );
}
