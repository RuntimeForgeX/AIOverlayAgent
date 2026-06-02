"""Windows hardware fingerprint for device-bound licensing."""

import hashlib
import platform
import subprocess
import winreg


def get_hardware_fingerprint():
    components = []

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            mg = winreg.QueryValueEx(key, "MachineGuid")[0]
            components.append(f"mg:{mg}")
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            "wmic cpu get ProcessorId /value",
            shell=True,
            stderr=subprocess.DEVNULL,
        ).decode(errors="ignore")
        for line in out.splitlines():
            if "ProcessorId=" in line and line.split("=")[1].strip():
                components.append(f"cpu:{line.split('=')[1].strip()}")
                break
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            'wmic diskdrive where "MediaType=\'Fixed hard disk media\'" get SerialNumber /value',
            shell=True,
            stderr=subprocess.DEVNULL,
        ).decode(errors="ignore")
        for line in out.splitlines():
            if "SerialNumber=" in line and line.split("=")[1].strip():
                components.append(f"disk:{line.split('=')[1].strip()}")
                break
    except Exception:
        pass

    components.append(f"os:{platform.platform()}")
    combined = "|".join(sorted(c for c in components if c))
    return hashlib.sha256(combined.encode()).hexdigest()


def get_device_info():
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "node": platform.node(),
    }
