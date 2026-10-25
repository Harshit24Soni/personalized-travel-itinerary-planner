"""Travel planning data and generation helpers."""

from __future__ import annotations

import json
import itertools
import math
import re
from datetime import date
from typing import Any

import requests


CURRENCY_RATES = {
    "USD": 1.0,
    "INR": 83.0,
    "EUR": 0.92,
    "JPY": 150.0,
    "THB": 36.5,
    "AED": 3.67,
    "GBP": 0.79,
    "IDR": 15_600.0,
    "NPR": 134.0,
    "TRY": 32.0,
    "MXN": 17.0,
}

CITIES: dict[str, dict[str, Any]] = {
    "Lisbon": {
        "country": "Portugal", "currency": "EUR", "vibes": ["coastal", "cultural", "urban"],
        "best_months": [3, 4, 5, 6, 9, 10], "budget": "moderate", "tags": ["Golden-hour viewpoints", "Seafood", "Tile-lined lanes"],
        "stops": [
            {"name": "Alfama & São Jorge Castle", "area": "Alfama", "kind": "History", "time": "Morning Sightseeing", "cost": 15, "lat": 38.7139, "lon": -9.1335},
            {"name": "Time Out Market lunch", "area": "Cais do Sodré", "kind": "Food", "time": "Lunch Recommendation", "cost": 18, "lat": 38.7074, "lon": -9.1456},
            {"name": "Riverside walk at Belém", "area": "Belém", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 8, "lat": 38.6962, "lon": -9.2065},
            {"name": "Fado dinner in Bairro Alto", "area": "Bairro Alto", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 38, "lat": 38.7150, "lon": -9.1440},
            {"name": "LX Factory food hall", "area": "Alcântara", "kind": "Food", "time": "Lunch Recommendation", "cost": 16, "lat": 38.7037, "lon": -9.1780},
            {"name": "Miradouro da Senhora do Monte", "area": "Graça", "kind": "Adventure", "time": "Afternoon Leisure", "cost": 0, "lat": 38.7193, "lon": -9.1328},
        ],
    },
    "Tokyo": {
        "country": "Japan", "currency": "JPY", "vibes": ["urban", "cultural", "foodie"],
        "best_months": [3, 4, 5, 10, 11], "budget": "moderate", "tags": ["Late-night eats", "Temple mornings", "Design-forward"],
        "stops": [
            {"name": "Meiji Shrine forest walk", "area": "Harajuku", "kind": "History", "time": "Morning Sightseeing", "cost": 0, "lat": 35.6764, "lon": 139.6993},
            {"name": "Market sushi lunch", "area": "Shibuya", "kind": "Food", "time": "Lunch Recommendation", "cost": 2200, "lat": 35.6595, "lon": 139.7005},
            {"name": "Omotesando galleries & shops", "area": "Omotesando", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 1200, "lat": 35.6654, "lon": 139.7120},
            {"name": "Izakaya dinner in Shinjuku", "area": "Shinjuku", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 4500, "lat": 35.6938, "lon": 139.7034},
            {"name": "Senso-ji & Nakamise Street", "area": "Asakusa", "kind": "History", "time": "Morning Sightseeing", "cost": 500, "lat": 35.7148, "lon": 139.7967},
            {"name": "teamLab Planets", "area": "Toyosu", "kind": "Adventure", "time": "Afternoon Leisure", "cost": 3800, "lat": 35.6491, "lon": 139.7894},
        ],
    },
    "Jaipur": {
        "country": "India", "currency": "INR", "vibes": ["cultural", "history", "foodie"],
        "best_months": [10, 11, 12, 1, 2, 3], "budget": "budget", "tags": ["Pink-city heritage", "Rooftop dining", "Craft markets"],
        "stops": [
            {"name": "Amber Fort", "area": "Amer", "kind": "History", "time": "Morning Sightseeing", "cost": 500, "lat": 26.9855, "lon": 75.8513},
            {"name": "Local thali lunch", "area": "Amer Road", "kind": "Food", "time": "Lunch Recommendation", "cost": 450, "lat": 26.9700, "lon": 75.8390},
            {"name": "Hawa Mahal & old city lanes", "area": "Old City", "kind": "History", "time": "Afternoon Leisure", "cost": 200, "lat": 26.9239, "lon": 75.8267},
            {"name": "Rooftop dinner near Badi Chaupar", "area": "Old City", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 1100, "lat": 26.9250, "lon": 75.8280},
            {"name": "Jantar Mantar", "area": "Old City", "kind": "History", "time": "Morning Sightseeing", "cost": 200, "lat": 26.9248, "lon": 75.8246},
            {"name": "Bapu Bazaar browsing", "area": "Old City", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 0, "lat": 26.9160, "lon": 75.8210},
        ],
    },
    "Mexico City": {
        "country": "Mexico", "currency": "MXN", "vibes": ["cultural", "urban", "foodie"],
        "best_months": [2, 3, 4, 10, 11], "budget": "moderate", "tags": ["Museum-rich", "Street food", "Lively plazas"],
        "stops": [
            {"name": "Chapultepec Castle & park", "area": "Chapultepec", "kind": "History", "time": "Morning Sightseeing", "cost": 95, "lat": 19.4204, "lon": -99.1819},
            {"name": "Roma Norte taco lunch", "area": "Roma Norte", "kind": "Food", "time": "Lunch Recommendation", "cost": 220, "lat": 19.4195, "lon": -99.1617},
            {"name": "Museo Frida Kahlo", "area": "Coyoacán", "kind": "History", "time": "Afternoon Leisure", "cost": 320, "lat": 19.3553, "lon": -99.1625},
            {"name": "Cantina dinner in Centro", "area": "Centro Histórico", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 450, "lat": 19.4326, "lon": -99.1332},
            {"name": "National Museum of Anthropology", "area": "Chapultepec", "kind": "History", "time": "Morning Sightseeing", "cost": 95, "lat": 19.4260, "lon": -99.1860},
            {"name": "Condesa café & leafy walk", "area": "Condesa", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 150, "lat": 19.4110, "lon": -99.1710},
        ],
    },
    "Bali": {
        "country": "Indonesia", "currency": "IDR", "vibes": ["coastal", "adventure", "relaxed"],
        "best_months": [4, 5, 6, 7, 8, 9], "budget": "moderate", "tags": ["Island mornings", "Wellness", "Waterfalls"],
        "stops": [
            {"name": "Tegallalang rice terraces", "area": "Ubud", "kind": "Adventure", "time": "Morning Sightseeing", "cost": 50000, "lat": -8.4312, "lon": 115.2792},
            {"name": "Ubud warung lunch", "area": "Ubud Center", "kind": "Food", "time": "Lunch Recommendation", "cost": 80000, "lat": -8.5069, "lon": 115.2625},
            {"name": "Tirta Empul water temple", "area": "Tampaksiring", "kind": "History", "time": "Afternoon Leisure", "cost": 75000, "lat": -8.4151, "lon": 115.3150},
            {"name": "Sunset seafood on Jimbaran beach", "area": "Jimbaran", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 250000, "lat": -8.7680, "lon": 115.1650},
            {"name": "Campuhan Ridge stroll", "area": "Ubud", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 0, "lat": -8.4992, "lon": 115.2540},
            {"name": "Balinese cooking class", "area": "Ubud", "kind": "Food", "time": "Morning Sightseeing", "cost": 350000, "lat": -8.5100, "lon": 115.2650},
        ],
    },
    "Phuket": {
        "country": "Thailand", "currency": "THB", "vibes": ["coastal", "adventure", "relaxed"],
        "best_months": [11, 12, 1, 2, 3, 4], "budget": "moderate", "tags": ["Andaman coast", "Island-hopping", "Night markets"],
        "stops": [
            {"name": "Wat Chalong temple grounds", "area": "Chalong", "kind": "History", "time": "Morning Sightseeing", "cost": 0, "lat": 7.8467, "lon": 98.3370},
            {"name": "Old Town street-food lunch", "area": "Phuket Old Town", "kind": "Food", "time": "Lunch Recommendation", "cost": 280, "lat": 7.8840, "lon": 98.3890},
            {"name": "Kata Beach afternoon", "area": "Kata", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 0, "lat": 7.8200, "lon": 98.2990},
            {"name": "Seafood dinner by Rawai", "area": "Rawai", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 900, "lat": 7.7790, "lon": 98.3260},
            {"name": "Karon viewpoint walk", "area": "Karon", "kind": "Adventure", "time": "Morning Sightseeing", "cost": 0, "lat": 7.8290, "lon": 98.3030},
            {"name": "Phuket Weekend Night Market", "area": "Phuket Old Town", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 100, "lat": 7.8790, "lon": 98.3780},
        ],
    },
    "Kathmandu": {
        "country": "Nepal", "currency": "NPR", "vibes": ["mountains", "cultural", "adventure"],
        "best_months": [3, 4, 5, 9, 10, 11], "budget": "budget", "tags": ["Himalayan trailheads", "Temple squares", "Mountain air"],
        "stops": [
            {"name": "Swayambhunath hilltop stupa", "area": "Swayambhu", "kind": "History", "time": "Morning Sightseeing", "cost": 200, "lat": 27.7149, "lon": 85.2906},
            {"name": "Tibetan momo lunch in Boudha", "area": "Boudha", "kind": "Food", "time": "Lunch Recommendation", "cost": 450, "lat": 27.7215, "lon": 85.3620},
            {"name": "Garden of Dreams pause", "area": "Thamel", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 400, "lat": 27.7132, "lon": 85.3150},
            {"name": "Newari dinner in Patan", "area": "Patan", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 1200, "lat": 27.6727, "lon": 85.3250},
            {"name": "Pashupatinath riverside complex", "area": "Gaushala", "kind": "History", "time": "Morning Sightseeing", "cost": 1000, "lat": 27.7104, "lon": 85.3488},
            {"name": "Patan Durbar Square", "area": "Patan", "kind": "History", "time": "Afternoon Leisure", "cost": 1000, "lat": 27.6729, "lon": 85.3255},
        ],
    },
    "New York": {
        "country": "United States", "currency": "USD", "vibes": ["urban", "cultural", "nightlife"],
        "best_months": [4, 5, 6, 9, 10], "budget": "luxury", "tags": ["Neighborhood-hopping", "Broadway", "Iconic skyline"],
        "stops": [
            {"name": "The Met & Central Park edge", "area": "Upper East Side", "kind": "History", "time": "Morning Sightseeing", "cost": 30, "lat": 40.7794, "lon": -73.9632},
            {"name": "Chelsea Market lunch", "area": "Chelsea", "kind": "Food", "time": "Lunch Recommendation", "cost": 28, "lat": 40.7424, "lon": -74.0061},
            {"name": "High Line stroll", "area": "Chelsea", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 0, "lat": 40.7480, "lon": -74.0048},
            {"name": "West Village dinner & jazz", "area": "West Village", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 95, "lat": 40.7358, "lon": -74.0036},
            {"name": "Brooklyn Bridge & DUMBO", "area": "Brooklyn", "kind": "Adventure", "time": "Morning Sightseeing", "cost": 0, "lat": 40.7033, "lon": -73.9894},
            {"name": "Tenement Museum", "area": "Lower East Side", "kind": "History", "time": "Afternoon Leisure", "cost": 30, "lat": 40.7188, "lon": -73.9900},
        ],
    },
    "Istanbul": {
        "country": "Türkiye", "currency": "TRY", "vibes": ["cultural", "history", "foodie"],
        "best_months": [4, 5, 9, 10], "budget": "moderate", "tags": ["Two-continent energy", "Bazaar culture", "Waterfront sunsets"],
        "stops": [
            {"name": "Hagia Sophia & Sultanahmet", "area": "Sultanahmet", "kind": "History", "time": "Morning Sightseeing", "cost": 850, "lat": 41.0086, "lon": 28.9802},
            {"name": "Spice Bazaar lunch bites", "area": "Eminönü", "kind": "Food", "time": "Lunch Recommendation", "cost": 450, "lat": 41.0165, "lon": 28.9700},
            {"name": "Galata & Karaköy lanes", "area": "Karaköy", "kind": "Leisure", "time": "Afternoon Leisure", "cost": 250, "lat": 41.0247, "lon": 28.9744},
            {"name": "Bosphorus-side meze dinner", "area": "Beşiktaş", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 1300, "lat": 41.0430, "lon": 29.0020},
            {"name": "Topkapı Palace", "area": "Sultanahmet", "kind": "History", "time": "Morning Sightseeing", "cost": 1500, "lat": 41.0115, "lon": 28.9833},
            {"name": "Ferry to Kadıköy market", "area": "Kadıköy", "kind": "Adventure", "time": "Afternoon Leisure", "cost": 100, "lat": 40.9906, "lon": 29.0277},
        ],
    },
    "Dubai": {
        "country": "United Arab Emirates", "currency": "AED", "vibes": ["urban", "luxury", "adventure"],
        "best_months": [11, 12, 1, 2, 3], "budget": "luxury", "tags": ["Desert nights", "Architecture", "Big-city sparkle"],
        "stops": [
            {"name": "Al Fahidi historic district", "area": "Bur Dubai", "kind": "History", "time": "Morning Sightseeing", "cost": 0, "lat": 25.2630, "lon": 55.3000},
            {"name": "Old Dubai creekside lunch", "area": "Deira", "kind": "Food", "time": "Lunch Recommendation", "cost": 65, "lat": 25.2700, "lon": 55.3050},
            {"name": "Museum of the Future", "area": "Trade Centre", "kind": "Adventure", "time": "Afternoon Leisure", "cost": 149, "lat": 25.2192, "lon": 55.2820},
            {"name": "Dinner at Dubai Marina", "area": "Dubai Marina", "kind": "Nightlife", "time": "Evening Dining & Entertainment", "cost": 180, "lat": 25.0805, "lon": 55.1403},
            {"name": "Desert conservation evening", "area": "Dubai Desert", "kind": "Adventure", "time": "Afternoon Leisure", "cost": 350, "lat": 24.9000, "lon": 55.5000},
            {"name": "Jumeirah beach morning", "area": "Jumeirah", "kind": "Leisure", "time": "Morning Sightseeing", "cost": 0, "lat": 25.2048, "lon": 55.2708},
        ],
    },
}

