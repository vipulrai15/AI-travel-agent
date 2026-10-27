"""Build deterministic day-by-day schedules from a route plan."""
from __future__ import annotations

from datetime import date, timedelta
from math import ceil

from .rules import eligible_attractions, interest_match, matching_hotels

PACE_ACTIVITY_LIMIT = {"relaxed": 1, "normal": 2, "fast": 3}
SLOTS = [("Morning", "09:00", "12:00"), ("Afternoon", "13:30", "17:00"),
         ("Evening", "18:00", "21:00")]


def _minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def _opening_fit(attraction: dict, day_date, start: str, end: str) -> bool:
    if attraction.get("closed_days", "None") == day_date.strftime("%A"):
        return False
    opening = attraction.get("opening_hours", "00:00-23:59")
    open_start, open_end = opening.split("-")
    last_entry = attraction.get("last_entry", open_end)
    start_min = _minutes(start)
    finish_min = start_min + attraction["duration_minutes"]
    return (start_min >= _minutes(open_start) and finish_min <= _minutes(open_end)
            and start_min <= _minutes(last_entry))


def _pick_activities(city: str, day_date, request, kb) -> list[dict]:
    pool = eligible_attractions(city, request, kb)
    forced = [a for a in pool if any(term.casefold() in a["name"].casefold() for term in request.must_visit)]
    rest = [a for a in pool if a not in forced]
    rest.sort(key=lambda a: (interest_match(a, request.interests), a["rating"]), reverse=True)
    max_items = max(PACE_ACTIVITY_LIMIT.get(request.travel_pace, 2), len(forced))
    chosen = (forced + rest)[:max_items]
    results = []
    slot_index = 0
    for attraction in chosen:
        scheduled = None
        for idx in range(slot_index, len(SLOTS)):
            label, start, end = SLOTS[idx]
            if attraction["duration_minutes"] <= (_minutes(end) - _minutes(start)) and _opening_fit(attraction, day_date, start, end):
                scheduled = {**attraction, "slot": label, "start_time": start,
                             "end_time": f"{(_minutes(start) + attraction['duration_minutes']) // 60:02d}:{(_minutes(start) + attraction['duration_minutes']) % 60:02d}"}
                slot_index = idx + 1
                break
        if scheduled:
            results.append(scheduled)
    return results


def _steps_for_route(route_plan) -> list[dict]:
    steps = []
    for leg_index, leg in enumerate(route_plan.legs):
        target = leg.nodes[-1] if leg.nodes else route_plan.origin
        for edge_index, edge in enumerate(leg.edges):
            arrival_absolute = _minutes(edge.departure_time) + round(edge.duration_hours * 60)
            arrival_offset = arrival_absolute // (24 * 60)
            next_edge = leg.edges[edge_index + 1] if edge_index + 1 < len(leg.edges) else None
            travel_step = {"kind": "travel", "city": edge.destination, "edge": edge,
                           "transport_cost_inr": edge.fare_per_person_inr,
                           "arrival_day_offset": arrival_offset,
                           "leg_target": target, "leg_index": leg_index,
                           "recovery_buffer_scheduled": True}
            steps.append(travel_step)
            if next_edge or target != route_plan.origin:
                next_departure = _minutes(next_edge.departure_time) if next_edge else 9 * 60
                required_gap = 12 * 60 if edge.duration_hours >= 6 else 2 * 60
                gap = 24 * 60 + next_departure - arrival_absolute
                while gap < required_gap:
                    steps.append({"kind": "rest", "city": edge.destination,
                                  "transport_cost_inr": 0, "leg_target": target,
                                  "leg_index": leg_index,
                                  "activity_note": "Rest and allow a full recovery/connection buffer."})
                    gap += 24 * 60
                travel_step["recovery_buffer_scheduled"] = gap >= required_gap
        if target != route_plan.origin:
            steps.append({"kind": "stay", "city": target, "transport_cost_inr": 0,
                          "leg_target": target, "leg_index": leg_index})
    if route_plan.edges and route_plan.edges[-1].destination == route_plan.origin:
        final_edge = route_plan.edges[-1]
        final_arrival = _minutes(final_edge.departure_time) + round(final_edge.duration_hours * 60)
        if final_arrival // (24 * 60) > 0:
            steps.append({"kind": "arrival", "city": route_plan.origin,
                          "transport_cost_inr": 0, "leg_target": route_plan.origin,
                          "leg_index": len(route_plan.legs) - 1,
                          "activity_note": "Arrive back at the origin on the following date."})
    return steps


