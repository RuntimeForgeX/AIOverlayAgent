"""
WASAPI Loopback audio capture for Windows.

Captures ONLY desktop/system audio (no microphone).
Uses sounddevice with WASAPI backend in loopback mode.
"""

import io
import struct
import threading
import time
import wave
from typing import Optional


def _rms_energy(audio_bytes: bytes, sample_width: int = 2) -> float:
    """Calculate RMS energy of audio data (16-bit PCM)."""
    if not audio_bytes or len(audio_bytes) < sample_width:
        return 0.0
    n_samples = len(audio_bytes) // sample_width
    if n_samples == 0:
        return 0.0
    fmt = f"<{n_samples}h"
    try:
        samples = struct.unpack(fmt, audio_bytes[:n_samples * sample_width])
    except struct.error:
        return 0.0
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / n_samples) ** 0.5


def is_silent(audio_bytes: bytes, threshold: float = 200.0) -> bool:
    """Check if an audio chunk is silence based on RMS energy."""
    return _rms_energy(audio_bytes) < threshold


def pcm_to_wav_bytes(pcm_data: bytes, channels: int = 1,
                      sample_rate: int = 16000, sample_width: int = 2) -> bytes:
    """Convert raw PCM bytes to WAV format in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class AudioCapture:
    """Captures desktop audio via Windows WASAPI loopback.

    Audio is captured as 16kHz mono 16-bit PCM (Whisper-compatible).
    Chunks are accumulated in an internal buffer and can be retrieved
    when ready (based on configurable chunk duration).
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    SAMPLE_WIDTH = 2  # 16-bit
    CHUNK_DURATION = 30  # seconds

    def __init__(self, chunk_duration: int = 30):
        self.CHUNK_DURATION = chunk_duration
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._chunks = []  # completed chunks ready for transcription
        self._stop_event = threading.Event()
        self._error: Optional[str] = None
        self._native_samplerate = 48000
        self._native_channels = 2

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def error(self) -> Optional[str]:
        return self._error

    def start(self):
        """Begin capturing desktop audio."""
        if self._recording:
            return

        self._error = None
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

        if remaining and not is_silent(remaining):
            try:
                import numpy as np
                # Convert bytes to numpy float32 array
                pcm_arr = np.frombuffer(remaining, dtype=np.int16).astype(np.float32) / 32767.0
                
                # Reshape to (frames, channels)
                frames = len(pcm_arr) // self._native_channels
                pcm_arr = pcm_arr[:frames * self._native_channels].reshape(-1, self._native_channels)
                
                # Downmix to Mono
                if self._native_channels > 1:
                    mono_arr = np.mean(pcm_arr, axis=1)
                else:
                    mono_arr = pcm_arr.flatten()
                    
                # Resample to target SAMPLE_RATE using linear interpolation
                if self._native_samplerate != self.SAMPLE_RATE:
                    new_length = int(len(mono_arr) * self.SAMPLE_RATE / self._native_samplerate)
                    old_indices = np.arange(len(mono_arr))
                    new_indices = np.linspace(0, len(mono_arr) - 1, new_length)
                    mono_arr = np.interp(new_indices, old_indices, mono_arr)
                    
                # Convert to int16 PCM bytes
                pcm_bytes = (mono_arr * 32767).astype(np.int16).tobytes()
                return pcm_to_wav_bytes(pcm_bytes, self.CHANNELS, self.SAMPLE_RATE, self.SAMPLE_WIDTH)
            except Exception as e:
                print(f"[AudioCapture] Error converting remaining chunk: {e}")
                
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
        except ImportError:
            self._error = "sounddevice is not installed. Install it with: pip install sounddevice"
            self._recording = False
            return

        # Find WASAPI loopback device
        loopback_device = self._find_loopback_device(sd)
        if loopback_device is None:
            self._error = "No WASAPI loopback device found. Ensure Windows audio is available."
            self._recording = False
            return

        device_info = sd.query_devices(loopback_device)
        self._native_channels = int(device_info.get('max_input_channels', 0))
        if self._native_channels == 0:
            self._native_channels = int(device_info.get('max_output_channels', 2))
        if self._native_channels == 0:
            self._native_channels = 2
            
        self._native_samplerate = int(device_info.get('default_samplerate', 48000))
        if self._native_samplerate <= 0:
            self._native_samplerate = 48000

        bytes_per_chunk = (self._native_samplerate * self.SAMPLE_WIDTH *
                           self._native_channels * self.CHUNK_DURATION)

        try:
            import numpy as np
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"[AudioCapture] Status: {status}")
                
                # 1. Downmix to Mono
                if indata.shape[1] > 1:
                    mono_data = np.mean(indata, axis=1)
                else:
                    mono_data = indata.flatten()
                    
                # 2. Resample to 16000Hz using linear interpolation
                if self._native_samplerate != self.SAMPLE_RATE:
                    new_length = int(len(mono_data) * self.SAMPLE_RATE / self._native_samplerate)
                    old_indices = np.arange(len(mono_data))
                    new_indices = np.linspace(0, len(mono_data) - 1, new_length)
                    mono_data = np.interp(new_indices, old_indices, mono_data)
                    
                # 3. Convert float32 to int16 PCM bytes
                pcm = (mono_data * 32767).astype(np.int16).tobytes()
                
                with self._lock:
                    self._buffer.extend(pcm)
                    # Note: our buffer is now storing the processed 16kHz Mono PCM.
                    # bytes_per_chunk should be calculated based on 16kHz mono.
                    # Wait, bytes_per_chunk in the outer scope is calculated using native format.
                    # Let's fix that calculation here.
                    target_bytes_per_chunk = (self.SAMPLE_RATE * self.SAMPLE_WIDTH * 
                                              self.CHANNELS * self.CHUNK_DURATION)
                                              
                    if len(self._buffer) >= target_bytes_per_chunk:
                        chunk_data = bytes(self._buffer[:target_bytes_per_chunk])
                        self._buffer = self._buffer[target_bytes_per_chunk:]
                        if not is_silent(chunk_data):
                            wav = pcm_to_wav_bytes(
                                chunk_data, self.CHANNELS,
                                self.SAMPLE_RATE, self.SAMPLE_WIDTH,
                            )
                            self._chunks.append(wav)

            # Open WASAPI loopback stream using device's native settings
            with sd.InputStream(
                device=loopback_device,
                samplerate=self._native_samplerate,
                channels=self._native_channels,
                dtype="float32",
                callback=audio_callback,
                blocksize=int(self._native_samplerate * 0.5),  # 500ms blocks
                extra_settings=sd.WasapiSettings(exclusive=False),
            ):
                while not self._stop_event.is_set():
                    time.sleep(0.1)

        except Exception as e:
            self._error = f"Audio capture error: {e}"
        finally:
            self._recording = False

    def _find_loopback_device(self, sd) -> Optional[int]:
        """Find a WASAPI loopback capture device."""
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()

            # Find WASAPI host API index
            wasapi_idx = None
            for i, api in enumerate(hostapis):
                if "wasapi" in api.get("name", "").lower():
                    wasapi_idx = i
                    break

            if wasapi_idx is None:
                return None

            # Find a loopback device (output device used as input)
            # WASAPI loopback: we look for the default output device under WASAPI
            for i, dev in enumerate(devices):
                if dev.get("hostapi") == wasapi_idx:
                    if dev.get("max_output_channels", 0) > 0:
                        # This is an output device — use it for loopback
                        # sounddevice supports loopback via WasapiSettings
                        return i

            # Fallback: try default output device
            default_output = sd.default.device[1]
            if default_output is not None and default_output >= 0:
                return default_output

        except Exception as e:
            print(f"[AudioCapture] Error finding loopback device: {e}")

        return None