SLOT_ORDER = [
    "Morning Sightseeing",
    "Lunch Recommendation",
    "Afternoon Leisure",
    "Evening Dining & Entertainment",
]

VIBE_ALIASES = {
    "beach": {"coastal", "beach"},
    "mountains": {"mountains", "mountain", "adventure"},
    "food-focused": {"food", "foodie"},
    "relaxed": {"relaxed", "coastal"},
}


def estimate_usd(amount: float, currency: str) -> float:
    return amount / CURRENCY_RATES.get(currency, 1.0)


def _distance(left: dict[str, Any], right: dict[str, Any]) -> float:
    lat1, lat2 = math.radians(left["lat"]), math.radians(right["lat"])
    delta_lat = lat2 - lat1
    delta_lon = math.radians(right["lon"] - left["lon"])
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(haversine))


def recommend_destinations(vibe: str, budget: str, month: int, interests: list[str]) -> list[dict[str, Any]]:
    scores = []
    vibe_key = vibe.lower()
    desired_vibes = VIBE_ALIASES.get(vibe_key, {vibe_key})
    for city, info in CITIES.items():
        score = 2 if desired_vibes.intersection(info["vibes"]) or vibe_key in city.lower() else 0
        score += 2 if info["budget"] == budget.lower() else 0
        score += 2 if month in info["best_months"] else 0
        matching = [interest for interest in interests if any(interest.lower() in tag.lower() or tag.lower() in interest.lower() for tag in info["tags"])]
        score += min(len(matching), 2)
        scores.append((score, city, info))
    mood_matches = [item for item in scores if desired_vibes.intersection(item[2]["vibes"])]
    candidates = mood_matches if len(mood_matches) >= 3 else scores
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [
        {"city": city, "country": info["country"], "score": score, "tags": info["tags"], "reason": _recommendation_reason(info, vibe_key, budget, month)}
        for score, city, info in candidates[:3]
    ]


