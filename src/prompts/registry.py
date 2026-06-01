"""
Dynamic prompt registry — auto-discovers prompt modules in this package.

Loads each *.py file from the prompts folder (works in dev and PyInstaller builds).
Add a new prompt: create `my_prompt.py` exporting a PROMPT dict (see README.md).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import List, Optional

from src.prompts.types import PromptProfile

DEFAULT_PROMPT_ID = "any"
_REGISTRY_FILES_SKIP = frozenset({"registry", "types", "__init__"})
_cached_prompts: Optional[List[PromptProfile]] = None


def _prompts_directory() -> Path:
    """Directory containing prompt profile .py files."""
    import src.prompts as prompts_package

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        bundled = meipass / "src" / "prompts"
        if bundled.is_dir():
            return bundled

    return Path(prompts_package.__file__).resolve().parent


def _normalize_prompt(raw: dict, module_name: str) -> PromptProfile:
    if "system_prompt" in raw and "systemPrompt" not in raw:
        raw = {**raw, "systemPrompt": raw["system_prompt"]}

    missing = [k for k in ("id", "title", "description", "systemPrompt") if k not in raw]
    if missing:
        raise ValueError(
            f"Prompt module '{module_name}' PROMPT missing keys: {', '.join(missing)}"
        )
    prompt_id = str(raw["id"]).strip()
    title = str(raw["title"]).strip()
    description = str(raw["description"]).strip()
    system_prompt = str(raw["systemPrompt"]).strip()
    if not prompt_id or not title or not system_prompt:
        raise ValueError(f"Prompt module '{module_name}' has empty id, title, or systemPrompt")
    return PromptProfile(
        id=prompt_id,
        title=title,
        description=description,
        systemPrompt=system_prompt,
    )


def _load_prompt_from_path(py_path: Path) -> Optional[PromptProfile]:
    stem = py_path.stem
    if stem in _REGISTRY_FILES_SKIP or stem.startswith("_"):
        return None

    module_name = f"src.prompts.{stem}"
    spec = importlib.util.spec_from_file_location(module_name, py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load prompt module from {py_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    raw = getattr(module, "PROMPT", None)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError(f"{py_path.name}: PROMPT must be a dict")
    return _normalize_prompt(raw, stem)


def discover_prompts(*, reload: bool = False) -> List[PromptProfile]:
    """Load every prompt profile .py file in src/prompts/."""
    global _cached_prompts
    if _cached_prompts is not None and not reload:
        return list(_cached_prompts)

    prompts_dir = _prompts_directory()
    profiles: List[PromptProfile] = []
    seen_ids: set[str] = set()

    for py_path in sorted(prompts_dir.glob("*.py")):
        profile = _load_prompt_from_path(py_path)
        if profile is None:
            continue
        if profile["id"] in seen_ids:
            raise ValueError(f"Duplicate prompt id '{profile['id']}' in {py_path.name}")
        seen_ids.add(profile["id"])
        profiles.append(profile)

    if not profiles:
        raise RuntimeError(
            f"No prompt profiles found in {prompts_dir}. "
            "Add a .py file exporting PROMPT = {{id, title, description, systemPrompt}}."
        )

    profiles.sort(key=lambda p: p["title"].lower())
    _cached_prompts = profiles
    return list(profiles)


def get_all_prompts() -> List[PromptProfile]:
    return discover_prompts()


def get_prompt_by_id(prompt_id: str) -> Optional[PromptProfile]:
    for profile in get_all_prompts():
        if profile["id"] == prompt_id:
            return profile
    return None


def get_prompt_by_title(title: str) -> Optional[PromptProfile]:
    for profile in get_all_prompts():
        if profile["title"] == title:
            return profile
    return None


def get_default_prompt_id() -> str:
    if get_prompt_by_id(DEFAULT_PROMPT_ID):
        return DEFAULT_PROMPT_ID
    return get_all_prompts()[0]["id"]


def get_default_system_prompt() -> str:
    profile = get_prompt_by_id(get_default_prompt_id())
    if profile is None:
        raise RuntimeError("Default prompt profile not found")
    return profile["systemPrompt"]
