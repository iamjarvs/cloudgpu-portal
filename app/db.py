"""SQLite access layer.

Deliberately raw `sqlite3` (stdlib), no ORM/migration framework — this app is
single-instance, low-traffic, and the schema is small enough that a plain
`CREATE TABLE IF NOT EXISTS` per table is all the "migration" story it needs.

sqlite3 is a blocking API, and a single `sqlite3.Connection` object is NOT
safe to use concurrently from multiple threads even with
`check_same_thread=False` (that flag only lifts the same-thread restriction,
it doesn't add locking) — FastAPI's sync `def` route handlers run in a
worker thread pool, so two simultaneous GET requests really could call
`.execute()` on the same shared connection at the same time. This showed up
in practice as an intermittent `sqlite3.InterfaceError: bad parameter or
other API misuse` once Netris API-call logging made writes frequent enough
to collide with concurrent reads.

The fix: each OS thread gets its own connection (all pointing at the same
file, in WAL mode, which is what actually provides safe concurrent access)
via `threading.local()`. Writes are additionally serialized through a
process-wide lock — WAL still only allows one writer at a time, and the
lock turns that contention into a wait instead of a "database is locked"
error surfacing to a caller.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

_write_lock = threading.Lock()
_local = threading.local()
_db_path: Path | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    netris_base_url TEXT,
    netris_username TEXT,
    netris_password_encrypted TEXT,
    netris_site_id INTEGER,
    netris_site_name TEXT,
    netris_template_id INTEGER,
    netris_template_name TEXT,
    netris_verify_ssl INTEGER NOT NULL DEFAULT 0,
    ssh_jump_host TEXT,
    ssh_jump_port INTEGER NOT NULL DEFAULT 22,
    ssh_jump_username TEXT,
    ssh_jump_password_encrypted TEXT,
    demo_app_port INTEGER NOT NULL DEFAULT 8080,
    gpus_per_server INTEGER NOT NULL DEFAULT 8,
    max_servers_per_request INTEGER NOT NULL DEFAULT 16,
    tenant_display_name TEXT NOT NULL DEFAULT 'HackMeCorp',
    customer_username TEXT NOT NULL,
    customer_password_hash TEXT NOT NULL,
    operator_username TEXT NOT NULL,
    operator_password_hash TEXT NOT NULL,
    session_secret TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS environments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    netris_name TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('dummy', 'real')),
    requested_server_count INTEGER NOT NULL,
    gpus_per_server INTEGER NOT NULL,
    status TEXT NOT NULL,
    status_detail TEXT,
    error_message TEXT,
    fake_sim_started_at TEXT,
    fake_sim_done_at TEXT,
    netris_cluster_id INTEGER,
    netris_vpc_id INTEGER,
    netris_vpc_name TEXT,
    netris_status_label TEXT,
    netris_status_value TEXT,
    netris_last_polled_at TEXT,
    netris_delete_confirmed INTEGER,
    servers_json TEXT,
    subnets_json TEXT,
    seed_key TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_environments_status ON environments(status);

CREATE TABLE IF NOT EXISTS environment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    environment_id INTEGER NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
    at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    message TEXT,
    raw_payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_env_id ON environment_events(environment_id, at);
"""

# `CREATE TABLE IF NOT EXISTS` above only helps a brand-new database — it's a
# no-op against a table that already exists, so a column added to SCHEMA
# after first deploy would silently never appear on a live database. Each
# entry here is applied with `ALTER TABLE ADD COLUMN` exactly once (guarded
# by checking it doesn't already exist), so existing databases pick up
# columns added after their initial creation. Append to this list — never
# remove or edit past entries — whenever a new column is added to SCHEMA.
_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("app_settings", "ssh_jump_host", "TEXT"),
    ("app_settings", "ssh_jump_port", "INTEGER NOT NULL DEFAULT 22"),
    ("app_settings", "ssh_jump_username", "TEXT"),
    ("app_settings", "ssh_jump_password_encrypted", "TEXT"),
    ("app_settings", "demo_app_port", "INTEGER NOT NULL DEFAULT 8080"),
    ("environments", "netris_extras_json", "TEXT"),
]


def _apply_column_migrations(conn: sqlite3.Connection) -> None:
    for table, column, ddl in _COLUMN_MIGRATIONS:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _connect() -> sqlite3.Connection:
    if _db_path is None:
        raise RuntimeError("Database not initialized — call init_db() at startup first.")
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path) -> sqlite3.Connection:
    global _db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    _db_path = path
    conn = _connect()
    conn.executescript(SCHEMA)
    _apply_column_migrations(conn)
    conn.commit()
    _local.conn = conn
    return conn


def get_db() -> sqlite3.Connection:
    if _db_path is None:
        raise RuntimeError("Database not initialized — call init_db() at startup first.")
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _connect()
        _local.conn = conn
    return conn


def close_db() -> None:
    """Closes only the calling thread's own connection — each thread owns
    its own, so there's no single connection to close on process shutdown.
    Fine for a small demo app: the OS reclaims the rest on process exit."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def execute(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
    """Serialized write helper — use for INSERT/UPDATE/DELETE."""
    with _write_lock:
        conn = get_db()
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def query_one(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return get_db().execute(sql, params).fetchone()


def query_all(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()
