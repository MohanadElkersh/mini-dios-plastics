"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { DIBlueprintResponse } from "@/lib/types";

const GATE_TITLES_AR: Record<string, string> = {
  "GATE-1-STRUCTURAL": "البوابة ١: السلامة الهيكلية وتكامل الروابط المرجعية",
  "GATE-2-CAPABILITY": "البوابة ٢: توافق قدرات الماكينات والقوالب والسخان الساخن",
  "GATE-3-POLICY": "البوابة ٣: سياسات التشغيل وأرصدة صوامع الخامات والصيانة",
};

const PRIMITIVE_META: {
  key: string;
  titleEn: string;
  titleAr: string;
  descEn: string;
  descAr: string;
  accent: string;
}[] = [
  {
    key: "ResourceNode",
    titleEn: "1. ResourceNode",
    titleAr: "١. عقد الموارد (ResourceNode)",
    descEn: "Primary Unary Presses, Secondary Exclusive Molds, and Consumable Resin Silo Pools",
    descAr: "ماكينات الحقن والنفخ الأحادية، القوالب الفيزيائية الحصرية، وصوامع الخامات القابلة للاستهلاك",
    accent: "border-cyan-500/35 bg-cyan-500/10 text-cyan-300",
  },
  {
    key: "ActivityNode",
    titleEn: "2. ActivityNode",
    titleAr: "٢. عقد الأنشطة والأوامر (ActivityNode)",
    descEn: "Schedulable Production Orders with Pre-Drying Release Floors, Due Dates & Virgin/Regrind Splits",
    descAr: "أوامر التشغيل القابلة للجدولة مع حد تجفيف الخام وموعد التسليم ونسب الخلط البكر/المعاد تدويره",
    accent: "border-emerald-500/35 bg-emerald-500/10 text-emerald-300",
  },
  {
    key: "TransitionMatrix",
    titleEn: "3. TransitionMatrix",
    titleAr: "٣. مصفوفة الانتقالات (TransitionMatrix)",
    descEn: "Asymmetric Sequence-Dependent Setup & Barrel Purge AddCircuit Arcs + Iftar Blackouts",
    descAr: "مسارات AddCircuit غير المتماثلة لتبديل القوالب وتنظيف الألوان مع حظر وقت الإفطار",
    accent: "border-purple-500/35 bg-purple-500/10 text-purple-300",
  },
  {
    key: "CumulativeEnvelope",
    titleEn: "4. CumulativeEnvelope",
    titleAr: "٤. المظاريف التراكمية (CumulativeEnvelope)",
    descEn: "CUMULATIVE_CAP: Silo Virgin/Regrind Caps, Peak Tariff Windows & Two-Way Shift Operator Envelopes",
    descAr: "سقف مخزون الصوامع، نوافذ تعريفة ذروة الكهرباء، ومظاريف توافر المشغلين ثنائية الاتجاه",
    accent: "border-amber-500/35 bg-amber-500/10 text-amber-300",
  },
  {
    key: "SynchronizationGroup",
    titleEn: "5. SynchronizationGroup",
    titleAr: "٥. مجموعات التزامن (SynchronizationGroup)",
    descEn: "Multi-SKU Export Container Release Barriers & Autonomous Floating / Static Mold PM Windows",
    descAr: "حواجز تجميع حاويات التصدير متعددة الأصناف ونوافذ الصيانة الوقائية الذاتية أو الثابتة للقوالب",
    accent: "border-indigo-500/35 bg-indigo-500/10 text-indigo-300",
  },
  {
    key: "ObjectiveTerm",
    titleEn: "6. ObjectiveTerm",
    titleAr: "٦. حدود دالة الهدف (ObjectiveTerm)",
    descEn: "Multi-Objective Weighted Coefficients in Integer Cents (Scrap, OTIF, Energy, Working Capital, Labor)",
    descAr: "أوزان دالة الهدف متعددة المعايير بالسنت الصحيح (الهالك، التسليم، الكهرباء، رأس المال العامل، العمالة)",
    accent: "border-teal-500/35 bg-teal-500/10 text-teal-300",
  },
];

interface ArchOntologyViewProps {
  blueprint: DIBlueprintResponse;
}

