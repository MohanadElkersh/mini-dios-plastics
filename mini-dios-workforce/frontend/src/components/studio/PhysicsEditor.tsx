"use client";

import React from "react";
import { CalendarClock, Flame, Zap } from "lucide-react";
import { useApp } from "@/lib/store";
import type { Currency } from "@/lib/types";

interface SliderNumberFieldProps {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  step: number;
  testId: string;
  onChange: (val: number) => void;
}

function SliderNumberField({
  label,
  unit,
  value,
  min,
  max,
  step,
  testId,
  onChange,
}: SliderNumberFieldProps) {
  return (
    <div className="space-y-2 rounded-xl border border-slate-800/80 bg-slate-950/60 p-3">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-medium text-slate-300">{label}</span>
        <div dir="ltr" className="flex shrink-0 items-center gap-1.5">
          <input
            type="number"
            data-testid={testId}
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (!Number.isNaN(v)) onChange(v);
            }}
            className="min-h-[40px] w-20 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-end font-mono text-base font-bold text-cyan-300 md:min-h-0 md:text-xs"
          />
          <span className="w-14 text-[10px] text-slate-400">{unit}</span>
        </div>
      </div>
      <div className="py-1.5 md:py-0">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={Math.min(max, Math.max(min, value))}
          onChange={(e) => onChange(Number(e.target.value))}
          className="dios-slider w-full"
        />
      </div>
    </div>
  );
}

