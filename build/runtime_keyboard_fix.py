"""
PyInstaller runtime hook: fix keyboard low-level hook on 64-bit Windows.

See https://github.com/boppreh/keyboard/issues/157
"""

import sys

if sys.platform == "win32":
    try:
        import ctypes
        import keyboard._winkeyboard as _wk

        if not getattr(_wk, "_pyinstaller_patched", False):
            _orig_set_hook = _wk.SetWindowsHookEx

            def _set_hook_ex(id_hook, lpfn, hmod, thread_id):
                if hmod is not None:
                    try:
                        handle_val = int(ctypes.cast(hmod, ctypes.c_void_p).value or 0)
                    except (TypeError, ValueError, ctypes.ArgumentError):
                        handle_val = int(_wk.GetModuleHandleW(None) or 0)
                else:
                    handle_val = int(_wk.GetModuleHandleW(None) or 0)
                fixed = ctypes.c_void_p(ctypes.c_ulonglong(handle_val).value)
                return _orig_set_hook(id_hook, lpfn, fixed, thread_id)

            _wk.SetWindowsHookEx = _set_hook_ex
            _wk._pyinstaller_patched = True
    except Exception:
        pass
