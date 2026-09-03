"""Delete/terminate flow — structurally separate dummy vs real paths so a
dummy row can never accidentally trigger a real Netris call, and a real
delete failure can never be silently reported as success.
"""
from __future__ import annotations

import asyncio
import json
import logging

from app import db, ssh_client
from app.netris.client import NetrisClient
from app.netris.exceptions import NetrisAPIError, NetrisAuthError
from app.provisioning import state_machine as sm
from app.security import SecretBox

logger = logging.getLogger("delete_flow")


class WrongKindError(Exception):
    pass


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_environment(environment_id: int) -> dict | None:
    row = db.query_one("SELECT * FROM environments WHERE id = ?", (environment_id,))
    return _row_to_dict(row) if row else None


async def dummy_delete(environment_id: int) -> None:
    env = get_environment(environment_id)
    if env is None:
        return
    if env["kind"] != "dummy":
        raise WrongKindError("dummy_delete called on a real environment")
    db.execute(
        "UPDATE environments SET status = ?, deleted_at = ?, updated_at = ? WHERE id = ?",
        (sm.DELETED, sm.now_iso(), sm.now_iso(), environment_id),
    )
    sm.log_event(environment_id, "delete_attempt", to_status=sm.DELETED, message="Cosmetic removal, no external call")


async def real_delete(environment_id: int, client: NetrisClient, secret_box: SecretBox) -> None:
    env = get_environment(environment_id)
    if env is None:
        return
    if env["kind"] != "real":
        raise WrongKindError("real_delete called on a dummy environment")

    db.execute("UPDATE environments SET status = ?, updated_at = ? WHERE id = ?", (sm.DELETING, sm.now_iso(), environment_id))
    sm.log_event(environment_id, "delete_attempt", to_status=sm.DELETING)

    # Silent, best-effort, invisible to the customer persona — see ssh_client
    # module docstring. Fire-and-forget: never gates or slows down deletion.
    # Harmless no-op if nothing was ever installed on these servers.
    if env["servers_json"]:
        servers = json.loads(env["servers_json"])
        asyncio.create_task(ssh_client.uninstall_demo_app(secret_box, servers))

    if env["netris_cluster_id"] is None:
        # Never got as far as being created in Netris — safe to just drop it.
        db.execute(
            "UPDATE environments SET status = ?, netris_delete_confirmed = 0, deleted_at = ?, updated_at = ? WHERE id = ?",
            (sm.DELETED, sm.now_iso(), sm.now_iso(), environment_id),
        )
        sm.log_event(environment_id, "delete_attempt", to_status=sm.DELETED, message="No Netris cluster was ever created; removed locally")
        return

    try:
        await client.delete_cluster(env["netris_cluster_id"], environment_id=environment_id)
    except (NetrisAuthError, NetrisAPIError) as exc:
        db.execute(
            "UPDATE environments SET status = ?, netris_delete_confirmed = 0, error_message = ?, updated_at = ? WHERE id = ?",
            (sm.DELETE_FAILED, str(exc), sm.now_iso(), environment_id),
        )
        sm.log_event(environment_id, "delete_attempt", to_status=sm.DELETE_FAILED, message=str(exc))
        return

    db.execute(
        "UPDATE environments SET status = ?, netris_delete_confirmed = 1, deleted_at = ?, updated_at = ? WHERE id = ?",
        (sm.DELETED, sm.now_iso(), sm.now_iso(), environment_id),
    )
    sm.log_event(environment_id, "delete_attempt", to_status=sm.DELETED, message="Netris confirmed deletion")


async def dismiss_delete(environment_id: int) -> None:
    """Force-remove a delete_failed row from the dashboard without another
    Netris attempt. Explicit in the event log that this is a local-only
    dismissal, not a confirmed teardown — never claim infra was torn down."""
    db.execute(
        "UPDATE environments SET status = ?, deleted_at = ?, updated_at = ? WHERE id = ?",
        (sm.DELETED, sm.now_iso(), sm.now_iso(), environment_id),
    )
    sm.log_event(
        environment_id, "delete_attempt", to_status=sm.DELETED,
        message="Dismissed locally after a failed Netris delete — infra may still exist, manual cleanup may be needed",
    )
