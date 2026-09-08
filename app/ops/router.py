"""Operator-only surface: Netris connection + demo-tuning settings, and a
reference docs page. Deliberately NOT part of the React app or its router —
a separate, unlinked route prefix gated by HTTP Basic Auth against a
credential pair that has nothing to do with the customer session login (see
app/routers/auth.py). Even a customer session cookie cannot reach this.
"""
from __future__ import annotations

import secrets as secrets_module
from pathlib import Path

import asyncssh
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import settings_store
from app.security import constant_time_eq, verify_password
from app.ssh_client import resolve_aliases

router = APIRouter(prefix="/ops", tags=["ops"])

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
_basic = HTTPBasic()


def require_operator(credentials: HTTPBasicCredentials = Depends(_basic)) -> None:
    settings = settings_store.get_settings()
    valid_user = constant_time_eq(credentials.username, settings.operator_username)
    valid_pass = verify_password(credentials.password, settings.operator_password_hash)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


class SettingsUpdate(BaseModel):
    netris_base_url: str | None = None
    netris_username: str | None = None
    netris_password: str | None = None
    netris_site_id: int | None = None
    netris_site_name: str | None = None
    netris_template_id: int | None = None
    netris_template_name: str | None = None
    netris_verify_ssl: bool | None = None
    ssh_jump_host: str | None = None
    ssh_jump_port: int | None = None
    ssh_jump_username: str | None = None
    ssh_jump_password: str | None = None
    demo_app_port: int | None = None
    gpus_per_server: int | None = None
    max_servers_per_request: int | None = None
    tenant_display_name: str | None = None
    customer_username: str | None = None
    customer_password: str | None = None
    operator_username: str | None = None
    operator_password: str | None = None


class TestConnectionRequest(BaseModel):
    netris_base_url: str
    netris_username: str
    netris_password: str | None = None  # blank/omitted = use the currently stored password
    netris_site_id: int
    netris_site_name: str
    netris_verify_ssl: bool = False


class TestSSHConnectionRequest(BaseModel):
    ssh_jump_host: str
    ssh_jump_port: int = 22
    ssh_jump_username: str
    ssh_jump_password: str | None = None  # blank/omitted = use the currently stored password


@router.get("", response_class=HTMLResponse)
def settings_page(request: Request, _: None = Depends(require_operator)):
    settings = settings_store.get_settings()
    return _templates.TemplateResponse("settings.html", {"request": request, "settings": settings})


@router.get("/docs", response_class=HTMLResponse)
def docs_page(request: Request, _: None = Depends(require_operator)):
    return _templates.TemplateResponse("docs.html", {"request": request})


@router.get("/api/settings")
def get_settings_api(_: None = Depends(require_operator)):
    s = settings_store.get_settings()
    return {
        "netris_base_url": s.netris_base_url,
        "netris_username": s.netris_username,
        "netris_password_set": bool(s.netris_password_encrypted),
        "netris_site_id": s.netris_site_id,
        "netris_site_name": s.netris_site_name,
        "netris_template_id": s.netris_template_id,
        "netris_template_name": s.netris_template_name,
        "netris_verify_ssl": bool(s.netris_verify_ssl),
        "ssh_jump_host": s.ssh_jump_host,
        "ssh_jump_port": s.ssh_jump_port,
        "ssh_jump_username": s.ssh_jump_username,
        "ssh_jump_password_set": bool(s.ssh_jump_password_encrypted),
        "ssh_configured": s.ssh_configured,
        "demo_app_port": s.demo_app_port,
        "gpus_per_server": s.gpus_per_server,
        "max_servers_per_request": s.max_servers_per_request,
        "tenant_display_name": s.tenant_display_name,
        "customer_username": s.customer_username,
        "operator_username": s.operator_username,
        "netris_configured": s.netris_configured,
    }



# Fields that change *which account* the shared NetrisClient is
# authenticated as — see NetrisClient.invalidate_session.
_NETRIS_SESSION_FIELDS = {"netris_base_url", "netris_username", "netris_password", "netris_verify_ssl"}


@router.get("/api/device-credentials")
def device_credentials(request: Request, _: None = Depends(require_operator)):
    """Plaintext Netris + SSH jump-host credentials, for bootstrapping the
    Meridian demo console onto a compute host at install time. Unlike
    /api/settings above, this intentionally returns decrypted secrets — the
    console authenticates to Netris and the jump host directly, the same way
    this app's own netris_client/ssh_client do internally, rather than
    proxying every lookup back through this Portal at runtime. Gated by the
    same operator Basic Auth as everything else under /ops; there is no
    narrower credential for this on purpose (see the device-console plan).
    """
    settings = settings_store.get_settings()
    secret_box = request.app.state.secret_box
    netris_password = (
        secret_box.decrypt(settings.netris_password_encrypted)
        if settings.netris_password_encrypted
        else None
    )
    ssh_jump_password = (
        secret_box.decrypt(settings.ssh_jump_password_encrypted)
        if settings.ssh_jump_password_encrypted
        else None
    )
    return {
        "netris_base_url": settings.netris_base_url,
        "netris_username": settings.netris_username,
        "netris_password": netris_password,
        "netris_verify_ssl": bool(settings.netris_verify_ssl),
        "ssh_jump_host": settings.ssh_jump_host,
        "ssh_jump_port": settings.ssh_jump_port,
        "ssh_jump_username": settings.ssh_jump_username,
        "ssh_jump_password": ssh_jump_password,
        "tenant_display_name": settings.tenant_display_name,
        "gpus_per_server": settings.gpus_per_server,
    }


