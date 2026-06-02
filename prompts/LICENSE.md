# Premium License System
## Device-bound JWT licensing (Python client)

This document is the **source of truth** for the premium license integration in the Windows overlay app. Read it before changing licensing, build, or startup code.

---

## Overview

| Item | Detail |
|------|--------|
| Cryptography | JWT **RS256** — server signs with private key; app embeds **public key only** |
| Activation | One-time **online** `POST {activate_base_url}{activate_path}` |
| After activation | **Fully offline** verify: signature + `device_hash` + expiry / `lifetime` |
| License file | `%APPDATA%\<appdata_folder>\<license_filename>` (default `license.jwt`) |
| State file | `%APPDATA%\<appdata_folder>\license_state.json` (`last_verified_at` for clock rollback) |
| Local auth toggle | `.env` → `LICENSE_AUTH=0` (skip) or `LICENSE_AUTH=1` (require) |
| Dev bypass (legacy) | `OVERLAY_LICENSE_BYPASS=1` also skips the gate |

`appdata_folder` comes from `app_config.ini` → `[APP] appdata_folder` (default `PersonalAiAgentSurya`).

---

## Startup flow

```
main.py
  load_environment()
  load_config()          # includes [LICENSE] from bundled or %APPDATA% config.ini
  tk.Tk()
  run_license_gate()     # src/licensing/dialog.py
    → bypass env? → continue
    → verify_license_offline(load_license)? → continue
    → show License Required UI → activate → save license.jwt → continue
    → user closes window → exit app
  OverlayApp(root, config)
  root.mainloop()
```

The entire app is gated until a valid **activated** license exists (unless bypass).

---

## Config (`config.ini` → `[LICENSE]`)

URLs are **config-driven**; for local dev, **`.env` overrides `config.ini`** (loaded by `load_environment()` before the gate).

**`.env` (local Node on port 3000):**

```env
LICENSE_AUTH=0
LICENSE_NODE_PORT=3000
LICENSE_ACTIVATE_BASE_URL=http://localhost:3000
LICENSE_GET_LICENSE_URL=http://localhost:3000/request
LICENSE_ACTIVATE_PATH=/api/activate
```

| `LICENSE_AUTH` | Behavior |
|----------------|----------|
| `0` | Skip license gate (dev) |
| `1` | Require valid activated license |

**`config.ini` defaults** (same localhost URLs; used when `.env` omits URL vars):

```ini
[LICENSE]
activate_base_url = http://localhost:3000
get_license_url = http://localhost:3000/request
activate_path = /api/activate
license_filename = license.jwt
activate_timeout_seconds = 30
clock_rollback_grace_hours = 24
```

Production user override: `%APPDATA%\<appdata_folder>\config.ini`

| Key | Purpose |
|-----|---------|
| `activate_base_url` | Server base (no trailing slash required) |
| `get_license_url` | Opens in browser from “Get License / Activate” button |
| `activate_path` | Path appended to base (default `/api/activate`) |
| `license_filename` | JWT file name under AppData |
| `activate_timeout_seconds` | HTTP timeout for activation |
| `clock_rollback_grace_hours` | Tolerance if system clock moves backward |

**Effective activation URL:** `{activate_base_url}{activate_path}`  
Example: `https://yourdomain.com/api/activate`

---

## Server contract (Node backend)

### Activate (required)

`POST {activate_base_url}{activate_path}`

Request body:

```json
{
  "raw_jwt": "<admin-issued raw JWT>",
  "device_hash": "<sha256 fingerprint>",
  "device_info": { "platform": "...", "machine": "...", "node": "..." }
}
```

Success response:

```json
{ "activated_jwt": "<JWT with device_hash claim>" }
```

### JWT claims (activated token)

| Claim | Required | Notes |
|-------|----------|--------|
| `device_hash` | Yes (activated) | Must match `get_hardware_fingerprint()` |
| `exp` | Yes unless `lifetime: true` | Unix timestamp |
| `lifetime` | Optional | If `true`, ignore `exp` |
| `jti` | Optional | For future revocation API |

