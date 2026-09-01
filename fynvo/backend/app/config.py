import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

APP_VERSION = "1.17.1"


class Settings(BaseModel):
    data_dir: Path
    database_url: str
    timezone: str = "Australia/Melbourne"
    currency: str = "AUD"
    session_days: int = 7
    session_expiry_minutes: int = 60 * 24 * 7
    session_cookie_name: str = "fynvo_session"
    cookie_secure: bool = False
    admin_username: str = ""
    admin_display_name: str = ""
    admin_password: str = ""
    admin_recovery_mode: bool = False


def _load_addon_options() -> dict[str, Any]:
    path = Path("/data/options.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _option(options: dict[str, Any], env_name: str, option_name: str, default: Any) -> Any:
    if env_name in os.environ:
        return os.environ[env_name]
    return options.get(option_name, default)


@lru_cache
def get_settings() -> Settings:
    options = _load_addon_options()
    data_dir = Path(os.getenv("FYNVO_DATA_DIR", "/data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    session_days = int(_option(options, "FYNVO_SESSION_DAYS", "session_days", 7) or 7)
    session_days = max(1, min(session_days, 30))
    return Settings(
        data_dir=data_dir,
        database_url=os.getenv("FYNVO_DATABASE_URL", f"sqlite:///{data_dir / 'fynvo.db'}"),
        timezone=os.getenv("FYNVO_TIMEZONE", "Australia/Melbourne"),
        currency=os.getenv("FYNVO_CURRENCY", "AUD"),
        session_days=session_days,
        session_expiry_minutes=session_days * 24 * 60,
        session_cookie_name=os.getenv("FYNVO_SESSION_COOKIE", "fynvo_session"),
        cookie_secure=os.getenv("FYNVO_COOKIE_SECURE", "false").lower() == "true",
        admin_username=str(_option(options, "FYNVO_ADMIN_USERNAME", "admin_username", "") or "").strip(),
        admin_display_name=str(_option(options, "FYNVO_ADMIN_DISPLAY_NAME", "admin_display_name", "") or "").strip(),
        admin_password=str(_option(options, "FYNVO_ADMIN_PASSWORD", "admin_password", "") or ""),
        admin_recovery_mode=str(_option(options, "FYNVO_ADMIN_RECOVERY_MODE", "admin_recovery_mode", False)).lower() in {"1", "true", "yes", "on"},
    )
