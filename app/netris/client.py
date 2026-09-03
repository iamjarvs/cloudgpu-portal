"""Netris SDN controller client — cookie-based auth, auto re-login on 401.

There is exactly one configured Netris account for this whole tool, so a
single shared cookie jar (one NetrisClient instance living on app.state,
wrapping one shared httpx.AsyncClient) is correct, not a limitation.
Credentials are re-read from app_settings on every (re-)login, so an
operator changing them via /ops takes effect on the client's next login
without an app restart.

Every outward-facing call goes through `_request`, which centralizes the
401-then-re-login-then-retry-once logic so no call site has to think about
cookie expiry itself, and (when given an `environment_id`) records the raw
request/response as an `environment_events` row so it can be inspected from
the environment detail page's API log.
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx

from app import settings_store
from app.netris.exceptions import NetrisAPIError, NetrisAuthError, NetrisCapacityError
from app.security import SecretBox

logger = logging.getLogger("netris")

_REDACTED = "••••••••"


def _redact(body: dict | None) -> dict | None:
    if not isinstance(body, dict):
        return body
    return {k: (_REDACTED if k in ("password", "netris_password") else v) for k, v in body.items()}


def _truncate(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "… (truncated)"


def _check_success(resp: httpx.Response, action: str) -> dict:
    if resp.status_code >= 400:
        raise NetrisAPIError(f"{action} failed (HTTP {resp.status_code}).", resp.status_code)
    try:
        payload = resp.json()
    except ValueError as exc:
        raise NetrisAPIError(f"{action} returned a non-JSON response.", resp.status_code) from exc
    if payload.get("isSuccess") is False:
        errors = payload.get("errors") or payload.get("message") or "unknown error"
        raise NetrisAPIError(f"{action} rejected by controller: {errors}", resp.status_code)
    return payload


class NetrisClient:
    def __init__(self, http_client: httpx.AsyncClient, secret_box: SecretBox):
        self._http = http_client
        self._secret_box = secret_box
        self._login_lock = asyncio.Lock()
        self._logged_in = False
        self._admin_id: int | None = None
        self._admin_name: str | None = None

    def _base_url(self) -> str:
        settings = settings_store.get_settings()
        if not settings.netris_base_url:
            raise NetrisAuthError("Netris controller is not configured yet — set it up in /ops.")
        return settings.netris_base_url.rstrip("/")

    async def _login(self) -> None:
        async with self._login_lock:
            if self._logged_in:
                return  # another waiter already refreshed it
            settings = settings_store.get_settings()
            if not settings.netris_configured:
                raise NetrisAuthError("Netris controller is not configured yet — set it up in /ops.")
            password = self._secret_box.decrypt(settings.netris_password_encrypted)
            url = f"{settings.netris_base_url.rstrip('/')}/api/auth"
            try:
                resp = await self._http.post(
                    url,
                    json={"user": settings.netris_username, "password": password, "auth_scheme_id": 1},
                    timeout=15,
                )
            except httpx.HTTPError as exc:
                raise NetrisAuthError(f"Could not reach Netris controller: {exc}") from exc
            if resp.status_code >= 400:
                raise NetrisAuthError(f"Netris login rejected (HTTP {resp.status_code}).")
            # The authenticated account's own identity — used as the `admin`
            # field on create_cluster. This must reflect who actually logged
            # in, not a hardcoded placeholder: Netris ties cluster-create
            # permission to this identity, and a mismatch here (e.g. always
            # sending a fixed id/name regardless of which account is
            # configured) is rejected with a 403 even when the account
            # genuinely has create rights.
            try:
                login_data = (resp.json() or {}).get("data") or {}
            except ValueError:
                login_data = {}
            self._admin_id = login_data.get("user_id")
            self._admin_name = login_data.get("name") or settings.netris_username
            self._logged_in = True
            logger.info("Netris login OK as %s (id=%s)", self._admin_name, self._admin_id)

    async def get_admin_identity(self) -> tuple[int, str]:
        if not self._logged_in:
            await self._login()
        return self._admin_id, self._admin_name

    def _log_call(
        self,
        environment_id: int | None,
        action: str,
        method: str,
        url: str,
        request_body: dict | None,
        resp: httpx.Response,
    ) -> None:
        if environment_id is None:
            return
        # Local import to avoid a module-load-time cycle (state_machine -> db,
        # nothing imports netris.client back).
        from app.provisioning import state_machine as sm

        try:
            response_body = resp.json()
        except ValueError:
            response_body = resp.text

        payload = {
            "method": method,
            "url": url,
            "request_body": _redact(request_body),
            "response_status": resp.status_code,
            "response_body": response_body,
        }
        sm.log_event(
            environment_id,
            "netris_api_call",
            message=f"{action}: {method} {url} → HTTP {resp.status_code}",
            raw_payload=_truncate(json.dumps(payload, default=str)),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        environment_id: int | None = None,
        action: str | None = None,
        **kwargs,
    ) -> httpx.Response:
        if not self._logged_in:
            await self._login()
        url = f"{self._base_url()}{path}"
        resp = await self._http.request(method, url, timeout=30, **kwargs)
        if resp.status_code == 401:
            self._logged_in = False
            await self._login()
            resp = await self._http.request(method, url, timeout=30, **kwargs)
            if resp.status_code == 401:
                raise NetrisAuthError("Netris rejected credentials even after re-login.")
        self._log_call(environment_id, action or f"{method} {path}", method, url, kwargs.get("json"), resp)
        return resp

    async def list_all_servers(self, *, environment_id: int | None = None) -> list[dict]:
        resp = await self._request(
            "GET", "/api/v2/server-cluster/servers", environment_id=environment_id, action="List servers"
        )
        payload = _check_success(resp, "List servers")
        return payload.get("data") or []

    async def list_available_servers(self, site_id: int, *, environment_id: int | None = None) -> list[dict]:
        servers = await self.list_all_servers(environment_id=environment_id)
        available = [
            s
            for s in servers
            if (s.get("site") or {}).get("id") == site_id and s.get("serverClusterID") is None
        ]
        available.sort(key=lambda s: s["name"])
        return available

    async def pick_servers_for_request(
        self, site_id: int, count: int, *, environment_id: int | None = None
    ) -> list[dict]:
        available = await self.list_available_servers(site_id, environment_id=environment_id)
        if len(available) < count:
            raise NetrisCapacityError(requested=count, available=len(available))
        return available[:count]

    async def create_cluster(
        self,
        *,
        name: str,
        admin_id: int,
        admin_name: str,
        site_id: int,
        site_name: str,
        template_id: int,
        template_name: str,
        servers: list[dict],
        environment_id: int | None = None,
    ) -> None:
        body = {
            "name": name,
            "admin": {"id": admin_id, "name": admin_name},
            "site": {"id": site_id, "name": site_name},
            "vpc": {"id": 0, "name": "Create New"},
            "srvClusterTemplate": {"id": template_id, "name": template_name, "vlans": []},
            "tags": [],
            "servers": [{"id": s["id"], "name": s["name"], "shared": False} for s in servers],
        }
        resp = await self._request(
            "POST", "/api/v2/server-cluster", environment_id=environment_id, action="Create server-cluster", json=body
        )
        _check_success(resp, "Create server-cluster")

    async def list_clusters(self, *, environment_id: int | None = None) -> list[dict]:
        resp = await self._request(
            "GET", "/api/v2/server-cluster", environment_id=environment_id, action="List server-clusters"
        )
        payload = _check_success(resp, "List server-clusters")
        return payload.get("data") or []

    async def get_cluster_by_name(self, netris_name: str, *, environment_id: int | None = None) -> dict | None:
        for cluster in await self.list_clusters(environment_id=environment_id):
            if cluster.get("name") == netris_name:
                return cluster
        return None

    async def get_cluster_by_id(self, cluster_id: int, *, environment_id: int | None = None) -> dict | None:
        for cluster in await self.list_clusters(environment_id=environment_id):
            if cluster.get("id") == cluster_id:
                return cluster
        return None

    async def delete_cluster(self, cluster_id: int, *, environment_id: int | None = None) -> None:
        """DELETE /api/v2/server-cluster/{id} — verified against the live controller
        (creates a real cluster, confirms it, deletes it, confirms removal and that the
        server is freed). Still, treat any failure here as "not deleted", never as a
        soft/ignorable error — see provisioning/delete_flow.py."""
        resp = await self._request(
            "DELETE",
            f"/api/v2/server-cluster/{cluster_id}",
            environment_id=environment_id,
            action="Delete server-cluster",
        )
        if resp.status_code >= 300:
            raise NetrisAPIError(
                f"Delete failed (HTTP {resp.status_code}) — endpoint may not match the live controller.",
                resp.status_code,
            )
