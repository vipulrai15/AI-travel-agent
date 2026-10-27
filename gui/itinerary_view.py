"""Interactive itinerary, budget, and reasoning views."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from backend.storage import save_itinerary


def _saved_summary(result):
    route = result["route_plan"]
    days = []
    for day in result["days"]:
        item = {key: value for key, value in day.items() if key != "transport_edges"}
        item["transport_legs"] = [edge.__dict__ for edge in day.get("transport_edges", [])]
        days.append(item)
    request = result["request"]
    if hasattr(request, "__dataclass_fields__"):
        request = {key: getattr(request, key) for key in request.__dataclass_fields__}
        for key, value in list(request.items()):
            if hasattr(value, "isoformat"):
                request[key] = value.isoformat()
    return {
        "saved_at": datetime.now().isoformat(timespec="minutes"),
        "request": request,
        "route": {
            "algorithm": route.algorithm,
            "metric": route.metric,
            "nodes": route.nodes,
            "destination_order": route.destination_order,
            "total_cost_per_traveller": route.total_cost,
            "total_time_hours": route.total_time_hours,
            "hops": route.hops,
            "edges": [edge.__dict__ for edge in route.edges],
        },
        "days": days,
        "costs": result["costs"],
        "utility_score": result["utility_score"],
        "validations": result["validations"],
        "reasoning": result["reasoning"],
    }


def _render_day(day, total_days):
    with st.container(border=True):
        st.markdown(f"### Day {day['day_number']} · {day['city']}")
        st.caption(day["date"] + (f" · {day.get('activity_note')}" if day.get("activity_note") else ""))

        if day.get("transport_edges"):
            edge = day["transport_edges"][0]
            arrival = edge.arrival_time
            if day.get("transport_arrival_date") and day["transport_arrival_date"] != day["date"]:
                arrival += f" on {day['transport_arrival_date']}"
            st.info(
                f"Intercity leg: **{edge.source} → {edge.destination}** by {edge.mode.title()} · "
                f"depart {edge.departure_time} · arrive {arrival} · {edge.duration_hours:.1f} h · "
                f"₹{day['transport_cost_inr']:,} for the group."
            )

        if day.get("hotel"):
            hotel = day["hotel"]
            with st.container(border=True):
                left, right = st.columns([2, 1])
                left.markdown(f"**Stay · {hotel['name']}**")
                left.caption(f"{hotel['comfort_level'].title()} · " + ", ".join(hotel.get("amenities", [])))
                right.markdown(f"**₹{hotel['price_per_night_inr']:,} / night**")
                right.caption(f"{day['hotel_rooms']} room(s) · check-in {day['hotel_check_in']} · check-out {day.get('hotel_actual_check_out', day['hotel_check_out'])}")

        activities = day.get("activities", [])
        st.markdown("#### The day")
        if activities:
            for activity in activities:
                time_col, detail_col, fee_col = st.columns([.9, 2.6, .9])
                time_col.markdown(f"**{activity['start_time']}**")
                time_col.caption(activity["end_time"])
                detail_col.markdown(f"**{activity['name']}** · {activity['category'].title()}")
                detail_col.caption(
                    f"⭐ {activity['rating']:.1f} · {activity['opening_hours']} · "
                    f"{activity['duration_minutes']} min · {activity['local_transport']}"
                )
                fee_col.metric("Entry / person", f"₹{activity['entry_fee_inr']}")
        else:
            st.write("A lighter day for travel, check-in, and recovery.")

        st.markdown("#### Meal ideas")
        meal_cols = st.columns(len(day.get("meals", [])) or 1)
        for column, meal in zip(meal_cols, day.get("meals", [])):
            column.markdown(f"🍽️ {meal}")

        daily = day.get("estimated_cost_inr")
        if daily is not None:
            st.caption(f"Estimated day spend: ₹{daily:,}")


def render():
    st.markdown("<div class='section-kicker'>YOUR JOURNEY, AT A GLANCE</div>", unsafe_allow_html=True)
    st.title("Itinerary")
    result = st.session_state.get("trip_result")
    if not result or not result.get("success"):
        st.info("Generate a trip to see its detailed itinerary.")
        if st.button("Open trip planner", type="primary"):
            st.session_state.page = "Plan a Trip"
            st.rerun()
        return

    route, costs = result["route_plan"], result["costs"]
    request = result["request"]
    total = costs["estimated_total_inr"]
    budget = getattr(request, "total_budget_inr", total)
    days = result.get("days", [])

    overview = st.columns(4)
    overview[0].metric("Estimated total", f"₹{total:,}", "Includes 12% contingency")
    overview[1].metric("Route travel time", f"{route.total_time_hours:.1f} h")
    overview[2].metric("Utility score", f"{result['utility_score']:.1f}/100")
    overview[3].metric("Stops", max(0, len(route.destination_order)))
    st.markdown("**Your route** · " + " → ".join(route.nodes))
    st.progress(min(total / max(budget, 1), 1.0), text=f"₹{total:,} estimated against ₹{budget:,} budget")

    if result.get("feasible"):
        st.success("This draft passes the current constraint checks. Sample data is not a live booking confirmation.")
    else:
        st.warning("This is a draft. Review the constraint checks and suggested fixes before relying on the schedule.")

    if st.button("♡  Save this itinerary on this device", type="primary", key="save_current_itinerary"):
        try:
            save_itinerary(_saved_summary(result))
            st.success("Saved. You can reopen it from Saved Itineraries.")
        except (OSError, TypeError, ValueError) as exc:
            st.error(f"Could not save this itinerary: {exc}")

    schedule_tab, budget_tab, notes_tab = st.tabs(["Day-by-day plan", "Budget breakdown", "Why this plan fits"])
    with schedule_tab:
        if days:
            labels = [f"Day {day['day_number']} · {day['date']} · {day['city']}" for day in days]
            selected = st.selectbox("Explore a day", labels, key="itinerary_selected_day")
            index = labels.index(selected)
            day = dict(days[index])
            daily_row = next((row for row in costs.get("daily", []) if row.get("day") == day.get("day_number")), None)
            if daily_row:
                day["estimated_cost_inr"] = daily_row.get("subtotal", 0)
            _render_day(day, len(days))
            if len(days) > 1:
                st.caption(f"Day {index + 1} of {len(days)} · Use the selector above to move through the trip.")
        else:
            st.info("No scheduled days were returned for this plan.")

    with budget_tab:
        st.markdown("### Where the estimate goes")
        categories = [
            ("Intercity transport", costs.get("transport_inr", 0)),
            ("Hotels", costs.get("hotel_inr", 0)),
            ("Food", costs.get("food_inr", 0)),
            ("Local transport", costs.get("local_transport_inr", 0)),
            ("Attraction fees", costs.get("attraction_fees_inr", 0)),
            ("Contingency", costs.get("contingency_inr", 0)),
        ]
        chart_col, table_col = st.columns([1, 1.15], gap="large")
        with chart_col:
            fig = px.pie(
                names=[name for name, value in categories if value > 0],
                values=[value for _, value in categories if value > 0],
                hole=.68,
                color_discrete_sequence=["#0d7774", "#e47b62", "#80b7a5", "#e6bd85", "#547a8a", "#c8d8d2"],
            )
            fig.update_traces(textposition="inside", textinfo="percent", sort=False)
            fig.update_layout(height=340, showlegend=True, legend_title_text="", margin={"l": 0, "r": 0, "t": 10, "b": 0},
                              paper_bgcolor="rgba(0,0,0,0)", font={"color": "#355462"})
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with table_col:
            st.dataframe(pd.DataFrame(costs.get("daily", [])), use_container_width=True, hide_index=True)
            st.caption("The daily table shows estimated pre-contingency costs. The total includes the contingency shown in the chart.")
        remaining = budget - total
        if remaining >= 0:
            st.success(f"Estimated headroom: ₹{remaining:,} within your total budget.")
        else:
            st.warning(f"Estimated overage: ₹{abs(remaining):,}. Consider more budget, fewer stops, or a lower hotel range.")

    with notes_tab:
        st.markdown("### The planner’s reasoning")
        for number, reason in enumerate(result.get("reasoning", []), start=1):
            with st.container(border=True):
                st.markdown(f"**{number:02d}**  {reason}")
        if result.get("schedule_warnings"):
            st.markdown("### Scheduling notes")
            for warning in result["schedule_warnings"]:
                st.warning(warning)
