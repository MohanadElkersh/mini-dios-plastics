"""Unit tests for Mini-DIOS Plastics Google Drive In-Place Sync Engine (mocked Drive backend)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sync_docs_to_drive import DriveFileResult, sync_docs_to_drive  # noqa: E402


class MockDriveBackend:
    """In-memory mock of DriveBackend recording every folder, create, and update call."""

    def __init__(self) -> None:
        self.counter = 0
        self.folders_created: list[tuple[str, Optional[str]]] = []
        self.docs_created: list[tuple[str, str, str]] = []  # (file_id, title, parent_id)
        self.docs_updated: list[tuple[str, Optional[str]]] = []  # (file_id, title)

    def _next_id(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}_{self.counter:03d}"

    def ensure_folder(self, name: str, parent_id: Optional[str] = None) -> DriveFileResult:
        fid = self._next_id("FLD")
        self.folders_created.append((name, parent_id))
        return DriveFileResult(file_id=fid, web_view_link=f"https://drive.google.com/drive/folders/{fid}")

    def create_google_doc(self, title: str, markdown_path: Path, parent_id: str) -> DriveFileResult:
        assert markdown_path.exists()
        fid = self._next_id("DOC")
        self.docs_created.append((fid, title, parent_id))
        return DriveFileResult(file_id=fid, web_view_link=f"https://docs.google.com/document/d/{fid}/edit")

    def update_google_doc(self, file_id: str, markdown_path: Path, title: Optional[str] = None) -> DriveFileResult:
        assert markdown_path.exists()
        self.docs_updated.append((file_id, title))
        return DriveFileResult(file_id=file_id, web_view_link=f"https://docs.google.com/document/d/{file_id}/edit")


class TestDriveSyncEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name)
        docs = self.project_root / "docs"
        drafts = docs / "templates-and-drafts"
        tech = docs / "technical"
        drafts.mkdir(parents=True)
        tech.mkdir(parents=True)
        (docs / "MASTER_USER_GUIDE_AND_MANUAL.md").write_text("# User Guide v1\n", encoding="utf-8")
        (docs / "MASTER_PLAYBOOK.md").write_text("# Playbook v1\n", encoding="utf-8")
        (tech / "TECHNICAL_REFERENCE.md").write_text("# Technical Reference v1\n", encoding="utf-8")
        (docs / "CHANGELOG.md").write_text("# Changelog v1\n", encoding="utf-8")
        (drafts / "README.md").write_text("# Readme ignored\n", encoding="utf-8")
        (drafts / "proposal-riyadh-sar.md").write_text("# Riyadh Proposal\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_first_sync_creates_folders_docs_and_manifest(self) -> None:
        backend = MockDriveBackend()
        res = sync_docs_to_drive(self.project_root, backend=backend)

        self.assertEqual(len(backend.folders_created), 3)  # root + client + technical
        self.assertEqual(len(backend.docs_created), 6)  # 5 master/tech docs + 1 client draft (README skipped)
        self.assertEqual(len(backend.docs_updated), 0)

        manifest_path = self.project_root / "docs" / ".drive-sync-manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(manifest["folder_id"])
        self.assertIsNotNone(manifest["client_subfolder_id"])
        self.assertIsNotNone(manifest["tech_subfolder_id"])
        self.assertEqual(set(manifest["documents"].keys()), {
            "master_complete_reference",
            "master_user_guide",
            "master_playbook",
            "technical_reference",
            "living_changelog",
        })
        self.assertIn("proposal-riyadh-sar", manifest["client_documents"])
        self.assertEqual(len(res["actions"]), 6)
        self.assertTrue(all(a["action"] == "created" for a in res["actions"]))

    def test_edit_local_doc_updates_same_file_id_never_creates(self) -> None:
        backend = MockDriveBackend()
        first = sync_docs_to_drive(self.project_root, backend=backend)
        manifest_before = first["manifest"]
        guide_id = manifest_before["documents"]["master_user_guide"]["file_id"]
        combined_id = manifest_before["documents"]["master_complete_reference"]["file_id"]
        playbook_id = manifest_before["documents"]["master_playbook"]["file_id"]

        # Edit only the User Guide locally
        (self.project_root / "docs" / "MASTER_USER_GUIDE_AND_MANUAL.md").write_text(
            "# User Guide v1.1\nAdded new section.\n", encoding="utf-8"
        )

        backend.docs_created.clear()
        backend.docs_updated.clear()
        second = sync_docs_to_drive(self.project_root, backend=backend)

        # Must NEVER create a new file; must update ONLY User Guide + Combined Reference on their exact IDs
        self.assertEqual(len(backend.docs_created), 0)
        updated_ids = {fid for fid, _ in backend.docs_updated}
        self.assertEqual(updated_ids, {guide_id, combined_id})

        by_key = {a["key"]: a for a in second["actions"]}
        self.assertEqual(by_key["master_user_guide"]["action"], "updated")
        self.assertEqual(by_key["master_user_guide"]["file_id"], guide_id)
        self.assertEqual(by_key["master_complete_reference"]["action"], "updated")
        self.assertEqual(by_key["master_complete_reference"]["file_id"], combined_id)
        self.assertEqual(by_key["master_playbook"]["action"], "skipped_unchanged")
        self.assertEqual(by_key["master_playbook"]["file_id"], playbook_id)

    def test_unchanged_files_skipped_unless_force_true(self) -> None:
        backend = MockDriveBackend()
        sync_docs_to_drive(self.project_root, backend=backend)

        backend.docs_created.clear()
        backend.docs_updated.clear()
        res_skip = sync_docs_to_drive(self.project_root, backend=backend, force=False)
        self.assertEqual(len(backend.docs_created), 0)
        self.assertEqual(len(backend.docs_updated), 0)
        self.assertTrue(all(a["action"] == "skipped_unchanged" for a in res_skip["actions"]))

        res_force = sync_docs_to_drive(self.project_root, backend=backend, force=True)
        self.assertEqual(len(backend.docs_created), 0)
        self.assertEqual(len(backend.docs_updated), 6)
        self.assertTrue(all(a["action"] == "updated" for a in res_force["actions"]))


if __name__ == "__main__":
    unittest.main()
