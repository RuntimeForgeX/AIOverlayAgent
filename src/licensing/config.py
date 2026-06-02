"""License-related settings: config.ini [LICENSE] is the ONLY source of truth.

All LICENSE_* values are baked in at build time via config.ini — they are
never read from os.environ or .env at runtime.

  LICENSE_AUTH      = 1  (hardcoded — always required, cannot be overridden)
  LICENSE_NODE_PORT = from config.ini [LICENSE] node_port
  activate_base_url = from config.ini [LICENSE] activate_base_url
  get_license_url   = from config.ini [LICENSE] get_license_url
  activate_path     = from config.ini [LICENSE] activate_path
"""

import sys

from src.config.settings import get_config_value

_DEFAULT_NODE_PORT = "3000"
_DEFAULT_BASE_URL  = "http://localhost:3000"
_DEFAULT_GET_URL   = "http://localhost:3000/request"
_DEFAULT_PATH      = "/api/activate"


def _is_frozen_app() -> bool:
    """True when running from a packaged executable (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


# ─────────────────────────────────────────────────────────────────────────────
# LICENSE_AUTH = 1  (build-time constant — no env / .env override)
# ─────────────────────────────────────────────────────────────────────────────

def is_license_auth_required() -> bool:
    """
    Always True — LICENSE_AUTH is fixed to 1 at build time.
    This value is never read from os.environ or .env.
    """
    return True


def license_bypass_enabled() -> bool:
    return not is_license_auth_required()


# ─────────────────────────────────────────────────────────────────────────────
# URL / path settings — read from config.ini [LICENSE] only
# ─────────────────────────────────────────────────────────────────────────────

def _cfg_str(config, key: str, default: str) -> str:
    """Read a key from config.ini [LICENSE] with a hard-coded fallback."""
    return (get_config_value(config, "LICENSE", key, default) or default).strip()


def get_license_settings(config):
    """Read license URLs and paths from config.ini [LICENSE] only.

    These values are fixed at build time and cannot be changed at runtime.
    """
    port = _cfg_str(config, "node_port", _DEFAULT_NODE_PORT)
    default_base = f"http://localhost:{port}"

    base = _cfg_str(config, "activate_base_url", default_base).rstrip("/")

    get_url = _cfg_str(config, "get_license_url", f"{default_base}/request")

    filename = _cfg_str(config, "license_filename", "license.jwt") or "license.jwt"

    activate_path = _cfg_str(config, "activate_path", _DEFAULT_PATH)
    if not activate_path.startswith("/"):
        activate_path = "/" + activate_path

    try:
        grace_hours = int(_cfg_str(config, "clock_rollback_grace_hours", "24"))
    except (TypeError, ValueError):
        grace_hours = 24

    try:
        request_timeout = int(_cfg_str(config, "activate_timeout_seconds", "30"))
    except (TypeError, ValueError):
        request_timeout = 30

    return {
        "activate_base_url": base,
        "activate_url": f"{base}{activate_path}",
        "get_license_url": get_url,
        "license_filename": filename,
        "clock_rollback_grace_hours": max(0, grace_hours),
        "activate_timeout_seconds": max(5, request_timeout),
        "license_auth_required": is_license_auth_required(),
    }
