from typing import List, Optional
from fastapi import APIRouter, Query

from backend.app.services.gis_engine import gis_engine
from backend.app.models.schemas import RedZoneResponse, SafeZoneCollectionResponse

router = APIRouter(prefix="/hazards", tags=["Hazards & Red Zones"])


@router.get("/red-zones", response_model=List[RedZoneResponse], summary="Get delineated active hazard red zones")
def get_red_zones(
    district: Optional[str] = Query(None, description="Optional district name filter"),
):
    """Returns spatial polygons and risk metrics for severe landslide, flash flood, and cloudburst zones.
    Derives dynamic buffer margins and spatial polygons from PostGIS when available, with verified prototype fallback.
    """
    return gis_engine.get_dynamic_red_zones(district=district)


@router.get("/safe-zones", response_model=SafeZoneCollectionResponse, summary="Get dynamic candidate safe green zones")
def get_safe_zones(
    district: Optional[str] = Query(None, description="Optional district name filter"),
):
    """Returns standard GeoJSON FeatureCollection of candidate safe green parcels derived
    using multi-criteria GIS exclusion rules (zero red-zone overlap, gentle slope, road access, and capacity headroom).
    """
    return gis_engine.get_dynamic_safe_zones(district=district)
