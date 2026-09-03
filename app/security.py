"""Password hashing, secret-at-rest encryption, and constant-time comparisons.

Two independent credential pairs live in the DB (customer session login,
operator Basic-Auth login) plus one encrypted secret (the Netris password).
Nothing here is shared between the customer and operator auth domains —
see app/routers/auth.py (customer) vs app/ops/router.py (operator).
"""
from __future__ import annotations

import hmac

import bcrypt
from cryptography.fernet import Fernet, InvalidToken


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


class SecretBox:
    """Thin wrapper so call sites never touch the Fernet key directly."""

    def __init__(self, fernet_key: str):
        self._fernet = Fernet(fernet_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError(
                "Could not decrypt stored Netris password — FERNET_KEY may have changed."
            ) from exc
