"use client";

import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  Clock,
  Cpu,
  Download,
  GitCommit,
  GitFork,
  Loader2,
  Play,
  ShieldCheck,
  Table2,
  Workflow,
} from "lucide-react";
import { downloadDiBlueprintArtifact } from "@/lib/api";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { DIBlueprintResponse, DIBPMNFlowNode } from "@/lib/types";

const BPMN_NODE_NAMES_AR: Record<string, string> = {
  Start_Weekly_MPS_Cycle: "بدء دورة جدولة المصنع والورديات الأسبوعية",
  Task_Architecture_Validation_Gate: "بوابة الفحص المسبق للأنطولوجيا ومعمارية الأعمال",
  Task_DMN_FoodGrade_Regrind_Policy: "تقييم سياسة الريجريند الغذائي وسقف صوامع الخامات",
  Task_DMN_Mold_PM_Gate: "تقييم سياسة الصيانة الوقائية للقوالب وعداد الضربات",
  Gw_Mold_PM_Mode: "بوابة: نافذة صيانة ذاتية عائمة أم قفل ثابت عند س=0؟",
  Task_DMN_Sequence_Purge_Matrix: "بناء مصفوفة مسارات تنظيف الألوان والخامات (AddCircuit)",
  Task_Press_Execution_Schedule: "ترجمة وحل مخطط UEM السداسي للمكابس في OR-Tools CP-SAT",
  Timer_Export_Port_Cutoff: "مؤقت إغلاق ميناء التصدير وأفق 168 ساعة",
  Gw_Container_And_Workforce_Fork: "بوابة متوازية: ربط حاويات التصدير وعمالة الورديات (5 أدوار)",
  Task_Export_Container_Barrier_Sync: "مزامنة حواجز إطلاق حاويات التصدير متعددة الأصناف",
  Task_DMN_Shift_Workforce_Demand: "اشتقاق وحل مظاريف عمالة الورديات للأدوار الخمسة",
  Gw_TwoWay_Labor_Feedback: "بوابة التغذية الراجعة المزدوجة للعمالة (بحد أقصى دورة واحدة ≤ 2 ثانية)",
  Task_PostSolve_UEM_Verification: "التحقق الرياضي المستقل بعد الحل (uem_verify.py + HC1-HC6)",
  End_Verified_Plant_Schedule: "إصدار الجدول الموثق ومطابقة الأرباح والمخطط السببي للقرار",
};

type LaneId = "lane_validation" | "lane_rules" | "lane_execution" | "lane_verification";

function classifyBpmnLane(node: DIBPMNFlowNode): LaneId {
  if (
    node.node_id === "Start_Weekly_MPS_Cycle" ||
    node.node_id === "Task_Architecture_Validation_Gate"
  ) {
    return "lane_validation";
  }
  if (
    node.kind === "businessRuleTask" ||
    node.node_id === "Gw_Mold_PM_Mode"
  ) {
    return "lane_rules";
  }
  if (
    node.node_id === "Task_PostSolve_UEM_Verification" ||
    node.node_id === "End_Verified_Plant_Schedule"
  ) {
    return "lane_verification";
  }
  return "lane_execution";
}

function formatOmgShapeTag(kind: string): string {
  switch (kind) {
    case "startEvent":
      return "START_EVENT";
    case "endEvent":
      return "END_EVENT";
    case "boundaryTimerEvent":
      return "TIMER_EVENT";
    case "exclusiveGateway":
      return "EXCLUSIVE_GATEWAY";
    case "parallelGateway":
      return "PARALLEL_GATEWAY";
    case "businessRuleTask":
      return "BUSINESS_RULE_TASK";
    case "serviceTask":
    default:
      return "TASK";
  }
}

interface BPMNFlowViewProps {
  blueprint: DIBlueprintResponse;
}

