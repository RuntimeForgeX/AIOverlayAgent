#!/usr/bin/env python3
"""Verify MODEL_CHOICES OpenRouter slugs against the live OpenRouter catalog."""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.models import MODEL_CHOICES  # noqa: E402


def main() -> int:
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as resp:
        live = {m["id"] for m in json.load(resp).get("data", [])}

    errors = []
    for label, provider, model_id in MODEL_CHOICES:
        if provider != "openrouter":
            continue
        if model_id not in live:
            errors.append(f"  MISSING: {label!r} -> {model_id!r}")

    if errors:
        print("OpenRouter model verification FAILED:\n" + "\n".join(errors))
        return 1

    n = sum(1 for _, p, _ in MODEL_CHOICES if p == "openrouter")
    print(f"OK — all {n} OpenRouter model IDs exist in the live catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
