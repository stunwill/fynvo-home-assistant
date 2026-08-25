import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

APP_VERSION = "1.11.0"


class Settings(BaseModel):
    data_dir: Path
    database_url: str
    timezone: str = "Australia/Melbourne"
    currency: str = "AUD"
    session_days: int = 7
    session_expiry_minutes: int = 60 * 24 * 7
    session_cookie_name: str = "fynvo_session"
    cookie_secure: bool = False
    max_login_attempts: int = 5
    login_attempt_window_seconds: int = 15 * 60
    admin_username: str | None = None
    admin_display_name: str | None = None
    admin_password: str | None = None
    admin_recovery_mode: bool = False
    options_source: str = "none"


def _read_addon_options(data_dir: Path) -> tuple[dict[str, Any], str]:
    option_paths = [
        Path(os.getenv("FYNVO_OPTIONS_FILE", "")) if os.getenv("FYNVO_OPTIONS_FILE") else None,
        data_dir / "options.json",
        Path("/data/options.json"),
    ]
    seen: set[Path] = set()
    for path in option_paths:
        if path is None:
            continue
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.exists():
            continue
        try:
            with resolved.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {}, str(resolved)
        return (data if isinstance(data, dict) else {}), str(resolved)
    return {}, "none"


def _option(options: dict[str, Any], key: str, env: str, default: Any = None) -> Any:
    value = os.getenv(env)
    if value not in (None, ""):
        return value
    return options.get(key, default)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.getenv("FYNVO_DATA_DIR", "/data"))
    options, options_source = _read_addon_options(data_dir)
    database_url = os.getenv("FYNVO_DATABASE_URL", f"sqlite:///{data_dir / 'fynvo.sqlite3'}")
    cookie_secure = _bool(_option(options, "cookie_secure", "FYNVO_COOKIE_SECURE", "false"))
    session_days = int(_option(options, "session_days", "FYNVO_SESSION_DAYS", "7") or 7)
    return Settings(
        data_dir=data_dir,
        database_url=database_url,
        cookie_secure=cookie_secure,
        session_days=session_days,
        session_expiry_minutes=session_days * 24 * 60,
        admin_username=_option(options, "admin_username", "FYNVO_ADMIN_USERNAME"),
        admin_display_name=_option(options, "admin_display_name", "FYNVO_ADMIN_DISPLAY_NAME"),
        admin_password=_option(options, "admin_password", "FYNVO_ADMIN_PASSWORD"),
        admin_recovery_mode=_bool(_option(options, "admin_recovery_mode", "FYNVO_ADMIN_RECOVERY_MODE", False)),
        options_source=options_source if not any(os.getenv(name) for name in ("FYNVO_ADMIN_USERNAME", "FYNVO_ADMIN_PASSWORD", "FYNVO_ADMIN_RECOVERY_MODE", "FYNVO_SESSION_DAYS")) else "environment",
    )
