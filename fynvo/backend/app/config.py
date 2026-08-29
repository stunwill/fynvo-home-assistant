import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

APP_VERSION = "1.16.0"


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
