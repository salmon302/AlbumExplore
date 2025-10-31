"""Favorites manager for persisting favorite album IDs and notifying views.

Stores favorites in a JSON file under the user's home directory
.albumexplore/favorites.json and provides a PyQt-friendly interface
with a signal emitted when favorites change.
"""
from pathlib import Path
import json
from typing import Set

from PyQt6.QtCore import QObject, pyqtSignal


class FavoritesManager(QObject):
    favorites_changed = pyqtSignal()

    def __init__(self, storage_path: Path = None):
        super().__init__()
        if storage_path is None:
            self.storage_dir = Path.home() / ".albumexplore"
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.storage_path = self.storage_dir / "favorites.json"
        else:
            self.storage_path = Path(storage_path)

        self._favorites: Set[str] = set()
        self._load()

    def _load(self):
        try:
            if self.storage_path.exists():
                with self.storage_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        self._favorites = set(data)
        except Exception:
            # Do not let favorites failure break the app
            self._favorites = set()

    def _save(self):
        try:
            with self.storage_path.open("w", encoding="utf-8") as fh:
                json.dump(sorted(list(self._favorites)), fh, indent=2)
        except Exception:
            # Ignore save errors; favorites are best-effort
            pass

    def is_favorite(self, album_id: str) -> bool:
        return album_id in self._favorites

    def add(self, album_id: str):
        if album_id and album_id not in self._favorites:
            self._favorites.add(album_id)
            self._save()
            self.favorites_changed.emit()

    def remove(self, album_id: str):
        if album_id and album_id in self._favorites:
            self._favorites.remove(album_id)
            self._save()
            self.favorites_changed.emit()

    def toggle(self, album_id: str) -> bool:
        """Toggle favorite state for album_id. Returns True if now favorite."""
        if self.is_favorite(album_id):
            self.remove(album_id)
            return False
        else:
            self.add(album_id)
            return True

    def all(self):
        return set(self._favorites)


# Module-level singleton
_manager: FavoritesManager | None = None


def get_favorites_manager() -> FavoritesManager:
    global _manager
    if _manager is None:
        _manager = FavoritesManager()
    return _manager
