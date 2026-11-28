"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  Filter,
  Loader2,
  Table2,
} from "lucide-react";
import { downloadDiBlueprintArtifact } from "@/lib/api";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { DIBlueprintResponse, DIDMNDecisionTable } from "@/lib/types";

const DMN_TABLE_TITLES_AR: Record<string, { name: string; desc: string }> = {
  DMN_BARREL_PURGE_TRANSITION: {
    name: "جدول قواعد تنظيف الأسطوانة وتبديل الخامات والألوان",
    desc: "يحدد وضع التجهيز، دقائق التنظيف، ووزن هالك التنظيف (كجم) بين كل أمرين متتاليين على نفس المكبس.",
  },
  DMN_MOLD_PM_POLICY: {
    name: "جدول حوكمة الصيانة الوقائية للقوالب وعداد الضربات",
    desc: "يحكم وضع تنفيذ صيانة القالب الإلزامية (قفل ثابت عند س=0 مقابل نافذة عائمة ذاتية ضمن 75% من الأفق).",
  },
  DMN_FOOD_GRADE_REGRIND_SAFETY: {
    name: "جدول سلامة الخامات الغذائية والتصدير (منع الريجريند)",
    desc: "يحمي أوامر الأغذية والأدوية والتصدير ذات نسبة 0% ريجريند من أي تجاوزات في السيناريوهات.",
  },
  DMN_SHIFT_WORKFORCE_HEADCOUNT: {
    name: "جدول اشتقاق أعداد العمالة المساعدة للورديات",
    desc: "يشتق الاحتياج لكل وردية من المشرفين، مفتشي الجودة، مناولي الخامات، وفنيي القوالب.",
  },
};

const DMN_RULE_DESC_AR: Record<string, string> = {
  R_PURGE_1: "تبديل عائلة بوليمر غير متوافقة يتطلب تفكيك وتنظيف ثقيل للأسطوانة",
  R_PURGE_2: "الانتقال من لون داكن إلى فاتح يتطلب تنظيفاً عميقاً للحلزون والمجاري",
  R_PURGE_3: "التدرج من الفاتح إلى الداكن يتطلب شطفاً أمامياً سريعاً",
  R_PURGE_4: "نفس درجة اللون بين بولي أوليفينات متوافقة (PP/HDPE/LDPE) يتطلب شطفاً حرارياً خفيفاً",
  R_PURGE_5: "تطابق الخامة واللون يتطلب صفر تنظيف للأسطوانة",
  R_PM_1: "قالب عند أو فوق 100% من حد الضربات يُقفل فوراً للصيانة عند س=0 قبل أي تشغيل",
  R_PM_2: "تفعيل الصيانة الذاتية تحت 100% من حد الضربات يعوّم نافذة الصيانة ضمن 75% من الأفق",
  R_PM_3: "الوضع القياسي الثابت يقفل القالب للصيانة في بداية الأسبوع (س=0)",
  R_RG_1: "أوامر صفر ريجريند (الأغذية والأدوية والألبان) تلزم باستخدام 100% خام بكر",
  R_RG_2: "الأوامر الصناعية ذات السقف الموجب تسمح بخلط الريجريند المخرّز",
  R_WF_IDLE: "وردية خاملة بصفر مكابس نشطة وصفر أحداث قوالب",
  R_WF_HIGH_HEAVY_MOLD: "وردية عالية الحمل أو خامات مجففة (PET/ABS) مع 3+ تبديلات/صيانة قوالب",
  R_WF_HIGH_STD_MOLD: "وردية عالية الحمل أو خامات مجففة مع 1–2 تبديل/صيانة قوالب",
  R_WF_HIGH_NO_MOLD: "وردية عالية الحمل أو خامات مجففة بدون تبديل قوالب",
  R_WF_STD_HEAVY_MOLD: "وردية بحمل قياسي مع 3+ تبديلات/صيانة قوالب",
  R_WF_STD_MOLD: "وردية بحمل قياسي مع 1–2 تبديل/صيانة قوالب",
  R_WF_STD_NO_MOLD: "وردية بحمل قياسي بدون تبديل قوالب",
};

interface DMNInspectorViewProps {
  blueprint: DIBlueprintResponse;
}

