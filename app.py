"""Personalized Travel Itinerary Planner Streamlit application."""

from __future__ import annotations

import os
from html import escape
from datetime import date, timedelta
from typing import Any

import streamlit as st

from pdf_export import build_itinerary_pdf
from travel_core import (
    CITIES,
    SLOT_ORDER,
    add_running_totals,
    as_trip_date,
    generate_ai_itinerary,
    generate_demo_itinerary,
    recommend_destinations,
    replace_activity,
    trip_total_usd,
)


st.set_page_config(
    page_title="Personalized Travel Itinerary Planner",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root {
      --ink: #18332e; --muted: #64756d; --paper: #f6f7f1; --surface: #ffffff;
      --forest: #1d6554; --leaf: #dcebe2; --coral: #db755c; --line: #dfe6df;
            --text-color: #18332e; --background-color: #f6f7f1;
            --secondary-background-color: #edf2eb; --primary-color: #1d6554;
    }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] { color: var(--ink); }
        p, label, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] { color: var(--ink); }
        .stApp { color: var(--ink); background: radial-gradient(ellipse at 85% 2%, rgba(227,239,226,.8), transparent 32%), var(--paper); }
    h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: 0 !important; }
    [data-testid="stSidebar"] { background: #edf2eb; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size: 1rem; }
    .brand-kicker { color: var(--forest); text-transform: uppercase; font-size: .72rem; font-weight: 700; letter-spacing: .12em; }
    .hero-title { color: var(--ink); font-family: 'Manrope', sans-serif; font-size: clamp(2rem, 4vw, 3rem); font-weight: 800; line-height: 1.08; margin: .35rem 0 .6rem; }
    .hero-sub { color: var(--muted); font-size: 1.02rem; max-width: 700px; }
    .metric-strip { display: flex; gap: 12px; flex-wrap: wrap; margin: 1rem 0 1.4rem; }
    .metric-pill { background: white; border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px; min-width: 132px; }
    .metric-label { display:block; color:var(--muted); font-size:.72rem; text-transform:uppercase; font-weight:700; }
    .metric-value { display:block; color:var(--ink); font-weight:700; font-size:1.05rem; margin-top:2px; }
    .destination-card { background: white; border: 1px solid var(--line); border-top: 3px solid var(--coral); border-radius: 8px; padding: 18px; height: 100%; }
    .destination-image { display:block; width:100%; aspect-ratio: 16 / 9; object-fit:cover; border-radius:5px; margin:0 0 14px; }
    .destination-card h3 { margin: 0 0 3px; font-size: 1.15rem; }
    .destination-card p { color: var(--muted); font-size: .9rem; }
    .tag { display: inline-block; padding: 4px 8px; border-radius: 4px; margin: 3px 4px 0 0; color: #285b4f; background: var(--leaf); font-size: .74rem; font-weight: 600; }
    .day-header { display:flex; align-items:baseline; gap:10px; padding: 12px 0 4px; border-bottom: 1px solid var(--line); }
    .day-header h3 { margin:0; }
    .activity { padding: 14px 0; border-bottom: 1px solid var(--line); }
    .activity-slot { color:var(--forest); font-size:.73rem; font-weight:700; text-transform:uppercase; }
    .activity-name { font-family:'Manrope',sans-serif; font-weight:700; font-size:1rem; margin:2px 0; }
    .activity-meta { color:var(--muted); font-size:.86rem; }
    .cost { color:var(--ink); font-weight:700; white-space:nowrap; }
    .stButton > button, .stDownloadButton > button { border-radius: 6px; font-weight: 700; min-height: 2.6rem; }
    .stButton > button[kind="primary"] { background: var(--forest); border-color: var(--forest); }
    div[data-testid="stMetric"] { background: white; border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }
    div[data-testid="stTabs"] button { font-weight: 700; }
    .note { color:var(--muted); font-size:.84rem; }
    @media (max-width: 700px) { .hero-title { font-size:2rem; } .metric-pill { flex:1; min-width:40%; } }
    </style>
    """,
    unsafe_allow_html=True,
)


if "saved_trips" not in st.session_state:
    st.session_state.saved_trips = []
if "current_trip" not in st.session_state:
    st.session_state.current_trip = None


def _choose_city(city: str) -> None:
    st.session_state["prefs_destination"] = city


def _secret_for(provider: str) -> str:
    env_name = "GEMINI_API_KEY" if provider == "Gemini" else "GROQ_API_KEY"
    key = os.environ.get(env_name, "")
    if not key:
        try:
            key = st.secrets.get(env_name, "")
        except Exception:
            key = ""
    return key


def _format_money(value: float, currency: str) -> str:
    if currency == "JPY" or currency == "IDR":
        return f"{currency} {value:,.0f}"
    return f"{currency} {value:,.2f}"


def _html(value: Any) -> str:
    return escape(str(value))


CITY_IMAGES = {
    "Lisbon": "https://images.unsplash.com/photo-1555881400-74d7acaacd8b?auto=format&fit=crop&w=900&q=80",
    "Tokyo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=900&q=80",
    "Jaipur": "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=900&q=80",
    "Mexico City": "https://images.unsplash.com/photo-1512813195386-6cf811ad3542?auto=format&fit=crop&w=900&q=80",
    "Bali": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=900&q=80",
    "Phuket": "https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?auto=format&fit=crop&w=900&q=80",
    "Kathmandu": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=900&q=80",
    "New York": "https://images.unsplash.com/photo-1534430480872-3498386e7856?auto=format&fit=crop&w=900&q=80",
    "Istanbul": "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=900&q=80",
    "Dubai": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=900&q=80",
}


def _render_activity(activity: dict[str, Any]) -> None:
    left, right = st.columns([5, 1], vertical_alignment="center")
    with left:
        st.markdown(
            f"<div class='activity'><div class='activity-slot'>{_html(activity['slot'])}</div>"
            f"<div class='activity-name'>{_html(activity['name'])}</div>"
            f"<div class='activity-meta'>{_html(activity.get('area', 'Local area'))} · {_html(activity.get('description', ''))}</div></div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(f"<div class='cost'>{_format_money(float(activity.get('cost_local', 0)), activity.get('currency', 'USD'))}</div>", unsafe_allow_html=True)
        st.caption(
            f"Running: {_format_money(float(activity.get('running_local', 0)), activity.get('currency', 'USD'))}"
            f" · ${float(activity.get('running_usd', 0)):.2f} · ₹{float(activity.get('running_inr', 0)):,.0f}"
        )


def _make_trip(destination: str, days: int, start_date: date, budget: str, party: str, pace: str,
               interests: list[str], party_size: int, dietary_needs: list[str],
               provider_mode: str, api_key: str) -> dict[str, Any]:
    end_date = start_date + timedelta(days=days - 1)
    date_label = f"{as_trip_date(start_date)} to {as_trip_date(end_date)}"
    used_ai = False
    if provider_mode in ("Gemini", "Groq") and api_key:
        try:
            itinerary = generate_ai_itinerary(
                provider_mode, api_key, destination, days, interests, budget, party, pace,
                date_label, party_size, dietary_needs,
            )
            used_ai = True
        except Exception:
            st.warning("The AI service could not return a usable itinerary. A curated demo itinerary is shown instead; your API key was not saved.")
            itinerary = generate_demo_itinerary(
                destination, days, interests, budget, party, party_size, dietary_needs,
            )
    else:
        itinerary = generate_demo_itinerary(
            destination, days, interests, budget, party, party_size, dietary_needs,
        )
    return {
        "id": f"{destination}-{date.today().isoformat()}-{len(st.session_state.saved_trips) + 1}",
        "destination": destination,
        "country": CITIES[destination]["country"],
        "days": days,
        "start_date": as_trip_date(start_date),
        "end_date": as_trip_date(end_date),
        "budget": budget,
        "party": party,
        "party_size": party_size,
        "pace": pace,
        "interests": interests,
        "dietary_needs": dietary_needs,
        "itinerary": itinerary,
        "created_at": date.today().isoformat(),
        "source": provider_mode if used_ai else "Demo mode",
        "currency": CITIES[destination]["currency"],
    }


with st.sidebar:
    st.markdown("### ✦ Wayfinder")
    st.caption("Personalized Travel Itinerary Planner")
    st.divider()
    st.markdown("#### Your trip")
    provider_mode = st.selectbox("Planning mode", ["Demo mode", "Gemini", "Groq"], help="Demo mode works without a key. API keys are used for this session only.")
    api_key = ""
    if provider_mode != "Demo mode":
        provider_label = "Gemini API key" if provider_mode == "Gemini" else "Groq API key"
        api_key = st.text_input(provider_label, type="password", placeholder="Paste key for this session", help="Never stored in trip history or written to disk.")
        if not api_key:
            api_key = _secret_for(provider_mode)
            if api_key:
                st.caption("Using configured environment / Streamlit secret.")
    st.markdown("---")
    destination_options = ["No fixed destination", *CITIES.keys()]
    destination = st.selectbox("Destination", destination_options, key="prefs_destination")
    vibe = st.selectbox("Travel mood", ["Beach", "Mountains", "Cultural", "Urban", "Food-focused", "Adventure", "Relaxed"])
    trip_days = st.number_input("Trip duration · days", min_value=1, max_value=14, value=4, step=1)
    start_date = st.date_input("Travel start date", value=date.today() + timedelta(days=21), min_value=date.today())
    budget = st.selectbox("Budget level", ["Budget", "Moderate", "Luxury"], index=1)
    party = st.selectbox("Travel party", ["Solo", "Couple", "Family", "Friends"])
    party_defaults = {"Solo": 1, "Couple": 2, "Family": 4, "Friends": 4}
    party_size = st.number_input("Number of travelers", min_value=1, max_value=20, value=party_defaults[party], step=1)
    pace = st.selectbox("Pace", ["Relaxed", "Moderate", "Fast-Paced"], index=1)
    interests = st.multiselect("Interests", ["Food", "Adventure", "History", "Nightlife"], default=["Food", "History"])
    dietary_needs = st.multiselect("Dietary needs", ["Vegetarian", "Vegan", "Gluten-free", "Halal", "Dairy-free"])
    if destination == "No fixed destination":
        st.caption("Pick a destination from the recommender before generating an itinerary.")

st.markdown("<div class='brand-kicker'>A better kind of getting away</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-title'>Your next trip, thoughtfully mapped.</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Find a place that fits your mood, then shape a day-by-day plan with less backtracking and a clearer handle on spend.</div>", unsafe_allow_html=True)

active_trip = st.session_state.current_trip
if active_trip:
    total = trip_total_usd(active_trip["itinerary"])
    st.markdown(
        f"<div class='metric-strip'><div class='metric-pill'><span class='metric-label'>Current trip</span><span class='metric-value'>{active_trip['destination']}</span></div>"
        f"<div class='metric-pill'><span class='metric-label'>Dates</span><span class='metric-value'>{active_trip['start_date']} → {active_trip['end_date']}</span></div>"
        f"<div class='metric-pill'><span class='metric-label'>Estimated total</span><span class='metric-value'>${total:,.2f} USD</span></div>"
        f"<div class='metric-pill'><span class='metric-label'>Plan source</span><span class='metric-value'>{active_trip['source']}</span></div></div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown("<div class='metric-strip'><div class='metric-pill'><span class='metric-label'>Planning style</span><span class='metric-value'>Human-paced</span></div><div class='metric-pill'><span class='metric-label'>Budget view</span><span class='metric-value'>Local + USD / INR</span></div><div class='metric-pill'><span class='metric-label'>Storage</span><span class='metric-value'>Private session history</span></div></div>", unsafe_allow_html=True)

tab_recommend, tab_itinerary, tab_custom, tab_manage = st.tabs([
    "01  Discover", "02  Itinerary", "03  Make it yours", "04  Trip library",
])

with tab_recommend:
    st.subheader("A destination with your kind of energy")
    st.write(f"Recommendations tuned to **{vibe.lower()}**, a **{budget.lower()}** budget, your travel season, and selected interests.")
    recommendations = recommend_destinations(vibe, budget, start_date.month, interests)
    cards = st.columns(3)
    for index, recommendation in enumerate(recommendations):
        with cards[index]:
            tags_html = "".join(f"<span class='tag'>{_html(tag)}</span>" for tag in recommendation["tags"])
            st.markdown(
                f"<div class='destination-card'><img class='destination-image' src='{CITY_IMAGES[recommendation['city']]}' alt='Travel view of {_html(recommendation['city'])}'>"
                f"<h3>{_html(recommendation['city'])}</h3><div class='note'>{_html(recommendation['country'])}</div>"
                f"<p>{_html(recommendation['reason'])}</p>{tags_html}</div>", unsafe_allow_html=True,
            )
            st.button("Choose destination", key=f"choose-{recommendation['city']}", use_container_width=True,
                      on_click=_choose_city, args=(recommendation["city"],))
    st.caption("Season fit uses a lightweight month-to-month travel guide, not a live weather forecast.")

with tab_itinerary:
    st.subheader("Day-by-day itinerary")
    if destination == "No fixed destination":
        st.info("Choose one of the recommended cities in Discover, or select a destination in the sidebar.")
    else:
        end_date = start_date + timedelta(days=int(trip_days) - 1)
        st.write(f"**{destination}, {CITIES[destination]['country']}** · {start_date:%b %d} – {end_date:%b %d, %Y} · {trip_days} days")
        if st.button("Generate optimized trip", type="primary", icon="🧭", use_container_width=False):
            trip = _make_trip(
                destination, int(trip_days), start_date, budget, party, pace, interests,
                int(party_size), dietary_needs, provider_mode, api_key,
            )
            st.session_state.current_trip = trip
            st.session_state.saved_trips.insert(0, trip)
            st.success(f"Your {trip['days']}-day plan for {destination} is ready.")
            st.rerun()
        active_trip = st.session_state.current_trip
        if active_trip:
            if active_trip["destination"] != destination:
                st.info(f"Showing the saved plan for {active_trip['destination']}. Generate again to replace it with {destination}.")
            for day in active_trip["itinerary"]:
                st.markdown(f"<div class='day-header'><h3>{_html(day['title'])}</h3><span class='note'>Four stops · neighborhood-aware ordering</span></div>", unsafe_allow_html=True)
                for activity in day["activities"]:
                    _render_activity(activity)
            total_usd = trip_total_usd(active_trip["itinerary"])
            local_total = sum(float(item.get("cost_local", 0)) for day in active_trip["itinerary"] for item in day["activities"])
            metric_a, metric_b, metric_c = st.columns(3)
            metric_a.metric("Estimated total · USD", f"${total_usd:,.2f}")
            metric_b.metric(f"Estimated total · {active_trip['currency']}", _format_money(local_total, active_trip["currency"]))
            metric_c.metric("Estimated total · INR", f"₹{total_usd * 83:,.0f}")
            st.caption("Estimates cover listed activities and meals only. Rates are static approximations; transport, lodging, taxes, and live prices are not included.")
        else:
            st.info("Set your preferences in the sidebar, then generate your itinerary here.")

with tab_custom:
    st.subheader("Tune a day without rebuilding the trip")
    active_trip = st.session_state.current_trip
    if not active_trip:
        st.info("Generate a trip first. Your swaps will be limited to one selected day and time slot.")
    else:
        chosen_day_number = st.selectbox("Day to customize", [day["day"] for day in active_trip["itinerary"]], format_func=lambda value: f"Day {value}")
        selected_day = next(day for day in active_trip["itinerary"] if day["day"] == chosen_day_number)
        selected_slot = st.selectbox("Time slot", SLOT_ORDER)
        current_activity = next(item for item in selected_day["activities"] if item["slot"] == selected_slot)
        st.caption(f"Current: {current_activity['name']} · {current_activity.get('area', '')}")
        with st.form("swap_activity_form"):
            swap_request = st.text_input("What would you like instead?", placeholder="e.g. Swap museum for outdoor market")
            swap_submitted = st.form_submit_button("Apply activity swap")
        if swap_submitted:
            if not swap_request.strip():
                st.warning("Describe the change you want before applying a swap.")
            else:
                updated_day = replace_activity(selected_day, selected_slot, swap_request, active_trip["destination"])
                active_trip["itinerary"] = [updated_day if day["day"] == chosen_day_number else day for day in active_trip["itinerary"]]
                active_trip["itinerary"] = add_running_totals(active_trip["itinerary"])
                st.session_state.current_trip = active_trip
                for saved in st.session_state.saved_trips:
                    if saved["id"] == active_trip["id"]:
                        saved.update(active_trip)
                st.success("Updated that slot. The rest of your itinerary is unchanged.")
                st.rerun()
        if st.button("Regenerate this day", help="Rebuild the four slots for this day only using your current preferences."):
            replacement = None
            if provider_mode in ("Gemini", "Groq") and api_key:
                try:
                    day_date = date.fromisoformat(active_trip["start_date"]) + timedelta(days=chosen_day_number - 1)
                    replacement = generate_ai_itinerary(
                        provider_mode, api_key, active_trip["destination"], 1, active_trip["interests"],
                        active_trip["budget"], active_trip["party"], active_trip["pace"], as_trip_date(day_date),
                        active_trip.get("party_size"), active_trip.get("dietary_needs", []),
                    )[0]
                except Exception:
                    st.warning("The AI service could not regenerate this day. A different curated day is shown instead.")
            if replacement is None:
                replacement = generate_demo_itinerary(
                    active_trip["destination"], chosen_day_number + 1, active_trip["interests"],
                    active_trip["budget"], active_trip["party"], active_trip.get("party_size"),
                    active_trip.get("dietary_needs", []),
                )[-1]
            replacement["day"] = chosen_day_number
            replacement["title"] = f"Day {chosen_day_number} · refreshed neighborhood plan"
            active_trip["itinerary"] = [replacement if day["day"] == chosen_day_number else day for day in active_trip["itinerary"]]
            active_trip["itinerary"] = add_running_totals(active_trip["itinerary"])
            st.session_state.current_trip = active_trip
            for saved in st.session_state.saved_trips:
                if saved["id"] == active_trip["id"]:
                    saved.update(active_trip)
            st.success("Only the selected day was regenerated.")
            st.rerun()

with tab_manage:
    st.subheader("Your trip library")
    st.caption("Trips are held in this Streamlit session. No external database is required; session history is cleared when the session ends.")
    trips = st.session_state.saved_trips
    if not trips:
        st.info("Your saved itineraries will appear here after the first generation.")
    else:
        labels = [f"{trip['destination']} · {trip['start_date']} · {trip['days']} days" for trip in trips]
        selected_trip_index = st.selectbox("Trip history", range(len(trips)), format_func=lambda index: labels[index])
        selected_trip = trips[selected_trip_index]
        left, right = st.columns([1, 3])
        with left:
            if st.button("Load trip", use_container_width=True):
                st.session_state.current_trip = selected_trip
                st.success("Trip loaded into the Itinerary and Make it yours tabs.")
        with right:
            st.markdown(f"**{selected_trip['destination']}** · {selected_trip['country']} · {selected_trip['days']} days · {selected_trip['source']}")
            st.caption(f"{selected_trip['start_date']} to {selected_trip['end_date']} · Estimated ${trip_total_usd(selected_trip['itinerary']):,.2f} USD")
        pdf_bytes = build_itinerary_pdf(selected_trip)
        st.download_button(
            "Download offline PDF guide", data=pdf_bytes,
            file_name=f"{selected_trip['destination'].lower().replace(' ', '-')}-itinerary.pdf",
            mime="application/pdf", icon="⬇", type="primary",
        )
        st.markdown("#### Emergency checklist")
        st.checkbox("Save local emergency number and accommodation address", key="emergency-local")
        st.checkbox("Share itinerary and check-in plan with a trusted contact", key="emergency-share")
        st.checkbox("Keep travel insurance and key documents accessible offline", key="emergency-docs")
