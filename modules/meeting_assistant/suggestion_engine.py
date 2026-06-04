"""
AI Suggestion Engine for the Meeting Assistant.

Uses the existing LLM provider infrastructure to generate
response suggestions based on transcript + personal context.
"""

import threading
from typing import Callable, Optional

from src.services.llm_provider import get_provider
from src.config.settings import load_config


class SuggestionEngine:
    """Generates AI response suggestions from meeting transcripts.

    Reuses the existing provider infrastructure (get_provider).
    Integrates personal context (resume, skills) when available.
    """

    SUGGESTION_SYSTEM_PROMPT = (
        "You are a real-time meeting assistant. The user is in a live meeting "
        "(Google Meet, Zoom, Teams, Discord, etc.).\n\n"
        "Based on the transcript provided, generate helpful response suggestions "
        "that the user could say next. Focus on:\n"
        "- Answering questions directed at the user\n"
        "- Providing relevant technical information\n"
        "- Suggesting professional responses\n\n"
        "Keep suggestions concise (2-4 sentences each). "
        "Provide 1-3 suggestions separated by blank lines.\n"
        "Label each suggestion with a number.\n\n"
        "IMPORTANT: These are suggestions only. "
        "Do NOT send anything to the meeting automatically."
    )

    def __init__(self, config=None, personal_context_manager=None):
        self._config = config or load_config()
        self._personal_context_manager = personal_context_manager
        self._provider = None
        self._busy = False

    def _get_provider(self):
        """Get or create an LLM provider for suggestions."""
        if self._provider is None or not self._provider.is_ready():
            system_prompt = self._build_system_prompt()
            self._provider = get_provider(self._config, system_prompt=system_prompt)
        return self._provider

    def _build_system_prompt(self) -> str:
        """Build system prompt with optional personal context."""
        prompt = self.SUGGESTION_SYSTEM_PROMPT

        if self._personal_context_manager is not None:
            try:
                from modules.personal_context.context_builder import build_context_block
                context = build_context_block(self._personal_context_manager)
                if context:
                    prompt += (
                        "\n\nThe following is the user's personal context. "
                        "Use it to personalize suggestions based on their "
                        "background, skills, and experience:\n\n"
                        + context
                    )
            except Exception:
                pass

        return prompt

    def generate_suggestion(
        self,
        transcript_text: str,
        on_response: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Generate response suggestions from transcript text.

        Runs in a background thread. Calls on_response(suggestion_text, tokens)
        on success, or on_error(error_text) on failure.
        """
        if not transcript_text or not transcript_text.strip():
            if on_error:
                on_error("No transcript text to generate suggestions from")
            return

        if self._busy:
            return

        def _do_suggest():
            self._busy = True
            try:
                provider = self._get_provider()
                if not provider or not provider.is_ready():
                    if on_error:
                        on_error("AI provider not ready. Check API key configuration.")
                    return

                # Update system prompt with latest personal context
                provider.apply_system_prompt(self._build_system_prompt())

                # Clear history each time — suggestions are one-shot
                provider.clear_history()

                message = (
                    "Here is the latest meeting transcript. "
                    "Generate response suggestions for the user:\n\n"
                    f"--- TRANSCRIPT ---\n{transcript_text}\n--- END TRANSCRIPT ---"
                )

                provider.send_message(
                    message,
                    on_response=on_response or (lambda text, tokens: None),
                    on_error=on_error or (lambda err: None),
                )

            except Exception as e:
                if on_error:
                    on_error(f"Suggestion generation error: {e}")
            finally:
                self._busy = False

        thread = threading.Thread(target=_do_suggest, daemon=True)
        thread.start()

    @property
    def is_ready(self) -> bool:
        try:
            provider = self._get_provider()
            return provider is not None and provider.is_ready()
        except Exception:
            return False
