"""Lightweight HMAC-SHA256 session authentication, rate limiting, and Copilot quota shield.

Designed for shareable hosted demos of Mini-DIOS Plastics:
- `AUTH_ENABLED=false` (default): local frictionless mode (`start.bat`, `pytest`).
- `AUTH_ENABLED=true`: protects all operational `/api/*` endpoints behind an `HttpOnly`
  HMAC-SHA256 signed session cookie (`dios_session`).
- Per-IP sliding-window brute-force rate limiting on `POST /api/auth/login`.
- Per-session hourly sliding-window quota shield (`COPILOT_MAX_LIVE_CALLS_PER_HOUR`)
  protecting live Gemini API calls with automatic fallback to deterministic offline CP-SAT.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel

SESSION_COOKIE_NAME = "dios_session"
SESSION_TTL_SECONDS = 60 * 60 * 24  # 24 hours
LOGIN_WINDOW_SECONDS = 60 * 5  # 5 minutes
LOGIN_MAX_FAILURES = 10
COPILOT_WINDOW_SECONDS = 60 * 60  # 1 hour

_EPHEMERAL_FALLBACK_SECRET = secrets.token_hex(32)
_lock = threading.Lock()
_login_failures: dict[str, deque[float]] = defaultdict(deque)
_copilot_calls: dict[str, deque[float]] = defaultdict(deque)


class AuthSession(BaseModel):
    session_id: str
    client_label: str
    authenticated: bool = True
    auth_enabled: bool = False


def is_auth_enabled() -> bool:
    return os.environ.get("AUTH_ENABLED", "false").strip().lower() in ("true", "1", "yes")


def is_instant_demo_enabled() -> bool:
    return os.environ.get("ALLOW_INSTANT_DEMO", "false").strip().lower() in ("true", "1", "yes")


def get_auth_secret() -> str:
    secret = os.environ.get("AUTH_SECRET_KEY", "").strip()
    return secret if secret else _EPHEMERAL_FALLBACK_SECRET


def get_copilot_hourly_limit() -> int:
    raw = os.environ.get("COPILOT_MAX_LIVE_CALLS_PER_HOUR", "15").strip()
    try:
        val = int(raw)
        return max(0, val)
    except ValueError:
        return 15


def parse_access_codes() -> dict[str, str]:
    """Return mapping of `{passcode: client_label}` from `DEMO_ACCESS_CODES` and `ADMIN_PASSWORD`."""
    mapping: dict[str, str] = {}
    raw_codes = os.environ.get("DEMO_ACCESS_CODES", "").strip()
    if raw_codes:
        for entry in raw_codes.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                label, code = entry.split(":", 1)
                label = label.strip() or "Executive Demo"
                code = code.strip()
                if code:
                    mapping[code] = label
            else:
                mapping[entry] = "Executive Demo"

    admin_pw = os.environ.get("ADMIN_PASSWORD", "").strip()
    if admin_pw:
        mapping[admin_pw] = "Admin"

    return mapping


def verify_passcode(passcode: str) -> Optional[str]:
    """Constant-time lookup of passcode against configured access codes. Returns client_label or None."""
    candidate = (passcode or "").strip()
    if not candidate:
        return None
    codes = parse_access_codes()
    matched_label: Optional[str] = None
    for valid_code, label in codes.items():
        if hmac.compare_digest(candidate.encode("utf-8"), valid_code.encode("utf-8")):
            matched_label = label
    return matched_label


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def sign_session_token(session_id: str, client_label: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    now = int(time.time())
    payload = {
        "sid": session_id,
        "lbl": client_label,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = hmac.new(get_auth_secret().encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: Optional[str]) -> Optional[AuthSession]:
    if not token or "." not in token:
        return None
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    payload_b64, sig_b64 = parts
    expected_sig = hmac.new(
        get_auth_secret().encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(actual_sig, expected_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        sid = str(payload.get("sid", "")).strip()
        lbl = str(payload.get("lbl", "Executive Demo")).strip() or "Executive Demo"
        if not sid:
            return None
        return AuthSession(
            session_id=sid,
            client_label=lbl,
            authenticated=True,
            auth_enabled=is_auth_enabled(),
        )
    except Exception:
        return None


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").lower()
    force_secure = os.environ.get("COOKIE_SECURE", "").strip().lower() in ("true", "1", "yes")
    is_secure = force_secure or request.url.scheme == "https" or forwarded_proto == "https"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/", samesite="lax")


def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_login_rate_limit(ip: str) -> None:
    now = time.time()
    with _lock:
        dq = _login_failures[ip]
        while dq and now - dq[0] > LOGIN_WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= LOGIN_MAX_FAILURES:
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Please wait a few minutes and try again.",
            )


def record_login_failure(ip: str) -> None:
    now = time.time()
    with _lock:
        dq = _login_failures[ip]
        while dq and now - dq[0] > LOGIN_WINDOW_SECONDS:
            dq.popleft()
        dq.append(now)


def clear_login_failures(ip: str) -> None:
    with _lock:
        _login_failures.pop(ip, None)


def consume_copilot_live_quota(session_id: str) -> tuple[bool, int, int]:
    """Check and consume 1 live Gemini Copilot call for `session_id`.

    Returns `(allowed, used_in_window, limit)`.
    """
    limit = get_copilot_hourly_limit()
    if limit <= 0:
        return False, 0, 0
    now = time.time()
    with _lock:
        dq = _copilot_calls[session_id]
        while dq and now - dq[0] > COPILOT_WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= limit:
            return False, len(dq), limit
        dq.append(now)
        return True, len(dq), limit


def reset_auth_runtime_state() -> None:
    """Clear in-memory rate-limit and quota counters (for tests)."""
    with _lock:
        _login_failures.clear()
        _copilot_calls.clear()


def get_optional_session(request: Request) -> Optional[AuthSession]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    sess = verify_session_token(token)
    if sess is not None:
        return sess
    # Also support Neon Auth JWT Bearer tokens verified against NEON_AUTH_JWKS_URL
    auth_header = (request.headers.get("authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()
        if bearer_token:
            from .neon_services import verify_neon_auth_jwt

            neon_claims = verify_neon_auth_jwt(bearer_token)
            if neon_claims is not None:
                return AuthSession(
                    session_id=neon_claims["session_id"],
                    client_label=neon_claims["client_label"],
                    authenticated=True,
                    auth_enabled=is_auth_enabled(),
                )
    return None


def require_auth_session(request: Request) -> AuthSession:
    """FastAPI dependency protecting operational `/api/*` endpoints when `AUTH_ENABLED=true`."""
    if not is_auth_enabled():
        return AuthSession(
            session_id="local",
            client_label="Local Plant",
            authenticated=True,
            auth_enabled=False,
        )
    session = get_optional_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in with an access code.")
    return session


def new_session_id() -> str:
    return f"sess_{secrets.token_hex(12)}"
