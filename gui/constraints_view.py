import streamlit as st


def render():
    st.markdown("<div class='section-kicker'>PLAN HEALTH CHECK</div>", unsafe_allow_html=True)
    st.title("Constraint Validation")
    st.caption("Review how the draft fits your budget, schedule, route, meals, rest, and access needs.")
    result = st.session_state.get("trip_result")
    if not result or not result.get("success"):
        st.info("Generate a trip first to run the constraint checks.")
        return
    validations = result.get("validations", [])
    passed = sum(row["passed"] is True for row in validations)
    failed = sum(row["passed"] is False for row in validations)
    c1, c2, c3 = st.columns(3)
    c1.metric("Passed", passed)
    c2.metric("Needs attention", failed)
    c3.metric("Overall", "Feasible" if failed == 0 else "Review required")
    if validations:
        st.progress(passed / len(validations), text=f"{passed} of {len(validations)} checks passed")
    view = st.radio("Show checks", ["All checks", "Needs attention", "Passed"], horizontal=True)
    visible = [row for row in validations
               if view == "All checks"
               or (view == "Needs attention" and row["passed"] is False)
               or (view == "Passed" and row["passed"] is True)]
    if not visible:
        st.success("There are no checks in this group.")
    for row in visible:
        is_attention = row["passed"] is False
        with st.expander(f"{'⚠️' if is_attention else ('✅' if row['passed'] else '⚪')}  {row['constraint']}", expanded=is_attention):
            st.write(row["message"])
            if row.get("suggestion"):
                st.caption("Possible fix: " + row["suggestion"])
    if failed:
        st.warning("Fix the failed checks by adjusting route, dates, pace, budget, transport, or hotel settings in Plan a Trip, then regenerate.")
