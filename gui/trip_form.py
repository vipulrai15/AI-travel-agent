"""Guided, four-step trip request wizard."""
from datetime import date, timedelta

import streamlit as st

from backend.goal_agent import TripRequest
from backend.itinerary_generator import generate_best_itinerary
from backend.rules import KNOWN_INTERESTS


STEPS = ["Route & dates", "Budget & stay", "Travel style", "Priorities"]
STEP_KEYS = {
    0: ["planner_origin", "planner_selection_mode", "planner_destinations", "planner_start_date",
        "planner_end_date", "planner_available_days", "planner_return_to_origin", "planner_transport_mode"],
    1: ["planner_total_budget", "planner_daily_budget", "planner_travellers", "planner_max_daily_travel",
        "planner_hotel_min", "planner_hotel_max", "planner_hotel_comfort"],
    2: ["planner_interests", "planner_pace", "planner_must_visit", "planner_excluded",
        "planner_dietary", "planner_accessibility"],
    3: ["planner_weight_cost", "planner_weight_time", "planner_weight_preferences", "planner_weight_quality"],
}


def _seed(key, value):
    if key not in st.session_state:
        answers = st.session_state.get("_planner_answers", {})
        st.session_state[key] = answers.get(key, value)


def _save_step_answers(step):
    answers = st.session_state.setdefault("_planner_answers", {})
    for key in STEP_KEYS[step]:
        if key in st.session_state:
            value = st.session_state[key]
            answers[key] = list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value


def _load_home_prefill():
    prefill = st.session_state.pop("planner_prefill", None)
    if not prefill:
        return
    key_map = {
        "origin": "planner_origin",
        "destination_cities": "planner_destinations",
        "available_days": "planner_available_days",
        "return_to_origin": "planner_return_to_origin",
        "selection_mode": "planner_selection_mode",
    }
    for source, target in key_map.items():
        if source in prefill:
            st.session_state[target] = prefill[source]
            st.session_state.setdefault("_planner_answers", {})[target] = prefill[source]


def _request_from_state():
    selection_mode = st.session_state.planner_selection_mode
    selected_cities = st.session_state.planner_destinations if selection_mode == "Select cities" else []
    return TripRequest.from_dict({
        "origin": st.session_state.planner_origin,
        "destination_cities": selected_cities,
        "start_date": st.session_state.planner_start_date,
        "end_date": st.session_state.planner_end_date,
        "available_days": int(st.session_state.planner_available_days),
        "total_budget_inr": float(st.session_state.planner_total_budget),
        "daily_budget_limit_inr": float(st.session_state.planner_daily_budget),
        "travellers": int(st.session_state.planner_travellers),
        "interests": st.session_state.planner_interests,
        "transport_mode": st.session_state.planner_transport_mode,
        "max_daily_travel_hours": float(st.session_state.planner_max_daily_travel),
        "hotel_min_inr": int(st.session_state.planner_hotel_min),
        "hotel_max_inr": int(st.session_state.planner_hotel_max),
        "hotel_comfort": st.session_state.planner_hotel_comfort,
        "travel_pace": st.session_state.planner_pace,
        "must_visit": [item.strip() for item in st.session_state.planner_must_visit.split(",") if item.strip()],
        "excluded_items": [item.strip() for item in st.session_state.planner_excluded.split(",") if item.strip()],
        "dietary_preference": st.session_state.planner_dietary,
        "accessibility_needs": st.session_state.planner_accessibility.strip(),
        "return_to_origin": st.session_state.planner_return_to_origin,
        "priority_weights": {
            "cost": st.session_state.planner_weight_cost,
            "time": st.session_state.planner_weight_time,
            "preferences": st.session_state.planner_weight_preferences,
            "quality": st.session_state.planner_weight_quality,
        },
    })


def _step_intro(step):
    descriptions = [
        "Choose the places and travel window. We’ll check sample route connections between your stops.",
        "Set a trip-wide budget, daily limit, group size, and hotel comfort range.",
        "Tell the agent what a good trip feels like, including access and food needs.",
        "Decide which trade-offs matter most. The agent will score feasible plans with these weights.",
    ]
    st.markdown(
        f"<div class='wizard-title'><span class='wizard-number'>{step + 1}</span>"
        f"<div><div class='section-kicker'>STEP {step + 1} OF {len(STEPS)}</div>"
        f"<h2 style='margin:0'>{STEPS[step]}</h2></div></div>",
        unsafe_allow_html=True,
    )
    st.caption(descriptions[step])


