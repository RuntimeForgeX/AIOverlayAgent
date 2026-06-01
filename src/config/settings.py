import os
import sys
import configparser
from pathlib import Path

from dotenv import load_dotenv
# ============================================================================
# CONFIGURATION
# ============================================================================

def is_frozen_app():
    """True when running from a packaged executable (PyInstaller, etc.)."""
    return bool(getattr(sys, "frozen", False))


def get_project_root():
    """Repository root (contains main.py, config.ini, prompts/)."""
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_resource_root():
    """Base folder for bundled, read-only resources."""
    return get_project_root()


def load_app_config():
    """Load app metadata from app_config.ini (bundled or alongside exe)."""
    defaults = {
        "name": "PersonalAiAgentSurya",
        "appdata_folder": "PersonalAiAgentSurya",
        "window_title": "AI OVERLAY",
    }

    cp = configparser.ConfigParser()

    candidates = [
        get_resource_root() / "app_config.ini",
    ]
    if is_frozen_app():
        try:
            candidates.append(Path(sys.executable).parent / "app_config.ini")
        except Exception:
            pass
    candidates.append(get_project_root() / "app_config.ini")

    for path in candidates:
        try:
            if path.exists():
                cp.read(path, encoding="utf-8")
                break
        except Exception:
            continue

    return {
        "name": cp.get("APP", "name", fallback=defaults["name"]).strip(),
        "appdata_folder": cp.get(
            "APP", "appdata_folder", fallback=defaults["appdata_folder"]
        ).strip(),
        "window_title": cp.get(
            "APP", "window_title", fallback=defaults["window_title"]
        ).strip(),
    }


APP_META = load_app_config()
APP_NAME = APP_META.get("name") or "PersonalAiAgentSurya"
APPDATA_FOLDER = APP_META.get("appdata_folder") or APP_NAME
WINDOW_TITLE = APP_META.get("window_title") or "AI OVERLAY"


def get_user_data_root(app_name=None):
    """Per-user writable data folder (AppData\\Roaming)."""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / (app_name or APPDATA_FOLDER)


def get_candidate_dotenv_files(app_name=None):
    """Optional .env locations (used only when a key is not already in the environment)."""
    candidates = []
    try:
        candidates.append(get_user_data_root(app_name) / ".env")
    except Exception:
        pass
    try:
        if is_frozen_app():
            candidates.append(Path(sys.executable).parent / ".env")
    except Exception:
        pass
    candidates.append(get_project_root() / ".env")
    return candidates


def load_environment():
    """
    Load API keys and secrets into os.environ.

    Windows user/system environment variables are already in os.environ and always win.
    .env files only fill in keys that are not already set (override=False).
    """
    for dotenv_file in get_candidate_dotenv_files():
        try:
            if dotenv_file.is_file():
                load_dotenv(dotenv_path=dotenv_file, override=False, encoding="utf-8")
        except Exception:
            pass


def get_api_key(name):
    """Read an API key from the process environment (system env or .env)."""
    value = os.environ.get(name)
    if value is None:
        value = os.getenv(name)
    if not value:
        return None
    value = value.strip()
    return value or None


def api_key_env_name(provider_name):
    """Environment variable name for the configured provider."""
    mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    return mapping.get((provider_name or "").lower(), "ANTHROPIC_API_KEY")

def load_config():
    """Load configuration from config.ini with fallbacks."""
    config = configparser.ConfigParser()

    # Prefer per-user config so installs work under Program Files.
    user_config = get_user_data_root() / "config.ini"
    exe_side_config = None
    if is_frozen_app():
        try:
            exe_side_config = Path(sys.executable).parent / "config.ini"
        except Exception:
            exe_side_config = None
    bundled_config = get_resource_root() / "config.ini"

    if user_config.exists():
        config.read(user_config)
    elif exe_side_config and exe_side_config.exists():
        config.read(exe_side_config)
    elif bundled_config.exists():
        config.read(bundled_config)
    
    return config


def get_config_value(config, section, key, default):
    """Safely get a config value with default fallback."""
    try:
        if section == "HOTKEYS":
            return config.get(section, key, fallback=default)
        elif section in ["API", "API_OPENAI", "API_GEMINI", "UI", "CAPTURE"]:
            return config.get(section, key, fallback=default)
    except:
        pass
    return default


