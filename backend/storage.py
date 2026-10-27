"""Local JSON persistence for saved itinerary summaries."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path

SAVED_PATH = Path(__file__).resolve().parents[1] / "data" / "saved_itineraries.json"


def _default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def load_saved(path: Path | str = SAVED_PATH) -> list[dict]:
    file = Path(path)
    if not file.exists():
        return []
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def save_itinerary(summary: dict, path: Path | str = SAVED_PATH) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    existing = load_saved(file)
    existing.insert(0, summary)
    file.write_text(json.dumps(existing[:50], indent=2, ensure_ascii=False, default=_default) + "\n", encoding="utf-8")
