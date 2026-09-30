import logging
from typing import Dict, Any, List, Optional
import httpx

from backend.app.core.config import settings
from backend.app.services.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class BhuvanAdapter(BaseAdapter):
    """Adapter for ISRO NRSC Bhuvan Geoportal WMS metadata and spatial layers.
    
    Treats Bhuvan as an authoritative geospatial raster/vector WMS provider.
    Never assumes WMS responses are standard JSON.
    """

    SOURCE_ID = "BHUVAN_NRSC"
    SOURCE_NAME = "ISRO NRSC Bhuvan Geoportal"

    # Known standard Bhuvan WMS hazard & thematic layers
    REGISTERED_LAYERS = [
        {
            "layer_id": "bhuvan:flood_hazard_zoning",
            "title": "Flood Hazard Zoning & Historical Inundation",
            "category": "hazard",
            "format": "image/png",
            "transparent": True,
            "version": "1.3.0",
            "srs": "EPSG:4326",
        },
        {
            "layer_id": "bhuvan:lulc_50k",
            "title": "Land Use / Land Cover 1:50,000 (NRSC)",
            "category": "thematic_land",
            "format": "image/png",
            "transparent": True,
            "version": "1.3.0",
            "srs": "EPSG:4326",
        },
        {
            "layer_id": "bhuvan:landslide_inventory",
            "title": "National Landslide Susceptibility & Past Scarps",
            "category": "hazard",
            "format": "image/png",
            "transparent": True,
            "version": "1.3.0",
            "srs": "EPSG:4326",
        },
    ]

    def __init__(self):
        super().__init__(source_id=self.SOURCE_ID, name=self.SOURCE_NAME)
        self.wms_url = getattr(settings, "BHUVAN_WMS_URL", "https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms")
        self.timeout = getattr(settings, "INGESTION_TIMEOUT_SECONDS", 15)

    async def fetch(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch WMS capabilities metadata from Bhuvan geoportal."""
        params = params or {}
        capabilities_url = f"{self.wms_url}?service=WMS&version=1.3.0&request=GetCapabilities"

        headers = {
            "User-Agent": "SIH2026-DSS-Bhuvan-Client/1.0",
            "Accept": "text/xml,application/xml,*/*",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(capabilities_url, headers=headers)
                return {
                    "status_code": res.status_code,
                    "content_type": res.headers.get("content-type", ""),
                    "capabilities_xml": res.text[:2000] if res.status_code == 200 else "",
                    "is_live": res.status_code == 200,
                }
        except Exception as exc:
            logger.warning("Bhuvan WMS GetCapabilities request failed: %s", exc)
            return {
                "status_code": 0,
                "error": str(exc),
                "is_live": False,
                "capabilities_xml": "",
            }

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize registered Bhuvan layer metadata into standard layer descriptors."""
        layers = []
        is_live = raw_data.get("is_live", False) if isinstance(raw_data, dict) else False

        for layer_def in self.REGISTERED_LAYERS:
            layers.append({
                "source_id": self.SOURCE_ID,
                "layer_id": layer_def["layer_id"],
                "title": layer_def["title"],
                "category": layer_def["category"],
                "wms_url": self.wms_url,
                "wms_options": {
                    "layers": layer_def["layer_id"],
                    "format": layer_def["format"],
                    "transparent": layer_def["transparent"],
                    "version": layer_def["version"],
                    "attribution": "© ISRO / NRSC Bhuvan Geoportal",
                },
                "is_endpoint_live": is_live,
                "is_fallback": not is_live,
            })

        return layers

    def validate(self, normalized_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate layer specifications have requisite WMS parameters."""
        valid_records = []
        for rec in normalized_records:
            if rec.get("layer_id") and rec.get("wms_url") and rec.get("wms_options"):
                valid_records.append(rec)
        return valid_records

    async def health_check(self) -> Dict[str, Any]:
        """Verify Bhuvan WMS endpoint reachability."""
        if not self.wms_url:
            return {"configured": False, "status": "unconfigured", "message": "BHUVAN_WMS_URL not set"}

        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 5)) as client:
                res = await client.get(self.wms_url)
                # WMS servers often respond 200, 400 (missing parameters), or 404 to bare root
                is_accessible = res.status_code in (200, 400)
                return {
                    "configured": True,
                    "status": "healthy" if is_accessible else "unreachable",
                    "http_status": res.status_code,
                    "wms_url": self.wms_url,
                }
        except Exception as exc:
            return {
                "configured": True,
                "status": "unreachable",
                "error": str(exc),
                "wms_url": self.wms_url,
            }