def _recommendation_reason(info: dict[str, Any], vibe: str, budget: str, month: int) -> str:
    desired_vibes = VIBE_ALIASES.get(vibe, {vibe})
    mood = "matches your travel mood" if desired_vibes.intersection(info["vibes"]) else "offers a fresh take on your travel mood"
    season = "is in a favorable travel season" if month in info["best_months"] else "has plenty to explore year-round"
    price = "fits your budget profile" if info["budget"] == budget.lower() else "has options across price points"
    return f"This destination {mood}, {season}, and {price}."


def _cluster_day(stops: list[dict[str, Any]], used_names: set[str]) -> list[dict[str, Any]]:
    by_slot = [[stop for stop in stops if stop["time"] == slot] for slot in SLOT_ORDER]
    if any(not candidates for candidates in by_slot):
        return [next(stop for stop in stops if stop["time"] == slot) for slot in SLOT_ORDER]

    candidates = itertools.product(*by_slot)
    return min(
        candidates,
        key=lambda route: sum(_distance(route[index], route[index + 1]) for index in range(len(route) - 1))
        + 30 * sum(stop["name"] in used_names for stop in route),
    )


def generate_demo_itinerary(destination: str, days: int, interests: list[str], budget: str, party: str) -> list[dict[str, Any]]:
    info = CITIES[destination]
    all_stops = info["stops"]
    preferred = [stop for stop in all_stops if not interests or stop["kind"].lower() in {item.lower() for item in interests}]
    pool = preferred + [stop for stop in all_stops if stop not in preferred]
    itinerary: list[dict[str, Any]] = []
    used_names: set[str] = set()
    budget_factor = {"Budget": 0.8, "Moderate": 1.0, "Luxury": 1.45}.get(budget, 1.0)
    party_factor = 1.0 if party == "Solo" else 1.7 if party == "Couple" else 2.5 if party == "Family" else 2.0
    for day_number in range(1, days + 1):
        selected = _cluster_day(pool, used_names)
        used_names.update(stop["name"] for stop in selected)
        activities = []
        for slot, stop in zip(SLOT_ORDER, selected):
            cost = round(stop["cost"] * budget_factor * party_factor)
            activities.append({
                "slot": slot, "name": stop["name"], "area": stop["area"], "kind": stop["kind"],
                "description": f"Explore {stop['area']} with an easy connection to the next stop.",
                "cost_local": cost, "currency": info["currency"],
                "cost_usd": round(estimate_usd(cost, info["currency"]), 2),
            })
        itinerary.append({"day": day_number, "title": f"Day {day_number} · {selected[0]['area']} and nearby", "activities": activities})
    return add_running_totals(itinerary)


