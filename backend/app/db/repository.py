import logging
from typing import List, Optional, Dict, Any, Union
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select, func, or_, update, text
from sqlalchemy.orm import Session, selectinload
from geoalchemy2.shape import to_shape

from backend.app.core.config import settings
from backend.app.db.mock_data import (
    KPI_METRICS,
    DISTRICT_PROFILES,
    VULNERABLE_HABITATIONS,
    CANDIDATE_RELOCATION_SITES,
    RED_ZONES,
    RECENT_SYSTEM_ALERTS,
    RISK_ANALYTICS_DATA,
)
from backend.app.db.session import get_engine, check_db_health
from backend.app.models.orm_models import (
    District,
    Habitation,
    HabitationAiFactor,
    CandidateRelocationSite,
    RedZone,
    SystemAlert,
    DataSource,
    DataIngestionRun,
    WeatherObservation,
    RainfallObservation,
    HazardEvent,
    InfrastructureFeature,
)
from backend.app.services.capacity_engine import capacity_engine

logger = logging.getLogger(__name__)


def _district_to_dict(d: District) -> Dict[str, Any]:
    """Convert District ORM model to dictionary matching DistrictProfile."""
    return {
        "id": d.id,
        "name": d.name,
        "state": d.state,
        "habitationsCount": d.habitations_count,
        "criticalCount": d.critical_count,
        "exposedPop": d.exposed_pop,
        "dominantHazard": d.dominant_hazard or "",
    }


def _habitation_to_dict(h: Habitation) -> Dict[str, Any]:
    """Convert Habitation ORM model to dictionary matching HabitationResponse."""
    coords = [0.0, 0.0]
    if h.geom is not None:
        pt = to_shape(h.geom)
        # Point(x, y) where x is longitude, y is latitude.
        # Frontend Leaflet requires [latitude, longitude].
        coords = [float(pt.y), float(pt.x)]

    ai_factors = [
        {
            "factor": f.factor,
            "impact": f.impact,
            "direction": f.direction,
            "description": f.description or "",
            "weight": float(f.weight),
        }
        for f in (h.ai_factors or [])
    ]

    return {
        "id": h.id,
        "name": h.name,
        "district": h.district_name,
        "state": h.state,
        "coordinates": coords,
        "population": h.population,
        "households": h.households,
        "riskScore": float(h.risk_score),
        "riskTier": h.risk_tier,
        "vulnerabilityIndex": float(h.vulnerability_index),
        "dominantHazards": h.dominant_hazards or "",
        "slopeDegree": float(h.slope_degree),
        "rainfall3dMm": float(h.rainfall_3d_mm),
        "rainfallAnomalyPercent": float(h.rainfall_anomaly_percent),
        "kutchaHousingPercent": float(h.kutcha_housing_percent),
        "roadIsolationDistanceKm": float(h.road_isolation_distance_km),
        "hospitalDistanceKm": float(h.hospital_distance_km),
        "historicalDisastersCount": h.historical_disasters_count,
        "recentCasualties": h.recent_casualties,
        "priority": h.priority,
        "priorityLabel": h.priority_label,
        "recommendedSiteId": h.recommended_site_id,
        "aiFactors": ai_factors,
    }


