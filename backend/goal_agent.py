"""Goal-based destination and route planning agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .graph import CityGraph, Edge
from .rules import eligible_attractions, interest_match, matching_hotels
from .search_algorithms import SearchResult, search_route


@dataclass
class TripRequest:
    origin: str = "Dehradun"
    destination_cities: list[str] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    available_days: int = 3
    total_budget_inr: float = 25000
    daily_budget_limit_inr: float = 10000
    travellers: int = 1
    interests: list[str] = field(default_factory=list)
    transport_mode: str = "any"
    max_daily_travel_hours: float = 8
    hotel_min_inr: int = 500
    hotel_max_inr: int = 5000
    hotel_comfort: str = "budget"
    travel_pace: str = "normal"
    must_visit: list[str] = field(default_factory=list)
    excluded_items: list[str] = field(default_factory=list)
    dietary_preference: str = "no preference"
    accessibility_needs: str = ""
    return_to_origin: bool = True
    priority_weights: dict = field(default_factory=lambda: {"cost": 25, "time": 25, "preferences": 25, "quality": 25})

    @classmethod
    def from_dict(cls, data: dict) -> "TripRequest":
        values = dict(data)
        for key in ("destination_cities", "interests", "must_visit", "excluded_items"):
            values[key] = list(values.get(key, []))
        for key in ("start_date", "end_date"):
            value = values.get(key)
            if isinstance(value, str) and value:
                values[key] = date.fromisoformat(value)
        allowed = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in values.items() if k in allowed})


@dataclass
class RoutePlan:
    algorithm: str
    found: bool
    origin: str
    destination_order: list[str]
    legs: list[SearchResult]
    edges: list[Edge]
    nodes: list[str]
    total_cost: float
    total_time_hours: float
    nodes_explored: int
    runtime_ms: float
    reason: str = ""
    metric: str = "cost"

    @property
    def hops(self) -> int:
        return len(self.edges)


def choose_destinations(request: TripRequest, kb, graph: CityGraph) -> tuple[list[str], list[str]]:
    """Resolve explicit cities or rank up to two interest-matching cities."""
    reasons = []
    if request.destination_cities:
        destinations = list(dict.fromkeys(request.destination_cities))
    else:
        candidates = []
        for city in kb.city_by_name:
            if city == request.origin:
                continue
            attractions = eligible_attractions(city, request, kb)
            matching = [a for a in attractions if interest_match(a, request.interests)]
            if not matching or not matching_hotels(city, request, kb):
                continue
            modes = None if request.transport_mode == "any" else {request.transport_mode}
            route = search_route(graph, request.origin, city, "UCS", modes=modes)
            if not route.found:
                continue
            score = (sum(interest_match(a, request.interests) for a in matching) * 2 +
                     sum(a["rating"] for a in matching[:3]) - route.total_cost / 10000)
            candidates.append((score, city))
        candidates.sort(reverse=True)
        max_destinations = 2 if request.available_days >= 6 else 1
        destinations = [city for _, city in candidates[:max_destinations]]
        if destinations:
            reasons.append("Selected " + ", ".join(destinations) + " from the offline city and attraction matches for your interests.")
    # Must-visit names add their city where it is not already included.
    for must in request.must_visit:
        match = next((a for a in kb.attractions if must.casefold() in a["name"].casefold()), None)
        if match and match["city"] != request.origin and match["city"] not in destinations:
            destinations.append(match["city"])
            reasons.append(f"Added {match['city']} because it contains the must-visit attraction '{match['name']}'.")
    excluded = [x.casefold() for x in request.excluded_items]
    destinations = [d for d in destinations if d.casefold() not in excluded]
    eligible = []
    for city in destinations:
        attractions = eligible_attractions(city, request, kb)
        has_interest_match = not request.interests or any(interest_match(a, request.interests) for a in attractions)
        has_required_attraction = any(
            term.casefold() in a["name"].casefold() for term in request.must_visit for a in kb.attractions_for(city))
        if not has_interest_match and not has_required_attraction:
            reasons.append(f"Rejected {city}: no available attraction matches the selected interests. Add a matching interest or choose another city.")
            continue
        if not matching_hotels(city, request, kb):
            reasons.append(f"Rejected {city}: no hotel matches the selected comfort and nightly price range. Raise the nightly range or change hotel comfort.")
            continue
        eligible.append(city)
    destinations = eligible
    if request.destination_cities:
        for city in destinations:
            reasons.append(f"Included {city} because you selected it and it passed the attraction and hotel filters.")
    if not destinations:
        reasons.append("No eligible destination matched the request; select a city or broaden interests/hotel range.")
    return destinations, reasons


def plan_route(request: TripRequest, kb, algorithm: str = "A*", metric: str = "cost") -> RoutePlan:
    graph = CityGraph(kb.cities, kb.routes)
    destinations, reasons = choose_destinations(request, kb, graph)
    modes = None if request.transport_mode == "any" else {request.transport_mode}
    stop_sequence = destinations + ([request.origin] if request.return_to_origin and destinations else [])
    current = request.origin
    all_legs, all_edges, nodes = [], [], [request.origin]
    cost = hours = runtime = 0.0
    explored = 0
    for target in stop_sequence:
        leg = search_route(graph, current, target, algorithm, modes=modes, metric=metric)
        all_legs.append(leg)
        runtime += leg.runtime_ms
        explored += leg.nodes_explored
        if not leg.found:
            reason = leg.reason or f"No route from {current} to {target}."
            return RoutePlan(algorithm, False, request.origin, destinations, all_legs,
                             all_edges, nodes, cost, hours, explored, runtime,
                             "; ".join(reasons + [reason]), metric)
        all_edges.extend(leg.edges)
        for node in leg.nodes[1:]:
            nodes.append(node)
        cost += leg.total_cost
        hours += leg.total_time
        current = target
    if not stop_sequence:
        return RoutePlan(algorithm, False, request.origin, [], [], [], [request.origin], 0, 0, 0, 0,
                         "; ".join(reasons), metric)
    return RoutePlan(algorithm, True, request.origin, destinations, all_legs, all_edges,
                     nodes, cost, hours, explored, runtime, "; ".join(reasons), metric)
