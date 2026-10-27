"""Constraint validation with user-facing explanations and repair ideas."""
from __future__ import annotations


def _result(name: str, passed: bool | None, message: str, fix: str = "") -> dict:
    return {"constraint": name, "passed": passed, "message": message, "suggestion": fix}


def validate_trip(request, route_plan, days: list[dict], costs: dict, kb) -> list[dict]:
    checks = []
    if costs:
        over = costs["estimated_total_inr"] > request.total_budget_inr
        daily_over = any(row["subtotal"] * 1.12 > request.daily_budget_limit_inr for row in costs["daily"])
        checks.append(_result("Budget constraint", not (over or daily_over),
            f"Estimated ₹{costs['estimated_total_inr']:,} including 12% contingency; daily cap is ₹{request.daily_budget_limit_inr:,.0f}.",
            "Increase the total or daily budget, choose cheaper hotels/transport, or remove a stop." if over or daily_over else ""))
    span = (request.end_date - request.start_date).days + 1 if request.start_date and request.end_date else request.available_days
    duration_ok = bool(days) and len(days) <= request.available_days and len(days) <= span
    checks.append(_result("Trip duration constraint", duration_ok,
        f"The schedule uses {len(days)} day(s); {request.available_days} day(s) are available across a {span}-day date range.",
        "Add a day, shorten the route, or align the dates with the available-day count." if not duration_ok else ""))
    checks.append(_result("Reachability constraint", route_plan.found,
        "Every planned leg has a route in the offline network." if route_plan.found else route_plan.reason,
        "Choose a connected city, allow another transport mode, or add a transfer city." if not route_plan.found else ""))

    edges = route_plan.edges
    schedule_ok = True
    travel_items = []
    for day in days:
        for edge in day.get("transport_edges", []):
            if day.get("weekday") and day["weekday"] not in edge.operating_days:
                schedule_ok = False
            travel_items.append((day["day_number"], edge))
    for (previous_day, previous), (next_day, following) in zip(travel_items, travel_items[1:]):
        elapsed = ((next_day - previous_day) * 24 * 60
                   + int(following.departure_time[:2]) * 60 + int(following.departure_time[3:]))
        elapsed -= (int(previous.departure_time[:2]) * 60 + int(previous.departure_time[3:])
                    + round(previous.duration_hours * 60))
        min_buffer = 12 * 60 if previous.duration_hours >= 6 else 2 * 60
        if elapsed < min_buffer:
            schedule_ok = False
    checks.append(_result("Transport schedule constraint", schedule_ok,
        "Each service operates on its travel day and transfer/recovery buffers are sufficient." if schedule_ok else "A service is unavailable that day or a connection leaves before arrival and the required buffer.",
        "Shift the travel date, add a transfer day, or select another mode/service." if not schedule_ok else ""))

    hotel_ok = True
    hotel_cities = []
    for day in days:
        if day["city"] == request.origin:
            continue
        if (day.get("kind") == "travel" and day.get("transport_arrival_date")
                and day["transport_arrival_date"] != day["date"]):
            continue  # The traveller is still on the overnight service on this date.
        hotel = day.get("hotel", {})
        rooms_needed = day.get("hotel_rooms", 0)
        if (not hotel or hotel.get("price_per_night_inr", 0) < request.hotel_min_inr
                or hotel.get("price_per_night_inr", 0) > request.hotel_max_inr
                or hotel.get("comfort_level") != request.hotel_comfort
                or hotel.get("available_rooms", 0) < rooms_needed):
            hotel_ok = False
        else:
            hotel_cities.append(day["city"])
    checks.append(_result("Hotel availability constraint", hotel_ok,
        "A matching hotel and enough rooms are available for every overnight city." if hotel_ok else "At least one overnight city has no hotel in the selected price/comfort range or enough rooms.",
        "Raise the hotel range, change comfort level, reduce travellers, or remove that stop." if not hotel_ok else ""))

    opening_ok = True
    for day in days:
        for activity in day.get("activities", []):
            if activity.get("closed_days") == day.get("weekday"):
                opening_ok = False
            if activity.get("start_time", "00:00") > activity.get("last_entry", "23:59"):
                opening_ok = False
    missing = [name for name in request.must_visit if not any(
        name.casefold() in activity["name"].casefold()
        for day in days for activity in day.get("activities", []))]
    opening_ok = opening_ok and not missing
    opening_msg = "All scheduled attractions fit their opening windows." if opening_ok else (
        "Could not schedule must-visit attraction(s): " + ", ".join(missing) if missing else "An attraction is closed or past last entry.")
    checks.append(_result("Attraction opening-hours constraint", opening_ok, opening_msg,
        "Choose another date, remove an unavailable must-visit, or add a day." if not opening_ok else ""))

    interest_cities = route_plan.destination_order
    interest_ok = (not request.interests or all(any(
        any(interest.casefold() in {tag.casefold() for tag in activity.get("tags", [])}
            | {activity.get("category", "").casefold()} for interest in request.interests)
        for day in days if day["city"] == city for activity in day.get("activities", []))
        for city in interest_cities))
    checks.append(_result("Interest match", interest_ok,
        "Each selected destination has at least one scheduled attraction matching your interests." if interest_ok else "At least one selected destination has no scheduled attraction matching the selected interests.",
        "Choose an interest-matched destination or add another day for a matching attraction." if not interest_ok else ""))

    overlap_ok = True
    for day in days:
        intervals = sorted((a["start_time"], a["end_time"]) for a in day.get("activities", []))
        if any(intervals[i][1] > intervals[i + 1][0] for i in range(len(intervals) - 1)):
            overlap_ok = False
    checks.append(_result("No overlapping activities", overlap_ok,
        "Scheduled attraction time blocks do not overlap." if overlap_ok else "At least two activities overlap.",
        "Reduce the daily activity count or move an activity to another day." if not overlap_ok else ""))

    daily_travel_ok = all(day.get("transport_hours", 0) <= request.max_daily_travel_hours for day in days)
    worst = max((day.get("transport_hours", 0) for day in days), default=0)
    checks.append(_result("Daily travel-time limit", daily_travel_ok,
        f"Longest scheduled travel day is {worst:.1f} hours; limit is {request.max_daily_travel_hours:.1f} hours.",
        "Choose a faster mode, increase the daily travel limit, or split the journey with an extra day." if not daily_travel_ok else ""))

    meals_ok = all(len(day.get("meal_breaks", [])) >= 3 and len(day.get("meals", [])) >= 3 for day in days)
    checks.append(_result("Meal-break constraint", meals_ok,
        "Breakfast, lunch, and dinner breaks are reserved each day." if meals_ok else "A day is missing a meal break.",
        "Add meal breaks to travel days or simplify that day's schedule." if not meals_ok else ""))

    rest_ok = True
    for i, day in enumerate(days):
        if day.get("transport_hours", 0) >= 6 and day["city"] != request.origin:
            if (day.get("rest_hours_after_travel", 0) < 12
                    or not day.get("recovery_buffer_scheduled", False)):
                rest_ok = False
    checks.append(_result("Rest after long journeys", rest_ok,
        "Long travel legs are followed by an overnight rest before planned activities." if rest_ok else "A long journey does not have enough recovery time.",
        "Add a rest day or choose a faster connection." if not rest_ok else ""))

    hotel_time_ok = True
    for i, day in enumerate(days):
        hotel = day.get("hotel", {})
        if not hotel:
            continue
        checkout = day.get("hotel_actual_check_out", hotel.get("check_out", "11:00"))
        if i + 1 < len(days) and days[i + 1].get("transport_edges"):
            edge = days[i + 1]["transport_edges"][0]
            if edge.source == day["city"] and checkout > edge.departure_time:
                hotel_time_ok = False
        arrival = day.get("transport_arrival")
        # Late arrival is supported; early arrivals can leave bags at reception until check-in.
        if arrival and arrival > "23:00":
            hotel_time_ok = False
    checks.append(_result("Hotel check-in/check-out constraint", hotel_time_ok,
        "Hotel arrival and departure times are compatible with the route; early departures use early check-out." if hotel_time_ok else "A hotel arrival or departure conflicts with its check-in/out window.",
        "Choose a later connection or confirm an early check-in/late check-out with the hotel." if not hotel_time_ok else ""))

    access_ok = True
    if request.accessibility_needs:
        access_ok = all(d.get("hotel", {}).get("accessible", False)
                        for d in days if d["city"] != request.origin and
                        not (d.get("kind") == "travel" and d.get("transport_arrival_date")
                             and d["transport_arrival_date"] != d["date"]))
        access_ok = access_ok and all(e.accessible for e in edges)
        access_ok = access_ok and all(a.get("accessible", False) for d in days for a in d.get("activities", []))
    checks.append(_result("Accessibility constraint", access_ok,
        "Hotels, selected transport, and scheduled attractions match the accessibility filter." if access_ok else "A hotel, transport leg, or attraction does not meet the requested accessibility needs.",
        "Remove inaccessible stops, select accessible transport, or broaden the accessibility details." if not access_ok else ""))

    diet_ok = True
    if request.dietary_preference == "vegan":
        diet_ok = all("vegan" in m.lower() or "no dairy" in m.lower() for d in days for m in d.get("meals", []))
    elif request.dietary_preference == "vegetarian":
        diet_ok = all(not any(term in m.lower() for term in ("meat", "chicken", "fish")) for d in days for m in d.get("meals", []))
    elif request.dietary_preference == "non-vegetarian":
        diet_ok = all(any(term in " ".join(d.get("meals", [])).lower() for term in ("meat", "eggs", "non-vegetarian")) for d in days)
    checks.append(_result("Dietary constraint", diet_ok,
        f"Meal suggestions are tailored for {request.dietary_preference}." if diet_ok else "Meal suggestions do not match the chosen dietary preference.",
        "Select no preference or customize meal suggestions before travel." if not diet_ok else ""))

    returned = bool(route_plan.nodes and route_plan.nodes[-1] == request.origin)
    return_ok = returned if request.return_to_origin else True
    checks.append(_result("Return-route constraint", return_ok,
        "The route returns to the origin." if returned else ("Return was not requested." if not request.return_to_origin else "No return leg reaches the origin."),
        "Enable a return leg, allow another transport mode, or choose a reachable destination." if not return_ok else ""))
    return checks
