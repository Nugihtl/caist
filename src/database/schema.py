"""Versioned SQLite schema and migrations for CAIST."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Callable

from config.settings import DB_VERSION
from src.database.connection import transaction


def _migration_1(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        BEGIN IMMEDIATE;
        CREATE TABLE regions (
            region_id TEXT PRIMARY KEY,
            region_name TEXT NOT NULL CHECK (length(trim(region_name)) > 0),
            parent_code TEXT NOT NULL,
            parent_name TEXT NOT NULL CHECK (length(trim(parent_name)) > 0),
            province_name TEXT,
            created_at_utc TEXT NOT NULL
        );

        CREATE TABLE region_static_features (
            region_id TEXT NOT NULL,
            data_version TEXT NOT NULL,
            elevation_mean_m REAL,
            elevation_median_m REAL,
            elevation_p10_m REAL,
            slope_mean_deg REAL CHECK (slope_mean_deg IS NULL OR slope_mean_deg BETWEEN 0 AND 90),
            landcover_10_tree_cover_share REAL CHECK (landcover_10_tree_cover_share IS NULL OR landcover_10_tree_cover_share BETWEEN 0 AND 1),
            landcover_20_shrubland_share REAL CHECK (landcover_20_shrubland_share IS NULL OR landcover_20_shrubland_share BETWEEN 0 AND 1),
            landcover_30_grassland_share REAL CHECK (landcover_30_grassland_share IS NULL OR landcover_30_grassland_share BETWEEN 0 AND 1),
            landcover_40_cropland_share REAL CHECK (landcover_40_cropland_share IS NULL OR landcover_40_cropland_share BETWEEN 0 AND 1),
            landcover_50_built_up_share REAL CHECK (landcover_50_built_up_share IS NULL OR landcover_50_built_up_share BETWEEN 0 AND 1),
            landcover_60_bare_sparse_vegetation_share REAL CHECK (landcover_60_bare_sparse_vegetation_share IS NULL OR landcover_60_bare_sparse_vegetation_share BETWEEN 0 AND 1),
            landcover_70_snow_ice_share REAL CHECK (landcover_70_snow_ice_share IS NULL OR landcover_70_snow_ice_share BETWEEN 0 AND 1),
            landcover_80_permanent_water_share REAL CHECK (landcover_80_permanent_water_share IS NULL OR landcover_80_permanent_water_share BETWEEN 0 AND 1),
            landcover_90_herbaceous_wetland_share REAL CHECK (landcover_90_herbaceous_wetland_share IS NULL OR landcover_90_herbaceous_wetland_share BETWEEN 0 AND 1),
            landcover_95_mangroves_share REAL CHECK (landcover_95_mangroves_share IS NULL OR landcover_95_mangroves_share BETWEEN 0 AND 1),
            landcover_100_moss_lichen_share REAL CHECK (landcover_100_moss_lichen_share IS NULL OR landcover_100_moss_lichen_share BETWEEN 0 AND 1),
            landcover_share_sum REAL CHECK (landcover_share_sum IS NULL OR abs(landcover_share_sum - 1.0) < 0.001),
            river_length_km REAL CHECK (river_length_km IS NULL OR river_length_km >= 0),
            river_density_km_per_km2 REAL CHECK (river_density_km_per_km2 IS NULL OR river_density_km_per_km2 >= 0),
            representative_point_to_river_km REAL CHECK (representative_point_to_river_km IS NULL OR representative_point_to_river_km >= 0),
            PRIMARY KEY (region_id, data_version),
            FOREIGN KEY (region_id) REFERENCES regions(region_id) ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE daily_features (
            region_id TEXT NOT NULL,
            feature_date TEXT NOT NULL CHECK (date(feature_date) = feature_date),
            data_version TEXT NOT NULL,
            precipitation_mm_day REAL CHECK (precipitation_mm_day IS NULL OR precipitation_mm_day >= 0),
            chirps_pixel_count INTEGER CHECK (chirps_pixel_count IS NULL OR chirps_pixel_count > 0),
            flood_event_rows INTEGER CHECK (flood_event_rows IS NULL OR flood_event_rows > 0),
            flood_reported INTEGER CHECK (flood_reported IS NULL OR flood_reported IN (0, 1)),
            label_status TEXT NOT NULL CHECK (label_status IN ('reported_event', 'unknown_no_report')),
            PRIMARY KEY (region_id, feature_date, data_version),
            FOREIGN KEY (region_id) REFERENCES regions(region_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            CHECK (
                (label_status = 'reported_event' AND flood_reported = 1 AND flood_event_rows > 0)
                OR (label_status = 'unknown_no_report' AND flood_reported IS NULL AND flood_event_rows IS NULL)
            )
        );

        CREATE TABLE flood_events (
            event_id INTEGER PRIMARY KEY,
            region_id TEXT NOT NULL,
            event_date TEXT NOT NULL CHECK (date(event_date) = event_date),
            data_version TEXT NOT NULL,
            source_event_rows INTEGER NOT NULL CHECK (source_event_rows > 0),
            source_files TEXT NOT NULL,
            source_rows TEXT NOT NULL,
            source_locations TEXT NOT NULL,
            UNIQUE (region_id, event_date, data_version),
            FOREIGN KEY (region_id) REFERENCES regions(region_id) ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE monitoring_stations (
            station_id TEXT PRIMARY KEY,
            station_name TEXT NOT NULL CHECK (length(trim(station_name)) > 0),
            latitude REAL CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
            longitude REAL CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
            source TEXT NOT NULL,
            measured_parameters TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'unverified' CHECK (status IN ('unverified', 'active', 'inactive'))
        );

        CREATE TABLE sensor_observations (
            observation_id INTEGER PRIMARY KEY,
            station_id TEXT NOT NULL,
            observed_at_utc TEXT NOT NULL,
            parameter TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            received_at_utc TEXT NOT NULL,
            quality_flag TEXT NOT NULL DEFAULT 'unreviewed',
            UNIQUE (station_id, observed_at_utc, parameter, source),
            FOREIGN KEY (station_id) REFERENCES monitoring_stations(station_id) ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE model_versions (
            model_version TEXT PRIMARY KEY,
            artifact_relative_path TEXT,
            trained_at_utc TEXT,
            feature_list_json TEXT NOT NULL,
            metrics_json TEXT,
            status TEXT NOT NULL CHECK (status IN ('registered', 'validated', 'retired'))
        );

        CREATE TABLE predictions (
            prediction_id INTEGER PRIMARY KEY,
            region_id TEXT NOT NULL,
            prediction_created_at_utc TEXT NOT NULL,
            target_date TEXT NOT NULL CHECK (date(target_date) = target_date),
            probability REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
            risk_level TEXT,
            model_version TEXT NOT NULL,
            input_data_version TEXT NOT NULL,
            UNIQUE (region_id, target_date, model_version, input_data_version),
            FOREIGN KEY (region_id) REFERENCES regions(region_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (model_version) REFERENCES model_versions(model_version) ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE data_sync_logs (
            sync_id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            started_at_utc TEXT NOT NULL,
            finished_at_utc TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('succeeded', 'succeeded_with_warnings', 'failed')),
            records_read INTEGER NOT NULL DEFAULT 0 CHECK (records_read >= 0),
            records_written INTEGER NOT NULL DEFAULT 0 CHECK (records_written >= 0),
            records_rejected INTEGER NOT NULL DEFAULT 0 CHECK (records_rejected >= 0),
            details_json TEXT NOT NULL DEFAULT '{}',
            error_message TEXT
        );

        CREATE INDEX idx_daily_features_date ON daily_features(feature_date);
        CREATE INDEX idx_daily_features_version_date ON daily_features(data_version, feature_date);
        CREATE INDEX idx_flood_events_date ON flood_events(event_date);
        CREATE INDEX idx_sensor_observations_time ON sensor_observations(observed_at_utc);
        CREATE INDEX idx_predictions_target_date ON predictions(target_date);
        CREATE INDEX idx_data_sync_logs_source_time ON data_sync_logs(source, started_at_utc);
        """
    )


