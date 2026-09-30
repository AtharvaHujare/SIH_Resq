from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    Index,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry

Base = declarative_base()


class District(Base):
    """Monitored administrative district corridor."""
    __tablename__ = "districts"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    habitations_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    exposed_pop = Column(Integer, default=0)
    dominant_hazard = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    habitations = relationship("Habitation", back_populates="district_rel", cascade="all, delete-orphan")
    relocation_sites = relationship("CandidateRelocationSite", back_populates="district_rel")


class Habitation(Base):
    """Vulnerable settlement exposed to natural hazards."""
    __tablename__ = "habitations"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    district_id = Column(String(50), ForeignKey("districts.id"), nullable=True)
    district_name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    # Demographic & Socio-structural
    population = Column(Integer, nullable=False, default=0)
    households = Column(Integer, nullable=False, default=0)
    kutcha_housing_percent = Column(Float, default=0.0)

    # Composite Risk Engine Outputs
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_tier = Column(String(50), nullable=False, default="Moderate")
    vulnerability_index = Column(Float, default=0.0)
    dominant_hazards = Column(String(255), nullable=True)

    # Physical / Environmental Metrics
    slope_degree = Column(Float, default=0.0)
    rainfall_3d_mm = Column(Float, default=0.0)
    rainfall_anomaly_percent = Column(Float, default=0.0)
    road_isolation_distance_km = Column(Float, default=0.0)
    hospital_distance_km = Column(Float, default=0.0)
    historical_disasters_count = Column(Integer, default=0)
    recent_casualties = Column(Integer, default=0)

    # Prioritization Queue Assignment
    priority = Column(Integer, nullable=False, default=4)
    priority_label = Column(String(100), default="In-Situ Monitoring")
    recommended_site_id = Column(String(50), ForeignKey("candidate_relocation_sites.id"), nullable=True)

    # PostGIS Geospatial Column: Geographic Point (SRID 4326, WGS84: longitude, latitude)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    district_rel = relationship("District", back_populates="habitations")
    recommended_site = relationship("CandidateRelocationSite", back_populates="assigned_habitations")
    ai_factors = relationship("HabitationAiFactor", back_populates="habitation", cascade="all, delete-orphan")


class HabitationAiFactor(Base):
    """Explainable AI / TreeSHAP factor attributions for a vulnerable settlement."""
    __tablename__ = "habitation_ai_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    habitation_id = Column(String(50), ForeignKey("habitations.id", ondelete="CASCADE"), nullable=False)
    factor = Column(String(150), nullable=False)
    impact = Column(String(50), nullable=False)
    direction = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, default=0.0)

    # Relationships
    habitation = relationship("Habitation", back_populates="ai_factors")


class CandidateRelocationSite(Base):
    """Audited candidate safe parcel for proactive population resettlement."""
    __tablename__ = "candidate_relocation_sites"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    district_id = Column(String(50), ForeignKey("districts.id"), nullable=True)
    district_name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)

    # Spatial buffer & Land Metrics
    distance_from_red_zone_km = Column(Float, default=0.0)
    usable_area_sqm = Column(Float, nullable=False, default=0.0)
    usable_area_acres = Column(Float, default=0.0)
    estimated_capacity = Column(Integer, nullable=False, default=0)
    slope_degree = Column(Float, default=0.0)

    # AHP Suitability Engine Metrics
    suitability_score = Column(Float, nullable=False, default=0.0)
    overall_recommendation = Column(String(100), default="Suitable")
    factor_hazard_safety = Column(Integer, default=80)
    factor_accessibility = Column(Integer, default=80)
    factor_land_suitability = Column(Integer, default=80)
    factor_water_availability = Column(Integer, default=80)
    factor_healthcare_access = Column(Integer, default=80)
    factor_education_access = Column(Integer, default=80)
    factor_carrying_capacity = Column(Integer, default=80)

    # Carrying Capacity Engine Metrics
    capacity_status = Column(String(50), default="Optimal")
    carrying_capacity_factor = Column(Float, default=1.0)
    water_availability_status = Column(String(255), nullable=True)
    distance_to_road_m = Column(Float, default=0.0)
    road_accessibility = Column(String(255), nullable=True)
    distance_to_hospital_km = Column(Float, default=0.0)
    healthcare_status = Column(String(255), nullable=True)
    distance_to_school_km = Column(Float, default=0.0)
    schooling_status = Column(String(255), nullable=True)
    power_grid_access = Column(String(255), nullable=True)

    # Allocated metrics
    allocated_population = Column(Integer, default=0)
    maximum_absorption = Column(Integer, default=0)
    remaining_capacity = Column(Integer, default=0)
    utilization_percent = Column(Float, default=0.0)
    potable_water_daily_needed_kl = Column(Float, default=0.0)
    potable_water_daily_supplied_kl = Column(Float, default=0.0)
    hospital_beds_required = Column(Integer, default=0)
    hospital_beds_available = Column(Integer, default=0)

    # PostGIS Geospatial Column: Geographic Point (SRID 4326, WGS84: longitude, latitude)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    district_rel = relationship("District", back_populates="relocation_sites")
    assigned_habitations = relationship("Habitation", back_populates="recommended_site")


