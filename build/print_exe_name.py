import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

cp = configparser.ConfigParser()
cp.read(ROOT / "app_config.ini", encoding="utf-8")
app_name = cp.get("APP", "name", fallback="AIOverlayAgent").strip()
exe_base = cp.get("BUILD", "exe_base_name", fallback=app_name).strip()
print(f"{exe_base}.exe")
