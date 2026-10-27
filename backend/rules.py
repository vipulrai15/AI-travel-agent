"""Eligibility and input rules shared by agents and the GUI."""
from __future__ import annotations

from datetime import date

KNOWN_INTERESTS = ["history", "nature", "adventure", "food", "shopping", "nightlife",
                   "religious places", "beaches", "mountains"]
TRANSPORT_MODES = ["any", "bus", "train", "flight", "car"]


def parse_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def validate_request(request, kb) -> list[str]:
    errors = []
    if request.origin not in kb.city_by_name:
        errors.append(f"Origin '{request.origin}' is not in the offline knowledge base.")
    if request.start_date and request.end_date and request.end_date < request.start_date:
        errors.append("End date must be on or after the start date.")
    if request.available_days < 1:
        errors.append("Available days must be at least 1.")
    if request.travellers < 1:
        errors.append("Number of travellers must be at least 1.")
    if request.total_budget_inr <= 0:
        errors.append("Total budget must be greater than ₹0.")
    if request.daily_budget_limit_inr <= 0:
        errors.append("Daily budget limit must be greater than ₹0.")
    if request.hotel_min_inr < 0 or request.hotel_max_inr < request.hotel_min_inr:
        errors.append("Hotel price range is invalid.")
    if request.max_daily_travel_hours <= 0:
        errors.append("Maximum daily travel time must be greater than zero.")
    unknown = [city for city in request.destination_cities if city not in kb.city_by_name]
    if unknown:
        errors.append("Unknown destination(s): " + ", ".join(unknown))
    if request.transport_mode not in TRANSPORT_MODES:
        errors.append("Choose a supported transport mode.")
    if request.destination_cities and request.origin in request.destination_cities:
        errors.append("Origin cannot also be a destination.")
    return errors


def interest_match(attraction: dict, interests: list[str]) -> int:
    normalized = {i.lower().strip() for i in interests}
    tags = {t.lower().strip() for t in attraction.get("tags", [])}
    category = attraction.get("category", "").lower()
    return len(normalized.intersection(tags | {category}))


def excluded(item_name: str, excluded_terms: list[str]) -> bool:
    name = item_name.casefold()
    return any(term.casefold() in name for term in excluded_terms)


def matching_hotels(city: str, request, kb) -> list[dict]:
    rows = [h for h in kb.hotels_for(city)
            if request.hotel_min_inr <= h["price_per_night_inr"] <= request.hotel_max_inr
            and h.get("available_rooms", 0) > 0
            and h.get("comfort_level") == request.hotel_comfort]
    if request.accessibility_needs:
        rows = [h for h in rows if h.get("accessible", False)]
    return sorted(rows, key=lambda h: (-h["rating"], h["price_per_night_inr"]))


def eligible_attractions(city: str, request, kb) -> list[dict]:
    attractions = [a for a in kb.attractions_for(city)
                   if not excluded(a["name"], request.excluded_items)
                   and (not request.accessibility_needs or a.get("accessible", False))]
    return sorted(attractions,
                  key=lambda a: (interest_match(a, request.interests), a["rating"]), reverse=True)
