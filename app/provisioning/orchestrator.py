"""Per-environment provisioning coroutine.

Runs the fake compute animation and the real Netris allocate/create/poll
flow concurrently, and gates `active` on *both* — Netris is always the
authoritative network gate, however long it takes. See `_try_finalize`,
which is the one place that decision is made, called from both sides
whenever either one reaches a point that might unblock the other.

Only ever invoked for `kind == 'real'` environments — dummy rows are
inserted directly as already `active` by app/seed.py and never touch this
module (see resume_all_incomplete in worker.py, which only ever finds
non-terminal real rows).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from app import db, settings_store, ssh_client
from app.netris.client import NetrisClient
from app.netris.exceptions import NetrisAPIError, NetrisAuthError, NetrisCapacityError
from app.provisioning import extras, fake_compute
from app.provisioning import state_machine as sm
from app.security import SecretBox

logger = logging.getLogger("provisioning")

POLL_INTERVAL_SECONDS = 5
STALL_THRESHOLD_SECONDS = 20 * 60
STALLED_POLL_INTERVAL_SECONDS = 30

NETRIS_TERMINAL_SUCCESS = {"active", "success"}
NETRIS_TERMINAL_ERROR = {"error", "failed"}

# Serializes allocate+create across all concurrently-provisioning environments —
# Netris has no compare-and-swap on server assignment, so two near-simultaneous
# creates could otherwise claim the same servers.
_netris_allocation_lock = asyncio.Lock()


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_environment(environment_id: int) -> dict | None:
    row = db.query_one("SELECT * FROM environments WHERE id = ?", (environment_id,))
    return _row_to_dict(row) if row else None


async def run_provisioning(environment_id: int, netris_client: NetrisClient, secret_box: SecretBox) -> None:
    """Entry point for both a freshly created environment and a resumed one
    after a restart (see worker.BackgroundTaskManager.resume_all_incomplete).
    Wrapped by the caller in a blanket exception handler — this function only
    needs to handle *expected* Netris/capacity failures cleanly."""
    env = get_environment(environment_id)
    if env is None or env["status"] in sm.TERMINAL:
        return
    if env["kind"] != "real":
        logger.warning("run_provisioning called for non-real environment %s; ignoring", environment_id)
        return

    if env["fake_sim_started_at"] is None:
        now = sm.now_iso()
        db.execute(
            "UPDATE environments SET status = ?, fake_sim_started_at = ?, updated_at = ? WHERE id = ?",
            (sm.PROVISIONING_COMPUTE, now, now, environment_id),
        )
        sm.log_event(environment_id, "state_change", from_status=env["status"], to_status=sm.PROVISIONING_COMPUTE)

    fake_task = asyncio.create_task(_run_fake_compute(environment_id, secret_box))
    netris_task = asyncio.create_task(_run_real_netris_flow(environment_id, netris_client, fake_task, secret_box))
    await asyncio.gather(fake_task, netris_task, return_exceptions=True)


async def _run_fake_compute(environment_id: int, secret_box: SecretBox) -> None:
    env = get_environment(environment_id)
    seed = env["uuid"]
    started_at = datetime.fromisoformat(env["fake_sim_started_at"])
    total = fake_compute.total_duration_seconds(seed)

    last_logged_step = -2  # sentinel, never a real step index
    while True:
        progress = fake_compute.progress_at(seed, started_at)
        db.execute(
            "UPDATE environments SET status_detail = ?, updated_at = ? WHERE id = ?",
            (progress.current_step_label or "Compute provisioning complete", sm.now_iso(), environment_id),
        )
        if progress.current_step_index != last_logged_step:
            sm.log_event(
                environment_id, "fake_step",
                message=progress.current_step_label or "Compute provisioning complete",
            )
            last_logged_step = progress.current_step_index
        if progress.done:
            db.execute(
                "UPDATE environments SET fake_sim_done_at = ?, updated_at = ? WHERE id = ?",
                (sm.now_iso(), sm.now_iso(), environment_id),
            )
            _try_finalize(environment_id, secret_box)
            return
        await asyncio.sleep(min(2.0, max(0.5, total - progress.elapsed_seconds)))


async def _allocate_and_create_if_needed(environment_id: int, client: NetrisClient, settings) -> None:
    env = get_environment(environment_id)
    if env["netris_cluster_id"] is not None:
        return  # already created & located, nothing to do

    # Resume safety: a previous run may have crashed after the create call
    # actually succeeded on Netris but before we recorded netris_cluster_id.
    # Check by name before ever creating (or re-creating) anything.
    existing = await client.get_cluster_by_name(env["netris_name"], environment_id=environment_id)
    if existing is not None:
        _store_cluster_snapshot(environment_id, existing)
        sm.log_event(environment_id, "netris_poll", message="Found existing cluster by name on resume; skipped create")
        return

    if env["servers_json"] is not None:
        servers = json.loads(env["servers_json"])
    else:
        servers = await client.pick_servers_for_request(
            settings.netris_site_id, env["requested_server_count"], environment_id=environment_id
        )
        db.execute(
            "UPDATE environments SET servers_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(servers), sm.now_iso(), environment_id),
        )

    # The `admin` field must reflect whoever actually authenticated, not a
    # hardcoded placeholder — Netris ties create permission to this identity,
    # and a mismatch here is rejected with a 403 even for an account that
    # genuinely has create rights.
    admin_id, admin_name = await client.get_admin_identity()

    await client.create_cluster(
        name=env["netris_name"],
        admin_id=admin_id,
        admin_name=admin_name,
        site_id=settings.netris_site_id,
        site_name=settings.netris_site_name,
        template_id=settings.netris_template_id,
        template_name=settings.netris_template_name,
        servers=servers,
        environment_id=environment_id,
    )
    sm.log_event(environment_id, "netris_poll", message="Cluster create request sent")


def _store_cluster_snapshot(environment_id: int, cluster: dict) -> None:
    vpc = cluster.get("vpc") or {}
    status = cluster.get("status") or {}
    db.execute(
        """UPDATE environments SET netris_cluster_id = ?, netris_vpc_id = ?, netris_vpc_name = ?,
           netris_status_label = ?, netris_status_value = ?, netris_last_polled_at = ?,
           subnets_json = ?, updated_at = ? WHERE id = ?""",
        (
            cluster.get("id"),
            vpc.get("id"),
            vpc.get("name"),
            status.get("label"),
            status.get("value") or cluster.get("state"),
            sm.now_iso(),
            json.dumps(cluster.get("resources") or {}),
            sm.now_iso(),
            environment_id,
        ),
    )


async def _run_real_netris_flow(
    environment_id: int, client: NetrisClient, fake_task: asyncio.Task, secret_box: SecretBox
) -> None:
    settings = settings_store.get_settings()

    try:
        async with _netris_allocation_lock:
            await _allocate_and_create_if_needed(environment_id, client, settings)
    except NetrisCapacityError as exc:
        sm.set_status(environment_id, sm.FAILED, error_message=str(exc))
        fake_task.cancel()
        return
    except (NetrisAuthError, NetrisAPIError) as exc:
        sm.set_status(environment_id, sm.FAILED, error_message=f"Netris error: {exc}")
        fake_task.cancel()
        return

    started_polling_at = datetime.now(timezone.utc)

    while True:
        env = get_environment(environment_id)
        if env is None or env["status"] == sm.FAILED:
            return

        try:
            if env["netris_cluster_id"] is not None:
                cluster = await client.get_cluster_by_id(env["netris_cluster_id"], environment_id=environment_id)
            else:
                cluster = await client.get_cluster_by_name(env["netris_name"], environment_id=environment_id)
        except (NetrisAuthError, NetrisAPIError) as exc:
            sm.log_event(environment_id, "error", message=f"Poll failed, will retry: {exc}")
            cluster = None

        if cluster is not None:
            _store_cluster_snapshot(environment_id, cluster)
            await extras.create_all_pending(environment_id, client, settings)
            status_value = (cluster.get("status") or {}).get("value") or cluster.get("state")
            status_label = (cluster.get("status") or {}).get("label")
            if status_value in NETRIS_TERMINAL_SUCCESS:
                _try_finalize(environment_id, secret_box)
                return
            if status_value in NETRIS_TERMINAL_ERROR:
                sm.set_status(
                    environment_id, sm.FAILED,
                    error_message=f"Netris reported an error state: {status_label or status_value}",
                )
                fake_task.cancel()
                return

        elapsed = (datetime.now(timezone.utc) - started_polling_at).total_seconds()
        if elapsed > STALL_THRESHOLD_SECONDS:
            current = get_environment(environment_id)
            if current and current["status"] in sm.NON_TERMINAL and current["status"] != sm.STALLED:
                db.execute(
                    "UPDATE environments SET status = ?, updated_at = ? WHERE id = ?",
                    (sm.STALLED, sm.now_iso(), environment_id),
                )
                sm.log_event(
                    environment_id, "state_change", to_status=sm.STALLED,
                    message="Netris hasn't confirmed active yet; slowing poll cadence and continuing to wait.",
                )
            await asyncio.sleep(STALLED_POLL_INTERVAL_SECONDS)
        else:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def _try_finalize(environment_id: int, secret_box: SecretBox) -> None:
    """Called whenever either the fake animation or the Netris poll reaches a
    point that might unblock the other. Active only when both sides agree."""
    env = get_environment(environment_id)
    if env is None or env["status"] in (sm.FAILED, sm.ACTIVE, sm.DELETING, sm.DELETED, sm.DELETE_FAILED):
        return
    if env["fake_sim_done_at"] is None:
        return  # compute animation not done yet; nothing to finalize

    netris_ok = env["netris_status_value"] in NETRIS_TERMINAL_SUCCESS
    if not netris_ok:
        if env["status"] not in (sm.STALLED, sm.AWAITING_NETWORK):
            db.execute(
                "UPDATE environments SET status = ?, updated_at = ? WHERE id = ?",
                (sm.AWAITING_NETWORK, sm.now_iso(), environment_id),
            )
            sm.log_event(
                environment_id, "state_change", to_status=sm.AWAITING_NETWORK,
                message="Compute provisioning complete; waiting on Netris network fabric confirmation",
            )
        return

    db.execute("UPDATE environments SET status = ?, updated_at = ? WHERE id = ?", (sm.ACTIVE, sm.now_iso(), environment_id))
    sm.log_event(environment_id, "state_change", to_status=sm.ACTIVE)

    # Silent, best-effort, invisible to the customer persona — see ssh_client
    # module docstring. Fire-and-forget: never gates the ACTIVE transition.
    if env["servers_json"]:
        servers = json.loads(env["servers_json"])
        asyncio.create_task(ssh_client.install_demo_app(secret_box, servers))
