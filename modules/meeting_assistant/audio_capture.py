"""
WASAPI / Stereo Mix loopback audio capture for Windows.

Captures desktop/system audio (not the microphone when a loopback device is used).
Uses sounddevice; prefers Stereo Mix or similarly named loopback input devices.
"""

import io
import struct
import threading
import time
import wave
from typing import Optional, Tuple

# Device name fragments that indicate system-audio loopback capture.
_LOOPBACK_NAME_KEYWORDS = (
    "stereo mix",
    "loopback",
    "what u hear",
    "wave out mix",
    "mixed output",
    "monitor",
)

# Realtek "PC Speaker" endpoints sometimes expose loopback as a capture device.
_PC_SPEAKER_KEYWORD = "pc speaker"


def _rms_energy(audio_bytes: bytes, sample_width: int = 2) -> float:
    """Calculate RMS energy of audio data (16-bit PCM)."""
    if not audio_bytes or len(audio_bytes) < sample_width:
        return 0.0
    n_samples = len(audio_bytes) // sample_width
    if n_samples == 0:
        return 0.0
    fmt = f"<{n_samples}h"
    try:
        samples = struct.unpack(fmt, audio_bytes[: n_samples * sample_width])
    except struct.error:
        return 0.0
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / n_samples) ** 0.5


def is_silent(audio_bytes: bytes, threshold: float = 200.0) -> bool:
    """Check if an audio chunk is silence based on RMS energy."""
    return _rms_energy(audio_bytes) < threshold


def pcm_to_wav_bytes(
    pcm_data: bytes,
    channels: int = 1,
    sample_rate: int = 16000,
    sample_width: int = 2,
) -> bytes:
    """Convert raw PCM bytes to WAV format in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def find_loopback_input_device(sd) -> Tuple[Optional[int], Optional[str]]:
    """Return (device_index, device_name) for desktop audio capture, or (None, None)."""
    try:
        devices = sd.query_devices()
    except Exception as exc:
        print(f"[AudioCapture] query_devices failed: {exc}")
        return None, None

    ranked: list[tuple[int, int, int]] = []  # (priority, index, name_len)

    for i, dev in enumerate(devices):
        in_ch = int(dev.get("max_input_channels", 0) or 0)
        if in_ch <= 0:
            continue
        name = dev.get("name", "") or ""
        lower = name.lower()

        if any(kw in lower for kw in _LOOPBACK_NAME_KEYWORDS):
            priority = 0 if "stereo mix" in lower else 1
            ranked.append((priority, i, len(name)))
            continue

        if _PC_SPEAKER_KEYWORD in lower:
            ranked.append((2, i, len(name)))

    if ranked:
        ranked.sort(key=lambda x: (x[0], x[2]))
        idx = ranked[0][1]
        return idx, devices[idx].get("name")

    return None, None


class AudioCapture:
    """Captures desktop audio as 16 kHz mono 16-bit PCM (Whisper-compatible)."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    SAMPLE_WIDTH = 2  # 16-bit
    CHUNK_DURATION = 30  # seconds

    def __init__(self, chunk_duration: int = 30, silence_threshold: float = 200.0):
        self.CHUNK_DURATION = max(5, int(chunk_duration))
        self._silence_threshold = silence_threshold
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._chunks: list[bytes] = []
        self._stop_event = threading.Event()
        self._error: Optional[str] = None
        self._device_name: Optional[str] = None
        self._native_samplerate = 48000
        self._native_channels = 2

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name

    def start(self):
        """Begin capturing desktop audio."""
        if self._recording:
            return

        self._error = None
        self._device_name = None
        self._stop_event.clear()
        self._buffer = bytearray()
        self._chunks = []
        self._recording = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self) -> bytes:
        """Stop capturing and return any remaining buffered audio as WAV."""
        self._stop_event.set()
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        with self._lock:
            remaining = bytes(self._buffer)
            self._buffer = bytearray()

        if remaining and not is_silent(remaining, self._silence_threshold):
            return pcm_to_wav_bytes(
                remaining, self.CHANNELS, self.SAMPLE_RATE, self.SAMPLE_WIDTH
            )
        return b""

    def get_chunk(self) -> Optional[bytes]:
        """Get the next completed audio chunk as WAV bytes, or None."""
        with self._lock:
            if self._chunks:
                return self._chunks.pop(0)
        return None

    def has_chunks(self) -> bool:
        with self._lock:
            return len(self._chunks) > 0

    def _capture_loop(self):
        """Main capture loop running in a background thread."""
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self._error = (
                "sounddevice/numpy not installed. "
                "Run: pip install sounddevice numpy"
            )
            self._recording = False
            return

        device_idx, device_name = find_loopback_input_device(sd)
        if device_idx is None:
            self._error = (
                "No desktop audio capture device found. "
                "Enable 'Stereo Mix' in Windows Sound settings → Recording tab "
                "(right-click → Show disabled devices), then retry."
            )
            self._recording = False
            return

        self._device_name = device_name

        try:
            device_info = sd.query_devices(device_idx)
        except Exception as exc:
            self._error = f"Could not query audio device: {exc}"
            self._recording = False
            return

        self._native_channels = max(1, int(device_info.get("max_input_channels", 1) or 1))
        self._native_samplerate = int(device_info.get("default_samplerate", 48000) or 48000)
        if self._native_samplerate <= 0:
            self._native_samplerate = 48000

        target_bytes_per_chunk = (
            self.SAMPLE_RATE * self.SAMPLE_WIDTH * self.CHANNELS * self.CHUNK_DURATION
        )

        hostapi_idx = device_info.get("hostapi")
        extra_settings = None
        try:
            if hostapi_idx is not None:
                api_name = sd.query_hostapis(hostapi_idx).get("name", "").lower()
                if "wasapi" in api_name:
                    extra_settings = sd.WasapiSettings(exclusive=False)
        except Exception:
            pass

        stream_kwargs = dict(
            device=device_idx,
            samplerate=self._native_samplerate,
            channels=self._native_channels,
            dtype="float32",
            blocksize=max(256, int(self._native_samplerate * 0.25)),
        )
        if extra_settings is not None:
            stream_kwargs["extra_settings"] = extra_settings

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[AudioCapture] Status: {status}")

            if indata.shape[1] > 1:
                mono_data = np.mean(indata, axis=1)
            else:
                mono_data = indata.flatten()

            if self._native_samplerate != self.SAMPLE_RATE:
                new_length = int(
                    len(mono_data) * self.SAMPLE_RATE / self._native_samplerate
                )
                if new_length > 0:
                    old_indices = np.arange(len(mono_data))
                    new_indices = np.linspace(0, len(mono_data) - 1, new_length)
                    mono_data = np.interp(new_indices, old_indices, mono_data)

            pcm = (mono_data * 32767).astype(np.int16).tobytes()

            with self._lock:
                self._buffer.extend(pcm)
                while len(self._buffer) >= target_bytes_per_chunk:
                    chunk_data = bytes(self._buffer[:target_bytes_per_chunk])
                    self._buffer = self._buffer[target_bytes_per_chunk:]
                    if not is_silent(chunk_data, self._silence_threshold):
                        wav = pcm_to_wav_bytes(
                            chunk_data,
                            self.CHANNELS,
                            self.SAMPLE_RATE,
                            self.SAMPLE_WIDTH,
                        )
                        self._chunks.append(wav)

        try:
            with sd.InputStream(callback=audio_callback, **stream_kwargs):
                while not self._stop_event.is_set():
                    time.sleep(0.1)
        except Exception as exc:
            self._error = f"Audio capture error: {exc}"
        finally:
            self._recording = False
