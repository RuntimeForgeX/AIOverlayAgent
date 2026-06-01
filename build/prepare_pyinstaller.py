#!/usr/bin/env python3
"""Best-effort cleanup before PyInstaller (Windows/OneDrive file locks)."""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Legacy work folder inside the repo (often locked by OneDrive or a running build).
LOCAL_WORK = PROJECT_ROOT / "pyinstaller_build"


def _rmtree(path: Path, retries: int = 5, delay: float = 0.4) -> bool:
    if not path.exists():
        return True
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError:
            if attempt + 1 < retries:
                time.sleep(delay * (attempt + 1))
        except OSError:
            if attempt + 1 < retries:
                time.sleep(delay * (attempt + 1))
    return not path.exists()


def main() -> int:
    if _rmtree(LOCAL_WORK):
        return 0
    print(
        f"Warning: could not fully remove {LOCAL_WORK}\n"
        "Close PersonalAiAgentSurya.exe if it is running, then retry.\n"
        "Build will use %TEMP% for work files instead.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