export function PhysicsEditor() {
  const { lang, currency, setCurrency, config, setConfig, updatePhysics } = useApp();
  const ph = config.physics;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Card 1: Purge & Changeover Physics */}
      <div className="space-y-3 rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/15 text-amber-300">
            <Flame className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              {lang === "ar" ? "فيزياء التنظيف والتبديل" : "Purge & Changeover Physics"}
            </h3>
            <p className="text-[11px] text-slate-400">
              {lang === "ar" ? "أزمنة وهالك تبديل الألوان والخامات" : "Color & incompatible resin purge rates"}
            </p>
          </div>
        </div>

        <SliderNumberField
          label={lang === "ar" ? "تنظيف فاتح ← غامق (دقائق)" : "Light → Dark Purge (mins)"}
          unit="min"
          value={ph.light_to_dark_purge_mins}
          min={0}
          max={180}
          step={1}
          testId="physics-ltd-mins"
          onChange={(v) => updatePhysics({ light_to_dark_purge_mins: Math.round(v) })}
        />
        <SliderNumberField
          label={lang === "ar" ? "هالك فاتح ← غامق (كجم)" : "Light → Dark Purge Scrap (kg)"}
          unit="kg"
          value={ph.light_to_dark_purge_kg}
          min={0}
          max={100}
          step={0.5}
          testId="physics-ltd-kg"
          onChange={(v) => updatePhysics({ light_to_dark_purge_kg: v })}
        />
        <SliderNumberField
          label={lang === "ar" ? "تنظيف غامق ← فاتح (دقائق)" : "Dark → Light Purge (mins)"}
          unit="min"
          value={ph.dark_to_light_purge_mins}
          min={0}
          max={480}
          step={5}
          testId="physics-dtl-mins"
          onChange={(v) => updatePhysics({ dark_to_light_purge_mins: Math.round(v) })}
        />
        <SliderNumberField
          label={lang === "ar" ? "هالك غامق ← فاتح (كجم)" : "Dark → Light Purge Scrap (kg)"}
          unit="kg"
          value={ph.dark_to_light_purge_kg}
          min={0}
          max={250}
          step={1}
          testId="physics-dtl-kg"
          onChange={(v) => updatePhysics({ dark_to_light_purge_kg: v })}
        />
        <SliderNumberField
          label={lang === "ar" ? "تبديل خامات غير متوافقة (دقائق)" : "Incompatible Resin Purge (mins)"}
          unit="min"
          value={ph.incompatible_resin_purge_mins}
          min={0}
          max={600}
          step={5}
          testId="physics-incompat-mins"
          onChange={(v) => updatePhysics({ incompatible_resin_purge_mins: Math.round(v) })}
        />
        <SliderNumberField
          label={lang === "ar" ? "هالك خامات غير متوافقة (كجم)" : "Incompatible Resin Scrap (kg)"}
          unit="kg"
          value={ph.incompatible_resin_purge_kg}
          min={0}
          max={300}
          step={1}
          testId="physics-incompat-kg"
          onChange={(v) => updatePhysics({ incompatible_resin_purge_kg: v })}
        />
      </div>

      {/* Card 2: Energy & Financial Rules */}
      <div className="space-y-3 rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-300">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              {lang === "ar" ? "الطاقة والقواعد المالية" : "Energy & Financial Rules"}
            </h3>
            <p className="text-[11px] text-slate-400">
              {lang === "ar" ? "تعريفة الكهرباء، الذروة، وتكلفة الاحتفاظ" : "Electricity tariffs, WIP holding & FX"}
            </p>
          </div>
        </div>

        <SliderNumberField
          label={lang === "ar" ? "تعريفة الكهرباء (SAR/kWh)" : "Electricity Tariff (SAR/kWh)"}
          unit="SAR/kWh"
          value={ph.energy_tariff_per_kwh}
          min={0.05}
          max={3.0}
          step={0.01}
          testId="physics-energy-tariff"
          onChange={(v) => updatePhysics({ energy_tariff_per_kwh: v })}
        />
        <SliderNumberField
          label={lang === "ar" ? "مضاعف تعريفة الذروة" : "Peak Tariff Multiplier"}
          unit="x"
          value={ph.peak_tariff_multiplier}
          min={1.0}
          max={3.0}
          step={0.05}
          testId="physics-peak-mult"
          onChange={(v) => updatePhysics({ peak_tariff_multiplier: v })}
        />
        <div className="grid grid-cols-2 gap-2.5 rounded-xl border border-slate-800/80 bg-slate-950/60 p-3 text-xs">
          <label className="space-y-1">
            <span className="text-slate-400">{lang === "ar" ? "بداية الذروة (ساعة)" : "Peak Start Hr"}</span>
            <input
              type="number"
              min={0}
              max={22}
              value={ph.peak_start_hr}
              onChange={(e) => {
                const s = Math.max(0, Math.min(22, Number(e.target.value)));
                updatePhysics({ peak_start_hr: s, peak_end_hr: Math.max(s + 1, ph.peak_end_hr) });
              }}
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 font-mono text-white"
            />
          </label>
          <label className="space-y-1">
            <span className="text-slate-400">{lang === "ar" ? "نهاية الذروة (ساعة)" : "Peak End Hr"}</span>
            <input
              type="number"
              min={ph.peak_start_hr + 1}
              max={24}
              value={ph.peak_end_hr}
              onChange={(e) => {
                const end = Math.max(ph.peak_start_hr + 1, Math.min(24, Number(e.target.value)));
                updatePhysics({ peak_end_hr: end });
              }}
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 font-mono text-white"
            />
          </label>
        </div>

        <SliderNumberField
          label={lang === "ar" ? "تكلفة احتفاظ المخزون (SAR/kg/يوم)" : "WIP Holding Cost (SAR/kg/day)"}
          unit="SAR/kg/d"
          value={ph.holding_cost_per_kg_per_day}
          min={0}
          max={5}
          step={0.01}
          testId="physics-holding-cost"
          onChange={(v) => updatePhysics({ holding_cost_per_kg_per_day: v })}
        />

        <div className="grid grid-cols-2 gap-2.5 rounded-xl border border-slate-800/80 bg-slate-950/60 p-3 text-xs">
          <div className="space-y-1">
            <span className="text-slate-400">{lang === "ar" ? "عملة العرض" : "Display Currency"}</span>
            <div className="grid grid-cols-2 gap-1 rounded-lg border border-slate-700 bg-slate-900 p-0.5">
              {(["SAR", "EGP"] as Currency[]).map((cur) => (
                <button
                  key={cur}
                  type="button"
                  onClick={() => setCurrency(cur)}
                  className={`rounded-md py-1 text-xs font-bold transition ${
                    currency === cur ? "bg-cyan-500 text-slate-950" : "text-slate-400 hover:text-white"
                  }`}
                >
                  {cur}
                </button>
              ))}
            </div>
          </div>
          <label className="space-y-1">
            <span className="text-slate-400">FX (EGP / SAR)</span>
            <input
              type="number"
              step="0.1"
              min={1}
              value={config.fx_egp_per_sar}
              onChange={(e) => setConfig((prev) => ({ ...prev, fx_egp_per_sar: Math.max(1, Number(e.target.value)) }))}
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 font-mono text-white"
            />
          </label>
        </div>
      </div>

      {/* Card 3: Calendar & Solver Engine */}
      <div className="space-y-3 rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-300">
            <CalendarClock className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              {lang === "ar" ? "التقويم ومحرك الحل" : "Calendar & Solver Engine"}
            </h3>
            <p className="text-[11px] text-slate-400">
              {lang === "ar" ? "أفق التخطيط وساعات رمضان وسقف الحل" : "Horizon bounds, Ramadan shifts & CP-SAT time cap"}
            </p>
          </div>
        </div>

        <SliderNumberField
          label={lang === "ar" ? "أفق التخطيط (ساعة)" : "Planning Horizon (hours)"}
          unit="hrs"
          value={ph.horizon_hrs}
          min={24}
          max={336}
          step={24}
          testId="physics-horizon-hrs"
          onChange={(v) => updatePhysics({ horizon_hrs: Math.round(v) })}
        />

        <SliderNumberField
          label={lang === "ar" ? "ساعات وردية رمضان" : "Ramadan Shift Hours"}
          unit="hrs/shift"
          value={ph.ramadan_shift_hours}
          min={4}
          max={12}
          step={1}
          testId="physics-ramadan-hrs"
          onChange={(v) => updatePhysics({ ramadan_shift_hours: Math.round(v) })}
        />

        <SliderNumberField
          label={lang === "ar" ? "سقف وقت حل CP-SAT (ثانية)" : "CP-SAT Max Solve Time (sec)"}
          unit="sec"
          value={ph.max_solve_seconds}
          min={1}
          max={30}
          step={0.5}
          testId="physics-max-solve-sec"
          onChange={(v) => updatePhysics({ max_solve_seconds: v })}
        />

        <SliderNumberField
          label={lang === "ar" ? "المصاريف الثابتة الأسبوعية (SAR)" : "Weekly Fixed Overhead (SAR)"}
          unit="SAR/wk"
          value={ph.weekly_fixed_overhead}
          min={0}
          max={100000}
          step={500}
          testId="physics-fixed-overhead"
          onChange={(v) => updatePhysics({ weekly_fixed_overhead: v })}
        />

        <SliderNumberField
          label={lang === "ar" ? "نسبة استرداد هالك التنظيف (%)" : "Scrap Regrind Recovery (%)"}
          unit="%"
          value={ph.scrap_regrind_recovery_pct}
          min={0}
          max={100}
          step={1}
          testId="physics-scrap-recovery"
          onChange={(v) => updatePhysics({ scrap_regrind_recovery_pct: v })}
        />

        <SliderNumberField
          label={lang === "ar" ? "أسابيع التشغيل السنوية" : "Annual Operating Weeks"}
          unit="wks/yr"
          value={ph.annual_operating_weeks}
          min={1}
          max={52}
          step={1}
          testId="physics-operating-weeks"
          onChange={(v) => updatePhysics({ annual_operating_weeks: Math.round(v) })}
        />

        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-[11px] leading-relaxed text-slate-400">
          {lang === "ar"
            ? "كل معاملات الفيزياء أعلاه تدخل مباشرة في قيود OR-Tools CP-SAT وخط الأساس FIFO وحسابات التوفير ومساعد العمليات وتصدير الإكسل."
            : "All physics parameters above flow directly into OR-Tools CP-SAT constraints, the Naive FIFO baseline, ROI KPI cards, Operations Copilot, and Excel exports."}
        </div>
      </div>
    </div>
  );
}
