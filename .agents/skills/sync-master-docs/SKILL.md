---
name: sync-master-docs
description: >-
  Synchronizes Mini-DIOS Plastics Master Living Documents
  (docs/MASTER_USER_GUIDE_AND_MANUAL.md, docs/MASTER_PLAYBOOK.md, and
  docs/CHANGELOG.md) in-place after any backend or frontend code change. Use
  whenever features, solver math, parameters, endpoints, or UI labels change.
---

# Sync Master Living Documents (`sync-master-docs`)

Use this procedure to keep all Mini-DIOS Plastics Master Living Documents 100% grounded in the live codebase with zero drift and zero duplicate files.

## Step 1: Identify Exact Code Changes
1. If inside a git repository, run `git status` and `git diff` to list every modified file in `mini-dios-workforce/backend/` and `mini-dios-workforce/frontend/`.
2. Otherwise, read the recently modified source files directly.
3. Cross-check coupled ground-truth files:
   - **Backend:** `ontology.py`, `solver.py`, `workforce_solver.py`, `financials.py`, `risk_radar.py`, `disruptions.py`, `kpi.py`, `verify.py`, `copilot.py`, `seed.py`, `api/routes.py`.
   - **Frontend:** `src/lib/i18n.ts`, `TopBar.tsx`, `DecisionLoopStrip.tsx`, `ScopeView.tsx`, `DataStudioView.tsx`, `TradeoffConsole.tsx`, `ProductionGanttView.tsx`, `FinancialsView.tsx`, `WorkforceView.tsx`, `RiskRadarPanel.tsx`, `ExecutiveBriefModal.tsx`, `CopilotDrawer.tsx`, and `components/studio/*`.

## Step 2: Update `docs/MASTER_USER_GUIDE_AND_MANUAL.md` In-Place
- Map each code change to its exact section:
  - Launch/env/Docker change -> **Section 2 (Quick Start & Launching Locally)**
  - UI tab, button, toggle, or Studio parameter change -> **Section 3 (Complete Tab-by-Tab User Guide)**
  - Copilot tool, prompt chip, or Gemini/offline behavior change -> **Section 4 (Using the Operations Copilot)**
  - Constraint (HC1–HC6 / WHC1–WHC5), objective weight, Risk Radar rule, Autonomous PM, or P&L formula change -> **Section 5 (Mathematical & Technical Architecture Appendix)**
  - New error code or validation rule -> **Section 6 (Troubleshooting & Operator FAQ)**
- Edit the canonical file in-place using `edit_file`. NEVER create `_v2` or `_NEW` copies.

## Step 3: Update `docs/MASTER_PLAYBOOK.md` In-Place (If Commercial Impact Changed)
- If a change introduces a new commercial capability, demo talking point, KPI, or deployment option, update the corresponding section(s) in `docs/MASTER_PLAYBOOK.md`:
  - **Section 1** (Positioning & Differentiation)
  - **Section 3** (Live 10-Minute Executive Demo Script)
  - **Section 5** (Customizable Enterprise Proposal Template)
  - **Section 6** (Executive Objection Handling Playbook)

## Step 4: Log the Update in `docs/CHANGELOG.md`
- Prepend or append a dated entry (`YYYY-MM-DD`) documenting:
  - What changed in the backend/frontend application.
  - Which exact sections of `docs/MASTER_USER_GUIDE_AND_MANUAL.md` and `docs/MASTER_PLAYBOOK.md` were updated.

## Step 5: Push In-Place Sync to Google Drive & Verify `file_id`s
1. Read `docs/.drive-sync-manifest.json` to get the canonical `file_id`s for:
   - `Mini-DIOS Plastics — Master Complete Reference`
   - `Mini-DIOS Plastics — Master User Guide & Operations Manual`
   - `Mini-DIOS Plastics — Master Commercial & Sales Playbook`
   - `Mini-DIOS Plastics — Living Changelog`
2. Re-assemble `docs/.combined_master_reference.md` using `assemble_complete_reference()` from `scripts/sync_docs_to_drive.py`.
3. For every doc whose SHA-256 differs from `last_synced_sha256` in `docs/.drive-sync-manifest.json`:
   - **Primary (Antigravity `gdrive` CLI):** Run bare `gdrive mutate update <FILE_ID> <local_path> --mime-type "application/vnd.google-apps.document"` (preserving exact `file_id`, shareable link, permissions, and version history). Update `last_synced_sha256` and `last_synced_at` in `docs/.drive-sync-manifest.json`.
   - **Fallback (Python Drive API v3):** Run `python scripts/sync_docs_to_drive.py`.
4. Verify zero duplicate files exist in the Drive folder (`gdrive readonly ls <folder_id>`) and include the updated Google Doc links in the final summary.

## Step 6: Drift & Hygiene Verification
1. Verify every tab name, button label, and toggle matches `mini-dios-workforce/frontend/src/lib/i18n.ts`.
2. Verify every constraint (`HC1–HC6`, `WHC1–WHC5`), default parameter, and financial reconciliation formula matches `ontology.py`, `solver.py`, `workforce_solver.py`, and `financials.py`.
3. Confirm zero stale references to removed features (no legacy file-upload dropzones in Tab 1 UI, no legacy call-center schemas).
4. Confirm zero application source files were modified unless explicitly requested.
