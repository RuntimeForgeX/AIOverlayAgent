"""Legacy loader — delegates to the dynamic prompt registry."""

from src.prompts.registry import get_default_system_prompt


def load_system_prompt():
    """Return the default profile's system prompt from src/prompts/."""
    return get_default_system_prompt()
