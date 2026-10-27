# Intelligent Travel Planning Agent

A modular Python travel planner with a Streamlit graphical interface. It runs without paid services or internet access after installation and uses the bundled JSON knowledge base for cities, attractions, hotels, transport timetables, and daily costs.

> **Planning estimates:** route times, fares, hotel prices, ratings, hours, and room counts are illustrative sample data. They are not live schedules, availability, or booking quotes. The application adds a 12% contingency to its estimated trip total.

## Setup and run

Python 3.10 or newer is required.

On macOS, open a terminal in the project folder and create a private environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, create and activate the environment with `python -m venv .venv` and `.venv\Scripts\Activate.ps1`, then run the same pip and Streamlit commands. Open the local URL printed by Streamlit. The application starts on the Home page. Use the sidebar to open the planner, route explorer, itinerary, constraint checks, knowledge base, algorithm lab, and saved trips.

## Project structure

```text
travel_planner_gui/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── cities.json
│   ├── attractions.json
│   ├── hotels.json
│   ├── transport_routes.json
│   └── user_profiles.json
├── backend/
│   ├── knowledge_base.py
│   ├── graph.py
│   ├── rules.py
│   ├── search_algorithms.py
│   ├── goal_agent.py
│   ├── utility_agent.py
│   ├── scheduler.py
│   ├── cost_calculator.py
│   ├── itinerary_generator.py
│   ├── validators.py
│   └── storage.py
├── gui/
│   ├── home.py
│   ├── trip_form.py
│   ├── route_view.py
│   ├── itinerary_view.py
│   ├── constraints_view.py
│   ├── knowledge_base_view.py
│   ├── algorithm_comparison.py
│   └── saved_itineraries.py
└── tests/
    ├── conftest.py
    ├── test_search_algorithms.py
    ├── test_constraints.py
    └── test_itinerary_generation.py
```

### Architecture

- **Knowledge base:** `backend/knowledge_base.py` reads JSON records from `data/`. The sample contains Dehradun plus 11 other Indian cities, 50 attractions, 36 hotels, and 60 directed transport connections.
- **Graph and search:** `backend/graph.py` models parallel route edges with fare, time, mode, distance, departure, and operating days. `backend/search_algorithms.py` implements BFS, DFS, UCS, Greedy Best-First, and A*.
- **Goal-based planning:** `backend/goal_agent.py` resolves explicit or interest-matched destinations and builds a route through each selected stop, including the requested return leg.
- **Scheduling and cost:** `backend/scheduler.py` schedules route legs, hotel nights, attraction slots, meals, and rest. `backend/cost_calculator.py` calculates per-category INR estimates and contingency.
- **Utility and validation:** `backend/utility_agent.py` combines normalized cost, time, preference, and quality scores using the user's weights. Trip generation compares the five route algorithms plus UCS/A* time-optimized routes, then selects the highest-utility feasible result. `backend/validators.py` reports each requested constraint with an explanation and a suggested repair.
- **GUI:** `app.py` provides a custom travel-studio shell and routes navigation to independent Streamlit views. Trip setup uses a four-step wizard; the home page includes a destination preview, the route map can reveal alternate links, itinerary days and cost charts are interactive, and knowledge-base tables are grouped into searchable tabs. The backend has no Streamlit dependency, so it can later be called from Tkinter, an API, or a mobile client.
- **Saved trips:** the UI stores summaries in `data/saved_itineraries.json` on the current device. This file is created the first time a user saves a trip.

## Algorithms

| Algorithm | Search objective | Optimality note |
|---|---|---|
| BFS | Fewest route hops | Minimum-hop route for unweighted edges |
| DFS | Explore a path deeply | Not guaranteed optimal |
| UCS | Lowest fare (per traveller) | Optimal for nonnegative fare weights |
| Greedy Best-First | Lowest straight-line fare heuristic | Not guaranteed optimal |
| A* | Accumulated fare + admissible straight-line heuristic | Optimal for fare weights in this graph |

Search metrics are per local run and can vary slightly between runs. The comparison page runs all algorithms against the same trip request.

## Sample trip scenarios

1. **Dehradun → Rishikesh, 3 days, 1 traveller, budget hotel, ₹25,000.** Expected route: direct bus each way, with one full day for nature-oriented attractions. Approximate route travel is 2.6 hours total; the sample estimate is about ₹5,300 including contingency. Exact attraction slots depend on the chosen dates and closed days.
2. **Dehradun → Jaipur, train preferred, 4 days.** Expected route: Dehradun → Delhi → Jaipur by train, then the reverse legs. The planner allocates travel days and an overnight stay at Jaipur; if the date window is too short or the daily travel cap is too low, validation calls that out.
3. **Dehradun → Goa by any mode, 7 days.** Expected route uses one or more transfers (for example, through Delhi and Mumbai) depending on search algorithm. Long transfers are separated into route days; a too-short trip is marked infeasible with a suggestion to add days or choose a closer destination.
4. **Budget failure example:** Dehradun → Rishikesh with a total budget of ₹1,000. The route is still reachable, but the total budget constraint fails after hotel, food, local transport, attraction fees, and contingency are included.
5. **Reachability failure example:** select Dehradun → Jaipur with `car` as the only permitted transport mode. The sample data has no all-car route between these cities, so the agent explains that no permitted connection is available.

## GUI experience

The app uses a calm travel-studio palette with a dark navigation rail, a destination preview on Home, and compact budget and route summaries. Plan a Trip guides people through route and dates, budget and stay, travel style, and priority weights. Search & Route combines an offline Plotly map with algorithm selection, an alternate-connection toggle, and mode filters. Itinerary lets people select a day, inspect meal and hotel details, and explore a cost chart. Constraint Validation can be filtered to passing checks or items needing attention. Knowledge Base tables are grouped into searchable tabs, while Compare Algorithms lets people chart utility, fare, duration, or explored nodes.

## Run the tests

The test suite covers all five search algorithms, budget validation, an unreachable mode-filtered route, invalid dates, and itinerary scheduling.

```bash
pip install -r requirements.txt
pytest -q
```

## Offline limitations

- The data is a small static demonstration set, not a booking or navigation service.
- Attraction opening times, fares, and hotel prices should be checked with providers before travel.
- Accessibility fields are simple dataset flags; contact venues and carriers for current, specific access information.
- The itinerary generator models one overnight hotel stay per scheduled day outside the origin and uses sample route departure times. It does not reserve tickets or rooms.
