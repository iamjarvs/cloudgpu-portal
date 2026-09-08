"""Optional Netris "add-on" services attachable to an environment beyond
compute: NAT rules, ACLs, extra V-Nets, and L4 load balancers.

Each is user-initiated — either bundled into the deploy request or added
later from the environment detail page — and tracked as one JSON blob
(`environments.netris_extras_json`, `{kind: [item, ...]}`) rather than
separate tables, since there's no need to query across environments by
extra. An item is `pending` until Netris confirms it (which needs the
environment's VPC, so a real environment's extras stay pending until the
orchestrator's poll loop has a `netris_vpc_id`), then `created` with the
real `netris_id`, or `failed` with an error. Dummy environments skip the
network round-trip entirely and go straight to `created` with a fabricated
id — see `mark_created_fake` — matching the rest of this app's
dummy-environments-are-cosmetic-only convention (app/seed.py, delete_flow.py).
"""
from __future__ import annotations

import json
import random
import uuid as uuid_lib

from app import db
from app.netris.client import NetrisClient
from app.netris.exceptions import NetrisAPIError, NetrisAuthError
from app.provisioning import state_machine as sm

KINDS = ("nat", "acl", "vnet", "lb")

KIND_LABELS = {"nat": "NAT rule", "acl": "ACL rule", "vnet": "V-Net", "lb": "Load balancer"}

# Fabricated Netris ids for dummy environments' extras — a distinct high
# range so they're never mistaken for real controller-assigned ids (see the
# 90000-range server ids in app/seed.py, same idea).
_FAKE_ID_BASE = {"nat": 81000, "acl": 82000, "vnet": 83000, "lb": 84000}


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_environment(environment_id: int) -> dict:
    row = db.query_one("SELECT * FROM environments WHERE id = ?", (environment_id,))
    return _row_to_dict(row)


def _load(env: dict) -> dict:
    raw = env.get("netris_extras_json")
    data = json.loads(raw) if raw else {}
    for k in KINDS:
        data.setdefault(k, [])
    return data


def _save(environment_id: int, data: dict) -> None:
    db.execute(
        "UPDATE environments SET netris_extras_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(data), sm.now_iso(), environment_id),
    )


def list_extras(environment_id: int) -> dict:
    return _load(get_environment(environment_id))


def find(environment_id: int, kind: str, local_id: str) -> dict | None:
    data = _load(get_environment(environment_id))
    return next((item for item in data.get(kind, []) if item["local_id"] == local_id), None)


def add_pending(environment_id: int, kind: str, config: dict) -> dict:
    env = get_environment(environment_id)
    data = _load(env)
    item = {
        "local_id": uuid_lib.uuid4().hex[:10],
        "kind": kind,
        "state": "pending",
        "netris_id": None,
        "config": config,
        "error": None,
        "created_at": sm.now_iso(),
    }
    data[kind].append(item)
    _save(environment_id, data)
    sm.log_event(
        environment_id, "extra_requested",
        message=f"{KIND_LABELS[kind]} '{config.get('name', '')}' requested",
    )
    return item


def mark_created(environment_id: int, kind: str, local_id: str, netris_id) -> None:
    env = get_environment(environment_id)
    data = _load(env)
    for item in data[kind]:
        if item["local_id"] == local_id:
            item["state"] = "created"
            item["netris_id"] = netris_id
            item["error"] = None
            break
    _save(environment_id, data)


def mark_failed(environment_id: int, kind: str, local_id: str, error: str) -> None:
    env = get_environment(environment_id)
    data = _load(env)
    for item in data[kind]:
        if item["local_id"] == local_id:
            item["state"] = "failed"
            item["error"] = error
            break
    _save(environment_id, data)


def mark_created_fake(environment_id: int, kind: str, local_id: str) -> None:
    """Dummy-environment path: no Netris call, just a cosmetic id."""
    item = find(environment_id, kind, local_id)
    seed = f"{environment_id}-{kind}-{local_id}"
    fake_id = _FAKE_ID_BASE[kind] + (random.Random(seed).randint(0, 999) if item else 0)
    mark_created(environment_id, kind, local_id, fake_id)


def remove(environment_id: int, kind: str, local_id: str) -> dict | None:
    env = get_environment(environment_id)
    data = _load(env)
    removed = None
    kept = []
    for item in data[kind]:
        if item["local_id"] == local_id and removed is None:
            removed = item
        else:
            kept.append(item)
    data[kind] = kept
    _save(environment_id, data)
    return removed


