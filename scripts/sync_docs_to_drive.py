#!/usr/bin/env python3
"""Mini-DIOS Plastics — Dual-Mode Google Drive Master Documentation Sync Engine.

Maintains a dedicated Google Drive folder (`Mini-DIOS Plastics — Master Documentation`)
containing formatted native Google Docs synchronized strictly in-place (preserving exact
`file_id`, shareable URL, permissions, and version history — zero duplicates):

  1. Mini-DIOS Plastics — Master Complete Reference  (auto-assembled from the 3 master docs)
  2. Mini-DIOS Plastics — Master User Guide & Operations Manual  (docs/MASTER_USER_GUIDE_AND_MANUAL.md)
  3. Mini-DIOS Plastics — Master Commercial & Sales Playbook     (docs/MASTER_PLAYBOOK.md)
  4. Mini-DIOS Plastics — Living Changelog                       (docs/CHANGELOG.md)
  5. Subfolder: Client Proposals & Emails  (mirrors docs/templates-and-drafts/*.md)

Backends:
  - `gdrive`: Uses Antigravity's authenticated `gdrive` plugin CLI (zero OAuth files needed).
  - `api`:    Uses Google Drive API v3 (`google-api-python-client` + `credentials.json` / `token.json`)
              with native Markdown import (`media_mime_type="text/markdown"`, target
              `mimeType="application/vnd.google-apps.document"`) and `files().update()` in-place.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

ROOT_FOLDER_NAME = "Mini-DIOS Plastics — Master Documentation"
CLIENT_SUBFOLDER_NAME = "Client Proposals & Emails"
TECH_SUBFOLDER_NAME = "Technical Specs (For Engineers & IT)"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

MASTER_DOCS: list[dict[str, str]] = [
    {
        "key": "master_complete_reference",
        "title": "Mini-DIOS Plastics — Master Complete Reference",
        "local_path": "docs/.combined_master_reference.md",
        "kind": "combined",
        "folder": "root",
    },
    {
        "key": "master_user_guide",
        "title": "Mini-DIOS Plastics — Master User Guide & Operations Manual",
        "local_path": "docs/MASTER_USER_GUIDE_AND_MANUAL.md",
        "kind": "master",
        "folder": "root",
    },
    {
        "key": "master_playbook",
        "title": "Mini-DIOS Plastics — Master Commercial & Sales Playbook",
        "local_path": "docs/MASTER_PLAYBOOK.md",
        "kind": "master",
        "folder": "root",
    },
    {
        "key": "roadmap_and_backlog",
        "title": "Mini-DIOS Plastics — Product Roadmap & Future Constraints Backlog",
        "local_path": "docs/ROADMAP_AND_BACKLOG.md",
        "kind": "master",
        "folder": "root",
        "optional": "true",
    },
    {
        "key": "technical_reference",
        "title": "Mini-DIOS Plastics — Technical Reference",
        "local_path": "docs/technical/TECHNICAL_REFERENCE.md",
        "kind": "technical",
        "folder": "tech",
    },
    {
        "key": "codebase_and_updates_log",
        "title": "Mini-DIOS Plastics — Codebase & Code-Update Ledger",
        "local_path": "docs/technical/CODEBASE_AND_UPDATES_LOG.md",
        "kind": "technical",
        "folder": "tech",
    },
    {
        "key": "living_changelog",
        "title": "Mini-DIOS Plastics — Living Changelog",
        "local_path": "docs/CHANGELOG.md",
        "kind": "technical",
        "folder": "tech",
    },
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assemble_complete_reference(docs_dir: Path) -> str:
    """Combine ONLY the human-friendly User Guide, Commercial Playbook & Roadmap into one deterministic Markdown doc."""
    guide = (docs_dir / "MASTER_USER_GUIDE_AND_MANUAL.md").read_text(encoding="utf-8").strip()
    playbook = (docs_dir / "MASTER_PLAYBOOK.md").read_text(encoding="utf-8").strip()
    roadmap_path = docs_dir / "ROADMAP_AND_BACKLOG.md"
    roadmap = roadmap_path.read_text(encoding="utf-8").strip() if roadmap_path.exists() else ""

    header = (
        "# Mini-DIOS Plastics — Master Complete Reference\n\n"
        "> **What this document is:** One complete, plain-language handbook combining our **User Guide & Operations Manual**, our **Commercial & Sales Playbook (Egypt & KSA)**, and our **Product Roadmap & Future Factory Constraints Backlog**.\n"
        "> **Who it is for:** Factory owners, operations directors, production planners, and commercial partners who want everything in one readable document.\n\n"
        "---\n\n"
        "## Part I — User Guide & Operations Manual\n\n"
    )
    out = (
        f"{header}{guide}\n\n"
        "---\n\n"
        "## Part II — Commercial & Sales Playbook (Egypt & KSA)\n\n"
        f"{playbook}\n"
    )
    if roadmap:
        out += (
            "\n---\n\n"
            "## Part III — Product Roadmap & Future Constraints Backlog\n\n"
            f"{roadmap}\n"
        )
    return out


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "version": 2,
        "root_folder_name": ROOT_FOLDER_NAME,
        "folder_id": None,
        "folder_url": None,
        "client_subfolder_name": CLIENT_SUBFOLDER_NAME,
        "client_subfolder_id": None,
        "client_subfolder_url": None,
        "tech_subfolder_name": TECH_SUBFOLDER_NAME,
        "tech_subfolder_id": None,
        "tech_subfolder_url": None,
        "documents": {},
        "client_documents": {},
    }


def save_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass
class DriveFileResult:
    file_id: str
    web_view_link: str


class DriveBackend(Protocol):
    def ensure_folder(self, name: str, parent_id: Optional[str] = None) -> DriveFileResult: ...
    def create_google_doc(self, title: str, markdown_path: Path, parent_id: str) -> DriveFileResult: ...
    def update_google_doc(self, file_id: str, markdown_path: Path, title: Optional[str] = None) -> DriveFileResult: ...


# --------------------------------------------------------------------------------------------
# Backend 1: Google Drive API v3 (google-api-python-client + OAuth Desktop credentials.json)
# --------------------------------------------------------------------------------------------
class GoogleApiDriveBackend:
    """Deterministic Google Drive API v3 backend using native Markdown -> Google Docs conversion."""

    def __init__(self, service: Any):
        self.service = service

    @classmethod
    def from_oauth(cls, project_root: Path) -> "GoogleApiDriveBackend":
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Missing Google API libraries. Install them with:\n"
                "  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
            ) from exc

        creds_path = project_root / "credentials.json"
        token_path = project_root / "token.json"
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Google OAuth credentials not found at {creds_path}.\n"
                        "3-Step Setup:\n"
                        "  1. In Google Cloud Console, enable Google Drive API and create an OAuth 2.0 Desktop Client ID.\n"
                        "  2. Download the JSON file as `credentials.json` in the project root (already in .gitignore).\n"
                        "  3. Run: `.venv\\Scripts\\python.exe scripts/sync_docs_to_drive.py` once to authorize."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        service = build("drive", "v3", credentials=creds)
        return cls(service)

    def ensure_folder(self, name: str, parent_id: Optional[str] = None) -> DriveFileResult:
        safe_name = name.replace("'", "\\'")
        q = f"name = '{safe_name}' and mimeType = '{GOOGLE_FOLDER_MIME}' and trashed = false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        resp = self.service.files().list(q=q, fields="files(id, name, webViewLink)", pageSize=5).execute()
        files = resp.get("files") or []
        if files:
            f = files[0]
            return DriveFileResult(
                file_id=f["id"],
                web_view_link=f.get("webViewLink") or f"https://drive.google.com/drive/folders/{f['id']}",
            )
        meta: dict[str, Any] = {"name": name, "mimeType": GOOGLE_FOLDER_MIME}
        if parent_id:
            meta["parents"] = [parent_id]
        created = self.service.files().create(body=meta, fields="id, webViewLink").execute()
        fid = created["id"]
        return DriveFileResult(
            file_id=fid,
            web_view_link=created.get("webViewLink") or f"https://drive.google.com/drive/folders/{fid}",
        )

    def create_google_doc(self, title: str, markdown_path: Path, parent_id: str) -> DriveFileResult:
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(markdown_path), mimetype="text/markdown", resumable=True)
        meta = {"name": title, "mimeType": GOOGLE_DOC_MIME, "parents": [parent_id]}
        created = (
            self.service.files()
            .create(body=meta, media_body=media, fields="id, webViewLink")
            .execute()
        )
        fid = created["id"]
        return DriveFileResult(
            file_id=fid,
            web_view_link=created.get("webViewLink") or f"https://docs.google.com/document/d/{fid}/edit",
        )

    def update_google_doc(self, file_id: str, markdown_path: Path, title: Optional[str] = None) -> DriveFileResult:
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(markdown_path), mimetype="text/markdown", resumable=True)
        body: dict[str, Any] = {}
        if title:
            body["name"] = title
        updated = (
            self.service.files()
            .update(fileId=file_id, body=body or None, media_body=media, fields="id, webViewLink")
            .execute()
        )
        fid = updated.get("id") or file_id
        return DriveFileResult(
            file_id=fid,
            web_view_link=updated.get("webViewLink") or f"https://docs.google.com/document/d/{fid}/edit",
        )


# --------------------------------------------------------------------------------------------
# Backend 2: Authenticated Antigravity `gdrive` Plugin CLI
# --------------------------------------------------------------------------------------------
class GdriveCliBackend:
    """Uses Antigravity's authenticated `gdrive` CLI for zero-credential-file Drive syncing."""

    def __init__(self, binary: str = "gdrive"):
        self.binary = shutil.which(binary) or binary

    def _build_cmd(self, args: list[str]) -> list[str]:
        return [self.binary, *args]

    def _run_json(self, args: list[str]) -> Any:
        import time

        cmd = self._build_cmd([*args, "--json"])
        for attempt in range(4):
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
            if proc.returncode == 0:
                break
            err_txt = (proc.stderr or "") + (proc.stdout or "")
            if ("rateLimitExceeded" in err_txt or "Quota exceeded" in err_txt) and attempt < 3:
                time.sleep(2.5 * (attempt + 1))
                continue
            raise RuntimeError(f"gdrive command failed ({' '.join(cmd)}): {proc.stderr.strip() or proc.stdout.strip()}")
        out = proc.stdout.strip()
        if not out:
            return {}
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            # Extract file ID if gdrive returned human-readable text instead of JSON
            for token in out.replace("(", " ").replace(")", " ").split():
                if len(token) >= 25 and all(c.isalnum() or c in "-_" for c in token):
                    return {"id": token}
            return {"raw": out}

    def _run_text(self, args: list[str]) -> str:
        import time

        cmd = self._build_cmd(args)
        for attempt in range(4):
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
            if proc.returncode == 0:
                return proc.stdout.strip()
            err_txt = (proc.stderr or "") + (proc.stdout or "")
            if ("rateLimitExceeded" in err_txt or "Quota exceeded" in err_txt) and attempt < 3:
                time.sleep(2.5 * (attempt + 1))
                continue
            raise RuntimeError(f"gdrive command failed ({' '.join(cmd)}): {proc.stderr.strip() or proc.stdout.strip()}")
        return ""

    def ensure_folder(self, name: str, parent_id: Optional[str] = None) -> DriveFileResult:
        search_args = ["readonly", "search", "--name-exact", name, "--type", "folder"]
        if parent_id:
            search_args.extend(["--parent-id", parent_id])
        items = self._run_json(search_args)
        if isinstance(items, list) and items:
            fid = items[0]["id"]
            return DriveFileResult(
                file_id=fid,
                web_view_link=items[0].get("webViewLink") or f"https://drive.google.com/drive/folders/{fid}",
            )
        mk_args = ["mutate", "mkdir", name]
        if parent_id:
            mk_args.extend(["--parent", parent_id])
        created = self._run_json(mk_args)
        fid = created["id"]
        return DriveFileResult(
            file_id=fid,
            web_view_link=created.get("webViewLink") or f"https://drive.google.com/drive/folders/{fid}",
        )

    def create_google_doc(self, title: str, markdown_path: Path, parent_id: str) -> DriveFileResult:
        created = self._run_json(
            [
                "mutate",
                "upload",
                str(markdown_path),
                "--mime-type",
                GOOGLE_DOC_MIME,
                "--parent",
                parent_id,
            ]
        )
        fid = created["id"]
        self._run_text(["mutate", "rename", fid, title])
        return DriveFileResult(
            file_id=fid,
            web_view_link=created.get("webViewLink") or f"https://docs.google.com/document/d/{fid}/edit",
        )

    def update_google_doc(self, file_id: str, markdown_path: Path, title: Optional[str] = None) -> DriveFileResult:
        updated = self._run_json(
            ["mutate", "update", file_id, str(markdown_path), "--mime-type", GOOGLE_DOC_MIME]
        )
        fid = updated.get("id") or file_id
        return DriveFileResult(
            file_id=fid,
            web_view_link=updated.get("webViewLink") or f"https://docs.google.com/document/d/{fid}/edit",
        )


