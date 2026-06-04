"""
Context builder — assembles personal context into a text block
ready for injection into AI system prompts.

Uses priority ordering and token-based chunking to stay within limits.
"""

from typing import Optional, List


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token)."""
    return max(1, len(text) // 4)


def _priority_key(item: dict) -> int:
    """Sort key for context items.  Lower = higher priority.

    Priority:
      1. Resume / CV
      2. Project READMEs
      3. Everything else
    """
    name_lower = item.get("name", "").lower()
    if any(kw in name_lower for kw in ("resume", "cv", "curriculum")):
        return 0
    if any(kw in name_lower for kw in ("readme", "project")):
        return 1
    return 2


def build_context_block(manager, token_limit: Optional[int] = None) -> str:
    """Build a formatted context string from all stored personal context items.

    Args:
        manager: PersonalContextManager instance.
        token_limit: Max tokens for the context block. Defaults to manager setting.

    Returns:
        Formatted context string, or empty string if nothing available.
    """
    if not manager.is_enabled():
        return ""

    items = manager.get_all_items()
    if not items:
        return ""

    if token_limit is None:
        token_limit = manager.get_token_limit()

    # Sort by priority
    items.sort(key=_priority_key)

    parts: List[str] = []
    total_tokens = 0

    # Header
    header = (
        "=== PERSONAL CONTEXT (provided by user) ===\n"
        "The following is personal information the user has stored for reference.\n"
        "Use it to give personalized, relevant responses.\n"
    )
    header_tokens = estimate_tokens(header)
    total_tokens += header_tokens

    for item in items:
        text = item.get("text_content", "").strip()
        if not text:
            continue

        name = item.get("name", "Unknown")
        file_type = item.get("type", "txt").upper()

        section = f"\n--- {name} ({file_type}) ---\n{text}\n"
        section_tokens = estimate_tokens(section)

        if total_tokens + section_tokens > token_limit:
            # Try to fit a truncated version
            remaining_tokens = token_limit - total_tokens - 20  # margin
            if remaining_tokens > 100:
                # Truncate text to fit
                max_chars = remaining_tokens * 4
                truncated = text[:max_chars] + "\n... [truncated]"
                section = f"\n--- {name} ({file_type}) ---\n{truncated}\n"
                parts.append(section)
            break

        parts.append(section)
        total_tokens += section_tokens

    if not parts:
        return ""

    return header + "".join(parts) + "\n=== END PERSONAL CONTEXT ===\n"


def is_context_enabled(manager) -> bool:
    """Check if personal context injection is enabled."""
    if manager is None:
        return False
    return manager.is_enabled()
