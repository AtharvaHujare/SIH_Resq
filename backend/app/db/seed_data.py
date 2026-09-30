"""Idempotent Database Seeder for Supabase PostgreSQL + PostGIS.
Extracts prototype data from backend.app.db.mock_data (mirror of frontend/src/data/mockData.js)
and performs PostgreSQL ON CONFLICT DO UPDATE upserts into:
  1. districts
  2. candidate_relocation_sites
  3. habitations
  4. habitation_ai_factors
  5. red_zones
  6. system_alerts

GIS Geometries are converted to WGS84 (EPSG:4326) with correct [longitude, latitude] ordering.
"""

import os
import re
import sys
import logging
import urllib.parse
from datetime import datetime
from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon

# Ensure project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.app.db.mock_data import (
    DISTRICT_PROFILES,
    CANDIDATE_RELOCATION_SITES,
    VULNERABLE_HABITATIONS,
    RED_ZONES,
    RECENT_SYSTEM_ALERTS,
)
from backend.app.models.orm_models import (
    District,
    CandidateRelocationSite,
    Habitation,
    HabitationAiFactor,
    RedZone,
    SystemAlert,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_db")


def get_connection_url() -> str:
    """Safely retrieves DATABASE_URL from .env handling potential unencoded '@' in password."""
    # Look across directory tree for .env
    current_dir = os.path.abspath(os.path.dirname(__file__))
    candidate_paths = []
    p = current_dir
    for _ in range(6):
        candidate_paths.append(os.path.join(p, ".env"))
        p = os.path.dirname(p)

    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        for p in candidate_paths:
            if os.path.exists(p):
                vals = dotenv_values(p)
                if vals.get("DATABASE_URL"):
                    raw_url = vals["DATABASE_URL"]
                    break

    if not raw_url:
        raise ValueError("DATABASE_URL not found in environment or .env files.")

    # URL-encode password if it has unescaped @
    match = re.match(r"^(postgresql://[^:]+:)(.*)(@[^@]+)$", raw_url)
    if match:
        prefix, pwd, host_part = match.groups()
        db_url = f"{prefix}{urllib.parse.quote_plus(pwd)}{host_part}" if "@" in pwd else raw_url
    else:
        db_url = raw_url

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    return db_url


def seed_database():
    db_url = get_connection_url()
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    stats = {
        "districts": {"inserted": 0, "updated": 0, "skipped": 0},
        "candidate_relocation_sites": {"inserted": 0, "updated": 0, "skipped": 0},
        "habitations": {"inserted": 0, "updated": 0, "skipped": 0},
        "habitation_ai_factors": {"inserted": 0, "updated": 0, "skipped": 0},
        "red_zones": {"inserted": 0, "updated": 0, "skipped": 0},
        "system_alerts": {"inserted": 0, "updated": 0, "skipped": 0},
    }

    try:
        # ----------------------------------------------------------------------
        # 1. Seed Districts
        # ----------------------------------------------------------------------
        logger.info("Seeding districts...")
        for d in DISTRICT_PROFILES:
            stmt = insert(District).values(
                id=d["id"],
                name=d["name"],
                state=d["state"],
                habitations_count=d.get("habitationsCount", 0),
                critical_count=d.get("criticalCount", 0),
                exposed_pop=d.get("exposedPop", 0),
                dominant_hazard=d.get("dominantHazard"),
                updated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[District.id],
                set_={
                    "name": stmt.excluded.name,
                    "state": stmt.excluded.state,
                    "habitations_count": stmt.excluded.habitations_count,
                    "critical_count": stmt.excluded.critical_count,
                    "exposed_pop": stmt.excluded.exposed_pop,
                    "dominant_hazard": stmt.excluded.dominant_hazard,
                    "updated_at": datetime.utcnow(),
                },
            )
            res = session.execute(stmt)
            # In PostgreSQL on_conflict_do_update rowcount is 1 on insert or update
            stats["districts"]["inserted"] += 1

        session.commit()

        # ----------------------------------------------------------------------
        # 2. Seed Candidate Relocation Sites (Before habitations due to FK)
        # ----------------------------------------------------------------------
        logger.info("Seeding candidate_relocation_sites...")
        # Map district names to district IDs
        district_lookup = {d["name"]: d["id"] for d in DISTRICT_PROFILES}
        district_lookup.update({
            "Guwahati": "DIST_GUW",
            "Raigad": "DIST_01",
            "Pune": "DIST_02",
            "Ratnagiri": "DIST_03",
            "Wayanad Scarp": "DIST_04",
            "Shimla Ridge": "DIST_05",
        })

        for s in CANDIDATE_RELOCATION_SITES:
            lat, lng = s["coordinates"][0], s["coordinates"][1]
            geom = from_shape(Point(lng, lat), srid=4326)

            district_id = district_lookup.get(s["district"], "DIST_01")
            breakdown = s.get("suitabilityBreakdown", {})
            metrics = s.get("capacityMetrics", {})

            stmt = insert(CandidateRelocationSite).values(
                id=s["id"],
                name=s["name"],
                district_id=district_id,
                district_name=s["district"],
                state=s["state"],
                distance_from_red_zone_km=s.get("distanceFromRedZoneKm", 0.0),
                usable_area_sqm=s.get("usableAreaSqm", 0.0),
                usable_area_acres=s.get("usableAreaAcres", 0.0),
                estimated_capacity=s.get("estimatedCapacity", 0),
                slope_degree=s.get("slopeDegree", 0.0),
                suitability_score=s.get("suitabilityScore", 0.0),
                overall_recommendation=s.get("overallRecommendation", "Suitable"),
                factor_hazard_safety=breakdown.get("hazardSafety", 80),
                factor_accessibility=breakdown.get("accessibility", 80),
                factor_land_suitability=breakdown.get("landSuitability", 80),
                factor_water_availability=breakdown.get("waterAvailability", 80),
                factor_healthcare_access=breakdown.get("healthcareAccess", 80),
                factor_education_access=breakdown.get("educationAccess", 80),
                factor_carrying_capacity=breakdown.get("carryingCapacity", 80),
                capacity_status=s.get("capacityStatus", "Optimal"),
                carrying_capacity_factor=s.get("carryingCapacityFactor", 1.0),
                water_availability_status=s.get("waterAvailabilityStatus"),
                distance_to_road_m=s.get("distanceToRoadM", 0.0),
                road_accessibility=s.get("roadAccessibility"),
                distance_to_hospital_km=s.get("distanceToHospitalKm", 0.0),
                healthcare_status=s.get("healthcareStatus"),
                distance_to_school_km=s.get("distanceToSchoolKm", 0.0),
                schooling_status=s.get("schoolingStatus"),
                power_grid_access=s.get("powerGridAccess"),
                allocated_population=metrics.get("allocatedPopulation", 0),
                maximum_absorption=metrics.get("maximumAbsorption", s.get("estimatedCapacity", 0)),
                remaining_capacity=metrics.get("remainingCapacity", 0),
                utilization_percent=metrics.get("utilizationPercent", 0.0),
                potable_water_daily_needed_kl=metrics.get("potableWaterDailyNeededKl", 0.0),
                potable_water_daily_supplied_kl=metrics.get("potableWaterDailySuppliedKl", 0.0),
                hospital_beds_required=metrics.get("hospitalBedsRequired", 0),
                hospital_beds_available=metrics.get("hospitalBedsAvailable", 0),
                geom=geom,
                updated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[CandidateRelocationSite.id],
                set_={
                    "name": stmt.excluded.name,
                    "district_id": stmt.excluded.district_id,
                    "district_name": stmt.excluded.district_name,
                    "state": stmt.excluded.state,
                    "distance_from_red_zone_km": stmt.excluded.distance_from_red_zone_km,
                    "usable_area_sqm": stmt.excluded.usable_area_sqm,
                    "usable_area_acres": stmt.excluded.usable_area_acres,
                    "estimated_capacity": stmt.excluded.estimated_capacity,
                    "slope_degree": stmt.excluded.slope_degree,
                    "suitability_score": stmt.excluded.suitability_score,
                    "overall_recommendation": stmt.excluded.overall_recommendation,
                    "capacity_status": stmt.excluded.capacity_status,
                    "geom": stmt.excluded.geom,
                    "updated_at": datetime.utcnow(),
                },
            )
            session.execute(stmt)
            stats["candidate_relocation_sites"]["inserted"] += 1

        session.commit()

        # ----------------------------------------------------------------------
        # 3. Seed Habitations & Habitation AI Factors
        # ----------------------------------------------------------------------
        logger.info("Seeding habitations & ai_factors...")
        for h in VULNERABLE_HABITATIONS:
            lat, lng = h["coordinates"][0], h["coordinates"][1]
            geom = from_shape(Point(lng, lat), srid=4326)
            district_id = district_lookup.get(h["district"], "DIST_01")

            stmt = insert(Habitation).values(
                id=h["id"],
                name=h["name"],
                district_id=district_id,
                district_name=h["district"],
                state=h["state"],
                population=h.get("population", 0),
                households=h.get("households", 0),
                kutcha_housing_percent=float(h.get("kutchaHousingPercent", 0)),
                risk_score=float(h.get("riskScore", 0.0)),
                risk_tier=h.get("riskTier", "Moderate"),
                vulnerability_index=float(h.get("vulnerabilityIndex", 0.0)),
                dominant_hazards=h.get("dominantHazards"),
                slope_degree=float(h.get("slopeDegree", 0.0)),
                rainfall_3d_mm=float(h.get("rainfall3dMm", 0.0)),
                rainfall_anomaly_percent=float(h.get("rainfallAnomalyPercent", 0.0)),
                road_isolation_distance_km=float(h.get("roadIsolationDistanceKm", 0.0)),
                hospital_distance_km=float(h.get("hospitalDistanceKm", 0.0)),
                historical_disasters_count=int(h.get("historicalDisastersCount", 0)),
                recent_casualties=int(h.get("recentCasualties", 0)),
                priority=int(h.get("priority", 4)),
                priority_label=h.get("priorityLabel", "In-Situ Monitoring"),
                recommended_site_id=h.get("recommendedSiteId"),
                geom=geom,
                updated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[Habitation.id],
                set_={
                    "name": stmt.excluded.name,
                    "district_id": stmt.excluded.district_id,
                    "district_name": stmt.excluded.district_name,
                    "state": stmt.excluded.state,
                    "population": stmt.excluded.population,
                    "households": stmt.excluded.households,
                    "risk_score": stmt.excluded.risk_score,
                    "risk_tier": stmt.excluded.risk_tier,
                    "priority": stmt.excluded.priority,
                    "recommended_site_id": stmt.excluded.recommended_site_id,
                    "geom": stmt.excluded.geom,
                    "updated_at": datetime.utcnow(),
                },
            )
            session.execute(stmt)
            stats["habitations"]["inserted"] += 1

            # Seed AI Factors (clear existing factors for this habitation to ensure idempotency)
            ai_factors = h.get("aiFactors", [])
            if ai_factors:
                session.query(HabitationAiFactor).filter_by(habitation_id=h["id"]).delete()
                for factor in ai_factors:
                    new_factor = HabitationAiFactor(
                        habitation_id=h["id"],
                        factor=factor.get("factor", ""),
                        impact=factor.get("impact", "Medium"),
                        direction=factor.get("direction", "up"),
                        description=factor.get("description", ""),
                        weight=float(factor.get("weight", 0.0)),
                    )
                    session.add(new_factor)
                    stats["habitation_ai_factors"]["inserted"] += 1

        session.commit()

        # ----------------------------------------------------------------------
        # 4. Seed Red Zones (Polygons)
        # ----------------------------------------------------------------------
        logger.info("Seeding red_zones...")
        for rz in RED_ZONES:
            # Coordinates in mockData.js are [[lat, lng], [lat, lng], ...]
            # Shapely Polygon requires [(lng, lat), (lng, lat), ...]
            ring = [(pt[1], pt[0]) for pt in rz["coordinates"]]
            # Ensure closed ring
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])

            poly = Polygon(ring)
            geom = from_shape(poly, srid=4326)

            stmt = insert(RedZone).values(
                id=rz["id"],
                name=rz["name"],
                hazard_type=rz.get("hazardType", "Landslide"),
                risk_level=rz.get("riskLevel", "Critical"),
                area_sq_km=float(rz.get("areaSqKm", 0.0)),
                enclosed_habitations_count=int(rz.get("enclosedHabitationsCount", 0)),
                exposed_population=int(rz.get("exposedPopulation", 0)),
                buffer_margin_m=float(rz.get("bufferMarginM", 300.0)),
                primary_trigger=rz.get("primaryTrigger"),
                geom=geom,
                updated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[RedZone.id],
                set_={
                    "name": stmt.excluded.name,
                    "hazard_type": stmt.excluded.hazard_type,
                    "risk_level": stmt.excluded.risk_level,
                    "area_sq_km": stmt.excluded.area_sq_km,
                    "enclosed_habitations_count": stmt.excluded.enclosed_habitations_count,
                    "exposed_population": stmt.excluded.exposed_population,
                    "buffer_margin_m": stmt.excluded.buffer_margin_m,
                    "primary_trigger": stmt.excluded.primary_trigger,
                    "geom": stmt.excluded.geom,
                    "updated_at": datetime.utcnow(),
                },
            )
            session.execute(stmt)
            stats["red_zones"]["inserted"] += 1

        session.commit()

        # ----------------------------------------------------------------------
        # 5. Seed System Alerts
        # ----------------------------------------------------------------------
        logger.info("Seeding system_alerts...")
        for alt in RECENT_SYSTEM_ALERTS:
            stmt = insert(SystemAlert).values(
                id=alt["id"],
                severity=alt.get("severity", "warning"),
                title=alt.get("title", ""),
                message=alt.get("message", ""),
                timestamp_text=alt.get("timestamp"),
                read=bool(alt.get("read", False)),
                district=alt.get("district", "Statewide"),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[SystemAlert.id],
                set_={
                    "severity": stmt.excluded.severity,
                    "title": stmt.excluded.title,
                    "message": stmt.excluded.message,
                    "timestamp_text": stmt.excluded.timestamp_text,
                    "read": stmt.excluded.read,
                    "district": stmt.excluded.district,
                },
            )
            session.execute(stmt)
            stats["system_alerts"]["inserted"] += 1

        session.commit()
        logger.info("Seeding completed successfully.")
        return stats

    except Exception as e:
        session.rollback()
        logger.error(f"Error during seeding: {e}")
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
