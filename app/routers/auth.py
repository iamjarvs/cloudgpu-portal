"""Customer self-service session login.

This is the login the demo audience sees: signing in as the fake tenant
(e.g. "HackMeCorp"), not as an admin. Completely separate credential pair
and mechanism from the /ops operator Basic-Auth surface — see app/ops/router.py.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import settings_store
from app.security import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_LOGIN_WINDOW_SECONDS = 300
_LOGIN_MAX_ATTEMPTS = 10
_login_attempts: dict[str, list[float]] = defaultdict(list)


class LoginRequest(BaseModel):
    username: str
    password: str


def _rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    attempts = _login_attempts[client_ip]
    attempts[:] = [t for t in attempts if now - t < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        return True
    attempts.append(now)
    return False


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts — try again in a few minutes.")

    settings = settings_store.get_settings()
    if payload.username != settings.customer_username or not verify_password(
        payload.password, settings.customer_password_hash
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    request.session["authenticated"] = True
    return {"ok": True}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    settings = settings_store.get_settings()
    return {
        "tenant_display_name": settings.tenant_display_name,
        "logged_in": bool(request.session.get("authenticated")),
    }
