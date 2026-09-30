import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.adapters.imd_adapter import IMDAdapter
from backend.app.services.adapters.osm_adapter import OSMAdapter
from backend.app.services.adapters.bhuvan_adapter import BhuvanAdapter
from backend.app.services.ingestion_service import IngestionService


class TestIngestionCore(unittest.TestCase):
    """Test suite for external data adapters, validation, error handling, and ingestion orchestration."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.service = IngestionService()
        self.imd_adapter = IMDAdapter()
        self.osm_adapter = OSMAdapter()
        self.bhuvan_adapter = BhuvanAdapter()

    # ==========================================================================
    # 1. Configuration & Security
    # ==========================================================================
    def test_configuration_safe_defaults(self):
        """Verifies ingestion settings load safe defaults and secrets default to None."""
        self.assertIsNotNone(settings.IMD_API_URL)
        self.assertIsNotNone(settings.OVERPASS_API_URL)
        self.assertIsNotNone(settings.BHUVAN_WMS_URL)
        self.assertIsNotNone(settings.ELEVATION_API_URL)
        self.assertGreater(settings.INGESTION_TIMEOUT_SECONDS, 0)
        self.assertGreater(settings.DEFAULT_BUFFER_METERS, 0.0)

        # API keys must default to None unless explicitly set via environment
        if not settings.IMD_API_KEY:
            self.assertIsNone(settings.IMD_API_KEY)
        if not settings.ELEVATION_API_KEY:
            self.assertIsNone(settings.ELEVATION_API_KEY)

    # ==========================================================================
    # 2. IMD Adapter Normalization & Validation
    # ==========================================================================
    def test_imd_adapter_normalize_valid_payload(self):
        """Tests conversion of raw IMD AWS JSON telemetry into structured weather and rainfall records."""
        sample_raw = {
            "records": [
                {
                    "station_id": "IMD_MAH_001",
                    "station_name": "Mahad Agri-AWS",
                    "district_name": "Raigad",
                    "temperature_c": 28.5,
                    "humidity_percent": 88.0,
                    "wind_speed_kmh": 14.2,
                    "weather_condition": "Heavy Rain",
                    "warning_level": "Orange",
                    "warning_text": "Localized cloudburst potential in foothill sector",
                    "rainfall_24h_mm": 145.0,
                    "rainfall_72h_mm": 280.0,
                    "rainfall_anomaly_percent": 42.5,
                    "observed_at": "2026-09-11T12:00:00Z",
                    "latitude": 18.082,
                    "longitude": 73.425,
                }
            ]
        }

        normalized = self.imd_adapter.normalize(sample_raw)
        self.assertIn("weather", normalized)
        self.assertIn("rainfall", normalized)
        self.assertEqual(len(normalized["weather"]), 1)
        self.assertEqual(len(normalized["rainfall"]), 1)

        w = normalized["weather"][0]
        self.assertEqual(w["station_id"], "IMD_MAH_001")
        self.assertEqual(w["district_name"], "Raigad")
        self.assertEqual(w["temperature_c"], 28.5)
        self.assertEqual(w["warning_level"], "Orange")
        self.assertIsNotNone(w["coordinates"])
        self.assertEqual(w["coordinates"], (73.425, 18.082))  # (lon, lat)

        r = normalized["rainfall"][0]
        self.assertEqual(r["rainfall_24h_mm"], 145.0)
        self.assertEqual(r["rainfall_72h_mm"], 280.0)
        self.assertEqual(r["rainfall_anomaly_percent"], 42.5)

        # Validation passes
        validated = self.imd_adapter.validate(normalized)
        self.assertEqual(len(validated["weather"]), 1)
        self.assertEqual(len(validated["rainfall"]), 1)

    def test_imd_adapter_rejects_invalid_values(self):
        """Tests that physically implausible values (temperature > 60, humidity > 100) are filtered out."""
        invalid_raw = {
            "records": [
                {
                    "station_id": "IMD_BAD_001",
                    "district_name": "Raigad",
                    "temperature_c": 120.0,  # Physically impossible ambient temp
                    "humidity_percent": 150.0,  # Invalid humidity
                    "rainfall_24h_mm": -10.0,  # Negative rainfall impossible
                    "observed_at": "2026-09-11T12:00:00Z",
                }
            ]
        }
        normalized = self.imd_adapter.normalize(invalid_raw)
        validated = self.imd_adapter.validate(normalized)

        # Weather record rejected due to out-of-range temperature
        self.assertEqual(len(validated["weather"]), 0)

    # ==========================================================================
    # 3. IMD Error Handling (Timeout & HTTP Failures)
    # ==========================================================================
    @patch("httpx.AsyncClient.get")
    def test_imd_adapter_timeout_handling(self, mock_get):
        """Verifies that network timeouts raise TimeoutError without unhandled crash."""
        import asyncio
        mock_get.side_effect = httpx.TimeoutException("Read timed out")

        with self.assertRaises(TimeoutError):
            asyncio.run(self.imd_adapter.fetch())

    @patch("httpx.AsyncClient.get")
    def test_imd_adapter_http_error_handling(self, mock_get):
        """Verifies that non-200 responses raise RuntimeError."""
        import asyncio
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with self.assertRaises(RuntimeError):
            asyncio.run(self.imd_adapter.fetch())

    # ==========================================================================
    # 4. OSM Overpass Normalization
    # ==========================================================================
    def test_osm_adapter_normalize_infrastructure(self):
        """Tests normalization of hospitals, schools, roads, and waterways from Overpass elements."""
        sample_osm = {
            "elements": [
                {
                    "type": "node",
                    "id": 1234567,
                    "lat": 18.085,
                    "lon": 73.430,
                    "tags": {
                        "amenity": "hospital",
                        "name": "Sub-District Hospital Mahad",
                        "beds": "60",
                        "addr:district": "Raigad",
                    },
                },
                {
                    "type": "way",
                    "id": 8901234,
                    "geometry": [
                        {"lat": 18.080, "lon": 73.420},
                        {"lat": 18.085, "lon": 73.425},
                        {"lat": 18.090, "lon": 73.430},
                    ],
                    "tags": {
                        "highway": "primary",
                        "name": "NH-66 Mumbai-Goa Highway",
                        "surface": "asphalt",
                    },
                },
                {
                    "type": "way",
                    "id": 9999001,
                    "geometry": [
                        {"lat": 18.070, "lon": 73.410},
                        {"lat": 18.075, "lon": 73.415},
                    ],
                    "tags": {
                        "waterway": "river",
                        "name": "Savitri River",
                    },
                },
            ]
        }

        normalized = self.osm_adapter.normalize(sample_osm)
        self.assertEqual(len(normalized), 3)

        # Check hospital node
        hosp = next(f for f in normalized if f["feature_type"] == "hospital")
        self.assertEqual(hosp["id"], "osm:node:1234567")
        self.assertEqual(hosp["name"], "Sub-District Hospital Mahad")
        self.assertEqual(hosp["capacity_or_beds"], 60)
        self.assertEqual(hosp["coordinates"], (73.430, 18.085))

        # Check road way
        road = next(f for f in normalized if f["feature_type"] == "road")
        self.assertEqual(road["id"], "osm:way:8901234")
        self.assertTrue(road["all_weather_access"])
        self.assertEqual(road["geometry_type"], "LINESTRING")
        self.assertEqual(len(road["coordinates"]), 3)

        # Check river
        river = next(f for f in normalized if f["feature_type"] == "waterway")
        self.assertEqual(river["id"], "osm:way:9999001")
        self.assertEqual(river["feature_type"], "waterway")

        # Validation passes
        validated = self.osm_adapter.validate(normalized)
        self.assertEqual(len(validated), 3)

    # ==========================================================================
    # 5. Bhuvan Adapter Metadata
    # ==========================================================================
    def test_bhuvan_adapter_wms_layer_metadata(self):
        """Verifies that Bhuvan produces structured WMS layer configurations for Leaflet without assuming JSON."""
        mock_raw = {"is_live": True, "status_code": 200}
        layers = self.bhuvan_adapter.normalize(mock_raw)
        self.assertGreater(len(layers), 0)

        first = layers[0]
        self.assertIn("layer_id", first)
        self.assertIn("wms_url", first)
        self.assertIn("wms_options", first)
        self.assertEqual(first["wms_options"]["format"], "image/png")
        self.assertTrue(first["wms_options"]["transparent"])

    # ==========================================================================
    # 6. Ingestion Service Orchestration & Idempotency
    # ==========================================================================
    def test_ingestion_service_idempotent_sync_imd(self):
        """Tests that repeated ingestion of identical observations updates rather than creates uncontrolled duplicates."""
        mock_payload = {
            "records": [
                {
                    "station_id": "STN_TEST_001",
                    "station_name": "Test Station",
                    "district_name": "Raigad",
                    "temperature_c": 26.0,
                    "rainfall_24h_mm": 50.0,
                    "rainfall_72h_mm": 110.0,
                    "observed_at": "2026-09-11T08:00:00Z",
                    "latitude": 18.05,
                    "longitude": 73.40,
                }
            ]
        }

        # Mock adapter fetch
        with patch.object(self.service.imd_adapter, "fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_payload

            import asyncio
            # First sync run
            res1 = asyncio.run(self.service.sync_imd())
            self.assertIn(res1["status"], ("completed", "partial"))

            # Second sync run with same data
            res2 = asyncio.run(self.service.sync_imd())
            self.assertIn(res2["status"], ("completed", "partial"))

            # If DB is active, second run updates records instead of duplicating
            if self.service._is_db_active():
                self.assertGreaterEqual(res2["records_updated"], 1)

    def test_ingestion_service_handles_fetch_failure_gracefully(self):
        """Tests that complete fetch failure marks run as 'failed' without corrupting system state."""
        with patch.object(self.service.imd_adapter, "fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = TimeoutError("Connection refused")

            import asyncio
            res = asyncio.run(self.service.sync_imd())
            self.assertEqual(res["status"], "failed")
            self.assertIn("error_summary", res)
            self.assertIsNotNone(res["error_summary"])

    # ==========================================================================
    # 7. Ingestion API Endpoints
    # ==========================================================================
    def test_get_ingestion_status_api(self):
        """Tests GET /api/v1/ingestion/status returns complete data provenance and sources."""
        response = self.client.get("/api/v1/ingestion/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("status", data)
        self.assertIn("databaseConnected", data)
        self.assertIn("dataProvenanceMode", data)
        self.assertIn("summary", data)
        self.assertIn("sources", data)
        self.assertGreaterEqual(len(data["sources"]), 3)

        source_ids = [s["id"] for s in data["sources"]]
        self.assertIn("IMD", source_ids)
        self.assertIn("OSM_OVERPASS", source_ids)
        self.assertIn("BHUVAN_NRSC", source_ids)

    def test_post_sync_imd_api_mocked(self):
        """Tests POST /api/v1/ingestion/sync/imd endpoint."""
        with patch("backend.app.api.v1.endpoints.ingestion.ingestion_service.sync_imd", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "run_id": "run_test_imd",
                "source": "IMD",
                "status": "completed",
                "records_ingested": 10,
                "records_updated": 0,
                "records_failed": 0,
                "error_summary": None,
                "completed_at": "2026-09-11T20:00:00Z",
            }
            response = self.client.post("/api/v1/ingestion/sync/imd", json={"district": "Raigad"})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["run_id"], "run_test_imd")
            self.assertEqual(data["source"], "IMD")
            self.assertEqual(data["records_ingested"], 10)

    def test_post_sync_osm_api_mocked(self):
        """Tests POST /api/v1/ingestion/sync/osm endpoint."""
        with patch("backend.app.api.v1.endpoints.ingestion.ingestion_service.sync_osm", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "run_id": "run_test_osm",
                "source": "OSM_OVERPASS",
                "status": "completed",
                "records_ingested": 25,
                "records_updated": 0,
                "records_failed": 0,
                "error_summary": None,
                "completed_at": "2026-09-11T20:00:00Z",
            }
            response = self.client.post("/api/v1/ingestion/sync/osm", json={"bbox": [18.0, 73.0, 18.5, 73.5]})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["run_id"], "run_test_osm")
            self.assertEqual(data["source"], "OSM_OVERPASS")
            self.assertEqual(data["records_ingested"], 25)

    def test_post_sync_bhuvan_api_mocked(self):
        """Tests POST /api/v1/ingestion/sync/bhuvan endpoint."""
        with patch("backend.app.api.v1.endpoints.ingestion.ingestion_service.sync_bhuvan", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                "run_id": "run_test_bhuvan",
                "source": "BHUVAN_NRSC",
                "status": "completed",
                "records_ingested": 3,
                "records_updated": 0,
                "records_failed": 0,
                "error_summary": None,
                "completed_at": "2026-09-11T20:00:00Z",
            }
            response = self.client.post("/api/v1/ingestion/sync/bhuvan")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["run_id"], "run_test_bhuvan")
            self.assertEqual(data["source"], "BHUVAN_NRSC")


if __name__ == "__main__":
    unittest.main()
