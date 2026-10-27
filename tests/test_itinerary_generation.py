from datetime import date

from backend.goal_agent import TripRequest
from backend.itinerary_generator import generate_itinerary


def test_itinerary_has_days_activities_cost_and_constraints(kb):
    request = TripRequest.from_dict({"origin": "Dehradun", "destination_cities": ["Rishikesh"],
        "start_date": date(2026, 11, 10), "end_date": date(2026, 11, 12),
        "available_days": 3, "total_budget_inr": 25000, "daily_budget_limit_inr": 10000,
        "travellers": 1, "interests": ["nature"], "transport_mode": "any",
        "max_daily_travel_hours": 8, "hotel_min_inr": 500, "hotel_max_inr": 5000,
        "hotel_comfort": "budget", "travel_pace": "normal", "must_visit": [],
        "excluded_items": [], "dietary_preference": "vegetarian", "accessibility_needs": "",
        "return_to_origin": True, "priority_weights": {"cost": 25, "time": 25, "preferences": 25, "quality": 25}})
    result = generate_itinerary(request, kb, "A*")
    assert result["success"]
    assert len(result["days"]) == 3
    assert result["costs"]["estimated_total_inr"] > result["costs"]["subtotal_inr"]
    assert any(day["activities"] for day in result["days"])
    assert result["route_plan"].nodes[-1] == "Dehradun"