def _migration_2(connection: sqlite3.Connection) -> None:
    """Add explicit binary/unknown flood labels while preserving existing rows."""
    connection.executescript("""
        BEGIN IMMEDIATE;
        DROP INDEX IF EXISTS idx_daily_features_date;
        DROP INDEX IF EXISTS idx_daily_features_version_date;
        ALTER TABLE daily_features RENAME TO daily_features_v1;
        CREATE TABLE daily_features (
            region_id TEXT NOT NULL,
            feature_date TEXT NOT NULL CHECK (date(feature_date) = feature_date),
            data_version TEXT NOT NULL,
            precipitation_mm_day REAL CHECK (precipitation_mm_day IS NULL OR precipitation_mm_day >= 0),
            chirps_pixel_count INTEGER CHECK (chirps_pixel_count IS NULL OR chirps_pixel_count > 0),
            flood_event_rows INTEGER CHECK (flood_event_rows IS NULL OR flood_event_rows > 0),
            flood_reported INTEGER CHECK (flood_reported IS NULL OR flood_reported IN (0, 1)),
            flood_label INTEGER NOT NULL CHECK (flood_label IN (-1, 0, 1)),
            label_status TEXT NOT NULL CHECK (label_status IN ('reported_event', 'pseudo_absence_hydro', 'unknown_no_report')),
            PRIMARY KEY (region_id, feature_date, data_version),
            FOREIGN KEY (region_id) REFERENCES regions(region_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            CHECK (
                (label_status = 'reported_event' AND flood_label = 1 AND flood_reported = 1 AND flood_event_rows > 0)
                OR (label_status = 'pseudo_absence_hydro' AND flood_label = 0 AND flood_reported IS NULL AND flood_event_rows IS NULL)
                OR (label_status = 'unknown_no_report' AND flood_label = -1 AND flood_reported IS NULL AND flood_event_rows IS NULL)
            )
        );
        INSERT INTO daily_features(
            region_id, feature_date, data_version, precipitation_mm_day, chirps_pixel_count,
            flood_event_rows, flood_reported, flood_label, label_status
        ) SELECT region_id, feature_date, data_version, precipitation_mm_day, chirps_pixel_count,
            flood_event_rows, flood_reported,
            CASE WHEN label_status='reported_event' THEN 1 ELSE -1 END,
            CASE WHEN label_status='reported_event' THEN 'reported_event' ELSE 'unknown_no_report' END
        FROM daily_features_v1;
        DROP TABLE daily_features_v1;
        CREATE INDEX idx_daily_features_date ON daily_features(feature_date);
        CREATE INDEX idx_daily_features_version_date ON daily_features(data_version, feature_date);
        COMMIT;
    """)


MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {1: _migration_1, 2: _migration_2}


def initialize_database(db_path: str | Path | None = None) -> int:
    """Apply pending migrations atomically and return the current schema version."""
    with transaction(db_path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at_utc TEXT NOT NULL,
                description TEXT NOT NULL
            )"""
        )
        current = connection.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
        ).fetchone()["version"]
        if current > DB_VERSION:
            raise RuntimeError(
                f"Database schema version {current} is newer than supported {DB_VERSION}."
            )
        for version in range(current + 1, DB_VERSION + 1):
            migration = MIGRATIONS.get(version)
            if migration is None:
                raise RuntimeError(f"Missing database migration {version}.")
            migration(connection)
            applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at_utc, description) VALUES (?, ?, ?)",
                (version, applied_at, f"Create CAIST operational data schema v{version}"),
            )
        return DB_VERSION