@router.put("/api/settings")
def update_settings_api(payload: SettingsUpdate, request: Request, _: None = Depends(require_operator)):
    fields = payload.model_dump(exclude_unset=True)
    if "netris_verify_ssl" in fields and fields["netris_verify_ssl"] is not None:
        fields["netris_verify_ssl"] = int(fields["netris_verify_ssl"])
    updated = settings_store.update_settings(request.app.state.secret_box, **fields)
    if _NETRIS_SESSION_FIELDS & fields.keys():
        request.app.state.netris_client.invalidate_session()
    return {"ok": True, "updated_at": updated.updated_at}


@router.post("/api/settings/test-netris-connection")
async def test_connection(payload: TestConnectionRequest, request: Request):
    password = payload.netris_password
    if not password:
        current = settings_store.get_settings()
        if not current.netris_password_encrypted:
            return {"ok": False, "message": "No password provided and none stored yet."}
        password = request.app.state.secret_box.decrypt(current.netris_password_encrypted)

    base_url = payload.netris_base_url.rstrip("/")
    async with httpx.AsyncClient(verify=payload.netris_verify_ssl, follow_redirects=True) as http:
        try:
            login_resp = await http.post(
                f"{base_url}/api/auth",
                json={"user": payload.netris_username, "password": password, "auth_scheme_id": 1},
                timeout=15,
            )
        except httpx.HTTPError as exc:
            return {"ok": False, "message": f"Could not reach controller: {exc}"}
        if login_resp.status_code >= 400:
            return {"ok": False, "message": f"Login failed (HTTP {login_resp.status_code})."}

        try:
            servers_resp = await http.get(f"{base_url}/api/v2/server-cluster/servers", timeout=15)
        except httpx.HTTPError as exc:
            return {"ok": False, "message": f"Login succeeded but listing servers failed: {exc}"}
        if servers_resp.status_code >= 400:
            return {"ok": False, "message": f"Login succeeded but listing servers failed (HTTP {servers_resp.status_code})."}

        data = (servers_resp.json() or {}).get("data") or []
        matching_names = sorted({
            (s.get("site") or {}).get("name")
            for s in data
            if (s.get("site") or {}).get("id") == payload.netris_site_id
        } - {None})

        if not matching_names:
            return {
                "ok": False,
                "message": f"Login OK, but no servers found with site id {payload.netris_site_id}. Double-check the site id.",
            }
        if payload.netris_site_name and payload.netris_site_name not in matching_names:
            return {
                "ok": False,
                "message": f"Site id {payload.netris_site_id} resolves to {matching_names}, not "
                f"'{payload.netris_site_name}' — check for a typo in the site name.",
            }
        available = sum(
            1 for s in data
            if (s.get("site") or {}).get("id") == payload.netris_site_id and s.get("serverClusterID") is None
        )
        return {
            "ok": True,
            "message": f"Connected. Site {payload.netris_site_id} = '{matching_names[0]}'. "
            f"{available} server(s) currently available there out of {len(data)} total visible.",
        }


@router.post("/api/settings/test-ssh-connection")
async def test_ssh_connection(payload: TestSSHConnectionRequest, request: Request):
    password = payload.ssh_jump_password
    if not password:
        current = settings_store.get_settings()
        if not current.ssh_jump_password_encrypted:
            return {"ok": False, "message": "No password provided and none stored yet."}
        password = request.app.state.secret_box.decrypt(current.ssh_jump_password_encrypted)

    try:
        async with asyncssh.connect(
            payload.ssh_jump_host,
            port=payload.ssh_jump_port,
            username=payload.ssh_jump_username,
            password=password,
            known_hosts=None,
        ) as conn:
            aliases = await resolve_aliases(conn)
    except Exception as exc:
        return {"ok": False, "message": f"Could not reach jump host: {exc}"}

    if not aliases:
        return {
            "ok": False,
            "message": "Connected, but found no 'hgx-*' device aliases in the jump host's interactive shell "
            "(~/.bash_aliases) — device hops will fail until those exist.",
        }
    return {"ok": True, "message": f"Connected. Found {len(aliases)} device aliases on the jump host."}
