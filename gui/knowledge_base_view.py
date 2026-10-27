"""Filterable, tabbed browser for the offline travel knowledge base."""
import pandas as pd
import streamlit as st

from backend.rules import KNOWN_INTERESTS


def render(kb):
    st.markdown("<div class='section-kicker'>OFFLINE INDIA DATA</div>", unsafe_allow_html=True)
    st.title("Knowledge Base")
    st.caption("Search the bundled sample cities, attractions, stays, connections, and daily travel estimates.")

    city_options = ["All cities"] + list(kb.city_by_name)
    controls = st.columns([1.1, 1.1, 1, 1], gap="medium")
    with controls[0]:
        city_filter = st.selectbox("City", city_options)
    with controls[1]:
        interest_filter = st.selectbox("Interest", ["All interests"] + KNOWN_INTERESTS)
    with controls[2]:
        mode_filter = st.selectbox("Transport mode", ["All modes", "bus", "train", "flight", "car"])
    with controls[3]:
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 0.0, 0.1)
    hotel_price_range = st.slider("Hotel price range per night (₹)", 0, 20000, (0, 10000), 500)
    query = st.text_input("Search across records", placeholder="Try a city, attraction, hotel, category, or transport mode")
    chosen_city = None if city_filter == "All cities" else city_filter
    term = query.casefold().strip()

    cities = [city for city in kb.cities if (not chosen_city or city["name"] == chosen_city)
              and (not term or term in str(city).casefold())]
    attractions = [item for item in kb.attractions
                   if (not chosen_city or item["city"] == chosen_city)
                   and item.get("rating", 0) >= min_rating
                   and (interest_filter == "All interests" or interest_filter in item.get("tags", [])
                        or interest_filter == item.get("category"))
                   and (not term or term in str(item).casefold())]
    hotels = [item for item in kb.hotels
              if (not chosen_city or item["city"] == chosen_city)
              and hotel_price_range[0] <= item["price_per_night_inr"] <= hotel_price_range[1]
              and (not term or term in str(item).casefold())]
    routes = [item for item in kb.routes
              if (not chosen_city or chosen_city in (item["source"], item["destination"]))
              and (mode_filter == "All modes" or item["mode"] == mode_filter)
              and (not term or term in str(item).casefold())]
    costs = [{"City": city["name"], "Food / person / day (₹)": city["food_cost_per_person"],
              "Local transport / person / day (₹)": city["local_transport_per_person"]}
             for city in kb.cities if not chosen_city or city["name"] == chosen_city]
    if term:
        costs = [item for item in costs if term in str(item).casefold()]

    summary = st.columns(4)
    summary[0].metric("Cities", len(cities))
    summary[1].metric("Attractions", len(attractions))
    summary[2].metric("Hotels", len(hotels))
    summary[3].metric("Transport links", len(routes))
    if not any((cities, attractions, hotels, routes, costs)):
        st.warning("No records match those filters. Try clearing the search or widening the price and rating ranges.")

    city_tab, attraction_tab, hotel_tab, route_tab, daily_tab = st.tabs(
        ["Cities", "Attractions", "Hotels", "Connections", "Daily costs"]
    )
    with city_tab:
        st.dataframe(pd.DataFrame(cities), use_container_width=True, hide_index=True)
    with attraction_tab:
        st.dataframe(pd.DataFrame(attractions), use_container_width=True, hide_index=True)
    with hotel_tab:
        st.dataframe(pd.DataFrame(hotels), use_container_width=True, hide_index=True)
    with route_tab:
        st.dataframe(pd.DataFrame(routes), use_container_width=True, hide_index=True)
    with daily_tab:
        st.dataframe(pd.DataFrame(costs), use_container_width=True, hide_index=True)
        st.caption("Food and local transport are per-person daily sample estimates.")
    st.caption(f"Bundled sample data · {len(kb.cities)} cities · {len(kb.attractions)} attractions · {len(kb.routes)} directed links · {len(kb.hotels)} hotels. Schedules and prices are not live.")