def render(kb):
    _load_home_prefill()
    city_names = list(kb.city_by_name)
    default_start = date.today() + timedelta(days=7)
    default_end = default_start + timedelta(days=2)

    _seed("planner_origin", "Dehradun" if "Dehradun" in city_names else city_names[0])
    _seed("planner_selection_mode", "Select cities")
    _seed("planner_destinations", ["Rishikesh"] if "Rishikesh" in city_names else [])
    _seed("planner_start_date", default_start)
    _seed("planner_end_date", default_end)
    _seed("planner_available_days", 3)
    _seed("planner_return_to_origin", True)
    _seed("planner_transport_mode", "any")
    _seed("planner_total_budget", 25000)
    _seed("planner_daily_budget", 10000)
    _seed("planner_travellers", 1)
    _seed("planner_max_daily_travel", 8.0)
    _seed("planner_hotel_min", 500)
    _seed("planner_hotel_max", 5000)
    _seed("planner_hotel_comfort", "budget")
    _seed("planner_interests", ["history", "nature"])
    _seed("planner_pace", "normal")
    _seed("planner_must_visit", "")
    _seed("planner_excluded", "")
    _seed("planner_dietary", "no preference")
    _seed("planner_accessibility", "")
    _seed("planner_weight_cost", 25)
    _seed("planner_weight_time", 25)
    _seed("planner_weight_preferences", 25)
    _seed("planner_weight_quality", 25)
    _seed("planner_step", 0)

    step = max(0, min(int(st.session_state.planner_step), len(STEPS) - 1))
    st.markdown("<div class='section-kicker'>YOUR JOURNEY STARTS HERE</div>", unsafe_allow_html=True)
    st.title("Plan a trip")
    st.caption("A few focused steps are easier to complete. Your answers stay here as you move between steps.")
    st.progress((step + 1) / len(STEPS), text=f"Step {step + 1} of {len(STEPS)} · {STEPS[step]}")

    _step_intro(step)
    go_back = False
    advance = False

    with st.form("trip_request_wizard", clear_on_submit=False):
        if step == 0:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.selectbox("Where are you starting?", city_names, key="planner_origin")
            with c2:
                st.radio("How should we choose destinations?", ["Select cities", "Match my interests"],
                         horizontal=True, key="planner_selection_mode")

            origin = st.session_state.planner_origin
            destination_options = [city for city in city_names if city != origin]
            valid_destinations = [city for city in st.session_state.planner_destinations if city in destination_options]
            if valid_destinations != st.session_state.planner_destinations:
                st.session_state.planner_destinations = valid_destinations
            st.multiselect(
                "Destination cities",
                destination_options,
                key="planner_destinations",
                disabled=st.session_state.planner_selection_mode != "Select cities",
                help="Choose one or more cities. Interest matching can select eligible destinations automatically.",
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                st.date_input("Start date", min_value=date.today(), key="planner_start_date")
            with c2:
                start_date = st.session_state.planner_start_date
                if st.session_state.planner_end_date < start_date:
                    st.session_state.planner_end_date = start_date
                st.date_input("End date", min_value=start_date, key="planner_end_date")
            with c3:
                st.number_input("Available days", min_value=1, max_value=30, step=1,
                                key="planner_available_days", help="How many calendar days the trip can use.")
            st.checkbox("Return to my origin", key="planner_return_to_origin")
            st.selectbox("Preferred transport", ["any", "bus", "train", "flight", "car"], key="planner_transport_mode")

        elif step == 1:
            st.markdown("#### Keep the numbers comfortable")
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("Total trip budget (₹)", min_value=1000, max_value=2000000, step=1000,
                                key="planner_total_budget")
                st.number_input("Daily budget limit (₹)", min_value=500, max_value=500000, step=500,
                                key="planner_daily_budget")
            with c2:
                st.number_input("Travellers", min_value=1, max_value=20, step=1, key="planner_travellers")
                st.slider("Maximum intercity travel per day", 1.0, 18.0, step=0.5,
                          key="planner_max_daily_travel", help="The scheduler checks each travel day against this limit.")
            st.markdown("#### Choose your stay")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.number_input("Minimum hotel price / night (₹)", min_value=0, max_value=100000, step=250,
                                key="planner_hotel_min")
            with c2:
                st.number_input("Maximum hotel price / night (₹)", min_value=500, max_value=200000, step=500,
                                key="planner_hotel_max")
            with c3:
                st.selectbox("Comfort level", ["budget", "mid-range", "luxury"], key="planner_hotel_comfort")
            st.caption("Hotel costs are estimated per night from the bundled sample listings.")

        elif step == 2:
            st.markdown("#### What would make this trip yours?")
            st.multiselect("Interests", KNOWN_INTERESTS, key="planner_interests",
                           help="Choose as many as you like; attraction matches help the agent rank destinations.")
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("Travel pace", ["relaxed", "normal", "fast"], key="planner_pace")
                st.selectbox("Dietary preference", ["no preference", "vegetarian", "vegan", "non-vegetarian"],
                             key="planner_dietary")
            with c2:
                st.text_input("Must-visit attractions", key="planner_must_visit",
                              placeholder="For example: Taj Mahal, Humayun’s Tomb",
                              help="Separate multiple attraction names with commas.")
                st.text_input("Places to exclude", key="planner_excluded",
                              placeholder="Cities or attraction names, comma separated")
            st.text_input("Accessibility needs", key="planner_accessibility",
                          placeholder="For example: step-free access or limited walking")
            st.info("The sample knowledge base has simple accessibility and dietary tags. Confirm specific needs with providers before travel.")

        else:
            st.markdown("#### Balance the trade-offs")
            st.caption("Higher values tell the utility agent to give that dimension more influence when comparing feasible itineraries.")
            weight_cols = st.columns(4)
            for column, key, label, help_text in zip(
                weight_cols,
                ["planner_weight_cost", "planner_weight_time", "planner_weight_preferences", "planner_weight_quality"],
                ["Cost", "Time", "Preference fit", "Attraction quality"],
                ["Favor lower estimated spend.", "Favor less time in transit.", "Favor your chosen interests.", "Favor highly rated attractions."],
            ):
                with column:
                    st.slider(label, 0, 100, step=5, key=key, help=help_text)
            chosen = st.session_state.planner_destinations if st.session_state.planner_selection_mode == "Select cities" else []
            destination_label = ", ".join(chosen) if chosen else "Interest-matched destinations"
            summary = st.columns(4)
            summary[0].metric("Starting city", st.session_state.planner_origin)
            summary[1].metric("Trip window", f"{st.session_state.planner_available_days} days")
            summary[2].metric("Destination", destination_label)
            summary[3].metric("Budget", f"₹{st.session_state.planner_total_budget:,}")
            st.markdown(
                "<div class='soft-note'>The planner will compare route searches, schedule suitable attractions, "
                "estimate costs with a 12% contingency, and explain the selected plan.</div>",
                unsafe_allow_html=True,
            )

        st.write("")
        back_col, spacer, next_col = st.columns([1, 3, 1])
        with back_col:
            if step > 0:
                go_back = st.form_submit_button("← Back", use_container_width=True)
            else:
                st.caption("You can revise these details later.")
        with next_col:
            button_text = "Generate my trip" if step == len(STEPS) - 1 else "Continue →"
            advance = st.form_submit_button(button_text, type="primary", use_container_width=True)

    if go_back:
        _save_step_answers(step)
        st.session_state.planner_step = step - 1
        st.rerun()

    if advance:
        _save_step_answers(step)
        if step == 0 and st.session_state.planner_selection_mode == "Select cities" and not st.session_state.planner_destinations:
            st.error("Choose at least one destination, or select ‘Match my interests’.")
            return
        if step < len(STEPS) - 1:
            st.session_state.planner_step = step + 1
            st.rerun()
        try:
            request = _request_from_state()
            if request.end_date and request.start_date and request.end_date < request.start_date:
                st.error("End date must be on or after the start date.")
                return
            with st.spinner("Comparing routes and building your day-by-day plan…"):
                result = generate_best_itinerary(request, kb)
        except (TypeError, ValueError, KeyError) as exc:
            st.error(f"Please review the trip details and try again: {exc}")
            return
        st.session_state.trip_request = request
        st.session_state.trip_result = result
        if result.get("success"):
            st.session_state.planner_step = 0
            st.session_state.page = "Search & Route"
            st.rerun()
        for error in result.get("errors", []):
            st.error(error)