export function DMNInspectorView({ blueprint }: DMNInspectorViewProps) {
  const { lang } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";

  const dmnLayer = blueprint.layers.layer_4_dmn_decision_tables;
  const tables: DIDMNDecisionTable[] = dmnLayer?.tables ?? [];
  const hitCountsMap = dmnLayer?.rule_hit_counts ?? {};

  const [showFiredOnly, setShowFiredOnly] = useState(false);
  const [collapsedTables, setCollapsedTables] = useState<Record<string, boolean>>({});
  const [downloadingXml, setDownloadingXml] = useState(false);

  const toggleTable = (tableId: string) => {
    setCollapsedTables((prev) => ({ ...prev, [tableId]: !prev[tableId] }));
  };

  const handleDownloadDmnXml = async () => {
    if (downloadingXml) return;
    setDownloadingXml(true);
    try {
      await downloadDiBlueprintArtifact("dmn_xml");
    } finally {
      setDownloadingXml(false);
    }
  };

  return (
    <div data-testid="di-tab-panel-dmn" className="space-y-4">
      {/* Top Action & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/75 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <Table2 className="h-4 w-4 text-purple-400" />
          <span className="text-xs font-bold text-white">
            {isAr
              ? `سجل جداول قرارات OMG DMN 1.3 (${tables.length} جداول مفعّلة)`
              : `OMG DMN 1.3 Decision Table Registry (${tables.length} Active Tables)`}
          </span>
          <span
            dir="ltr"
            className="rounded-md border border-purple-500/35 bg-purple-500/10 px-2 py-0.5 font-mono text-[10px] text-purple-200"
          >
            {dmnLayer?.registry_id ?? "DMN-MINI-DIOS-PLASTICS-V1"}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="toggle-dmn-fired-only"
            onClick={() => setShowFiredOnly((prev) => !prev)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
              showFiredOnly
                ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                : "border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-600 hover:text-white"
            }`}
          >
            <Filter className="h-3.5 w-3.5" />
            <span>{t.diShowFiredOnly}</span>
          </button>

          <button
            type="button"
            data-testid="btn-dmn-tab-download-xml"
            disabled={downloadingXml}
            onClick={() => void handleDownloadDmnXml()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/45 bg-purple-500/15 px-3 py-1.5 text-xs font-bold text-purple-200 transition hover:bg-purple-500/25 disabled:opacity-50"
          >
            {downloadingXml ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 text-purple-300" />
            )}
            <span>{t.diDownloadDmnBtn}</span>
          </button>
        </div>
      </div>

      {/* Expandable DMN Table Cards */}
      <div className="space-y-3.5">
        {tables.map((tbl) => {
          const isCollapsed = Boolean(collapsedTables[tbl.table_id]);
          const arMeta = DMN_TABLE_TITLES_AR[tbl.table_id];
          const rulesWithHits = tbl.rules.map((r) => {
            const count = r.hit_count ?? hitCountsMap[r.rule_id] ?? 0;
            const fired = r.fired !== undefined ? r.fired : count > 0;
            return { ...r, hit_count: count, fired };
          });
          const firedRulesCount = rulesWithHits.filter((r) => r.fired).length;
          const visibleRules = showFiredOnly
            ? rulesWithHits.filter((r) => r.fired)
            : rulesWithHits;

          return (
            <div
              key={tbl.table_id}
              data-testid={`dmn-table-card-${tbl.table_id}`}
              className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0a101f]"
            >
              {/* Table Header */}
              <button
                type="button"
                onClick={() => toggleTable(tbl.table_id)}
                className="flex w-full flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 bg-slate-900/80 px-4 py-3 text-start transition hover:bg-slate-900"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      dir="ltr"
                      className="rounded-md border border-cyan-500/35 bg-cyan-500/10 px-2 py-0.5 font-mono text-[11px] font-bold text-cyan-300"
                    >
                      {tbl.table_id}
                    </span>
                    <h3 className="text-xs font-bold text-white sm:text-sm">
                      {isAr ? arMeta?.name ?? tbl.name : tbl.name}
                    </h3>
                  </div>
                  {(tbl.description || arMeta?.desc) && (
                    <p className="mt-1 text-[11px] text-slate-400">
                      {isAr ? arMeta?.desc ?? tbl.description : tbl.description}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <span
                    dir="ltr"
                    className="rounded-lg border border-purple-500/40 bg-purple-500/15 px-2.5 py-1 font-mono text-[10px] font-bold text-purple-200"
                  >
                    {t.diHitPolicyLabel}: {tbl.hit_policy}
                  </span>
                  <span className="rounded-lg border border-emerald-500/35 bg-emerald-500/10 px-2.5 py-1 font-mono text-[10px] font-bold text-emerald-300">
                    {firedRulesCount}/{tbl.rules.length} {t.diRuleFiredBadge}
                  </span>
                  {isCollapsed ? (
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  ) : (
                    <ChevronUp className="h-4 w-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Horizontal-Scroll-Contained Rule Matrix */}
              {!isCollapsed && (
                <div className="w-full overflow-x-auto">
                  <table className="w-full min-w-[640px] border-collapse text-start text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-950/90 text-[11px] text-slate-400">
                        <th className="px-3 py-2 text-start font-semibold">Rule ID</th>
                        <th className="px-3 py-2 text-start font-semibold">
                          {isAr ? "حالة التفعيل" : "Trace Status"}
                        </th>
                        {tbl.inputs.map((inp) => (
                          <th
                            key={inp.input_id}
                            className="border-s border-slate-800/80 bg-cyan-950/20 px-3 py-2 text-start font-semibold text-cyan-200"
                          >
                            <div>{inp.label}</div>
                            <div dir="ltr" className="font-mono text-[10px] text-cyan-400/80">
                              IN: {inp.expression} ({inp.type_ref})
                            </div>
                          </th>
                        ))}
                        {tbl.outputs.map((out) => (
                          <th
                            key={out.output_id}
                            className="border-s border-slate-800/80 bg-emerald-950/20 px-3 py-2 text-start font-semibold text-emerald-200"
                          >
                            <div>{out.label}</div>
                            <div dir="ltr" className="font-mono text-[10px] text-emerald-400/80">
                              OUT: {out.name} ({out.type_ref})
                            </div>
                          </th>
                        ))}
                        <th className="border-s border-slate-800/80 px-3 py-2 text-start font-semibold">
                          {isAr ? "توصيف القاعدة" : "Policy Rationale"}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/70">
                      {visibleRules.map((rule) => {
                        const isFired = Boolean(rule.fired);
                        const hits = rule.hit_count ?? 0;
                        return (
                          <tr
                            key={rule.rule_id}
                            data-testid={`dmn-rule-row-${rule.rule_id}`}
                            className={
                              isFired
                                ? "bg-emerald-500/10 hover:bg-emerald-500/15"
                                : "bg-slate-950/40 text-slate-400 hover:bg-slate-900/60"
                            }
                          >
                            <td dir="ltr" className="px-3 py-2.5 font-mono text-[11px] font-bold text-white">
                              {rule.rule_id}
                            </td>
                            <td className="px-3 py-2.5">
                              {isFired ? (
                                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/50 bg-emerald-500/20 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-200">
                                  <CheckCircle2 className="h-3 w-3 text-emerald-300" />
                                  <span>{t.diRuleFiredBadge}</span>
                                  <span dir="ltr" className="rounded bg-emerald-400/25 px-1 text-emerald-100">
                                    {hits}×
                                  </span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                                  {t.diRuleStandbyBadge}
                                </span>
                              )}
                            </td>
                            {tbl.inputs.map((inp, idx) => (
                              <td
                                key={`${rule.rule_id}_in_${inp.input_id}`}
                                dir="ltr"
                                className="border-s border-slate-800/60 px-3 py-2.5 font-mono text-[11px] text-cyan-200"
                              >
                                {rule.input_entries[idx] ?? "-"}
                              </td>
                            ))}
                            {tbl.outputs.map((out) => {
                              const val = rule.output_entries[out.name];
                              return (
                                <td
                                  key={`${rule.rule_id}_out_${out.output_id}`}
                                  dir="ltr"
                                  className="border-s border-slate-800/60 px-3 py-2.5 font-mono text-[11px] font-bold text-emerald-300"
                                >
                                  {typeof val === "boolean"
                                    ? val
                                      ? "true"
                                      : "false"
                                    : String(val ?? "—")}
                                </td>
                              );
                            })}
                            <td className="border-s border-slate-800/60 px-3 py-2.5 text-[11px] text-slate-300">
                              {isAr
                                ? DMN_RULE_DESC_AR[rule.rule_id] ?? rule.description
                                : rule.description}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
