import logging
from typing import Dict, Any, Optional
import httpx
from fastapi import APIRouter, Query, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routing", tags=["Road Network & Evacuation Routing"])

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
OSRM_TIMEOUT_SECONDS = 10.0


@router.get("/route", summary="Compute real-world road evacuation route using OSRM")
async def get_road_route(
    from_lat: float = Query(..., description="Origin latitude", ge=-90.0, le=90.0),
    from_lon: float = Query(..., description="Origin longitude", ge=-180.0, le=180.0),
    to_lat: float = Query(..., description="Destination latitude", ge=-90.0, le=90.0),
    to_lon: float = Query(..., description="Destination longitude", ge=-180.0, le=180.0),
) -> Dict[str, Any]:
    """Computes an authoritative road-network evacuation/relocation route via OSRM.

    Accepts origin and destination coordinates (lat, lon), queries the OSRM driving engine
    using coordinate format (lon,lat), and returns full GeoJSON route geometry, travel distance,
    and estimated driving time.
    """
    # Format for OSRM URL: {lon},{lat};{lon},{lat}
    coordinates_str = f"{from_lon},{from_lat};{to_lon},{to_lat}"
    osrm_url = f"{OSRM_BASE_URL}/{coordinates_str}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT_SECONDS) as client:
            headers = {"User-Agent": "SIH-Relocation-DSS/2.0 (Relocation Planning Platform)"}
            response = await client.get(osrm_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("OSRM returned non-OK status: %s", data.get("code"))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OSRM routing failed: {data.get('message', 'No valid route found')}",
            )

        best_route = data["routes"][0]
        distance_meters = best_route.get("distance", 0.0)
        duration_seconds = best_route.get("duration", 0.0)
        geometry = best_route.get("geometry", {})

        # Extract high-level turn-by-turn steps summary if present
        steps_summary = []
        legs = best_route.get("legs", [])
        if legs and "steps" in legs[0]:
            for step in legs[0]["steps"]:
                name = step.get("name") or "Connecting Road"
                maneuver = step.get("maneuver", {}).get("type", "")
                modifier = step.get("maneuver", {}).get("modifier", "")
                step_dist = round(step.get("distance", 0.0) / 1000, 2)
                if step_dist > 0:
                    steps_summary.append({
                        "instruction": f"{maneuver.capitalize()} {modifier} onto {name}".strip(),
                        "distanceKm": step_dist,
                    })

        return {
            "status": "success",
            "source": "OSRM/OpenStreetMap",
            "distance_km": round(distance_meters / 1000.0, 2),
            "distanceKm": round(distance_meters / 1000.0, 2),
            "duration_minutes": round(duration_seconds / 60.0, 1),
            "durationMinutes": round(duration_seconds / 60.0, 1),
            "geometry": geometry,
            "origin": {"lat": from_lat, "lon": from_lon},
            "destination": {"lat": to_lat, "lon": to_lon},
            "steps": steps_summary[:10],  # Top maneuver steps
            "provenance": "EXTERNAL_OSRM_ROUTING",
        }

    except httpx.HTTPError as exc:
        logger.error("OSRM HTTP connection error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to OSRM routing service: {exc}",
        )
    except Exception as exc:
        logger.error("Unexpected error during route calculation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route calculation error: {exc}",
        )
