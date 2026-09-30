"""create_data_ingestion_and_provenance_tables

Revision ID: 0002_data_ingestion_core
Revises: 0001_initial_schema
Create Date: 2026-09-11 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = '0002_data_ingestion_core'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Table: data_sources
    op.create_table(
        'data_sources',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('cadence', sa.String(length=50), nullable=False, server_default='on_demand'),
        sa.Column('endpoint_url', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(length=50), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Table: data_ingestion_runs
    op.create_table(
        'data_ingestion_runs',
        sa.Column('id', sa.String(length=60), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='running'),
        sa.Column('records_ingested', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ingestion_runs_source', 'data_ingestion_runs', ['source_id', 'started_at'], unique=False)

    # 3. Table: weather_observations
    op.create_table(
        'weather_observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('district_name', sa.String(length=100), nullable=False),
        sa.Column('station_id', sa.String(length=50), nullable=False),
        sa.Column('station_name', sa.String(length=150), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('humidity_percent', sa.Float(), nullable=True),
        sa.Column('wind_speed_kmh', sa.Float(), nullable=True),
        sa.Column('weather_condition', sa.String(length=100), nullable=True),
        sa.Column('warning_level', sa.String(length=50), nullable=False, server_default='Green'),
        sa.Column('warning_text', sa.Text(), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('ingested_at', sa.DateTime(), nullable=False),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'observed_at', name='uq_weather_station_observed')
    )
    op.create_index('idx_weather_district_obs', 'weather_observations', ['district_name', 'observed_at'], unique=False)

    # 4. Table: rainfall_observations
    op.create_table(
        'rainfall_observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('district_name', sa.String(length=100), nullable=False),
        sa.Column('station_id', sa.String(length=50), nullable=False),
        sa.Column('station_name', sa.String(length=150), nullable=True),
        sa.Column('rainfall_24h_mm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rainfall_72h_mm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rainfall_anomaly_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('ingested_at', sa.DateTime(), nullable=False),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_id', 'observed_at', name='uq_rainfall_station_observed')
    )
    op.create_index('idx_rainfall_district_obs', 'rainfall_observations', ['district_name', 'observed_at'], unique=False)

    # 5. Table: hazard_events
    op.create_table(
        'hazard_events',
        sa.Column('id', sa.String(length=60), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('district_name', sa.String(length=100), nullable=False),
        sa.Column('hazard_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='High'),
        sa.Column('trigger_description', sa.Text(), nullable=True),
        sa.Column('affected_radius_m', sa.Float(), nullable=False, server_default='500.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('ingested_at', sa.DateTime(), nullable=False),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_hazard_district_active', 'hazard_events', ['district_name', 'is_active'], unique=False)

    # 6. Table: infrastructure_features
    op.create_table(
        'infrastructure_features',
        sa.Column('id', sa.String(length=80), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('feature_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('district_name', sa.String(length=100), nullable=False),
        sa.Column('capacity_or_beds', sa.Integer(), nullable=True),
        sa.Column('all_weather_access', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('properties_json', sa.JSON(), nullable=True),
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=True), nullable=True),
        sa.Column('ingested_at', sa.DateTime(), nullable=False),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_infra_type_district', 'infrastructure_features', ['feature_type', 'district_name'], unique=False)

    # 7. Seed Authoritative Data Sources
    op.execute("""
        INSERT INTO data_sources (id, name, category, cadence, endpoint_url, is_active, created_at, updated_at)
        VALUES 
            ('IMD', 'India Meteorological Department', 'weather', 'near_real_time', 'https://mausam.imd.gov.in/api', true, now(), now()),
            ('OSM_OVERPASS', 'OpenStreetMap Overpass API', 'geospatial', 'on_demand', 'https://overpass-api.de/api/interpreter', true, now(), now()),
            ('BHUVAN_NRSC', 'ISRO NRSC Bhuvan Geoportal', 'hazard', 'wms', 'https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms', true, now(), now()),
            ('OPEN_ELEVATION', 'Digital Elevation Model Service', 'elevation', 'on_demand', 'https://api.open-elevation.com/api/v1/lookup', true, now(), now()),
            ('CENSUS_INDIA', 'Office of Registrar General & Census Commissioner', 'demographics', 'static', NULL, true, now(), now())
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('idx_infra_type_district', table_name='infrastructure_features')
    op.drop_table('infrastructure_features')

    op.drop_index('idx_hazard_district_active', table_name='hazard_events')
    op.drop_table('hazard_events')

    op.drop_index('idx_rainfall_district_obs', table_name='rainfall_observations')
    op.drop_table('rainfall_observations')

    op.drop_index('idx_weather_district_obs', table_name='weather_observations')
    op.drop_table('weather_observations')

    op.drop_index('idx_ingestion_runs_source', table_name='data_ingestion_runs')
    op.drop_table('data_ingestion_runs')

    op.drop_table('data_sources')
