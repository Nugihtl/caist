"""Data repositories: database access stays out of the UI layer."""

from __future__ import annotations

import sqlite3
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Iterable, Mapping, Any

from src.database.connection import transaction

STATIC_COLUMNS = (
    "elevation_mean_m",
    "elevation_median_m",
    "elevation_p10_m",
    "slope_mean_deg",
    "landcover_10_tree_cover_share",
    "landcover_20_shrubland_share",
    "landcover_30_grassland_share",
    "landcover_40_cropland_share",
    "landcover_50_built_up_share",
    "landcover_60_bare_sparse_vegetation_share",
    "landcover_70_snow_ice_share",
    "landcover_80_permanent_water_share",
    "landcover_90_herbaceous_wetland_share",
    "landcover_95_mangroves_share",
    "landcover_100_moss_lichen_share",
    "landcover_share_sum",
    "river_length_km",
    "river_density_km_per_km2",
    "representative_point_to_river_km",
)


def _require_utc_timestamp(value: str, field: str) -> str:
    """Require ISO-8601 UTC timestamps in the database-facing API."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be an ISO-8601 UTC timestamp ending in 'Z'.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO-8601 timestamp.") from exc
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field} must use UTC.")
    return value


def _json_text(value: Any, field: str) -> str:
    if isinstance(value, str):
        json.loads(value)
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be JSON serializable.") from exc


class RegionRepository:
    """Create and query verified administrative region references."""

    @staticmethod
    def upsert_many(connection: sqlite3.Connection, regions: Iterable[Mapping[str, Any]]) -> int:
        rows = [
            (
                str(row["region_id"]),
                str(row["region_name"]),
                str(row["parent_code"]),
                str(row["parent_name"]),
                row.get("province_name"),
                row["created_at_utc"],
            )
            for row in regions
        ]
        connection.executemany(
            """INSERT INTO regions(region_id, region_name, parent_code, parent_name, province_name, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_id) DO UPDATE SET
                region_name=excluded.region_name,
                parent_code=excluded.parent_code,
                parent_name=excluded.parent_name,
                province_name=excluded.province_name""",
            rows,
        )
        return len(rows)

    @staticmethod
    def get(connection: sqlite3.Connection, region_id: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM regions WHERE region_id = ?", (region_id,)
        ).fetchone()

    @staticmethod
    def list_all(db_path: str | Path | None = None) -> list[sqlite3.Row]:
        with transaction(db_path) as connection:
            return connection.execute(
                "SELECT * FROM regions ORDER BY parent_code, region_id"
            ).fetchall()


class FeatureRepository:
    """Store normalized static and time-varying features."""

    @staticmethod
    def upsert_static_many(
        connection: sqlite3.Connection,
        data_version: str,
        features: Iterable[Mapping[str, Any]],
    ) -> int:
        columns = ("region_id", "data_version", *STATIC_COLUMNS)
        names = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f"{column}=excluded.{column}" for column in STATIC_COLUMNS)
        rows = [
            (str(feature["district_code"]), data_version)
            + tuple(feature.get(column) for column in STATIC_COLUMNS)
            for feature in features
        ]
        connection.executemany(
            f"INSERT INTO region_static_features ({names}) VALUES ({placeholders}) "
            f"ON CONFLICT(region_id, data_version) DO UPDATE SET {updates}",
            rows,
        )
        return len(rows)

    @staticmethod
    def upsert_daily_many(
        connection: sqlite3.Connection,
        data_version: str,
        features: Iterable[Mapping[str, Any]],
    ) -> int:
        rows = [
            (
                str(row["district_code"]),
                row["date"],
                data_version,
                row.get("precipitation_mm_day"),
                row.get("chirps_pixel_count"),
                row.get("flood_event_rows"),
                row.get("flood_reported"),
                int(row["flood_label"]),
                row["label_status"],
            )
            for row in features
        ]
        connection.executemany(
            """INSERT INTO daily_features(
                region_id, feature_date, data_version, precipitation_mm_day,
                chirps_pixel_count, flood_event_rows, flood_reported, flood_label, label_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_id, feature_date, data_version) DO UPDATE SET
                precipitation_mm_day=excluded.precipitation_mm_day,
                chirps_pixel_count=excluded.chirps_pixel_count,
                flood_event_rows=excluded.flood_event_rows,
                flood_reported=excluded.flood_reported,
                flood_label=excluded.flood_label,
                label_status=excluded.label_status""",
            rows,
        )
        return len(rows)

    @staticmethod
    def get_daily(
        connection: sqlite3.Connection,
        region_id: str,
        start_date: str,
        end_date: str,
        data_version: str | None = None,
    ) -> list[sqlite3.Row]:
        if data_version is None:
            return connection.execute(
                """SELECT * FROM daily_features
                WHERE region_id=? AND feature_date BETWEEN ? AND ?
                ORDER BY feature_date""",
                (region_id, start_date, end_date),
            ).fetchall()
        return connection.execute(
            """SELECT * FROM daily_features
            WHERE region_id=? AND feature_date BETWEEN ? AND ? AND data_version=?
            ORDER BY feature_date""",
            (region_id, start_date, end_date, data_version),
        ).fetchall()


class FloodEventRepository:
    """Store source-traceable, district-day flood reports."""

    @staticmethod
    def upsert_many(
        connection: sqlite3.Connection,
        data_version: str,
        events: Iterable[Mapping[str, Any]],
    ) -> int:
        rows = [
            (
                str(row["district_code"]),
                row["date"],
                data_version,
                int(row["source_event_rows"]),
                row["source_files"],
                row["source_rows"],
                row["source_locations"],
            )
            for row in events
        ]
        connection.executemany(
            """INSERT INTO flood_events(
                region_id, event_date, data_version, source_event_rows,
                source_files, source_rows, source_locations
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_id, event_date, data_version) DO UPDATE SET
                source_event_rows=excluded.source_event_rows,
                source_files=excluded.source_files,
                source_rows=excluded.source_rows,
                source_locations=excluded.source_locations""",
            rows,
        )
        return len(rows)

    @staticmethod
    def get_by_region(
        connection: sqlite3.Connection, region_id: str, start_date: str, end_date: str
    ) -> list[sqlite3.Row]:
        return connection.execute(
            """SELECT * FROM flood_events
            WHERE region_id=? AND event_date BETWEEN ? AND ? ORDER BY event_date""",
            (region_id, start_date, end_date),
        ).fetchall()


class MonitoringRepository:
    """Store verified station references and deduplicated observations."""

    @staticmethod
    def upsert_station(connection: sqlite3.Connection, station: Mapping[str, Any]) -> None:
        parameters = station["measured_parameters"]
        if not isinstance(parameters, str):
            parameters = _json_text(parameters, "measured_parameters")
        connection.execute(
            """INSERT INTO monitoring_stations(
                station_id, station_name, latitude, longitude, source,
                measured_parameters, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(station_id) DO UPDATE SET
                station_name=excluded.station_name,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                source=excluded.source,
                measured_parameters=excluded.measured_parameters,
                status=excluded.status""",
            (
                station["station_id"], station["station_name"], station.get("latitude"),
                station.get("longitude"), station["source"], parameters,
                station.get("status", "unverified"),
            ),
        )

    @staticmethod
    def upsert_observations(
        connection: sqlite3.Connection,
        observations: Iterable[Mapping[str, Any]],
    ) -> int:
        rows = []
        for observation in observations:
            rows.append((
                observation["station_id"],
                _require_utc_timestamp(observation["observed_at_utc"], "observed_at_utc"),
                observation["parameter"],
                float(observation["value"]),
                observation["unit"],
                observation["source"],
                _require_utc_timestamp(observation["received_at_utc"], "received_at_utc"),
                observation.get("quality_flag", "unreviewed"),
            ))
        connection.executemany(
            """INSERT INTO sensor_observations(
                station_id, observed_at_utc, parameter, value, unit, source,
                received_at_utc, quality_flag
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(station_id, observed_at_utc, parameter, source) DO UPDATE SET
                value=excluded.value,
                unit=excluded.unit,
                received_at_utc=excluded.received_at_utc,
                quality_flag=excluded.quality_flag""",
            rows,
        )
        return len(rows)

    @staticmethod
    def get_observations(
        connection: sqlite3.Connection,
        station_id: str,
        start_utc: str,
        end_utc: str,
        parameter: str | None = None,
    ) -> list[sqlite3.Row]:
        _require_utc_timestamp(start_utc, "start_utc")
        _require_utc_timestamp(end_utc, "end_utc")
        if parameter is None:
            return connection.execute(
                """SELECT * FROM sensor_observations
                WHERE station_id=? AND observed_at_utc BETWEEN ? AND ?
                ORDER BY observed_at_utc""",
                (station_id, start_utc, end_utc),
            ).fetchall()
        return connection.execute(
            """SELECT * FROM sensor_observations
            WHERE station_id=? AND observed_at_utc BETWEEN ? AND ? AND parameter=?
            ORDER BY observed_at_utc""",
            (station_id, start_utc, end_utc, parameter),
        ).fetchall()


class ModelVersionRepository:
    """Register model metadata without embedding machine-specific absolute paths."""

    @staticmethod
    def upsert(connection: sqlite3.Connection, model: Mapping[str, Any]) -> None:
        artifact_path = model.get("artifact_relative_path")
        if artifact_path and re.match(r"^(?:[A-Za-z]:[\\/]|[/\\])", artifact_path):
            raise ValueError("artifact_relative_path must be relative to the project/data root.")
        trained_at = model.get("trained_at_utc")
        if trained_at is not None:
            trained_at = _require_utc_timestamp(trained_at, "trained_at_utc")
        feature_list = _json_text(model["feature_list_json"], "feature_list_json")
        metrics = model.get("metrics_json")
        metrics_text = None if metrics is None else _json_text(metrics, "metrics_json")
        connection.execute(
            """INSERT INTO model_versions(
                model_version, artifact_relative_path, trained_at_utc,
                feature_list_json, metrics_json, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_version) DO UPDATE SET
                artifact_relative_path=excluded.artifact_relative_path,
                trained_at_utc=excluded.trained_at_utc,
                feature_list_json=excluded.feature_list_json,
                metrics_json=excluded.metrics_json,
                status=excluded.status""",
            (
                model["model_version"], artifact_path, trained_at, feature_list,
                metrics_text, model["status"],
            ),
        )

    @staticmethod
    def get(connection: sqlite3.Connection, model_version: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM model_versions WHERE model_version=?", (model_version,)
        ).fetchone()


class PredictionRepository:
    """Persist and query model predictions by region and target date."""

    @staticmethod
    def upsert_many(
        connection: sqlite3.Connection,
        predictions: Iterable[Mapping[str, Any]],
    ) -> int:
        rows = []
        for prediction in predictions:
            rows.append((
                prediction["region_id"],
                _require_utc_timestamp(prediction["prediction_created_at_utc"], "prediction_created_at_utc"),
                prediction["target_date"],
                float(prediction["probability"]),
                prediction.get("risk_level"),
                prediction["model_version"],
                prediction["input_data_version"],
            ))
        connection.executemany(
            """INSERT INTO predictions(
                region_id, prediction_created_at_utc, target_date, probability,
                risk_level, model_version, input_data_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_id, target_date, model_version, input_data_version) DO UPDATE SET
                prediction_created_at_utc=excluded.prediction_created_at_utc,
                probability=excluded.probability,
                risk_level=excluded.risk_level""",
            rows,
        )
        return len(rows)

    @staticmethod
    def get_for_date(
        connection: sqlite3.Connection,
        target_date: str,
        model_version: str | None = None,
    ) -> list[sqlite3.Row]:
        if model_version is None:
            return connection.execute(
                "SELECT * FROM predictions WHERE target_date=? ORDER BY region_id",
                (target_date,),
            ).fetchall()
        return connection.execute(
            """SELECT * FROM predictions WHERE target_date=? AND model_version=?
            ORDER BY region_id""",
            (target_date, model_version),
        ).fetchall()


class DataSyncLogRepository:
    """Record successful, warning, and failed local data imports."""

    @staticmethod
    def insert(connection: sqlite3.Connection, row: Mapping[str, Any]) -> int:
        cursor = connection.execute(
            """INSERT INTO data_sync_logs(
                source, started_at_utc, finished_at_utc, status, records_read,
                records_written, records_rejected, details_json, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["source"],
                row["started_at_utc"],
                row["finished_at_utc"],
                row["status"],
                row.get("records_read", 0),
                row.get("records_written", 0),
                row.get("records_rejected", 0),
                row.get("details_json", "{}"),
                row.get("error_message"),
            ),
        )
        return int(cursor.lastrowid)

    @staticmethod
    def list_recent(
        connection: sqlite3.Connection, limit: int = 50
    ) -> list[sqlite3.Row]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")
        return connection.execute(
            "SELECT * FROM data_sync_logs ORDER BY sync_id DESC LIMIT ?", (limit,)
        ).fetchall()