**Raw JWT** (before activation): no `device_hash` — user pastes in app; app calls activate endpoint.

---

## Python modules

```
src/licensing/
├── __init__.py
├── fingerprint.py    # get_hardware_fingerprint(), get_device_info()
├── public_key.py     # LICENSE_PUBLIC_KEY_PEM — replace before release
├── config.py         # get_license_settings(config)
├── manager.py        # load/save/activate/verify/is_premium
└── dialog.py         # run_license_gate(root, config)
```

### Key functions

- `get_hardware_fingerprint()` — MachineGuid + CPU + disk + OS (see `fingerprint.py`)
- `load_license(config)` / `save_license(config, token)`
- `activate_license(raw_jwt, config)` — HTTP POST, save activated JWT
- `verify_license_offline(token, config)` → `LicenseStatus`
- `is_premium(config)` — shorthand for valid offline license
- `license_bypass_enabled()` — env `OVERLAY_LICENSE_BYPASS`

---

## Public key (release build)

1. Generate RS256 key pair on the **server** only.
2. Paste the **public** PEM into `src/licensing/public_key.py` → `LICENSE_PUBLIC_KEY_PEM`.
3. Rebuild the `.exe` — the private key must never ship in the client.

Until the placeholder is replaced, offline verification fails with a clear error.

---

## Developer testing

Copy `.env.example` → `.env` in the project root (already gitignored).

```env
LICENSE_AUTH=0
LICENSE_ACTIVATE_BASE_URL=http://localhost:3000
```

Node server lives in **`license-server/`** — see `license-server/README.md`.

Start Postgres + server on port **3000**, then:

```bat
python main.py
```

To test the full gate + activation against localhost:

```env
LICENSE_AUTH=1
```

Legacy: `OVERLAY_LICENSE_BYPASS=1` also skips the gate.

---

## PyInstaller build

Dependencies (in `requirements.txt`):

```
PyJWT[crypto]>=2.8.0
cryptography>=42.0.0
requests>=2.31.0
```

Build (unchanged entry `main.py`):

```bat
build\build_exe.bat
build\build_installer.bat
```

`build/ai_overlay_agent.spec` collects `src.licensing` and hidden imports `jwt`, `cryptography`, `requests`.

Stdlib used by licensing: `winreg`, `subprocess`, `hashlib`, `platform` — no extra hidden imports.

Work path remains `%TEMP%\ai-overlay-agent-pyinstaller` (OneDrive-safe).

---

## Security notes

- Embed **public key only**; consider PyArmor / obfuscation for release builds later.
- License file is user-writable — security relies on RS256 + `device_hash`, not file hiding.
- Clock rollback: `license_state.json` stores `last_verified_at`; large backward jumps fail after grace.
- Optional future: `POST /api/verify` with `jti` for revocation (not implemented in client yet).

---

## Quality checklist

- [ ] `public_key.py` updated with production PEM before release
- [ ] `[LICENSE]` URLs point to real server in shipped `config.ini` or documented for users
- [ ] Fresh install: no license → gate UI → activate → app starts
- [ ] Second launch: offline verify only (airplane mode OK)
- [ ] Wrong machine: “bound to a different computer”
- [ ] Expired JWT: clear error in gate UI
- [ ] `LICENSE_AUTH=0` in `.env` skips gate; `LICENSE_AUTH=1` enforces it
- [ ] Installed `.exe`: hotkeys + overlay still work after licensed startup
- [ ] Rebuild after licensing code changes: `build\build_exe.bat`

---

## Related docs

- `prompts/AGENT_INSTRUCTIONS.md` — repo rules and build layout
- `prompts/PRD.md` — product features (all currently behind license gate)
- `prompts/memory.md` — conversation memory (unchanged by licensing)