def add_running_totals(itinerary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    running_usd = 0.0
    running_local: dict[str, float] = {}
    for day in itinerary:
        for activity in day.get("activities", []):
            running_usd += float(activity.get("cost_usd", 0))
            currency = activity.get("currency", "USD")
            running_local[currency] = running_local.get(currency, 0.0) + float(activity.get("cost_local", 0))
            activity["running_local"] = round(running_local[currency], 2)
            activity["running_usd"] = round(running_usd, 2)
            activity["running_inr"] = round(running_usd * 83, 0)
    return itinerary


def _extract_json(text: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("The AI response did not contain a JSON itinerary.")
    return json.loads(cleaned[start : end + 1])


def generate_ai_itinerary(
    provider: str,
    api_key: str,
    destination: str,
    days: int,
    interests: list[str],
    budget: str,
    party: str,
    pace: str,
    dates: str,
) -> list[dict[str, Any]]:
    info = CITIES[destination]
    prompt = f"""Create a realistic {days}-day itinerary for {destination}, {info['country']} ({dates}).
Travel party: {party}. Budget: {budget}. Pace: {pace}. Interests: {', '.join(interests) or 'general discovery'}.
Use these local places as grounding and keep each day geographically clustered, minimizing backtracking: {json.dumps(info['stops'], ensure_ascii=False)}.
Return ONLY a JSON array with exactly {days} objects. Each object must have integer day, string title, and activities array with exactly these sequential slots: {json.dumps(SLOT_ORDER)}.
Each activity object must include slot, name, area, kind, description, cost_local (number, per trip party), currency ("{info['currency']}"), and cost_usd (number). No markdown or extra keys are needed."""

    if provider == "Gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        response = requests.post(
            url,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.6}},
            timeout=35,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.6},
            timeout=35,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]

    result = _extract_json(text)
    if not isinstance(result, list) or len(result) != days:
        raise ValueError("The AI returned an itinerary with an unexpected number of days.")
    for index, day in enumerate(result, start=1):
        activities = day.get("activities", [])
        if len(activities) != 4 or [activity.get("slot") for activity in activities] != SLOT_ORDER:
            raise ValueError(f"The AI response for day {index} does not have the required four time slots.")
        for activity in activities:
            activity["currency"] = info["currency"]
            activity["cost_local"] = max(0, float(activity.get("cost_local", 0)))
            activity["cost_usd"] = max(0, float(activity.get("cost_usd", estimate_usd(activity["cost_local"], info["currency"]))))
        day["day"] = index
    return add_running_totals(result)


