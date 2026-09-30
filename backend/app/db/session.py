import logging
from typing import Optional, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.config import settings
from backend.app.models.orm_models import Base

logger = logging.getLogger(__name__)

# Engine and sessionmaker singletons
_engine = None
_SessionLocal = None


def get_database_url() -> Optional[str]:
    """Retrieve DATABASE_URL from settings or environment."""
    return settings.DATABASE_URL


def init_db_engine():
    """Initializes the SQLAlchemy synchronous engine if DATABASE_URL is configured."""
    global _engine, _SessionLocal
    db_url = get_database_url()

    if not db_url:
        logger.info("No DATABASE_URL configured. Supabase database engine not initialized.")
        return None

    # Handle Postgres URL dialect prefix if needed (e.g., postgres:// -> postgresql://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        _engine = create_engine(
            db_url,
            pool_size=getattr(settings, "DB_POOL_SIZE", 10),
            max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 5),
            pool_timeout=15,
            pool_recycle=300,
            pool_pre_ping=True,
            connect_args={"connect_timeout": min(getattr(settings, "DB_TIMEOUT_SECONDS", 10), 2)},
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Supabase PostgreSQL/PostGIS engine initialized successfully.")
        return _engine
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")
        _engine = None
        _SessionLocal = None
        return None


def warm_connection_pool(concurrency: int = 3):
    """Pre-establishes connections in the pool during startup to eliminate cold handshake latency."""
    engine = get_engine()
    if not engine:
        return
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            for _ in range(concurrency):
                executor.submit(engine.connect)
    except Exception as e:
        logger.debug(f"Connection pool warm-up skipped or non-critical: {e}")


def get_engine():
    """Returns initialized database engine or initializes lazily."""
    global _engine
    if _engine is None and get_database_url():
        return init_db_engine()
    return _engine


def get_session_factory():
    """Returns sessionmaker singleton."""
    global _SessionLocal
    if _SessionLocal is None and get_database_url():
        init_db_engine()
    return _SessionLocal


def get_db_session() -> Generator[Optional[Session], None, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    global _SessionLocal
    if _SessionLocal is None and get_database_url():
        init_db_engine()

    if _SessionLocal is None:
        yield None
        return

    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


_last_health_check = None
_last_health_time = 0.0
HEALTH_CACHE_TTL = 30.0


def check_db_health() -> dict:
    """Evaluates database and PostGIS extension health with short TTL caching to prevent request latency when offline."""
    global _last_health_check, _last_health_time
    import time
    now = time.time()
    if _last_health_check is not None and (now - _last_health_time < HEALTH_CACHE_TTL):
        return _last_health_check

    engine = get_engine()
    if not engine:
        _last_health_check = {
            "configured": False,
            "status": "unconfigured",
            "message": "DATABASE_URL environment variable is not set. System using in-memory mock repository fallback.",
            "postgis_available": False,
        }
        _last_health_time = now
        return _last_health_check

    try:
        with engine.connect() as conn:
            # 1. Test basic connectivity
            conn.execute(text("SELECT 1"))

            # 2. Test PostGIS extension
            try:
                result = conn.execute(text("SELECT PostGIS_Full_Version()")).scalar()
                postgis_available = True
                postgis_version = str(result)
            except Exception:
                postgis_available = False
                postgis_version = "PostGIS extension not active or installed"

            _last_health_check = {
                "configured": True,
                "status": "healthy",
                "postgis_available": postgis_available,
                "postgis_version": postgis_version,
                "message": "Successfully connected to Supabase PostgreSQL/PostGIS.",
            }
            _last_health_time = now
            return _last_health_check
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        _last_health_check = {
            "configured": True,
            "status": "unhealthy",
            "error": str(exc),
            "message": "Database connection attempt failed. Falling back to in-memory repository.",
            "postgis_available": False,
        }
        _last_health_time = now
        return _last_health_check
