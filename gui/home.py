"""Interactive landing dashboard and quick-start trip picker."""
import streamlit as st


def _open_page(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def render(kb):
    cities = list(kb.city_by_name)
    destinations = [city for city in cities if city != "Dehradun"]
    default_destination = "Rishikesh" if "Rishikesh" in destinations else destinations[0]

    st.markdown(
        """
        <section class="hero-panel">
          <div class="hero-kicker">A smarter way to explore India</div>
          <h1>Make a little room<br>for the <em>unexpected.</em></h1>
          <p>Shape a trip around your time, budget, and interests. Compare routes, see the trade-offs, and leave with a day-by-day plan built from the app’s offline travel data.</p>
          <div class="hero-points"><span>Route-aware planning</span><span>Budget with contingency</span><span>Transparent recommendations</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    metrics = st.columns(4)
    metrics[0].metric("Cities in the guide", len(kb.cities), "Across India")
    metrics[1].metric("Places to discover", len(kb.attractions), "Rated attractions")
    metrics[2].metric("Route connections", len(kb.routes), "Bus, train, flight, car")
    metrics[3].metric("Hotels to compare", len(kb.hotels), "Sample nightly rates")

    st.write("")
    left, right = st.columns([1.08, .92], gap="large")
    with left:
        st.markdown("<div class='section-kicker'>START WITH A SPARK</div>", unsafe_allow_html=True)
        st.subheader("Where would you like to go?")
        st.caption("Choose a destination for a quick start. You can adjust every detail in the planner.")
        destination = st.selectbox(
            "Destination idea",
            destinations,
            index=destinations.index(default_destination),
            key="home_destination",
            label_visibility="collapsed",
        )
        days = st.slider("How much time do you have?", 1, 14, 3, 1, key="home_days")
        return_to_origin = st.toggle("Plan a return to Dehradun", value=True, key="home_return")
        if st.button("Shape this trip", type="primary", use_container_width=True, key="home_start_trip"):
            st.session_state.planner_prefill = {
                "origin": "Dehradun",
                "destination_cities": [destination],
                "available_days": days,
                "return_to_origin": return_to_origin,
                "selection_mode": "Select cities",
            }
            st.session_state.planner_step = 0
            _open_page("Plan a Trip")

    with right:
        direct = [r for r in kb.routes if r["source"] == "Dehradun" and r["destination"] == destination]
        matching_attractions = sorted(kb.attractions_for(destination), key=lambda item: item.get("rating", 0), reverse=True)
        st.markdown("<div class='section-kicker'>A FIRST LOOK</div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"### Dehradun <span style='color:#0d7774'>→</span> {destination}", unsafe_allow_html=True)
            st.caption("A preview from the bundled sample data. Route and attraction choices can change with your preferences.")
            if direct:
                fastest = min(direct, key=lambda item: item["duration_hours"])
                cheapest = min(direct, key=lambda item: item["fare_per_person_inr"])
                a, b = st.columns(2)
                a.metric("Direct options", len(direct), ", ".join(sorted({r["mode"].title() for r in direct})))
                b.metric("Fastest sample leg", f"{fastest['duration_hours']:.1f} h", fastest["mode"].title())
                st.caption(f"Lowest sample fare: ₹{cheapest['fare_per_person_inr']:,} per traveller · {cheapest['mode'].title()}")
            else:
                st.info("No direct sample connection is listed. The route planner can search for an indirect connection.")
            if matching_attractions:
                st.markdown("**Top-rated places to explore**")
                for attraction in matching_attractions[:3]:
                    st.markdown(f"⭐ **{attraction['rating']:.1f}** · {attraction['name']} · {attraction['category'].title()}")
            st.caption("All fares, times, ratings, and availability shown here are illustrative, not live quotes.")

    st.write("")
    st.markdown("<div class='section-kicker'>EXPLORE THE STUDIO</div>", unsafe_allow_html=True)
    st.subheader("Your trip, from first idea to final check")
    actions = st.columns(3, gap="medium")
    action_cards = [
        ("↗", "Compare routes", "See how BFS, UCS, Greedy, and A* choose a path.", "Search & Route"),
        ("◫", "Explore the guide", "Filter the offline cities, hotels, attractions, and connections.", "Knowledge Base"),
        ("⇄", "Open algorithm lab", "Compare route cost, duration, explored nodes, and utility.", "Compare Algorithms"),
    ]
    for column, (icon, title, description, page) in zip(actions, action_cards):
        with column:
            with st.container(border=True):
                st.markdown(f"### {icon} &nbsp; {title}", unsafe_allow_html=True)
                st.write(description)
                if st.button("Explore →", key=f"home_open_{page}", use_container_width=True):
                    _open_page(page)

    saved = st.session_state.get("trip_result")
    if saved and saved.get("success"):
        st.write("")
        st.markdown("<div class='section-kicker'>PICK UP WHERE YOU LEFT OFF</div>", unsafe_allow_html=True)
        route = saved["route_plan"]
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2, 1, 1])
            col_a.markdown("### " + " → ".join(route.nodes))
            col_b.metric("Current estimate", f"₹{saved['costs']['estimated_total_inr']:,}")
            col_c.metric("Utility", f"{saved['utility_score']:.1f}/100")
            if st.button("Continue reviewing this trip", type="primary", key="home_continue_trip"):
                _open_page("Itinerary")
