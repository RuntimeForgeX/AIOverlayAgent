import os
import json
import stat
from pathlib import Path
from src.config.settings import get_user_data_root
# ============================================================================
# PERSISTENCE HELPERS
# ============================================================================


def _set_restrictive_permissions(path: Path):
    """Best-effort: restrict file access to the owner only.

    On Windows os.chmod does not translate Unix-style modes exactly,
    so this is a defense-in-depth measure rather than a guarantee.
    """
    try:
        if hasattr(os, "chmod"):
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def _ensure_private_dir(path: Path) -> Path:
    """Create directory (and ancestors) with best-effort restricted access."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        _set_restrictive_permissions(path)
    except Exception:
        pass
    return path

def save_theme_preference(theme_name):
    """Save theme preference to AppData."""
    prefs_file = get_user_data_root() / "preferences.json"
    _ensure_private_dir(prefs_file.parent)
    prefs = {}
    try:
        if prefs_file.exists():
            prefs = json.loads(prefs_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    prefs["theme"] = theme_name
    try:
        prefs_file.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
        _set_restrictive_permissions(prefs_file)
    except Exception:
        pass


def load_theme_preference():
    """Load theme preference from AppData."""
    prefs_file = get_user_data_root() / "preferences.json"
    try:
        if prefs_file.exists():
            prefs = json.loads(prefs_file.read_text(encoding="utf-8"))
            return prefs.get("theme", "dark")
    except Exception:
        pass
    return "dark"


def _load_preferences():
    prefs_file = get_user_data_root() / "preferences.json"
    try:
        if prefs_file.exists():
            return json.loads(prefs_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_preferences(prefs):
    prefs_file = get_user_data_root() / "preferences.json"
    _ensure_private_dir(prefs_file.parent)
    try:
        prefs_file.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
        _set_restrictive_permissions(prefs_file)
    except Exception:
        pass


def save_prompt_profile_id(prompt_id):
    """Persist selected prompt profile id to AppData."""
    prefs = _load_preferences()
    prefs["prompt_profile_id"] = prompt_id
    _save_preferences(prefs)


def load_prompt_profile_id():
    """Load selected prompt profile id from AppData."""
    return _load_preferences().get("prompt_profile_id", "any")


def clear_screenshot_queue():
    """Remove persisted screenshot queue file (security housekeeping)."""
    try:
        queue_file = get_user_data_root() / "screenshot_queue.json"
        if queue_file.exists():
            queue_file.unlink()
    except Exception:
        pass


def save_display_log(display_log):
    """Save chat display log to AppData."""
    history_file = get_user_data_root() / "chat_history.json"
    _ensure_private_dir(history_file.parent)
    try:
        # Keep at most 200 messages
        trimmed = display_log[-200:]
        history_file.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")
        _set_restrictive_permissions(history_file)
    except Exception:
        pass


def load_display_log():
    """Load chat display log from AppData."""
    history_file = get_user_data_root() / "chat_history.json"
    try:
        if history_file.exists():
            return json.loads(history_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save_screenshot_queue_to_disk(queue):
    """Save up to 5 queued screenshots to AppData."""
    queue_file = get_user_data_root() / "screenshot_queue.json"
    _ensure_private_dir(queue_file.parent)
    try:
        data = [{"b64": entry["b64"]} for entry in queue[:5]]
        queue_file.write_text(json.dumps(data), encoding="utf-8")
        _set_restrictive_permissions(queue_file)
    except Exception:
        pass


def load_screenshot_queue_from_disk():
    """Load queued screenshots from AppData."""
    queue_file = get_user_data_root() / "screenshot_queue.json"
    try:
        if queue_file.exists():
            data = json.loads(queue_file.read_text(encoding="utf-8"))
            return [entry["b64"] for entry in data if "b64" in entry]
    except Exception:
        pass
    return []


