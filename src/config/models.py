"""
Model labels and API routing for the overlay.

OpenRouter IDs verified against GET https://openrouter.ai/api/v1/models (2026-06-01).
Direct OpenAI IDs from https://developers.openai.com/api/docs/changelog
Direct Gemini from https://ai.google.dev/gemini-api/docs/models
Direct Anthropic from https://docs.anthropic.com/en/docs/about-claude/models

To re-verify OpenRouter slugs:
  python -c "import urllib.request,json; ..."
"""

from __future__ import annotations

from src.config.settings import get_config_value

# (dropdown label, provider key, model id passed to the API)
MODEL_CHOICES: list[tuple[str, str, str]] = [
    # --- OpenRouter (OPENROUTER_API_KEY) ---
    ("OR Gemini 3.1 Pro", "openrouter", "google/gemini-3.1-pro-preview"),
    ("OR GPT-5.5", "openrouter", "openai/gpt-5.5"),
    ("OR kimi 4.6","openrouter","moonshotai/kimi-k2.6"),
    # --- Direct OpenAI (OPENAI_API_KEY) — Chat Completions compatible ---
    ("GPT-5.5 (direct)", "openai", "gpt-5.5"),
    ("GPT-5.2 (direct)", "openai", "gpt-5.2"),
    # --- Direct Google Gemini (GEMINI_API_KEY) ---
    ("Gemini 3.1 Pro (direct)", "gemini", "gemini-3.1-pro-preview"),
    ("Free Gemini 3.5-flash","gemini","gemini-3.5-flash"),
    # --- Direct Anthropic (ANTHROPIC_API_KEY) ---
    ("Claude Opus 4.8 (direct)", "anthropic", "claude-opus-4-8"),
]

DEFAULT_OPENROUTER_MODEL = "google/gemini-3.1-pro-preview"
DEFAULT_OPENAI_MODEL = "gpt-5.2-chat-latest"
DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-4.8"
DEFAULT_MODEL_LABEL = "OR Gemini 3.1 Pro"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Quick lookup: (provider, model_id) must be in MODEL_CHOICES
_VALID_MODEL_KEYS = frozenset((p, m) for _, p, m in MODEL_CHOICES)


def model_labels() -> list[str]:
    return [label for label, _, _ in MODEL_CHOICES]


def build_model_map() -> dict[str, tuple[str, str]]:
    return {label: (provider, model_id) for label, provider, model_id in MODEL_CHOICES}


def is_known_model(provider: str, model_id: str) -> bool:
    return (provider.lower(), model_id) in _VALID_MODEL_KEYS


def resolve_model_label(config) -> str:
    """Pick dropdown label matching saved config, or default."""
    provider = get_config_value(config, "API", "provider", "openrouter").lower()
    if provider == "openrouter":
        model_id = get_config_value(
            config, "API_OPENROUTER", "model", DEFAULT_OPENROUTER_MODEL
        )
    elif provider == "gemini":
        model_id = get_config_value(config, "API_GEMINI", "model", DEFAULT_GEMINI_MODEL)
    elif provider == "openai":
        model_id = get_config_value(config, "API_OPENAI", "model", DEFAULT_OPENAI_MODEL)
    elif provider == "anthropic":
        model_id = get_config_value(config, "API", "model", DEFAULT_ANTHROPIC_MODEL)
    else:
        return DEFAULT_MODEL_LABEL

    for label, p, mid in MODEL_CHOICES:
        if p == provider and mid == model_id:
            return label

    # Saved config points at a removed/invalid id — fall back safely
    return DEFAULT_MODEL_LABEL


def normalize_config_model(config) -> None:
    """If config.ini has an old/invalid model id, reset to a known default."""
    provider = get_config_value(config, "API", "provider", "openrouter").lower()
    if provider == "openrouter":
        model_id = get_config_value(
            config, "API_OPENROUTER", "model", DEFAULT_OPENROUTER_MODEL
        )
    elif provider == "gemini":
        model_id = get_config_value(config, "API_GEMINI", "model", DEFAULT_GEMINI_MODEL)
    elif provider == "openai":
        model_id = get_config_value(config, "API_OPENAI", "model", DEFAULT_OPENAI_MODEL)
    elif provider == "anthropic":
        model_id = get_config_value(config, "API", "model", DEFAULT_ANTHROPIC_MODEL)
    else:
        model_id = ""

    if is_known_model(provider, model_id):
        return

    default_label = DEFAULT_MODEL_LABEL
    provider_name, safe_id = build_model_map()[default_label]
    apply_model_to_config(config, provider_name, safe_id)


def apply_model_to_config(config, provider_name: str, model_id: str) -> None:
    """Write provider + model into config object."""
    if not is_known_model(provider_name, model_id):
        raise ValueError(
            f"Unknown model '{model_id}' for provider '{provider_name}'. "
            "Pick a model from the header dropdown."
        )

    config.set("API", "provider", provider_name)
    if provider_name == "openrouter":
        if not config.has_section("API_OPENROUTER"):
            config.add_section("API_OPENROUTER")
        config.set("API_OPENROUTER", "model", model_id)
    elif provider_name == "gemini":
        if not config.has_section("API_GEMINI"):
            config.add_section("API_GEMINI")
        config.set("API_GEMINI", "model", model_id)
    elif provider_name == "openai":
        if not config.has_section("API_OPENAI"):
            config.add_section("API_OPENAI")
        config.set("API_OPENAI", "model", model_id)
    elif provider_name == "anthropic":
        config.set("API", "model", model_id)
