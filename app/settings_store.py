"""Reads/writes the single `app_settings` row.

Two very different kinds of data live in this one table on purpose:
- Boot-seeded, rarely-touched-again credentials (customer/operator logins,
  the session secret) — seeded from .env on first run, editable later only
  via /ops.
- Netris connection + demo-tuning knobs (base URL, site, template, GPU math)
  that start empty and are expected to be filled in / changed via /ops
  without ever needing a redeploy.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, fields
from datetime import datetime, timezone

from app import db
from app.config import ProcessConfig
from app.security import SecretBox, hash_password


@dataclass
class AppSettings:
    netris_base_url: str | None
    netris_username: str | None
    netris_password_encrypted: str | None
    netris_site_id: int | None
    netris_site_name: str | None
    netris_template_id: int | None
    netris_template_name: str | None
    netris_verify_ssl: int
    ssh_jump_host: str | None
    ssh_jump_port: int
    ssh_jump_username: str | None
    ssh_jump_password_encrypted: str | None
    demo_app_port: int
    gpus_per_server: int
    max_servers_per_request: int
    tenant_display_name: str
    customer_username: str
    customer_password_hash: str
    operator_username: str
    operator_password_hash: str
    session_secret: str
    updated_at: str

    @property
    def netris_configured(self) -> bool:
        return bool(
            self.netris_base_url
            and self.netris_username
            and self.netris_password_encrypted
            and self.netris_site_id
            and self.netris_template_id
        )

    @property
    def ssh_configured(self) -> bool:
        return bool(self.ssh_jump_host and self.ssh_jump_username and self.ssh_jump_password_encrypted)


_FIELD_NAMES = {f.name for f in fields(AppSettings)}


def _row_to_settings(row) -> AppSettings:
    return AppSettings(**{k: row[k] for k in row.keys() if k in _FIELD_NAMES})


def get_settings() -> AppSettings:
    row = db.query_one("SELECT * FROM app_settings WHERE id = 1")
    if row is None:
        raise RuntimeError("app_settings row missing — ensure_bootstrapped() was not called at startup.")
    return _row_to_settings(row)


def ensure_bootstrapped(cfg: ProcessConfig) -> None:
    """Create the singleton settings row on first boot only. Never overwrites an existing row."""
    existing = db.query_one("SELECT id FROM app_settings WHERE id = 1")
    if existing is not None:
        return
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO app_settings (
            id, gpus_per_server, max_servers_per_request, tenant_display_name,
            customer_username, customer_password_hash,
            operator_username, operator_password_hash,
            session_secret, updated_at
        ) VALUES (1, 8, 16, 'HackMeCorp', ?, ?, ?, ?, ?, ?)
        """,
        (
            cfg.seed_customer_username,
            hash_password(cfg.seed_customer_password),
            cfg.seed_operator_username,
            hash_password(cfg.seed_operator_password),
            cfg.session_secret or secrets.token_hex(32),
            now,
        ),
    )


def update_settings(secret_box: SecretBox, **fields) -> AppSettings:
    """Partial update. `netris_password` (plain) encrypts to netris_password_encrypted if present.
    `customer_password` / `operator_password` (plain) hash into their *_hash columns if present.
    Any field left unset (or explicitly None) leaves the stored value untouched."""
    current = get_settings()
    updates: dict = {}

    plain_netris_password = fields.pop("netris_password", None)
    if plain_netris_password:
        updates["netris_password_encrypted"] = secret_box.encrypt(plain_netris_password)

    plain_customer_password = fields.pop("customer_password", None)
    if plain_customer_password:
        updates["customer_password_hash"] = hash_password(plain_customer_password)

    plain_operator_password = fields.pop("operator_password", None)
    if plain_operator_password:
        updates["operator_password_hash"] = hash_password(plain_operator_password)

    plain_ssh_password = fields.pop("ssh_jump_password", None)
    if plain_ssh_password:
        updates["ssh_jump_password_encrypted"] = secret_box.encrypt(plain_ssh_password)

    for key, value in fields.items():
        if value is not None and hasattr(current, key):
            updates[key] = value

    if not updates:
        return current

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    db.execute(f"UPDATE app_settings SET {set_clause} WHERE id = 1", tuple(updates.values()))
    return get_settings()
