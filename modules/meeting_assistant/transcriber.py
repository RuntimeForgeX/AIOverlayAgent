"""
OpenAI Whisper API transcriber.

Reuses the existing OPENAI_API_KEY from the application environment.
"""

import io
import threading
from typing import Callable, Optional

from src.config.settings import get_api_key


class WhisperTranscriber:
    """Transcribes audio using the OpenAI Whisper API."""

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def _ensure_client(self):
        """Lazily initialize the OpenAI client."""
        if self._client is not None:
            return True
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            return False
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
            return True
        except Exception:
            return False

    def is_ready(self) -> bool:
        return self._ensure_client()

    def _parse_response(self, response) -> tuple[str, list]:
        text = getattr(response, "text", None) or str(response)
        segments = []
        raw_segments = getattr(response, "segments", None)
        if raw_segments:
            for seg in raw_segments:
                segments.append({
                    "start": getattr(seg, "start", 0),
                    "end": getattr(seg, "end", 0),
                    "text": getattr(seg, "text", ""),
                })
        return text, segments

    def _call_whisper(self, audio_file) -> tuple[str, list]:
        """Call Whisper with verbose JSON, falling back to plain text."""
        try:
            with self._lock:
                response = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                )
            return self._parse_response(response)
        except Exception as verbose_err:
            audio_file.seek(0)
            try:
                with self._lock:
                    response = self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                    )
                text = response if isinstance(response, str) else str(response)
                return text, []
            except Exception:
                raise verbose_err

    def transcribe(
        self,
        wav_bytes: bytes,
        on_result: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Transcribe WAV audio bytes on a background thread."""
        if not wav_bytes:
            if on_error:
                on_error("No audio data to transcribe")
            return

        def _do_transcribe():
            try:
                if not self._ensure_client():
                    if on_error:
                        on_error(
                            "OPENAI_API_KEY is not set. "
                            "Add it in Windows Environment Variables or .env file."
                        )
                    return

                audio_file = io.BytesIO(wav_bytes)
                audio_file.name = "audio.wav"
                text, segments = self._call_whisper(audio_file)

                if on_result:
                    on_result(text, segments)

            except Exception as e:
                if on_error:
                    on_error(f"Whisper transcription error: {e}")

        threading.Thread(target=_do_transcribe, daemon=True).start()

    def transcribe_sync(self, wav_bytes: bytes) -> dict:
        """Synchronous transcription — returns {text, segments, error}."""
        result = {"text": "", "segments": [], "error": None}

        if not wav_bytes:
            result["error"] = "No audio data"
            return result

        if not self._ensure_client():
            result["error"] = "OPENAI_API_KEY not set"
            return result

        try:
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"
            text, segments = self._call_whisper(audio_file)
            result["text"] = text
            result["segments"] = segments
        except Exception as e:
            result["error"] = str(e)

        return result
