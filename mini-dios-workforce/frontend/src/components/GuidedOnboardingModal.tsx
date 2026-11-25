"use client";

import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Boxes,
  CheckCircle2,
  ClipboardCheck,
  Factory,
  Loader2,
  Palette,
  ShieldCheck,
  Sparkles,
  Users,
  Wrench,
  X,
} from "lucide-react";
import { generateGuidedWorkspaceApi } from "@/lib/api";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { GuidedSetupRequest, ReadinessChecklistItem } from "@/lib/types";

export function GuidedOnboardingModal() {
  const {
    lang,
    currency,
    onboardingModalOpen,
    setOnboardingModalOpen,
    applyGuidedWorkspace,
    createNewBlankPlant,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";

  const [step, setStep] = useState<number>(1);
  const [busy, setBusy] = useState(false);
  const [checklist, setChecklist] = useState<ReadinessChecklistItem[] | null>(null);
  const [form, setForm] = useState<GuidedSetupRequest>({
    plant_name: "6th of October & Riyadh Polymer Plant",
    primary_process: "Hybrid",
    operating_model: "Hybrid",
    currency,
    press_count: 6,
    tonnage_tier: "mixed",
    backup_press_enabled: true,
    backup_speed_factor: 0.92,
    standard_pm_duration_hrs: 5,
    light_to_dark_priority: "strict",
    min_batch_run_hrs: 8,
    max_regrind_allowance_pct: 20,
    shift_pattern: "3x8h",
    avoid_peak_tariff_hrs: true,
    max_weekly_hours_cap: 48,
    container_sync_enabled: true,
    fg_storage_capacity_tons: 22,
  });

  useEffect(() => {
    setForm((prev) => ({ ...prev, currency }));
  }, [currency]);

  useEffect(() => {
    if (!onboardingModalOpen) {
      setStep(1);
      setChecklist(null);
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOnboardingModalOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onboardingModalOpen, setOnboardingModalOpen]);

  if (!onboardingModalOpen) return null;

  const handleGenerate = async () => {
    setBusy(true);
    try {
      const res = await generateGuidedWorkspaceApi(form);
      setChecklist(res.readiness_checklist);
      applyGuidedWorkspace(res);
    } finally {
      setBusy(false);
    }
  };

  const stepTitles = isAr
    ? [
        "١. العملية ونموذج التشغيل",
        "٢. المكابس والماكينات البديلة",
        "٣. تسلسل الألوان والريجريند",
        "٤. الورديات وتعريفة الكهرباء",
        "٥. الحاويات والمخزن وقائمة الجاهزية",
      ]
    : [
        "1. Process & Operating Model",
        "2. Presses & Backup Logic",
        "3. Color Purge & Batch Rules",
        "4. Workforce & Tariff Rules",
        "5. Export & Warehouse Rules",
      ];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div
        className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm"
        onClick={() => setOnboardingModalOpen(false)}
      />

      <div
        data-testid="guided-onboarding-modal"
        className="relative z-10 flex max-h-[92dvh] w-full max-w-3xl flex-col overflow-hidden rounded-t-3xl border border-slate-700/80 bg-[#0b1120] shadow-2xl sm:rounded-2xl"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 py-3.5 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-500/40 bg-gradient-to-br from-cyan-500/20 to-indigo-500/20 text-cyan-300">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-bold text-white sm:text-base">
                {t.guidedSetupTitle}
              </h2>
              <p className="truncate text-[11px] text-slate-400">{t.guidedSetupSubtitle}</p>
            </div>
          </div>
          <button
            type="button"
            data-testid="btn-close-onboarding-modal"
            onClick={() => setOnboardingModalOpen(false)}
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0 md:p-1.5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 5-Step Progress Strip */}
        <div className="no-scrollbar flex shrink-0 items-center gap-1.5 overflow-x-auto border-b border-slate-800/80 bg-slate-950/50 px-4 py-2.5 sm:px-6">
          {stepTitles.map((title, idx) => {
            const sNum = idx + 1;
            const active = step === sNum;
            const done = step > sNum || checklist !== null;
            return (
              <button
                key={sNum}
                type="button"
                data-testid={`onboarding-step-tab-${sNum}`}
                onClick={() => setStep(sNum)}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition ${
                  active
                    ? "bg-cyan-500 text-slate-950 font-bold"
                    : done
                      ? "border border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      : "bg-slate-900 text-slate-400 hover:text-slate-200"
                }`}
              >
                {done && !active && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                <span>{title}</span>
              </button>
            );
          })}
        </div>

        {/* Body */}
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          {/* Step 1: Process & Operating Model */}
          {step === 1 && (
            <div data-testid="onboarding-step-1" className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Factory className="h-4 w-4 text-cyan-400" />
                <span>{stepTitles[0]}</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "اسم المصنع / مساحة العمل" : "Factory / Plant Workspace Name"}
                  </label>
                  <input
                    type="text"
                    data-testid="input-onboarding-plant-name"
                    value={form.plant_name}
                    onChange={(e) => setForm({ ...form, plant_name: e.target.value })}
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "عملية التشكيل الأساسية" : "Primary Molding Process"}
                  </label>
                  <select
                    data-testid="select-onboarding-process"
                    value={form.primary_process}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        primary_process: e.target.value as GuidedSetupRequest["primary_process"],
                      })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-base text-white md:min-h-0 md:text-xs"
                  >
                    <option value="Hybrid">
                      {isAr ? "مختلط (حقن بلاستيك + نفخ عبوات)" : "Hybrid (Injection + Blow Molding)"}
                    </option>
                    <option value="Injection">
                      {isAr ? "حقن بلاستيك (Injection Molding)" : "Plastic Injection Molding"}
                    </option>
                    <option value="BlowMolding">
                      {isAr ? "نفخ عبوات وجراكن (Blow Molding)" : "Blow Molding (Bottles & Jerrycans)"}
                    </option>
                    <option value="Extrusion">
                      {isAr ? "بثق مواسير وقطاعات (Extrusion)" : "Extrusion Lines"}
                    </option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "نموذج تلبية الطلبات" : "Commercial Operating Model"}
                  </label>
                  <select
                    value={form.operating_model}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        operating_model: e.target.value as GuidedSetupRequest["operating_model"],
                      })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-base text-white md:min-h-0 md:text-xs"
                  >
                    <option value="Hybrid">
                      {isAr ? "هجين (طلبيات عملاء MTO + تخزين MTS)" : "Hybrid (Make-to-Order + Make-to-Stock)"}
                    </option>
                    <option value="MTO">
                      {isAr ? "حسب طلب العميل والتصدير (MTO)" : "Make-to-Order (MTO / Export Deadlines)"}
                    </option>
                    <option value="MTS">
                      {isAr ? "إنتاج للمخزن وتجديد الأرصدة (MTS)" : "Make-to-Stock (MTS / Replenishment)"}
                    </option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "العملة المالية للمصنع" : "Plant Reporting Currency"}
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {(["EGP", "SAR"] as const).map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setForm({ ...form, currency: c })}
                        className={`min-h-[44px] rounded-xl border px-3 py-2 text-xs font-bold transition md:min-h-0 ${
                          form.currency === c
                            ? "border-cyan-400 bg-cyan-500/20 text-cyan-200"
                            : "border-slate-700 bg-slate-900 text-slate-400"
                        }`}
                      >
                        {c === "EGP" ? "EGP (جنيه مصري)" : "SAR (ريال سعودي)"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Presses & Backup Logic */}
          {step === 2 && (
            <div data-testid="onboarding-step-2" className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Wrench className="h-4 w-4 text-amber-400" />
                <span>{stepTitles[1]}</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "عدد خطوط/ماكينات الإنتاج النشطة" : "Number of Active Presses / Lines"}
                  </label>
                  <input
                    type="number"
                    min={2}
                    max={12}
                    value={form.press_count}
                    onChange={(e) =>
                      setForm({ ...form, press_count: Math.max(2, Math.min(12, Number(e.target.value) || 6)) })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-base text-white md:min-h-0 md:text-xs"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "فئات قوة الغلق (التوناج)" : "Press Clamping Tonnage Tiers"}
                  </label>
                  <select
                    value={form.tonnage_tier}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        tonnage_tier: e.target.value as GuidedSetupRequest["tonnage_tier"],
                      })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-base text-white md:min-h-0 md:text-xs"
                  >
                    <option value="mixed">{isAr ? "متنوع (150T إلى 650T)" : "Mixed Fleet (150T – 650T)"}</option>
                    <option value="small_med">
                      {isAr ? "صغير ومتوسط للعبوات والأغطية (150T–350T)" : "Small/Medium Packaging (150T – 350T)"}
                    </option>
                    <option value="heavy">
                      {isAr ? "ثقيل للصناديق والسيارات (450T–800T)" : "Heavy Industrial & Crates (450T – 800T)"}
                    </option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "تفعيل الماكينات البديلة عند الأعطال" : "Backup Press Crossover Logic"}
                  </label>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, backup_press_enabled: !form.backup_press_enabled })}
                    className={`flex min-h-[44px] w-full items-center justify-between rounded-xl border px-3.5 py-2 text-xs font-bold transition md:min-h-0 ${
                      form.backup_press_enabled
                        ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-200"
                        : "border-slate-700 bg-slate-900 text-slate-400"
                    }`}
                  >
                    <span>
                      {form.backup_press_enabled
                        ? isAr
                          ? "مفعّل: تحويل القالب تلقائياً لماكينة بديلة متوافقة"
                          : "Enabled: Auto-reroute mold to backup press on breakdown"
                        : isAr
                          ? "معطّل: كل قالب مقيد بماكينة واحدة فقط"
                          : "Disabled: Strict single-press per mold"}
                    </span>
                    <span>{form.backup_press_enabled ? "ON" : "OFF"}</span>
                  </button>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "مدة الصيانة الوقائية القياسية للقالب (ساعات)" : "Standard Mold PM Window (Hours)"}
                  </label>
                  <input
                    type="number"
                    min={2}
                    max={24}
                    value={form.standard_pm_duration_hrs}
                    onChange={(e) =>
                      setForm({ ...form, standard_pm_duration_hrs: Math.max(2, Number(e.target.value) || 5) })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-base text-white md:min-h-0 md:text-xs"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Color/Resin Purge & Batch Rules */}
          {step === 3 && (
            <div data-testid="onboarding-step-3" className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Palette className="h-4 w-4 text-cyan-400" />
                <span>{stepTitles[2]}</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "أولوية تسلسل الألوان (فاتح ← غامق)" : "Light-to-Dark Color Sequencing Priority"}
                  </label>
                  <select
                    value={form.light_to_dark_priority}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        light_to_dark_priority: e.target.value as GuidedSetupRequest["light_to_dark_priority"],
                      })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-base text-white md:min-h-0 md:text-xs"
                  >
                    <option value="strict">
                      {isAr
                        ? "أولوية قصوى لخفض هالك التنظيف (شفاف ← أبيض ← أصفر ← أزرق ← أحمر ← أسود)"
                        : "Strict Light → Dark Batching (Minimize Barrel Purge Waste)"}
                    </option>
                    <option value="balanced">
                      {isAr ? "متوازن مع مواعيد التسليم" : "Balanced with Urgent Delivery Deadlines"}
                    </option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "سقف خلط الريجريند للمنتجات غير الغذائية (%)" : "Non-Food Regrind Allowance (%)"}
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={40}
                    step={5}
                    value={form.max_regrind_allowance_pct}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        max_regrind_allowance_pct: Math.max(0, Math.min(40, Number(e.target.value) || 0)),
                      })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-base text-white md:min-h-0 md:text-xs"
                  />
                  <p className="mt-1 text-[11px] text-emerald-300">
                    {isAr
                      ? "ملاحظة: أوامر الأغذية والأدوية تظل محمية بنسبة 0% ريجريند دائماً."
                      : "Note: Food & pharma orders remain strictly locked at 0% regrind (HC5)."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Workforce & Tariff Rules */}
          {step === 4 && (
            <div data-testid="onboarding-step-4" className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Users className="h-4 w-4 text-indigo-400" />
                <span>{stepTitles[3]}</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "نظام الورديات اليومي" : "Factory Shift Schedule Pattern"}
                  </label>
                  <select
                    value={form.shift_pattern}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        shift_pattern: e.target.value as GuidedSetupRequest["shift_pattern"],
                      })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-base text-white md:min-h-0 md:text-xs"
                  >
                    <option value="3x8h">
                      {isAr ? "٣ ورديات × ٨ ساعات (صباحية / مسائية / ليلية)" : "3 × 8-Hour Shifts (Morning / Afternoon / Night)"}
                    </option>
                    <option value="2x12h">
                      {isAr ? "٢ وردية × ١٢ ساعة" : "2 × 12-Hour Rotational Shifts"}
                    </option>
                    <option value="ramadan_4x6h">
                      {isAr ? "ورديات رمضان (٤ × ٦ ساعات مع حظر تبديل الإفطار)" : "Ramadan Mode (4 × 6-Hour Shifts + Iftar Blackout)"}
                    </option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr ? "تجنب شريحة ذروة الكهرباء (13:00–17:00)" : "Peak Electricity Tariff Avoidance (13:00–17:00)"}
                  </label>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, avoid_peak_tariff_hrs: !form.avoid_peak_tariff_hrs })}
                    className={`flex min-h-[44px] w-full items-center justify-between rounded-xl border px-3.5 py-2 text-xs font-bold transition md:min-h-0 ${
                      form.avoid_peak_tariff_hrs
                        ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-200"
                        : "border-slate-700 bg-slate-900 text-slate-400"
                    }`}
                  >
                    <span>
                      {form.avoid_peak_tariff_hrs
                        ? isAr
                          ? "مفعّل: إزاحة الأحمال الثقيلة خارج ساعات الذروة"
                          : "Enabled: Shift heavy kW molding away from peak hours"
                        : isAr
                          ? "معطّل: تعريفة كهرباء موحدة"
                          : "Disabled: Flat electricity tariff"}
                    </span>
                    <span>{form.avoid_peak_tariff_hrs ? "ON" : "OFF"}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 5: Export & Warehouse Rules + "Current Specs Only" Readiness Checklist */}
          {step === 5 && (
            <div data-testid="onboarding-step-5" className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Boxes className="h-4 w-4 text-emerald-400" />
                <span>{stepTitles[4]}</span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr
                      ? "مزامنة حاويات التصدير متعددة الأصناف"
                      : "Multi-SKU Export Container Consolidation"}
                  </label>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, container_sync_enabled: !form.container_sync_enabled })}
                    className={`flex min-h-[44px] w-full items-center justify-between rounded-xl border px-3.5 py-2 text-xs font-bold transition md:min-h-0 ${
                      form.container_sync_enabled
                        ? "border-cyan-500/50 bg-cyan-500/15 text-cyan-200"
                        : "border-slate-700 bg-slate-900 text-slate-400"
                    }`}
                  >
                    <span>
                      {form.container_sync_enabled
                        ? isAr
                          ? "مفعّل: مزامنة أصناف الحاوية لمنع تجميد رأس المال"
                          : "Enabled: Synchronize container SKUs to cut WIP lockup"
                        : isAr
                          ? "معطّل: شحن كل صنف منفرداً"
                          : "Disabled: Independent single-SKU shipping"}
                    </span>
                    <span>{form.container_sync_enabled ? "ON" : "OFF"}</span>
                  </button>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">
                    {isAr
                      ? "سعة مخزن المنتج التام القصوى (طن)"
                      : "Finished-Goods Warehouse Storage Ceiling (Tons)"}
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={500}
                    value={form.fg_storage_capacity_tons}
                    onChange={(e) =>
                      setForm({ ...form, fg_storage_capacity_tons: Math.max(5, Number(e.target.value) || 22) })
                    }
                    className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-base text-white md:min-h-0 md:text-xs"
                  />
                </div>
              </div>

              {/* "Current Specs Only" Readiness Checklist */}
              <div
                data-testid="onboarding-readiness-checklist"
                className="rounded-2xl border border-emerald-500/35 bg-emerald-500/10 p-4 space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-200">
                    <ClipboardCheck className="h-4 w-4 text-emerald-400" />
                    <span>
                      {isAr
                        ? "قائمة جاهزية التشغيل السريع (المواصفات الحالية فقط — صفر سجلات ERP تاريخية!)"
                        : '"Current Specs Only" 3-Hour Onboarding Checklist (Zero Historical ERP Data Needed)'}
                    </span>
                  </div>
                  <span className="rounded-full border border-emerald-400/40 bg-emerald-500/20 px-2.5 py-0.5 text-[10px] font-bold text-emerald-200">
                    0 ERP HISTORY REQUIRED
                  </span>
                </div>

                <div className="grid gap-2 sm:grid-cols-2">
                  {(
                    checklist ?? [
                      {
                        item_id: "c1",
                        title_en: `1. Press Fleet & kW Ratings (${form.press_count} Active Lines)`,
                        title_ar: `١. قائمة الماكينات واستهلاك الكهرباء (${form.press_count} خطوط)`,
                        detail_en: "Clamping tonnage, process type, and current kWh/hr rating. Zero historical downtime logs needed.",
                        detail_ar: "قوة الغلق بالطن ونوع الماكينة واستهلاك الكهرباء الحالي فقط.",
                        erp_history_needed: false,
                        status: "ready",
                      },
                      {
                        item_id: "c2",
                        title_en: "2. Active Mold Cavities & Cycle Time Seconds",
                        title_ar: "٢. عدد فجوات القوالب النشطة وزمن الدورة بالثواني",
                        detail_en: `Active cavities, cycle time, and current shot count (${form.standard_pm_duration_hrs}h PM window).`,
                        detail_ar: `عدد الفجوات النشطة حالياً وزمن الدورة وعداد الضربات الحالي.`,
                        erp_history_needed: false,
                        status: "ready",
                      },
                      {
                        item_id: "c3",
                        title_en: `3. Part Weights, Colors & Regrind Rule (${form.max_regrind_allowance_pct}% Max)`,
                        title_ar: `٣. وزن القطعة بالجرام واللون ونسبة الريجريند (${form.max_regrind_allowance_pct}%)`,
                        detail_en: "Net part weight (g), resin grade, and color rank. Zero past ERP sales history needed.",
                        detail_ar: "وزن القطعة الصافي ونوع الخامة واللون دون أي جداول مبيعات تاريخية.",
                        erp_history_needed: false,
                        status: "ready",
                      },
                      {
                        item_id: "c4",
                        title_en: `4. Morning Silo Stock & Warehouse Ceiling (${form.fg_storage_capacity_tons}t)`,
                        title_ar: `٤. رصيد الخام الصباحي وسقف المخزن (${form.fg_storage_capacity_tons} طن)`,
                        detail_en: "Today's virgin/regrind kg on the floor and this week's open orders & export containers.",
                        detail_ar: "رصيد الخام البكر والمعاد تدويره صباح اليوم وأوامر الأسبوع المفتوحة.",
                        erp_history_needed: false,
                        status: "ready",
                      },
                    ]
                  ).map((item) => (
                    <div
                      key={item.item_id}
                      className="rounded-xl border border-slate-800/90 bg-slate-950/80 p-3 text-xs"
                    >
                      <div className="flex items-center gap-1.5 font-bold text-white">
                        <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                        <span>{isAr ? item.title_ar : item.title_en}</span>
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
                        {isAr ? item.detail_ar : item.detail_en}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-slate-800 bg-slate-950/90 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
          <button
            type="button"
            data-testid="btn-start-empty-blank-plant"
            onClick={() => {
              createNewBlankPlant();
              setOnboardingModalOpen(false);
            }}
            className="text-[11px] font-semibold text-slate-400 underline hover:text-slate-200"
          >
            {isAr ? "أو البدء بمصنع فارغ تماماً (0 ماكينات)" : "Or start with an empty 0-press blank canvas"}
          </button>

          <div className="flex items-center gap-2">
            {step > 1 && (
              <button
                type="button"
                data-testid="btn-onboarding-prev"
                onClick={() => setStep((s) => Math.max(1, s - 1))}
                className="inline-flex min-h-[44px] items-center gap-1 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 md:min-h-0"
              >
                <ArrowLeft className="h-3.5 w-3.5 rtl:rotate-180" />
                <span>{isAr ? "السابق" : "Back"}</span>
              </button>
            )}

            {step < 5 ? (
              <button
                type="button"
                data-testid="btn-onboarding-next"
                onClick={() => setStep((s) => Math.min(5, s + 1))}
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 md:min-h-0"
              >
                <span>{isAr ? "الخطوة التالية" : "Next Step"}</span>
                <ArrowRight className="h-3.5 w-3.5 rtl:rotate-180" />
              </button>
            ) : (
              <button
                type="button"
                data-testid="btn-onboarding-generate"
                disabled={busy}
                onClick={async () => {
                  await handleGenerate();
                  setOnboardingModalOpen(false);
                }}
                className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 hover:bg-emerald-400 disabled:opacity-50 md:min-h-0"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                <span>
                  {isAr
                    ? "توليد مساحة عمل المصنع وتشغيل CP-SAT الآن"
                    : "Generate & Solve Plant Workspace Now"}
                </span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
