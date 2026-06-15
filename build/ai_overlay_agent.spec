#!/usr/bin/env python
# -*- mode: python ; coding: utf-8 -*-

import configparser
import os

from PyInstaller.utils.hooks import collect_submodules


_SPEC_DIR = os.path.abspath(SPECPATH)
_PROJECT_ROOT = os.path.abspath(os.path.join(_SPEC_DIR, ".."))


def _read_build_config():
    cp = configparser.ConfigParser()
    app_config_path = os.path.join(_PROJECT_ROOT, "app_config.ini")
    try:
        cp.read(app_config_path, encoding="utf-8")
    except Exception:
        cp.read(app_config_path)
    app_name = cp.get("APP", "name", fallback="AIOverlayAgent").strip()
    exe_base = cp.get("BUILD", "exe_base_name", fallback=app_name).strip()
    return {
        "app_name": app_name,
        "exe_base": exe_base,
    }


def _drop_google_discovery_cache(items):
    """Remove discovery_cache JSON blobs that break one-file extraction on Windows."""
    filtered = []
    for item in items:
        # TOC entries: (dest_name, src_name, typecode) or legacy 2-tuple
        dest = item[0] if item else ""
        src = item[1] if len(item) > 1 else ""
        blob = f"{dest}|{src}".lower()
        if "discovery_cache" in blob:
            continue
        filtered.append(item)
    return filtered


_cfg = _read_build_config()

block_cipher = None

hiddenimports = []

# Packages to fully collect. Do NOT collect google.generativeai here — the custom hook
# bundles it without googleapiclient discovery_cache (thousands of JSON files).
_COLLECT_PACKAGES = [
    "langchain_openai",
    "langchain_anthropic",
    "langchain_core",
    "openai",
    "anthropic",
    "dotenv",
    "keyboard",
    "PIL",
    "src",
    "src.config",
    "src.config.settings",
    "src.prompts",
    "src.services",
    "src.services.llm_provider",
    "src.services.capture",
    "src.services.storage",
    "src.ui",
    "src.ui.app",
    "src.ui.cursor",
    "src.ui.styles",
    "src.ui.styles.themes",
    "src.ui.markdown",
    "src.ui.markdown.renderer",
    "src.utils",
    "src.utils.win32_invisibility",
    "src.utils.error_handler",
    "google.ai.generativelanguage",
    "google.api_core",
    "google.auth",
    "google.protobuf",
]

for pkg in _COLLECT_PACKAGES:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# Gemini SDK (handled by build/hook-google.generativeai.py)
hiddenimports += [
    "google.generativeai",
    "google.ai.generativelanguage",
    "google.api_core",
    "google.auth",
    "google.protobuf",
]

datas = [
    (os.path.join(_PROJECT_ROOT, "app_config.ini"), "."),
    (os.path.join(_PROJECT_ROOT, "config.ini"), "."),
    (os.path.join(_PROJECT_ROOT, "prompts"), "prompts"),
    # Prompt registry profiles (file-based discovery in frozen builds)
    (os.path.join(_PROJECT_ROOT, "src", "prompts"), "src/prompts"),
]

_EXCLUDES = [
    "googleapiclient.discovery_cache",
    "googleapiclient.discovery_cache.documents",
    "langchain_community",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "tkinter.test",
]

a = Analysis(
    [os.path.join(_PROJECT_ROOT, "main.py")],
    pathex=[_PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports + ["keyboard", "keyboard._winkeyboard", "keyboard._generic"],
    hookspath=[_SPEC_DIR],
    hooksconfig={},
    runtime_hooks=[
        os.path.join(_SPEC_DIR, "runtime_keyboard_fix.py"),
        os.path.join(_SPEC_DIR, "runtime_google_fix.py"),
    ],
    excludes=_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.datas = _drop_google_discovery_cache(a.datas)
a.binaries = _drop_google_discovery_cache(a.binaries)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=_cfg["exe_base"],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
)
