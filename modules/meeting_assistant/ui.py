"""
Meeting Assistant UI — Tkinter panel for audio capture, transcription, and AI suggestions.
"""

import tkinter as tk
from tkinter import scrolledtext
import time
from datetime import datetime
from typing import Optional

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
        self._stop_pending = False
        self._pending_transcriptions = 0
        self._start_time = None
        self._timer_id = None
        self._poll_id = None
        self._suggestion_after_id = None
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
        self.window.geometry("380x520")
        self.window.configure(bg=COLORS["bg_main"])
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._refresh_ready_status()
        self.window.show()

    def _refresh_ready_status(self):
        """Update status line for Whisper / AI readiness."""
        if not self._status_label or not self.window or not self.window.winfo_exists():
            return
        if self._is_recording:
            return
        parts = []
        if self._transcriber.is_ready():
            parts.append("Whisper ready")
        else:
            parts.append("Whisper: set OPENAI_API_KEY")
        if self.storage.is_suggestions_enabled():
            if self._suggestion_engine.is_ready:
                parts.append("AI ready")
            else:
                parts.append("AI: check API key")
        self._status_label.config(
            text="● " + " · ".join(parts) if parts else "● Ready",
            fg=COLORS["text_dim"],
        )

    def _build_ui(self):
        """Build all UI components."""
        win = self.window
        c = COLORS

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

        controls_frame = tk.Frame(win, bg=c["bg_main"])
        controls_frame.pack(fill=tk.X, padx=10, pady=8)

        self._start_btn = tk.Button(
            controls_frame, text="▶ Start",
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

        self._status_label = tk.Label(
            controls_frame, text="● Ready",
            fg=c["text_dim"], bg=c["bg_main"],
            font=("Courier New", 8),
            wraplength=180,
            justify=tk.RIGHT,
        )
        self._status_label.pack(side=tk.RIGHT, padx=5)

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

        tk.Label(
            win, text="Live Transcript:",
            fg=c["text_normal"], bg=c["bg_main"],
            font=("Courier New", 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(4, 0))

        self._transcript_display = scrolledtext.ScrolledText(
            win,
            bg=c["bg_chat"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, highlightthickness=0,
            state=tk.DISABLED, height=12,
        )
        self._transcript_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        tk.Label(
            win, text="AI Suggestions:",
            fg=c["accent_blue"], bg=c["bg_main"],
            font=("Courier New", 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(4, 0))

        self._suggestion_display = scrolledtext.ScrolledText(
            win,
            bg=c["bg_input"], fg=c["accent_green"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, highlightthickness=0,
            state=tk.DISABLED, height=6,
        )
        self._suggestion_display.pack(fill=tk.BOTH, padx=10, pady=4)

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

        if not self._transcriber.is_ready():
            self.add_system_message(
                "[WARN] Meeting Assistant: OPENAI_API_KEY required for Whisper transcription."
            )
            self._append_to_transcript(
                "[Error] OPENAI_API_KEY is not set — add it to .env or environment variables."
            )
            return

        chunk_duration = self.storage.get_chunk_duration()
        silence_threshold = self.storage.get_silence_threshold()
        self._audio_capture = AudioCapture(
            chunk_duration=chunk_duration,
            silence_threshold=silence_threshold,
        )
        self._audio_capture.start()

        self._is_recording = True
        self._stop_pending = False
        self._pending_transcriptions = 0
        self._start_time = time.time()
        self._transcript_entries = []
        self._full_transcript_text = ""

        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._status_label.config(text="● Starting…", fg=COLORS["accent_blue"])
        self.add_system_message("[OK] Meeting Assistant started — capturing desktop audio")

        self.window.after(400, self._check_capture_error)
        self._update_timer()
        self._poll_audio_chunks()

    def _check_capture_error(self):
        """Check if audio capture failed during startup."""
        if not self._is_recording or not self._audio_capture:
            return
        if self._audio_capture.error:
            self._handle_capture_failed(self._audio_capture.error)

    def _handle_capture_failed(self, error: str):
        """Reset UI after capture cannot continue."""
        self._is_recording = False
        self._stop_pending = False
        self._cancel_timers()
        self._audio_capture = None
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._status_label.config(text="● Error", fg=COLORS["error_red"])
        self._append_to_transcript(f"[Error] {error}")
        self.add_system_message(f"[WARN] Meeting Assistant: {error}")

    def _stop_recording(self):
        """Stop audio capture; save after pending transcriptions finish."""
        if not self._is_recording and not self._stop_pending:
            return

        self._is_recording = False
        self._stop_pending = True
        self._cancel_timers()

        remaining_wav = b""
        if self._audio_capture:
            remaining_wav = self._audio_capture.stop()
            self._audio_capture = None

        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)
        self._status_label.config(text="● Finishing…", fg=COLORS["accent_blue"])

        if remaining_wav:
            self._transcribe_chunk(remaining_wav)

        self._try_finish_stop()

    def _try_finish_stop(self):
        """Save transcript once all in-flight Whisper jobs complete."""
        if not self._stop_pending:
            return
        if self._pending_transcriptions > 0:
            if self.window and self.window.winfo_exists():
                self._status_label.config(
                    text=f"● Transcribing ({self._pending_transcriptions})…",
                    fg=COLORS["accent_blue"],
                )
                self.window.after(500, self._try_finish_stop)
            return

        self._stop_pending = False
        duration = int(time.time() - self._start_time) if self._start_time else 0
        self._status_label.config(text="● Stopped", fg=COLORS["text_dim"])
        self._refresh_ready_status()

        if self._transcript_entries:
            self.storage.save_transcript(self._transcript_entries, duration)
            self.add_system_message(
                f"[OK] Meeting transcript saved ({len(self._transcript_entries)} entries, "
                f"{_format_duration(duration)})"
            )
        else:
            self.add_system_message("[OK] Meeting Assistant stopped — no speech transcribed")

    def _cancel_timers(self):
        if self._timer_id:
            try:
                self.window.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None
        if self._poll_id:
            try:
                self.window.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
        if self._suggestion_after_id:
            try:
                self.window.after_cancel(self._suggestion_after_id)
            except Exception:
                pass
            self._suggestion_after_id = None

    # ------------------------------------------------------------------
    # Timer and polling
    # ------------------------------------------------------------------

    def _update_timer(self):
        if not self._is_recording:
            return
        elapsed = int(time.time() - self._start_time) if self._start_time else 0
        self._timer_label.config(text=_format_duration(elapsed))
        self._timer_id = self.window.after(1000, self._update_timer)

    def _poll_audio_chunks(self):
        if not self._is_recording:
            return

        if self._audio_capture:
            if self._audio_capture.error:
                self._handle_capture_failed(self._audio_capture.error)
                return

            while self._audio_capture.has_chunks():
                chunk_wav = self._audio_capture.get_chunk()
                if chunk_wav:
                    self._transcribe_chunk(chunk_wav)

            device = self._audio_capture.device_name
            if device and self._is_recording:
                self._status_label.config(
                    text=f"● Recording ({device[:22]}…)"
                    if len(device) > 22
                    else f"● Recording ({device})",
                    fg=COLORS["error_red"],
                )

        self._poll_id = self.window.after(1500, self._poll_audio_chunks)

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _transcribe_chunk(self, wav_bytes: bytes):
        self._pending_transcriptions += 1
        if self._is_recording or self._stop_pending:
            self._status_label.config(text="● Transcribing…", fg=COLORS["accent_blue"])

        def on_result(text, segments):
            if self.window and self.window.winfo_exists():
                self.window.after(
                    0, lambda: self._on_transcription_done(text, segments, None)
                )

        def on_error(error):
            if self.window and self.window.winfo_exists():
                self.window.after(
                    0, lambda: self._on_transcription_done("", [], error)
                )

        self._transcriber.transcribe(wav_bytes, on_result=on_result, on_error=on_error)

    def _on_transcription_done(self, text: str, segments: list, error: Optional[str] = None):
        self._pending_transcriptions = max(0, self._pending_transcriptions - 1)

        if error:
            self._append_to_transcript(f"[Transcription Error] {error}")
        elif text and text.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = {
                "time": timestamp,
                "text": text.strip(),
                "segments": segments,
            }
            self._transcript_entries.append(entry)
            self._full_transcript_text += f"\n[{timestamp}] {text.strip()}"
            self._append_to_transcript(f"[{timestamp}]\n{text.strip()}\n")

            if self.storage.is_suggestions_enabled():
                self._schedule_suggestion()

        if self._is_recording:
            self._status_label.config(text="● Recording", fg=COLORS["error_red"])
        elif self._stop_pending:
            self._try_finish_stop()
        else:
            self._refresh_ready_status()

    def _append_to_transcript(self, text: str):
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
        self._refresh_ready_status()

    def _schedule_suggestion(self):
        """Debounce suggestion requests (wait 2s after last transcript update)."""
        if self._suggestion_after_id:
            try:
                self.window.after_cancel(self._suggestion_after_id)
            except Exception:
                pass
        self._suggestion_after_id = self.window.after(2000, self._generate_suggestion)

    def _generate_suggestion(self):
        self._suggestion_after_id = None
        recent_text = self._full_transcript_text[-2000:].strip()
        if not recent_text:
            return

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
        history_win = InvisibleTopLevel(self.window)
        history_win.title("Transcript History")
        history_win.geometry("560x520")
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

        list_frame = tk.Frame(history_win, bg=c["bg_chat"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        history_list = scrolledtext.ScrolledText(
            list_frame,
            bg=c["bg_chat"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT, state=tk.DISABLED,
        )
        history_list.pack(fill=tk.BOTH, expand=True)

        records_holder = {"records": []}

        def refresh_history(*_args):
            query = search_var.get().strip()
            if query:
                records_holder["records"] = self.storage.search_transcripts(query)
            else:
                records_holder["records"] = self.storage.get_history()

            history_list.config(state=tk.NORMAL)
            history_list.delete("1.0", tk.END)

            if not records_holder["records"]:
                history_list.insert(tk.END, "No transcripts found.\n")
            else:
                for i, record in enumerate(records_holder["records"]):
                    date = record.get("date", "")[:19]
                    duration = _format_duration(record.get("duration_seconds", 0))
                    entries = record.get("entry_count", 0)
                    tid = record.get("id", "")

                    history_list.insert(
                        tk.END,
                        f"[{i + 1}] {date}  |  {duration}  |  {entries} entries\n"
                        f"     id: {tid}\n\n",
                    )

            history_list.config(state=tk.DISABLED)

        def open_selected():
            try:
                sel = history_list.index(tk.INSERT).split(".")[0]
                idx = int(sel) - 1
            except (ValueError, IndexError):
                idx = 0
            records = records_holder["records"]
            if idx < 0 or idx >= len(records):
                return
            self._open_transcript_viewer(records[idx].get("id", ""))

        btn_frame = tk.Frame(history_win, bg=c["bg_main"])
        btn_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Button(
            btn_frame, text="Open Selected",
            command=open_selected,
            bg=c["accent_green"], fg=c["bg_main"],
            font=("Courier New", 9, "bold"), relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame, text="Refresh",
            command=refresh_history,
            bg=c["bg_header"], fg=c["text_normal"],
            font=("Courier New", 9), relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=2)

        search_var.trace_add("write", refresh_history)
        refresh_history()
        history_win.show()

    def _open_transcript_viewer(self, transcript_id: str):
        data = self.storage.get_transcript(transcript_id)
        if not data:
            self.add_system_message("[WARN] Transcript not found.")
            return

        viewer = InvisibleTopLevel(self.window)
        viewer.title("Transcript")
        viewer.geometry("560x480")
        viewer.configure(bg=COLORS["bg_main"])
        c = COLORS

        header = tk.Frame(viewer, bg=c["bg_header"])
        header.pack(fill=tk.X)
        date = data.get("date", "")[:19]
        tk.Label(
            header,
            text=f"📋 {date} · {_format_duration(data.get('duration_seconds', 0))}",
            fg=c["accent_green"],
            bg=c["bg_header"],
            font=("Courier New", 11, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=8)
        create_header_close_button(
            header, viewer.destroy, colors=c,
        ).pack(side=tk.RIGHT, padx=(4, 8), pady=6)

        body = scrolledtext.ScrolledText(
            viewer,
            bg=c["bg_chat"], fg=c["text_normal"],
            font=("Courier New", 9), wrap=tk.WORD,
            relief=tk.FLAT,
        )
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        for entry in data.get("entries", []):
            t = entry.get("time", "")
            txt = entry.get("text", "")
            body.insert(tk.END, f"[{t}]\n{txt}\n\n")
        body.config(state=tk.DISABLED)
        viewer.show()

    def _clear_transcript(self):
        if self._is_recording:
            self.add_system_message("[WARN] Stop recording before clearing the transcript.")
            return
        self._transcript_entries = []
        self._full_transcript_text = ""
        self._transcript_display.config(state=tk.NORMAL)
        self._transcript_display.delete("1.0", tk.END)
        self._transcript_display.config(state=tk.DISABLED)
        self._suggestion_display.config(state=tk.NORMAL)
        self._suggestion_display.delete("1.0", tk.END)
        self._suggestion_display.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Window movement / cleanup
    # ------------------------------------------------------------------

    def _start_move(self, event):
        self.window.x = event.x
        self.window.y = event.y

    def _do_move(self, event):
        x = self.window.winfo_x() - self.window.x + event.x
        y = self.window.winfo_y() - self.window.y + event.y
        self.window.geometry(f"+{x}+{y}")

    def _on_close(self):
        if self._is_recording or self._stop_pending:
            self._stop_recording()
        self._cancel_timers()
        if self.window:
            self.window.destroy()
            self.window = None
