import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, update, text
from sqlalchemy.orm import Session
from shapely.geometry import Point, LineString
from geoalchemy2.shape import from_shape

from backend.app.db.session import get_engine, check_db_health
from backend.app.models.orm_models import (
    DataSource,
    DataIngestionRun,
    WeatherObservation,
    RainfallObservation,
    InfrastructureFeature,
)
from backend.app.services.adapters.imd_adapter import IMDAdapter
from backend.app.services.adapters.osm_adapter import OSMAdapter
from backend.app.services.adapters.bhuvan_adapter import BhuvanAdapter

logger = logging.getLogger(__name__)


class IngestionService:
    """Central orchestrator for authoritative external data ingestion, validation, and idempotent upserts."""

    def __init__(self):
        self.imd_adapter = IMDAdapter()
        self.osm_adapter = OSMAdapter()
        self.bhuvan_adapter = BhuvanAdapter()

        # In-memory run ledger for when database is in mock fallback mode
        self._mock_runs: List[Dict[str, Any]] = []

    def _is_db_active(self) -> bool:
        """Check if live database connection is operational."""
        health = check_db_health()
        return health.get("status") == "healthy"

    def _create_run(self, source_id: str) -> str:
        """Record the start of a new ingestion run."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        if self._is_db_active():
            try:
                engine = get_engine()
                with Session(engine) as session:
                    run = DataIngestionRun(
                        id=run_id,
                        source_id=source_id,
                        status="running",
                        records_ingested=0,
                        records_updated=0,
                        records_failed=0,
                        started_at=now,
                    )
                    session.add(run)
                    session.commit()
                    return run_id
            except Exception as exc:
                logger.warning("Failed to record run in database: %s", exc)

        # Fallback tracking
        self._mock_runs.append({
            "id": run_id,
            "source_id": source_id,
            "status": "running",
            "records_ingested": 0,
            "records_updated": 0,
            "records_failed": 0,
            "error_log": None,
            "started_at": now.isoformat(),
            "completed_at": None,
        })
        return run_id

    def _complete_run(
        self,
        run_id: str,
        source_id: str,
        status: str,
        ingested: int,
        updated: int,
        failed: int,
        error_log: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record the completion of an ingestion run and update source metadata."""
        now = datetime.now(timezone.utc)

        if self._is_db_active():
            try:
                engine = get_engine()
                with Session(engine) as session:
                    # Update ingestion run
                    session.execute(
                        update(DataIngestionRun)
                        .where(DataIngestionRun.id == run_id)
                        .values(
                            status=status,
                            records_ingested=ingested,
                            records_updated=updated,
                            records_failed=failed,
                            error_log=error_log,
                            completed_at=now,
                        )
                    )

                    # Update data source last sync
                    session.execute(
                        update(DataSource)
                        .where(DataSource.id == source_id)
                        .values(
                            last_sync_at=now,
                            last_sync_status=status,
                        )
                    )
                    session.commit()
            except Exception as exc:
                logger.warning("Failed to finalize run in database: %s", exc)

        # Update in-memory fallback
        for r in self._mock_runs:
            if r["id"] == run_id:
                r["status"] = status
                r["records_ingested"] = ingested
                r["records_updated"] = updated
                r["records_failed"] = failed
                r["error_log"] = error_log
                r["completed_at"] = now.isoformat()
                break

        return {
            "run_id": run_id,
            "source": source_id,
            "status": status,
            "records_ingested": ingested,
            "records_updated": updated,
            "records_failed": failed,
            "error_summary": error_log,
            "completed_at": now.isoformat(),
        }

    # ==========================================================================
    # 1. IMD Sync (Weather & Rainfall)
    # ==========================================================================
    async def sync_imd(self, district: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrate IMD weather and rainfall observations ingestion."""
        run_id = self._create_run(IMDAdapter.SOURCE_ID)
        params = {"district": district} if district else {}

        try:
            raw_data = await self.imd_adapter.fetch(params)
        except Exception as exc:
            logger.warning("IMD fetch failed for run %s: %s", run_id, exc)
            return self._complete_run(
                run_id, IMDAdapter.SOURCE_ID, "failed", 0, 0, 0, error_log=f"Fetch failed: {exc}"
            )

        try:
            normalized = self.imd_adapter.normalize(raw_data)
            validated = self.imd_adapter.validate(normalized)
        except Exception as exc:
            logger.warning("IMD normalization/validation failed: %s", exc)
            return self._complete_run(
                run_id, IMDAdapter.SOURCE_ID, "failed", 0, 0, 0, error_log=f"Validation failed: {exc}"
            )

        weather_list = validated.get("weather", [])
        rainfall_list = validated.get("rainfall", [])

        ingested_count = 0
        updated_count = 0
        failed_count = 0

        if self._is_db_active():
            try:
                engine = get_engine()
                with Session(engine) as session:
                    # 1. Upsert weather observations
                    for w in weather_list:
                        try:
                            stmt = select(WeatherObservation).where(
                                WeatherObservation.station_id == w["station_id"],
                                WeatherObservation.observed_at == w["observed_at"],
                            )
                            existing = session.scalars(stmt).first()

                            geom_val = None
                            if w.get("coordinates"):
                                lon, lat = w["coordinates"]
                                geom_val = from_shape(Point(lon, lat), srid=4326)

                            if existing:
                                existing.temperature_c = w["temperature_c"]
                                existing.humidity_percent = w["humidity_percent"]
                                existing.wind_speed_kmh = w["wind_speed_kmh"]
                                existing.weather_condition = w["weather_condition"]
                                existing.warning_level = w["warning_level"]
                                existing.warning_text = w["warning_text"]
                                existing.ingested_at = datetime.now(timezone.utc)
                                existing.geom = geom_val
                                updated_count += 1
                            else:
                                new_obs = WeatherObservation(
                                    source_id=w["source_id"],
                                    district_name=w["district_name"],
                                    station_id=w["station_id"],
                                    station_name=w["station_name"],
                                    temperature_c=w["temperature_c"],
                                    humidity_percent=w["humidity_percent"],
                                    wind_speed_kmh=w["wind_speed_kmh"],
                                    weather_condition=w["weather_condition"],
                                    warning_level=w["warning_level"],
                                    warning_text=w["warning_text"],
                                    observed_at=w["observed_at"],
                                    ingested_at=w["ingested_at"],
                                    is_fallback=w["is_fallback"],
                                    geom=geom_val,
                                )
                                session.add(new_obs)
                                ingested_count += 1
                        except Exception as w_exc:
                            logger.warning("Failed to upsert weather record: %s", w_exc)
                            failed_count += 1

                    # 2. Upsert rainfall observations
                    for r in rainfall_list:
                        try:
                            stmt = select(RainfallObservation).where(
                                RainfallObservation.station_id == r["station_id"],
                                RainfallObservation.observed_at == r["observed_at"],
                            )
                            existing = session.scalars(stmt).first()

                            geom_val = None
                            if r.get("coordinates"):
                                lon, lat = r["coordinates"]
                                geom_val = from_shape(Point(lon, lat), srid=4326)

                            if existing:
                                existing.rainfall_24h_mm = r["rainfall_24h_mm"]
                                existing.rainfall_72h_mm = r["rainfall_72h_mm"]
                                existing.rainfall_anomaly_percent = r["rainfall_anomaly_percent"]
                                existing.ingested_at = datetime.now(timezone.utc)
                                existing.geom = geom_val
                                updated_count += 1
                            else:
                                new_rf = RainfallObservation(
                                    source_id=r["source_id"],
                                    district_name=r["district_name"],
                                    station_id=r["station_id"],
                                    station_name=r["station_name"],
                                    rainfall_24h_mm=r["rainfall_24h_mm"],
                                    rainfall_72h_mm=r["rainfall_72h_mm"],
                                    rainfall_anomaly_percent=r["rainfall_anomaly_percent"],
                                    observed_at=r["observed_at"],
                                    ingested_at=r["ingested_at"],
                                    is_fallback=r["is_fallback"],
                                    geom=geom_val,
                                )
                                session.add(new_rf)
                                ingested_count += 1
                        except Exception as r_exc:
                            logger.warning("Failed to upsert rainfall record: %s", r_exc)
                            failed_count += 1

                    session.commit()
            except Exception as db_exc:
                logger.error("Database transaction error during IMD sync: %s", db_exc)
                return self._complete_run(
                    run_id, IMDAdapter.SOURCE_ID, "failed", ingested_count, updated_count, failed_count,
                    error_log=f"Database error: {db_exc}"
                )
        else:
            # Fallback mock mode counts
            ingested_count = len(weather_list) + len(rainfall_list)

        total_processed = ingested_count + updated_count
        status = "completed" if failed_count == 0 and total_processed > 0 else ("partial" if total_processed > 0 else "failed")
        return self._complete_run(run_id, IMDAdapter.SOURCE_ID, status, ingested_count, updated_count, failed_count)

    # ==========================================================================
    # 2. OSM Sync (Infrastructure Features)
    # ==========================================================================
    async def sync_osm(self, bbox: Optional[Tuple[float, float, float, float]] = None) -> Dict[str, Any]:
        """Orchestrate OpenStreetMap infrastructure ingestion for safe parcel analysis."""
        run_id = self._create_run(OSMAdapter.SOURCE_ID)
        params = {"bbox": bbox} if bbox else {}

        try:
            raw_data = await self.osm_adapter.fetch(params)
        except Exception as exc:
            logger.warning("OSM fetch failed for run %s: %s", run_id, exc)
            return self._complete_run(
                run_id, OSMAdapter.SOURCE_ID, "failed", 0, 0, 0, error_log=f"Fetch failed: {exc}"
            )

        try:
            normalized = self.osm_adapter.normalize(raw_data)
            validated = self.osm_adapter.validate(normalized)
        except Exception as exc:
            logger.warning("OSM normalization/validation failed: %s", exc)
            return self._complete_run(
                run_id, OSMAdapter.SOURCE_ID, "failed", 0, 0, 0, error_log=f"Validation failed: {exc}"
            )

        ingested_count = 0
        updated_count = 0
        failed_count = 0

        if self._is_db_active():
            try:
                engine = get_engine()
                with Session(engine) as session:
                    for feat in validated:
                        try:
                            stmt = select(InfrastructureFeature).where(InfrastructureFeature.id == feat["id"])
                            existing = session.scalars(stmt).first()

                            # Build geometry
                            geom_val = None
                            coords = feat.get("coordinates")
                            if coords:
                                if feat.get("geometry_type") == "POINT":
                                    geom_val = from_shape(Point(coords[0], coords[1]), srid=4326)
                                elif feat.get("geometry_type") == "LINESTRING" and len(coords) >= 2:
                                    geom_val = from_shape(LineString(coords), srid=4326)

                            if existing:
                                existing.name = feat["name"]
                                existing.feature_type = feat["feature_type"]
                                existing.capacity_or_beds = feat["capacity_or_beds"]
                                existing.all_weather_access = feat["all_weather_access"]
                                existing.properties_json = feat["properties_json"]
                                existing.ingested_at = datetime.now(timezone.utc)
                                existing.geom = geom_val
                                updated_count += 1
                            else:
                                new_feat = InfrastructureFeature(
                                    id=feat["id"],
                                    source_id=feat["source_id"],
                                    feature_type=feat["feature_type"],
                                    name=feat["name"],
                                    district_name=feat["district_name"],
                                    capacity_or_beds=feat["capacity_or_beds"],
                                    all_weather_access=feat["all_weather_access"],
                                    properties_json=feat["properties_json"],
                                    geom=geom_val,
                                    ingested_at=datetime.now(timezone.utc),
                                    is_fallback=feat["is_fallback"],
                                )
                                session.add(new_feat)
                                ingested_count += 1
                        except Exception as feat_exc:
                            logger.warning("Failed to upsert OSM feature %s: %s", feat.get("id"), feat_exc)
                            failed_count += 1

                    session.commit()
            except Exception as db_exc:
                logger.error("Database error during OSM sync: %s", db_exc)
                return self._complete_run(
                    run_id, OSMAdapter.SOURCE_ID, "failed", ingested_count, updated_count, failed_count,
                    error_log=f"Database error: {db_exc}"
                )
        else:
            ingested_count = len(validated)

        total_processed = ingested_count + updated_count
        status = "completed" if failed_count == 0 and total_processed > 0 else ("partial" if total_processed > 0 else "failed")
        return self._complete_run(run_id, OSMAdapter.SOURCE_ID, status, ingested_count, updated_count, failed_count)

    # ==========================================================================
    # 3. Bhuvan Sync (WMS Metadata Verification)
    # ==========================================================================
    async def sync_bhuvan(self) -> Dict[str, Any]:
        """Query Bhuvan WMS capabilities and refresh verified layer metadata in registry."""
        run_id = self._create_run(BhuvanAdapter.SOURCE_ID)

        try:
            raw_data = await self.bhuvan_adapter.fetch()
            normalized = self.bhuvan_adapter.normalize(raw_data)
            validated = self.bhuvan_adapter.validate(normalized)
        except Exception as exc:
            logger.warning("Bhuvan sync failed: %s", exc)
            return self._complete_run(
                run_id, BhuvanAdapter.SOURCE_ID, "failed", 0, 0, 0, error_log=f"Capabilities check failed: {exc}"
            )

        is_live = raw_data.get("is_live", False)
        status = "completed" if is_live else "partial"
        error_msg = None if is_live else "Bhuvan WMS endpoint returned non-200; registered layers preserved as fallback."

        # Update metadata in DataSource
        if self._is_db_active():
            try:
                engine = get_engine()
                with Session(engine) as session:
                    session.execute(
                        update(DataSource)
                        .where(DataSource.id == BhuvanAdapter.SOURCE_ID)
                        .values(
                            metadata_json={"registered_layers": validated, "is_live": is_live},
                            last_sync_at=datetime.now(timezone.utc),
                            last_sync_status=status,
                        )
                    )
                    session.commit()
            except Exception as db_exc:
                logger.warning("Could not persist Bhuvan metadata in DB: %s", db_exc)

        return self._complete_run(
            run_id, BhuvanAdapter.SOURCE_ID, status, len(validated), 0, 0, error_log=error_msg
        )

    # ==========================================================================
    # 4. Status & Audit Queries
    # ==========================================================================
    def get_ingestion_status(self) -> Dict[str, Any]:
        """Aggregate configuration, provenance status, and recent sync telemetry across all data sources."""
        sources = []
        is_db = self._is_db_active()

        if is_db:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    ds_list = session.scalars(select(DataSource).order_by(DataSource.id)).all()
                    for ds in ds_list:
                        sources.append({
                            "id": ds.id,
                            "name": ds.name,
                            "category": ds.category,
                            "cadence": ds.cadence,
                            "endpointUrl": ds.endpoint_url,
                            "isActive": ds.is_active,
                            "lastSyncAt": ds.last_sync_at.isoformat() if ds.last_sync_at else None,
                            "lastSyncStatus": ds.last_sync_status or "Never Synced",
                            "provenanceClassification": "LIVE/EXTERNAL DATA" if ds.last_sync_status == "completed" else "PROTOTYPE FALLBACK",
                        })
            except Exception as exc:
                logger.warning("Failed to fetch sources from DB: %s", exc)

        if not sources:
            # Fallback status representation
            sources = [
                {
                    "id": "IMD",
                    "name": "India Meteorological Department",
                    "category": "weather",
                    "cadence": "near_real_time",
                    "endpointUrl": getattr(settings, "IMD_API_URL", "https://mausam.imd.gov.in/api"),
                    "isActive": True,
                    "lastSyncAt": None,
                    "lastSyncStatus": "Standby",
                    "provenanceClassification": "PROTOTYPE FALLBACK",
                },
                {
                    "id": "OSM_OVERPASS",
                    "name": "OpenStreetMap Overpass API",
                    "category": "geospatial",
                    "cadence": "on_demand",
                    "endpointUrl": getattr(settings, "OVERPASS_API_URL", "https://overpass-api.de/api/interpreter"),
                    "isActive": True,
                    "lastSyncAt": None,
                    "lastSyncStatus": "Standby",
                    "provenanceClassification": "PROTOTYPE FALLBACK",
                },
                {
                    "id": "BHUVAN_NRSC",
                    "name": "ISRO NRSC Bhuvan Geoportal",
                    "category": "hazard",
                    "cadence": "wms",
                    "endpointUrl": getattr(settings, "BHUVAN_WMS_URL", "https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms"),
                    "isActive": True,
                    "lastSyncAt": None,
                    "lastSyncStatus": "Standby",
                    "provenanceClassification": "PROTOTYPE FALLBACK",
                },
                {
                    "id": "OPEN_ELEVATION",
                    "name": "Digital Elevation Model Service",
                    "category": "elevation",
                    "cadence": "on_demand",
                    "endpointUrl": getattr(settings, "ELEVATION_API_URL", "https://api.open-elevation.com/api/v1/lookup"),
                    "isActive": True,
                    "lastSyncAt": None,
                    "lastSyncStatus": "Standby",
                    "provenanceClassification": "PROTOTYPE FALLBACK",
                },
                {
                    "id": "CENSUS_INDIA",
                    "name": "Office of Registrar General & Census Commissioner",
                    "category": "demographics",
                    "cadence": "static",
                    "endpointUrl": None,
                    "isActive": True,
                    "lastSyncAt": None,
                    "lastSyncStatus": "Static Baseline (2011/Survey)",
                    "provenanceClassification": "CACHED DATA",
                },
            ]

        # Ingestion counts summary
        total_weather = 0
        total_rainfall = 0
        total_infra = 0
        if is_db:
            try:
                engine = get_engine()
                with Session(engine) as session:
                    total_weather = session.execute(text("SELECT count(*) FROM weather_observations")).scalar() or 0
                    total_rainfall = session.execute(text("SELECT count(*) FROM rainfall_observations")).scalar() or 0
                    total_infra = session.execute(text("SELECT count(*) FROM infrastructure_features")).scalar() or 0
            except Exception:
                pass

        return {
            "status": "operational",
            "databaseConnected": is_db,
            "dataProvenanceMode": "LIVE_AND_CACHED_POSTGIS" if is_db else "IN_MEMORY_PROTOTYPE_FALLBACK",
            "summary": {
                "weatherObservationsCount": total_weather,
                "rainfallObservationsCount": total_rainfall,
                "infrastructureFeaturesCount": total_infra,
            },
            "sources": sources,
            "recentRuns": self._mock_runs[-5:] if not is_db else self._get_db_recent_runs(),
        }

    def _get_db_recent_runs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Query recent ingestion runs from database."""
        try:
            engine = get_engine()
            with Session(engine) as session:
                runs = session.scalars(
                    select(DataIngestionRun).order_by(DataIngestionRun.started_at.desc()).limit(limit)
                ).all()
                return [
                    {
                        "id": r.id,
                        "sourceId": r.source_id,
                        "status": r.status,
                        "recordsIngested": r.records_ingested,
                        "recordsUpdated": r.records_updated,
                        "recordsFailed": r.records_failed,
                        "startedAt": r.started_at.isoformat() if r.started_at else None,
                        "completedAt": r.completed_at.isoformat() if r.completed_at else None,
                        "errorSummary": r.error_log,
                    }
                    for r in runs
                ]
        except Exception:
            return []


ingestion_service = IngestionService()