def replace_activity(day: dict[str, Any], slot: str, request_text: str, destination: str) -> dict[str, Any]:
    info = CITIES[destination]
    lowered = request_text.lower()
    if "vegetarian" in lowered or "vegan" in lowered:
        name, kind, cost = f"Vegetarian-friendly meal near {day['activities'][1]['area']}", "Food", 14
    elif "outdoor" in lowered or "market" in lowered:
        name, kind, cost = f"Open-air market walk in {day['activities'][2]['area']}", "Leisure", 8
    elif "museum" in lowered or "history" in lowered:
        name, kind, cost = f"Local history museum in {day['activities'][0]['area']}", "History", 18
    elif "nature" in lowered or "park" in lowered or "hike" in lowered:
        name, kind, cost = f"Greenway and viewpoint near {day['activities'][2]['area']}", "Adventure", 6
    else:
        name, kind, cost = f"A fresh local experience in {day['activities'][0]['area']}", "Leisure", 12
    if info["currency"] != "USD":
        cost = round(cost * CURRENCY_RATES[info["currency"]])
    updated = {**day, "activities": [dict(activity) for activity in day["activities"]]}
    activity = next(item for item in updated["activities"] if item["slot"] == slot)
    activity.update({
        "name": name, "kind": kind, "description": f"A tailored swap: {request_text.strip()}.",
        "cost_local": cost, "currency": info["currency"], "cost_usd": round(estimate_usd(cost, info["currency"]), 2),
    })
    return updated


def trip_total_usd(itinerary: list[dict[str, Any]]) -> float:
    return round(sum(float(activity.get("cost_usd", 0)) for day in itinerary for activity in day.get("activities", [])), 2)


def as_trip_date(value: date | None) -> str:
    return value.isoformat() if value else "Dates flexible"
