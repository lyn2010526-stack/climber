"""User preference persistence.

"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UserPreference:
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


class UserPreferenceManager:
    """Persist user operation preferences.

    """

    def __init__(self, storage_path: str = "./data/user_preferences"):
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, UserPreference] = {}

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        pref = self._cache.get(user_id) or self._load(user_id)
        return pref.preferences.get(key, default)

    def set(self, user_id: str, key: str, value: Any) -> None:
        pref = self._cache.get(user_id) or self._load(user_id)
        pref.preferences[key] = value
        self._save(pref)

    def get_all(self, user_id: str) -> dict[str, Any]:
        pref = self._cache.get(user_id) or self._load(user_id)
        return dict(pref.preferences)

    def set_many(self, user_id: str, values: dict[str, Any]) -> None:
        pref = self._cache.get(user_id) or self._load(user_id)
        pref.preferences.update(values)
        self._save(pref)

    def _load(self, user_id: str) -> UserPreference:
        path = self._storage_path / f"{user_id}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pref = UserPreference(
                    user_id=data.get("user_id", user_id),
                    preferences=data.get("preferences", {}),
                    updated_at=data.get("updated_at", ""),
                )
                self._cache[user_id] = pref
                return pref
            except Exception:
                pass
        pref = UserPreference(user_id=user_id)
        self._cache[user_id] = pref
        return pref

    def _save(self, pref: UserPreference) -> None:
        pref.updated_at = __import__("datetime").datetime.utcnow().isoformat()
        path = self._storage_path / f"{pref.user_id}.json"
        data = {
            "user_id": pref.user_id,
            "preferences": pref.preferences,
            "updated_at": pref.updated_at,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


user_preference_manager = UserPreferenceManager()