def schedule_trip(request, route_plan, kb) -> tuple[list[dict], list[str]]:
    if not route_plan.found:
        return [], [route_plan.reason]
    steps = _steps_for_route(route_plan)
    # Add spare days as rest/exploration days at the final destination before a return leg.
    used = len(steps)
    spare = max(0, request.available_days - used)
    if spare:
        insertion = len(steps)
        if request.return_to_origin:
            # Add spare nights at the final destination before starting the return leg.
            return_leg_index = len(route_plan.legs) - 1
            insertion = next((idx for idx, step in enumerate(steps)
                              if step.get("leg_index") == return_leg_index), len(steps))
        city = route_plan.destination_order[-1] if route_plan.destination_order else request.origin
        extra = [{"kind": "stay", "city": city, "transport_cost_inr": 0,
                  "leg_target": city, "leg_index": -1} for _ in range(spare)]
        steps[insertion:insertion] = extra
    warnings = []
    if len(steps) > request.available_days:
        warnings.append(f"The route needs {len(steps)} calendar days, but only {request.available_days} are available.")
    if len(steps) > 60:
        return [], ["The route is too long to schedule in a single trip. Remove a stop or choose a closer destination."]

    hotel_by_city = {}
    for step in steps:
        city = step["city"]
        if city != request.origin and city not in hotel_by_city:
            options = matching_hotels(city, request, kb)
            if options:
                hotel_by_city[city] = options[0]

    days = []
    start = request.start_date
    for idx, step in enumerate(steps):
        current_date = (start + timedelta(days=idx)) if start else None
        city, kind = step["city"], step["kind"]
        activities = _pick_activities(city, current_date, request, kb) if kind == "stay" and current_date else []
        if kind == "stay" and not current_date:
            activities = _pick_activities(city, date.today(), request, kb)
        hotel = hotel_by_city.get(city)
        if kind == "travel" and step.get("arrival_day_offset", 0) > 0:
            hotel = None  # Overnight service arrives the following calendar day.
        rooms = ceil(request.travellers / hotel["max_guests_per_room"]) if hotel else 0
        edge = step.get("edge")
        if kind == "travel" and edge:
            departure, arrival = edge.departure_time, edge.arrival_time
            activity_note = ("Overnight travel; hotel check-in is scheduled for the arrival date."
                             if step.get("arrival_day_offset", 0) > 0
                             else "Travel and check in; keep the remaining time for rest.")
            travel_edges = [edge]
            travel_hours = edge.duration_hours
            arrival_date = (current_date + timedelta(days=step.get("arrival_day_offset", 0))) if current_date else None
        else:
            departure = arrival = None
            activity_note = step.get("activity_note", "Rest day for recovery and local buffer." if kind == "rest" else "")
            travel_edges = []
            travel_hours = 0.0
            arrival_date = None
        meal_templates = {
            "vegetarian": ["Breakfast: poha/idli with tea", "Lunch: local thali with dal and seasonal vegetables", "Dinner: paneer or lentil curry with rice/roti"],
            "vegan": ["Breakfast: fruit, poha or vegan upma", "Lunch: vegan dal, rice and vegetable thali (confirm no dairy/ghee)", "Dinner: chana/vegetable curry with rice (confirm no dairy)"],
            "non-vegetarian": ["Breakfast: eggs and toast or local breakfast", "Lunch: regional meal with a meat option", "Dinner: local non-vegetarian speciality"],
            "no preference": ["Breakfast: local breakfast", "Lunch: regional thali", "Dinner: locally popular meal"]}
        meals = meal_templates.get(request.dietary_preference, meal_templates["no preference"])
        daily_activities = [{**a, "local_transport": "Auto/taxi or walk; allow 20–30 minutes between stops."} for a in activities]
        days.append({"day_number": idx + 1, "date": current_date.isoformat() if current_date else "Date not set",
                     "weekday": current_date.strftime("%A") if current_date else "",
                     "city": city, "kind": kind, "hotel": hotel or {}, "hotel_rooms": rooms,
                     "hotel_check_in": (hotel.get("check_in", "14:00") if hotel and
                                         (idx == 0 or days[-1]["city"] != city or not days[-1].get("hotel"))
                                         else "Already checked in") if hotel else "—",
                     "hotel_check_out": hotel.get("check_out", "11:00") if hotel else "—",
                     "transport_edges": travel_edges, "transport_departure": departure,
                     "transport_arrival": arrival,
                     "transport_arrival_date": arrival_date.isoformat() if arrival_date else None,
                     "transport_hours": travel_hours,
                     "transport_cost_inr": step.get("transport_cost_inr", 0) * request.travellers,
                     "activities": daily_activities, "activity_note": activity_note,
                     "meals": meals,
                     "meal_breaks": [{"name": "Breakfast", "time": "08:00"},
                                     {"name": "Lunch", "time": "12:30"},
                                     {"name": "Dinner", "time": "19:30"}],
                     "rest_hours_after_travel": 12 if travel_hours >= 6 else 8,
                     "recovery_buffer_scheduled": step.get("recovery_buffer_scheduled", True),
                     "step_leg_index": step.get("leg_index", -1)})
    # Hotel check-out is tied to the next service's departure, with a 30-minute buffer.
    for idx, day in enumerate(days):
        hotel = day.get("hotel")
        if not hotel:
            continue
        checkout = "Continues"
        if idx + 1 < len(days) and days[idx + 1].get("transport_edges"):
            next_edge = days[idx + 1]["transport_edges"][0]
            if next_edge.source == day["city"]:
                dep = _minutes(next_edge.departure_time) - 30
                if dep >= 0:
                    checkout = f"{dep // 60:02d}:{dep % 60:02d}"
                else:
                    checkout = "23:30"
        elif idx == len(days) - 1:
            checkout = hotel.get("check_out", "11:00")
        day["hotel_actual_check_out"] = checkout
    if not any(day.get("hotel") for day in days if day["city"] != request.origin):
        warnings.append("No hotel matched the selected cities, comfort level, and nightly price range.")
    missing_must = [name for name in request.must_visit
                    if not any(name.casefold() in a["name"].casefold() for d in days for a in d["activities"])]
    if missing_must:
        warnings.append("Could not schedule must-visit attraction(s): " + ", ".join(missing_must))
    return days, warnings
