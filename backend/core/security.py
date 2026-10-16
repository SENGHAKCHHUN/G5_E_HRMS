"""Password hashing (pwdlib: Argon2, still verifies old bcrypt hashes) and JWT access tokens (PyJWT)."""
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from .config import config

ADMIN = "Admin"
HR = "HR Manager"
EMPLOYEE = "Employee"
STAFF = (ADMIN, HR)

# New hashes use Argon2 (current OWASP recommendation); bcrypt hashes from older versions
# still verify and are upgraded at the next successful login (see verify_and_update).
_hasher = PasswordHash((Argon2Hasher(), BcryptHasher()))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def verify_and_update(password: str, password_hash: str) -> tuple[bool, str | None]:
    """(valid, new_hash): new_hash is set when the stored hash uses an outdated algorithm."""
    return _hasher.verify_and_update(password, password_hash)


def temporary_password() -> str:
    """Readable one-time password, e.g. 'Kx7m-Qp42-Wd9r'."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))


def password_stamp(password_hash: str) -> str:
    """Changes whenever the password changes, so older tokens stop working."""
    return password_hash[-10:]


def create_access_token(user_id: int, role: str, password_hash: str, hours: int) -> str:
    now = datetime.now(UTC)
    claims = {"sub": str(user_id), "role": role, "pw": password_stamp(password_hash),
              "iat": now, "exp": now + timedelta(hours=hours)}
    return jwt.encode(claims, config.secret_key, algorithm=config.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Return the token claims, or None when the token is invalid or expired."""
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.jwt_algorithm],
                             options={"require": ["sub", "exp"]})
        int(payload["sub"])
        return payload
    except (jwt.PyJWTError, ValueError):
        return None
