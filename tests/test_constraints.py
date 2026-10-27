from datetime import date, timedelta

from backend.goal_agent import TripRequest
from backend.itinerary_generator import generate_itinerary


def sample_request(**updates):
    payload = {"origin": "Dehradun", "destination_cities": ["Rishikesh"],
               "start_date": date(2026, 11, 10), "end_date": date(2026, 11, 12),
               "available_days": 3, "total_budget_inr": 25000,
               "daily_budget_limit_inr": 10000, "travellers": 1,
               "interests": ["nature"], "transport_mode": "any",
               "max_daily_travel_hours": 8, "hotel_min_inr": 500,
               "hotel_max_inr": 5000, "hotel_comfort": "budget",
               "travel_pace": "normal", "must_visit": [], "excluded_items": [],
               "dietary_preference": "vegetarian", "accessibility_needs": "",
               "return_to_origin": True,
               "priority_weights": {"cost": 25, "time": 25, "preferences": 25, "quality": 25}}
    payload.update(updates)
    return TripRequest.from_dict(payload)


def test_budget_failure_is_reported(kb):
    result = generate_itinerary(sample_request(total_budget_inr=1000), kb)
    budget = next(x for x in result["validations"] if x["constraint"] == "Budget constraint")
    assert result["success"]
    assert budget["passed"] is False
    assert budget["suggestion"]


def test_invalid_dates_are_rejected(kb):
    result = generate_itinerary(sample_request(start_date=date(2026, 11, 12),
                                               end_date=date(2026, 11, 10)), kb)
    assert not result["success"]
    assert any("End date" in error for error in result["errors"])


def test_unreachable_destination_with_car_only(kb):
    result = generate_itinerary(sample_request(destination_cities=["Jaipur"],
                                               transport_mode="car"), kb)
    assert not result["success"]
    assert any("No permitted connection" in error for error in result["errors"])


def test_invalid_days_validation(kb):
    result = generate_itinerary(sample_request(available_days=0), kb)
    assert not result["success"]
    assert any("at least 1" in error for error in result["errors"])
