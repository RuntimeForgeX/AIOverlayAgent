"""
Personal Context System — isolated module.

Allows users to store personal documents (resume, portfolio, etc.)
and inject them as context into AI conversations.

Removal: delete this directory + remove imports from main.py / app.py.
"""

from modules.personal_context.storage import PersonalContextManager
from modules.personal_context.context_builder import build_context_block, is_context_enabled

__all__ = [
    "PersonalContextManager",
    "build_context_block",
    "is_context_enabled",
]
