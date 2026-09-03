"""Status constants and the audit-trail/status-write helpers shared by the
orchestrator, worker, and delete flow. The actual transition logic lives in
orchestrator.py — this module just names the states and gives one place to
write a status change plus its corresponding environment_events row.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app import db

QUEUED = "queued"
PROVISIONING_COMPUTE = "provisioning_compute"
AWAITING_NETWORK = "awaiting_network"
STALLED = "stalled"
ACTIVE = "active"
FAILED = "failed"
DELETING = "deleting"
DELETED = "deleted"
DELETE_FAILED = "delete_failed"

NON_TERMINAL = [QUEUED, PROVISIONING_COMPUTE, AWAITING_NETWORK, STALLED, DELETING]
TERMINAL = [ACTIVE, FAILED, DELETED, DELETE_FAILED]

# Split of NON_TERMINAL used by worker.BackgroundTaskManager on boot: rows in
# these statuses resume the provisioning coroutine; DELETING rows instead
# resume the delete flow (see resume_pending_deletes).
RESUMABLE_PROVISIONING = [QUEUED, PROVISIONING_COMPUTE, AWAITING_NETWORK, STALLED]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(
    environment_id: int,
    event_type: str,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
    message: str | None = None,
    raw_payload: str | None = None,
) -> None:
    db.execute(
        """INSERT INTO environment_events
           (environment_id, at, event_type, from_status, to_status, message, raw_payload)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (environment_id, now_iso(), event_type, from_status, to_status, message, raw_payload),
    )


def set_status(
    environment_id: int,
    new_status: str,
    *,
    from_status: str | None = None,
    status_detail: str | None = None,
    error_message: str | None = None,
) -> None:
    db.execute(
        "UPDATE environments SET status = ?, status_detail = ?, error_message = ?, updated_at = ? WHERE id = ?",
        (new_status, status_detail, error_message, now_iso(), environment_id),
    )
    log_event(
        environment_id,
        "state_change",
        from_status=from_status,
        to_status=new_status,
        message=status_detail or error_message,
    )
