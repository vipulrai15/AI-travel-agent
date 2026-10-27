"""Load and query the bundled, offline JSON knowledge base."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class KnowledgeBaseError(RuntimeError):
    """Raised when the bundled travel data is missing or malformed."""


class KnowledgeBase:
    def __init__(self, data_dir: Path | str = DATA_DIR):
        self.data_dir = Path(data_dir)
        try:
            self.cities = self._load("cities.json")
            self.attractions = self._load("attractions.json")
            self.hotels = self._load("hotels.json")
            self.routes = self._load("transport_routes.json")
            self.user_profiles = self._load("user_profiles.json")
        except (OSError, json.JSONDecodeError) as exc:
            raise KnowledgeBaseError(f"Could not load offline travel data: {exc}") from exc
        self.city_by_name = {c["name"]: c for c in self.cities}

    def _load(self, filename: str) -> Any:
        path = self.data_dir / filename
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    def attractions_for(self, city: str) -> list[dict]:
        return [a for a in self.attractions if a["city"] == city]

    def hotels_for(self, city: str) -> list[dict]:
        return [h for h in self.hotels if h["city"] == city]

    def routes_from(self, city: str) -> list[dict]:
        return [r for r in self.routes if r["source"] == city]

    def food_and_local_cost(self, city: str) -> tuple[int, int]:
        data = self.city_by_name[city]
        return data["food_cost_per_person"], data["local_transport_per_person"]


def load_knowledge_base(data_dir: Path | str = DATA_DIR) -> KnowledgeBase:
    return KnowledgeBase(data_dir)
