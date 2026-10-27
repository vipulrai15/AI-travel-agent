import pandas as pd
import plotly.express as px
import streamlit as st

from backend.itinerary_generator import generate_itinerary
from backend.search_algorithms import ALGORITHMS


def render(kb):
    st.markdown("<div class='section-kicker'>SEARCH STRATEGY LAB</div>", unsafe_allow_html=True)
    st.title("Compare Algorithms")
    st.caption("Run the same trip request through five search strategies and inspect the results side by side.")
    request = st.session_state.get("trip_request")
    if not request:
        st.info("Generate a trip first. Then each search algorithm will be run against the same origin, stops, mode, and constraints.")
        return
    st.write(f"Same request: **{request.origin}** → **{', '.join(request.destination_cities) or 'interest-selected destination'}** · {request.transport_mode} mode filter.")
    if st.button("Run all algorithms", type="primary"):
        rows = []
        for algorithm in ALGORITHMS:
            result = generate_itinerary(request, kb, algorithm)
            route = result.get("route_plan")
            rows.append({"Algorithm": algorithm,
                         "Route found": bool(route and route.found),
                         "Route": " → ".join(route.nodes) if route and route.found else "—",
                         "Total cost (₹ / person)": round(route.total_cost) if route and route.found else None,
                         "Total time (h)": round(route.total_time_hours, 1) if route and route.found else None,
                         "Hops": route.hops if route and route.found else None,
                         "Nodes explored": route.nodes_explored if route else 0,
                         "Runtime (ms)": round(route.runtime_ms, 3) if route else None,
                         "Optimality": "; ".join(sorted({leg.optimality for leg in route.legs})) if route and route.found else "No route",
                         "Utility (/100)": result.get("utility_score") if result.get("success") else None,
                         "Constraint feasible": result.get("feasible", False)})
        st.session_state.comparison_results = rows
    rows = st.session_state.get("comparison_results")
    if not rows:
        return
    frame = pd.DataFrame(rows)
    successful = frame[frame["Route found"]]
    if not successful.empty:
        utility_rows = successful.dropna(subset=["Utility (/100)"])
        fastest = successful.loc[successful["Total time (h)"].idxmin(), "Algorithm"] if successful["Total time (h)"].notna().any() else "—"
        cheapest = successful.loc[successful["Total cost (₹ / person)"].idxmin(), "Algorithm"] if successful["Total cost (₹ / person)"].notna().any() else "—"
        highest = utility_rows.loc[utility_rows["Utility (/100)"].idxmax(), "Algorithm"] if not utility_rows.empty else "—"
        cards = st.columns(3)
        cards[0].metric("Lowest sample fare", cheapest)
        cards[1].metric("Shortest travel time", fastest)
        cards[2].metric("Highest utility", highest)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    st.markdown("### Compare a dimension")
    dimension = st.selectbox("Chart metric", ["Utility (/100)", "Total cost (₹ / person)", "Total time (h)", "Nodes explored"])
    usable = frame.dropna(subset=[dimension])
    if not usable.empty:
        fig = px.bar(usable, x="Algorithm", y=dimension, color="Algorithm",
                     color_discrete_sequence=["#0d7774", "#e47b62", "#80b7a5", "#e6bd85", "#355462"])
        fig.update_layout(showlegend=False, height=350, margin={"t": 20, "b": 10},
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No successful routes have this metric to chart.")
    st.caption("BFS minimizes hops; UCS minimizes fare; A* uses an admissible straight-line fare heuristic. Greedy and DFS are not guaranteed to return an optimal route. Runtime is local and can vary between runs.")
