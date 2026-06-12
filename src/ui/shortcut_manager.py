"""
Centralized global shortcut manager for the AI Overlay HUD.

All keyboard shortcuts are registered and dispatched through this module.
Handlers are always scheduled on the Tk main thread for thread safety.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Dict, Optional, Tuple

import keyboard

from src.config.settings import get_config_value


class ShortcutManager:
    """Centralized global shortcut registry and dispatcher."""

    def __init__(self, root: tk.Tk, config):
        self._root = root
        self._config = config
        self._bindings: Dict[str, _Binding] = {}
        self._active = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        combo: str,
        handler: Callable,
        description: str = "",
    ) -> None:
        """Register a named shortcut.

        ``combo`` is a ``keyboard`` library combo string such as
        ``"ctrl+shift+space"``.  The handler is always dispatched on the
        Tk main thread via ``root.after(0, ...)``.
        """
        if name in self._bindings:
            self.unregister(name)

        self._bindings[name] = _Binding(
            name=name,
            combo=combo,
            handler=handler,
            description=description,
            remover=None,
        )

    def register_from_config(
        self,
        name: str,
        config_key: str,
        default_combo: str,
        handler: Callable,
        description: str = "",
    ) -> None:
        """Register a shortcut whose combo is read from ``[HOTKEYS]`` in config."""
        combo = get_config_value(self._config, "HOTKEYS", config_key, default_combo)
        self.register(name, combo, handler, description)

    def activate_all(self) -> list[str]:
        """Hook every registered shortcut into the OS via ``keyboard``.

        Returns a list of combos that failed to register.
        """
        self._warmup()
        failed: list[str] = []
        for binding in self._bindings.values():
            try:
                remover = keyboard.add_hotkey(
                    binding.combo,
                    lambda h=binding.handler: self._dispatch(h),
                    suppress=False,
                )
                binding.remover = remover
            except Exception:
                failed.append(binding.combo)

        self._active = True
        return failed

    def unregister(self, name: str) -> None:
        """Remove a single shortcut by name."""
        binding = self._bindings.pop(name, None)
        if binding and binding.remover is not None:
            try:
                binding.remover()
            except Exception:
                pass

    def unregister_all(self) -> None:
        """Remove every registered shortcut (call on exit)."""
        for binding in list(self._bindings.values()):
            if binding.remover is not None:
                try:
                    binding.remover()
                except Exception:
                    pass
        self._bindings.clear()
        self._active = False

    def dispatch(self, name: str) -> None:
        """Execute a shortcut handler by name (thread-safe)."""
        binding = self._bindings.get(name)
        if binding:
            self._dispatch(binding.handler)

    def get_all_bindings(self) -> Dict[str, Tuple[str, str]]:
        """Return ``{name: (combo, description)}`` for help / debug display."""
        return {
            b.name: (b.combo, b.description)
            for b in self._bindings.values()
        }

    @property
    def is_active(self) -> bool:
        return self._active

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _dispatch(self, handler: Callable) -> None:
        """Schedule *handler* on the Tk main thread."""
        try:
            self._root.after(0, handler)
        except tk.TclError:
            pass

    @staticmethod
    def _warmup() -> None:
        """Poke the ``keyboard`` hook thread (needed for some PyInstaller builds)."""
        try:
            keyboard.start_recording()
            keyboard.stop_recording()
        except Exception:
            pass


class _Binding:
    """Internal storage for a single shortcut registration."""

    __slots__ = ("name", "combo", "handler", "description", "remover")

    def __init__(
        self,
        name: str,
        combo: str,
        handler: Callable,
        description: str,
        remover: Optional[Callable],
    ):
        self.name = name
        self.combo = combo
        self.handler = handler
        self.description = description
        self.remover = remover
