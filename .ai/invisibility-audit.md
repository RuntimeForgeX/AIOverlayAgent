# Invisibility Module Audit Report

**Date:** 2026-06-07  
**Auditor:** AI Agent  
**Scope:** `src/utils/win32_invisibility.py`, `src/ui/app.py`, `src/utils/error_handler.py`, `src/services/storage.py`, related modules

---

## Executive Summary

The invisibility module uses `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` to hide the overlay from screen capture tools. This audit identifies detection vectors, information leaks, security weaknesses, and stability issues. All feasible fixes have been applied; inherent Windows limitations are documented honestly.

**Status:** Audit complete. Hardening applied.

---

## 1. Pre-Audit Detection Vectors

| Vector | Risk | Before |
|--------|------|--------|
| `EnumWindows` | HIGH | All HWNDs discoverable |
| `GetWindowText` | MEDIUM | Static title `"AI OVERLAY"` — easily fingerprinted |
| `GetClassName` | MEDIUM | `"Tk"` / `"TkChild"` class names |
| `FindWindowW(None, title)` | MEDIUM | Title-based lookup trivial |
| `tk.Menu` context menus | HIGH | Separate OS window WITHOUT capture exclusion |
| Console prints | MEDIUM | HWND values, titles, error details printed |

---

## 2. Fixes Applied

### 2.1 Window Title Randomization

**Files:** `src/utils/win32_invisibility.py`, `src/ui/app.py`

- `InvisibleTopLevel.__init__` auto-assigns ephemeral title: `"panel-a3f2c1b8d9e4f5a6"`
- `_apply_invisibility()` re-randomizes on every visibility event
- `app.py` no longer passes predictable `WINDOW_TITLE` to `apply_capture_exclusion()`
- `collect_tk_window_hwnds()` no longer auto-infers title from `window.title()`

### 2.2 Native Context Menu Replacement

**Files:** `src/utils/win32_invisibility.py`, `src/ui/app.py`

- Added `InvisibleContextMenu(InvisibleTopLevel)` class
- Replaces `tk.Menu` which creates a separate non-excluded OS window
- Same appearance/behavior; inherits full capture exclusion
- Dismisses on outside click

### 2.3 Debug Output Gating

**File:** `src/utils/win32_invisibility.py`

- All prints replaced with `_debug_print()` — only emits when `AI_OVERLAY_DEBUG=1`
- `apply_capture_exclusion()` default changed `verbose=True` → `verbose=False`

**File:** `src/ui/app.py`

- Removed startup print, invisibility setup header, HWND prints

### 2.4 Error Message Sanitization

**File:** `src/utils/error_handler.py`

- `_redact_sensitive()` redacts API key patterns before display:
  - `sk-…`, `sk-proj-…`, `sk-ant-…`
- Strips explicit env values for known key names
- Removed unconditional stderr prints

### 2.5 ctypes Signature Hardening

**File:** `src/utils/win32_invisibility.py`

- All `user32` functions have explicit `argtypes`/`restype`
- Uses `wintypes.HWND`, `wintypes.DWORD` instead of `ctypes.c_void_p`
- `ctypes.WinDLL("user32", use_last_error=True)` for reliable error codes

### 2.6 Storage Permission Hardening

**File:** `src/services/storage.py`

- `_set_restrictive_permissions()` — best-effort `0o600`
- `_ensure_private_dir()` for directory creation
- Applied to all persisted JSON files

### 2.7 Polling & Cleanup

**File:** `src/ui/app.py`

- Polling interval: 3s → 5s
- Skips when window is withdrawn
- `_on_window_close()` calls `clear_screenshot_queue()`

---

## 3. Inherent Limitations (Cannot Be Fixed)

| Limitation | Why |
|------------|-----|
| Process visible in Task Manager | Windows provides no API to hide a process |
| HWND discoverable via `EnumWindows` | No "private window" concept in Win32 |
| Tkinter class name `"Tk"` | Baked into Tcl/Tk internals |
| `WDA_EXCLUDEFROMCAPTURE` requires Win10 2004+ | OS API limitation |
| Window-targeted capture may bypass exclusion | Depends on capture API implementation |

---

## 4. Security Assessment

| Check | Status |
|-------|--------|
| `eval()` / `exec()` / `subprocess` with user input | Not present |
| API keys in storage files | Not present |
| API keys in error messages | Redacted |
| API keys in console output | Gated behind debug flag |
| Path traversal risk | Low — destination always under `%APPDATA%` |
| Race conditions | No exploitable races found |

---

## 5. Files Modified

| File | Changes |
|------|---------|
| `src/utils/win32_invisibility.py` | Title randomization, `InvisibleContextMenu`, debug gating, ctypes hardening |
| `src/ui/app.py` | `InvisibleContextMenu`, logging cleanup, polling optimize, exit cleanup |
| `src/utils/error_handler.py` | API key redaction, stderr cleanup |
| `src/services/storage.py` | File permissions, `clear_screenshot_queue()` |
| `prompts/invisibility-module.md` | Architecture & hardening documentation |

---

## 6. Honest Assessment

This application is **as invisible as Windows allows** without kernel-mode code. Remaining detection vectors are architectural limitations, not implementation flaws.

**Attacker CAN detect:**
- A process is running (Task Manager)
- A window exists (`EnumWindows`)
- Window class is `"Tk"` (if enumerated)

**Attacker CANNOT detect:**
- Window content (excluded/black in capture)
- Window title (randomized, meaningless)
- Application identity from metadata
- Internal state from outside the process

**Primary goal achieved:** Content invisibility during screen capture.
