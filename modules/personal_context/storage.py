"""
Personal Context storage manager.

Handles file storage, index management, and settings persistence
in %APPDATA%/<AppName>/personal_context/.
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config.settings import get_user_data_root

from modules.personal_context.parser import extract_text, detect_file_type


def _context_root() -> Path:
    """Root directory for personal context data in %APPDATA%."""
    return get_user_data_root() / "personal_context"


def _files_dir() -> Path:
    return _context_root() / "files"


def _index_path() -> Path:
    return _context_root() / "index.json"


def _settings_path() -> Path:
    return _context_root() / "settings.json"


class PersonalContextManager:
    """Manages personal context documents stored in %APPDATA%."""

    def __init__(self):
        self._ensure_dirs()
        self._index: List[dict] = self._load_index()
        self._settings: dict = self._load_settings()

    # ------------------------------------------------------------------
    # Directory setup
    # ------------------------------------------------------------------

    def _ensure_dirs(self):
        _context_root().mkdir(parents=True, exist_ok=True)
        _files_dir().mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Index persistence
    # ------------------------------------------------------------------

    def _load_index(self) -> List[dict]:
        try:
            if _index_path().exists():
                return json.loads(_index_path().read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_index(self):
        try:
            _index_path().write_text(
                json.dumps(self._index, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> dict:
        defaults = {"enabled": False, "token_limit": 4000}
        try:
            if _settings_path().exists():
                data = json.loads(_settings_path().read_text(encoding="utf-8"))
                defaults.update(data)
        except Exception:
            pass
        return defaults

    def save_settings(self):
        try:
            _settings_path().write_text(
                json.dumps(self._settings, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def get_settings(self) -> dict:
        return dict(self._settings)

    def set_enabled(self, enabled: bool):
        self._settings["enabled"] = enabled
        self.save_settings()

    def is_enabled(self) -> bool:
        return self._settings.get("enabled", False)

    def get_token_limit(self) -> int:
        return self._settings.get("token_limit", 4000)

    def set_token_limit(self, limit: int):
        self._settings["token_limit"] = max(500, min(limit, 32000))
        self.save_settings()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def add_file(self, source_path: str, name: Optional[str] = None) -> dict:
        """Copy a file into storage, extract its text, and add to index."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"File not found: {source_path}")

        item_id = str(uuid.uuid4())
        file_type = detect_file_type(source_path)
        dest_name = f"{item_id}{source.suffix}"
        dest_path = _files_dir() / dest_name

        shutil.copy2(str(source), str(dest_path))

        text_content = extract_text(str(dest_path))

        item = {
            "id": item_id,
            "name": name or source.stem,
            "type": file_type,
            "original_filename": source.name,
            "size": os.path.getsize(str(dest_path)),
            "date_added": datetime.now().isoformat(),
            "file_path": str(dest_path),
            "text_content": text_content,
        }
        self._index.append(item)
        self._save_index()
        return item

    def add_text(self, text: str, name: str) -> dict:
        """Store pasted text as a .txt file and add to index."""
        item_id = str(uuid.uuid4())
        dest_path = _files_dir() / f"{item_id}.txt"

        dest_path.write_text(text, encoding="utf-8")

        item = {
            "id": item_id,
            "name": name,
            "type": "txt",
            "original_filename": f"{name}.txt",
            "size": len(text.encode("utf-8")),
            "date_added": datetime.now().isoformat(),
            "file_path": str(dest_path),
            "text_content": text,
        }
        self._index.append(item)
        self._save_index()
        return item

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all_items(self) -> List[dict]:
        return list(self._index)

    def get_item(self, item_id: str) -> Optional[dict]:
        for item in self._index:
            if item["id"] == item_id:
                return item
        return None

    def get_item_count(self) -> int:
        return len(self._index)

    # ------------------------------------------------------------------
    # Modification
    # ------------------------------------------------------------------

    def rename_item(self, item_id: str, new_name: str) -> bool:
        for item in self._index:
            if item["id"] == item_id:
                item["name"] = new_name
                self._save_index()
                return True
        return False

    def update_item_text(self, item_id: str, new_text: str) -> bool:
        """Update the text content of a context item (and the stored file)."""
        for item in self._index:
            if item["id"] == item_id:
                item["text_content"] = new_text
                # Also update the stored file if it's a txt
                if item["type"] == "txt":
                    try:
                        Path(item["file_path"]).write_text(new_text, encoding="utf-8")
                        item["size"] = len(new_text.encode("utf-8"))
                    except Exception:
                        pass
                self._save_index()
                return True
        return False

    def delete_item(self, item_id: str) -> bool:
        for i, item in enumerate(self._index):
            if item["id"] == item_id:
                # Remove the stored file
                try:
                    file_path = Path(item["file_path"])
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass
                self._index.pop(i)
                self._save_index()
                return True
        return False

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_items(self, query: str) -> List[dict]:
        """Search items by name and text content."""
        if not query:
            return self.get_all_items()
        query_lower = query.lower()
        results = []
        for item in self._index:
            name_match = query_lower in item.get("name", "").lower()
            text_match = query_lower in item.get("text_content", "").lower()
            if name_match or text_match:
                results.append(item)
        return results
