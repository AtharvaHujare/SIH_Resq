import os
import re
import urllib.parse
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import dotenv_values


def _find_env_candidates() -> List[str]:
    """Discovers .env files across project and workspace parent folders."""
    cur = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    p = cur
    for _ in range(6):
        env_path = os.path.join(p, ".env")
        if os.path.exists(env_path):
            candidates.append(env_path)
        p = os.path.dirname(p)
    return candidates


def _get_raw_database_url() -> Optional[str]:
    """Extract raw DATABASE_URL from environment or discovered .env files."""
    if os.environ.get("DATABASE_URL"):
        return os.environ.get("DATABASE_URL")
    for env_file in _find_env_candidates():
        vals = dotenv_values(env_file)
        if vals.get("DATABASE_URL"):
            return vals["DATABASE_URL"]
    return None


class Settings(BaseSettings):
    # Application Metadata
    APP_NAME: str = "Intelligent GIS-Based Proactive Relocation DSS API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database Mode Flags
    USE_DATABASE: bool = True
    DB_FIRST_MODE: bool = True

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Database Configuration (Supabase PostgreSQL / PostGIS)
    DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT_SECONDS: int = 10

    # Coordinate Reference System (CRS) Settings
    DEFAULT_STORAGE_CRS: str = "EPSG:4326"
    DEFAULT_PROJECTED_CRS: str = "EPSG:32643"

    # External Data Sources & Ingestion Configuration
    IMD_API_URL: str = "https://mausam.imd.gov.in/api"
    IMD_API_KEY: Optional[str] = None
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    BHUVAN_WMS_URL: str = "https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms"
    ELEVATION_API_URL: str = "https://api.open-elevation.com/api/v1/lookup"
    ELEVATION_API_KEY: Optional[str] = None
    INGESTION_TIMEOUT_SECONDS: int = 15
    DEFAULT_BUFFER_METERS: float = 300.0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Optional[str]) -> Optional[str]:
        raw = v or _get_raw_database_url()
        if not raw:
            return None
        if raw.startswith("postgres://"):
            raw = raw.replace("postgres://", "postgresql://", 1)
        # URL encode password if contains unescaped @
        match = re.match(r"^(postgresql://[^:]+:)(.*)(@[^@]+)$", raw)
        if match:
            prefix, pwd, host_part = match.groups()
            if "@" in pwd:
                raw = f"{prefix}{urllib.parse.quote_plus(pwd)}{host_part}"
        return raw

    model_config = SettingsConfigDict(
        env_file=tuple(_find_env_candidates()) if _find_env_candidates() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

