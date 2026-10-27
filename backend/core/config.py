"""Application configuration (pydantic-settings).

Every value can be set with an environment variable prefixed HRMS_ or in a `.env`
file in the project root, e.g.

    HRMS_DATABASE_URL=postgresql://user:pass@localhost:5432/hr_system
    HRMS_SECRET_KEY=...            (default: random key kept in backend/.secret_key)
    HRMS_SMTP_PASSWORD=...         (overrides the SMTP password stored in Settings)
    HRMS_TRUSTED_PROXIES=127.0.0.1 (reverse proxies allowed to set X-Forwarded-For)
    HRMS_LOG_LEVEL=INFO
    HRMS_DEMO_PASSWORD_CHANGE=false (let the demo accounts keep their public passwords)
"""
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
SECRET_FILE = BACKEND_DIR / ".secret_key"


def _generated_secret() -> str:
    """A random key created once and kept in backend/.secret_key (git-ignored)."""
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    key = secrets.token_urlsafe(48)
    SECRET_FILE.write_text(key)
    return key


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HRMS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./hr_system.db"
    secret_key: str = Field(default_factory=_generated_secret)
    jwt_algorithm: str = "HS256"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    # reverse proxies (nginx/Caddy) whose X-Forwarded-For header is trusted for the client IP
    trusted_proxies: list[str] = []
    # optional: keep the SMTP password out of the database entirely
    smtp_password: str | None = None
    # login protection
    login_max_failures: int = 5
    login_lockout_minutes: int = 15
    # a sign-in with a demo account's public password must first choose a new password
    demo_password_change: bool = True


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()


config = get_config()
