"""Classic graph search algorithms for route planning."""
from __future__ import annotations

import heapq
import time
from dataclasses import dataclass
from itertools import count
from typing import Callable

from .graph import CityGraph, Edge

ALGORITHMS = ("BFS", "DFS", "UCS", "Greedy Best-First", "A*")


@dataclass
class SearchResult:
    algorithm: str
    found: bool
    nodes: list[str]
    edges: list[Edge]
    total_cost: float
    total_time: float
    nodes_explored: int
    runtime_ms: float
    optimality: str
    reason: str = ""

    @property
    def hops(self) -> int:
        return len(self.edges)


def _weight(edge: Edge, metric: str) -> float:
    return edge.duration_hours if metric == "time" else float(edge.fare_per_person_inr)


def _assemble(algorithm: str, start: str, goal: str, edges: list[Edge], explored: int,
              elapsed: float, optimality: str, found: bool = True, reason: str = "") -> SearchResult:
    nodes = [start]
    for edge in edges:
        nodes.append(edge.destination)
    return SearchResult(algorithm, found, nodes if found else [], edges if found else [],
                        sum(e.fare_per_person_inr for e in edges) if found else 0,
                        sum(e.duration_hours for e in edges) if found else 0,
                        explored, elapsed, optimality, reason)


def search_route(graph: CityGraph, start: str, goal: str, algorithm: str = "A*",
                 modes: set[str] | None = None, metric: str = "cost") -> SearchResult:
    """Search from start to goal; BFS/DFS optimize hops/exploration, others metric."""
    if start not in graph.cities or goal not in graph.cities:
        return SearchResult(algorithm, False, [], [], 0, 0, 0, 0, "No route", "Unknown city")
    t0 = time.perf_counter()
    if start == goal:
        return _assemble(algorithm, start, goal, [], 1, 0.0, "Optimal", True)

    if algorithm in ("BFS", "DFS"):
        frontier: list[tuple[str, list[Edge]]] = [(start, [])]
        seen = {start}
        explored = 0
        while frontier:
            node, path = frontier.pop(0) if algorithm == "BFS" else frontier.pop()
            explored += 1
            if node == goal:
                return _assemble(algorithm, start, goal, path, explored,
                                 (time.perf_counter() - t0) * 1000,
                                 "Minimum hops" if algorithm == "BFS" else "Not guaranteed")
            candidates = graph.neighbors(node, modes)
            if algorithm == "DFS":
                candidates = list(reversed(candidates))
            for edge in candidates:
                if edge.destination not in seen:
                    seen.add(edge.destination)
                    frontier.append((edge.destination, path + [edge]))
        return _assemble(algorithm, start, goal, [], explored,
                         (time.perf_counter() - t0) * 1000, "Not guaranteed", False,
                         f"No {('permitted ' if modes else '')}connection from {start} to {goal}.")

    # Cost per km lower bound makes the A* heuristic admissible for fares.
    if metric == "time":
        rate = min((e.duration_hours / max(e.distance_km, 1) for edges in graph.adjacency.values() for e in edges), default=0)
    else:
        rate = min((e.fare_per_person_inr / max(e.distance_km, 1) for edges in graph.adjacency.values() for e in edges), default=0)
    def heuristic(city: str) -> float:
        return graph.straight_distance_km(city, goal) * rate

    serial = count()
    # Entries: priority, g-cost, stable tiebreaker, node, path.
    frontier: list[tuple[float, float, int, str, list[Edge]]] = []
    h0 = heuristic(start)
    heapq.heappush(frontier, (h0 if algorithm == "Greedy Best-First" else h0 if algorithm == "A*" else 0,
                              0.0, next(serial), start, []))
    best_g = {start: 0.0}
    explored = 0
    while frontier:
        _, g, _, node, path = heapq.heappop(frontier)
        if g > best_g.get(node, float("inf")):
            continue
        explored += 1
        if node == goal:
            opt = "Optimal for selected metric" if algorithm in ("UCS", "A*") else "Not guaranteed"
            return _assemble(algorithm, start, goal, path, explored,
                             (time.perf_counter() - t0) * 1000, opt)
        for edge in graph.neighbors(node, modes):
            nxt = edge.destination
            new_g = g + _weight(edge, metric)
            if new_g < best_g.get(nxt, float("inf")):
                best_g[nxt] = new_g
                h = heuristic(nxt)
                priority = h if algorithm == "Greedy Best-First" else (new_g + h if algorithm == "A*" else new_g)
                heapq.heappush(frontier, (priority, new_g, next(serial), nxt, path + [edge]))
    return _assemble(algorithm, start, goal, [], explored,
                     (time.perf_counter() - t0) * 1000,
                     "Not guaranteed" if algorithm == "Greedy Best-First" else "Optimal for selected metric",
                     False, f"No {('permitted ' if modes else '')}connection from {start} to {goal}.")


def bfs(graph: CityGraph, start: str, goal: str, **kwargs) -> SearchResult:
    return search_route(graph, start, goal, "BFS", **kwargs)


def dfs(graph: CityGraph, start: str, goal: str, **kwargs) -> SearchResult:
    return search_route(graph, start, goal, "DFS", **kwargs)


def ucs(graph: CityGraph, start: str, goal: str, **kwargs) -> SearchResult:
    return search_route(graph, start, goal, "UCS", **kwargs)


def greedy_best_first(graph: CityGraph, start: str, goal: str, **kwargs) -> SearchResult:
    return search_route(graph, start, goal, "Greedy Best-First", **kwargs)


def a_star(graph: CityGraph, start: str, goal: str, **kwargs) -> SearchResult:
    return search_route(graph, start, goal, "A*", **kwargs)
