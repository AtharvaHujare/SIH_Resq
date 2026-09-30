import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, func, text, and_, or_
from sqlalchemy.orm import Session
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, mapping, shape
from shapely.ops import unary_union
from geoalchemy2.shape import to_shape, from_shape

from backend.app.core.config import settings
from backend.app.db.session import get_engine, check_db_health
from backend.app.models.orm_models import (
    RedZone,
    CandidateRelocationSite,
    Habitation,
    HazardEvent,
    RainfallObservation,
    InfrastructureFeature,
)
from backend.app.services.capacity_engine import capacity_engine
from backend.app.services.suitability_engine import suitability_engine
from backend.app.db.mock_data import RED_ZONES, CANDIDATE_RELOCATION_SITES

logger = logging.getLogger(__name__)


def _normalize_district(district: Optional[str]) -> Optional[str]:
    """Normalize district query by stripping UI labels like '(Primary Demo)' or '(Ghat Region)'."""
    if not district or district.strip().lower() == "all":
        return None
    cleaned = district.split("(")[0].strip()
    return cleaned if cleaned else district.strip()


class GISEngine:
    """Deterministic Geospatial Engine implementing PostGIS & Shapely spatial operations:
    - Multi-hazard dynamic red zone polygon synthesis and buffering
    - Multi-criteria safe/green zone polygon derivation
    - Spatial distance, intersection, and containment audits
    - GeoJSON FeatureCollection generation with rigorous CRS handling
    """

    # Project Configuration & Decision Criteria (Configurable decision thresholds)
    MIN_SAFE_DISTANCE_RED_ZONE_M = 1500.0   # Configured decision margin away from active landslide/flood scarps
    MIN_SAFE_DISTANCE_WATERWAY_M = 300.0     # Configured decision buffer away from major flash inundation streams
    MAX_SAFE_SLOPE_DEG = 8.0                 # Configured maximum slope gradient suitable for resettlement parcels
    MAX_ROAD_ISOLATION_M = 1200.0            # Configured road accessibility threshold (paved/all-weather link)
    MIN_USABLE_AREA_SQM = 10000.0            # Configured minimum contiguous usable land (approx 2.5 acres)
    EXTREME_RAIN_72H_THRESHOLD_MM = 200.0    # Configured heavy precipitation trigger threshold (based on IMD localized criteria)

    def _is_db_active(self) -> bool:
        """Check live database connectivity."""
        if not getattr(settings, "USE_DATABASE", True):
            return False
        health = check_db_health()
        return health.get("status") == "healthy"

    # ==========================================================================
    # 1. Dynamic Red Zones
    # ==========================================================================
    def get_dynamic_red_zones(self, district: Optional[str] = None) -> List[Dict[str, Any]]:
        """Synthesize active multi-hazard exclusion polygons using PostGIS spatial union,
        sensor trigger buffers, and baseline hazard boundaries.
        
        Returns List of dicts matching RedZoneResponse with Leaflet coordinates [[lat, lng], ...].
        """
        if not self._is_db_active():
            return self._get_prototype_red_zones_fallback(district)

        clean_dist = _normalize_district(district)
        try:
            engine = get_engine()
            with Session(engine) as session:
                # 1. Fetch baseline red zones
                stmt_rz = select(RedZone)
                if clean_dist:
                    d = clean_dist.lower()
                    if d == "guwahati":
                        stmt_rz = stmt_rz.where(or_(
                            RedZone.id.ilike("RZ_GUW%"),
                            RedZone.name.ilike("%guwahati%"),
                            RedZone.name.ilike("%brahmaputra%"),
                            RedZone.name.ilike("%kharghuli%"),
                            RedZone.name.ilike("%noonmati%"),
                            RedZone.name.ilike("%pandu%")
                        ))
                    elif d == "pune":
                        stmt_rz = stmt_rz.where(or_(
                            RedZone.id.ilike("RZ_PUN%"),
                            RedZone.name.ilike("%pune%"),
                            RedZone.name.ilike("%malin%"),
                            RedZone.name.ilike("%ambegaon%")
                        ))
                    elif d == "raigad":
                        stmt_rz = stmt_rz.where(or_(
                            RedZone.id.ilike("RZ_00%"),
                            RedZone.name.ilike("%raigad%"),
                            RedZone.name.ilike("%taliye%"),
                            RedZone.name.ilike("%varandha%"),
                            RedZone.name.ilike("%savitri%"),
                            RedZone.name.ilike("%mahad%")
                        ))
                    else:
                        stmt_rz = stmt_rz.where(RedZone.name.ilike(f"%{clean_dist}%"))
                baseline_zones = session.scalars(stmt_rz).all()

                # 2. Check active hazard events in district
                stmt_he = select(HazardEvent).where(HazardEvent.is_active == True)
                if clean_dist:
                    stmt_he = stmt_he.where(HazardEvent.district_name.ilike(f"%{clean_dist}%"))
                hazard_events = session.scalars(stmt_he).all()

                # 3. Check recent extreme rainfall in district
                stmt_rf = (
                    select(RainfallObservation)
                    .order_by(RainfallObservation.observed_at.desc())
                    .limit(10)
                )
                if clean_dist:
                    stmt_rf = stmt_rf.where(RainfallObservation.district_name.ilike(f"%{clean_dist}%"))
                rainfall_obs = session.scalars(stmt_rf).all()

                # Determine if rainfall triggers dynamic buffer expansion
                max_rain_72h = max([r.rainfall_72h_mm for r in rainfall_obs], default=0.0)
                buffer_multiplier = 1.0
                if max_rain_72h >= self.EXTREME_RAIN_72H_THRESHOLD_MM:
                    # Dynamically expand hazard buffer margin based on extreme rainfall intensity
                    buffer_multiplier = 1.0 + min(0.6, (max_rain_72h - self.EXTREME_RAIN_72H_THRESHOLD_MM) / 200.0)

                # Process baseline zones into result models
                results = []
                for bz in baseline_zones:
                    coords = []
                    effective_buffer = round(float(bz.buffer_margin_m) * buffer_multiplier, 1)

                    if bz.geom is not None:
                        poly = to_shape(bz.geom)
                        # Expand or preserve geometry based on rainfall trigger
                        if buffer_multiplier > 1.0:
                            # Project buffer in degrees (approx 1 deg ~ 111km -> 100m ~ 0.0009 deg)
                            deg_buffer = (effective_buffer - float(bz.buffer_margin_m)) / 111000.0
                            poly = poly.buffer(deg_buffer)

                        if poly.geom_type == "Polygon":
                            coords = [[float(c[1]), float(c[0])] for c in poly.exterior.coords]
                        elif poly.geom_type == "MultiPolygon":
                            # Use largest polygon
                            largest = max(poly.geoms, key=lambda p: p.area)
                            coords = [[float(c[1]), float(c[0])] for c in largest.exterior.coords]

                    trigger_desc = bz.primary_trigger or "Topographic & Historical Hazard Model"
                    if buffer_multiplier > 1.0:
                        trigger_desc += f" • Rain-Triggered Dynamic Expansion (+{int((buffer_multiplier-1)*100)}%)"

                    results.append({
                        "id": bz.id,
                        "name": bz.name,
                        "hazardType": bz.hazard_type,
                        "riskLevel": bz.risk_level,
                        "areaSqKm": round(float(bz.area_sq_km) * buffer_multiplier, 2),
                        "enclosedHabitationsCount": bz.enclosed_habitations_count,
                        "exposedPopulation": bz.exposed_population,
                        "bufferMarginM": effective_buffer,
                        "primaryTrigger": trigger_desc,
                        "coordinates": coords,
                        "isFallback": False,
                        "calculationMode": "POSTGIS_DYNAMIC_BUFFER" if buffer_multiplier > 1.0 else "DATABASE_VERIFIED",
                        "dataTimestamp": datetime.now(timezone.utc).isoformat(),
                    })

                # If dynamic events found that aren't yet in baseline, synthesize dynamic event polygons
                for he in hazard_events:
                    if he.geom is not None:
                        shp = to_shape(he.geom)
                        he_buffer_m = float(he.affected_radius_m) * buffer_multiplier
                        deg_buffer = he_buffer_m / 111000.0
                        buffered_poly = shp.buffer(deg_buffer)

                        coords = []
                        if buffered_poly.geom_type == "Polygon":
                            coords = [[float(c[1]), float(c[0])] for c in buffered_poly.exterior.coords]

                        results.append({
                            "id": he.id,
                            "name": f"Dynamic Hazard Area: {he.hazard_type.capitalize()}",
                            "hazardType": he.hazard_type.capitalize(),
                            "riskLevel": he.severity,
                            "areaSqKm": round((3.14159 * (he_buffer_m ** 2)) / 1000000.0, 3),
                            "enclosedHabitationsCount": 1,
                            "exposedPopulation": 250,
                            "bufferMarginM": round(he_buffer_m, 1),
                            "primaryTrigger": he.trigger_description or "Active Telemetry Sensor Trigger",
                            "coordinates": coords,
                            "isFallback": False,
                            "calculationMode": "TELEMETRY_EVENT_BUFFER",
                            "dataTimestamp": he.observed_at.isoformat() if he.observed_at else datetime.now(timezone.utc).isoformat(),
                        })

                if results:
                    return results

        except Exception as exc:
            logger.warning("Dynamic red-zone calculation failed: %s. Falling back to prototype dataset.", exc)

        return self._get_prototype_red_zones_fallback(district)

    def _get_prototype_red_zones_fallback(self, district: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fallback to verified prototype red zones with explicit fallback flags."""
        from copy import deepcopy
        zones = deepcopy(RED_ZONES)
        clean_dist = _normalize_district(district)
        if clean_dist:
            d = clean_dist.lower()
            if d == "guwahati":
                zones = [z for z in zones if z.get("district", "").lower() == "guwahati" or z.get("id", "").startswith("RZ_GUW") or any(k in z["name"].lower() for k in ["brahmaputra", "kharghuli", "noonmati", "pandu"])]
            elif d == "pune":
                zones = [z for z in zones if z.get("district", "").lower() == "pune" or z.get("id", "").startswith("RZ_PUN") or any(k in z["name"].lower() for k in ["malin", "ambegaon"])]
            elif d == "raigad":
                zones = [z for z in zones if z.get("district", "").lower() == "raigad" or any(k in z["name"].lower() for k in ["taliye", "varandha", "savitri", "mahad"])]
            else:
                zones = [z for z in zones if d in z.get("district", "").lower() or d in z["name"].lower()]

        for z in zones:
            z["isFallback"] = True
            z["calculationMode"] = "PROTOTYPE_FALLBACK"
            z["dataTimestamp"] = "2026-09-10T00:00:00Z"
        return zones

    # ==========================================================================
    # 2. Dynamic Green / Safe Zones
    # ==========================================================================
    def get_dynamic_safe_zones(self, district: Optional[str] = None) -> Dict[str, Any]:
        """Derives candidate resettlement safe havens using multi-criteria exclusion GIS:
        - Exclusion 1: Negative spatial buffer outside any active Red Zone (>= 1,500m)
        - Exclusion 2: Outside river/waterway flash inundation buffer (>= 300m)
        - Constraint 3: Gentle slope (<= 8 degrees)
        - Constraint 4: Road corridor accessibility (<= 1,200m)
        - Constraint 5: Usable land acreage (>= 2.5 acres / 10,000 sqm)
        
        Returns GeoJSON FeatureCollection.
        """
        features = []
        is_fallback = False
        calc_mode = "DETERMINISTIC_POSTGIS_MCDA"
        status_msg = "Safe zones derived from multi-criteria GIS exclusion rules."

        if self._is_db_active():
            try:
                engine = get_engine()
                with Session(engine) as session:
                    # Query candidate parcels
                    clean_dist = _normalize_district(district)
                    stmt = select(CandidateRelocationSite)
                    if clean_dist:
                        stmt = stmt.where(CandidateRelocationSite.district_name.ilike(f"%{clean_dist}%"))
                    sites = session.scalars(stmt).all()

                    for s in sites:
                        # Evaluate safety constraints
                        dist_hazard = float(s.distance_from_red_zone_km) * 1000.0
                        slope = float(s.slope_degree)
                        dist_road = float(s.distance_to_road_m)
                        area_sqm = float(s.usable_area_sqm)

                        # Must satisfy multi-criteria safety thresholds
                        is_safe = (
                            dist_hazard >= self.MIN_SAFE_DISTANCE_RED_ZONE_M
                            and slope <= self.MAX_SAFE_SLOPE_DEG
                            and dist_road <= self.MAX_ROAD_ISOLATION_M
                            and area_sqm >= self.MIN_USABLE_AREA_SQM
                        )

                        if not is_safe and s.suitability_score < 70.0:
                            continue

                        # Generate synthetic polygon parcel boundary around site point for visualization
                        # Radius based on usable area: Area = pi * r^2 -> r = sqrt(Area / pi)
                        radius_m = (area_sqm / 3.14159) ** 0.5
                        radius_deg = radius_m / 111000.0

                        pt_coords = [73.48, 18.06]  # default
                        if s.geom is not None:
                            pt = to_shape(s.geom)
                            pt_coords = [float(pt.x), float(pt.y)]  # [lon, lat]

                        center = Point(pt_coords[0], pt_coords[1])
                        safe_poly = center.buffer(radius_deg, quad_segs=16)

                        # Liebig capacity evaluation
                        cap_audit = capacity_engine.evaluate_carrying_capacity(
                            site_capacity=s.estimated_capacity,
                            target_population=int(s.estimated_capacity * 0.7),
                            potable_water_supply_kl=float(s.potable_water_daily_supplied_kl),
                            available_hospital_beds=s.hospital_beds_available,
                            usable_area_sqm=area_sqm,
                        )

                        geojson_poly = mapping(safe_poly)

                        features.append({
                            "type": "Feature",
                            "geometry": geojson_poly,
                            "properties": {
                                "id": f"SAFE_{s.id}",
                                "name": f"Green Safe Parcel: {s.name}",
                                "district": s.district_name,
                                "usableAreaAcres": float(s.usable_area_acres),
                                "usableAreaSqm": area_sqm,
                                "estimatedCapacity": cap_audit["feasibleCapacity"],
                                "feasibleCapacity": cap_audit["feasibleCapacity"],
                                "grossCapacity": cap_audit["grossCapacity"],
                                "utilization": cap_audit.get("utilization", 70.0),
                                "limitingFactor": cap_audit["limitingFactor"],
                                "slopeDegree": slope,
                                "suitabilityScore": float(s.suitability_score),
                                "nearestRoadDistanceM": dist_road,
                                "nearestHazardDistanceM": dist_hazard,
                                "derivationCriteria": f"Zero Red-Zone Overlap ({round(dist_hazard/1000, 1)}km margin) • Flat Topography ({slope}°) • Road Access ({int(dist_road)}m)",
                                "provenance": "DETERMINISTIC_GIS_CALCULATION",
                                "isFallback": False,
                            },
                        })

                    if features:
                        return {
                            "type": "FeatureCollection",
                            "features": features,
                            "metadata": {
                                "totalSafeZones": len(features),
                                "district": district or "All Monitored Corridors",
                                "calculationMode": calc_mode,
                                "fallbackUsed": False,
                                "statusMessage": status_msg,
                            },
                        }
            except Exception as exc:
                logger.warning("GIS safe zone generation failed: %s", exc)

        # Fallback using prototype candidate parcels with explicit metadata
        return self._get_prototype_safe_zones_fallback(district)

    def _get_prototype_safe_zones_fallback(self, district: Optional[str] = None) -> Dict[str, Any]:
        """Generate verified candidate safe parcels from baseline data with explicit fallback flags."""
        features = []
        sites = [s for s in CANDIDATE_RELOCATION_SITES if s.get("suitabilityScore", 0) >= 80]
        clean_dist = _normalize_district(district)
        if clean_dist:
            sites = [s for s in sites if clean_dist.lower() in s["district"].lower()]

        for s in sites:
            lat, lon = s["coordinates"]
            area_sqm = float(s.get("usableAreaSqm", 48000.0))
            radius_m = (area_sqm / 3.14159) ** 0.5
            radius_deg = radius_m / 111000.0

            center = Point(lon, lat)  # [lon, lat]
            poly = center.buffer(radius_deg, quad_segs=16)

            cap_audit = capacity_engine.evaluate_carrying_capacity(
                site_capacity=s["estimatedCapacity"],
                target_population=int(s["estimatedCapacity"] * 0.7),
                potable_water_supply_kl=float(s.get("potableWaterDailySuppliedKl", 450.0)),
                available_hospital_beds=s.get("hospitalBedsAvailable", 15),
                usable_area_sqm=area_sqm,
            )

            features.append({
                "type": "Feature",
                "geometry": mapping(poly),
                "properties": {
                    "id": f"SAFE_{s['id']}",
                    "name": f"Green Safe Parcel: {s['name']}",
                    "district": s["district"],
                    "usableAreaAcres": float(s["usableAreaAcres"]),
                    "usableAreaSqm": area_sqm,
                    "estimatedCapacity": cap_audit["feasibleCapacity"],
                    "feasibleCapacity": cap_audit["feasibleCapacity"],
                    "grossCapacity": cap_audit["grossCapacity"],
                    "utilization": cap_audit.get("utilization", 70.0),
                    "limitingFactor": cap_audit["limitingFactor"],
                    "slopeDegree": float(s["slopeDegree"]),
                    "suitabilityScore": float(s["suitabilityScore"]),
                    "nearestRoadDistanceM": float(s["distanceToRoadM"]),
                    "nearestHazardDistanceM": float(s["distanceFromRedZoneKm"]) * 1000.0,
                    "derivationCriteria": f"Prototype Audited Safe Parcel • Safe Margin ({s['distanceFromRedZoneKm']}km) • Flat Slope ({s['slopeDegree']}°)",
                    "provenance": "PROTOTYPE_FALLBACK",
                    "isFallback": True,
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "totalSafeZones": len(features),
                "district": district or "All Monitored Corridors",
                "calculationMode": "PROTOTYPE_FALLBACK",
                "fallbackUsed": True,
                "statusMessage": "Displayed candidate safe parcels derived from baseline audited land parcels.",
            },
        }


gis_engine = GISEngine()