# --------------------------------------------------------------------------------------------
# Core Sync Orchestrator (Strict In-Place Updates + SHA-256 Change Detection)
# --------------------------------------------------------------------------------------------
def sync_docs_to_drive(
    project_root: Path,
    backend: Optional[DriveBackend],
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    docs_dir = project_root / "docs"
    manifest_path = docs_dir / ".drive-sync-manifest.json"
    manifest = load_manifest(manifest_path)

    # 1. Assemble unified Master Complete Reference in memory / temp file
    combined_md = assemble_complete_reference(docs_dir)
    combined_tmp_dir = Path(tempfile.mkdtemp(prefix="dios_drive_sync_"))
    combined_path = combined_tmp_dir / "Mini-DIOS_Master_Complete_Reference.md"
    combined_path.write_text(combined_md, encoding="utf-8")

    actions: list[dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # 2. Ensure root, client, and technical subfolders exist
        if dry_run:
            root_folder_id = manifest.get("folder_id") or "DRY_RUN_ROOT_FOLDER_ID"
            client_folder_id = manifest.get("client_subfolder_id") or "DRY_RUN_CLIENT_FOLDER_ID"
            tech_folder_id = manifest.get("tech_subfolder_id") or "DRY_RUN_TECH_FOLDER_ID"
        else:
            assert backend is not None
            if not manifest.get("folder_id"):
                root_res = backend.ensure_folder(ROOT_FOLDER_NAME)
                manifest["folder_id"] = root_res.file_id
                manifest["folder_url"] = root_res.web_view_link
            root_folder_id = manifest["folder_id"]

            if not manifest.get("client_subfolder_id"):
                sub_res = backend.ensure_folder(CLIENT_SUBFOLDER_NAME, parent_id=root_folder_id)
                manifest["client_subfolder_id"] = sub_res.file_id
                manifest["client_subfolder_url"] = sub_res.web_view_link
            client_folder_id = manifest["client_subfolder_id"]

            if not manifest.get("tech_subfolder_id"):
                tech_res = backend.ensure_folder(TECH_SUBFOLDER_NAME, parent_id=root_folder_id)
                manifest["tech_subfolder_name"] = TECH_SUBFOLDER_NAME
                manifest["tech_subfolder_id"] = tech_res.file_id
                manifest["tech_subfolder_url"] = tech_res.web_view_link
            tech_folder_id = manifest["tech_subfolder_id"]

        # 3. Sync Master Docs (Human-Friendly in root; Technical Reference & Changelog in tech subfolder)
        docs_map: dict[str, Any] = manifest.setdefault("documents", {})
        for spec in MASTER_DOCS:
            key = spec["key"]
            title = spec["title"]
            target_parent_id = tech_folder_id if spec.get("folder") == "tech" else root_folder_id
            src_path = combined_path if spec["kind"] == "combined" else (project_root / spec["local_path"])
            if not src_path.exists():
                if spec.get("optional") == "true":
                    continue
                raise FileNotFoundError(f"Expected master document not found: {src_path}")

            content = src_path.read_text(encoding="utf-8")
            content_sha = sha256_text(content)
            existing = docs_map.get(key) or {}
            existing_id = existing.get("file_id")
            prev_sha = existing.get("last_synced_sha256")

            if existing_id and prev_sha == content_sha and not force:
                actions.append(
                    {
                        "key": key,
                        "title": title,
                        "action": "skipped_unchanged",
                        "file_id": existing_id,
                        "webViewLink": existing.get("webViewLink"),
                    }
                )
                continue

            if dry_run:
                act = "would_update" if existing_id else "would_create"
                actions.append(
                    {
                        "key": key,
                        "title": title,
                        "action": act,
                        "file_id": existing_id or "NEW_FILE_ID",
                        "sha256": content_sha[:12],
                    }
                )
                continue

            assert backend is not None
            if existing_id:
                res = backend.update_google_doc(existing_id, src_path, title=title)
                act = "updated"
            else:
                res = backend.create_google_doc(title, src_path, parent_id=target_parent_id)
                act = "created"

            docs_map[key] = {
                "title": title,
                "local_path": spec["local_path"],
                "file_id": res.file_id,
                "webViewLink": res.web_view_link,
                "last_synced_sha256": content_sha,
                "last_synced_at": now_iso,
            }
            manifest["last_sync_at"] = now_iso
            save_manifest(manifest_path, manifest)
            actions.append(
                {
                    "key": key,
                    "title": title,
                    "action": act,
                    "file_id": res.file_id,
                    "webViewLink": res.web_view_link,
                }
            )

        # 4. Mirror bespoke client drafts in docs/templates-and-drafts/*.md
        drafts_dir = docs_dir / "templates-and-drafts"
        client_map: dict[str, Any] = manifest.setdefault("client_documents", {})
        if drafts_dir.exists():
            for md_file in sorted(drafts_dir.glob("*.md")):
                if md_file.name.lower() == "readme.md":
                    continue
                rel_path = f"docs/templates-and-drafts/{md_file.name}"
                key = md_file.stem
                title = md_file.stem.replace("-", " ").replace("_", " ").title()
                content = md_file.read_text(encoding="utf-8")
                content_sha = sha256_text(content)
                existing = client_map.get(key) or {}
                existing_id = existing.get("file_id")
                prev_sha = existing.get("last_synced_sha256")

                if existing_id and prev_sha == content_sha and not force:
                    actions.append(
                        {
                            "key": key,
                            "title": title,
                            "action": "skipped_unchanged",
                            "file_id": existing_id,
                            "webViewLink": existing.get("webViewLink"),
                        }
                    )
                    continue

                if dry_run:
                    actions.append(
                        {
                            "key": key,
                            "title": title,
                            "action": "would_update" if existing_id else "would_create",
                            "file_id": existing_id or "NEW_CLIENT_DOC_ID",
                            "sha256": content_sha[:12],
                        }
                    )
                    continue

                assert backend is not None
                if existing_id:
                    res = backend.update_google_doc(existing_id, md_file, title=title)
                    act = "updated"
                else:
                    res = backend.create_google_doc(title, md_file, parent_id=client_folder_id)
                    act = "created"

                client_map[key] = {
                    "title": title,
                    "local_path": rel_path,
                    "file_id": res.file_id,
                    "webViewLink": res.web_view_link,
                    "last_synced_sha256": content_sha,
                    "last_synced_at": now_iso,
                }
                actions.append(
                    {
                        "key": key,
                        "title": title,
                        "action": act,
                        "file_id": res.file_id,
                        "webViewLink": res.web_view_link,
                    }
                )

        if not dry_run:
            manifest["last_sync_at"] = now_iso
            save_manifest(manifest_path, manifest)

        return {"manifest": manifest, "actions": actions}
    finally:
        shutil.rmtree(combined_tmp_dir, ignore_errors=True)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync Mini-DIOS Plastics Master Docs to Google Drive in-place.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--backend", choices=["auto", "gdrive", "api"], default="auto")
    parser.add_argument("--force", action="store_true", help="Force re-sync even when SHA-256 is unchanged.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without calling Google Drive.")
    args = parser.parse_args(argv)

    backend: Optional[DriveBackend] = None
    if not args.dry_run:
        chosen = args.backend
        if chosen == "auto":
            chosen = "gdrive" if shutil.which("gdrive") else "api"
        if chosen == "gdrive":
            backend = GdriveCliBackend()
        else:
            backend = GoogleApiDriveBackend.from_oauth(args.project_root)

    summary = sync_docs_to_drive(args.project_root, backend=backend, force=args.force, dry_run=args.dry_run)
    print(json.dumps(summary["actions"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
