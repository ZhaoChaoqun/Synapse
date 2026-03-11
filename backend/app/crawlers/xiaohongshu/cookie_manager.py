"""Cookie manager for Xiaohongshu crawler."""

import json
from pathlib import Path
from typing import Any


COOKIE_FILE = Path(__file__).parent / "cookies.json"


class CookieManager:
    """Manage browser cookies for Xiaohongshu login persistence."""

    @staticmethod
    def save_cookies(storage_state: dict[str, Any]) -> None:
        """Save browser storage state to file."""
        COOKIE_FILE.write_text(json.dumps(storage_state, ensure_ascii=False, indent=2))

    @staticmethod
    def load_cookies() -> dict[str, Any] | None:
        """Load saved cookies from file."""
        if COOKIE_FILE.exists():
            try:
                return json.loads(COOKIE_FILE.read_text())
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def is_logged_in(storage_state: dict[str, Any]) -> bool:
        """Check if user is logged in by examining cookies."""
        cookies = storage_state.get("cookies", [])
        # Check for Xiaohongshu login-related cookies
        login_cookie_names = {"web_session", "xsecappid", "a1", "webId"}
        for cookie in cookies:
            if cookie.get("name") in login_cookie_names:
                return True
        return False

    @staticmethod
    def clear_cookies() -> None:
        """Remove saved cookies."""
        if COOKIE_FILE.exists():
            COOKIE_FILE.unlink()
