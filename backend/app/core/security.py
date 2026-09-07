"""Symmetric encryption for sensitive values (API keys) stored in the DB."""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet = Fernet(settings.fernet_key)


def encrypt_secret(plaintext: str | None) -> str | None:
    if not plaintext:
        return None
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # If the key changed or value is not encrypted, fail closed.
        return None
