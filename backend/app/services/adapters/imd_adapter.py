import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx

from backend.app.core.config import settings
from backend.app.services.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class IMDAdapter(BaseAdapter):
    """Adapter for India Meteorological Department (IMD) telemetry, rainfall, and district warnings."""

    SOURCE_ID = "IMD"
    SOURCE_NAME = "India Meteorological Department"

    def __init__(self):
        super().__init__(source_id=self.SOURCE_ID, name=self.SOURCE_NAME)
        self.api_url = getattr(settings, "IMD_API_URL", "https://mausam.imd.gov.in/api")
        self.api_key = getattr(settings, "IMD_API_KEY", None)
        self.timeout = getattr(settings, "INGESTION_TIMEOUT_SECONDS", 15)

    async def fetch(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch weather/rainfall observations from configured IMD endpoint."""
        query_params = params or {}
        headers = {
            "Accept": "application/json",
            "User-Agent": "SIH2026-DSS-Ingestor/1.0",
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = f"{self.api_url.rstrip('/')}/observations"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=query_params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            logger.warning("IMD API timeout after %ss: %s", self.timeout, exc)
            raise TimeoutError(f"IMD API connection timed out: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("IMD API responded with HTTP %s: %s", exc.response.status_code, exc)
            raise RuntimeError(f"IMD API error {exc.response.status_code}: {exc}") from exc
        except Exception as exc:
            logger.warning("Failed to fetch from IMD API: %s", exc)
            raise ConnectionError(f"IMD connection failed: {exc}") from exc

    def _parse_timestamp(self, ts_val: Any) -> Optional[datetime]:
        """Safely parse various datetime formats into UTC datetime."""
        if not ts_val:
            return None
        if isinstance(ts_val, datetime):
            return ts_val.astimezone(timezone.utc) if ts_val.tzinfo else ts_val
        if isinstance(ts_val, (int, float)):
            try:
                # Check for millisecond timestamp
                if ts_val > 1e11:
                    ts_val /= 1000.0
                return datetime.fromtimestamp(ts_val, tz=timezone.utc)
            except Exception:
                return None

        ts_str = str(ts_val).strip()
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(ts_str, fmt)
                return dt.astimezone(timezone.utc) if dt.tzinfo else dt
            except ValueError:
                continue
        return None

    def normalize(self, raw_data: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Normalize raw IMD JSON response into structured weather and rainfall records.
        
        Returns:
            Dict containing 'weather' and 'rainfall' lists of dictionaries.
        """
        weather_records = []
        rainfall_records = []

        if not raw_data:
            return {"weather": weather_records, "rainfall": rainfall_records}

        # Handle various response envelope patterns: { "data": [...] } or direct list
        items = []
        if isinstance(raw_data, list):
            items = raw_data
        elif isinstance(raw_data, dict):
            items = (
                raw_data.get("data")
                or raw_data.get("stations")
                or raw_data.get("observations")
                or raw_data.get("records")
                or [raw_data]
            )

        if not isinstance(items, list):
            items = [items]

        now_utc = datetime.now(timezone.utc)

        for item in items:
            if not isinstance(item, dict):
                continue

            station_id = str(
                item.get("station_id")
                or item.get("stationId")
                or item.get("StationId")
                or item.get("station_code")
                or item.get("id")
                or ""
            ).strip()

            district_name = str(
                item.get("district_name")
                or item.get("district")
                or item.get("District")
                or item.get("city")
                or ""
            ).strip()

            station_name = str(
                item.get("station_name")
                or item.get("StationName")
                or item.get("station")
                or item.get("name")
                or station_id
            ).strip()

            if not station_id or not district_name:
                continue

            observed_at = self._parse_timestamp(
                item.get("observed_at")
                or item.get("timestamp")
                or item.get("DateTime")
                or item.get("observation_time")
                or item.get("date")
            ) or now_utc

            # Extract spatial coordinates if available
            lat = item.get("latitude") or item.get("lat") or item.get("Lat")
            lon = item.get("longitude") or item.get("lon") or item.get("lng") or item.get("Lon")
            coords = None
            if lat is not None and lon is not None:
                try:
                    flat, flon = float(lat), float(lon)
                    if 6.0 <= flat <= 38.0 and 68.0 <= flon <= 98.0:
                        coords = (flon, flat)  # (lon, lat) for PostGIS / Shapely
                except (ValueError, TypeError):
                    coords = None

            # 1. Weather observation normalization
            temp = item.get("temperature_c") or item.get("temp") or item.get("temperature") or item.get("Temperature")
            hum = item.get("humidity_percent") or item.get("humidity") or item.get("Humidity") or item.get("rh")
            wind = item.get("wind_speed_kmh") or item.get("wind_speed") or item.get("windSpeed")
            cond = item.get("weather_condition") or item.get("condition") or item.get("weather") or "Normal"
            warn_lvl = item.get("warning_level") or item.get("warning") or item.get("alert_level") or "Green"
            warn_txt = item.get("warning_text") or item.get("warning_desc") or item.get("description") or ""

            try:
                f_temp = float(temp) if temp is not None else None
            except (ValueError, TypeError):
                f_temp = None

            try:
                f_hum = float(hum) if hum is not None else None
            except (ValueError, TypeError):
                f_hum = None

            try:
                f_wind = float(wind) if wind is not None else None
            except (ValueError, TypeError):
                f_wind = None

            weather_records.append({
                "source_id": self.SOURCE_ID,
                "district_name": district_name,
                "station_id": station_id,
                "station_name": station_name,
                "temperature_c": f_temp,
                "humidity_percent": f_hum,
                "wind_speed_kmh": f_wind,
                "weather_condition": str(cond),
                "warning_level": str(warn_lvl).capitalize(),
                "warning_text": str(warn_txt),
                "observed_at": observed_at,
                "ingested_at": now_utc,
                "is_fallback": False,
                "coordinates": coords,
            })

            # 2. Rainfall observation normalization
            rf_24h = (
                item.get("rainfall_24h_mm")
                or item.get("rainfall_24h")
                or item.get("rf_24h")
                or item.get("rainfall")
                or item.get("Rainfall")
                or 0.0
            )
            rf_72h = (
                item.get("rainfall_72h_mm")
                or item.get("rainfall_72h")
                or item.get("rainfall_3d")
                or item.get("rf_72h")
                or 0.0
            )
            rf_anomaly = (
                item.get("rainfall_anomaly_percent")
                or item.get("rainfall_anomaly")
                or item.get("anomaly")
                or 0.0
            )

            try:
                f_rf24 = max(0.0, float(rf_24h))
            except (ValueError, TypeError):
                f_rf24 = 0.0

            try:
                f_rf72 = max(0.0, float(rf_72h))
            except (ValueError, TypeError):
                f_rf72 = f_rf24

            try:
                f_anom = float(rf_anomaly)
            except (ValueError, TypeError):
                f_anom = 0.0

            rainfall_records.append({
                "source_id": self.SOURCE_ID,
                "district_name": district_name,
                "station_id": station_id,
                "station_name": station_name,
                "rainfall_24h_mm": f_rf24,
                "rainfall_72h_mm": f_rf72,
                "rainfall_anomaly_percent": f_anom,
                "observed_at": observed_at,
                "ingested_at": now_utc,
                "is_fallback": False,
                "coordinates": coords,
            })

        return {"weather": weather_records, "rainfall": rainfall_records}

    def validate(self, records_dict: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Filter out physically invalid or incomplete records."""
        valid_weather = []
        valid_rainfall = []

        weather_list = records_dict.get("weather", []) if isinstance(records_dict, dict) else []
        rainfall_list = records_dict.get("rainfall", []) if isinstance(records_dict, dict) else []

        for rec in weather_list:
            if not rec.get("station_id") or not rec.get("district_name") or not rec.get("observed_at"):
                continue
            # Validate temperature range (-20 to +60 C)
            t = rec.get("temperature_c")
            if t is not None and not (-20.0 <= t <= 60.0):
                continue
            # Validate humidity (0 to 100%)
            h = rec.get("humidity_percent")
            if h is not None and not (0.0 <= h <= 100.0):
                continue
            valid_weather.append(rec)

        for rec in rainfall_list:
            if not rec.get("station_id") or not rec.get("district_name") or not rec.get("observed_at"):
                continue
            # Rainfall cannot be negative; extreme 24h cloudburst upper bound ~ 1500mm
            rf24 = rec.get("rainfall_24h_mm", 0.0)
            if not (0.0 <= rf24 <= 1500.0):
                continue
            valid_rainfall.append(rec)

        return {"weather": valid_weather, "rainfall": valid_rainfall}

    async def health_check(self) -> Dict[str, Any]:
        """Check availability of configured IMD endpoint."""
        if not self.api_url:
            return {"configured": False, "status": "unconfigured", "message": "IMD_API_URL not set"}

        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5)) as client:
                res = await client.get(self.api_url)
                is_ok = res.status_code < 500
                return {
                    "configured": True,
                    "status": "healthy" if is_ok else "unhealthy",
                    "http_status": res.status_code,
                    "message": "Endpoint reached successfully" if is_ok else "Endpoint returned error",
                }
        except Exception as exc:
            return {
                "configured": True,
                "status": "unreachable",
                "error": str(exc),
                "message": "Failed to connect to IMD endpoint",
            }
