import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from pydantic import BaseModel
APP_VERSION = "1.9.0"
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

def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data_dir = Path(os.getenv("FYNVO_DATA_DIR", "/data")); data_dir.mkdir(parents=True, exist_ok=True)
    options = _read_json(Path(os.getenv("FYNVO_OPTIONS_FILE", "/data/options.json")))
    session_days = int(os.getenv("FYNVO_SESSION_DAYS", options.get("session_days", 7) or 7))
    return Settings(data_dir=data_dir,database_url=os.getenv("FYNVO_DATABASE_URL", f"sqlite:///{data_dir / 'fynvo.db'}"),timezone=os.getenv("FYNVO_TIMEZONE", "Australia/Melbourne"),currency=os.getenv("FYNVO_CURRENCY", "AUD"),session_days=session_days,session_expiry_minutes=session_days*24*60,session_cookie_name=os.getenv("FYNVO_SESSION_COOKIE", "fynvo_session"),cookie_secure=os.getenv("FYNVO_COOKIE_SECURE", "false").lower()=="true",admin_username=options.get("admin_username") or None,admin_display_name=options.get("admin_display_name") or None,admin_password=options.get("admin_password") or None,admin_recovery_mode=bool(options.get("admin_recovery_mode",False)))
