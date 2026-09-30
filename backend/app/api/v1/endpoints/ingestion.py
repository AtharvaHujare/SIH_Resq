import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.app.models.schemas import (
    IngestionStatusResponse,
    SyncResponse,
    SyncImdRequest,
    SyncOsmRequest,
)
from backend.app.services.ingestion_service import ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion & Provenance"])


@router.get("/status", response_model=IngestionStatusResponse, summary="Get authoritative data sources and sync status")
def get_ingestion_status():
    """Returns configuration status, data provenance modes, observation counts, and audit ledger."""
    return ingestion_service.get_ingestion_status()


@router.post("/sync/imd", response_model=SyncResponse, summary="Trigger manual IMD weather and rainfall sync")
async def sync_imd(payload: Optional[SyncImdRequest] = None):
    """Fetches, validates, and idempotently upserts real-world IMD observations."""
    district = payload.district if payload else None
    result = await ingestion_service.sync_imd(district=district)
    return result


@router.post("/sync/osm", response_model=SyncResponse, summary="Trigger manual OpenStreetMap infrastructure sync")
async def sync_osm(payload: Optional[SyncOsmRequest] = None):
    """Fetches and idempotently upserts OSM infrastructure assets (hospitals, schools, roads, waterways)."""
    bbox = tuple(payload.bbox) if payload and payload.bbox and len(payload.bbox) == 4 else None
    result = await ingestion_service.sync_osm(bbox=bbox)
    return result


@router.post("/sync/bhuvan", response_model=SyncResponse, summary="Trigger Bhuvan WMS capabilities verification")
async def sync_bhuvan():
    """Queries ISRO NRSC Bhuvan WMS capabilities and verifies thematic hazard layers."""
    result = await ingestion_service.sync_bhuvan()
    return result


@router.post("/sync/all", summary="Trigger multi-source ingestion sync")
async def sync_all():
    """Triggers end-to-end sync across all configured authoritative external data sources."""
    imd_res = await ingestion_service.sync_imd()
    bhuvan_res = await ingestion_service.sync_bhuvan()
    osm_res = await ingestion_service.sync_osm()

    return {
        "status": "completed",
        "results": {
            "IMD": imd_res,
            "BHUVAN_NRSC": bhuvan_res,
            "OSM_OVERPASS": osm_res,
        },
    }