async def create_now(environment_id: int, kind: str, local_id: str, client: NetrisClient, settings) -> None:
    """Fires the real Netris create call for one pending item. Safe to call
    repeatedly (e.g. once per orchestrator poll) — a no-op once the item is
    no longer `pending`."""
    item = find(environment_id, kind, local_id)
    if item is None or item["state"] != "pending":
        return
    env = get_environment(environment_id)
    cfg = item["config"]
    vpc_id, vpc_name = env["netris_vpc_id"], env["netris_vpc_name"]
    try:
        if kind == "nat":
            netris_id = await client.create_nat_rule(
                name=cfg["name"],
                site_id=settings.netris_site_id, site_name=settings.netris_site_name,
                vpc_id=vpc_id, vpc_name=vpc_name,
                state=cfg.get("state", "enabled"), action=cfg.get("action", "DNAT"),
                protocol=cfg.get("protocol", "all"),
                source_address=cfg.get("sourceAddress", "0.0.0.0/0"), source_port=cfg.get("sourcePort", "1-65535"),
                destination_address=cfg["destinationAddress"], destination_port=cfg.get("destinationPort", ""),
                dnat_to_ip=cfg.get("dnatToIP", ""), dnat_to_port=cfg.get("dnatToPort", ""),
                comment=cfg.get("comment", ""), pool=cfg.get("pool", True), port_group=cfg.get("portGroup", ""),
                environment_id=environment_id,
            )
        elif kind == "acl":
            netris_id = await client.create_acl_rule(
                name=cfg["name"], vpc_id=vpc_id, vpc_name=vpc_name, comment=cfg.get("comment", ""),
                action=cfg.get("action", "permit"), proto=cfg.get("proto", "tcp"),
                src_prefix=cfg.get("src_prefix", "0.0.0.0/0"), dst_prefix=cfg.get("dst_prefix", "0.0.0.0/0"),
                src_port_from=cfg.get("src_port_from"), src_port_to=cfg.get("src_port_to"),
                dst_port_from=cfg.get("dst_port_from"), dst_port_to=cfg.get("dst_port_to"),
                environment_id=environment_id,
            )
        elif kind == "vnet":
            tenant_id, tenant_name = await client.get_default_tenant(environment_id=environment_id)
            netris_id = await client.create_vnet(
                name=cfg["name"], tenant_id=tenant_id, tenant_name=tenant_name,
                site_id=settings.netris_site_id, site_name=settings.netris_site_name,
                vpc_id=vpc_id, vpc_name=vpc_name, vlan=cfg.get("vlan", "auto"), state=cfg.get("state", "active"),
                ip_family=cfg.get("ipFamily", "dual"), gateways=cfg.get("gateways") or [],
                environment_id=environment_id,
            )
        elif kind == "lb":
            netris_id = await client.create_load_balancer(
                name=cfg["name"], description=cfg.get("description", ""),
                site_id=settings.netris_site_id, site_name=settings.netris_site_name,
                vpc_id=vpc_id, vpc_name=vpc_name, protocol=cfg.get("protocol", "TCP"),
                ip_family=cfg.get("ipFamily", "IPv4"), ip=cfg.get("ip", "0.0.0.0"), port=cfg.get("port", 80),
                status=cfg.get("status", "enable"), health_check=cfg.get("healthCheck", "TCP"),
                timeout=cfg.get("timeOut", 1000), request_path=cfg.get("requestPath", ""),
                backend=cfg.get("backend") or [], environment_id=environment_id,
            )
        else:
            return
    except (NetrisAuthError, NetrisAPIError) as exc:
        mark_failed(environment_id, kind, local_id, str(exc))
        sm.log_event(
            environment_id, "extra_failed",
            message=f"{KIND_LABELS[kind]} '{cfg.get('name')}' failed: {exc}",
        )
        return
    mark_created(environment_id, kind, local_id, netris_id)
    sm.log_event(
        environment_id, "extra_created",
        message=f"{KIND_LABELS[kind]} '{cfg.get('name')}' created (Netris ID {netris_id})",
    )


async def create_all_pending(environment_id: int, client: NetrisClient, settings) -> None:
    """Called from the provisioning poll loop once the environment has a
    VPC — fires every extra still waiting on one, in one pass."""
    data = list_extras(environment_id)
    for kind in KINDS:
        for item in data[kind]:
            if item["state"] == "pending":
                await create_now(environment_id, kind, item["local_id"], client, settings)


async def delete_now(environment_id: int, kind: str, local_id: str, client: NetrisClient) -> None:
    """Best-effort teardown of one confirmed extra. Raises on failure — the
    router surfaces that to the caller; delete_flow.real_delete catches it
    instead, since a stray leftover NAT/ACL/V-Net/LB must never block
    tearing down the environment itself."""
    item = find(environment_id, kind, local_id)
    if item is None or item["netris_id"] is None:
        return
    netris_id = item["netris_id"]
    if kind == "nat":
        await client.delete_nat_rule(netris_id, environment_id=environment_id)
    elif kind == "acl":
        await client.delete_acl_rule(netris_id, environment_id=environment_id)
    elif kind == "vnet":
        await client.delete_vnet(netris_id, environment_id=environment_id)
    elif kind == "lb":
        await client.delete_load_balancer(netris_id, environment_id=environment_id)
    remove(environment_id, kind, local_id)
    sm.log_event(
        environment_id, "extra_deleted",
        message=f"{KIND_LABELS[kind]} '{item['config'].get('name')}' deleted (Netris ID {netris_id})",
    )