export function BPMNFlowView({ blueprint }: BPMNFlowViewProps) {
  const { lang } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";

  const bpmn = blueprint.layers.layer_3_bpmn_process_template;
  const nodes = bpmn?.nodes ?? [];
  const flows = bpmn?.sequence_flows ?? [];
  const topo = bpmn?.topology_validation;

  const [selectedNodeId, setSelectedNodeId] = useState<string>(
    nodes[0]?.node_id ?? "Start_Weekly_MPS_Cycle"
  );
  const [downloadingXml, setDownloadingXml] = useState(false);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.node_id === selectedNodeId) ?? nodes[0] ?? null,
    [nodes, selectedNodeId]
  );

  const incomingFlows = useMemo(
    () => flows.filter((f) => f.target_ref === selectedNode?.node_id),
    [flows, selectedNode]
  );
  const outgoingFlows = useMemo(
    () => flows.filter((f) => f.source_ref === selectedNode?.node_id),
    [flows, selectedNode]
  );

  const lanes: { id: LaneId; title: string; accent: string; badgeTone: string }[] = [
    {
      id: "lane_validation",
      title: t.diBpmnLaneValidation,
      accent: "border-cyan-500/35 bg-cyan-500/5",
      badgeTone: "border-cyan-500/40 bg-cyan-500/15 text-cyan-200",
    },
    {
      id: "lane_rules",
      title: t.diBpmnLaneRules,
      accent: "border-purple-500/35 bg-purple-500/5",
      badgeTone: "border-purple-500/40 bg-purple-500/15 text-purple-200",
    },
    {
      id: "lane_execution",
      title: t.diBpmnLaneExecution,
      accent: "border-amber-500/35 bg-amber-500/5",
      badgeTone: "border-amber-500/40 bg-amber-500/15 text-amber-200",
    },
    {
      id: "lane_verification",
      title: t.diBpmnLaneVerification,
      accent: "border-emerald-500/35 bg-emerald-500/5",
      badgeTone: "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
    },
  ];

  const handleDownloadBpmnXml = async () => {
    if (downloadingXml) return;
    setDownloadingXml(true);
    try {
      await downloadDiBlueprintArtifact("bpmn_xml");
    } finally {
      setDownloadingXml(false);
    }
  };

  return (
    <div data-testid="di-tab-panel-bpmn" className="space-y-4">
      {/* Top Process Header & Topology Verification Pill */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/75 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <Workflow className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-bold text-white">{bpmn?.name}</span>
          {topo && (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-0.5 font-mono text-[10px] font-bold text-emerald-200">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span dir="ltr">
                {topo.reachable_nodes}/{topo.total_nodes} Reachable • {flows.length} Flows
              </span>
            </span>
          )}
        </div>

        <button
          type="button"
          data-testid="btn-bpmn-tab-download-xml"
          disabled={downloadingXml}
          onClick={() => void handleDownloadBpmnXml()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/45 bg-emerald-500/15 px-3 py-1.5 text-xs font-bold text-emerald-200 transition hover:bg-emerald-500/25 disabled:opacity-50"
        >
          {downloadingXml ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5 text-emerald-300" />
          )}
          <span>{t.diDownloadBpmnBtn}</span>
        </button>
      </div>

      {/* Swimlane Process Diagram */}
      <div className="space-y-3">
        {lanes.map((lane) => {
          const laneNodes = nodes.filter((n) => classifyBpmnLane(n) === lane.id);
          return (
            <div
              key={lane.id}
              data-testid={`bpmn-swimlane-${lane.id}`}
              className={`rounded-2xl border p-3.5 ${lane.accent}`}
            >
              <div className="mb-2.5 flex items-center justify-between gap-2">
                <span className={`rounded-lg border px-2.5 py-0.5 text-[11px] font-bold ${lane.badgeTone}`}>
                  {lane.title}
                </span>
                <span dir="ltr" className="font-mono text-[10px] text-slate-400">
                  {laneNodes.length} {isAr ? "عقد" : "nodes"}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
                {laneNodes.map((node, idx) => {
                  const isSelected = selectedNode?.node_id === node.node_id;
                  const shapeTag = formatOmgShapeTag(node.kind);
                  return (
                    <div key={node.node_id} className="relative flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`bpmn-node-${node.node_id}`}
                        onClick={() => setSelectedNodeId(node.node_id)}
                        className={`flex w-full flex-col justify-between rounded-xl border p-3 text-start transition ${
                          isSelected
                            ? "border-cyan-400 bg-cyan-500/15 ring-1 ring-cyan-400/50"
                            : "border-slate-800 bg-slate-950/85 hover:border-slate-600"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1.5">
                          <span
                            dir="ltr"
                            className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono text-[9px] font-bold text-cyan-300"
                          >
                            {node.kind === "startEvent" && <Play className="h-2.5 w-2.5 text-emerald-400" />}
                            {node.kind === "endEvent" && <ShieldCheck className="h-2.5 w-2.5 text-emerald-400" />}
                            {node.kind === "boundaryTimerEvent" && <Clock className="h-2.5 w-2.5 text-amber-400" />}
                            {(node.kind === "exclusiveGateway" || node.kind === "parallelGateway") && (
                              <GitFork className="h-2.5 w-2.5 text-amber-300" />
                            )}
                            {node.kind === "businessRuleTask" && <Table2 className="h-2.5 w-2.5 text-purple-300" />}
                            {node.kind === "serviceTask" && <Cpu className="h-2.5 w-2.5 text-cyan-300" />}
                            <span>{shapeTag}</span>
                          </span>
                          {node.timer_duration_iso && (
                            <span
                              dir="ltr"
                              className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-amber-300"
                            >
                              {node.timer_duration_iso}
                            </span>
                          )}
                        </div>

                        <div className="mt-2 text-xs font-bold leading-snug text-white">
                          {isAr ? BPMN_NODE_NAMES_AR[node.node_id] ?? node.name : node.name}
                        </div>

                        <div className="mt-2 flex flex-wrap items-center gap-1 pt-1">
                          {node.compiles_to_primitive && (
                            <span
                              dir="ltr"
                              className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[9px] text-emerald-300"
                            >
                              → {node.compiles_to_primitive}
                            </span>
                          )}
                          {node.dmn_table_id && (
                            <span
                              dir="ltr"
                              className="rounded border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 font-mono text-[9px] text-purple-200"
                            >
                              {node.dmn_table_id}
                            </span>
                          )}
                        </div>
                      </button>

                      {/* Directional SVG Connector Arrow between lane neighbors on Desktop */}
                      {idx < laneNodes.length - 1 && (
                        <svg
                          viewBox="0 0 24 24"
                          className={`hidden h-5 w-5 shrink-0 text-slate-500 lg:block ${
                            isAr ? "rotate-180" : ""
                          }`}
                          aria-hidden="true"
                        >
                          <path
                            d="M4 12h14m-4-4 4 4-4 4"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected BPMN Node Detail Strip */}
      {selectedNode && (
        <div
          data-testid="bpmn-node-detail-strip"
          className="rounded-2xl border border-cyan-500/35 bg-slate-900/90 p-4 text-xs"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2">
              <GitCommit className="h-4 w-4 text-cyan-400" />
              <span className="font-bold text-white">{t.diBpmnNodeDetailTitle}:</span>
              <span dir="ltr" className="font-mono font-bold text-cyan-300">
                {selectedNode.node_id}
              </span>
            </div>
            <span
              dir="ltr"
              className="rounded-md border border-slate-700 bg-slate-950 px-2 py-0.5 font-mono text-[10px] text-slate-300"
            >
              {formatOmgShapeTag(selectedNode.kind)}
            </span>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                {isAr ? "هدف الترجمة في UEM / DMN" : "Compiled UEM Primitive & DMN Binding"}
              </div>
              <div dir="ltr" className="mt-1.5 space-y-1 font-mono text-[11px]">
                <div className="text-emerald-300">
                  UEM: {selectedNode.compiles_to_primitive ?? "WorkflowControl"}
                </div>
                {selectedNode.dmn_table_id && (
                  <div className="text-purple-300">DMN: {selectedNode.dmn_table_id}</div>
                )}
                {selectedNode.timer_duration_iso && (
                  <div className="text-amber-300">Timer: {selectedNode.timer_duration_iso}</div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                {isAr ? "التدفقات الواردة" : "Incoming Sequence Flows"}
              </div>
              <div dir="ltr" className="mt-1.5 space-y-1 font-mono text-[11px] text-slate-300">
                {incomingFlows.length === 0 ? (
                  <span className="text-slate-500">None (Process Start)</span>
                ) : (
                  incomingFlows.map((f) => (
                    <div key={f.flow_id}>
                      {f.source_ref} → ({f.flow_id})
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                {isAr ? "التدفقات الصادرة وشروط البوابات" : "Outgoing Sequence Flows & Conditions"}
              </div>
              <div dir="ltr" className="mt-1.5 space-y-1 font-mono text-[11px] text-cyan-200">
                {outgoingFlows.length === 0 ? (
                  <span className="text-slate-500">None (Process End)</span>
                ) : (
                  outgoingFlows.map((f) => (
                    <div key={f.flow_id}>
                      → {f.target_ref}
                      {f.condition_expression ? ` [${f.condition_expression}]` : ""}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
