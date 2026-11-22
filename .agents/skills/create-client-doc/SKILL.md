---
name: create-client-doc
description: >-
  Drafts bespoke client-facing commercial documents for Mini-DIOS Plastics —
  including tailored proposals (EGP or SAR), cold or follow-up outreach emails
  (English, Gulf Arabic, or Egyptian Arabic), executive briefs, investor
  explainers, and meeting prep — grounded in the live codebase and
  docs/MASTER_PLAYBOOK.md, saved cleanly in docs/templates-and-drafts/.
---

# Create Client & Commercial Document (`create-client-doc`)

Use this skill whenever the user asks for a client-specific email, WhatsApp/LinkedIn DM, tailored enterprise proposal, executive one-pager, investor explainer, or meeting prep brief for **Mini-DIOS Plastics**.

## Step 1: Load Ground Truth
1. Read `docs/MASTER_PLAYBOOK.md` for approved positioning, Egypt vs. KSA framing, pricing tiers (EGP & SAR), 60-day pilot structure, and objection responses.
2. Read `docs/MASTER_USER_GUIDE_AND_MANUAL.md` (and spot-check live backend/frontend files if any specific technical capability or metric is cited) so every feature claim is 100% accurate to the current codebase.
3. Confirm the target parameters from the user's request (or ask if ambiguous):
   - **Market & Currency:** Egypt (`EGP`) or Saudi Arabia / GCC (`SAR`)
   - **Language & Register:** Executive English, Gulf Business Arabic, or Egyptian Executive Arabic
   - **Buyer Persona:** Plant Owner / Chairman, COO / Operations Director, Production Planning Manager, or CFO
   - **Plant Profile (if known):** Press count, tonnage range, process types (`Injection`, `BlowMolding`, `Extrusion`), resin grades (`PP`, `HDPE`, `LDPE`, `PET`, `ABS`, `PVC`), export mix.

## Step 2: Enforce Commercial & Technical Accuracy Rules
- **100% Deterministic Math:** Always position Mini-DIOS Plastics as a deterministic **Google OR-Tools CP-SAT** scheduling & workforce optimization engine with **Zero LLM Arithmetic**—never as a probabilistic AI chatbot.
- **Exact Capabilities Only:** Reference only verified modules (Tab 1 Plant Scope & Risk Radar, Tab 2 Data & Parameters Studio, Tab 3 Trade-Off & Scenario Composer, Tab 4 Press Gantt & Color Sequence, Tab 5 Revenue & Savings P&L, Tab 6 Workforce & Shifts, Autonomous PM Co-Optimization, Peak Tariff Avoid, Ramadan 6h Shift Mode, Operations Copilot, Executive Brief Modal, On-Prem Docker / Air-Gapped Offline Mode).
- **No Unverified Client ROI Claims:** Distinguish clearly between seeded demo benchmarks and prospect-specific numbers to be proven during a live 15-minute diagnostic or 60-day paid pilot.
- **Data Sovereignty:** Emphasize 100% on-prem Docker + `OFFLINE_MODE=true` support for Egypt factories and KSA **SDAIA / PDPL** compliance.

## Step 3: Save Draft Locally & Sync to Google Drive (`Client Proposals & Emails`)
1. Save every bespoke client or meeting deliverable locally inside:
   `docs/templates-and-drafts/<doc-type>-<client-or-topic>-<lang-or-currency>.md`
   (Example: `docs/templates-and-drafts/proposal-riyadh-pack-sar.md` or `docs/templates-and-drafts/email-cairo-plastics-ar.md`).
2. NEVER overwrite or duplicate `docs/MASTER_PLAYBOOK.md` or `docs/MASTER_USER_GUIDE_AND_MANUAL.md`.
3. **Sync to Google Drive Subfolder (`Client Proposals & Emails`):**
   - Read `client_subfolder_id` and `client_documents` from `docs/.drive-sync-manifest.json`.
   - If this draft already has a `file_id` in `client_documents`, update it **in-place** via bare `gdrive mutate update <FILE_ID> <local_path> --mime-type "application/vnd.google-apps.document"`.
   - Otherwise, upload it as a native Google Doc via bare `gdrive mutate upload <local_path> --mime-type "application/vnd.google-apps.document" --parent <client_subfolder_id>`, rename it cleanly via `gdrive mutate rename <FILE_ID> "<Readable Title>"`, and record its `file_id`, `webViewLink`, and `last_synced_sha256` inside `docs/.drive-sync-manifest.json` under `client_documents`.
   - (Fallback if using local OAuth credentials: run `python scripts/sync_docs_to_drive.py`.)

## Step 4: Verify Before Delivering
- Verify all numbers, currency symbols (`SAR` / `EGP`), and feature names match the live system.
- Present a concise summary with clickable links to both the local Markdown draft and its live Google Doc URL.
