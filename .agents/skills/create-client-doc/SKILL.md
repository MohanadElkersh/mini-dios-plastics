---
name: create-client-doc
description: >-
  Drafts bespoke, 100% human-friendly client-facing commercial documents for
  Mini-DIOS Plastics — tailored proposals (EGP or SAR), outreach messages
  (English, Gulf Arabic, or Egyptian Arabic), demo scripts, and executive
  briefs — saved in docs/templates-and-drafts/ and synced in-place to Google Drive.
---

# Create Client & Commercial Document (`create-client-doc`)

Use this skill whenever the user asks for a client-specific email, WhatsApp/LinkedIn DM, tailored enterprise proposal, live demo script, executive one-pager, or meeting prep brief for **Mini-DIOS Plastics**.

## Step 1: Load Ground Truth
1. Read `docs/MASTER_PLAYBOOK.md` for approved Egypt/KSA positioning, pricing tiers (EGP & SAR), 60-day pilot structure, and objection responses.
2. Read `docs/MASTER_USER_GUIDE_AND_MANUAL.md` (and spot-check live UI labels if needed) so every feature claim matches the current product.
3. Confirm target market (`Egypt / EGP` or `KSA / SAR`), language/register (English, Egyptian Executive Arabic, or Gulf Executive Arabic), and buyer persona (Owner, COO, Production Manager, or CFO).

## Step 2: Enforce the Normal Human Test (Mandatory)
Every client-facing document is **Track A (Human-Friendly)** without exception:
- **Plain, sharp business language:** Write like an experienced industrial advisor speaking over coffee.
- **Zero raw technicalities or developer jargon:** NEVER mention `CP-SAT`, `OR-Tools`, `FastAPI`, `Next.js`, `SQLite`, `Docker`, `OFFLINE_MODE`, `SHA-256`, `CRUD`, `API`, `endpoint`, `HC1–HC6`, `WHC1–WHC5`, `LoginGate`, file paths, or code snippets.
  - Instead of *"Google OR-Tools CP-SAT"*, write *"exact mathematical scheduling"* or *"a proven mathematical scheduling engine"*.
  - Instead of *"On-Premises Docker with OFFLINE_MODE=true"*, write *"runs privately on your own factory server with zero internet connection required"*.
  - Instead of *"11/11 Hard Constraints (HC1–HC6, WHC1–WHC5)"*, write *"automatically enforces every press, mold, resin, and labor-law rule"*.
- **Self-contained opening:** Begin with 2–3 plain sentences explaining what the document is, who it is for, and how to use it.
- **Natural executive Arabic:** Write idiomatic Gulf or Egyptian executive Arabic—never literal translations of English tech jargon.
- **Quiet developer pointer (only if needed):** Add a single quiet line at the bottom pointing IT teams to the separate Technical Reference document.

## Step 3: Save Locally & Sync In-Place to Google Drive (`Client Proposals & Emails`)
1. Save locally inside `docs/templates-and-drafts/<doc-type>-<client-or-topic>-<lang-or-currency>.md`.
2. Read `client_subfolder_id` and `client_documents` from `docs/.drive-sync-manifest.json`.
3. If already listed in `client_documents`, update **in-place** via bare `gdrive mutate update <FILE_ID> <local_path> --mime-type "application/vnd.google-apps.document"`. Otherwise upload via bare `gdrive mutate upload <local_path> --mime-type "application/vnd.google-apps.document" --parent <client_subfolder_id>`, rename cleanly, and record in `docs/.drive-sync-manifest.json`.
4. Return clickable links to both the local draft and the live Google Doc.
