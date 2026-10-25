"""FastAPI service for the travel planner."""

from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv

from pdf_export import build_itinerary_pdf
from travel_core import (
    CITIES,
    add_running_totals,
    generate_ai_itinerary,
    generate_demo_itinerary,
    recommend_destinations,
    replace_activity,
    trip_total_usd,
)

load_dotenv(Path(__file__).with_name(".env"))

app = FastAPI(title="Personalized Travel Itinerary Planner API", version="1.0.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Session-ID"],
)


class Preferences(BaseModel):
    destination: str | None = None
    vibe: str = "Cultural"
    days: int = Field(default=4, ge=1, le=14)
    start_date: date = Field(default_factory=lambda: date.today() + timedelta(days=21))
    budget: str = "Moderate"
    party: str = "Solo"
    party_size: int | None = Field(default=None, ge=1, le=20)
    pace: str = "Moderate"
    interests: list[str] = Field(default_factory=list)
    dietary_needs: list[str] = Field(default_factory=list)
    provider: str = "Demo mode"
    api_key: SecretStr | None = None


class RecommendationRequest(BaseModel):
    vibe: str = "Cultural"
    budget: str = "Moderate"
    month: int = Field(default_factory=lambda: date.today().month, ge=1, le=12)
    interests: list[str] = Field(default_factory=list)


class SaveTripRequest(BaseModel):
    trip: dict[str, Any]


class MutateItineraryRequest(BaseModel):
    trip: dict[str, Any]
    day: int = Field(ge=1)


class SwapActivityRequest(MutateItineraryRequest):
    slot: str
    request_text: str = Field(min_length=1, max_length=300)


memory_trips: dict[str, list[dict[str, Any]]] = {}


def _jwt_subject(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims.get("sub")
    except (IndexError, ValueError, json.JSONDecodeError):
        return None


def _supabase_client(token: str | None) -> Any | None:
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not anon_key or not token:
        return None
    try:
        from supabase import create_client

        client = create_client(url, anon_key)
        client.postgrest.auth(token)
        return client
    except Exception as error:
        raise HTTPException(status_code=503, detail="Supabase is configured but unavailable.") from error


def _demo_session_key(session_id: str | None) -> str:
    if not session_id or not re.fullmatch(r"[A-Za-z0-9-]{16,80}", session_id):
        raise HTTPException(status_code=400, detail="A valid demo-session ID is required when not signed in.")
    return f"demo:{session_id}"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "itinerary-planner-api"}


@app.get("/api/destinations")
def destinations(
    vibe: str = "Cultural",
    budget: str = "Moderate",
    month: int | None = None,
    interests: list[str] | None = None,
) -> list[dict[str, Any]]:
    return recommend_destinations(vibe, budget, month or date.today().month, interests or [])


@app.post("/api/recommendations")
def recommendations(request: RecommendationRequest) -> list[dict[str, Any]]:
    return recommend_destinations(request.vibe, request.budget, request.month, request.interests)


@app.post("/api/itineraries")
def create_itinerary(preferences: Preferences) -> dict[str, Any]:
    destination = preferences.destination
    if not destination or destination not in CITIES:
        suggestions = recommend_destinations(
            preferences.vibe, preferences.budget, preferences.start_date.month, preferences.interests
        )
        return {"needs_destination": True, "recommendations": suggestions}

    end_date = preferences.start_date + timedelta(days=preferences.days - 1)
    date_label = f"{preferences.start_date.isoformat()} to {end_date.isoformat()}"
    provider = preferences.provider
    key = preferences.api_key.get_secret_value() if preferences.api_key else ""
    if provider in ("Gemini", "Groq") and key:
        try:
            itinerary = generate_ai_itinerary(
                provider, key, destination, preferences.days, preferences.interests, preferences.budget,
                preferences.party, preferences.pace, date_label, preferences.party_size, preferences.dietary_needs,
            )
        except Exception as error:
            raise HTTPException(status_code=502, detail="The selected AI provider could not create a valid itinerary.") from error
    else:
        itinerary = generate_demo_itinerary(
            destination, preferences.days, preferences.interests, preferences.budget, preferences.party,
            party_size=preferences.party_size, dietary_needs=preferences.dietary_needs,
        )
    return {
        "id": str(uuid.uuid4()),
        "destination": destination,
        "country": CITIES[destination]["country"],
        "start_date": preferences.start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": preferences.days,
        "budget": preferences.budget,
        "party": preferences.party,
        "party_size": preferences.party_size,
        "pace": preferences.pace,
        "interests": preferences.interests,
        "dietary_needs": preferences.dietary_needs,
        "currency": CITIES[destination]["currency"],
        "source": provider if provider in ("Gemini", "Groq") and key else "Demo mode",
        "itinerary": itinerary,
        "total_usd": trip_total_usd(itinerary),
    }


