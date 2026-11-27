"use client";

import React, { useState } from "react";
import { Download, FileSpreadsheet, FileText, FileCode2, Loader2, MessageSquareShare } from "lucide-react";
import { downloadIntegrationExportApi } from "@/lib/api";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

interface ScheduleExportMenuProps {
  compact?: boolean;
  testIdPrefix?: string;
}

export function ScheduleExportMenu({
  compact = false,
  testIdPrefix = "export-schedule",
}: ScheduleExportMenuProps) {
  const { lang, currency, result, setWhatsappModalOpen } = useApp();
  const t = COPY[lang];
  const [busyFormat, setBusyFormat] = useState<"xlsx" | "csv" | "json" | null>(null);

  const handleDownload = async (format: "xlsx" | "csv" | "json") => {
    if (busyFormat) return;
    setBusyFormat(format);
    try {
      const blob = await downloadIntegrationExportApi(format, result?.run_id, currency);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const runTag = result?.run_id || "LIVE";
      a.href = url;
      a.download =
        format === "xlsx"
          ? `mini_dios_schedule_${runTag}.xlsx`
          : format === "csv"
            ? `mini_dios_schedule_${runTag}.csv`
            : `mini_dios_erp_payload_${runTag}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // Non-fatal
    } finally {
      setBusyFormat(null);
    }
  };

  return (
    <div
      data-testid={`${testIdPrefix}-group`}
      className="flex flex-wrap items-center gap-1.5"
    >
      {!compact && (
        <span className="me-1 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400">
          <Download className="h-3.5 w-3.5 text-cyan-400" />
          <span>{t.exportScheduleLabel}:</span>
        </span>
      )}
      <button
        type="button"
        data-testid={`${testIdPrefix}-xlsx`}
        disabled={busyFormat !== null}
        onClick={() => void handleDownload("xlsx")}
        className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-semibold text-emerald-200 transition hover:bg-emerald-500/25 disabled:opacity-50 md:min-h-0"
      >
        {busyFormat === "xlsx" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
        )}
        <span>{t.exportExcelBtn}</span>
      </button>

      <button
        type="button"
        data-testid={`${testIdPrefix}-csv`}
        disabled={busyFormat !== null}
        onClick={() => void handleDownload("csv")}
        className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-2.5 py-1 text-[11px] font-semibold text-cyan-200 transition hover:bg-cyan-500/25 disabled:opacity-50 md:min-h-0"
      >
        {busyFormat === "csv" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <FileText className="h-3.5 w-3.5 text-cyan-400" />
        )}
        <span>{t.exportCsvBtn}</span>
      </button>

      <button
        type="button"
        data-testid={`${testIdPrefix}-json`}
        disabled={busyFormat !== null}
        onClick={() => void handleDownload("json")}
        className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-500/15 px-2.5 py-1 text-[11px] font-semibold text-indigo-200 transition hover:bg-indigo-500/25 disabled:opacity-50 md:min-h-0"
      >
        {busyFormat === "json" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <FileCode2 className="h-3.5 w-3.5 text-indigo-400" />
        )}
        <span>{t.exportErpJsonBtn}</span>
      </button>

      <button
        type="button"
        data-testid={`${testIdPrefix}-whatsapp`}
        onClick={() => setWhatsappModalOpen(true)}
        className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-teal-500/45 bg-teal-500/15 px-2.5 py-1 text-[11px] font-semibold text-teal-200 transition hover:bg-teal-500/25 md:min-h-0"
      >
        <MessageSquareShare className="h-3.5 w-3.5 text-teal-400" />
        <span>{t.whatsappDispatchBtn}</span>
      </button>
    </div>
  );
}
