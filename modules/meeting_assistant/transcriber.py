"""
OpenAI Whisper API transcriber.

Reuses the existing OPENAI_API_KEY from the application environment.
Sends audio chunks to the Whisper API and returns timestamped transcriptions.
"""

import io
import threading
from datetime import datetime
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

    def transcribe(self, wav_bytes: bytes,
                   on_result: Optional[Callable] = None,
                   on_error: Optional[Callable] = None):
        """Transcribe WAV audio bytes using Whisper API.

        Args:
            wav_bytes: WAV-format audio data.
            on_result: Callback with (text, segments) on success.
            on_error: Callback with (error_string) on failure.
        """
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

                # Create a file-like object from bytes
                audio_file = io.BytesIO(wav_bytes)
                audio_file.name = "audio.wav"

                with self._lock:
                    response = self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )

                text = response.text if hasattr(response, "text") else str(response)

                segments = []
                if hasattr(response, "segments") and response.segments:
                    for seg in response.segments:
                        segments.append({
                            "start": getattr(seg, "start", 0),
                            "end": getattr(seg, "end", 0),
                            "text": getattr(seg, "text", ""),
                        })

                if on_result:
                    on_result(text, segments)

            except Exception as e:
                if on_error:
                    on_error(f"Whisper transcription error: {e}")

        thread = threading.Thread(target=_do_transcribe, daemon=True)
        thread.start()

    def transcribe_sync(self, wav_bytes: bytes) -> dict:
        """Synchronous transcription — returns {"text": str, "segments": list}."""
        result = {"text": "", "segments": [], "error": None}

        def on_result(text, segments):
            result["text"] = text
            result["segments"] = segments

        def on_error(error):
            result["error"] = error

        # Run in current thread
        if not self._ensure_client():
            result["error"] = "OPENAI_API_KEY not set"
            return result

        try:
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"

            response = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

            result["text"] = response.text if hasattr(response, "text") else str(response)

            if hasattr(response, "segments") and response.segments:
                for seg in response.segments:
                    result["segments"].append({
                        "start": getattr(seg, "start", 0),
                        "end": getattr(seg, "end", 0),
                        "text": getattr(seg, "text", ""),
                    })
        except Exception as e:
            result["error"] = str(e)

        return result
