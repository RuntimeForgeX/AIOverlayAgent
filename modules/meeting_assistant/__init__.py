"""
Meeting Assistant — isolated module.

Captures desktop audio, transcribes via OpenAI Whisper API,
and optionally generates AI response suggestions.

Removal: delete this directory + remove imports from main.py / app.py.
"""

from modules.meeting_assistant.storage import MeetingStorage

__all__ = [
    "MeetingStorage",
]
