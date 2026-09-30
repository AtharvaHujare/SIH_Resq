import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx

from backend.app.core.config import settings
from backend.app.services.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class OSMAdapter(BaseAdapter):
    """Adapter for OpenStreetMap Overpass API extracting road, river, and shelter infrastructure."""

    SOURCE_ID = "OSM_OVERPASS"
    SOURCE_NAME = "OpenStreetMap Overpass API"

    # Default bounding box: Western Ghats / Raigad / Mahad corridor
    DEFAULT_BBOX = (17.80, 73.20, 18.35, 73.70)  # (min_lat, min_lon, max_lat, max_lon)

    def __init__(self):
        super().__init__(source_id=self.SOURCE_ID, name=self.SOURCE_NAME)
        self.api_url = getattr(settings, "OVERPASS_API_URL", "https://overpass-api.de/api/interpreter")
        self.timeout = getattr(settings, "INGESTION_TIMEOUT_SECONDS", 25)

    def build_overpass_query(self, bbox: Tuple[float, float, float, float]) -> str:
        """Construct Overpass QL query for essential infrastructure elements."""
        min_lat, min_lon, max_lat, max_lon = bbox
        bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"

        return f"""
        [out:json][timeout:{self.timeout}];
        (
          node["amenity"~"^(hospital|clinic|school|community_centre|shelter)$"]({bbox_str});
          way["amenity"~"^(hospital|clinic|school|community_centre|shelter)$"]({bbox_str});
          way["highway"~"^(primary|secondary|tertiary|trunk)$"]({bbox_str});
          way["waterway"~"^(river|stream|canal)$"]({bbox_str});
        );
        out body geom;
        """

    async def fetch(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query Overpass API with bounding box parameters."""
        params = params or {}
        bbox = params.get("bbox") or self.DEFAULT_BBOX
        ql_query = params.get("query") or self.build_overpass_query(bbox)

        headers = {
            "Accept": "application/json",
            "User-Agent": "SIH2026-DSS-OSM-Ingestor/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    data={"data": ql_query},
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            logger.warning("OSM Overpass API query timed out after %ss: %s", self.timeout, exc)
            raise TimeoutError(f"Overpass API timed out: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("OSM Overpass API responded with HTTP %s: %s", exc.response.status_code, exc)
            raise RuntimeError(f"Overpass API returned HTTP {exc.response.status_code}: {exc}") from exc
        except Exception as exc:
            logger.warning("Failed to fetch from OSM Overpass: %s", exc)
            raise ConnectionError(f"OSM Overpass query failed: {exc}") from exc

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize OSM elements into infrastructure_features domain entities."""
        features = []
        if not raw_data or not isinstance(raw_data, dict):
            return features

        elements = raw_data.get("elements", [])
        if not isinstance(elements, list):
            return features

        for el in elements:
            if not isinstance(el, dict):
                continue

            el_type = el.get("type", "node")
            el_id = el.get("id")
            if not el_id:
                continue

            osm_id = f"osm:{el_type}:{el_id}"
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en") or ""

            # Determine feature type
            amenity = tags.get("amenity", "").lower()
            highway = tags.get("highway", "").lower()
            waterway = tags.get("waterway", "").lower()

            if amenity in ("hospital", "clinic"):
                feat_type = "hospital"
            elif amenity in ("school", "college", "kindergarten"):
                feat_type = "school"
            elif amenity in ("community_centre", "shelter", "place_of_worship"):
                feat_type = "shelter"
            elif highway in ("primary", "secondary", "tertiary", "trunk"):
                feat_type = "road"
            elif waterway in ("river", "stream", "canal"):
                feat_type = "waterway"
            else:
                continue

            # Geometry extraction: Point for node or LineString / Polygon for way
            geom_coords = None
            geom_type = "POINT"

            if el_type == "node":
                lat = el.get("lat")
                lon = el.get("lon")
                if lat is not None and lon is not None:
                    geom_coords = (float(lon), float(lat))
                    geom_type = "POINT"
            elif el_type == "way":
                way_geometry = el.get("geometry", [])
                if way_geometry and isinstance(way_geometry, list):
                    # List of {"lat": ..., "lon": ...}
                    coords_list = [
                        (float(pt["lon"]), float(pt["lat"]))
                        for pt in way_geometry
                        if "lon" in pt and "lat" in pt
                    ]
                    if len(coords_list) >= 2:
                        geom_coords = coords_list
                        geom_type = "LINESTRING"
                    elif len(coords_list) == 1:
                        geom_coords = coords_list[0]
                        geom_type = "POINT"
                elif "center" in el:
                    cntr = el["center"]
                    geom_coords = (float(cntr["lon"]), float(cntr["lat"]))
                    geom_type = "POINT"

            if not geom_coords:
                continue

            # Capacity / beds estimate if available in tags
            beds = None
            if "beds" in tags:
                try:
                    beds = int(tags["beds"])
                except (ValueError, TypeError):
                    beds = None
            elif "capacity" in tags:
                try:
                    beds = int(tags["capacity"])
                except (ValueError, TypeError):
                    beds = None

            district = tags.get("addr:district") or tags.get("district") or "Raigad Corridor"

            features.append({
                "id": osm_id,
                "source_id": self.SOURCE_ID,
                "feature_type": feat_type,
                "name": name or f"{feat_type.capitalize()} ({el_id})",
                "district_name": district,
                "capacity_or_beds": beds,
                "all_weather_access": tags.get("surface") not in ("unpaved", "dirt", "mud"),
                "properties_json": tags,
                "coordinates": geom_coords,
                "geometry_type": geom_type,
                "is_fallback": False,
            })

        return features

    def validate(self, normalized_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate structure and bounding geometry of OSM infrastructure records."""
        valid_records = []
        for rec in normalized_records:
            if not rec.get("id") or not rec.get("feature_type") or not rec.get("coordinates"):
                continue

            coords = rec["coordinates"]
            # Validate coordinates are within geographic boundaries
            if rec.get("geometry_type") == "POINT":
                lon, lat = coords
                if not (6.0 <= lat <= 38.0 and 68.0 <= lon <= 98.0):
                    continue
            elif rec.get("geometry_type") == "LINESTRING":
                if not isinstance(coords, list) or len(coords) < 2:
                    continue
                lon, lat = coords[0]
                if not (6.0 <= lat <= 38.0 and 68.0 <= lon <= 98.0):
                    continue

            valid_records.append(rec)

        return valid_records

    async def health_check(self) -> Dict[str, Any]:
        """Check accessibility of OSM Overpass interpreter."""
        if not self.api_url:
            return {"configured": False, "status": "unconfigured", "message": "OVERPASS_API_URL not set"}

        try:
            # Overpass status endpoint
            status_url = self.api_url.replace("/interpreter", "/status")
            async with httpx.AsyncClient(timeout=min(self.timeout, 6)) as client:
                res = await client.get(status_url)
                is_ok = res.status_code == 200
                return {
                    "configured": True,
                    "status": "healthy" if is_ok else "degraded",
                    "http_status": res.status_code,
                    "message": "Overpass interpreter responding",
                }
        except Exception as exc:
            return {
                "configured": True,
                "status": "unreachable",
                "error": str(exc),
                "message": "Overpass interpreter unreachable",
            }
