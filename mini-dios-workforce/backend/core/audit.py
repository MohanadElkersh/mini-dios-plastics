"""Dual-Mode Persistence Layer (PostgreSQL + SQLite Fallback) & Decision Checkpoint Store for Mini-DIOS Plastics.

Supports:
1. `DATABASE_URL` (PostgreSQL on Neon, Supabase, or Render Postgres):
   - Automatically normalizes `postgres://` -> `postgresql://`.
   - Enforces a Render Free-Tier safe connection pool (`pool_size=3`, `max_overflow=2`, `pool_pre_ping=True`).
2. Local SQLite Fallback (`data/mini_dios.db` or `DIOS_AUDIT_DB`):
   - Activated automatically when `DATABASE_URL` is unset or points to `sqlite:///`, so the app never crashes on startup.

Auto-migrated tables scoped by `sandbox_id` (`session_id`) and `access_code` (`client_label`):
- `plastics_audit_runs`: Cryptographic SHA-256 solver audit trail.
- `saved_workspaces` (and legacy mirror `plastics_workspaces`): Custom plant workspaces (full JSON state, name, currency, timestamps).
- `pinned_scenarios`: Boardroom A/B/C side-by-side comparison pins.
- `backtest_runs`: Saved 1-month Historical Backtest Replay summaries.
- `decision_checkpoints`: Immutable audit trail recording every applied Copilot simulation, CTP rush-order commit, or workspace checkpoint save.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .neon_services import load_neon_env
from .ontology import PlantDataset, SolveResult, SolverConfig
from .seed import default_config, demo_dataset

load_neon_env()

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mini_dios.db"
LEGACY_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "audit.db"
DEFAULT_SESSION_ID = "local"
DEFAULT_ACCESS_CODE = "Local Plant"

POOL_CONFIG = {
    "pool_size": 3,
    "max_overflow": 2,
    "pool_pre_ping": True,
}


def normalize_database_url(raw_url: Optional[str]) -> Optional[str]:
    """Normalize `postgres://` -> `postgresql://` and ensure SSL on remote cloud Postgres hosts."""
    if not raw_url:
        return None
    cleaned = raw_url.strip()
    if not cleaned:
        return None
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql://") or cleaned.startswith("postgresql+"):
        parsed = urlparse(cleaned)
        host = (parsed.hostname or "").lower()
        is_remote = host not in ("", "localhost", "127.0.0.1", "postgres", "db")
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if is_remote and "sslmode" not in query:
            query["sslmode"] = "require"
            cleaned = urlunparse(parsed._replace(query=urlencode(query)))
    return cleaned


class _DbSessionAdapter:
    """Uniform SQL execution wrapper abstracting SQLite (`?`) vs PostgreSQL (`%s` / SQLAlchemy)."""

    def __init__(self, conn: Any, is_postgres: bool, is_sqlalchemy: bool = False):
        self._conn = conn
        self.is_postgres = is_postgres
        self.is_sqlalchemy = is_sqlalchemy

    def _translate_sql(self, sql: str) -> str:
        if not self.is_postgres:
            return sql
        # Translate SQLite `?` placeholders to `%s` for DBAPI psycopg/psycopg2
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        if self.is_sqlalchemy:
            from sqlalchemy import text

            # Convert positional `?` to `:p0, :p1, ...` for SQLAlchemy text() binding
            parts = sql.split("?")
            if len(parts) == 1:
                return self._conn.execute(text(sql))
            rebuilt = []
            bind_dict: dict[str, Any] = {}
            for idx, part in enumerate(parts[:-1]):
                key = f"p{idx}"
                rebuilt.append(f"{part}:{key}")
                bind_dict[key] = params[idx]
            rebuilt.append(parts[-1])
            return self._conn.execute(text("".join(rebuilt)), bind_dict)
        translated = self._translate_sql(sql)
        cur = self._conn.cursor()
        cur.execute(translated, params)
        return cur

    def fetchall_dicts(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        res = self.execute(sql, params)
        if self.is_sqlalchemy:
            return [dict(row._mapping) for row in res.fetchall()]
        rows = res.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], sqlite3.Row) or isinstance(rows[0], dict):
            return [dict(r) for r in rows]
        cols = [col[0] for col in res.description]
        return [dict(zip(cols, r)) for r in rows]

    def fetchone_dict(self, sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
        rows = self.fetchall_dicts(sql, params)
        return rows[0] if rows else None


class AuditStore:
    """Thread-safe dual-mode (PostgreSQL / SQLite fallback) persistence store with per-sandbox isolation."""

    def __init__(self, db_path: Optional[str | Path] = None, database_url: Optional[str] = None):
        raw_env_url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
        # If an explicit db_path is passed (e.g. unit tests with tmp_path / ":memory:"), prefer SQLite on that path
        if db_path is not None:
            self.database_url: Optional[str] = None
        else:
            self.database_url = normalize_database_url(raw_env_url)

        self.storage_backend: Literal["postgres", "sqlite_fallback"] = "sqlite_fallback"
        self.pool_config = dict(POOL_CONFIG)
        self._sa_engine: Any = None

        env_sqlite = os.environ.get("DIOS_AUDIT_DB")
        if db_path is not None:
            resolved = Path(db_path)
        elif env_sqlite:
            resolved = Path(env_sqlite)
        elif LEGACY_DB_PATH.exists() and not DEFAULT_DB_PATH.exists():
            resolved = LEGACY_DB_PATH
        else:
            resolved = DEFAULT_DB_PATH

        self.db_path = resolved

        if self.database_url and self.database_url.startswith("postgresql"):
            if self._try_init_postgres(self.database_url):
                self.storage_backend = "postgres"
            else:
                self.storage_backend = "sqlite_fallback"

        if self.storage_backend == "sqlite_fallback":
            if str(self.db_path) != ":memory:":
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_schema()

    def _try_init_postgres(self, pg_url: str) -> bool:
        """Attempt to initialize a bounded PostgreSQL connection pool via SQLAlchemy (psycopg2 / psycopg)."""
        try:
            from sqlalchemy import create_engine, text

            sa_url = pg_url
            if sa_url.startswith("postgresql://"):
                try:
                    import psycopg  # noqa: F401
                except ImportError:
                    try:
                        import psycopg2  # noqa: F401

                        sa_url = "postgresql+psycopg2://" + sa_url[len("postgresql://") :]
                    except ImportError:
                        pass

            engine = create_engine(
                sa_url,
                pool_size=POOL_CONFIG["pool_size"],
                max_overflow=POOL_CONFIG["max_overflow"],
                pool_pre_ping=POOL_CONFIG["pool_pre_ping"],
                pool_timeout=10,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._sa_engine = engine
            return True
        except Exception as exc:
            print(
                f"[AuditStore] DATABASE_URL PostgreSQL init failed ({exc}); falling back cleanly to local SQLite at {self.db_path}.",
                flush=True,
            )
            self._sa_engine = None
            return False

    @contextmanager
    def _session(self) -> Iterator[_DbSessionAdapter]:
        if self.storage_backend == "postgres" and self._sa_engine is not None:
            with self._sa_engine.begin() as conn:
                yield _DbSessionAdapter(conn, is_postgres=True, is_sqlalchemy=True)
            return

        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield _DbSessionAdapter(conn, is_postgres=False, is_sqlalchemy=False)
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._session() as db:
            # 1. Solver Audit Runs
            db.execute(
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
            if not db.is_postgres:
                run_cols = {r["name"] for r in db.fetchall_dicts("PRAGMA table_info(plastics_audit_runs)")}
                if "session_id" not in run_cols:
                    db.execute("ALTER TABLE plastics_audit_runs ADD COLUMN session_id TEXT NOT NULL DEFAULT 'local'")

            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_plastics_audit_created ON plastics_audit_runs (created_at DESC)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_plastics_audit_session ON plastics_audit_runs (session_id, created_at DESC)"
            )

            # 2. Legacy plastics_workspaces table (for backward compatibility & migration)
            if not db.is_postgres:
                ws_exists = db.fetchone_dict(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='plastics_workspaces'"
                )
                if ws_exists:
                    ws_cols = {r["name"] for r in db.fetchall_dicts("PRAGMA table_info(plastics_workspaces)")}
                    if "session_id" not in ws_cols:
                        db.execute(
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
                        db.execute(
                            """
                            INSERT INTO plastics_workspaces_v2 (
                                session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json
                            )
                            SELECT 'local', workspace_id, name, created_at, updated_at, dataset_json, config_json
                            FROM plastics_workspaces
                            """
                        )
                        db.execute("DROP TABLE plastics_workspaces")
                        db.execute("ALTER TABLE plastics_workspaces_v2 RENAME TO plastics_workspaces")
                else:
                    db.execute(
                        """
                        CREATE TABLE IF NOT EXISTS plastics_workspaces (
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
            else:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS plastics_workspaces (
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

            # 3. v1.4 Canonical Table: saved_workspaces
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_workspaces (
                    sandbox_id TEXT NOT NULL DEFAULT 'local',
                    access_code TEXT NOT NULL DEFAULT 'Local Plant',
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'SAR',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    dataset_json TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    PRIMARY KEY (sandbox_id, workspace_id)
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_workspaces_updated "
                "ON saved_workspaces (sandbox_id, updated_at DESC)"
            )

            # Migrate any existing rows from plastics_workspaces -> saved_workspaces
            legacy_rows = db.fetchall_dicts(
                "SELECT session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json FROM plastics_workspaces"
            )
            for lr in legacy_rows:
                existing_sw = db.fetchone_dict(
                    "SELECT workspace_id FROM saved_workspaces WHERE sandbox_id = ? AND workspace_id = ?",
                    (lr["session_id"], lr["workspace_id"]),
                )
                if not existing_sw:
                    try:
                        cfg_obj = json.loads(lr["config_json"])
                        cur = cfg_obj.get("currency", "SAR")
                    except Exception:
                        cur = "SAR"
                    state_blob = json.dumps(
                        {
                            "workspace_id": lr["workspace_id"],
                            "name": lr["name"],
                            "dataset": json.loads(lr["dataset_json"]),
                            "config": json.loads(lr["config_json"]),
                        }
                    )
                    db.execute(
                        """
                        INSERT INTO saved_workspaces (
                            sandbox_id, access_code, workspace_id, name, currency,
                            created_at, updated_at, dataset_json, config_json, state_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            lr["session_id"],
                            DEFAULT_ACCESS_CODE,
                            lr["workspace_id"],
                            lr["name"],
                            cur,
                            lr["created_at"],
                            lr["updated_at"],
                            lr["dataset_json"],
                            lr["config_json"],
                            state_blob,
                        ),
                    )

            # 4. v1.4 Canonical Table: pinned_scenarios
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS pinned_scenarios (
                    sandbox_id TEXT NOT NULL DEFAULT 'local',
                    access_code TEXT NOT NULL DEFAULT 'Local Plant',
                    slot TEXT NOT NULL,
                    pin_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    dataset_json TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    PRIMARY KEY (sandbox_id, slot)
                )
                """
            )

            # 5. v1.4 Canonical Table: backtest_runs
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    run_id TEXT PRIMARY KEY,
                    sandbox_id TEXT NOT NULL DEFAULT 'local',
                    access_code TEXT NOT NULL DEFAULT 'Local Plant',
                    created_at TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    orders_analyzed INTEGER NOT NULL,
                    cash_left_1m REAL NOT NULL,
                    annualized_cash REAL NOT NULL,
                    payback_days INTEGER NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_backtest_runs_sandbox "
                "ON backtest_runs (sandbox_id, created_at DESC)"
            )

            # 6. v1.4 Canonical Table: decision_checkpoints
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_checkpoints (
                    id TEXT PRIMARY KEY,
                    sandbox_id TEXT NOT NULL DEFAULT 'local',
                    access_code TEXT NOT NULL DEFAULT 'Local Plant',
                    created_at TEXT NOT NULL,
                    trigger_source TEXT NOT NULL,
                    title_en TEXT NOT NULL,
                    title_ar TEXT NOT NULL,
                    risk_score INTEGER NOT NULL DEFAULT 0,
                    weekly_savings REAL NOT NULL DEFAULT 0.0,
                    otif_pct REAL NOT NULL DEFAULT 100.0,
                    currency TEXT NOT NULL DEFAULT 'SAR',
                    state_snapshot_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_decision_checkpoints_sandbox "
                "ON decision_checkpoints (sandbox_id, created_at DESC)"
            )

            self._ensure_default_workspace(db, DEFAULT_SESSION_ID, DEFAULT_ACCESS_CODE)

    def _ensure_default_workspace(
        self,
        db: _DbSessionAdapter,
        session_id: str,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> None:
        row = db.fetchone_dict(
            "SELECT COUNT(*) as cnt FROM saved_workspaces WHERE sandbox_id = ?",
            (session_id,),
        )
        cnt = int(row["cnt"]) if row and row.get("cnt") is not None else 0
        if cnt == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            ds_seed = demo_dataset()
            cfg_seed = default_config()
            ds_json = ds_seed.model_dump_json()
            cfg_json = cfg_seed.model_dump_json()
            state_json = json.dumps(
                {
                    "workspace_id": "default",
                    "name": ds_seed.name,
                    "dataset": json.loads(ds_json),
                    "config": json.loads(cfg_json),
                }
            )
            db.execute(
                """
                INSERT INTO saved_workspaces (
                    sandbox_id, access_code, workspace_id, name, currency,
                    created_at, updated_at, dataset_json, config_json, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    access_code,
                    "default",
                    ds_seed.name,
                    cfg_seed.currency,
                    now_iso,
                    now_iso,
                    ds_json,
                    cfg_json,
                    state_json,
                ),
            )
            # Keep legacy table synced
            existing_leg = db.fetchone_dict(
                "SELECT workspace_id FROM plastics_workspaces WHERE session_id = ? AND workspace_id = ?",
                (session_id, "default"),
            )
            if not existing_leg:
                db.execute(
                    """
                    INSERT INTO plastics_workspaces (
                        session_id, workspace_id, name, created_at, updated_at, dataset_json, config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, "default", ds_seed.name, now_iso, now_iso, ds_json, cfg_json),
                )

    def _upsert_row(
        self,
        db: _DbSessionAdapter,
        table: str,
        pk_cols: tuple[str, ...],
        col_names: tuple[str, ...],
        values: tuple[Any, ...],
    ) -> None:
        where_clause = " AND ".join(f"{c} = ?" for c in pk_cols)
        pk_vals = tuple(values[col_names.index(c)] for c in pk_cols)
        db.execute(f"DELETE FROM {table} WHERE {where_clause}", pk_vals)
        placeholders = ", ".join("?" for _ in col_names)
        cols_str = ", ".join(col_names)
        db.execute(f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})", values)

    # ----------------------------------------------------------------------------------------
    # Audit Runs
    # ----------------------------------------------------------------------------------------
    def save_run(
        self,
        result: SolveResult,
        dataset: Optional[PlantDataset] = None,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> None:
        sc = result.scorecard
        cfg = result.audit.config
        cols = (
            "run_id",
            "session_id",
            "created_at",
            "dataset_name",
            "currency",
            "status",
            "solve_time_ms",
            "inputs_sha256",
            "schedule_sha256",
            "ramadan_shift_mode",
            "avoid_peak_tariff_hrs",
            "w_changeover_scrap",
            "w_otif",
            "w_energy_cost",
            "w_working_capital",
            "cash_savings",
            "cash_savings_pct",
            "purge_scrap_kg_saved",
            "changeover_hours_saved",
            "otif_pct",
            "oee_pct",
            "all_hard_constraints_passed",
            "payload_json",
            "dataset_json",
        )
        vals = (
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
        )
        with self._session() as db:
            self._upsert_row(db, "plastics_audit_runs", ("run_id",), cols, vals)

    def list_runs(self, limit: int = 50, session_id: str = DEFAULT_SESSION_ID) -> list[dict]:
        safe_limit = max(1, min(limit, 500))
        with self._session() as db:
            rows = db.fetchall_dicts(
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
            )

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
        with self._session() as db:
            if session_id is not None:
                row = db.fetchone_dict(
                    "SELECT payload_json FROM plastics_audit_runs WHERE run_id = ? AND session_id = ?",
                    (run_id, session_id),
                )
            else:
                row = db.fetchone_dict(
                    "SELECT payload_json FROM plastics_audit_runs WHERE run_id = ?", (run_id,)
                )
        if row is None:
            return None
        return SolveResult.model_validate_json(row["payload_json"])

    # ----------------------------------------------------------------------------------------
    # Saved Workspaces (`saved_workspaces` + legacy mirror `plastics_workspaces`)
    # ----------------------------------------------------------------------------------------
    def save_workspace(
        self,
        workspace_id: str,
        name: str,
        dataset: PlantDataset,
        config: Optional[SolverConfig] = None,
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        eff_cfg = config or default_config()
        dataset_json = dataset.model_dump_json()
        config_json = eff_cfg.model_dump_json()
        dataset_dict = json.loads(dataset_json)
        config_dict = json.loads(config_json)
        state_json = json.dumps(
            {
                "workspace_id": workspace_id,
                "name": name,
                "dataset": dataset_dict,
                "config": config_dict,
            }
        )
        with self._session() as db:
            existing = db.fetchone_dict(
                "SELECT created_at FROM saved_workspaces WHERE sandbox_id = ? AND workspace_id = ?",
                (session_id, workspace_id),
            )
            created_at = existing["created_at"] if existing else now_iso
            self._upsert_row(
                db,
                "saved_workspaces",
                ("sandbox_id", "workspace_id"),
                (
                    "sandbox_id",
                    "access_code",
                    "workspace_id",
                    "name",
                    "currency",
                    "created_at",
                    "updated_at",
                    "dataset_json",
                    "config_json",
                    "state_json",
                ),
                (
                    session_id,
                    access_code,
                    workspace_id,
                    name,
                    eff_cfg.currency,
                    created_at,
                    now_iso,
                    dataset_json,
                    config_json,
                    state_json,
                ),
            )
            self._upsert_row(
                db,
                "plastics_workspaces",
                ("session_id", "workspace_id"),
                ("session_id", "workspace_id", "name", "created_at", "updated_at", "dataset_json", "config_json"),
                (session_id, workspace_id, name, created_at, now_iso, dataset_json, config_json),
            )
        return {
            "workspace_id": workspace_id,
            "name": name,
            "currency": eff_cfg.currency,
            "created_at": created_at,
            "updated_at": now_iso,
            "dataset": dataset_dict,
            "config": config_dict,
        }

    def list_workspaces(
        self,
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> list[dict]:
        with self._session() as db:
            self._ensure_default_workspace(db, session_id, access_code)
            rows = db.fetchall_dicts(
                """
                SELECT workspace_id, name, currency, created_at, updated_at
                FROM saved_workspaces
                WHERE sandbox_id = ?
                ORDER BY updated_at DESC
                """,
                (session_id,),
            )
        return [
            {
                "workspace_id": r["workspace_id"],
                "name": r["name"],
                "currency": r.get("currency", "SAR"),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def get_workspace(
        self,
        workspace_id: str,
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> Optional[dict]:
        with self._session() as db:
            if workspace_id == "default":
                self._ensure_default_workspace(db, session_id, access_code)
            row = db.fetchone_dict(
                """
                SELECT workspace_id, name, currency, created_at, updated_at, dataset_json, config_json
                FROM saved_workspaces
                WHERE sandbox_id = ? AND workspace_id = ?
                """,
                (session_id, workspace_id),
            )
        if row is None:
            return None
        dataset_obj = json.loads(row["dataset_json"])
        if row["workspace_id"] == "default" and "workers" not in dataset_obj:
            from .seed import demo_workers

            dataset_obj["workers"] = [w.model_dump(mode="json") for w in demo_workers()]
        return {
            "workspace_id": row["workspace_id"],
            "name": row["name"],
            "currency": row.get("currency", "SAR"),
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
        with self._session() as db:
            existed = db.fetchone_dict(
                "SELECT workspace_id FROM saved_workspaces WHERE sandbox_id = ? AND workspace_id = ?",
                (session_id, workspace_id),
            )
            db.execute(
                "DELETE FROM saved_workspaces WHERE sandbox_id = ? AND workspace_id = ?",
                (session_id, workspace_id),
            )
            db.execute(
                "DELETE FROM plastics_workspaces WHERE session_id = ? AND workspace_id = ?",
                (session_id, workspace_id),
            )
            return existed is not None

    # ----------------------------------------------------------------------------------------
    # Decision Checkpoints (`decision_checkpoints`)
    # ----------------------------------------------------------------------------------------
    def save_checkpoint(
        self,
        dataset: PlantDataset,
        config: SolverConfig,
        result: Optional[SolveResult] = None,
        trigger_source: str = "workspace_save",
        title_en: str = "Saved Plant Workspace Snapshot",
        title_ar: str = "حفظ نقطة مرجعية لمساحة عمل المصنع",
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
        checkpoint_id: Optional[str] = None,
    ) -> dict[str, Any]:
        cp_id = checkpoint_id or f"CP-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        risk_score = 0
        weekly_savings = 0.0
        otif_pct = 100.0
        currency = config.currency

        if result is not None:
            currency = result.currency
            otif_pct = round(float(result.optimized.kpis.otif_pct), 1)
            weekly_savings = round(float(result.financials.total_weekly_savings), 2)
            if result.risk_radar is not None:
                risk_score = int(result.risk_radar.overall_risk_score)

        snapshot_obj = {
            "dataset": dataset.model_dump(mode="json"),
            "config": config.model_dump(mode="json"),
            "run_id": result.run_id if result else None,
        }
        snapshot_json = json.dumps(snapshot_obj)

        cols = (
            "id",
            "sandbox_id",
            "access_code",
            "created_at",
            "trigger_source",
            "title_en",
            "title_ar",
            "risk_score",
            "weekly_savings",
            "otif_pct",
            "currency",
            "state_snapshot_json",
        )
        vals = (
            cp_id,
            session_id,
            access_code,
            now_iso,
            trigger_source,
            title_en,
            title_ar,
            risk_score,
            weekly_savings,
            otif_pct,
            currency,
            snapshot_json,
        )
        with self._session() as db:
            self._upsert_row(db, "decision_checkpoints", ("id",), cols, vals)

        return {
            "id": cp_id,
            "checkpoint_id": cp_id,
            "sandbox_id": session_id,
            "access_code": access_code,
            "created_at": now_iso,
            "trigger_source": trigger_source,
            "title_en": title_en,
            "title_ar": title_ar,
            "risk_score": risk_score,
            "weekly_savings": weekly_savings,
            "otif_pct": otif_pct,
            "currency": currency,
            "orders_count": len(dataset.orders),
            "workers_count": len(dataset.workers),
        }

    def list_checkpoints(
        self,
        session_id: str = DEFAULT_SESSION_ID,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with self._session() as db:
            rows = db.fetchall_dicts(
                """
                SELECT
                    id, sandbox_id, access_code, created_at, trigger_source,
                    title_en, title_ar, risk_score, weekly_savings, otif_pct, currency,
                    state_snapshot_json
                FROM decision_checkpoints
                WHERE sandbox_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, safe_limit),
            )
        out: list[dict[str, Any]] = []
        for r in rows:
            orders_cnt = 0
            workers_cnt = 0
            try:
                snap = json.loads(r["state_snapshot_json"])
                ds_raw = snap.get("dataset") or {}
                orders_cnt = len(ds_raw.get("orders") or [])
                workers_cnt = len(ds_raw.get("workers") or [])
            except Exception:
                pass
            out.append(
                {
                    "id": r["id"],
                    "checkpoint_id": r["id"],
                    "sandbox_id": r["sandbox_id"],
                    "access_code": r["access_code"],
                    "created_at": r["created_at"],
                    "trigger_source": r["trigger_source"],
                    "title_en": r["title_en"],
                    "title_ar": r["title_ar"],
                    "risk_score": int(r["risk_score"]),
                    "weekly_savings": float(r["weekly_savings"]),
                    "otif_pct": float(r["otif_pct"]),
                    "currency": r.get("currency", "SAR"),
                    "orders_count": orders_cnt,
                    "workers_count": workers_cnt,
                }
            )
        return out

    def get_checkpoint(
        self,
        checkpoint_id: str,
        session_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        with self._session() as db:
            if session_id is not None:
                row = db.fetchone_dict(
                    "SELECT * FROM decision_checkpoints WHERE id = ? AND sandbox_id = ?",
                    (checkpoint_id, session_id),
                )
            else:
                row = db.fetchone_dict(
                    "SELECT * FROM decision_checkpoints WHERE id = ?",
                    (checkpoint_id,),
                )
        if row is None:
            return None
        snapshot = json.loads(row["state_snapshot_json"])
        return {
            "id": row["id"],
            "checkpoint_id": row["id"],
            "sandbox_id": row["sandbox_id"],
            "access_code": row["access_code"],
            "created_at": row["created_at"],
            "trigger_source": row["trigger_source"],
            "title_en": row["title_en"],
            "title_ar": row["title_ar"],
            "risk_score": int(row["risk_score"]),
            "weekly_savings": float(row["weekly_savings"]),
            "otif_pct": float(row["otif_pct"]),
            "currency": row.get("currency", "SAR"),
            "state_snapshot": snapshot,
        }

    # ----------------------------------------------------------------------------------------
    # Pinned Scenarios (`pinned_scenarios`) & Backtest Runs (`backtest_runs`)
    # ----------------------------------------------------------------------------------------
    def save_pinned_scenario(
        self,
        slot: str,
        pin_id: str,
        label: str,
        dataset: PlantDataset,
        config: SolverConfig,
        result: SolveResult,
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._session() as db:
            self._upsert_row(
                db,
                "pinned_scenarios",
                ("sandbox_id", "slot"),
                (
                    "sandbox_id",
                    "access_code",
                    "slot",
                    "pin_id",
                    "label",
                    "created_at",
                    "dataset_json",
                    "config_json",
                    "result_json",
                ),
                (
                    session_id,
                    access_code,
                    slot,
                    pin_id,
                    label,
                    now_iso,
                    dataset.model_dump_json(),
                    config.model_dump_json(),
                    result.model_dump_json(),
                ),
            )
        return {"slot": slot, "pin_id": pin_id, "label": label, "created_at": now_iso}

    def list_pinned_scenarios(self, session_id: str = DEFAULT_SESSION_ID) -> list[dict[str, Any]]:
        with self._session() as db:
            rows = db.fetchall_dicts(
                "SELECT * FROM pinned_scenarios WHERE sandbox_id = ? ORDER BY slot ASC",
                (session_id,),
            )
        return [
            {
                "id": r["pin_id"],
                "slot": r["slot"],
                "label": r["label"],
                "createdAt": r["created_at"],
                "dataset": json.loads(r["dataset_json"]),
                "solverConfig": json.loads(r["config_json"]),
                "result": json.loads(r["result_json"]),
            }
            for r in rows
        ]

    def save_backtest_run(
        self,
        report: Any,
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> dict[str, Any]:
        run_id = f"BT-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        rep_dict = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
        d = rep_dict.get("actual_vs_optimized") or {}
        with self._session() as db:
            self._upsert_row(
                db,
                "backtest_runs",
                ("run_id",),
                (
                    "run_id",
                    "sandbox_id",
                    "access_code",
                    "created_at",
                    "source_label",
                    "currency",
                    "orders_analyzed",
                    "cash_left_1m",
                    "annualized_cash",
                    "payback_days",
                    "report_json",
                ),
                (
                    run_id,
                    session_id,
                    access_code,
                    now_iso,
                    str(rep_dict.get("source_label", "sample_30day_log")),
                    str(rep_dict.get("currency", "SAR")),
                    int(rep_dict.get("orders_analyzed", 0)),
                    float(d.get("total_cash_left_on_floor_1month", 0.0)),
                    float(d.get("annualized_cash_left_on_floor", 0.0)),
                    int(d.get("estimated_payback_days", 0)),
                    json.dumps(rep_dict),
                ),
            )
        return {"run_id": run_id, "created_at": now_iso}

    def list_backtest_runs(self, session_id: str = DEFAULT_SESSION_ID, limit: int = 10) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 50))
        with self._session() as db:
            rows = db.fetchall_dicts(
                """
                SELECT run_id, sandbox_id, access_code, created_at, source_label,
                       currency, orders_analyzed, cash_left_1m, annualized_cash, payback_days
                FROM backtest_runs
                WHERE sandbox_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, safe_limit),
            )
        return rows

    def reset_session_sandbox(
        self,
        session_id: str = DEFAULT_SESSION_ID,
        access_code: str = DEFAULT_ACCESS_CODE,
    ) -> dict:
        """Delete all custom workspaces, pins, and checkpoints for `session_id` and reset `default` workspace."""
        ds = demo_dataset()
        cfg = default_config()
        now_iso = datetime.now(timezone.utc).isoformat()
        ds_json = ds.model_dump_json()
        cfg_json = cfg.model_dump_json()
        state_json = json.dumps(
            {
                "workspace_id": "default",
                "name": ds.name,
                "dataset": json.loads(ds_json),
                "config": json.loads(cfg_json),
            }
        )
        with self._session() as db:
            db.execute("DELETE FROM saved_workspaces WHERE sandbox_id = ?", (session_id,))
            db.execute("DELETE FROM plastics_workspaces WHERE session_id = ?", (session_id,))
            db.execute("DELETE FROM pinned_scenarios WHERE sandbox_id = ?", (session_id,))
            db.execute("DELETE FROM decision_checkpoints WHERE sandbox_id = ?", (session_id,))
            db.execute(
                """
                INSERT INTO saved_workspaces (
                    sandbox_id, access_code, workspace_id, name, currency,
                    created_at, updated_at, dataset_json, config_json, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    access_code,
                    "default",
                    ds.name,
                    cfg.currency,
                    now_iso,
                    now_iso,
                    ds_json,
                    cfg_json,
                    state_json,
                ),
            )
            db.execute(
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
                    ds_json,
                    cfg_json,
                ),
            )
        return {
            "reset": True,
            "session_id": session_id,
            "dataset": ds.model_dump(mode="json"),
            "default_config": cfg.model_dump(mode="json"),
        }

    def probe_database(self) -> dict[str, Any]:
        """Execute a live diagnostic query against the active database (Neon Postgres or SQLite fallback)."""
        unpooled_raw = os.environ.get("DATABASE_URL_UNPOOLED", "").strip()
        with self._session() as db:
            ws_row = db.fetchone_dict("SELECT COUNT(*) AS cnt FROM saved_workspaces")
            cp_row = db.fetchone_dict("SELECT COUNT(*) AS cnt FROM decision_checkpoints")
            ws_cnt = int(ws_row["cnt"]) if ws_row and ws_row.get("cnt") is not None else 0
            cp_cnt = int(cp_row["cnt"]) if cp_row and cp_row.get("cnt") is not None else 0
            if db.is_postgres:
                meta = db.fetchone_dict(
                    "SELECT current_database() AS db_name, current_user AS db_user, version() AS db_version"
                ) or {}
                return {
                    "configured": True,
                    "ok": True,
                    "storage_backend": self.storage_backend,
                    "database_name": meta.get("db_name", "neondb"),
                    "current_user": meta.get("db_user", "neondb_owner"),
                    "server_version": str(meta.get("db_version", ""))[:80],
                    "unpooled_url_configured": bool(unpooled_raw),
                    "pool_config": self.pool_config,
                    "saved_workspaces_count": ws_cnt,
                    "decision_checkpoints_count": cp_cnt,
                }
            return {
                "configured": False,
                "ok": True,
                "storage_backend": self.storage_backend,
                "database_name": str(self.db_path.name),
                "unpooled_url_configured": bool(unpooled_raw),
                "saved_workspaces_count": ws_cnt,
                "decision_checkpoints_count": cp_cnt,
            }
