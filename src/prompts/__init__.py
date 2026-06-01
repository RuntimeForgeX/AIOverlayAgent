"""Prompt profile registry — one file per profile under this package."""

from src.prompts.registry import (
    DEFAULT_PROMPT_ID,  # "any" — default-agent profile
    discover_prompts,
    get_all_prompts,
    get_default_prompt_id,
    get_default_system_prompt,
    get_prompt_by_id,
    get_prompt_by_title,
)
from src.prompts.types import PromptProfile

__all__ = [
    "DEFAULT_PROMPT_ID",
    "PromptProfile",
    "discover_prompts",
    "get_all_prompts",
    "get_default_prompt_id",
    "get_default_system_prompt",
    "get_prompt_by_id",
    "get_prompt_by_title",
]
