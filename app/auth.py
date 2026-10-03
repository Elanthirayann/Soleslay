"""
Admin authentication: password hashing, server-side sessions, CSRF
protection and login rate-limiting.

Design notes
------------
* Passwords are hashed with bcrypt (via passlib) — never stored in
  plaintext, never logged.
* Sessions are server-side (AdminSession rows). The cookie carries only an
  opaque random token; no user data lives client-side, and logout deletes
  the row so the cookie is immediately dead everywhere.
* CSRF: each session gets its own random csrf_token at login. All
  state-changing admin forms embed it as a hidden field; we compare it
  with hmac.compare_digest before accepting POST/PUT/DELETE.
* Rate limiting is in-memory + DB-logged. It is process-local, which is
  fine for a single-instance deployment (the norm for a store this size).
  If this is ever deployed behind multiple worker processes/instances,
  swap `_FAILURE_CACHE` for a shared store (e.g. Redis).
"""
import hmac
import os
import time
from datetime import timedelta
from typing import Optional

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import get_db, session_scope
from .models_db import AdminSession, AdminUser, LoginAttempt, utcnow

SESSION_COOKIE_NAME = "soleslay_admin_session"
SESSION_LIFETIME_HOURS = 12

# Is this process serving traffic over HTTPS? Set FORCE_HTTPS=1 in
# production. Cookies are only marked `secure` when true, since a `secure`
# cookie is silently dropped by browsers over plain HTTP (e.g. local dev).
FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "0") == "1"

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60

# ip_address -> list[timestamp] of recent failed attempts
_FAILURE_CACHE: dict[str, list[float]] = {}


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(raw_password: str) -> str:
    # bcrypt has a 72-byte input limit; enforced at create_admin.py's
    # minimum-length check being well under that, so this never silently
    # drops meaningful entropy for realistic passwords.
    return bcrypt.hashpw(raw_password.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8")[:72], password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str:
    # Trust X-Forwarded-For only if you control/trust the upstream proxy.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def is_rate_limited(request: Request) -> bool:
    ip = _client_ip(request)
    now = time.time()
    attempts = [t for t in _FAILURE_CACHE.get(ip, []) if now - t < LOCKOUT_WINDOW_SECONDS]
    _FAILURE_CACHE[ip] = attempts
    return len(attempts) >= MAX_FAILED_ATTEMPTS


def record_login_attempt(request: Request, db: Session, username: str, success: bool) -> None:
    ip = _client_ip(request)
    if not success:
        _FAILURE_CACHE.setdefault(ip, []).append(time.time())
    else:
        _FAILURE_CACHE.pop(ip, None)
    db.add(LoginAttempt(ip_address=ip, username=username[:64], success=success))
    # Best-effort prune of old rows so this table doesn't grow forever.
    cutoff = utcnow() - timedelta(days=7)
    db.query(LoginAttempt).filter(LoginAttempt.created_at < cutoff).delete()
    db.commit()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session(db: Session, user: AdminUser, request: Request) -> AdminSession:
    session = AdminSession(
        user_id=user.id,
        expires_at=AdminSession.new_expiry(SESSION_LIFETIME_HOURS),
        ip_address=_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(session)
    user.last_login_at = utcnow()
    db.commit()
    db.refresh(session)
    return session


def destroy_session(db: Session, token: Optional[str]) -> None:
    if not token:
        return
    db.query(AdminSession).filter(AdminSession.token == token).delete()
    db.commit()


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=FORCE_HTTPS,
        samesite="lax",
        max_age=SESSION_LIFETIME_HOURS * 3600,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Optional[AdminSession]:
    if not token:
        return None
    session = db.query(AdminSession).filter(AdminSession.token == token).first()
    if not session:
        return None
    if session.expires_at.replace(tzinfo=None) < utcnow().replace(tzinfo=None):
        db.delete(session)
        db.commit()
        return None
    return session


def require_admin(
    request: Request,
    session: Optional[AdminSession] = Depends(get_current_session),
) -> AdminSession:
    """FastAPI dependency: protects every admin route except /admin/login."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    request.state.admin_session = session
    return session


def verify_csrf(request: Request, session: AdminSession, submitted_token: Optional[str]) -> None:
    if not submitted_token or not hmac.compare_digest(submitted_token, session.csrf_token):
        raise HTTPException(status_code=400, detail="Invalid or missing CSRF token. Please retry.")
