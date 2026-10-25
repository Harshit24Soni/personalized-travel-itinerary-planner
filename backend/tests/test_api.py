from fastapi.testclient import TestClient

from backend.main import app, memory_trips
from travel_core import CITIES, SLOT_ORDER


client = TestClient(app)


def setup_function() -> None:
    memory_trips.clear()


def test_health_and_mood_matched_recommendations() -> None:
    assert client.get("/api/health").json()["status"] == "ok"
    response = client.post(
        "/api/recommendations",
        json={"vibe": "Beach", "budget": "Moderate", "month": 11, "interests": ["Food"]},
    )
    results = response.json()
    assert response.status_code == 200
    assert len(results) == 3
    assert all("coastal" in CITIES[item["city"]]["vibes"] for item in results)


def test_itinerary_captures_party_and_dietary_needs() -> None:
    response = client.post(
        "/api/itineraries",
        json={
            "destination": "Lisbon",
            "days": 2,
            "start_date": "2026-11-15",
            "budget": "Moderate",
            "party": "Couple",
            "party_size": 2,
            "pace": "Relaxed",
            "interests": ["Food"],
            "dietary_needs": ["Vegetarian"],
        },
    )
    trip = response.json()
    assert response.status_code == 200
    assert len(trip["itinerary"]) == 2
    assert all([activity["slot"] for activity in day["activities"]] == SLOT_ORDER for day in trip["itinerary"])
    lunch = next(activity for activity in trip["itinerary"][0]["activities"] if activity["slot"] == "Lunch Recommendation")
    assert "Vegetarian-friendly" in lunch["name"]
    assert all("running_usd" in activity and "running_inr" in activity for day in trip["itinerary"] for activity in day["activities"])


def test_swap_and_regenerate_preserve_other_days() -> None:
    trip = client.post(
        "/api/itineraries",
        json={"destination": "Lisbon", "days": 3, "start_date": "2026-11-15", "party": "Solo"},
    ).json()
    day_two_before = [
        (activity["name"], activity["area"], activity["cost_local"], activity["cost_usd"])
        for activity in trip["itinerary"][1]["activities"]
    ]
    swapped = client.post(
        "/api/itineraries/swap",
        json={"trip": trip, "day": 1, "slot": "Morning Sightseeing", "request_text": "replace with outdoor market"},
    ).json()
    day_two_after_swap = [
        (activity["name"], activity["area"], activity["cost_local"], activity["cost_usd"])
        for activity in swapped["itinerary"][1]["activities"]
    ]
    assert day_two_after_swap == day_two_before
    assert "market" in swapped["itinerary"][0]["activities"][0]["name"].lower()
    regenerated = client.post("/api/itineraries/regenerate-day", json={"trip": swapped, "day": 1}).json()
    day_two_after_regeneration = [
        (activity["name"], activity["area"], activity["cost_local"], activity["cost_usd"])
        for activity in regenerated["itinerary"][1]["activities"]
    ]
    assert day_two_after_regeneration == day_two_before
    assert [activity["slot"] for activity in regenerated["itinerary"][0]["activities"]] == SLOT_ORDER


def test_pdf_and_demo_trip_history() -> None:
    trip = client.post(
        "/api/itineraries",
        json={"destination": "Kathmandu", "days": 1, "start_date": "2026-11-15", "party": "Solo"},
    ).json()
    pdf = client.post("/api/itineraries/pdf", json={"trip": trip})
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")
    demo_headers = {"X-Session-ID": "session-12345678901234"}
    saved = client.post("/api/trips", json={"trip": trip}, headers=demo_headers)
    assert saved.json() == {"saved": True, "storage": "memory"}
    assert client.get("/api/trips", headers=demo_headers).json() == [trip]
    assert client.get("/api/trips", headers={"X-Session-ID": "session-09876543210987"}).json() == []
    edited_trip = {**trip, "title": "Updated itinerary"}
    updated = client.put(f"/api/trips/{trip['id']}", json={"trip": edited_trip}, headers=demo_headers)
    assert updated.json() == {"saved": True, "storage": "memory"}
    assert client.get("/api/trips", headers=demo_headers).json() == [edited_trip]
