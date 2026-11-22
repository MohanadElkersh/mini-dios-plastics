"""SQLite-backed deterministic audit log & session-isolated workspaces for Mini-DIOS Plastics."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .ontology import PlantDataset, SolveResult, SolverConfig
from .seed import default_config, demo_dataset

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "audit.db"
DEFAULT_SESSION_ID = "local"


class AuditStore:
    """Thread-safe SQLite audit & workspace store with per-session sandbox isolation."""

    def __init__(self, db_path: Optional[str | Path] = None):
        env_path = os.environ.get("DIOS_AUDIT_DB")
        resolved = Path(db_path) if db_path is not None else (Path(env_path) if env_path else DEFAULT_DB_PATH)
        self.db_path = resolved
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plastics_audit_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    solve_time_ms INTEGER NOT NULL,
                    inputs_sha256 TEXT NOT NULL,
                    schedule_sha256 TEXT NOT NULL,
                    ramadan_shift_mode INTEGER NOT NULL,
                    avoid_peak_tariff_hrs INTEGER NOT NULL,
                    w_changeover_scrap INTEGER NOT NULL,
                    w_otif INTEGER NOT NULL,
                    w_energy_cost INTEGER NOT NULL,
                    w_working_capital INTEGER NOT NULL,
                    cash_savings REAL NOT NULL,
                    cash_savings_pct REAL NOT NULL,
                    purge_scrap_kg_saved REAL NOT NULL,
                    changeover_hours_saved REAL NOT NULL,
                    otif_pct REAL NOT NULL,
                    oee_pct REAL NOT NULL,
                    all_hard_constraints_passed INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    dataset_json TEXT NOT NULL
                )
                """
            )
            # Safe migration for pre-existing audit DBs without session_id
            run_cols = {r["name"] for r in conn.execute("PRAGMA table_info(plastics_audit_runs)").fetchall()}
            if "session_id" not in run_cols:
                conn.execute("ALTER TABLE plastics_audit_runs ADD COLUMN session_id TEXT NOT NULL DEFAULT 'local'")

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plastics_audit_created ON plastics_audit_runs (created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plastics_audit_session ON plastics_audit_runs (session_id, created_at DESC)"
            )

            # Workspaces table with composite PRIMARY KEY (session_id, workspace_id)
            ws_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='plastics_workspaces'"
            ).fetchone()
            if ws_exists:
                ws_cols = {r["name"] for r in conn.execute("PRAGMA table_info(plastics_workspaces)").fetchall()}
                if "session_id" not in ws_cols:
                    # Migrate legacy single-tenant workspaces table into composite-PK multi-session table
                    conn.execute(
                        """
                        CREATE TABLE plastics_workspaces_v2 (
                            session_id TEXT NOT NULL DEFAULT 'local',
                            workspace_id TEXT NOT NULL,
                            name TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            dataset_json TEXT NOT NULL,
                            config_json TEXT NOT NULL,
                            PRIMARY KEY (session_id, workspace_id)
                        )
                        """
                    )
                    conn.execute(
                        """
                        INSERT INTO plastics_workspaces_v2 (
                            session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json
                        )
                        SELECT 'local', workspace_id, name, created_at, updated_at, dataset_json, config_json
                        FROM plastics_workspaces
                        """
                    )
                    conn.execute("DROP TABLE plastics_workspaces")
                    conn.execute("ALTER TABLE plastics_workspaces_v2 RENAME TO plastics_workspaces")
            else:
                conn.execute(
                    """
                    CREATE TABLE plastics_workspaces (
                        session_id TEXT NOT NULL DEFAULT 'local',
                        workspace_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        dataset_json TEXT NOT NULL,
                        config_json TEXT NOT NULL,
                        PRIMARY KEY (session_id, workspace_id)
                    )
                    """
                )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plastics_workspaces_updated "
                "ON plastics_workspaces (session_id, updated_at DESC)"
            )
            self._ensure_default_workspace(conn, DEFAULT_SESSION_ID)

    def _ensure_default_workspace(self, conn: sqlite3.Connection, session_id: str) -> None:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM plastics_workspaces WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row and row["cnt"] == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            ds_seed = demo_dataset()
            cfg_seed = default_config()
            conn.execute(
                """
                INSERT OR IGNORE INTO plastics_workspaces (
                    session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    "default",
                    ds_seed.name,
                    now_iso,
                    now_iso,
                    ds_seed.model_dump_json(),
                    cfg_seed.model_dump_json(),
                ),
            )

    def save_run(
        self,
        result: SolveResult,
        dataset: Optional[PlantDataset] = None,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> None:
        sc = result.scorecard
        cfg = result.audit.config
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO plastics_audit_runs (
                    run_id, session_id, created_at, dataset_name, currency, status, solve_time_ms,
                    inputs_sha256, schedule_sha256, ramadan_shift_mode, avoid_peak_tariff_hrs,
                    w_changeover_scrap, w_otif, w_energy_cost, w_working_capital,
                    cash_savings, cash_savings_pct, purge_scrap_kg_saved, changeover_hours_saved,
                    otif_pct, oee_pct, all_hard_constraints_passed, payload_json, dataset_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    session_id,
                    result.created_at,
                    result.dataset_name,
                    result.currency,
                    result.status,
                    result.solve_time_ms,
                    result.audit.inputs_sha256,
                    result.audit.schedule_sha256,
                    1 if cfg.ramadan_shift_mode else 0,
                    1 if cfg.avoid_peak_tariff_hrs else 0,
                    cfg.w_changeover_scrap,
                    cfg.w_otif,
                    cfg.w_energy_cost,
                    cfg.w_working_capital,
                    sc.cash_savings,
                    sc.cash_savings_pct,
                    sc.purge_scrap_kg_saved,
                    sc.changeover_hours_saved,
                    result.optimized.kpis.otif_pct,
                    result.optimized.kpis.oee_pct,
                    1 if result.audit.all_hard_constraints_passed else 0,
                    result.model_dump_json(),
                    dataset.model_dump_json() if dataset is not None else "{}",
                ),
            )

    def list_runs(self, limit: int = 50, session_id: str = DEFAULT_SESSION_ID) -> list[dict]:
        safe_limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    run_id, created_at, dataset_name, currency, status, solve_time_ms,
                    inputs_sha256, schedule_sha256, ramadan_shift_mode, avoid_peak_tariff_hrs,
                    w_changeover_scrap, w_otif, w_energy_cost, w_working_capital,
                    cash_savings, cash_savings_pct, purge_scrap_kg_saved, changeover_hours_saved,
                    otif_pct, oee_pct, all_hard_constraints_passed
                FROM plastics_audit_runs
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, safe_limit),
            ).fetchall()

        return [
            {
                "run_id": r["run_id"],
                "created_at": r["created_at"],
                "dataset_name": r["dataset_name"],
                "currency": r["currency"],
                "status": r["status"],
                "solve_time_ms": r["solve_time_ms"],
                "inputs_sha256": r["inputs_sha256"],
                "schedule_sha256": r["schedule_sha256"],
                "ramadan_shift_mode": bool(r["ramadan_shift_mode"]),
                "avoid_peak_tariff_hrs": bool(r["avoid_peak_tariff_hrs"]),
                "weights": {
                    "w_changeover_scrap": r["w_changeover_scrap"],
                    "w_otif": r["w_otif"],
                    "w_energy_cost": r["w_energy_cost"],
                    "w_working_capital": r["w_working_capital"],
                },
                "scorecard_summary": {
                    "cash_savings": r["cash_savings"],
                    "cash_savings_pct": r["cash_savings_pct"],
                    "purge_scrap_kg_saved": r["purge_scrap_kg_saved"],
                    "changeover_hours_saved": r["changeover_hours_saved"],
                    "otif_pct": r["otif_pct"],
                    "oee_pct": r["oee_pct"],
                },
                "all_hard_constraints_passed": bool(r["all_hard_constraints_passed"]),
            }
            for r in rows
        ]

    def get_run(self, run_id: str, session_id: Optional[str] = None) -> Optional[SolveResult]:
        with self._connect() as conn:
            if session_id is not None:
                row = conn.execute(
                    "SELECT payload_json FROM plastics_audit_runs WHERE run_id = ? AND session_id = ?",
                    (run_id, session_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT payload_json FROM plastics_audit_runs WHERE run_id = ?", (run_id,)
                ).fetchone()
        if row is None:
            return None
        return SolveResult.model_validate_json(row["payload_json"])

    def save_workspace(
        self,
        workspace_id: str,
        name: str,
        dataset: PlantDataset,
        config: Optional[SolverConfig] = None,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        dataset_json = dataset.model_dump_json()
        config_json = (config or default_config()).model_dump_json()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT created_at FROM plastics_workspaces WHERE session_id = ? AND workspace_id = ?",
                (session_id, workspace_id),
            ).fetchone()
            created_at = existing["created_at"] if existing else now_iso
            conn.execute(
                """
                INSERT OR REPLACE INTO plastics_workspaces (
                    session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, workspace_id, name, created_at, now_iso, dataset_json, config_json),
            )
        return {
            "workspace_id": workspace_id,
            "name": name,
            "created_at": created_at,
            "updated_at": now_iso,
            "dataset": json.loads(dataset_json),
            "config": json.loads(config_json),
        }

    def list_workspaces(self, session_id: str = DEFAULT_SESSION_ID) -> list[dict]:
        with self._connect() as conn:
            self._ensure_default_workspace(conn, session_id)
            rows = conn.execute(
                """
                SELECT workspace_id, name, created_at, updated_at
                FROM plastics_workspaces
                WHERE session_id = ?
                ORDER BY updated_at DESC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "workspace_id": r["workspace_id"],
                "name": r["name"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def get_workspace(
        self, workspace_id: str, session_id: str = DEFAULT_SESSION_ID
    ) -> Optional[dict]:
        with self._connect() as conn:
            if workspace_id == "default":
                self._ensure_default_workspace(conn, session_id)
            row = conn.execute(
                """
                SELECT workspace_id, name, created_at, updated_at, dataset_json, config_json
                FROM plastics_workspaces
                WHERE session_id = ? AND workspace_id = ?
                """,
                (session_id, workspace_id),
            ).fetchone()
        if row is None:
            return None
        dataset_obj = json.loads(row["dataset_json"])
        if row["workspace_id"] == "default" and "workers" not in dataset_obj:
            from .seed import demo_workers

            dataset_obj["workers"] = [w.model_dump(mode="json") for w in demo_workers()]
        return {
            "workspace_id": row["workspace_id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "dataset": dataset_obj,
            "config": json.loads(row["config_json"]),
        }

    def delete_workspace(
        self, workspace_id: str, session_id: str = DEFAULT_SESSION_ID
    ) -> bool:
        if workspace_id == "default":
            ds = demo_dataset()
            cfg = default_config()
            self.save_workspace("default", ds.name, ds, cfg, session_id=session_id)
            return True
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM plastics_workspaces WHERE session_id = ? AND workspace_id = ?",
                (session_id, workspace_id),
            )
            return cur.rowcount > 0

    def reset_session_sandbox(self, session_id: str = DEFAULT_SESSION_ID) -> dict:
        """Delete all custom workspaces for `session_id` and reset its `default` workspace to demo data."""
        ds = demo_dataset()
        cfg = default_config()
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM plastics_workspaces WHERE session_id = ?", (session_id,))
            conn.execute(
                """
                INSERT INTO plastics_workspaces (
                    session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    "default",
                    ds.name,
                    now_iso,
                    now_iso,
                    ds.model_dump_json(),
                    cfg.model_dump_json(),
                ),
            )
        return {
            "reset": True,
            "session_id": session_id,
            "dataset": ds.model_dump(mode="json"),
            "default_config": cfg.model_dump(mode="json"),
        }
