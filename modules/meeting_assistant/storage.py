"""
Meeting Assistant storage manager.

Handles transcript persistence, history tracking, and settings
in %APPDATA%/<AppName>/meeting_assistant/.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config.settings import get_user_data_root


def _meeting_root() -> Path:
    """Root directory for meeting assistant data in %APPDATA%."""
    return get_user_data_root() / "meeting_assistant"


def _transcripts_dir() -> Path:
    return _meeting_root() / "transcripts"


def _history_path() -> Path:
    return _meeting_root() / "history.json"


def _settings_path() -> Path:
    return _meeting_root() / "settings.json"


class MeetingStorage:
    """Manages meeting transcript storage and history in %APPDATA%."""

    def __init__(self):
        self._ensure_dirs()
        self._settings: dict = self._load_settings()

    # ------------------------------------------------------------------
    # Directory setup
    # ------------------------------------------------------------------

    def _ensure_dirs(self):
        _meeting_root().mkdir(parents=True, exist_ok=True)
        _transcripts_dir().mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _load_settings(self) -> dict:
        defaults = {
            "ai_suggestions_enabled": False,
            "chunk_duration": 30,
            "silence_threshold": 200,
        }
        try:
            if _settings_path().exists():
                data = json.loads(_settings_path().read_text(encoding="utf-8"))
                defaults.update(data)
        except Exception:
            pass
        return defaults

    def save_settings(self):
        try:
            _settings_path().write_text(
                json.dumps(self._settings, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def get_settings(self) -> dict:
        return dict(self._settings)

    def is_suggestions_enabled(self) -> bool:
        return self._settings.get("ai_suggestions_enabled", False)

    def set_suggestions_enabled(self, enabled: bool):
        self._settings["ai_suggestions_enabled"] = enabled
        self.save_settings()

    def get_chunk_duration(self) -> int:
        return int(self._settings.get("chunk_duration", 30))

    def get_silence_threshold(self) -> float:
        return float(self._settings.get("silence_threshold", 200))

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _load_history(self) -> List[dict]:
        try:
            if _history_path().exists():
                return json.loads(_history_path().read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_history(self, history: List[dict]):
        try:
            _history_path().write_text(
                json.dumps(history, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Transcript CRUD
    # ------------------------------------------------------------------

    def save_transcript(self, transcript_entries: List[dict],
                        duration_seconds: int = 0) -> dict:
        """Save a complete transcript session.

        Args:
            transcript_entries: List of {"time": str, "text": str} entries.
            duration_seconds: Total session duration in seconds.

        Returns:
            The history record for this transcript.
        """
        transcript_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        transcript_data = {
            "id": transcript_id,
            "date": timestamp,
            "duration_seconds": duration_seconds,
            "entries": transcript_entries,
        }

        # Save transcript file
        transcript_file = _transcripts_dir() / f"{transcript_id}.json"
        try:
            transcript_file.write_text(
                json.dumps(transcript_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

        # Update history
        history_record = {
            "id": transcript_id,
            "date": timestamp,
            "duration_seconds": duration_seconds,
            "entry_count": len(transcript_entries),
            "transcript_file": str(transcript_file),
        }

        history = self._load_history()
        history.insert(0, history_record)  # newest first
        self._save_history(history)

        return history_record

    def get_history(self) -> List[dict]:
        return self._load_history()

    def get_transcript(self, transcript_id: str) -> Optional[dict]:
        """Load full transcript data by ID."""
        transcript_file = _transcripts_dir() / f"{transcript_id}.json"
        try:
            if transcript_file.exists():
                return json.loads(transcript_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return None

    def delete_transcript(self, transcript_id: str) -> bool:
        """Delete a transcript and its history entry."""
        # Remove transcript file
        transcript_file = _transcripts_dir() / f"{transcript_id}.json"
        try:
            if transcript_file.exists():
                transcript_file.unlink()
        except Exception:
            pass

        # Remove from history
        history = self._load_history()
        new_history = [h for h in history if h.get("id") != transcript_id]
        if len(new_history) != len(history):
            self._save_history(new_history)
            return True
        return False

    def search_transcripts(self, query: str) -> List[dict]:
        """Search all transcripts for matching text."""
        if not query:
            return self.get_history()

        query_lower = query.lower()
        results = []

        history = self._load_history()
        for record in history:
            transcript = self.get_transcript(record.get("id", ""))
            if transcript is None:
                continue

            entries = transcript.get("entries", [])
            for entry in entries:
                if query_lower in entry.get("text", "").lower():
                    results.append(record)
                    break

        return results

    def get_transcript_count(self) -> int:
        return len(self._load_history())