export function ArchOntologyView({ blueprint }: ArchOntologyViewProps) {
  const { lang } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";

  const ont = blueprint.layers.layer_1_business_ontology;
  const arch = blueprint.layers.layer_2_architecture_validation;
  const uem = blueprint.layers.uem_graph_6_primitives;
  const counts = uem?.primitive_counts ?? {};

  const [ontologyExpanded, setOntologyExpanded] = useState(true);

  const overallStatus = !arch?.ready
    ? "BLOCKED"
    : arch.warning_count > 0
    ? "VALID_WITH_WARNINGS"
    : "VALID";

  const statusBannerTone =
    overallStatus === "BLOCKED"
      ? "border-rose-500/45 bg-rose-500/15 text-rose-200"
      : overallStatus === "VALID_WITH_WARNINGS"
      ? "border-amber-500/45 bg-amber-500/15 text-amber-200"
      : "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";

  const statusTitle =
    overallStatus === "BLOCKED"
      ? t.diArchStatusBlocked
      : overallStatus === "VALID_WITH_WARNINGS"
      ? t.diArchStatusWarnings
      : t.diArchStatusValid;

  return (
    <div data-testid="di-tab-panel-arch-uem" className="space-y-5">
      {/* 1. Pre-Solve Architecture Validation Banner & 3 Gates */}
      <div
        data-testid="arch-validation-banner"
        className={`rounded-2xl border p-4 ${statusBannerTone}`}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            {overallStatus === "BLOCKED" ? (
              <ShieldAlert className="h-5 w-5 shrink-0 text-rose-400" />
            ) : overallStatus === "VALID_WITH_WARNINGS" ? (
              <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400" />
            ) : (
              <ShieldCheck className="h-5 w-5 shrink-0 text-emerald-400" />
            )}
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  dir="ltr"
                  className="rounded-md bg-slate-950/70 px-2 py-0.5 font-mono text-[11px] font-bold"
                >
                  {overallStatus}
                </span>
                <h3 className="text-xs font-bold text-white sm:text-sm">{statusTitle}</h3>
              </div>
            </div>
          </div>

          <div dir="ltr" className="flex items-center gap-2 font-mono text-xs">
            <span className="rounded-lg bg-slate-950/70 px-2.5 py-1 text-rose-300">
              Errors: {arch?.error_count ?? 0}
            </span>
            <span className="rounded-lg bg-slate-950/70 px-2.5 py-1 text-amber-300">
              Warnings: {arch?.warning_count ?? 0}
            </span>
          </div>
        </div>

        {/* 3 Gate Cards */}
        <div className="mt-3.5 grid gap-3 sm:grid-cols-3">
          {(arch?.gates ?? []).map((gate) => (
            <div
              key={gate.gate_id}
              data-testid={`arch-gate-${gate.gate_id}`}
              className="rounded-xl border border-slate-800/90 bg-slate-950/85 p-3 text-xs"
            >
              <div className="flex items-center justify-between gap-2">
                <span dir="ltr" className="font-mono text-[11px] font-bold text-cyan-300">
                  {gate.gate_id}
                </span>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-bold ${
                    gate.passed
                      ? "bg-emerald-500/20 text-emerald-300"
                      : "bg-rose-500/20 text-rose-300"
                  }`}
                >
                  <CheckCircle2 className="h-3 w-3" />
                  <span>{gate.passed ? "PASSED" : "BLOCKED"}</span>
                </span>
              </div>
              <div className="mt-1.5 font-semibold text-white">
                {isAr ? GATE_TITLES_AR[gate.gate_id] ?? gate.name : gate.name}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-[10px] text-slate-400">
                {gate.error_count} errors • {gate.warning_count} warnings
              </div>
            </div>
          ))}
        </div>

        {/* Warnings / Advisories List */}
        {arch?.violations && arch.violations.length > 0 && (
          <div className="mt-3 space-y-1.5 rounded-xl border border-slate-800/90 bg-slate-950/80 p-3">
            <div className="text-[11px] font-bold text-slate-300">
              {isAr
                ? "التنبيهات والملاحظات الاستباقية المكتشفة قبل الحل:"
                : "Pre-Solve Architecture Diagnostics & Advisories:"}
            </div>
            {arch.violations.map((v, idx) => (
              <div
                key={`${v.invariant_id}_${idx}`}
                className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300"
              >
                <span
                  dir="ltr"
                  className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                    v.severity === "error"
                      ? "bg-rose-500/20 text-rose-300"
                      : "bg-amber-500/20 text-amber-300"
                  }`}
                >
                  {v.invariant_id}
                </span>
                {v.entity_id && (
                  <span dir="ltr" className="font-mono text-[10px] text-cyan-300">
                    [{v.entity_id}]
                  </span>
                )}
                <span>{v.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. 6-Primitive UEM Graph Summary Cards */}
      <div className="rounded-2xl border border-slate-800 bg-[#0a101f] p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Boxes className="h-4 w-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-white sm:text-sm">{t.diUemPrimitivesTitle}</h3>
          </div>
          <span
            dir="ltr"
            className="rounded-md border border-emerald-500/35 bg-emerald-500/10 px-2.5 py-0.5 font-mono text-[11px] text-emerald-200"
          >
            {uem?.graph_id ?? "UEM-MINI-DIOS-PLASTICS-V1"} • Horizon {uem?.horizon_mins ?? 14400} mins
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PRIMITIVE_META.map((pm) => {
            const countVal = counts[pm.key] ?? 0;
            return (
              <div
                key={pm.key}
                data-testid={`uem-primitive-card-${pm.key}`}
                className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950/85 p-3.5"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-white">
                      {isAr ? pm.titleAr : pm.titleEn}
                    </span>
                    <span
                      dir="ltr"
                      className={`rounded-lg border px-2.5 py-0.5 font-mono text-sm font-bold ${pm.accent}`}
                    >
                      {countVal.toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
                    {isAr ? pm.descAr : pm.descEn}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Collapsible Formal Business Ontology Summary */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0a101f]">
        <button
          type="button"
          data-testid="toggle-ontology-summary"
          onClick={() => setOntologyExpanded((prev) => !prev)}
          className="flex w-full flex-wrap items-center justify-between gap-2 bg-slate-900/80 px-4 py-3 text-start transition hover:bg-slate-900"
        >
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white sm:text-sm">{t.diOntologySummaryTitle}</h3>
          </div>
          <div className="flex items-center gap-2">
            <span
              dir="ltr"
              className="rounded-md border border-cyan-500/35 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] text-cyan-200"
            >
              {ont?.counts.entity_types ?? 6} EntityTypes • {ont?.counts.entities ?? 0} Entities •{" "}
              {ont?.counts.relationships ?? 0} TypedRelationships • {ont?.counts.invariants ?? 6}{" "}
              Invariants
            </span>
            {ontologyExpanded ? (
              <ChevronUp className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            )}
          </div>
        </button>

        {ontologyExpanded && (
          <div className="grid gap-4 border-t border-slate-800 p-4 lg:grid-cols-2">
            {/* Entity Types */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-cyan-300">
                {isAr ? "فئات الكيانات الرسمية (EntityTypes)" : "Formal Ontology EntityTypes"}
              </div>
              <div className="space-y-2">
                {(ont?.entity_types ?? []).map((et) => (
                  <div
                    key={et.type_id}
                    className="rounded-xl border border-slate-800 bg-slate-950/80 p-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span dir="ltr" className="font-mono font-bold text-white">
                        {et.type_id}
                      </span>
                      <span
                        dir="ltr"
                        className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300"
                      >
                        {et.ontology_role}
                      </span>
                    </div>
                    <div className="mt-1 text-[11px] text-slate-300">{et.label}</div>
                    <div dir="ltr" className="mt-1 font-mono text-[10px] text-slate-500">
                      Required: {et.required_attributes.join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Semantic Invariants */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-emerald-300">
                {isAr
                  ? "الثوابت الدلالية الصارمة (SemanticInvariants)"
                  : "Formal Semantic Invariants (INV-HC1..HC6)"}
              </div>
              <div className="space-y-2">
                {(ont?.invariants ?? []).map((inv) => (
                  <div
                    key={inv.invariant_id}
                    className="rounded-xl border border-slate-800 bg-slate-950/80 p-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span dir="ltr" className="font-mono font-bold text-emerald-300">
                        {inv.invariant_id}
                      </span>
                      <span
                        dir="ltr"
                        className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono text-[10px] text-slate-300"
                      >
                        {inv.category}
                      </span>
                    </div>
                    <div className="mt-1 text-[11px] font-semibold text-white">{inv.name}</div>
                    <div
                      dir="ltr"
                      className="mt-1 overflow-x-auto rounded bg-slate-900/90 px-2 py-1 font-mono text-[10px] text-cyan-200"
                    >
                      {inv.expression_summary}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
