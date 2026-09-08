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
        self._tenant_id: int | None = None
        self._tenant_name: str | None = None

    def invalidate_session(self) -> None:
        """Called by /ops right after the operator changes the Netris
        connection (base URL, username, password, or SSL verification) —
        without this, an already-authenticated client has no reason to
        re-login (only a 401 triggers that), so it would keep making calls
        as whichever account it logged in as, silently ignoring the new
        credentials until the process restarts. Also drops the cached admin
        identity and tenant, both of which are tied to the account that was
        logged in and must be re-derived under the new one."""
        self._logged_in = False
        self._admin_id = None
        self._admin_name = None
        self._tenant_id = None
        self._tenant_name = None

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

    async def get_default_tenant(self, *, environment_id: int | None = None) -> tuple[int, str]:
        """V-Net creation requires an owning tenant, which nothing else in
        this app currently tracks. Fetched once (GET /api/tenants, a v1
        endpoint that returns a bare array) and cached on this client for
        its lifetime — preferring 'adminTenant' since that's the tenant the
        seeded operator/customer credentials are expected to belong to."""
        if self._tenant_id is not None:
            return self._tenant_id, self._tenant_name
        resp = await self._request("GET", "/api/tenants", environment_id=environment_id, action="List tenants")
        if resp.status_code >= 400:
            raise NetrisAPIError(f"List tenants failed (HTTP {resp.status_code}).", resp.status_code)
        tenants = resp.json() or []
        if not tenants:
            raise NetrisAPIError("No tenants available on this Netris controller.", resp.status_code)
        tenant = next((t for t in tenants if t.get("name") == "adminTenant"), tenants[0])
        self._tenant_id, self._tenant_name = tenant["id"], tenant["name"]
        return self._tenant_id, self._tenant_name

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

    # ---------- NAT rules (POST/DELETE /api/v2/nat) ----------

    async def create_nat_rule(
        self,
        *,
        name: str,
        site_id: int,
        site_name: str,
        vpc_id: int,
        vpc_name: str,
        state: str = "enabled",
        action: str = "DNAT",
        protocol: str = "all",
        source_address: str = "0.0.0.0/0",
        source_port: str = "1-65535",
        destination_address: str,
        destination_port: str = "",
        dnat_to_ip: str = "",
        dnat_to_port: str = "",
        comment: str = "",
        pool: bool = True,
        port_group: str = "",
        environment_id: int | None = None,
    ) -> int:
        body = {
            "name": name,
            "site": {"id": site_id, "name": site_name},
            "vpc": {"id": vpc_id, "name": vpc_name},
            "state": state,
            "action": action,
            "protocol": protocol,
            "sourceAddress": source_address,
            "sourcePort": source_port,
            "destinationAddress": destination_address,
            "destinationPort": destination_port,
            "dnatToIP": dnat_to_ip,
            "dnatToPort": dnat_to_port,
            "comment": comment,
            "pool": pool,
            "portGroup": port_group,
        }
        resp = await self._request(
            "POST", "/api/v2/nat", environment_id=environment_id, action="Create NAT rule", json=body
        )
        payload = _check_success(resp, "Create NAT rule")
        return (payload.get("data") or {}).get("id")

    async def delete_nat_rule(self, nat_id: int, *, environment_id: int | None = None) -> None:
        resp = await self._request(
            "DELETE", f"/api/v2/nat/{nat_id}", environment_id=environment_id, action="Delete NAT rule"
        )
        _check_success(resp, "Delete NAT rule")

    # ---------- ACL rules (POST/DELETE /api/acl — a v1 endpoint, no /v2 prefix) ----------

    async def create_acl_rule(
        self,
        *,
        name: str,
        vpc_id: int | None,
        vpc_name: str | None,
        comment: str = "",
        action: str = "permit",
        proto: str = "tcp",
        src_prefix: str = "0.0.0.0/0",
        dst_prefix: str = "0.0.0.0/0",
        src_port_from: int | None = None,
        src_port_to: int | None = None,
        dst_port_from: int | None = None,
        dst_port_to: int | None = None,
        established: int = 1,
        reverse: str = "yes",
        environment_id: int | None = None,
    ) -> int:
        body = {
            "name": name,
            "vpc": {"id": vpc_id, "name": vpc_name} if vpc_id else None,
            "comment": comment,
            "action": action,
            "proto": proto,
            "src_prefix": src_prefix,
            "dst_prefix": dst_prefix,
            "src_port_from": src_port_from,
            "src_port_to": src_port_to,
            "src_port_group": None,
            "dst_port_from": dst_port_from,
            "dst_port_to": dst_port_to,
            "dst_port_group": None,
            "established": established,
            "reverse": reverse,
        }
        resp = await self._request(
            "POST", "/api/acl", environment_id=environment_id, action="Create ACL rule", json=body
        )
        payload = _check_success(resp, "Create ACL rule")
        return (payload.get("data") or {}).get("id")

    async def delete_acl_rule(self, acl_id: int, *, environment_id: int | None = None) -> None:
        resp = await self._request(
            "DELETE", "/api/acl", environment_id=environment_id, action="Delete ACL rule", json={"id": [acl_id]}
        )
        _check_success(resp, "Delete ACL rule")

    # ---------- V-Nets (POST/DELETE /api/v2/vnet) ----------

    async def create_vnet(
        self,
        *,
        name: str,
        tenant_id: int,
        tenant_name: str,
        site_id: int,
        site_name: str,
        vpc_id: int | None,
        vpc_name: str | None,
        vlan: str | int = "auto",
        state: str = "active",
        ip_family: str = "dual",
        gateways: list[dict] | None = None,
        environment_id: int | None = None,
    ) -> int:
        body = {
            "name": name,
            "tenant": {"id": tenant_id, "name": tenant_name},
            "sites": [{"id": site_id, "name": site_name}],
            "vpc": {"id": vpc_id, "name": vpc_name} if vpc_id else None,
            "vlan": vlan,
            "state": state,
            "ipFamily": ip_family,
            "gateways": gateways or [],
        }
        resp = await self._request(
            "POST", "/api/v2/vnet", environment_id=environment_id, action="Create V-Net", json=body
        )
        payload = _check_success(resp, "Create V-Net")
        # vnetResAddBody wraps the new id in a one-element array, unlike every other create call here.
        data = payload.get("data")
        if isinstance(data, list):
            return (data[0] or {}).get("id") if data else None
        return (data or {}).get("id")

    async def delete_vnet(self, vnet_id: int, *, environment_id: int | None = None) -> None:
        resp = await self._request(
            "DELETE", f"/api/v2/vnet/{vnet_id}", environment_id=environment_id, action="Delete V-Net"
        )
        _check_success(resp, "Delete V-Net")

    # ---------- L4 load balancers (POST/DELETE /api/v2/l4lb) ----------

    async def create_load_balancer(
        self,
        *,
        name: str,
        description: str = "",
        site_id: int,
        site_name: str,
        vpc_id: int | None,
        vpc_name: str | None,
        protocol: str = "TCP",
        ip_family: str = "IPv4",
        ip: str,
        port: int,
        status: str = "enable",
        health_check: str = "TCP",
        timeout: int = 1000,
        request_path: str = "",
        backend: list[dict] | None = None,
        environment_id: int | None = None,
    ) -> int:
        body = {
            "name": name,
            "description": description,
            "vpc": {"id": vpc_id, "name": vpc_name} if vpc_id else None,
            "site": {"id": site_id, "name": site_name},
            "protocol": protocol,
            "automatic": True,
            "ipFamily": ip_family,
            "ip": ip,
            "port": port,
            "status": status,
            "healthCheck": health_check,
            "timeOut": timeout,
            "requestPath": request_path,
            "backend": backend or [],
        }
        resp = await self._request(
            "POST", "/api/v2/l4lb", environment_id=environment_id, action="Create load balancer", json=body
        )
        payload = _check_success(resp, "Create load balancer")
        return (payload.get("data") or {}).get("id")

    async def delete_load_balancer(self, lb_id: int, *, environment_id: int | None = None) -> None:
        resp = await self._request(
            "DELETE", f"/api/v2/l4lb/{lb_id}", environment_id=environment_id, action="Delete load balancer"
        )
        _check_success(resp, "Delete load balancer")
