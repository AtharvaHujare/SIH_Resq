import unittest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.db.repository import repository
from backend.app.db.session import check_db_health
from backend.app.main import app


class TestSupabaseReadIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db_health = check_db_health()
        cls.is_live = cls.db_health.get("status") == "healthy"

    def setUp(self):
        # Ensure USE_DATABASE is True by default for tests
        settings.USE_DATABASE = True

    def test_database_connection_and_source_indicator(self):
        """Verifies database health and data_source indicator."""
        if self.is_live:
            self.assertTrue(repository.is_db_enabled)
            self.assertEqual(repository.data_source, "supabase")
        else:
            self.assertEqual(repository.data_source, "mock_fallback")

    def test_get_districts_read(self):
        """Tests GET /api/v1/districts and repository.get_districts()."""
        districts = repository.get_districts()
        self.assertGreaterEqual(len(districts), 3)
        for d in districts:
            self.assertIn("id", d)
            self.assertIn("name", d)
            self.assertIn("habitationsCount", d)

        # Test through FastAPI HTTP client
        response = self.client.get("/api/v1/districts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 3)

    def test_get_habitations_and_gis_coordinates(self):
        """Tests GET /api/v1/habitations and Leaflet [lat, lng] format."""
        habs = repository.get_habitations(limit=25)
        self.assertGreaterEqual(len(habs), 15)

        first = habs[0]
        self.assertIn("coordinates", first)
        self.assertEqual(len(first["coordinates"]), 2)
        lat, lng = first["coordinates"]
        # In India, latitude is approx 8-37 N, longitude is approx 68-98 E
        self.assertGreater(lat, 10.0)
        self.assertLess(lat, 35.0)
        self.assertGreater(lng, 70.0)
        self.assertLess(lng, 98.0)

        # HTTP API
        response = self.client.get("/api/v1/habitations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 15)

    def test_get_habitation_by_id_and_ai_factors(self):
        """Tests GET /api/v1/habitations/{id} with eager-loaded AI factors."""
        h = repository.get_habitation_by_id("HAB_001")
        self.assertIsNotNone(h)
        self.assertEqual(h["id"], "HAB_001")
        self.assertIn("aiFactors", h)
        self.assertGreater(len(h["aiFactors"]), 0)
        self.assertIn("factor", h["aiFactors"][0])

        # HTTP API
        response = self.client.get("/api/v1/habitations/HAB_001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "HAB_001")
        self.assertGreater(len(data["aiFactors"]), 0)

    def test_get_relocation_sites_and_gis_coordinates(self):
        """Tests GET /api/v1/relocation-sites and Leaflet [lat, lng] format."""
        sites = repository.get_relocation_sites()
        self.assertGreaterEqual(len(sites), 5)

        s = sites[0]
        self.assertIn("coordinates", s)
        self.assertEqual(len(s["coordinates"]), 2)
        lat, lng = s["coordinates"]
        self.assertGreater(lat, 10.0)
        self.assertLess(lat, 35.0)
        self.assertGreater(lng, 70.0)
        self.assertLess(lng, 98.0)
        self.assertIn("suitabilityBreakdown", s)
        self.assertIn("capacityMetrics", s)

        # HTTP API
        response = self.client.get("/api/v1/relocation-sites")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 5)

    def test_get_relocation_site_by_id(self):
        """Tests GET /api/v1/relocation-sites/{id}."""
        s = repository.get_relocation_site_by_id("SITE_001")
        self.assertIsNotNone(s)
        self.assertEqual(s["id"], "SITE_001")

        # HTTP API
        response = self.client.get("/api/v1/relocation-sites/SITE_001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "SITE_001")

    def test_get_red_zones_and_polygon_geometry(self):
        """Tests GET /api/v1/hazards/red-zones and polygon coordinates [[lat, lng], ...]."""
        zones = repository.get_red_zones()
        self.assertGreaterEqual(len(zones), 3)

        z = zones[0]
        self.assertIn("coordinates", z)
        coords = z["coordinates"]
        self.assertGreaterEqual(len(coords), 4)  # closed polygon has at least 4 vertices
        # Check first point is [lat, lng]
        pt = coords[0]
        self.assertEqual(len(pt), 2)
        self.assertGreater(pt[0], 10.0)  # lat
        self.assertGreater(pt[1], 70.0)  # lng

        # HTTP API
        response = self.client.get("/api/v1/hazards/red-zones")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 3)

    def test_get_prioritization_queue(self):
        """Tests GET /api/v1/prioritization/queue with candidate site matching."""
        response = self.client.get("/api/v1/prioritization/queue")
        self.assertEqual(response.status_code, 200)
        queue = response.json()
        self.assertGreater(len(queue), 0)
        first = queue[0]
        self.assertIn("priority", first)
        self.assertIn("recommendedSite", first)

    def test_get_analytics_kpis(self):
        """Tests GET /api/v1/analytics/kpis."""
        response = self.client.get("/api/v1/analytics/kpis")
        self.assertEqual(response.status_code, 200)
        kpis = response.json()
        self.assertGreaterEqual(kpis["totalHabitations"], 15)
        self.assertGreaterEqual(kpis["districtsMonitored"], 3)
        self.assertIn("averageSuitabilityScore", kpis)

    def test_get_analytics_risk_distribution(self):
        """Tests GET /api/v1/analytics/risk-distribution."""
        response = self.client.get("/api/v1/analytics/risk-distribution")
        self.assertEqual(response.status_code, 200)
        risk = response.json()
        self.assertIn("distribution", risk)
        self.assertIn("hazardContributions", risk)
        self.assertIn("districtComparisons", risk)

    def test_get_alerts(self):
        """Tests GET /api/v1/alerts."""
        response = self.client.get("/api/v1/alerts")
        self.assertEqual(response.status_code, 200)
        alerts = response.json()
        self.assertEqual(len(alerts), 4)

    def test_unified_search(self):
        """Tests GET /api/v1/search."""
        response = self.client.get("/api/v1/search?q=Taliye")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("habitations", data)
        self.assertIn("sites", data)
        self.assertIn("redZones", data)
        self.assertGreater(len(data["habitations"]), 0)

    def test_graceful_fallback_when_db_disabled(self):
        """Verifies repository seamlessly falls back to mock data when USE_DATABASE is False."""
        settings.USE_DATABASE = False
        try:
            self.assertFalse(repository.is_db_enabled)
            self.assertEqual(repository.data_source, "mock_fallback")

            districts = repository.get_districts()
            self.assertGreaterEqual(len(districts), 3)

            habs = repository.get_habitations()
            self.assertGreaterEqual(len(habs), 15)

            kpis = repository.get_kpis()
            self.assertEqual(kpis["totalHabitations"], 1248)
        finally:
            settings.USE_DATABASE = True


if __name__ == "__main__":
    unittest.main()
