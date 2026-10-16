"""Encryption of secrets stored in the database (e.g. the SMTP password).

Values are encrypted with Fernet (AES + HMAC) using a key derived from the app's
secret key, and stored as 'enc:<token>'. Keep backend/.secret_key (or
HRMS_SECRET_KEY) safe: without it stored secrets cannot be decrypted.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import config

PREFIX = "enc:"


def _fernet() -> Fernet:
    key = hashlib.sha256(("hrms-secrets:" + config.secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    if not value:
        return ""
    return PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Plain values from older versions are returned unchanged."""
    if not value or not value.startswith(PREFIX):
        return value or ""
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        return ""  # secret key changed: the stored secret must be entered again
