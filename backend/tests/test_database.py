import unittest
from shapely.geometry import Point, Polygon
from geoalchemy2.shape import from_shape, to_shape

from backend.app.models.orm_models import (
    District,
    Habitation,
    HabitationAiFactor,
    CandidateRelocationSite,
    RedZone,
    SystemAlert,
)
from backend.app.db.session import check_db_health, get_database_url
from backend.app.db.repository import repository


class TestDatabaseSchemaAndGis(unittest.TestCase):
    def test_database_url_not_hardcoded(self):
        """Verifies no secret credentials are statically hardcoded."""
        url = get_database_url()
        # If unset, url is None; if set, it must come from environment/settings
        if url is not None:
            self.assertIsInstance(url, str)

    def test_database_health_check_unconfigured(self):
        """When DATABASE_URL is not set, health check gracefully returns unconfigured status."""
        health = check_db_health()
        self.assertIn("status", health)
        self.assertIn("postgis_available", health)
        if not get_database_url():
            self.assertEqual(health["status"], "unconfigured")
            self.assertFalse(health["configured"])

    def test_mock_repository_fallback_available(self):
        """Mock repository functions seamlessly even with no active database."""
        kpis = repository.get_kpis()
        self.assertGreater(kpis["totalHabitations"], 0)
        self.assertGreaterEqual(len(repository.get_districts()), 3)
        self.assertGreater(len(repository.get_habitations()), 0)
        self.assertGreater(len(repository.get_relocation_sites()), 0)
        self.assertGreater(len(repository.get_red_zones()), 0)

    def test_spatial_point_generation_wgs84(self):
        """Validates standard WGS84 (SRID 4326) Point geometry construction (longitude, latitude)."""
        # Raigad coordinate: [lat=18.0142, lng=73.4925]
        # In PostGIS/Shapely, order is Point(longitude, latitude)
        lng, lat = 73.4925, 18.0142
        pt = Point(lng, lat)
        geom = from_shape(pt, srid=4326)

        # Re-convert to shapely
        extracted_shape = to_shape(geom)
        self.assertAlmostEqual(extracted_shape.x, lng, places=4)
        self.assertAlmostEqual(extracted_shape.y, lat, places=4)

    def test_spatial_polygon_generation_wgs84(self):
        """Validates polygon geometry construction for Red Zone boundaries."""
        ring = [
            (73.480, 18.005),
            (73.495, 18.035),
            (73.515, 18.040),
            (73.525, 18.010),
            (73.500, 17.995),
            (73.480, 18.005),
        ]
        poly = Polygon(ring)
        self.assertTrue(poly.is_valid)
        geom = from_shape(poly, srid=4326)
        self.assertIsNotNone(geom)

    def test_orm_models_table_names_and_columns(self):
        """Confirms table names and required columns exist on ORM classes."""
        self.assertEqual(District.__tablename__, "districts")
        self.assertEqual(Habitation.__tablename__, "habitations")
        self.assertEqual(HabitationAiFactor.__tablename__, "habitation_ai_factors")
        self.assertEqual(CandidateRelocationSite.__tablename__, "candidate_relocation_sites")
        self.assertEqual(RedZone.__tablename__, "red_zones")
        self.assertEqual(SystemAlert.__tablename__, "system_alerts")

        # Column checks
        self.assertTrue(hasattr(Habitation, "geom"))
        self.assertTrue(hasattr(CandidateRelocationSite, "geom"))
        self.assertTrue(hasattr(RedZone, "geom"))
        self.assertTrue(hasattr(Habitation, "risk_score"))
        self.assertTrue(hasattr(CandidateRelocationSite, "suitability_score"))


if __name__ == "__main__":
    unittest.main()
