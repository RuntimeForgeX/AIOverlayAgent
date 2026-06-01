# Prompt Registry

Each file in this folder defines one **prompt profile** for the AI overlay.

## Add a new prompt (no other code changes)

1. Create a new Python file, e.g. `interview_coach.py`
2. Export a `PROMPT` dictionary:

```python
PROMPT = {
    "id": "interview_coach",
    "title": "Interview Coach",
    "description": "Short description shown in the UI.",
    "systemPrompt": """Your full system instructions here...""",
}
```

3. Restart the app (or rebuild the `.exe`). The registry picks up the file automatically.

## Rules

- `id` must be unique
- `title` appears in the header dropdown
- `description` — short summary (one line is fine)
- `systemPrompt` — **required**; full instructions sent on every API call (do not put the long prompt in `description`)

## Filenames

- Use `.py` files only; hyphens are OK (`java-dsa-agent.py`)
- Avoid quotes or spaces in filenames (e.g. rename `mysql-agent'.py` → `mysql_agent.py`)
- Default profile id is `any` (`default-agent.py`)

## Do not rename

- `registry.py`, `types.py`, `__init__.py` — infrastructure, not prompt profiles

## After changing prompts in a built `.exe`

Rebuild with `build\build_exe.bat` so new/edited files are bundled.
