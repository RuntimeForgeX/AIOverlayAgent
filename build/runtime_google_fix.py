# Disable dynamic Google API discovery (not used by google.generativeai).
import os

os.environ.setdefault("GOOGLE_API_USE_CLIENT_DYNAMIC_DISCOVERY", "false")
