"""Transparent INR cost estimates and contingency handling."""

CONTINGENCY_RATE = 0.12


def calculate_costs(request, route_plan, itinerary_days: list[dict], kb) -> dict:
    transport = sum(edge.fare_per_person_inr for edge in route_plan.edges) * request.travellers
    hotel = sum(day.get("hotel", {}).get("price_per_night_inr", 0) *
                day.get("hotel_rooms", 1) for day in itinerary_days)
    food = local = attraction_fees = 0
    daily = []
    for day in itinerary_days:
        city = day["city"]
        if city in kb.city_by_name and city != request.origin:
            food_pp, local_pp = kb.food_and_local_cost(city)
            day_food, day_local = food_pp * request.travellers, local_pp * request.travellers
        else:
            day_food = day_local = 0
        day_fees = sum(a["entry_fee_inr"] for a in day.get("activities", [])) * request.travellers
        food += day_food
        local += day_local
        attraction_fees += day_fees
        daily.append({"day": day["day_number"], "city": city, "transport": day.get("transport_cost_inr", 0),
                      "hotel": day.get("hotel", {}).get("price_per_night_inr", 0) * day.get("hotel_rooms", 1),
                      "food": day_food, "local_transport": day_local, "attractions": day_fees,
                      "subtotal": day.get("transport_cost_inr", 0) +
                                  day.get("hotel", {}).get("price_per_night_inr", 0) * day.get("hotel_rooms", 1) +
                                  day_food + day_local + day_fees})
    subtotal = transport + hotel + food + local + attraction_fees
    return {"transport_inr": transport, "hotel_inr": hotel, "food_inr": food,
            "local_transport_inr": local, "attraction_fees_inr": attraction_fees,
            "subtotal_inr": subtotal, "contingency_rate": CONTINGENCY_RATE,
            "contingency_inr": round(subtotal * CONTINGENCY_RATE),
            "estimated_total_inr": round(subtotal * (1 + CONTINGENCY_RATE)), "daily": daily}
