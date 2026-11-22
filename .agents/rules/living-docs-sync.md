---
trigger: always_on
description: >-
  Always-on Living Documentation Sync Gate for Mini-DIOS Plastics — keeps
  docs/MASTER_USER_GUIDE_AND_MANUAL.md, docs/MASTER_PLAYBOOK.md, and
  docs/CHANGELOG.md 100% synchronized after every backend or frontend change.
---

# Living Documentation Auto-Sync Gate — Mini-DIOS Plastics

Whenever **ANY** feature addition, optimization math change, constraint edit, parameter addition, API route change, or UI label/component edit is made in `mini-dios-workforce/backend/` or `mini-dios-workforce/frontend/`, you **MUST** synchronize the Master Living Documents before declaring the task complete.

## Mandatory Post-Update Checklist
1. **Inspect Exact Changes:** Review the modified files (via `git diff` if in a git repo, or by directly reading the edited backend/frontend modules and `frontend/src/lib/i18n.ts`).
2. **Update `docs/MASTER_USER_GUIDE_AND_MANUAL.md` In-Place:**
   - Update affected tab walkthroughs, exact UI labels/toggles, input parameter descriptions, hard-constraint/objective formulas, Copilot tool capabilities, or troubleshooting entries.
   - Verify exact EN and AR UI labels match `frontend/src/lib/i18n.ts`.
3. **Update `docs/MASTER_PLAYBOOK.md` In-Place (when commercial impact changes):**
   - Update positioning, demo script click paths, proposal scope, or objection-handling answers if the change adds a new capability, module, or ROI lever.
4. **Append to `docs/CHANGELOG.md`:**
   - Add a dated entry listing what changed in the application and the exact sections updated in `MASTER_USER_GUIDE_AND_MANUAL.md` and/or `MASTER_PLAYBOOK.md`.
5. **Automatic In-Place Google Drive Sync (Mandatory):**
   - Read `docs/.drive-sync-manifest.json`, re-assemble `docs/.combined_master_reference.md` via `scripts/sync_docs_to_drive.py`, and update every changed Master Doc **in-place** on its exact `file_id` (never create duplicates):
     - Primary: bare `gdrive mutate update <FILE_ID> <local.md> --mime-type "application/vnd.google-apps.document"` + update `last_synced_sha256` & `last_synced_at` in `docs/.drive-sync-manifest.json`.
     - Fallback: `python scripts/sync_docs_to_drive.py` (using Google Drive API v3 OAuth).
   - Report the updated Google Drive links and sync status in the final response.
6. **Enforce Single-Source-of-Truth & Zero Stale References:**
   - NEVER create duplicate files locally (`USER_GUIDE_v2.md`, `PLAYBOOK_NEW.md`, etc.) or in Google Drive.
   - Remove or update any reference to deprecated, renamed, or removed features (e.g., confirm zero outdated references to removed UI file-upload dropzones or legacy call-center schemas).

## Reusable Skills
- For syncing Master Living Documents after code edits, follow `.agents/skills/sync-master-docs/SKILL.md`.
- For drafting bespoke client emails, proposals, or executive briefs, follow `.agents/skills/create-client-doc/SKILL.md`.
