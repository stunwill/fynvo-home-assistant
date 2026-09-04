import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

APP_VERSION = "1.17.6"


class Settings(BaseModel):
    data_dir: Path
    database_url: str
    timezone: str = "Australia/Melbourne"
    currency: str = "AUD"
    session_days: int = 7
    session_expiry_minutes: int = 60 * 24 * 7
    session_cookie_name: str = "fynvo_session"
    cookie_secure: bool = False