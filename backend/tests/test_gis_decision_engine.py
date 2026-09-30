import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.gis_engine import gis_engine
from backend.app.services.risk_engine import risk_engine, RiskEngine
from backend.app.services.capacity_engine import capacity_engine, CapacityEngine


class TestGisDecisionEngine(unittest.TestCase):
    """Test suite for Phase 3: Core Data-Driven GIS Decision Engine."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # ==========================================================================
    # 1. Dynamic Red Zones
    # ==========================================================================
    def test_get_red_zones_api_structure(self):
        """Tests GET /api/v1/hazards/red-zones returns valid zones with backward-compatible contracts."""
        response = self.client.get("/api/v1/hazards/red-zones")
        self.assertEqual(response.status_code, 200)
        zones = response.json()
        self.assertIsInstance(zones, list)
        self.assertGreater(len(zones), 0)

        first = zones[0]
        self.assertIn("id", first)
        self.assertIn("name", first)
        self.assertIn("hazardType", first)
        self.assertIn("coordinates", first)
        self.assertIn("isFallback", first)
        self.assertIn("calculationMode", first)
        self.assertIn("dataTimestamp", first)

        # Coordinates format must be Leaflet [[lat, lng], ...]
        coords = first["coordinates"]
        self.assertIsInstance(coords, list)
        self.assertGreaterEqual(len(coords), 3)
        self.assertEqual(len(coords[0]), 2)

    def test_get_red_zones_district_filter(self):
        """Tests district filtering on red-zones endpoint."""
        response = self.client.get("/api/v1/hazards/red-zones?district=Raigad")
        self.assertEqual(response.status_code, 200)
        zones = response.json()
        self.assertGreaterEqual(len(zones), 1)
        valid_keywords = ["raigad", "mahad", "taliye", "varandha", "savitri", "dynamic"]
        for z in zones:
            self.assertTrue(
                any(kw in z["name"].lower() for kw in valid_keywords)
            )

    # ==========================================================================
    # 2. Dynamic Green / Safe Zones (GeoJSON FeatureCollection)
    # ==========================================================================
    def test_get_safe_zones_geojson_validity(self):
        """Tests GET /api/v1/hazards/safe-zones returns standard RFC 7946 GeoJSON FeatureCollection."""
        response = self.client.get("/api/v1/hazards/safe-zones")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data.get("type"), "FeatureCollection")
        self.assertIn("features", data)
        self.assertIn("metadata", data)
        self.assertIsInstance(data["features"], list)

        meta = data["metadata"]
        self.assertIn("totalSafeZones", meta)
        self.assertIn("calculationMode", meta)
        self.assertIn("fallbackUsed", meta)

        if data["features"]:
            feat = data["features"][0]
            self.assertEqual(feat.get("type"), "Feature")
            self.assertIn("geometry", feat)
            self.assertIn("properties", feat)

            geom = feat["geometry"]
            self.assertEqual(geom["type"], "Polygon")
            self.assertIn("coordinates", geom)
            # GeoJSON coordinates format is [[[lon, lat], ...]]
            ring = geom["coordinates"][0]
            self.assertGreaterEqual(len(ring), 3)

            props = feat["properties"]
            self.assertIn("name", props)
            self.assertIn("usableAreaAcres", props)
            self.assertIn("estimatedCapacity", props)
            self.assertIn("grossCapacity", props)
            self.assertIn("limitingFactor", props)
            self.assertIn("slopeDegree", props)
            self.assertIn("suitabilityScore", props)
            self.assertIn("derivationCriteria", props)
            self.assertLessEqual(props["slopeDegree"], 8.0)  # Gentle gradient constraint

    def test_get_safe_zones_district_filter(self):
        """Tests safe-zone generation filtered by administrative corridor."""
        response = self.client.get("/api/v1/hazards/safe-zones?district=Raigad")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(data["metadata"]["district"], "Raigad")

    # ==========================================================================
    # 3. Deterministic Risk Engine
    # ==========================================================================
    def test_deterministic_risk_formula_weights(self):
        """Validates that Composite Risk = 0.45 * H + 0.25 * E + 0.30 * V."""
        # Baseline inputs: H=60, E=50, V=40
        # Expected: 0.45*60 + 0.25*50 + 0.30*40 = 27 + 12.5 + 12 = 51.5 -> tier Moderate
        with patch.object(RiskEngine, "calculate_hazard_index", return_value=60.0):
            with patch.object(RiskEngine, "calculate_exposure_index", return_value=50.0):
                with patch.object(RiskEngine, "calculate_vulnerability_index", return_value=40.0):
                    composite, tier, v = RiskEngine.calculate_composite_risk(
                        slope_degree=15.0,
                        rainfall_3d_mm=100.0,
                        rainfall_anomaly_pct=10.0,
                        historical_disasters=2,
                        population=1000,
                        households=200,
                        kutcha_housing_pct=40.0,
                        road_isolation_km=5.0,
                        hospital_distance_km=8.0,
                    )
                    self.assertEqual(composite, 51.5)
                    self.assertEqual(tier, "Moderate")
                    self.assertEqual(v, 40.0)

    def test_deterministic_risk_critical_tier_classification(self):
        """Verifies score >= 75 is classified as Critical."""
        self.assertEqual(RiskEngine.classify_tier(75.0), "Critical")
        self.assertEqual(RiskEngine.classify_tier(84.2), "Critical")
        self.assertEqual(RiskEngine.classify_tier(55.0), "High")
        self.assertEqual(RiskEngine.classify_tier(35.0), "Moderate")
        self.assertEqual(RiskEngine.classify_tier(20.0), "Low")

    def test_rule_based_attribution_without_ml(self):
        """Verifies factors are derived strictly from deterministic rule triggers, never calling ML."""
        data = {
            "slopeDegree": 32.0,                  # Exceeds 28 deg threshold
            "rainfall3dMm": 240.0,                # Exceeds 180mm threshold
            "kutchaHousingPercent": 65.0,         # Exceeds 45% threshold
            "roadIsolationDistanceKm": 12.0,      # Exceeds 8km threshold
            "hospitalDistanceKm": 18.0,           # Exceeds 15km threshold
            "distanceFromRedZoneKm": 0.2,         # Within 0.5km buffer
        }

        factors = RiskEngine.generate_xai_factors(data)
        factor_names = [f["factor"] for f in factors]

        self.assertTrue(any("Slope" in f for f in factor_names))
        self.assertTrue(any("Precipitation" in f for f in factor_names))
        self.assertTrue(any("Kutcha" in f for f in factor_names))
        self.assertTrue(any("Evacuation Road" in f for f in factor_names))
        self.assertTrue(any("Hospital" in f for f in factor_names))
        self.assertTrue(any("Hazard Zone" in f for f in factor_names))

        for f in factors:
            self.assertNotIn("shap", f["description"].lower())
            self.assertNotIn("lime", f["description"].lower())
            self.assertNotIn("model prediction", f["description"].lower())

    def test_missing_factor_graceful_baseline(self):
        """Verifies risk calculation handles missing/None parameters by falling back to documented baselines."""
        # Calculate with minimal parameters
        h = RiskEngine.calculate_hazard_index(
            slope_degree=0.0,
            rainfall_3d_mm=0.0,
            distance_to_red_zone_km=None,  # Missing parameter
        )
        self.assertGreaterEqual(h, 0.0)
        self.assertLessEqual(h, 100.0)

    # ==========================================================================
    # 4. Carrying Capacity & Liebig Law of the Minimum
    # ==========================================================================
    def test_carrying_capacity_water_bottleneck(self):
        """Verifies that when water supply is insufficient, feasible capacity is throttled by water."""
        # Usable area: 90,000 sqm -> Land capacity = 90,000 / 45 = 2,000 people
        # Water supply: 135 kL/day -> Water capacity = 135,000 / 135 = 1,000 people
        # Beds: 10 beds -> Health capacity = 10 * 500 = 5,000 people
        # Feasible should be min(2000, 1000, 5000) = 1,000 people (Water bottleneck)
        result = CapacityEngine.evaluate_carrying_capacity(
            site_capacity=2000,
            target_population=1200,
            potable_water_supply_kl=135.0,
            available_hospital_beds=10,
            usable_area_sqm=90000.0,
        )

        self.assertEqual(result["landCapacity"], 2000)
        self.assertEqual(result["waterCapacity"], 1000)
        self.assertEqual(result["healthCapacity"], 5000)
        self.assertEqual(result["grossCapacity"], 2000)
        self.assertEqual(result["feasibleCapacity"], 1000)
        self.assertIn("Water Supply", result["limitingFactor"])

    def test_carrying_capacity_land_bottleneck(self):
        """Verifies that when land is scarce, feasible capacity is throttled by land area."""
        # Usable area: 22,500 sqm -> Land capacity = 22,500 / 45 = 500 people
        # Water supply: 270 kL/day -> Water capacity = 270,000 / 135 = 2,000 people
        # Beds: 10 beds -> 5,000 people
        # Feasible should be min(500, 2000, 5000) = 500 people (Land bottleneck)
        result = CapacityEngine.evaluate_carrying_capacity(
            site_capacity=500,
            target_population=400,
            potable_water_supply_kl=270.0,
            available_hospital_beds=10,
            usable_area_sqm=22500.0,
        )

        self.assertEqual(result["feasibleCapacity"], 500)
        self.assertIn("Land Area", result["limitingFactor"])

    def test_carrying_capacity_missing_constraints_handling(self):
        """Verifies that if water or beds are 0 or None, the engine does not fabricate fake capacity."""
        result = CapacityEngine.evaluate_carrying_capacity(
            site_capacity=1500,
            target_population=1000,
            potable_water_supply_kl=0.0,     # Unquantified water supply
            available_hospital_beds=None,    # Missing bed data
            usable_area_sqm=67500.0,         # Land = 1500
        )

        self.assertEqual(result["landCapacity"], 1500)
        self.assertIsNone(result["waterCapacity"])
        self.assertIsNone(result["healthCapacity"])
        self.assertEqual(result["feasibleCapacity"], 1500)

    # ==========================================================================
    # 5. Relocation Site API Contract Compatibility
    # ==========================================================================
    def test_relocation_sites_api_enriched_capacity(self):
        """Verifies GET /api/v1/relocation-sites includes enriched carrying capacity metrics."""
        response = self.client.get("/api/v1/relocation-sites")
        self.assertEqual(response.status_code, 200)
        sites = response.json()
        self.assertGreater(len(sites), 0)

        site = sites[0]
        self.assertIn("capacityMetrics", site)
        metrics = site["capacityMetrics"]
        self.assertIn("allocatedPopulation", metrics)
        self.assertIn("maximumAbsorption", metrics)
        self.assertIn("grossCapacity", metrics)
        self.assertIn("feasibleCapacity", metrics)
        self.assertIn("limitingFactor", metrics)


if __name__ == "__main__":
    unittest.main()
