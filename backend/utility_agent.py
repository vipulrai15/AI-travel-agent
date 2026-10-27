"""Utility-based ranking of feasible travel plans."""
from __future__ import annotations

from .rules import interest_match


def score_itinerary(request, route_plan, itinerary_days: list[dict], costs: dict) -> tuple[float, dict]:
    max_cost = max(request.total_budget_inr, 1)
    cost_score = max(0.0, 100 * (1 - costs["estimated_total_inr"] / max_cost))
    available_hours = max(request.available_days * 14, 1)
    time_score = max(0.0, 100 * (1 - route_plan.total_time_hours / available_hours))
    all_activities = [a for day in itinerary_days for a in day.get("activities", [])]
    matched = sum(interest_match(a, request.interests) > 0 for a in all_activities)
    preference_score = 100 * matched / max(len(all_activities), 1)
    quality_score = (sum(a["rating"] for a in all_activities) / max(len(all_activities), 1)) / 5 * 100
    hotels = [d["hotel"] for d in itinerary_days if d.get("hotel")]
    hotel_score = sum(h.get("rating", 0) for h in hotels) / max(len(hotels), 1) / 5 * 100
    transfer_score = max(0, 100 - max(0, route_plan.hops - max(len(route_plan.destination_order), 1)) * 10)
    pace = {"relaxed": 100 if len(all_activities) <= len(itinerary_days) else 70,
            "normal": 100 if len(all_activities) <= 2 * len(itinerary_days) else 65,
            "fast": 100 if len(all_activities) <= 3 * len(itinerary_days) else 60}.get(request.travel_pace, 80)
    raw_weights = request.priority_weights or {"cost": 25, "time": 25, "preferences": 25, "quality": 25}
    weights = {"cost": raw_weights.get("cost", 25), "time": raw_weights.get("time", 25),
               "preferences": raw_weights.get("preferences", 25), "quality": raw_weights.get("quality", 25)}
    total_weight = max(sum(weights.values()), 1)
    components = {"cost": cost_score, "time": time_score,
                  "preferences": (preference_score + hotel_score + transfer_score + pace) / 4,
                  "quality": quality_score}
    score = sum(components[k] * weights[k] for k in components) / total_weight
    return round(score, 1), {k: round(v, 1) for k, v in components.items()}
