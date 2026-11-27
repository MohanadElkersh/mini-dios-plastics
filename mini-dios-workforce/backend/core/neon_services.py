"""Neon Cloud Platform Integrations for Mini-DIOS Plastics.

Wires all 5 Neon services provisioned via `neon.ts` and `.env.local`:
1. Neon Postgres (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`)
2. Neon Auth (`NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`)
3. Neon AI Gateway (`NEON_AI_GATEWAY_BASE_URL`, `NEON_AI_GATEWAY_TOKEN`)
4. Neon Functions (`NEON_BRANCH`, `NEON_BRANCH_ID`, `NEON_FUNCTION_HOST_SUFFIX`)
5. Neon Realtime (`NEON_REALTIME_URL`, `NEON_REALTIME_SECRET`)
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFORCE_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent.parent

_ENV_LOADED = False
_JWKS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "keys": []}


def load_neon_env() -> None:
    """Load `.env.local` and `.env` from repository root, workforce root, and backend root."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    candidates = [
        REPO_ROOT / ".env.local",
        REPO_ROOT / ".env",
        WORKFORCE_ROOT / ".env.local",
        WORKFORCE_ROOT / ".env",
        BACKEND_ROOT / ".env.local",
        BACKEND_ROOT / ".env",
    ]
    for env_file in candidates:
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
    _ENV_LOADED = True


def derive_database_name(database_url: Optional[str] = None) -> str:
    """Derive the Postgres database name from `DATABASE_URL` (recommended by `@neon/env` for Realtime)."""
    load_neon_env()
    raw = (database_url or os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        return "neondb"
    try:
        parsed = urlparse(raw)
        db_name = (parsed.path or "").lstrip("/")
        return db_name or "neondb"
    except Exception:
        return "neondb"


def get_neon_function_url(slug: str = "hello") -> Optional[str]:
    """Construct the deployed Neon Function URL matching `@neon/env`'s `functionBaseUrl(slug)`."""
    load_neon_env()
    branch_id = os.environ.get("NEON_BRANCH_ID", "").strip()
    host_suffix = os.environ.get("NEON_FUNCTION_HOST_SUFFIX", "").strip()
    if not branch_id or not host_suffix:
        return None
    clean_slug = slug.strip().lower()
    return f"https://{branch_id}-{clean_slug}{host_suffix}"


def invoke_neon_function(slug: str = "hello", path: str = "/", timeout_s: float = 8.0) -> dict[str, Any]:
    """Invoke a deployed Neon Function over HTTPS and return status + response body."""
    base_url = get_neon_function_url(slug)
    if not base_url:
        return {
            "configured": False,
            "ok": False,
            "slug": slug,
            "error": "NEON_BRANCH_ID or NEON_FUNCTION_HOST_SUFFIX is not set.",
        }
    clean_path = path if path.startswith("/") else f"/{path}"
    target_url = f"{base_url.rstrip('/')}{clean_path}"
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(target_url)
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))
        return {
            "configured": True,
            "ok": resp.status_code == 200,
            "slug": slug,
            "url": target_url,
            "status_code": resp.status_code,
            "body": resp.text,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))
        return {
            "configured": True,
            "ok": False,
            "slug": slug,
            "url": target_url,
            "error": str(exc),
            "latency_ms": latency_ms,
        }


