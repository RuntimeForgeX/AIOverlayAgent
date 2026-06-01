# PyInstaller hook: bundle Gemini SDK without the huge API discovery cache.
from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    "googleapiclient.discovery_cache",
    "googleapiclient.discovery_cache.documents",
]

hiddenimports = collect_submodules(
    "google.generativeai",
    filter=lambda name: "discovery_cache" not in name,
)
