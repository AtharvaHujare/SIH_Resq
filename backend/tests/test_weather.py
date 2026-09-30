import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import httpx

from backend.app.main import app
from backend.app.api.v1.endpoints.weather import CITY_COORDINATES, WMO_WEATHER_CODES


class TestWeatherEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_weather_guwahati_success(self):
        """Verify GET /api/v1/weather?city=Guwahati returns Open-Meteo data or fallback."""
        response = self.client.get("/api/v1/weather?city=Guwahati")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["city"], "Guwahati")
        self.assertIn("temperatureC", data)
        self.assertIn("humidityPercent", data)
        self.assertIn("precipitationMm", data)
        self.assertIn("weatherCondition", data)
        self.assertIn("observedAt", data)
        self.assertIn("source", data)
        self.assertIn("provenance", data)
        if not data["isFallback"]:
            self.assertEqual(data["source"], "Open-Meteo")
            self.assertEqual(data["provenance"], "EXTERNAL WEATHER DATA")

    def test_get_weather_pune_success(self):
        """Verify GET /api/v1/weather?city=Pune returns correct city weather."""
        response = self.client.get("/api/v1/weather?city=Pune")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["city"], "Pune")
        self.assertIn("temperatureC", data)

    def test_get_weather_fallback_on_network_error(self):
        """Verify graceful prototype fallback when Open-Meteo API is unreachable."""
        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            response = self.client.get("/api/v1/weather?city=Guwahati")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["city"], "Guwahati")
            self.assertTrue(data["isFallback"])
            self.assertEqual(data["source"], "Prototype Baseline")
            self.assertEqual(data["provenance"], "Weather unavailable — Prototype / Demo fallback")


if __name__ == "__main__":
    unittest.main()