@app.post("/api/itineraries/swap")
def swap_activity(request: SwapActivityRequest) -> dict[str, Any]:
    trip = request.trip
    destination = trip.get("destination")
    if destination not in CITIES:
        raise HTTPException(status_code=422, detail="Choose a supported destination before swapping activities.")
    day = next((item for item in trip.get("itinerary", []) if item.get("day") == request.day), None)
    if not day or request.slot not in {item.get("slot") for item in day.get("activities", [])}:
        raise HTTPException(status_code=404, detail="The selected day or time slot does not exist.")
    changed_day = replace_activity(day, request.slot, request.request_text, destination)
    trip["itinerary"] = [changed_day if item.get("day") == request.day else item for item in trip["itinerary"]]
    trip["itinerary"] = add_running_totals(trip["itinerary"])
    trip["total_usd"] = trip_total_usd(trip["itinerary"])
    return trip


@app.post("/api/itineraries/regenerate-day")
def regenerate_day(request: MutateItineraryRequest) -> dict[str, Any]:
    trip = request.trip
    destination = trip.get("destination")
    if destination not in CITIES:
        raise HTTPException(status_code=422, detail="Choose a supported destination before regenerating a day.")
    if not any(item.get("day") == request.day for item in trip.get("itinerary", [])):
        raise HTTPException(status_code=404, detail="The selected day does not exist.")
    replacement = generate_demo_itinerary(
        destination,
        request.day + 1,
        trip.get("interests", []),
        trip.get("budget", "Moderate"),
        trip.get("party", "Solo"),
        trip.get("party_size"),
        trip.get("dietary_needs", []),
    )[-1]
    replacement["day"] = request.day
    replacement["title"] = f"Day {request.day} · refreshed neighborhood plan"
    trip["itinerary"] = [replacement if item.get("day") == request.day else item for item in trip["itinerary"]]
    trip["itinerary"] = add_running_totals(trip["itinerary"])
    trip["total_usd"] = trip_total_usd(trip["itinerary"])
    return trip


@app.post("/api/itineraries/pdf")
def export_pdf(request: SaveTripRequest) -> Any:
    from fastapi.responses import StreamingResponse

    from io import BytesIO

    pdf = build_itinerary_pdf(request.trip)
    filename = f"{request.trip.get('destination', 'trip').lower().replace(' ', '-')}-itinerary.pdf"
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/trips")
def list_trips(
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    token = authorization.removeprefix("Bearer ") if authorization else None
    client = _supabase_client(token)
    if client:
        try:
            result = client.table("itinerary_plans").select("id,trip,created_at").order("created_at", desc=True).execute()
            return [row["trip"] for row in result.data]
        except Exception as error:
            raise HTTPException(status_code=503, detail="Unable to load saved trips from Supabase.") from error
    user_key = _jwt_subject(token) if token else None
    return memory_trips.get(user_key or _demo_session_key(x_session_id), [])


@app.post("/api/trips")
def save_trip(
    request: SaveTripRequest,
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
) -> dict[str, Any]:
    token = authorization.removeprefix("Bearer ") if authorization else None
    client = _supabase_client(token)
    if client:
        user_id = _jwt_subject(token or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="A valid Supabase access token is required.")
        try:
            client.table("itinerary_plans").insert({
                "user_id": user_id,
                "trip_id": request.trip.get("id"),
                "trip": request.trip,
            }).execute()
            return {"saved": True, "storage": "supabase"}
        except Exception as error:
            raise HTTPException(status_code=503, detail="Unable to save this trip to Supabase.") from error
    user_key = _jwt_subject(token) if token else None
    key = user_key or _demo_session_key(x_session_id)
    memory_trips.setdefault(key, []).insert(0, request.trip)
    return {"saved": True, "storage": "memory"}


@app.put("/api/trips/{trip_id}")
def update_trip(
    trip_id: str,
    request: SaveTripRequest,
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
) -> dict[str, Any]:
    if request.trip.get("id") != trip_id:
        raise HTTPException(status_code=422, detail="The trip ID in the URL must match the submitted trip.")
    token = authorization.removeprefix("Bearer ") if authorization else None
    client = _supabase_client(token)
    if client:
        user_id = _jwt_subject(token or "")
        if not user_id:
            raise HTTPException(status_code=401, detail="A valid Supabase access token is required.")
        try:
            result = (
                client.table("itinerary_plans")
                .update({"trip": request.trip})
                .eq("user_id", user_id)
                .eq("trip_id", trip_id)
                .execute()
            )
            if not result.data:
                raise HTTPException(status_code=404, detail="Saved trip was not found.")
            return {"saved": True, "storage": "supabase"}
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=503, detail="Unable to update this trip in Supabase.") from error
    key = _demo_session_key(x_session_id)
    trips = memory_trips.get(key, [])
    for index, saved_trip in enumerate(trips):
        if saved_trip.get("id") == trip_id:
            trips[index] = request.trip
            return {"saved": True, "storage": "memory"}
    raise HTTPException(status_code=404, detail="Saved trip was not found in this demo session.")
