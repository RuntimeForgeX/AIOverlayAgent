"""
Meeting Assistant UI — Tkinter panel for audio capture, transcription, and AI suggestions.

Uses InvisibleOverlayPanel / InvisibleTopLevel from win32_invisibility for
taskbar-free, non-activating, capture-excluded windows.
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import time
from datetime import datetime

from src.ui.styles.themes import COLORS
from src.ui.close_button import create_header_close_button
from src.utils.win32_invisibility import InvisibleTopLevel, InvisibleOverlayPanel, present_overlay_window
from src.config.settings import load_config

from modules.meeting_assistant.audio_capture import AudioCapture
from modules.meeting_assistant.transcriber import WhisperTranscriber
from modules.meeting_assistant.suggestion_engine import SuggestionEngine
from modules.meeting_assistant.storage import MeetingStorage


def _format_duration(seconds: int) -> str:
    """Format duration as HH:MM:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class MeetingAssistantUI:
    """UI panel for the Meeting Assistant."""

    def __init__(self, parent, meeting_storage, personal_context_manager=None,
                 config=None, add_system_message=None):
        self.parent = parent
        self.storage = meeting_storage
        self.personal_context_manager = personal_context_manager
        self.config = config or load_config()
        self.add_system_message = add_system_message or (lambda msg: None)

        self.window = None
        self._audio_capture = None
        self._transcriber = WhisperTranscriber()
        self._suggestion_engine = SuggestionEngine(
            config=self.config,
            personal_context_manager=personal_context_manager,
        )

        self._is_recording = False
        self._start_time = None
        self._timer_id = None
        self._poll_id = None
        self._transcript_entries = []
        self._full_transcript_text = ""

    def open(self):
        """Open the meeting assistant window."""
        if self.window and self.window.winfo_exists():
            present_overlay_window(self.window)
            return

        try:
            opacity = float(self.config.get("UI", "opacity", fallback="0.8"))
        except ValueError:
            opacity = 0.8

        self.window = InvisibleOverlayPanel(self.parent, opacity=opacity)
        self.window.title("Meeting Assistant")
        self.window.geometry("350x450")
        self.window.configure(bg=COLORS["bg_main"])
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.window.show()

    def _build_ui(self):
        """Build all UI components."""
        win = self.window
        c = COLORS

        # ---- Header ----
        header = tk.Frame(win, bg=c["bg_header"])
        header.pack(fill=tk.X)

        header.bind("<Button-1>", self._start_move)
        header.bind("<B1-Motion>", self._do_move)

        title_label = tk.Label(
            header, text="🎤 Meeting Assistant",
            fg=c["accent_green"], bg=c["bg_header"],
            font=("Courier New", 12, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=8)
        title_label.bind("<Button-1>", self._start_move)
        title_label.bind("<B1-Motion>", self._do_move)

        self._timer_label = tk.Label(
            header, text="00:00",
            fg=c["text_dim"], bg=c["bg_header"],
            font=("Courier New", 10),
        )
        self._timer_label.pack(side=tk.RIGHT, padx=10, pady=8)

        create_header_close_button(
            header, self._on_close, colors=c,
        ).pack(side=tk.RIGHT, padx=(4, 8), pady=6)

        # ---- Controls ----
        controls_frame = tk.Frame(win, bg=c["bg_main"])
        controls_frame.pack(fill=tk.X, padx=10, pady=8)

        self._start_btn = tk.Button(
            controls_frame, text="▶ Start Meeting Assistant",
            command=self._start_recording,
            bg=c["accent_green"], fg=c["bg_main"],
            font=("Courier New", 10, "bold"), relief=tk.FLAT,
        )
        self._start_btn.pack(side=tk.LEFT, padx=2)

        self._stop_btn = tk.Button(
            controls_frame, text="■ Stop",
            command=self._stop_recording,
            bg=c["error_red"], fg="#ffffff",
            font=("Courier New", 10, "bold"), relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=2)

        # Status indicator
        self._status_label = tk.Label(
            controls_frame, text="● Ready",
            fg=c["text_dim"], bg=c["bg_main"],
            font=("Courier New", 9),
        )
        self._status_label.pack(side=tk.RIGHT, padx=5)

        # ---- AI Suggestions toggle ----
        toggle_frame = tk.Frame(win, bg=c["bg_main"])
        toggle_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        self._suggestions_var = tk.BooleanVar(
            value=self.storage.is_suggestions_enabled()
        )
        suggestions_cb = tk.Checkbutton(
            toggle_frame, text="Enable AI Suggestions",
            variable=self._suggestions_var,
            command=self._toggle_suggestions,
            bg=c["bg_main"], fg=c["accent_blue"],
            selectcolor=c["bg_main"],
            activebackground=c["bg_main"],
            activeforeground=c["accent_blue"],
            font=("Courier New", 9),
        )
        suggestions_cb.pack(side=tk.LEFT)

        # ---- Transcript display ----
        transcript_label = tk.Label(
            win, text="Live Transcript:",
            fg=c["text_normal"], bg=c["bg_main"],
            font=("Courier New", 9, "bold"),
            anchor="w",
        )
        transcript_label.pack(fill=tk.X, padx=10, pady=(4, 0))

        self._transcript_display = scrolledtext.ScrolledText(
            win,
            bg=c["bg_chat"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, highlightthickness=0,
            state=tk.DISABLED, height=12,
        )
        self._transcript_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # Configure tags for transcript
        self._transcript_display.tag_config(
            "timestamp", foreground=c["text_dim"], font=("Courier New", 8),
        )
        self._transcript_display.tag_config(
            "speaker", foreground=c["accent_blue"], font=("Courier New", 9, "bold"),
        )
        self._transcript_display.tag_config(
            "text", foreground=c["text_normal"],
        )

        # ---- AI Suggestion display ----
        suggestion_label = tk.Label(
            win, text="AI Suggestions:",
            fg=c["accent_blue"], bg=c["bg_main"],
            font=("Courier New", 9, "bold"),
            anchor="w",
        )
        suggestion_label.pack(fill=tk.X, padx=10, pady=(4, 0))

        self._suggestion_display = scrolledtext.ScrolledText(
            win,
            bg=c["bg_input"], fg=c["accent_green"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, highlightthickness=0,
            state=tk.DISABLED, height=6,
        )
        self._suggestion_display.pack(fill=tk.BOTH, padx=10, pady=4)

        # ---- Bottom controls ----
        bottom_frame = tk.Frame(win, bg=c["bg_main"])
        bottom_frame.pack(fill=tk.X, padx=10, pady=4)

        tk.Button(
            bottom_frame, text="📜 History",
            command=self._show_history,
            bg=c["bg_header"], fg=c["text_normal"],
            font=("Courier New", 8), relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            bottom_frame, text="🗑 Clear",
            command=self._clear_transcript,
            bg=c["bg_header"], fg=c["text_normal"],
            font=("Courier New", 8), relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    # Recording controls
    # ------------------------------------------------------------------

    def _start_recording(self):
        """Start audio capture and transcription."""
        if self._is_recording:
            return

        chunk_duration = self.storage.get_chunk_duration()
        self._audio_capture = AudioCapture(chunk_duration=chunk_duration)
        self._audio_capture.start()

        # Check for immediate errors
        self.window.after(500, self._check_capture_error)

        self._is_recording = True
        self._start_time = time.time()
        self._transcript_entries = []
        self._full_transcript_text = ""

        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._status_label.config(text="● Recording", fg=COLORS["error_red"])
        self.add_system_message("[OK] Meeting Assistant started — recording desktop audio")

        self._update_timer()
        self._poll_audio_chunks()

    def _check_capture_error(self):
        """Check if audio capture had an initialization error."""
        if self._audio_capture and self._audio_capture.error:
            error = self._audio_capture.error
            self._is_recording = False
            self._start_btn.config(state=tk.NORMAL)
            self._stop_btn.config(state=tk.DISABLED)
            self._status_label.config(text="● Error", fg=COLORS["error_red"])
            self._append_to_transcript(f"[Error] {error}")
            self.add_system_message(f"[WARN] Meeting Assistant error: {error}")

    def _stop_recording(self):
        """Stop audio capture and save transcript."""
        if not self._is_recording:
            return

        self._is_recording = False

        # Cancel timers
        if self._timer_id:
            self.window.after_cancel(self._timer_id)
            self._timer_id = None
        if self._poll_id:
            self.window.after_cancel(self._poll_id)
            self._poll_id = None

        # Stop audio capture and process remaining audio
        if self._audio_capture:
            remaining_wav = self._audio_capture.stop()
            if remaining_wav:
                self._transcribe_chunk(remaining_wav)

        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._status_label.config(text="● Stopped", fg=COLORS["text_dim"])

        # Calculate duration
        duration = int(time.time() - self._start_time) if self._start_time else 0

        # Save transcript if we have entries
        if self._transcript_entries:
            record = self.storage.save_transcript(
                self._transcript_entries, duration,
            )
            self.add_system_message(
                f"[OK] Meeting transcript saved ({len(self._transcript_entries)} entries, "
                f"{_format_duration(duration)})"
            )
        else:
            self.add_system_message("[OK] Meeting Assistant stopped — no transcript to save")

    # ------------------------------------------------------------------
    # Timer and polling
    # ------------------------------------------------------------------

    def _update_timer(self):
        """Update the timer display."""
        if not self._is_recording:
            return
        elapsed = int(time.time() - self._start_time) if self._start_time else 0
        self._timer_label.config(text=_format_duration(elapsed))
        self._timer_id = self.window.after(1000, self._update_timer)

    def _poll_audio_chunks(self):
        """Poll for completed audio chunks and send to Whisper."""
        if not self._is_recording:
            return

        if self._audio_capture and self._audio_capture.has_chunks():
            chunk_wav = self._audio_capture.get_chunk()
            if chunk_wav:
                self._transcribe_chunk(chunk_wav)

        # Also check for errors
        if self._audio_capture and self._audio_capture.error:
            self._append_to_transcript(
                f"[Audio Error] {self._audio_capture.error}"
            )

        self._poll_id = self.window.after(2000, self._poll_audio_chunks)

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _transcribe_chunk(self, wav_bytes: bytes):
        """Send an audio chunk to Whisper for transcription."""
        self._status_label.config(text="● Transcribing...", fg=COLORS["accent_blue"])

        def on_result(text, segments):
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._on_transcription(text, segments))

        def on_error(error):
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._on_transcription_error(error))

        self._transcriber.transcribe(wav_bytes, on_result=on_result, on_error=on_error)

    def _on_transcription(self, text: str, segments: list):
        """Handle a transcription result."""
        if not text or not text.strip():
            if self._is_recording:
                self._status_label.config(
                    text="● Recording", fg=COLORS["error_red"],
                )
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        entry = {
            "time": timestamp,
            "text": text.strip(),
            "segments": segments,
        }
        self._transcript_entries.append(entry)
        self._full_transcript_text += f"\n[{timestamp}] {text.strip()}"

        # Display in transcript
        self._append_to_transcript(f"[{timestamp}]\n{text.strip()}\n")

        if self._is_recording:
            self._status_label.config(text="● Recording", fg=COLORS["error_red"])

        # Generate AI suggestion if enabled
        if self.storage.is_suggestions_enabled():
            self._generate_suggestion()

    def _on_transcription_error(self, error: str):
        """Handle a transcription error."""
        self._append_to_transcript(f"[Transcription Error] {error}")
        if self._is_recording:
            self._status_label.config(text="● Recording", fg=COLORS["error_red"])

    def _append_to_transcript(self, text: str):
        """Append text to the transcript display."""
        if not self._transcript_display or not self.window.winfo_exists():
            return
        self._transcript_display.config(state=tk.NORMAL)
        self._transcript_display.insert(tk.END, text + "\n")
        self._transcript_display.see(tk.END)
        self._transcript_display.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # AI Suggestions
    # ------------------------------------------------------------------

    def _toggle_suggestions(self):
        enabled = self._suggestions_var.get()
        self.storage.set_suggestions_enabled(enabled)
        state = "enabled" if enabled else "disabled"
        self.add_system_message(f"[OK] AI suggestions {state}")

    def _generate_suggestion(self):
        """Generate AI suggestion from current transcript."""
        # Use last ~2000 chars of transcript for context
        recent_text = self._full_transcript_text[-2000:]

        def on_response(suggestion_text, tokens):
            if self.window and self.window.winfo_exists():
                self.window.after(
                    0, lambda: self._display_suggestion(suggestion_text),
                )

        def on_error(error):
            if self.window and self.window.winfo_exists():
                self.window.after(
                    0, lambda: self._display_suggestion(f"[Error] {error}"),
                )

        self._suggestion_engine.generate_suggestion(
            recent_text, on_response=on_response, on_error=on_error,
        )

    def _display_suggestion(self, text: str):
        """Display an AI suggestion."""
        if not self._suggestion_display or not self.window.winfo_exists():
            return
        self._suggestion_display.config(state=tk.NORMAL)
        self._suggestion_display.delete("1.0", tk.END)
        self._suggestion_display.insert("1.0", text)
        self._suggestion_display.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _show_history(self):
        """Show transcript history browser."""
        history_win = InvisibleTopLevel(self.window)
        history_win.title("Transcript History")
        history_win.geometry("550x500")
        history_win.configure(bg=COLORS["bg_main"])

        c = COLORS

        history_header = tk.Frame(history_win, bg=c["bg_header"])
        history_header.pack(fill=tk.X)
        tk.Label(
            history_header,
            text="📜 Transcript History",
            fg=c["accent_green"],
            bg=c["bg_header"],
            font=("Courier New", 12, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=8)
        create_header_close_button(
            history_header, history_win.destroy, colors=c,
        ).pack(side=tk.RIGHT, padx=(4, 8), pady=6)

        # Search bar
        search_frame = tk.Frame(history_win, bg=c["bg_main"])
        search_frame.pack(fill=tk.X, padx=10, pady=4)

        search_var = tk.StringVar()
        tk.Label(
            search_frame, text="🔍",
            fg=c["text_dim"], bg=c["bg_main"],
            font=("Courier New", 10),
        ).pack(side=tk.LEFT, padx=(0, 5))

        search_entry = tk.Entry(
            search_frame,
            textvariable=search_var,
            bg=c["bg_input"], fg=c["text_normal"],
            font=("Courier New", 9), relief=tk.FLAT,
            insertbackground=c["accent_green"],
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # History list
        list_frame = tk.Frame(history_win, bg=c["bg_chat"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        history_list = scrolledtext.ScrolledText(
            list_frame,
            bg=c["bg_chat"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, state=tk.DISABLED,
        )
        history_list.pack(fill=tk.BOTH, expand=True)

        def refresh_history(*_args):
            query = search_var.get().strip()
            if query:
                records = self.storage.search_transcripts(query)
            else:
                records = self.storage.get_history()

            history_list.config(state=tk.NORMAL)
            history_list.delete("1.0", tk.END)

            if not records:
                history_list.insert(tk.END, "No transcripts found.\n")
            else:
                for record in records:
                    date = record.get("date", "")[:19]
                    duration = _format_duration(record.get("duration_seconds", 0))
                    entries = record.get("entry_count", 0)
                    tid = record.get("id", "")

                    history_list.insert(
                        tk.END,
                        f"📋 {date}  |  {duration}  |  {entries} entries\n"
                        f"   ID: {tid[:8]}...\n\n",
                    )

            history_list.config(state=tk.DISABLED)

        search_var.trace_add("write", refresh_history)
        refresh_history()

        history_win.show()

    def _clear_transcript(self):
        """Clear the current transcript display."""
        self._transcript_display.config(state=tk.NORMAL)
        self._transcript_display.delete("1.0", tk.END)
        self._transcript_display.config(state=tk.DISABLED)
        self._suggestion_display.config(state=tk.NORMAL)
        self._suggestion_display.delete("1.0", tk.END)
        self._suggestion_display.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Window Movement
    # ------------------------------------------------------------------
    def _start_move(self, event):
        self.window.x = event.x
        self.window.y = event.y

    def _do_move(self, event):
        x = self.window.winfo_x() - self.window.x + event.x
        y = self.window.winfo_y() - self.window.y + event.y
        self.window.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _on_close(self):
        """Handle window close — stop recording if active."""
        if self._is_recording:
            self._stop_recording()
        if self._timer_id:
            try:
                self.window.after_cancel(self._timer_id)
            except Exception:
                pass
        if self._poll_id:
            try:
                self.window.after_cancel(self._poll_id)
            except Exception:
                pass
        self.window.destroy()
        self.window = None
