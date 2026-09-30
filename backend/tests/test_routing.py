import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestRoutingEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_routing_guwahati_success(self):
        """Tests that OSRM routing endpoint connects and returns road route between Kharghuli and North Guwahati."""
        response = self.client.get(
            "/api/v1/routing/route",
            params={
                "from_lat": 26.195,
                "from_lon": 91.775,
                "to_lat": 26.235,
                "to_lon": 91.715,
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("source"), "OSRM/OpenStreetMap")
        self.assertGreater(data.get("distance_km"), 0.0)
        self.assertGreater(data.get("duration_minutes"), 0.0)
        self.assertIn("geometry", data)
        self.assertEqual(data["geometry"].get("type"), "LineString")
        self.assertGreater(len(data["geometry"].get("coordinates")), 10)

    def test_routing_invalid_coordinates(self):
        """Tests coordinate validation for out-of-range latitude."""
        response = self.client.get(
            "/api/v1/routing/route",
            params={
                "from_lat": 95.0,  # Invalid latitude > 90
                "from_lon": 91.775,
                "to_lat": 26.235,
                "to_lon": 91.715,
            }
        )
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()
