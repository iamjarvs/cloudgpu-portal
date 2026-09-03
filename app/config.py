"""Process-level configuration read from the environment at startup.

This is deliberately separate from `app_settings` in the database: everything
here is boot-time wiring (where the DB lives, what secret signs cookies, what
credentials seed the two logins on first run). Anything the operator should be
able to change later without a redeploy (Netris connection, site/template,
GPU math, tenant branding) lives in the DB and is edited via /ops instead.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill it in before starting the app."
        )
    return value


@dataclass(frozen=True)
class ProcessConfig:
    db_path: Path
    port: int
    fernet_key: str
    session_secret: str
    seed_customer_username: str
    seed_customer_password: str
    seed_operator_username: str
    seed_operator_password: str


def load_config() -> ProcessConfig:
    return ProcessConfig(
        db_path=BASE_DIR / os.environ.get("DB_PATH", "data/portal.db"),
        port=int(os.environ.get("PORT", "8000")),
        fernet_key=_require("FERNET_KEY"),
        session_secret=_require("SESSION_SECRET"),
        seed_customer_username=_require("CUSTOMER_USERNAME"),
        seed_customer_password=_require("CUSTOMER_PASSWORD"),
        seed_operator_username=_require("OPERATOR_USERNAME"),
        seed_operator_password=_require("OPERATOR_PASSWORD"),
    )
