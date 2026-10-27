import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backend.itinerary_generator import generate_itinerary
from backend.search_algorithms import ALGORITHMS


def _route_figure(route, kb, show_connections=True):
    fig = go.Figure()
    records = {c["name"]: c for c in kb.cities}
    selected = set(route.nodes)
    # Show all known connections among route cities, plus the chosen route itself.
    seen = set()
    for edge in [r for r in kb.routes if show_connections and r["source"] in selected and r["destination"] in selected]:
        key = (edge["source"], edge["destination"], edge["mode"])
        if key in seen:
            continue
        seen.add(key)
        a, b = records[edge["source"]], records[edge["destination"]]
        fig.add_trace(go.Scattergeo(lon=[a["lon"], b["lon"]], lat=[a["lat"], b["lat"]],
                                    mode="lines", line={"width": 1, "color": "#9aa6b2"},
                                    opacity=0.45, hovertemplate=f"{edge['source']} → {edge['destination']} · {edge['mode']}<extra></extra>",
                                    showlegend=False))
    route_nodes = route.nodes
    for index in range(len(route_nodes) - 1):
        a, b = records[route_nodes[index]], records[route_nodes[index + 1]]
        edge = route.edges[index] if index < len(route.edges) else None
        label = f"Chosen: {a['name']} → {b['name']}" + (f" · {edge.mode}" if edge else "")
        fig.add_trace(go.Scattergeo(lon=[a["lon"], b["lon"]], lat=[a["lat"], b["lat"]],
                                    mode="lines", line={"width": 4, "color": "#126e82"},
                                    hovertemplate=label + "<extra></extra>", showlegend=False))
    unique = list(dict.fromkeys(route_nodes))
    fig.add_trace(go.Scattergeo(lon=[records[n]["lon"] for n in unique],
                                lat=[records[n]["lat"] for n in unique], mode="markers+text",
                                text=unique, textposition="top center", marker={"size": 10, "color": "#e07a5f"},
                                hovertemplate="%{text}<extra></extra>", showlegend=False))
    fig.update_geos(scope="asia", projection_type="natural earth", showcountries=True,
                    showland=True, landcolor="#f4f1ea", showocean=True, oceancolor="#eaf3f7",
                    showlakes=True, lakecolor="#eaf3f7")
    fig.update_layout(height=440, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def render(kb):
    st.markdown("<div class='section-kicker'>ROUTE EXPLORER</div>", unsafe_allow_html=True)
    st.title("Search & Route")
    st.caption("Explore the route graph, switch search strategies, and inspect the sample transport legs.")
    result = st.session_state.get("trip_result")
    request = st.session_state.get("trip_request")
    if not result or not result.get("success") or not result.get("route_plan"):
        st.info("Generate a trip first. Then the selected route, available connections, and search metrics will appear here.")
        if st.button("Open trip planner", type="primary"):
            st.session_state.page = "Plan a Trip"
            st.rerun()
        return
    current_algorithm = result["route_plan"].algorithm
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        algorithm = st.selectbox("Search algorithm", ALGORITHMS, index=ALGORITHMS.index(current_algorithm))
    with c2:
        if algorithm in ("BFS", "DFS"):
            st.selectbox("Route objective", ["cost"], disabled=True,
                         help="BFS minimizes hops and DFS explores deeply; neither optimizes fare or duration.")
            metric = "cost"
        else:
            metric = st.selectbox("Route objective", ["cost", "time"],
                                  index=["cost", "time"].index(result["route_plan"].metric))
    if st.button("Apply route strategy", type="primary"):
        refreshed = generate_itinerary(request, kb, algorithm, metric)
        st.session_state.trip_result = refreshed
        st.rerun()
    result = st.session_state.trip_result
    route = result["route_plan"]
    st.caption(f"Origin: **{route.origin}** · Stops: **{', '.join(route.destination_order)}** · Algorithm: **{route.algorithm}** · Objective: **minimum {route.metric}**")
    show_connections = st.toggle("Show other available connections between route cities", value=True,
                                 help="Switch off to focus the map on the selected route only.")
    st.plotly_chart(_route_figure(route, kb, show_connections), use_container_width=True,
                    config={"displayModeBar": False})
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Route legs", route.hops)
        c2.metric("Route cost / traveller", f"₹{route.total_cost:,.0f}")
        c3.metric("Time in transit", f"{route.total_time_hours:.1f} h")
        c4.metric("Search nodes", route.nodes_explored)
    st.markdown("### Follow the route")
    st.caption("Each leg uses the sample departure schedule in the bundled knowledge base.")
    rows = []
    for edge in route.edges:
        rows.append({"From": edge.source, "To": edge.destination, "Mode": edge.mode.title(),
                     "Departure": edge.departure_time, "Arrival": edge.arrival_time,
                     "Time (h)": edge.duration_hours, "Fare / traveller": f"₹{edge.fare_per_person_inr:,}",
                     "Distance (km)": edge.distance_km})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("### Explore nearby connections")
    available_modes = sorted({r["mode"] for r in kb.routes if r["source"] in set(route.nodes) or r["destination"] in set(route.nodes)})
    selected_mode = st.selectbox("Filter the connection list by mode", ["All modes"] + available_modes)
    route_city_set = set(route.nodes)
    options = [r for r in kb.routes if (r["source"] in route_city_set or r["destination"] in route_city_set)
               and (selected_mode == "All modes" or r["mode"] == selected_mode)]
    available = pd.DataFrame([{"From": r["source"], "To": r["destination"], "Mode": r["mode"].title(),
                               "Duration (h)": r["duration_hours"], "Fare / person": r["fare_per_person_inr"],
                               "Departure": r["departure_time"]} for r in options])
    st.dataframe(available, use_container_width=True, hide_index=True)
    st.markdown("### Search summary")
    st.write(f"Route sequence: **{' → '.join(route.nodes)}**")
    st.write(f"Explored **{route.nodes_explored}** nodes in **{route.runtime_ms:.2f} ms**. Itinerary status: **{'Feasible' if result.get('feasible') else 'Needs attention'}**.")
    if route.reason:
        st.caption(route.reason)
