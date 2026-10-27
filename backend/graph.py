"""Weighted directed city graph supporting parallel transport modes."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt


@dataclass(frozen=True)
class Edge:
    source: str
    destination: str
    mode: str
    duration_hours: float
    fare_per_person_inr: int
    departure_time: str
    arrival_time: str
    operating_days: tuple[str, ...]
    distance_km: float
    accessible: bool = True

    @classmethod
    def from_record(cls, row: dict) -> "Edge":
        return cls(
            source=row["source"], destination=row["destination"], mode=row["mode"],
            duration_hours=float(row["duration_hours"]),
            fare_per_person_inr=int(row["fare_per_person_inr"]),
            departure_time=row["departure_time"], arrival_time=row["arrival_time"],
            operating_days=tuple(row.get("operating_days", [])),
            distance_km=float(row["distance_km"]), accessible=bool(row.get("accessible", True)),
        )


class CityGraph:
    def __init__(self, cities: list[dict], routes: list[dict]):
        self.cities = {c["name"]: c for c in cities}
        self.adjacency: dict[str, list[Edge]] = defaultdict(list)
        for row in routes:
            edge = Edge.from_record(row)
            self.adjacency[edge.source].append(edge)
        for edges in self.adjacency.values():
            edges.sort(key=lambda e: (e.destination, e.mode, e.fare_per_person_inr))

    def neighbors(self, city: str, modes: set[str] | None = None) -> list[Edge]:
        edges = self.adjacency.get(city, [])
        return [e for e in edges if not modes or e.mode in modes]

    def straight_distance_km(self, a: str, b: str) -> float:
        ca, cb = self.cities[a], self.cities[b]
        lat1, lon1, lat2, lon2 = map(radians, (ca["lat"], ca["lon"], cb["lat"], cb["lon"]))
        dlat, dlon = lat2 - lat1, lon2 - lon1
        hav = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6371.0 * 2 * asin(sqrt(hav))

    def networkx_edges(self) -> list[dict]:
        return [e.__dict__.copy() for edges in self.adjacency.values() for e in edges]
