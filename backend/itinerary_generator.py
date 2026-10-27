"""Orchestrate route search, scheduling, cost, utility, and validation."""
from __future__ import annotations

from .cost_calculator import calculate_costs
from .goal_agent import TripRequest, plan_route
from .rules import validate_request
from .scheduler import schedule_trip
from .utility_agent import score_itinerary
from .validators import validate_trip
from .search_algorithms import ALGORITHMS


def generate_itinerary(request: TripRequest | dict, kb, algorithm: str = "A*", metric: str = "cost") -> dict:
    if isinstance(request, dict):
        request = TripRequest.from_dict(request)
    errors = validate_request(request, kb)
    if errors:
        return {"success": False, "errors": errors, "request": request, "route_plan": None,
                "days": [], "costs": {}, "validations": [], "reasoning": []}
    route = plan_route(request, kb, algorithm, metric)
    if not route.found:
        return {"success": False, "errors": [route.reason], "request": request, "route_plan": route,
                "days": [], "costs": {}, "validations": [], "reasoning": [route.reason]}
    days, schedule_warnings = schedule_trip(request, route, kb)
    costs = calculate_costs(request, route, days, kb)
    validations = validate_trip(request, route, days, costs, kb)
    utility, components = score_itinerary(request, route, days, costs)
    destinations = route.destination_order
    reasoning = [f"Route chosen by {algorithm} for minimum {metric}: " + " → ".join(route.nodes) +
                 f" ({route.hops} leg(s), {route.total_time_hours:.1f} travel hours)."]
    for city in destinations:
        if request.interests:
            matched = [a["name"] for a in kb.attractions_for(city)
                       if any(i.casefold() in {tag.casefold() for tag in a.get("tags", [])}
                              | {a.get("category", "").casefold()} for i in request.interests)]
            if matched:
                reasoning.append(f"Included {city} because its attractions match {', '.join(request.interests)}; matches include {', '.join(matched[:3])}.")
        hotels = [d["hotel"] for d in days if d["city"] == city and d.get("hotel")]
        if hotels:
            hotel = hotels[0]
            reasoning.append(f"{hotel['name']} in {city} matches the {request.hotel_comfort} level and ₹{hotel['price_per_night_inr']:,}/night range.")
        attractions = [a for d in days if d["city"] == city for a in d.get("activities", [])]
        if attractions:
            names = ", ".join(a["name"] for a in attractions)
            reasoning.append(f"{city} activities were picked for interest fit and ratings: {names}.")
    reasoning.append(f"Estimated total includes a 12% contingency: ₹{costs['estimated_total_inr']:,}.")
    reasoning.append(f"Utility score {utility:.1f}/100 balances cost, time, preference fit, and attraction quality using your sliders.")
    if route.reason:
        reasoning.append(route.reason)
    if schedule_warnings:
        reasoning.extend(schedule_warnings)
    passed = all(item["passed"] is not False for item in validations)
    return {"success": True, "feasible": passed, "errors": [], "request": request,
            "route_plan": route, "days": days, "costs": costs, "validations": validations,
            "utility_score": utility, "utility_components": components,
            "reasoning": reasoning, "schedule_warnings": schedule_warnings}


def generate_best_itinerary(request: TripRequest | dict, kb) -> dict:
    """Compare route-search outputs and select the highest-utility feasible plan."""
    if isinstance(request, dict):
        request = TripRequest.from_dict(request)
    candidates = [generate_itinerary(request, kb, algorithm) for algorithm in ALGORITHMS]
    candidates.extend(generate_itinerary(request, kb, algorithm, metric="time")
                      for algorithm in ("UCS", "A*"))
    valid = [candidate for candidate in candidates if candidate.get("success")]
    if not valid:
        return candidates[-1]
    feasible = [candidate for candidate in valid if candidate.get("feasible")]
    pool = feasible or valid
    tie_break_rank = {"A*": 5, "UCS": 4, "BFS": 3, "Greedy Best-First": 2, "DFS": 1}
    weights = request.priority_weights or {}
    preferred_metric = "time" if weights.get("time", 0) > weights.get("cost", 0) else "cost"
    chosen = max(pool, key=lambda item: (item.get("utility_score", 0),
                                         -item["costs"].get("estimated_total_inr", 0),
                                         -item["route_plan"].total_time_hours,
                                         item["route_plan"].metric == preferred_metric,
                                         tie_break_rank.get(item["route_plan"].algorithm, 0)))
    chosen["algorithm_comparison"] = [{"algorithm": c.get("route_plan").algorithm if c.get("route_plan") else "—",
                                       "found": bool(c.get("route_plan") and c["route_plan"].found),
                                       "feasible": c.get("feasible", False),
                                       "utility_score": c.get("utility_score")}
                                      for c in candidates]
    chosen["reasoning"].append(
        f"The utility agent compared {len(candidates)} search results and selected {chosen['route_plan'].algorithm} optimizing {chosen['route_plan'].metric}, with the highest utility among {('feasible plans' if feasible else 'generated plans')}.")
    return chosen