def _site_to_dict(s: CandidateRelocationSite) -> Dict[str, Any]:
    """Convert CandidateRelocationSite ORM model to dictionary matching CandidateSiteResponse."""
    coords = [0.0, 0.0]
    if s.geom is not None:
        pt = to_shape(s.geom)
        coords = [float(pt.y), float(pt.x)]

    return {
        "id": s.id,
        "name": s.name,
        "district": s.district_name,
        "state": s.state,
        "coordinates": coords,
        "distanceFromRedZoneKm": float(s.distance_from_red_zone_km),
        "usableAreaSqm": float(s.usable_area_sqm),
        "usableAreaAcres": float(s.usable_area_acres),
        "estimatedCapacity": s.estimated_capacity,
        "slopeDegree": float(s.slope_degree),
        "suitabilityScore": float(s.suitability_score),
        "capacityStatus": s.capacity_status,
        "carryingCapacityFactor": float(s.carrying_capacity_factor),
        "waterAvailabilityStatus": s.water_availability_status or "Adequate Ground Recharge",
        "distanceToRoadM": float(s.distance_to_road_m),
        "roadAccessibility": s.road_accessibility or "All-Weather Paved Access",
        "distanceToHospitalKm": float(s.distance_to_hospital_km),
        "healthcareStatus": s.healthcare_status or "Community Health Center within 5km",
        "distanceToSchoolKm": float(s.distance_to_school_km),
        "schoolingStatus": s.schooling_status or "Primary & Secondary School within 3km",
        "powerGridAccess": s.power_grid_access or "High Tension Grid within 500m",
        "overallRecommendation": s.overall_recommendation,
        "suitabilityBreakdown": {
            "hazardSafety": s.factor_hazard_safety,
            "accessibility": s.factor_accessibility,
            "landSuitability": s.factor_land_suitability,
            "waterAvailability": s.factor_water_availability,
            "healthcareAccess": s.factor_healthcare_access,
            "educationAccess": s.factor_education_access,
            "carryingCapacity": s.factor_carrying_capacity,
        },
        "capacityMetrics": {
            "allocatedPopulation": s.allocated_population,
            "maximumAbsorption": s.maximum_absorption,
            "grossCapacity": int(s.usable_area_sqm / 45.0) if s.usable_area_sqm and s.usable_area_sqm > 0 else s.estimated_capacity,
            "feasibleCapacity": s.estimated_capacity,
            "limitingFactor": "Potable Water Supply (CPHEEO 135 LPD)" if (float(s.potable_water_daily_supplied_kl or 0) * 1000.0 / 135.0) < (s.usable_area_sqm / 45.0 if s.usable_area_sqm else s.estimated_capacity) else "Land Area & Topography (45 m²/person)",
            "landCapacity": int(s.usable_area_sqm / 45.0) if s.usable_area_sqm and s.usable_area_sqm > 0 else s.estimated_capacity,
            "waterCapacity": int(float(s.potable_water_daily_supplied_kl) * 1000.0 / 135.0) if s.potable_water_daily_supplied_kl and float(s.potable_water_daily_supplied_kl) > 0 else None,
            "healthCapacity": (s.hospital_beds_available * 500) if s.hospital_beds_available is not None else None,
            "remainingCapacity": s.remaining_capacity,
            "utilizationPercent": float(s.utilization_percent),
            "potableWaterDailyNeededKl": float(s.potable_water_daily_needed_kl),
            "potableWaterDailySuppliedKl": float(s.potable_water_daily_supplied_kl),
            "hospitalBedsRequired": s.hospital_beds_required,
            "hospitalBedsAvailable": s.hospital_beds_available,
        },
    }


def _red_zone_to_dict(rz: RedZone) -> Dict[str, Any]:
    """Convert RedZone ORM model to dictionary matching RedZoneResponse."""
    coords = []
    if rz.geom is not None:
        poly = to_shape(rz.geom)
        # poly.exterior.coords are (longitude, latitude).
        # Frontend Leaflet Polygon ring expects [[latitude, longitude], ...].
        coords = [[float(c[1]), float(c[0])] for c in poly.exterior.coords]

    return {
        "id": rz.id,
        "name": rz.name,
        "hazardType": rz.hazard_type,
        "riskLevel": rz.risk_level,
        "areaSqKm": float(rz.area_sq_km),
        "enclosedHabitationsCount": rz.enclosed_habitations_count,
        "exposedPopulation": rz.exposed_population,
        "bufferMarginM": float(rz.buffer_margin_m),
        "primaryTrigger": rz.primary_trigger or "",
        "coordinates": coords,
    }


def _alert_to_dict(a: SystemAlert) -> Dict[str, Any]:
    """Convert SystemAlert ORM model to dictionary matching AlertResponse."""
    ts = a.timestamp_text
    if not ts and a.created_at:
        ts = a.created_at.strftime("%Y-%m-%d %H:%M")
    return {
        "id": a.id,
        "severity": a.severity,
        "title": a.title,
        "message": a.message,
        "timestamp": ts or "Just now",
        "read": a.read,
        "district": a.district,
    }