class RedZone(Base):
    """Delineated severe hazard boundary polygon (landslide, flood, cloudburst)."""
    __tablename__ = "red_zones"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    hazard_type = Column(String(100), nullable=False)
    risk_level = Column(String(50), nullable=False, default="Critical")
    area_sq_km = Column(Float, default=0.0)
    enclosed_habitations_count = Column(Integer, default=0)
    exposed_population = Column(Integer, default=0)
    buffer_margin_m = Column(Float, default=300.0)
    primary_trigger = Column(String(255), nullable=True)

    # PostGIS Geospatial Column: Geographic Polygon / MultiPolygon (SRID 4326)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemAlert(Base):
    """Early warning system alert generated from IoT/Satellite sensor breaches."""
    __tablename__ = "system_alerts"

    id = Column(String(50), primary_key=True)
    severity = Column(String(30), nullable=False, default="warning")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    timestamp_text = Column(String(100), nullable=True)
    read = Column(Boolean, nullable=False, default=False)
    district = Column(String(100), nullable=False, default="Statewide")
    created_at = Column(DateTime, default=datetime.utcnow)


class DataSource(Base):
    """Registry of authoritative external data sources and ingestors."""
    __tablename__ = "data_sources"

    id = Column(String(50), primary_key=True)  # e.g., 'IMD', 'OSM_OVERPASS', 'BHUVAN_NRSC', 'OPEN_ELEVATION'
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)  # 'weather', 'geospatial', 'elevation', 'demographics', 'hazard'
    cadence = Column(String(50), nullable=False, default="on_demand")  # 'periodic', 'near_real_time', 'on_demand', 'static', 'wms'
    endpoint_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ingestion_runs = relationship("DataIngestionRun", back_populates="source", cascade="all, delete-orphan")


class DataIngestionRun(Base):
    """Audit ledger for external API sync operations and batch runs."""
    __tablename__ = "data_ingestion_runs"

    id = Column(String(60), primary_key=True)  # UUID string
    source_id = Column(String(50), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), nullable=False, default="running")  # 'running', 'completed', 'partial', 'failed'
    records_ingested = Column(Integer, default=0, nullable=False)
    records_updated = Column(Integer, default=0, nullable=False)
    records_failed = Column(Integer, default=0, nullable=False)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    source = relationship("DataSource", back_populates="ingestion_runs")


class WeatherObservation(Base):
    """Meteorological telemetry ingested from IMD or local AWS stations."""
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(50), ForeignKey("data_sources.id"), nullable=False)
    district_name = Column(String(100), nullable=False)
    station_id = Column(String(50), nullable=False)
    station_name = Column(String(150), nullable=True)
    temperature_c = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    weather_condition = Column(String(100), nullable=True)
    warning_level = Column(String(50), default="Green", nullable=False)  # 'Green', 'Yellow', 'Orange', 'Red'
    warning_text = Column(Text, nullable=True)
    observed_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_fallback = Column(Boolean, default=False, nullable=False)

    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("station_id", "observed_at", name="uq_weather_station_observed"),
    )


class RainfallObservation(Base):
    """Hyetometric rainfall observations and anomaly metrics (IMD)."""
    __tablename__ = "rainfall_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(50), ForeignKey("data_sources.id"), nullable=False)
    district_name = Column(String(100), nullable=False)
    station_id = Column(String(50), nullable=False)
    station_name = Column(String(150), nullable=True)
    rainfall_24h_mm = Column(Float, default=0.0, nullable=False)
    rainfall_72h_mm = Column(Float, default=0.0, nullable=False)
    rainfall_anomaly_percent = Column(Float, default=0.0, nullable=False)
    observed_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_fallback = Column(Boolean, default=False, nullable=False)

    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("station_id", "observed_at", name="uq_rainfall_station_observed"),
    )


class HazardEvent(Base):
    """Dynamic observed natural hazard event (landslide slip, flash flood, cloudburst)."""
    __tablename__ = "hazard_events"

    id = Column(String(60), primary_key=True)
    source_id = Column(String(50), ForeignKey("data_sources.id"), nullable=False)
    district_name = Column(String(100), nullable=False)
    hazard_type = Column(String(100), nullable=False)  # 'landslide', 'flash_flood', 'cloudburst'
    severity = Column(String(50), default="High", nullable=False)
    trigger_description = Column(Text, nullable=True)
    affected_radius_m = Column(Float, default=500.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    observed_at = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_fallback = Column(Boolean, default=False, nullable=False)

    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)


class InfrastructureFeature(Base):
    """Geospatial infrastructure asset ingested from OpenStreetMap (hospitals, schools, roads, waterways)."""
    __tablename__ = "infrastructure_features"

    id = Column(String(80), primary_key=True)  # e.g., 'osm:node:12345' or 'osm:way:67890'
    source_id = Column(String(50), ForeignKey("data_sources.id"), nullable=False)
    feature_type = Column(String(50), nullable=False)  # 'hospital', 'clinic', 'school', 'shelter', 'road', 'waterway'
    name = Column(String(200), nullable=True)
    district_name = Column(String(100), nullable=False)
    capacity_or_beds = Column(Integer, nullable=True)
    all_weather_access = Column(Boolean, default=True, nullable=False)
    properties_json = Column(JSON, nullable=True)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_fallback = Column(Boolean, default=False, nullable=False)


# Explicit GiST Spatial Indexes & Composite Query Indexes
Index("idx_habitations_district", Habitation.district_name)
Index("idx_habitations_risk_tier", Habitation.risk_tier)
Index("idx_habitations_priority", Habitation.priority)
Index("idx_sites_district", CandidateRelocationSite.district_name)
Index("idx_sites_suitability", CandidateRelocationSite.suitability_score)
Index("idx_alerts_read", SystemAlert.read)
Index("idx_weather_district_obs", WeatherObservation.district_name, WeatherObservation.observed_at)
Index("idx_rainfall_district_obs", RainfallObservation.district_name, RainfallObservation.observed_at)
Index("idx_hazard_district_active", HazardEvent.district_name, HazardEvent.is_active)
Index("idx_infra_type_district", InfrastructureFeature.feature_type, InfrastructureFeature.district_name)
Index("idx_ingestion_runs_source", DataIngestionRun.source_id, DataIngestionRun.started_at)
