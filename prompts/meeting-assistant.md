# Meeting Assistant

## Overview
The Meeting Assistant is an isolated module designed to transcribe desktop audio during meetings (Google Meet, Teams, Zoom, Discord, etc.) and generate AI response suggestions based on the conversation and the user's personal context.

## Architecture
- **Location**: `modules/meeting_assistant/`
- **Audio Capture**: Uses `sounddevice` to capture system/desktop audio via a loopback input device (e.g. **Stereo Mix**). Enable Stereo Mix under Windows Sound → Recording if no device is found.
- **Transcription**: Uses the OpenAI Whisper API (`whisper-1` model).
- **Storage**: All data is stored in `%APPDATA%\PersonalAiAgentSurya\meeting_assistant\`.
  - `transcripts/` — Individual transcript JSON files.
  - `history.json` — Summary of past transcripts.
  - `settings.json` — Module settings.

## Data Flow
1. User clicks "Start" in the Meeting Assistant UI.
2. `audio_capture.py` begins buffering audio in a background thread. It converts 32-bit float audio to 16-bit PCM.
3. Every 30 seconds (configurable), if the chunk contains speech (RMS energy > threshold), it is converted to a WAV byte stream.
4. The UI polls for chunks and sends them to `transcriber.py`.
5. `transcriber.py` calls the OpenAI Whisper API using the environment's `OPENAI_API_KEY`.
6. The transcription is added to the UI display and saved to memory.
7. If "AI Suggestions" is enabled, `suggestion_engine.py` is triggered with the recent transcript text. It reuses the main app's LLM provider and injects the user's personal context (if available) to generate a response suggestion.
8. Upon clicking "Stop", the final transcript is saved to disk via `storage.py`.

## Settings
- **AI Suggestions Enabled**: Toggles whether response suggestions are generated.
- **Chunk Duration**: How many seconds of audio are buffered before sending to Whisper.

## Removal Steps
To completely remove this feature from the codebase:
1. Delete the `modules/meeting_assistant/` directory.
2. In `main.py`, remove the `MeetingStorage` import and instantiation block.
3. In `src/ui/app.py`, remove the "Meeting" button from `_quick_buttons`.
4. In `src/ui/app.py`, remove the `open_meeting_assistant` method.
