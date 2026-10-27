import streamlit as st

from backend.storage import load_saved


def render():
    st.markdown("<div class='section-kicker'>YOUR LOCAL TRIP LIBRARY</div>", unsafe_allow_html=True)
    st.title("Saved Itineraries")
    items = load_saved()
    if not items:
        st.info("No saved itineraries yet. Generate a trip, open Itinerary, and choose ‘Save this itinerary locally’.")
        return
    st.caption(f"{len(items)} saved trip(s), stored in this project folder on this device.")
    query = st.text_input("Find a saved trip", placeholder="Search by city, date, or route")
    term = query.casefold().strip()
    filtered = [item for item in items
                if not term or term in str(item.get("request", {})).casefold()
                or term in str(item.get("route", {}).get("nodes", [])).casefold()]
    if not filtered:
        st.info("No saved trips match that search.")
        return
    st.markdown(f"**Showing {len(filtered)} of {len(items)} trips**")
    for idx, item in enumerate(filtered):
        request = item.get("request", {})
        route = item.get("route", {})
        title = f"{request.get('start_date', 'Trip')} · {' → '.join(route.get('nodes', []))} · ₹{item.get('costs', {}).get('estimated_total_inr', 0):,}"
        with st.expander(title, expanded=idx == 0):
            st.write(f"Saved: {item.get('saved_at', 'unknown')} · Algorithm: {route.get('algorithm', '—')} ({route.get('metric', 'cost')}) · Utility: {item.get('utility_score', 0):.1f}/100")
            st.write(f"Interests: {', '.join(request.get('interests', [])) or 'not specified'} · Dietary preference: {request.get('dietary_preference', '—')}")
            st.write(f"Estimated total includes contingency: ₹{item.get('costs', {}).get('estimated_total_inr', 0):,}")
            for day in item.get("days", []):
                st.markdown(f"**Day {day.get('day_number')} · {day.get('date')} · {day.get('city')}**")
                legs = day.get("transport_legs", [])
                if legs:
                    leg = legs[0]
                    st.caption(f"{leg['source']} → {leg['destination']} by {leg['mode']} · {leg['duration_hours']} h · depart {leg['departure_time']}")
                hotel = day.get("hotel", {})
                if hotel:
                    st.caption(f"Hotel: {hotel.get('name')} · ₹{hotel.get('price_per_night_inr'):,}/night")
                names = [a.get("name") for a in day.get("activities", [])]
                if names:
                    st.write("Activities: " + ", ".join(names))
