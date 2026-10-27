"""Streamlit entry point for the offline Intelligent Travel Planning Agent."""
import streamlit as st

from backend.knowledge_base import KnowledgeBaseError, load_knowledge_base
from gui import algorithm_comparison, constraints_view, home, itinerary_view
from gui import knowledge_base_view, route_view, saved_itineraries, trip_form


st.set_page_config(
    page_title="Intelligent Travel Planning Agent",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --ink: #17384a;
        --muted: #657985;
        --teal: #0d7774;
        --teal-dark: #095b5c;
        --coral: #e47b62;
        --paper: #f4f7f5;
        --line: #e2eae6;
      }
      .stApp { background: var(--paper); color: var(--ink); }
      [data-testid="stHeader"] { background: rgba(244,247,245,.88); }
      .block-container { max-width: 1380px; padding-top: 1.25rem; padding-bottom: 3rem; }
      h1, h2, h3 { color: var(--ink); letter-spacing: -.025em; }
      h1 { font-weight: 760; }
      h2 { font-weight: 700; }
      p, li { color: #4d6470; }
      [data-testid="stMetric"] {
        background: #fff; border: 1px solid var(--line); border-radius: 18px;
        padding: 1rem 1.1rem; box-shadow: 0 5px 18px rgba(27,60,66,.035);
      }
      [data-testid="stMetricLabel"] { color: var(--muted); }
      [data-testid="stMetricValue"] { color: var(--ink); font-weight: 750; }
      [data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: var(--line) !important; border-radius: 20px !important;
        background: rgba(255,255,255,.88);
      }
      [data-testid="stForm"] {
        background: #fff; border: 1px solid var(--line); border-radius: 22px;
        padding: 1.4rem; box-shadow: 0 8px 28px rgba(27,60,66,.045);
      }
      .stButton > button, [data-testid="stFormSubmitButton"] button {
        min-height: 2.8rem; border-radius: 12px; font-weight: 650;
        transition: transform .16s ease, box-shadow .16s ease;
      }
      .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px); box-shadow: 0 7px 16px rgba(13,119,116,.16);
      }
      .stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
        background: var(--teal) !important; border-color: var(--teal) !important;
        color: #fff !important;
      }
      [data-testid="stSidebar"] {
        background: linear-gradient(165deg, #123344 0%, #0d2a37 100%);
        border-right: 1px solid rgba(255,255,255,.07);
      }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
      [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #e8f1ef;
      }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #a9c0c3; }
      [data-testid="stSidebar"] [role="radiogroup"] > label {
        border-radius: 11px; padding: .35rem .55rem; margin: .08rem 0;
      }
      [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
        background: rgba(255,255,255,.07);
      }
      [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        color: #153648 !important;
      }
      .app-topline {
        display: flex; align-items: center; justify-content: space-between;
        gap: 1rem; margin: .1rem 0 1.15rem; color: #73858d;
        font-size: .72rem; font-weight: 750; letter-spacing: .12em;
        text-transform: uppercase;
      }
      .app-topline .brand-mark { color: var(--teal); }
      .app-topline .offline-pill {
        border: 1px solid #d7e7df; background: #edf6f0; color: #3b7662;
        border-radius: 999px; padding: .35rem .7rem; letter-spacing: .04em;
      }
      .hero-panel {
        position: relative; overflow: hidden; border-radius: 28px;
        padding: clamp(1.5rem, 4vw, 3.25rem);
        background: radial-gradient(circle at 84% 15%, rgba(237,190,138,.56), transparent 27%),
                    radial-gradient(circle at 100% 100%, rgba(68,159,147,.47), transparent 35%),
                    linear-gradient(118deg, #123648 0%, #155b65 58%, #2c827b 100%);
        color: #fff; box-shadow: 0 18px 42px rgba(19,58,66,.15);
      }
      .hero-panel h1 { color: #fff; max-width: 760px; font-size: clamp(2.3rem, 5vw, 4rem); line-height: 1.04; margin: .8rem 0 1rem; }
      .hero-panel h1 em { color: #f0c89d; font-style: normal; }
      .hero-panel p { color: rgba(244,250,247,.82); max-width: 660px; font-size: 1.08rem; }
      .hero-kicker { color: #c6e4d9; text-transform: uppercase; font-size: .75rem; font-weight: 750; letter-spacing: .16em; }
      .hero-points { display: flex; gap: .65rem; flex-wrap: wrap; margin-top: 1.3rem; }
      .hero-points span { border: 1px solid rgba(255,255,255,.22); background: rgba(255,255,255,.08); color: #edf5f2; padding: .42rem .7rem; border-radius: 999px; font-size: .8rem; }
      .section-kicker { color: var(--teal); font-size: .72rem; font-weight: 750; text-transform: uppercase; letter-spacing: .14em; margin-bottom: .25rem; }
      .wizard-title { display:flex; align-items:center; gap:.8rem; }
      .wizard-number { display:inline-flex; width:2.15rem; height:2.15rem; border-radius:50%; align-items:center; justify-content:center; background:#e2f2ec; color:var(--teal-dark); font-weight:800; }
      .mini-label { color: #788991; font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; font-weight: 700; }
      .soft-note { background:#edf5f1; border:1px solid #dcebe4; border-radius:14px; padding:.85rem 1rem; color:#45655d; }
      .route-line { color:#d3e8df; font-size:.95rem; letter-spacing:.03em; }
      .stProgress > div > div > div > div { background: var(--teal); }
      @media (max-width: 760px) {
        .app-topline { font-size:.62rem; }
        .hero-panel { border-radius:20px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if "page" not in st.session_state:
    st.session_state.page = "Home"
if "planner_step" not in st.session_state:
    st.session_state.planner_step = 0


def _sync_navigation():
    st.session_state.page = st.session_state.nav_page


if "nav_page" not in st.session_state:
    st.session_state.nav_page = st.session_state.page
elif st.session_state.page != st.session_state.nav_page:
    # Home-page actions can change the active section before the next rerun.
    st.session_state.nav_page = st.session_state.page

page_icons = {
    "Home": "⌂",
    "Plan a Trip": "✦",
    "Search & Route": "↗",
    "Itinerary": "▤",
    "Constraint Validation": "✓",
    "Knowledge Base": "◫",
    "Compare Algorithms": "⇄",
    "Saved Itineraries": "♡",
}
pages = list(page_icons)

with st.sidebar:
    st.markdown("<div style='font-size:2rem'>🧭</div>", unsafe_allow_html=True)
    st.markdown("## Travel Studio")
    st.caption("Offline planning · India edition")
    st.divider()
    st.markdown("<div class='mini-label'>YOUR WORKSPACE</div>", unsafe_allow_html=True)
    selected = st.radio(
        "Navigate",
        pages,
        format_func=lambda page: f"{page_icons[page]}   {page}",
        label_visibility="collapsed",
        key="nav_page",
        on_change=_sync_navigation,
    )
    st.divider()
    result = st.session_state.get("trip_result")
    if result and result.get("success"):
        request = result["request"]
        route = result["route_plan"]
        st.markdown("<div class='mini-label'>CURRENT DRAFT</div>", unsafe_allow_html=True)
        st.markdown("**" + " → ".join(route.nodes) + "**")
        st.caption(f"₹{result['costs']['estimated_total_inr']:,} estimate · {request.available_days} days")
        ratio = result["costs"]["estimated_total_inr"] / max(request.total_budget_inr, 1)
        st.progress(min(ratio, 1.0), text="Budget used")
        st.divider()
    st.caption("Sample fares, schedules, and hotel prices are estimates. No live bookings or paid APIs are used.")

st.markdown(
    "<div class='app-topline'><span class='brand-mark'>TRAVEL INTELLIGENCE STUDIO</span>"
    "<span class='offline-pill'>● Offline knowledge base</span></div>",
    unsafe_allow_html=True,
)

try:
    kb = load_knowledge_base()
except KnowledgeBaseError as exc:
    st.error(str(exc))
    st.stop()

if st.session_state.page == "Home":
    home.render(kb)
elif st.session_state.page == "Plan a Trip":
    trip_form.render(kb)
elif st.session_state.page == "Search & Route":
    route_view.render(kb)
elif st.session_state.page == "Itinerary":
    itinerary_view.render()
elif st.session_state.page == "Constraint Validation":
    constraints_view.render()
elif st.session_state.page == "Knowledge Base":
    knowledge_base_view.render(kb)
elif st.session_state.page == "Compare Algorithms":
    algorithm_comparison.render(kb)
elif st.session_state.page == "Saved Itineraries":
    saved_itineraries.render()
