"""Idempotent first-boot seeding of permanent dummy environments, so the
dashboard never looks empty on a fresh deploy. Guarded by `seed_key` — safe
to call on every startup.

Servers/VLAN/subnet data is fabricated once here and stored as-is; only the
cosmetic utilization numbers shown for these on the dashboard drift over
time, and that drift is computed client-side (see frontend), never here.
"""
from __future__ import annotations

import json
import uuid as uuid_lib

from app import db
from app.provisioning import state_machine as sm

_DUMMIES = [
    {
        "seed_key": "dummy-training-alpha",
        "name": "Training-Cluster-Alpha",
        "server_count": 6,
        "servers": [
            {"id": 90001, "name": "hgx-pod01-su0-h00", "shared": False},
            {"id": 90002, "name": "hgx-pod01-su0-h01", "shared": False},
            {"id": 90003, "name": "hgx-pod01-su0-h02", "shared": False},
            {"id": 90004, "name": "hgx-pod01-su0-h03", "shared": False},
            {"id": 90005, "name": "hgx-pod01-su0-h04", "shared": False},
            {"id": 90006, "name": "hgx-pod01-su0-h05", "shared": False},
        ],
        "vpc_id": 900, "vpc_name": "Training-Cluster-Alpha",
        "vlan_ns": 40, "vlan_oob": 41,
        "prefix_ns": "192.168.40.0/21", "prefix_oob": "192.168.48.0/21",
        "alloc_a": "192.168.32.0/21", "alloc_b": "192.168.40.0/21",
    },
    {
        "seed_key": "dummy-inference-east",
        "name": "Inference-Prod-East",
        "server_count": 4,
        "servers": [
            {"id": 90101, "name": "hgx-pod02-su0-h00", "shared": False},
            {"id": 90102, "name": "hgx-pod02-su0-h01", "shared": False},
            {"id": 90103, "name": "hgx-pod02-su0-h02", "shared": False},
            {"id": 90104, "name": "hgx-pod02-su0-h03", "shared": False},
        ],
        "vpc_id": 910, "vpc_name": "Inference-Prod-East",
        "vlan_ns": 50, "vlan_oob": 51,
        "prefix_ns": "192.168.56.0/21", "prefix_oob": "192.168.64.0/21",
        "alloc_a": "192.168.72.0/21", "alloc_b": "192.168.80.0/21",
    },
    {
        "seed_key": "dummy-staging-sandbox",
        "name": "Staging-Sandbox",
        "server_count": 2,
        "servers": [
            {"id": 90201, "name": "hgx-pod03-su1-h00", "shared": False},
            {"id": 90202, "name": "hgx-pod03-su1-h01", "shared": False},
        ],
        "vpc_id": 920, "vpc_name": "Staging-Sandbox",
        "vlan_ns": 60, "vlan_oob": 61,
        "prefix_ns": "192.168.88.0/21", "prefix_oob": "192.168.96.0/21",
        "alloc_a": "192.168.104.0/21", "alloc_b": "192.168.112.0/21",
    },
]


def _resources_for(d: dict) -> dict:
    return {
        "vnets": [
            {
                "id": d["vpc_id"], "name": f"{d['vpc_name']}-East-West", "vlan": 0,
                "vpc": {"id": d["vpc_id"], "name": d["vpc_name"], "serviceId": d["vpc_id"] + 1},
                "ipv4Gateways": [], "ipv6Gateways": [],
            },
            {
                "id": d["vpc_id"] + 1, "name": f"{d['vpc_name']}-North-South", "vlan": d["vlan_ns"],
                "vpc": {"id": d["vpc_id"], "name": d["vpc_name"], "serviceId": d["vpc_id"] + 2},
                "ipv4Gateways": [{"prefix": d["prefix_ns"]}], "ipv6Gateways": [],
            },
            {
                "id": d["vpc_id"] + 2, "name": f"{d['vpc_name']}-OOB-Management", "vlan": d["vlan_oob"],
                "vpc": {"id": d["vpc_id"], "name": d["vpc_name"], "serviceId": d["vpc_id"] + 3},
                "ipv4Gateways": [{"prefix": d["prefix_oob"]}], "ipv6Gateways": [],
            },
        ],
        "allocations": [{"id": d["vpc_id"] + 10, "prefix": d["alloc_a"]}, {"id": d["vpc_id"] + 11, "prefix": d["alloc_b"]}],
        "subnets": [{"id": d["vpc_id"] + 20, "prefix": d["alloc_a"]}, {"id": d["vpc_id"] + 21, "prefix": d["alloc_b"]}],
    }


def seed_dummy_environments() -> None:
    for d in _DUMMIES:
        existing = db.query_one("SELECT id FROM environments WHERE seed_key = ?", (d["seed_key"],))
        if existing is not None:
            continue
        now = sm.now_iso()
        env_uuid = str(uuid_lib.uuid4())
        db.execute(
            """INSERT INTO environments (
                uuid, name, netris_name, kind, requested_server_count, gpus_per_server,
                status, status_detail, fake_sim_started_at, fake_sim_done_at,
                netris_vpc_id, netris_vpc_name, netris_status_label, netris_status_value,
                servers_json, subnets_json, seed_key, created_at, updated_at
            ) VALUES (?, ?, ?, 'dummy', ?, 8, ?, 'Active', ?, ?, ?, ?, 'Active', 'active', ?, ?, ?, ?, ?)""",
            (
                env_uuid, d["name"], d["name"], d["server_count"],
                sm.ACTIVE, now, now,
                d["vpc_id"], d["vpc_name"],
                json.dumps(d["servers"]), json.dumps(_resources_for(d)),
                d["seed_key"], now, now,
            ),
        )
