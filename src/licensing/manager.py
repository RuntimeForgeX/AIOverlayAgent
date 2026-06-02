"""Device-bound premium license: activate online, verify offline."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jwt
import requests
from jwt.exceptions import InvalidTokenError

from src.config.settings import get_user_data_root
from src.licensing.config import get_license_settings, license_bypass_enabled
from src.licensing.fingerprint import get_device_info, get_hardware_fingerprint
from src.licensing.public_key import get_license_public_key

@dataclass
class LicenseStatus:
    ok: bool
    reason: str = ""
    payload: Optional[dict[str, Any]] = None


def _license_path(config) -> Path:
    settings = get_license_settings(config)
    root = get_user_data_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / settings["license_filename"]


def _state_path(config) -> Path:
    return _license_path(config).parent / "license_state.json"


def load_license(config) -> Optional[str]:
    path = _license_path(config)
    try:
        if path.is_file():
            token = path.read_text(encoding="utf-8").strip()
            return token or None
    except OSError:
        pass
    return None


def save_license(config, token: str) -> None:
    path = _license_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.strip(), encoding="utf-8")


def _read_last_verified(config) -> Optional[float]:
    path = _state_path(config)
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return float(data.get("last_verified_at", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _write_last_verified(config, timestamp: Optional[float] = None) -> None:
    path = _state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = timestamp if timestamp is not None else time.time()
    path.write_text(
        json.dumps({"last_verified_at": ts}, indent=2),
        encoding="utf-8",
    )


def _check_clock_rollback(config, payload: dict[str, Any]) -> LicenseStatus:
    settings = get_license_settings(config)
    grace_seconds = settings["clock_rollback_grace_hours"] * 3600
    last = _read_last_verified(config)
    now = time.time()

    if last is not None and now < last - grace_seconds:
        return LicenseStatus(
            ok=False,
            reason="System clock appears to have been set backward.",
            payload=payload,
        )

    exp = payload.get("exp")
    if exp is not None and not payload.get("lifetime"):
        try:
            if now > float(exp) + grace_seconds:
                return LicenseStatus(ok=False, reason="License has expired.", payload=payload)
        except (TypeError, ValueError):
            return LicenseStatus(ok=False, reason="Invalid license expiry.", payload=payload)

    _write_last_verified(config, now)
    return LicenseStatus(ok=True, payload=payload)


def verify_license_offline(token: Optional[str], config) -> LicenseStatus:
    if license_bypass_enabled():
        return LicenseStatus(ok=True, reason="developer bypass")

    if not token:
        return LicenseStatus(ok=False, reason="No license file found.")

    public_key = get_license_public_key()
    if not public_key:
        return LicenseStatus(
            ok=False,
            reason="Public key not configured. Set RS256 public key in src/licensing/public_key.py.",
        )

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_signature": True},
        )
    except InvalidTokenError as exc:
        return LicenseStatus(ok=False, reason=f"Invalid license: {exc}")

    if not payload.get("lifetime"):
        exp = payload.get("exp")
        if exp is None:
            return LicenseStatus(ok=False, reason="License missing expiry.", payload=payload)
        try:
            if time.time() > float(exp):
                return LicenseStatus(ok=False, reason="License has expired.", payload=payload)
        except (TypeError, ValueError):
            return LicenseStatus(ok=False, reason="Invalid license expiry.", payload=payload)

    device_hash = payload.get("device_hash")
    if not device_hash:
        return LicenseStatus(
            ok=False,
            reason="License is not activated for this device. Paste your key and click Activate.",
            payload=payload,
        )

    current = get_hardware_fingerprint()
    if device_hash != current:
        return LicenseStatus(
            ok=False,
            reason="License is bound to a different computer.",
            payload=payload,
        )

    rollback = _check_clock_rollback(config, payload)
    if not rollback.ok:
        return rollback

    return LicenseStatus(ok=True, payload=payload)


def is_premium(config) -> bool:
    return verify_license_offline(load_license(config), config).ok


def activate_license(raw_jwt: str, config) -> str:
    """One-time online activation; saves activated JWT locally."""
    settings = get_license_settings(config)
    raw = (raw_jwt or "").strip()
    if not raw:
        raise ValueError("License key is empty.")

    device_hash = get_hardware_fingerprint()
    body = {
        "raw_jwt": raw,
        "device_hash": device_hash,
        "device_info": get_device_info(),
    }

    try:
        response = requests.post(
            settings["activate_url"],
            json=body,
            timeout=settings["activate_timeout_seconds"],
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
    except requests.RequestException as exc:
        raise ValueError(f"Could not reach activation server: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text.strip() or response.reason
        try:
            err_json = response.json()
            detail = err_json.get("error") or err_json.get("message") or detail
        except Exception:
            pass
        raise ValueError(f"Activation failed ({response.status_code}): {detail}")

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("Activation server returned invalid JSON.") from exc

    activated = (data.get("activated_jwt") or data.get("token") or "").strip()
    if not activated:
        raise ValueError("Activation server did not return activated_jwt.")

    status = verify_license_offline(activated, config)
    if not status.ok:
        raise ValueError(status.reason or "Activated license failed offline verification.")

    save_license(config, activated)
    return activated


def license_summary(config) -> str:
    """Human-readable license info for UI (offline)."""
    if license_bypass_enabled():
        return "Developer bypass active"

    token = load_license(config)
    status = verify_license_offline(token, config)
    if not status.ok:
        return status.reason or "No valid license"

    payload = status.payload or {}
    if payload.get("lifetime"):
        return "Premium · lifetime"

    exp = payload.get("exp")
    if exp:
        try:
            dt = datetime.fromtimestamp(float(exp), tz=timezone.utc)
            return f"Premium · valid until {dt.strftime('%Y-%m-%d')} (UTC)"
        except (TypeError, ValueError, OSError):
            pass
    return "Premium · active"
