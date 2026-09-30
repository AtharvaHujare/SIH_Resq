import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Query

from backend.app.db.repository import _normalize_district

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Meteorological & Weather Engine"])

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_TIMEOUT_SECONDS = 8.0

# Supported demo cities coordinate mapping
CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    "guwahati": {"name": "Guwahati", "lat": 26.1445, "lon": 91.7362},
    "pune": {"name": "Pune", "lat": 18.5204, "lon": 73.8567},
    "raigad": {"name": "Raigad", "lat": 18.2357, "lon": 73.4447},
}

# WMO Weather interpretation codes (WW)
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Dense Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snow Fall",
    73: "Moderate Snow Fall",
    75: "Heavy Snow Fall",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}

# Static baseline fallback dataset if Open-Meteo is unavailable
CITY_PROTOTYPE_FALLBACKS: Dict[str, Dict[str, Any]] = {
    "guwahati": {
        "city": "Guwahati",
        "district": "Guwahati",
        "temperatureC": 28.4,
        "humidityPercent": 86,
        "precipitationMm": 0.0,
        "rainMm": 0.0,
        "weatherCode": 63,
        "weatherCondition": "Moderate Rain",
        "windSpeedKmh": 18.0,
        "observedAt": "2026-09-11T18:00:00Z",
        "source": "Prototype Baseline",
        "provenance": "Weather unavailable — prototype fallback",
        "isFallback": True,
    },
    "pune": {
        "city": "Pune",
        "district": "Pune",
        "temperatureC": 24.2,
        "humidityPercent": 78,
        "precipitationMm": 0.0,
        "rainMm": 0.0,
        "weatherCode": 3,
        "weatherCondition": "Overcast",
        "windSpeedKmh": 22.5,
        "observedAt": "2026-09-11T17:30:00Z",
        "source": "Prototype Baseline",
        "provenance": "Weather unavailable — prototype fallback",
        "isFallback": True,
    },
    "raigad": {
        "city": "Raigad",
        "district": "Raigad",
        "temperatureC": 26.5,
        "humidityPercent": 92,
        "precipitationMm": 0.0,
        "rainMm": 0.0,
        "weatherCode": 65,
        "weatherCondition": "Heavy Rain",
        "windSpeedKmh": 26.0,
        "observedAt": "2026-09-11T18:00:00Z",
        "source": "Prototype Baseline",
        "provenance": "Weather unavailable — prototype fallback",
        "isFallback": True,
    },
}


@router.get("", summary="Get city weather and rainfall telemetry from Open-Meteo")
async def get_city_weather(
    city: Optional[str] = Query(default=None, description="City name (e.g. Guwahati, Pune, Raigad)"),
    district: Optional[str] = Query(default=None, description="District name (alias for city)"),
) -> Dict[str, Any]:
    """Retrieve real-world weather and rainfall telemetry from the Open-Meteo API.
    
    1. Maps city to latitude/longitude
    2. Calls Open-Meteo forecast API (current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m)
    3. Normalizes response into clean JSON
    4. Includes source="Open-Meteo", provenance="EXTERNAL WEATHER DATA", and observed_at
    5. Falls back seamlessly to prototype baseline if Open-Meteo is unavailable.
    """
    raw_name = city or district or "Guwahati"
    clean_name = _normalize_district(raw_name) or "guwahati"
    dist_key = clean_name.lower().strip()

    # Find matching city coordinates
    matched_key = "guwahati"
    if "pune" in dist_key:
        matched_key = "pune"
    elif "raigad" in dist_key:
        matched_key = "raigad"
    elif dist_key in CITY_COORDINATES:
        matched_key = dist_key

    coords = CITY_COORDINATES[matched_key]
    city_display_name = coords["name"]

    try:
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
            "timezone": "auto",
        }

        async with httpx.AsyncClient(timeout=OPEN_METEO_TIMEOUT_SECONDS) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})
        weather_code = current.get("weather_code", 0)
        weather_condition = WMO_WEATHER_CODES.get(weather_code, "Normal Meteorological Conditions")

        return {
            "city": city_display_name,
            "district": city_display_name,
            "temperatureC": current.get("temperature_2m"),
            "humidityPercent": current.get("relative_humidity_2m"),
            "precipitationMm": current.get("precipitation", 0.0),
            "rainMm": current.get("rain", 0.0),
            "weatherCode": weather_code,
            "weatherCondition": weather_condition,
            "windSpeedKmh": current.get("wind_speed_10m"),
            "observedAt": current.get("time"),
            "observed_at": current.get("time"),
            "source": "Open-Meteo",
            "provenance": "EXTERNAL WEATHER DATA",
            "isFallback": False,
            "attribution": "Weather data by Open-Meteo.com",
        }

    except Exception as exc:
        logger.warning(
            "Open-Meteo API query failed for %s (%s). Falling back to prototype data: %s",
            city_display_name,
            matched_key,
            exc,
        )
        fallback = dict(CITY_PROTOTYPE_FALLBACKS.get(matched_key, CITY_PROTOTYPE_FALLBACKS["guwahati"]))
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        fallback["city"] = city_display_name
        fallback["district"] = city_display_name
        fallback["source"] = "Prototype Baseline"
        fallback["provenance"] = "Weather unavailable — Prototype / Demo fallback"
        fallback["observedAt"] = now_ts
        fallback["observed_at"] = now_ts
        fallback["isFallback"] = True
        fallback["attribution"] = "Weather data by Open-Meteo.com"
        return fallback
