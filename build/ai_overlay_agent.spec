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
    app_name = cp.get("APP", "name", fallback="PersonalAiAgentSurya").strip()
    exe_base = cp.get("BUILD", "exe_base_name", fallback=app_name).strip()
    return {
        "app_name": app_name,
        "exe_base": exe_base,
    }


_cfg = _read_build_config()

block_cipher = None

hiddenimports = []

# LangChain providers are optional at runtime, but we bundle them so packaged builds
# work when the user selects a provider.
for pkg in [
    "langchain_openai",
    "langchain_anthropic",
    "langchain_core",
    "langchain_community",
    "openai",
    "anthropic",
    "google.generativeai",
    "dotenv",
    "keyboard",
    "PIL",
]:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

datas = [
    (os.path.join(_PROJECT_ROOT, "app_config.ini"), "."),
    (os.path.join(_PROJECT_ROOT, "config.ini"), "."),
    (os.path.join(_PROJECT_ROOT, "prompts"), "prompts"),
]

a = Analysis(
    [os.path.join(_PROJECT_ROOT, "ai_overlay.py")],
    pathex=[_PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports + ["keyboard", "keyboard._winkeyboard", "keyboard._generic"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(_SPEC_DIR, "runtime_keyboard_fix.py")],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
)
