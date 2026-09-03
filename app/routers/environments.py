"""Customer-facing environment CRUD + status. Every route here requires the
customer session (see app/deps.py) — this is the self-service surface the
demo persona uses, entirely separate from /ops.
"""
from __future__ import annotations

import json
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app import db, settings_store, ssh_client
from app.deps import require_customer_session
from app.netris.exceptions import NetrisAPIError, NetrisAuthError
from app.provisioning import delete_flow, fake_compute
from app.provisioning import state_machine as sm
from datetime import datetime

router = APIRouter(
    prefix="/api/environments", tags=["environments"], dependencies=[Depends(require_customer_session)]
)


class CreateEnvironmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    server_count: int = Field(ge=1)


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def _get_row(env_uuid: str) -> dict:
    row = db.query_one("SELECT * FROM environments WHERE uuid = ?", (env_uuid,))
    if row is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    return _row_to_dict(row)


def _compute_progress(row: dict) -> dict:
    if row["kind"] != "real" or row["fake_sim_started_at"] is None:
        return {"pct": 100 if row["status"] == "active" else 0, "elapsed_seconds": None, "total_seconds": None}
    started_at = datetime.fromisoformat(row["fake_sim_started_at"])
    progress = fake_compute.progress_at(row["uuid"], started_at)
    pct = 100 if progress.done else round((progress.elapsed_seconds / progress.total_duration_seconds) * 100)
    return {
        "pct": pct,
        "elapsed_seconds": round(progress.elapsed_seconds),
        "total_seconds": round(progress.total_duration_seconds),
    }


def _public_environment(row: dict) -> dict:
    progress = _compute_progress(row)
    return {
        "uuid": row["uuid"],
        "name": row["name"],
        "kind": row["kind"],
        "status": row["status"],
        "status_detail": row["status_detail"],
        "error_message": row["error_message"],
        "requested_server_count": row["requested_server_count"],
        "gpus_per_server": row["gpus_per_server"],
        "total_gpus": row["requested_server_count"] * row["gpus_per_server"],
        "netris_vpc_name": row["netris_vpc_name"],
        "netris_status_label": row["netris_status_label"],
        "servers": json.loads(row["servers_json"]) if row["servers_json"] else [],
        "subnets": json.loads(row["subnets_json"]) if row["subnets_json"] else {},
        "netris_delete_confirmed": row["netris_delete_confirmed"],
        "compute_progress_pct": progress["pct"],
        "compute_elapsed_seconds": progress["elapsed_seconds"],
        "compute_total_seconds": progress["total_seconds"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "deleted_at": row["deleted_at"],
    }


@router.get("")
def list_environments():
    rows = db.query_all("SELECT * FROM environments WHERE deleted_at IS NULL ORDER BY created_at DESC")
    return [_public_environment(_row_to_dict(r)) for r in rows]


@router.get("/capacity")
async def capacity(request: Request):
    settings = settings_store.get_settings()
    if not settings.netris_configured:
        return {
            "available_count": 0,
            "gpus_per_server": settings.gpus_per_server,
            "max_per_request": settings.max_servers_per_request,
            "configured": False,
        }
    client = request.app.state.netris_client
    try:
        available = await client.list_available_servers(settings.netris_site_id)
    except (NetrisAuthError, NetrisAPIError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach the provider network: {exc}") from exc
    return {
        "available_count": len(available),
        "gpus_per_server": settings.gpus_per_server,
        "max_per_request": settings.max_servers_per_request,
        "configured": True,
    }


@router.post("", status_code=201)
async def create_environment(payload: CreateEnvironmentRequest, request: Request):
    settings = settings_store.get_settings()
    if not settings.netris_configured:
        raise HTTPException(
            status_code=503, detail="This Neo Cloud isn't accepting new orders right now — please contact support."
        )
    if payload.server_count > settings.max_servers_per_request:
        raise HTTPException(status_code=400, detail=f"Maximum {settings.max_servers_per_request} GPU servers per environment.")

    env_uuid = str(uuid_lib.uuid4())
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in payload.name.strip()) or "env"
    netris_name = f"{safe_name}-{env_uuid[:6]}"
    now = sm.now_iso()

    db.execute(
        """INSERT INTO environments
           (uuid, name, netris_name, kind, requested_server_count, gpus_per_server, status, created_at, updated_at)
           VALUES (?, ?, ?, 'real', ?, ?, ?, ?, ?)""",
        (env_uuid, payload.name.strip(), netris_name, payload.server_count, settings.gpus_per_server, sm.QUEUED, now, now),
    )
    row = _get_row(env_uuid)
    request.app.state.task_manager.start_provisioning(row["id"])
    return _public_environment(row)


@router.get("/{env_uuid}")
def get_environment(env_uuid: str):
    return _public_environment(_get_row(env_uuid))


@router.get("/{env_uuid}/events")
def get_environment_events(env_uuid: str):
    env = _get_row(env_uuid)
    rows = db.query_all(
        "SELECT at, event_type, from_status, to_status, message, raw_payload FROM environment_events "
        "WHERE environment_id = ? ORDER BY at ASC",
        (env["id"],),
    )
    events = []
    for r in rows:
        event = dict(r)
        raw = event.pop("raw_payload")
        if raw:
            try:
                event["detail"] = json.loads(raw)
            except ValueError:
                event["detail"] = {"raw": raw}
        else:
            event["detail"] = None
        events.append(event)
    return events


@router.post("/{env_uuid}/connectivity-test/{server_id}")
async def connectivity_test(env_uuid: str, server_id: int, request: Request):
    env = _get_row(env_uuid)
    if env["kind"] != "real":
        raise HTTPException(status_code=400, detail="Connectivity testing is only available for real environments.")
    servers = json.loads(env["servers_json"]) if env["servers_json"] else []
    source = next((s for s in servers if s["id"] == server_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Server not found on this environment.")
    targets = [s for s in servers if s["id"] != server_id]

    try:
        return await ssh_client.test_connectivity(request.app.state.secret_box, source, targets)
    except ssh_client.ConnectivityTestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{env_uuid}")
async def delete_environment(env_uuid: str, request: Request):
    env = _get_row(env_uuid)
    request.app.state.task_manager.cancel(env["id"])
    if env["kind"] == "dummy":
        await delete_flow.dummy_delete(env["id"])
    else:
        await delete_flow.real_delete(env["id"], request.app.state.netris_client, request.app.state.secret_box)
    return _public_environment(_get_row(env_uuid))


@router.post("/{env_uuid}/retry-delete")
async def retry_delete(env_uuid: str, request: Request):
    env = _get_row(env_uuid)
    if env["status"] != sm.DELETE_FAILED:
        raise HTTPException(status_code=400, detail="Environment is not in a failed-delete state")
    await delete_flow.real_delete(env["id"], request.app.state.netris_client, request.app.state.secret_box)
    return _public_environment(_get_row(env_uuid))


@router.post("/{env_uuid}/dismiss-delete")
async def dismiss_delete(env_uuid: str):
    env = _get_row(env_uuid)
    if env["status"] != sm.DELETE_FAILED:
        raise HTTPException(status_code=400, detail="Environment is not in a failed-delete state")
    await delete_flow.dismiss_delete(env["id"])
    return _public_environment(_get_row(env_uuid))
