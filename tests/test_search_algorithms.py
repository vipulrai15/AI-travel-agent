from backend.graph import CityGraph
from backend.search_algorithms import ALGORITHMS, search_route


def test_all_search_algorithms_find_direct_rishikesh_route(kb):
    graph = CityGraph(kb.cities, kb.routes)
    for algorithm in ALGORITHMS:
        result = search_route(graph, "Dehradun", "Rishikesh", algorithm)
        assert result.found
        assert result.nodes[0] == "Dehradun"
        assert result.nodes[-1] == "Rishikesh"
        assert result.hops >= 1


def test_bfs_returns_a_minimum_hop_route(kb):
    graph = CityGraph(kb.cities, kb.routes)
    result = search_route(graph, "Dehradun", "Delhi", "BFS")
    assert result.found
    assert result.hops == 1


def test_ucs_uses_lowest_fare_edge(kb):
    graph = CityGraph(kb.cities, kb.routes)
    result = search_route(graph, "Dehradun", "Rishikesh", "UCS")
    assert result.found
    assert result.total_cost == 150
    assert result.edges[0].mode == "bus"


def test_a_star_and_greedy_reach_a_goal(kb):
    graph = CityGraph(kb.cities, kb.routes)
    for algorithm in ("A*", "Greedy Best-First"):
        result = search_route(graph, "Dehradun", "Agra", algorithm)
        assert result.found
        assert result.nodes[-1] == "Agra"


def test_mode_filter_can_make_a_destination_unreachable(kb):
    graph = CityGraph(kb.cities, kb.routes)
    result = search_route(graph, "Dehradun", "Jaipur", "UCS", modes={"car"})
    assert not result.found
    assert "No permitted connection" in result.reason
