"""Tracks one asyncio.Task per environment and guarantees none of them can
die silently — an unhandled exception still leaves the row in a terminal,
explained state instead of hanging forever with nothing left running to
finish it. Also responsible for resuming any environment left mid-flight by
a restart.
"""
from __future__ import annotations

import asyncio
import logging

from app import db
from app.netris.client import NetrisClient
from app.netris.exceptions import NetrisAPIError, NetrisAuthError
from app.provisioning import delete_flow, orchestrator
from app.provisioning import state_machine as sm
from app.security import SecretBox

logger = logging.getLogger("worker")


class BackgroundTaskManager:
    def __init__(self, netris_client: NetrisClient, secret_box: SecretBox):
        self._netris_client = netris_client
        self._secret_box = secret_box
        self._tasks: dict[int, asyncio.Task] = {}

    def start_provisioning(self, environment_id: int) -> None:
        if environment_id in self._tasks:
            return  # already running, don't double-schedule
        task = asyncio.create_task(self._run_guarded(environment_id))
        self._tasks[environment_id] = task
        task.add_done_callback(lambda _t, eid=environment_id: self._tasks.pop(eid, None))

    async def _run_guarded(self, environment_id: int) -> None:
        try:
            await orchestrator.run_provisioning(environment_id, self._netris_client, self._secret_box)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Provisioning task for environment %s crashed", environment_id)
            db.execute(
                "UPDATE environments SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (sm.FAILED, "Internal error during provisioning — see server logs.", sm.now_iso(), environment_id),
            )
            sm.log_event(environment_id, "error", to_status=sm.FAILED, message="Unhandled exception, see server logs")

    def cancel(self, environment_id: int) -> None:
        task = self._tasks.get(environment_id)
        if task is not None and not task.done():
            task.cancel()

    def resume_all_incomplete(self) -> None:
        """Called once at startup. Rows left mid-provisioning resume the
        orchestrator; rows left mid-delete resume the delete flow instead —
        never the same path, a stuck delete must not re-enter provisioning."""
        placeholders = ",".join("?" * len(sm.RESUMABLE_PROVISIONING))
        rows = db.query_all(
            f"SELECT id FROM environments WHERE kind = 'real' AND status IN ({placeholders})",
            tuple(sm.RESUMABLE_PROVISIONING),
        )
        for row in rows:
            logger.info("Resuming provisioning for environment %s after restart", row["id"])
            self.start_provisioning(row["id"])

        deleting_rows = db.query_all("SELECT id, kind FROM environments WHERE status = ?", (sm.DELETING,))
        for row in deleting_rows:
            logger.info("Resuming delete for environment %s after restart", row["id"])
            asyncio.create_task(self._resume_delete(row["id"], row["kind"]))

    async def _resume_delete(self, environment_id: int, kind: str) -> None:
        try:
            if kind == "dummy":
                await delete_flow.dummy_delete(environment_id)
            else:
                await delete_flow.real_delete(environment_id, self._netris_client, self._secret_box)
        except (NetrisAuthError, NetrisAPIError):
            logger.exception("Resumed delete for environment %s failed", environment_id)