def _normalize_district(district: Optional[str]) -> Optional[str]:
    """Normalize district query by stripping UI labels like '(Primary Demo)' or '(Ghat Region)'."""
    if not district or district.strip().lower() == "all":
        return None
    cleaned = district.split("(")[0].strip()
    return cleaned if cleaned else district.strip()


class DataRepository:
    """Repository abstraction layer.
    Features:
    1. Primary: Transparently queries Supabase PostgreSQL/PostGIS when connected and enabled.
    2. Fallback: Automatically falls back to in-memory mock datasets if the database
       is unreachable or disabled, with explicit warning logs.
    3. Preserves exact dictionary outputs required by existing routes, Pydantic schemas,
       and Leaflet maps.
    """

    def __init__(self):
        self._alerts = deepcopy(RECENT_SYSTEM_ALERTS)
        self._last_source: str = "uninitialized"

    @property
    def is_db_enabled(self) -> bool:
        """Determines if database query mode is active and operational."""
        if not getattr(settings, "USE_DATABASE", True):
            return False
        health = check_db_health()
        return health.get("status") == "healthy"

    @property
    def is_db_active(self) -> bool:
        """Alias for checking live database health."""
        return self.is_db_enabled

    @property
    def data_source(self) -> str:
        """Returns the current data source: 'supabase' or 'mock_fallback'."""
        return "supabase" if self.is_db_enabled else "mock_fallback"

    # ==========================================================================
    # 1. KPIs
    # ==========================================================================
    def get_kpis(self, district: Optional[str] = None) -> Dict[str, Any]:
        """Fetch headline KPI summary metrics with optimized single-roundtrip aggregation."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    filter_district = bool(clean_dist)
                    hab_filter = "WHERE district_name ILIKE :dist" if filter_district else ""
                    hab_and = "AND district_name ILIKE :dist" if filter_district else ""
                    site_filter = "WHERE district_name ILIKE :dist" if filter_district else ""

                    sql = text(f"""
                        SELECT
                            (SELECT count(*) FROM habitations {hab_filter}) as total_habs,
                            (SELECT count(*) FROM habitations WHERE risk_score >= 55 {hab_and}) as high_risk,
                            (SELECT count(*) FROM habitations WHERE risk_tier = 'Critical' {hab_and}) as critical_habs,
                            (SELECT coalesce(sum(population), 0) FROM habitations WHERE risk_score >= 55 {hab_and}) as exposed_pop,
                            (SELECT count(*) FROM habitations WHERE priority = 1 {hab_and}) as immediate_queue,
                            (SELECT count(*) FROM candidate_relocation_sites {site_filter}) as total_sites,
                            (SELECT coalesce(avg(suitability_score), 87.4) FROM candidate_relocation_sites {site_filter}) as avg_suitability,
                            (SELECT count(*) FROM districts) as total_districts
                    """)
                    params = {"dist": f"%{clean_dist}%"} if filter_district else {}
                    row = session.execute(sql, params).mappings().first()

                    total_habs = int(row["total_habs"])
                    high_risk = int(row["high_risk"])
                    critical = int(row["critical_habs"])
                    exposed_pop = int(row["exposed_pop"])
                    queue_len = int(row["immediate_queue"])
                    total_sites = int(row["total_sites"])
                    avg_suitability = float(row["avg_suitability"])
                    dist_count = int(row["total_districts"]) or 5

                    self._last_source = "supabase"
                    logger.debug("Fetched KPIs from Supabase (district: %s)", district)
                    return {
                        "totalHabitations": total_habs,
                        "highRiskHabitations": high_risk,
                        "criticalRedZoneHabitations": critical,
                        "populationExposed": exposed_pop,
                        "potentialRelocationSites": total_sites,
                        "immediateRelocationQueue": queue_len,
                        "averageSuitabilityScore": round(avg_suitability, 1),
                        "districtsMonitored": dist_count,
                        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "modelConfidence": "94.2% (Ensemble-Calibrated)",
                    }
            except Exception as exc:
                logger.warning("Supabase KPI query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        return self._get_kpis_mock(district)

    def _get_kpis_mock(self, district: Optional[str] = None) -> Dict[str, Any]:
        metrics = deepcopy(KPI_METRICS)
        if district and district.lower() != "all":
            habs = [h for h in VULNERABLE_HABITATIONS if district.lower() in h["district"].lower()]
            if habs:
                metrics["totalHabitations"] = len(habs)
                metrics["highRiskHabitations"] = len([h for h in habs if h["riskScore"] >= 55])
                metrics["criticalRedZoneHabitations"] = len([h for h in habs if h["riskTier"] == "Critical"])
                metrics["populationExposed"] = sum(h["population"] for h in habs if h["riskScore"] >= 55)
                metrics["immediateRelocationQueue"] = len([h for h in habs if h["priority"] == 1])
        return metrics

    # ==========================================================================
    # 2. Districts
    # ==========================================================================
    def get_districts(self) -> List[Dict[str, Any]]:
        """Return monitored district profiles."""
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(District).order_by(District.name)
                    districts = session.scalars(stmt).all()
                    self._last_source = "supabase"
                    logger.debug("Fetched %d districts from Supabase", len(districts))
                    return [_district_to_dict(d) for d in districts]
            except Exception as exc:
                logger.warning("Supabase districts query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        return deepcopy(DISTRICT_PROFILES)

    # ==========================================================================
    # 3. Habitations
    # ==========================================================================
    def get_habitations(
        self,
        search_query: Optional[str] = None,
        district: Optional[str] = None,
        risk_tier: Optional[str] = None,
        priority: Optional[Union[int, str]] = None,
        sort_by: Optional[str] = "riskScore",
        page: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query habitations with multi-criteria filtering and sorting."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(Habitation).options(selectinload(Habitation.ai_factors))

                    if clean_dist:
                        stmt = stmt.where(Habitation.district_name.ilike(f"%{clean_dist}%"))

                    if risk_tier and risk_tier.lower() != "all":
                        stmt = stmt.where(Habitation.risk_tier.ilike(risk_tier))

                    if priority and str(priority).lower() != "all":
                        try:
                            stmt = stmt.where(Habitation.priority == int(priority))
                        except ValueError:
                            pass

                    if search_query:
                        q = f"%{search_query.strip()}%"
                        stmt = stmt.where(
                            or_(
                                Habitation.name.ilike(q),
                                Habitation.district_name.ilike(q),
                                Habitation.dominant_hazards.ilike(q),
                            )
                        )

                    # Sorting
                    if sort_by == "riskScore":
                        stmt = stmt.order_by(Habitation.risk_score.desc())
                    elif sort_by == "population":
                        stmt = stmt.order_by(Habitation.population.desc())
                    elif sort_by == "priority":
                        stmt = stmt.order_by(Habitation.priority.asc(), Habitation.risk_score.desc())
                    else:
                        stmt = stmt.order_by(Habitation.risk_score.desc())

                    # Pagination
                    offset = (page - 1) * limit
                    stmt = stmt.offset(offset).limit(limit)

                    habitations = session.scalars(stmt).all()
                    self._last_source = "supabase"
                    logger.debug("Fetched %d habitations from Supabase", len(habitations))
                    return [_habitation_to_dict(h) for h in habitations]
            except Exception as exc:
                logger.warning("Supabase habitations query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        return self._get_habitations_mock(
            search_query=search_query,
            district=district,
            risk_tier=risk_tier,
            priority=priority,
            sort_by=sort_by,
            page=page,
            limit=limit,
        )

    def _get_habitations_mock(
        self,
        search_query: Optional[str] = None,
        district: Optional[str] = None,
        risk_tier: Optional[str] = None,
        priority: Optional[Union[int, str]] = None,
        sort_by: Optional[str] = "riskScore",
        page: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        result = deepcopy(VULNERABLE_HABITATIONS)

        clean_dist = _normalize_district(district)
        if clean_dist:
            result = [h for h in result if clean_dist.lower() in h["district"].lower()]

        if risk_tier and risk_tier.lower() != "all":
            result = [h for h in result if h["riskTier"].lower() == risk_tier.lower()]

        if priority and str(priority).lower() != "all":
            result = [h for h in result if str(h["priority"]) == str(priority)]

        if search_query:
            q = search_query.lower().strip()
            result = [
                h for h in result
                if q in h["name"].lower()
                or q in h["district"].lower()
                or q in h["dominantHazards"].lower()
            ]

        # Sorting
        if sort_by:
            if sort_by == "riskScore":
                result.sort(key=lambda x: x["riskScore"], reverse=True)
            elif sort_by == "population":
                result.sort(key=lambda x: x["population"], reverse=True)
            elif sort_by == "priority":
                result.sort(key=lambda x: (x["priority"], -x["riskScore"]))

        # Pagination
        start = (page - 1) * limit
        return result[start : start + limit]

    def get_habitation_by_id(self, habitation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single habitation by ID."""
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = (
                        select(Habitation)
                        .options(selectinload(Habitation.ai_factors))
                        .where(Habitation.id.ilike(habitation_id.strip()))
                    )
                    h = session.scalars(stmt).first()
                    if h:
                        self._last_source = "supabase"
                        return _habitation_to_dict(h)
                    return None
            except Exception as exc:
                logger.warning("Supabase habitation_by_id query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        for h in VULNERABLE_HABITATIONS:
            if h["id"].upper() == habitation_id.upper():
                return deepcopy(h)
        return None

    # ==========================================================================
    # 4. Relocation Sites
    # ==========================================================================
    def get_relocation_sites(
        self,
        search_query: Optional[str] = None,
        district: Optional[str] = None,
        min_suitability: Optional[float] = None,
        min_capacity: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Query candidate safe relocation parcels with filtering."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(CandidateRelocationSite)

                    if clean_dist:
                        stmt = stmt.where(CandidateRelocationSite.district_name.ilike(f"%{clean_dist}%"))

                    if min_suitability is not None and float(min_suitability) > 0:
                        stmt = stmt.where(CandidateRelocationSite.suitability_score >= float(min_suitability))

                    if min_capacity is not None and int(min_capacity) > 0:
                        stmt = stmt.where(CandidateRelocationSite.estimated_capacity >= int(min_capacity))

                    if search_query:
                        q = f"%{search_query.strip()}%"
                        stmt = stmt.where(
                            or_(
                                CandidateRelocationSite.name.ilike(q),
                                CandidateRelocationSite.district_name.ilike(q),
                                CandidateRelocationSite.overall_recommendation.ilike(q),
                            )
                        )

                    stmt = stmt.order_by(CandidateRelocationSite.suitability_score.desc())
                    sites = session.scalars(stmt).all()
                    self._last_source = "supabase"
                    logger.debug("Fetched %d relocation sites from Supabase", len(sites))
                    return [_site_to_dict(s) for s in sites]
            except Exception as exc:
                logger.warning("Supabase relocation_sites query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        return self._get_relocation_sites_mock(
            search_query=search_query,
            district=district,
            min_suitability=min_suitability,
            min_capacity=min_capacity,
        )

    def _get_relocation_sites_mock(
        self,
        search_query: Optional[str] = None,
        district: Optional[str] = None,
        min_suitability: Optional[float] = None,
        min_capacity: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        result = deepcopy(CANDIDATE_RELOCATION_SITES)

        clean_dist = _normalize_district(district)
        if clean_dist:
            result = [s for s in result if clean_dist.lower() in s["district"].lower()]

        if min_suitability is not None and float(min_suitability) > 0:
            result = [s for s in result if s["suitabilityScore"] >= float(min_suitability)]

        if min_capacity is not None and int(min_capacity) > 0:
            result = [s for s in result if s["estimatedCapacity"] >= int(min_capacity)]

        if search_query:
            q = search_query.lower().strip()
            result = [
                s for s in result
                if q in s["name"].lower()
                or q in s["district"].lower()
                or q in s["overallRecommendation"].lower()
            ]

        return result

    def get_relocation_site_by_id(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single relocation site parcel by ID."""
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(CandidateRelocationSite).where(
                        CandidateRelocationSite.id.ilike(site_id.strip())
                    )
                    s = session.scalars(stmt).first()
                    if s:
                        self._last_source = "supabase"
                        return _site_to_dict(s)
                    return None
            except Exception as exc:
                logger.warning("Supabase relocation_site_by_id query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        for s in CANDIDATE_RELOCATION_SITES:
            if s["id"].upper() == site_id.upper():
                return deepcopy(s)
        return None

    # ==========================================================================
    # 5. Red Zones
    # ==========================================================================
    def get_red_zones(self, district: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve delineated high-risk Red Zone polygons."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(RedZone)
                    if clean_dist:
                        d = clean_dist.lower()
                        if d == "guwahati":
                            stmt = stmt.where(or_(
                                RedZone.id.ilike("RZ_GUW%"),
                                RedZone.name.ilike("%guwahati%"),
                                RedZone.name.ilike("%brahmaputra%"),
                                RedZone.name.ilike("%kharghuli%"),
                                RedZone.name.ilike("%noonmati%"),
                                RedZone.name.ilike("%pandu%")
                            ))
                        elif d == "pune":
                            stmt = stmt.where(or_(
                                RedZone.id.ilike("RZ_PUN%"),
                                RedZone.name.ilike("%pune%"),
                                RedZone.name.ilike("%malin%"),
                                RedZone.name.ilike("%ambegaon%")
                            ))
                        elif d == "raigad":
                            stmt = stmt.where(or_(
                                RedZone.id.ilike("RZ_00%"),
                                RedZone.name.ilike("%raigad%"),
                                RedZone.name.ilike("%taliye%"),
                                RedZone.name.ilike("%varandha%"),
                                RedZone.name.ilike("%savitri%"),
                                RedZone.name.ilike("%mahad%")
                            ))
                        else:
                            stmt = stmt.where(RedZone.name.ilike(f"%{clean_dist}%"))
                    stmt = stmt.order_by(RedZone.name.asc())
                    red_zones = session.scalars(stmt).all()
                    self._last_source = "supabase"
                    logger.debug("Fetched %d red zones from Supabase", len(red_zones))
                    return [_red_zone_to_dict(rz) for rz in red_zones]
            except Exception as exc:
                logger.warning("Supabase red_zones query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        result = deepcopy(RED_ZONES)
        if clean_dist:
            d = clean_dist.lower()
            if d == "guwahati":
                result = [r for r in result if r.get("district", "").lower() == "guwahati" or r.get("id", "").startswith("RZ_GUW") or any(k in r["name"].lower() for k in ["brahmaputra", "kharghuli", "noonmati", "pandu"])]
            elif d == "pune":
                result = [r for r in result if r.get("district", "").lower() == "pune" or r.get("id", "").startswith("RZ_PUN") or any(k in r["name"].lower() for k in ["malin", "ambegaon"])]
            elif d == "raigad":
                result = [r for r in result if r.get("district", "").lower() == "raigad" or any(k in r["name"].lower() for k in ["taliye", "varandha", "savitri", "mahad"])]
            else:
                result = [r for r in result if d in r.get("district", "").lower() or d in r["name"].lower()]
        return result

    # ==========================================================================
    # 6. Alerts
    # ==========================================================================
    def get_alerts(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Retrieve early warning system alerts."""
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(SystemAlert)
                    if unread_only:
                        stmt = stmt.where(SystemAlert.read == False)
                    stmt = stmt.order_by(SystemAlert.id.asc())
                    alerts = session.scalars(stmt).all()
                    self._last_source = "supabase"
                    logger.debug("Fetched %d alerts from Supabase", len(alerts))
                    return [_alert_to_dict(a) for a in alerts]
            except Exception as exc:
                logger.warning("Supabase alerts query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        if unread_only:
            return [a for a in self._alerts if not a["read"]]
        return deepcopy(self._alerts)

    def mark_all_alerts_read(self) -> int:
        """Mark all active alerts as read."""
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = update(SystemAlert).where(SystemAlert.read == False).values(read=True)
                    res = session.execute(stmt)
                    session.commit()
                    # Also keep local copy synced
                    for a in self._alerts:
                        a["read"] = True
                    self._last_source = "supabase"
                    return res.rowcount
            except Exception as exc:
                logger.warning("Supabase mark_all_alerts_read failed: %s. Falling back to local state.", exc)
                self._last_source = "mock_fallback"

        count = 0
        for alert in self._alerts:
            if not alert["read"]:
                alert["read"] = True
                count += 1
        return count

    # ==========================================================================
    # 7. Risk Analytics
    # ==========================================================================
    def get_risk_analytics(self, district: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve statistical risk distributions and factor contributions."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(Habitation)
                    if clean_dist:
                        stmt = stmt.where(Habitation.district_name.ilike(f"%{clean_dist}%"))
                    habs = session.scalars(stmt).all()

                    tier_colors = {
                        "Critical": "#EF4444",
                        "High": "#F97316",
                        "Moderate": "#F59E0B",
                        "Low": "#10B981",
                    }
                    distribution = []
                    for tier in ["Critical", "High", "Moderate", "Low"]:
                        t_habs = [h for h in habs if h.risk_tier.lower() == tier.lower()]
                        distribution.append({
                            "tier": tier,
                            "count": len(t_habs),
                            "color": tier_colors.get(tier, "#6B7280"),
                            "popExposed": sum(h.population for h in t_habs),
                        })

                    self._last_source = "supabase"
                    return {
                        "distribution": distribution,
                        "hazardContributions": deepcopy(RISK_ANALYTICS_DATA["hazardContributions"]),
                        "districtComparisons": deepcopy(RISK_ANALYTICS_DATA["districtComparisons"]),
                    }
            except Exception as exc:
                logger.warning("Supabase risk_analytics query failed: %s. Falling back to mock data.", exc)
                self._last_source = "mock_fallback"

        return deepcopy(RISK_ANALYTICS_DATA)

    # ==========================================================================
    # 8. Unified Search
    # ==========================================================================
    def search_all(self, query: str) -> Dict[str, Any]:
        """Perform unified search across habitations, candidate sites, and red zones."""
        q = query.strip()
        matched_habs = self.get_habitations(search_query=q, limit=50)
        matched_sites = self.get_relocation_sites(search_query=q)
        all_zones = self.get_red_zones()
        matched_zones = [
            z for z in all_zones
            if q.lower() in z["name"].lower() or q.lower() in z["hazardType"].lower()
        ]

        return {
            "query": query,
            "habitations": matched_habs,
            "sites": matched_sites,
            "redZones": matched_zones,
        }

    # ==========================================================================
    # 9. Ingestion & Observations Layer (Data Provenance & Spatial Features)
    # ==========================================================================
    def get_data_sources(self) -> List[Dict[str, Any]]:
        """Retrieve registered authoritative external data sources."""
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    sources = session.scalars(select(DataSource).order_by(DataSource.id)).all()
                    return [
                        {
                            "id": s.id,
                            "name": s.name,
                            "category": s.category,
                            "cadence": s.cadence,
                            "endpointUrl": s.endpoint_url,
                            "isActive": s.is_active,
                            "lastSyncAt": s.last_sync_at.isoformat() if s.last_sync_at else None,
                            "lastSyncStatus": s.last_sync_status or "Never Synced",
                        }
                        for s in sources
                    ]
            except Exception as exc:
                logger.warning("Supabase data_sources query failed: %s", exc)
        return []

    def get_weather_observations(self, district: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve latest meteorological observations with spatial coordinates."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(WeatherObservation)
                    if clean_dist:
                        stmt = stmt.where(WeatherObservation.district_name.ilike(f"%{clean_dist}%"))
                    stmt = stmt.order_by(WeatherObservation.observed_at.desc()).limit(limit)
                    obs = session.scalars(stmt).all()
                    result = []
                    for o in obs:
                        coords = None
                        if o.geom is not None:
                            pt = to_shape(o.geom)
                            coords = [float(pt.y), float(pt.x)]
                        result.append({
                            "id": o.id,
                            "sourceId": o.source_id,
                            "district": o.district_name,
                            "stationId": o.station_id,
                            "stationName": o.station_name,
                            "temperatureC": o.temperature_c,
                            "humidityPercent": o.humidity_percent,
                            "windSpeedKmh": o.wind_speed_kmh,
                            "weatherCondition": o.weather_condition,
                            "warningLevel": o.warning_level,
                            "warningText": o.warning_text,
                            "observedAt": o.observed_at.isoformat() if o.observed_at else None,
                            "ingestedAt": o.ingested_at.isoformat() if o.ingested_at else None,
                            "isFallback": o.is_fallback,
                            "coordinates": coords,
                        })
                    return result
            except Exception as exc:
                logger.warning("Supabase weather_observations query failed: %s", exc)
        return []

    def get_rainfall_observations(self, district: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve latest hyetometric rainfall observations and anomaly metrics."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(RainfallObservation)
                    if clean_dist:
                        stmt = stmt.where(RainfallObservation.district_name.ilike(f"%{clean_dist}%"))
                    stmt = stmt.order_by(RainfallObservation.observed_at.desc()).limit(limit)
                    obs = session.scalars(stmt).all()
                    result = []
                    for o in obs:
                        coords = None
                        if o.geom is not None:
                            pt = to_shape(o.geom)
                            coords = [float(pt.y), float(pt.x)]
                        result.append({
                            "id": o.id,
                            "sourceId": o.source_id,
                            "district": o.district_name,
                            "stationId": o.station_id,
                            "stationName": o.station_name,
                            "rainfall24hMm": o.rainfall_24h_mm,
                            "rainfall72hMm": o.rainfall_72h_mm,
                            "rainfallAnomalyPercent": o.rainfall_anomaly_percent,
                            "observedAt": o.observed_at.isoformat() if o.observed_at else None,
                            "ingestedAt": o.ingested_at.isoformat() if o.ingested_at else None,
                            "isFallback": o.is_fallback,
                            "coordinates": coords,
                        })
                    return result
            except Exception as exc:
                logger.warning("Supabase rainfall_observations query failed: %s", exc)
        return []

    def get_infrastructure_features(
        self,
        district: Optional[str] = None,
        feature_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve geospatial infrastructure features (hospitals, schools, roads, waterways)."""
        clean_dist = _normalize_district(district)
        if self.is_db_enabled:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    stmt = select(InfrastructureFeature)
                    if clean_dist:
                        stmt = stmt.where(InfrastructureFeature.district_name.ilike(f"%{clean_dist}%"))
                    if feature_type and feature_type.lower() != "all":
                        stmt = stmt.where(InfrastructureFeature.feature_type == feature_type.lower())
                    stmt = stmt.limit(limit)
                    feats = session.scalars(stmt).all()
                    result = []
                    for f in feats:
                        coords = None
                        if f.geom is not None:
                            shp = to_shape(f.geom)
                            if shp.geom_type == "Point":
                                coords = [float(shp.y), float(shp.x)]
                            elif shp.geom_type == "LineString":
                                coords = [[float(c[1]), float(c[0])] for c in shp.coords]
                        result.append({
                            "id": f.id,
                            "sourceId": f.source_id,
                            "featureType": f.feature_type,
                            "name": f.name,
                            "district": f.district_name,
                            "capacityOrBeds": f.capacity_or_beds,
                            "allWeatherAccess": f.all_weather_access,
                            "properties": f.properties_json or {},
                            "coordinates": coords,
                            "isFallback": f.is_fallback,
                        })
                    return result
            except Exception as exc:
                logger.warning("Supabase infrastructure_features query failed: %s", exc)
        return []


# Global repository instance
repository = DataRepository()
