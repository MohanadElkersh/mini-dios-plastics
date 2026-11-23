---
name: sync-master-docs
description: >-
  Synchronizes Mini-DIOS Plastics Two-Track Living Documents (human-friendly
  User Guide & Commercial Playbook + separate Technical Reference & Changelog)
  in-place locally and in Google Drive after any code or deployment change.
---

# Sync Master Living Documents (`sync-master-docs`)

Use this procedure after any backend, frontend, solver, or deployment change to keep both documentation tracks 100% accurate, cleanly separated, and synced in-place to Google Drive.

## Step 1: Inspect Exact Code Changes
1. Review modified files via `git diff` or direct reads across `mini-dios-workforce/backend/`, `mini-dios-workforce/frontend/`, `render.yaml`, and `docker-compose.yml`.
2. Cross-check live UI labels in `mini-dios-workforce/frontend/src/lib/i18n.ts`.

## Step 2: Route Updates Under the Two-Track Standard
- **Track A — Human-Friendly Docs (`docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`):**
  - Update user workflows, exact on-screen button names, business outcomes, demo scripts, or commercial scope **in plain, everyday language**.
  - **Strict check:** ZERO code blocks, file paths, env vars, terminal commands, HTTP codes, Docker/Render configs, or developer jargon (`CP-SAT`, `OR-Tools`, `FastAPI`, `Next.js`, `SQLite`, `CORS`, `endpoint`, `HC1`, `SHA-256`).
  - Keep a 2–3 sentence plain-language intro at the top and a single quiet pointer to the Technical Reference at the bottom.
- **Track B — Technical Reference (`docs/technical/TECHNICAL_REFERENCE.md`), Changelog (`docs/CHANGELOG.md`) & Codebase Ledger (`docs/technical/CODEBASE_AND_UPDATES_LOG.md`):**
  - **Every code edit (mandatory):** Update **Section A (Living Codebase Map)** in `docs/technical/CODEBASE_AND_UPDATES_LOG.md` whenever any file, route, component, or major function changes, and prepend a new detailed entry to **Section B (Complete Code Update Ledger)** (date + commit hash or `Uncommitted / Local`, title & why, exact files changed, granular per-file changes, impact/dependencies, verification status).
  - Update `docs/technical/TECHNICAL_REFERENCE.md` when architecture, endpoints, env var names (NEVER real secrets), Docker/Render specs, solver constraints, or math formulas change, and append a concise release note to `docs/CHANGELOG.md`.

## Step 3: Push In-Place Sync to Google Drive
1. Read `docs/.drive-sync-manifest.json`.
2. Re-assemble `docs/.combined_master_reference.md` via `assemble_complete_reference()` in `scripts/sync_docs_to_drive.py` (combines **ONLY** the human-friendly User Guide & Commercial Playbook so non-technical readers never see code or changelogs).
3. For every doc whose SHA-256 changed (including `docs/technical/CODEBASE_AND_UPDATES_LOG.md`):
   - **Primary:** Run bare `gdrive mutate update <FILE_ID> <local_path> --mime-type "application/vnd.google-apps.document"` and update `last_synced_sha256` & `last_synced_at` in `docs/.drive-sync-manifest.json`.
   - **Fallback:** Run `python scripts/sync_docs_to_drive.py`.
4. Ensure `Mini-DIOS Plastics — Technical Reference`, `Mini-DIOS Plastics — Codebase & Code-Update Ledger`, and `Mini-DIOS Plastics — Living Changelog` reside inside the **`Technical Specs (For Engineers & IT)`** Drive subfolder.

## Step 4: Hygiene & Security Verification
1. Verify zero secrets or `.env` values exist in any document.
2. Verify zero duplicate files exist locally or in Google Drive.
3. Report updated local paths and clickable Google Drive links in plain human language.