def fetch_neon_auth_jwks(timeout_s: float = 6.0, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch and cache the Neon Auth JWKS keys from `NEON_AUTH_JWKS_URL`."""
    load_neon_env()
    base_url = os.environ.get("NEON_AUTH_BASE_URL", "").strip()
    jwks_url = os.environ.get("NEON_AUTH_JWKS_URL", "").strip()
    if not jwks_url:
        return {
            "configured": False,
            "ok": False,
            "error": "NEON_AUTH_JWKS_URL is not set.",
        }
    now = time.time()
    if not force_refresh and _JWKS_CACHE["keys"] and (now - _JWKS_CACHE["fetched_at"] < 300):
        return {
            "configured": True,
            "ok": True,
            "base_url": base_url,
            "jwks_url": jwks_url,
            "keys_count": len(_JWKS_CACHE["keys"]),
            "keys": _JWKS_CACHE["keys"],
            "cached": True,
        }
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(jwks_url)
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))
        data = resp.json() if resp.status_code == 200 else {}
        keys = data.get("keys", []) if isinstance(data, dict) else []
        if resp.status_code == 200:
            _JWKS_CACHE["fetched_at"] = now
            _JWKS_CACHE["keys"] = keys
        return {
            "configured": True,
            "ok": resp.status_code == 200,
            "base_url": base_url,
            "jwks_url": jwks_url,
            "status_code": resp.status_code,
            "keys_count": len(keys),
            "key_ids": [k.get("kid") for k in keys if isinstance(k, dict) and k.get("kid")],
            "latency_ms": latency_ms,
            "cached": False,
        }
    except Exception as exc:
        return {
            "configured": True,
            "ok": False,
            "base_url": base_url,
            "jwks_url": jwks_url,
            "error": str(exc),
        }


def verify_neon_auth_jwt(token: str) -> Optional[dict[str, Any]]:
    """Verify a Neon Auth JWT bearer token against `NEON_AUTH_JWKS_URL`."""
    load_neon_env()
    jwks_url = os.environ.get("NEON_AUTH_JWKS_URL", "").strip()
    if not token or not jwks_url:
        return None
    try:
        import jwt
        from jwt import PyJWKClient

        jwk_client = PyJWKClient(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            options={"verify_aud": False},
        )
        sub = str(claims.get("sub") or claims.get("id") or "").strip()
        if not sub:
            return None
        email = str(claims.get("email") or claims.get("name") or "Neon Auth User").strip()
        sid_hash = hashlib.sha256(sub.encode("utf-8")).hexdigest()[:16]
        return {
            "session_id": f"neon_{sid_hash}",
            "client_label": email,
            "claims": claims,
        }
    except Exception:
        return None


def probe_neon_ai_gateway(timeout_s: float = 8.0) -> dict[str, Any]:
    """Probe the Neon AI Gateway (`NEON_AI_GATEWAY_BASE_URL`) using `NEON_AI_GATEWAY_TOKEN`."""
    load_neon_env()
    base_url = os.environ.get("NEON_AI_GATEWAY_BASE_URL", "").strip().rstrip("/")
    token = os.environ.get("NEON_AI_GATEWAY_TOKEN", "").strip()
    if not base_url or not token:
        return {
            "configured": False,
            "ok": False,
            "error": "NEON_AI_GATEWAY_BASE_URL or NEON_AI_GATEWAY_TOKEN is not set.",
        }
    models_url = f"{base_url}/v1/models"
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(
                models_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))
        body_data: Any = None
        try:
            body_data = resp.json()
        except Exception:
            body_data = resp.text[:300]

        models_list: list[str] = []
        if isinstance(body_data, dict) and isinstance(body_data.get("data"), list):
            models_list = [
                str(m.get("id")) for m in body_data["data"] if isinstance(m, dict) and m.get("id")
            ]

        credits_available = resp.status_code == 200 and len(models_list) > 0
        return {
            "configured": True,
            "reachable": True,
            "authenticated": resp.status_code != 401,
            "ok": resp.status_code in (200, 402, 403, 404),
            "credits_available": credits_available,
            "base_url": base_url,
            "endpoint_tested": models_url,
            "status_code": resp.status_code,
            "models_count": len(models_list),
            "models": models_list[:10],
            "gateway_response": body_data,
            "fallback_mode": "gemini_or_deterministic_cpsat" if not credits_available else "neon_ai_gateway",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))
        return {
            "configured": True,
            "reachable": False,
            "ok": False,
            "base_url": base_url,
            "endpoint_tested": models_url,
            "error": str(exc),
            "latency_ms": latency_ms,
        }


def call_neon_ai_gateway_narration(
    system_prompt: str,
    user_prompt: str,
    model: str = "openai/gpt-4o-mini",
    timeout_s: float = 8.0,
) -> Optional[str]:
    """Call Neon AI Gateway OpenAI-compatible chat completions endpoint to narrate deterministic CP-SAT output."""
    load_neon_env()
    base_url = os.environ.get("NEON_AI_GATEWAY_BASE_URL", "").strip().rstrip("/")
    token = os.environ.get("NEON_AI_GATEWAY_TOKEN", "").strip()
    if not base_url or not token:
        return None
    chat_url = f"{base_url}/openai/v1/chat/completions"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                chat_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
        if resp.status_code != 200:
            return None
        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            return None
        text = str((choices[0].get("message") or {}).get("content") or "").strip()
        return text or None
    except Exception:
        return None


def get_neon_realtime_config_status() -> dict[str, Any]:
    """Inspect Neon Realtime env configuration (`NEON_REALTIME_URL`, `NEON_REALTIME_SECRET`, `db`)."""
    load_neon_env()
    rt_url = os.environ.get("NEON_REALTIME_URL", "").strip()
    rt_secret = os.environ.get("NEON_REALTIME_SECRET", "").strip()
    db_name = derive_database_name()
    configured = bool(rt_url and rt_secret)
    return {
        "configured": configured,
        "ok": configured,
        "realtime_url": rt_url or None,
        "database": db_name,
        "secret_configured": bool(rt_secret),
        "nextjs_live_query_endpoint": "/api/neon/realtime",
    }
