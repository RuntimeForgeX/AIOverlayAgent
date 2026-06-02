"""License-related settings: .env overrides config.ini [LICENSE]."""

import os

from src.config.settings import get_config_value

_DEFAULT_NODE_PORT = "3000"
_ENV_AUTH = "LICENSE_AUTH"
_ENV_BYPASS = "OVERLAY_LICENSE_BYPASS"
_ENV_BASE_URL = "LICENSE_ACTIVATE_BASE_URL"
_ENV_GET_URL = "LICENSE_GET_LICENSE_URL"
_ENV_ACTIVATE_PATH = "LICENSE_ACTIVATE_PATH"
_ENV_NODE_PORT = "LICENSE_NODE_PORT"


def _env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip()


def _localhost_base(port: str) -> str:
    return f"http://localhost:{port}".rstrip("/")


def is_license_auth_required() -> bool:
    """
    LICENSE_AUTH in .env / environment:
      1 = require valid license (default when unset)
      0 = skip license gate (local dev)
    OVERLAY_LICENSE_BYPASS=1 also skips (legacy alias).
    """
    bypass = _env_str(_ENV_BYPASS).lower()
    if bypass in ("1", "true", "yes", "on"):
        return False

    auth = _env_str(_ENV_AUTH)
    if auth == "0":
        return False
    if auth == "1":
        return True
    return True


def license_bypass_enabled() -> bool:
    return not is_license_auth_required()


def get_license_settings(config):
    """Read license URLs and paths (.env wins over config.ini)."""
    port = _env_str(_ENV_NODE_PORT) or _DEFAULT_NODE_PORT
    default_base = _localhost_base(port)

    base = _env_str(_ENV_BASE_URL) or get_config_value(
        config, "LICENSE", "activate_base_url", default_base
    )
    base = base.strip().rstrip("/")

    default_get = f"{default_base}/request"
    get_url = _env_str(_ENV_GET_URL) or get_config_value(
        config, "LICENSE", "get_license_url", default_get
    )
    get_url = get_url.strip()

    filename = get_config_value(
        config, "LICENSE", "license_filename", "license.jwt"
    ).strip() or "license.jwt"

    activate_path = _env_str(_ENV_ACTIVATE_PATH) or get_config_value(
        config, "LICENSE", "activate_path", "/api/activate"
    ).strip()
    if not activate_path.startswith("/"):
        activate_path = "/" + activate_path

    try:
        grace_hours = int(
            get_config_value(config, "LICENSE", "clock_rollback_grace_hours", "24")
        )
    except (TypeError, ValueError):
        grace_hours = 24

    try:
        request_timeout = int(
            get_config_value(config, "LICENSE", "activate_timeout_seconds", "30")
        )
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
