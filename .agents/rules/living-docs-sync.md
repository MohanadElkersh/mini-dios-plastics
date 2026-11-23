---
trigger: always_on
description: >-
  Always-on Living Documentation Sync Gate & Two-Track Documentation Standard
  for Mini-DIOS Plastics — enforces strict separation between Human-Friendly
  Docs (default) and the dedicated Technical Reference, and syncs all updates
  in-place locally and to Google Drive.
---

# Living Documentation Auto-Sync & Two-Track Standard — Mini-DIOS Plastics

Whenever **ANY** document is created or updated—or whenever **ANY** feature, optimization math, constraint, parameter, API route, deployment config, or UI edit is made in `mini-dios-workforce/`—you **MUST** enforce the **Two-Track Documentation Standard** and synchronize both local files and Google Drive before declaring the task complete.

## 1. Permanent Two-Track Documentation Standard (Non-Negotiable)

### Track A — Human-Friendly Documents (Default for All General, Business, Executive & User Docs)
Applies to `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, and every client email, proposal, demo script, or brief inside `docs/templates-and-drafts/`.
Every human-friendly document **MUST pass the "Normal Human Test"** (a factory owner, plant manager, or business partner reading it cold months later understands 100% effortlessly):
1. **Plain, everyday language only:** Write the way a sharp, clear person explains something over coffee.
2. **Zero raw technicalities:** NEVER include code snippets, file paths (`src/...`), environment variable names (`AUTH_SECRET_KEY`), terminal commands, HTTP status codes, Docker/Render configs, database schemas, or internal variable/constraint codes (`HC1`, `WHC1`, `SHA-256`).
3. **No unexplained jargon or acronyms:** NEVER use developer terms like *CP-SAT, OR-Tools, FastAPI, Next.js, SQLite, CORS, reverse proxy, ephemeral storage, payload, CRUD, or endpoint*. If a business/factory term must be used (e.g., *OTIF*, *purge scrap*, *changeover*), explain it naturally in plain words the first time it appears.
4. **Self-contained opening:** Every document MUST open with a 2–3 sentence plain-language summary explaining **what this document is, who it is for, and what decision or action it helps with**.
5. **Story & real-world outcomes first:** Explain features by what they do for the factory floor and bottom line rather than how the software is engineered.
6. **Natural executive Arabic:** When writing in Arabic, use natural, executive Arabic (zero robotic literal translations of English tech terms).
7. **Quiet developer pointer:** If a topic has deeper engineering specs, add a single quiet one-line pointer at the bottom (e.g., *"For developers and IT teams: see the separate Technical Reference document."*).

### Track B — Separate Technical Reference Document (100% of Technicalities Live Here Only)
All engineering details live **ONLY** inside `docs/technical/TECHNICAL_REFERENCE.md` (and `docs/CHANGELOG.md` for release/implementation logs), synced to the dedicated **`Technical Specs (For Engineers & IT)`** subfolder in Google Drive:
- System architecture, tech stack (Next.js, FastAPI, Google OR-Tools CP-SAT), and folder/file trees
- API endpoints, proxy routing, cookies, CORS, and authentication internals
- Environment variable *names* (NEVER real secrets or `.env` values), Dockerfiles, `render.yaml`, deployment workflows, and Git release commands
- Exact solver constraints (`HC1–HC6`, `WHC1–WHC5`), mathematical formulations, database schemas, and test/audit scripts
- Bug fixes, changelogs, and implementation logs

## 2. Mandatory Post-Update Sync Checklist
1. **Inspect Exact Changes:** Review modified backend/frontend/deployment files (`git diff` or direct reads) and `frontend/src/lib/i18n.ts`.
2. **Route Updates to the Right Track (In-Place Only):**
   - User-visible workflows, business benefits, demo scripts, or commercial scope → update `docs/MASTER_USER_GUIDE_AND_MANUAL.md` and/or `docs/MASTER_PLAYBOOK.md` in plain human language.
   - Code architecture, endpoints, env vars, math, constraints, or deployment → update `docs/technical/TECHNICAL_REFERENCE.md` and append a dated entry to `docs/CHANGELOG.md`.
3. **Automatic In-Place Google Drive Sync (Mandatory):**
   - Read `docs/.drive-sync-manifest.json`, re-assemble `docs/.combined_master_reference.md` (Human-Friendly Guide + Playbook ONLY), and update every changed Google Doc **in-place** on its exact `file_id` (zero duplicates):
     - Primary: bare `gdrive mutate update <FILE_ID> <local.md> --mime-type "application/vnd.google-apps.document"` + update `last_synced_sha256` & `last_synced_at` in `docs/.drive-sync-manifest.json`.
     - Fallback: `python scripts/sync_docs_to_drive.py`.
   - Confirm zero secrets or `.env` values appear in any doc, and report updated Drive links in the final response.
4. **Zero Duplicate Files:** NEVER create `USER_GUIDE_v2.md`, `PLAYBOOK_NEW.md`, or duplicate Drive files.

## Reusable Skills
- For syncing Master Living Documents & Technical Reference after code edits: `.agents/skills/sync-master-docs/SKILL.md`.
- For drafting bespoke human-friendly client emails, proposals, or briefs: `.agents/skills/create-client-doc/SKILL.md`.
