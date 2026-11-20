"""Offline tests for the Stage 5 SQLite data layer."""

from __future__ import annotations

import sqlite3

import pytest

from config.settings import DATABASE_PATH, DB_VERSION, ROOT_DIR
from src.database.connection import transaction
from src.database.repositories import FeatureRepository, RegionRepository
from src.database.schema import initialize_database


def _test_region():
    return {
        "region_id": "TEST-REGION-001",
        "region_name": "Synthetic Test District",
        "parent_code": "TEST-PARENT",
        "parent_name": "Synthetic Test Parent",
        "province_name": "Test Province",
        "created_at_utc": "2026-01-01T00:00:00Z",
    }


def test_initialize_creates_versioned_schema_and_is_idempotent(tmp_path):
    db_path = tmp_path / "nested" / "caist-test.sqlite"

    assert initialize_database(db_path) == DB_VERSION
    assert initialize_database(db_path) == DB_VERSION

    with transaction(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        version = connection.execute(
            "SELECT MAX(version) AS version FROM schema_migrations"
        ).fetchone()["version"]

    assert {
        "regions",
        "region_static_features",
        "daily_features",
        "flood_events",
        "monitoring_stations",
        "sensor_observations",
        "model_versions",
        "predictions",
        "data_sync_logs",
        "schema_migrations",
    }.issubset(tables)
    assert version == DB_VERSION
    assert db_path.is_file()


def test_foreign_keys_unique_keys_and_nullable_unknown_label(tmp_path):
    db_path = tmp_path / "caist-test.sqlite"
    initialize_database(db_path)

    with transaction(db_path) as connection:
        RegionRepository.upsert_many(connection, [_test_region()])
        row = {
            "district_code": "TEST-REGION-001",
            "date": "2026-01-02",
            "precipitation_mm_day": 0.0,
            "chirps_pixel_count": 1,
            "flood_event_rows": None,
            "flood_reported": None,
            "flood_label": -1,
            "label_status": "unknown_no_report",
        }
        FeatureRepository.upsert_daily_many(connection, "fixture-v1", [row])
        selected = FeatureRepository.get_daily(
            connection,
            "TEST-REGION-001",
            "2026-01-02",
            "2026-01-02",
            "fixture-v1",
        )

    assert len(selected) == 1
    assert selected[0]["flood_reported"] is None
    assert selected[0]["label_status"] == "unknown_no_report"
    assert selected[0]["flood_label"] == -1

    with pytest.raises(sqlite3.IntegrityError):
        with transaction(db_path) as connection:
            connection.execute(
                """INSERT INTO daily_features(
                    region_id, feature_date, data_version, flood_label, label_status
                ) VALUES (?, ?, ?, ?, ?)""",
                ("MISSING-REGION", "2026-01-03", "fixture-v1", -1, "unknown_no_report"),
            )

    with pytest.raises(sqlite3.IntegrityError):
        with transaction(db_path) as connection:
            connection.execute(
                """INSERT INTO daily_features(
                    region_id, feature_date, data_version, flood_reported, flood_label,
                    flood_event_rows, label_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("TEST-REGION-001", "2026-01-03", "fixture-v1", 1, 0, 1, "reported_event"),
            )


def test_daily_feature_upsert_updates_existing_row(tmp_path):
    db_path = tmp_path / "caist-test.sqlite"
    initialize_database(db_path)

    with transaction(db_path) as connection:
        RegionRepository.upsert_many(connection, [_test_region()])
        row = {
            "district_code": "TEST-REGION-001",
            "date": "2026-01-02",
            "precipitation_mm_day": 3.0,
            "chirps_pixel_count": 1,
            "flood_event_rows": None,
            "flood_reported": None,
            "flood_label": -1,
            "label_status": "unknown_no_report",
        }
        FeatureRepository.upsert_daily_many(connection, "fixture-v1", [row])
        row["precipitation_mm_day"] = 7.5
        FeatureRepository.upsert_daily_many(connection, "fixture-v1", [row])
        selected = FeatureRepository.get_daily(
            connection,
            "TEST-REGION-001",
            "2026-01-02",
            "2026-01-02",
            "fixture-v1",
        )

    assert len(selected) == 1
    assert selected[0]["precipitation_mm_day"] == 7.5


def test_transaction_rolls_back_on_error(tmp_path):
    db_path = tmp_path / "caist-test.sqlite"
    initialize_database(db_path)

    with pytest.raises(RuntimeError, match="fixture failure"):
        with transaction(db_path) as connection:
            RegionRepository.upsert_many(connection, [_test_region()])
            raise RuntimeError("fixture failure")

    with transaction(db_path) as connection:
        assert RegionRepository.get(connection, "TEST-REGION-001") is None


def test_newer_schema_version_is_rejected(tmp_path):
    db_path = tmp_path / "future.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at_utc TEXT, description TEXT)"
        )
        connection.execute(
            "INSERT INTO schema_migrations VALUES (?, ?, ?)",
            (DB_VERSION + 1, "2026-01-01T00:00:00Z", "future fixture"),
        )

    with pytest.raises(RuntimeError, match="newer than supported"):
        initialize_database(db_path)


def test_default_database_location_is_project_local_and_gitignored():
    assert DATABASE_PATH == ROOT_DIR / "data" / "caist.sqlite"
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "*.sqlite" in gitignore.splitlines()

def test_monitoring_model_and_prediction_repositories(tmp_path):
    from src.database.repositories import (
        ModelVersionRepository,
        MonitoringRepository,
        PredictionRepository,
    )

    db_path = tmp_path / "repository-fixtures.sqlite"
    initialize_database(db_path)
    observed_at = "2026-11-19T01:00:00Z"
    received_at = "2026-11-19T01:05:00Z"

    with transaction(db_path) as connection:
        RegionRepository.upsert_many(connection, [_test_region()])
        MonitoringRepository.upsert_station(connection, {
            "station_id": "TEST-STATION-001",
            "station_name": "Synthetic Test Station",
            "latitude": -6.9,
            "longitude": 107.6,
            "source": "test fixture",
            "measured_parameters": ["water_level"],
        })
        observation = {
            "station_id": "TEST-STATION-001",
            "observed_at_utc": observed_at,
            "parameter": "water_level",
            "value": 12.5,
            "unit": "cm",
            "source": "test fixture",
            "received_at_utc": received_at,
        }
        MonitoringRepository.upsert_observations(connection, [observation])
        observation["value"] = 14.0
        MonitoringRepository.upsert_observations(connection, [observation])
        observations = MonitoringRepository.get_observations(
            connection, "TEST-STATION-001", observed_at, received_at
        )

        ModelVersionRepository.upsert(connection, {
            "model_version": "test-model-v1",
            "artifact_relative_path": "models/test-model.bin",
            "trained_at_utc": "2026-11-18T00:00:00Z",
            "feature_list_json": ["precipitation_mm_day"],
            "metrics_json": {"auc": 0.8},
            "status": "registered",
        })
        PredictionRepository.upsert_many(connection, [{
            "region_id": "TEST-REGION-001",
            "prediction_created_at_utc": received_at,
            "target_date": "2026-11-20",
            "probability": 0.7,
            "risk_level": "high",
            "model_version": "test-model-v1",
            "input_data_version": "fixture-v1",
        }])
        prediction = PredictionRepository.get_for_date(
            connection, "2026-11-20", "test-model-v1"
        )

    assert len(observations) == 1
    assert observations[0]["value"] == 14.0
    assert len(prediction) == 1
    assert prediction[0]["probability"] == 0.7

    with pytest.raises(ValueError, match="ISO-8601 UTC"):
        MonitoringRepository.upsert_observations(connection, [{
            "station_id": "TEST-STATION-001",
            "observed_at_utc": "2026-11-19T08:00:00+07:00",
            "parameter": "water_level",
            "value": 12.5,
            "unit": "cm",
            "source": "test fixture",
            "received_at_utc": received_at,
        }])

    with pytest.raises(ValueError, match="must be relative"):
        with transaction(db_path) as connection:
            ModelVersionRepository.upsert(connection, {
                "model_version": "test-model-absolute-path",
                "artifact_relative_path": "C:/models/model.bin",
                "feature_list_json": ["precipitation_mm_day"],
                "status": "registered",
            })



def test_v1_database_migrates_existing_labels_without_data_loss(tmp_path):
    from src.database.schema import _migration_1

    db_path = tmp_path / "v1-upgrade.sqlite"
    with transaction(db_path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at_utc TEXT NOT NULL, description TEXT NOT NULL)"
        )
        _migration_1(connection)
        RegionRepository.upsert_many(connection, [_test_region()])
        connection.execute(
            """INSERT INTO daily_features(
                region_id, feature_date, data_version, flood_event_rows, flood_reported, label_status
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            ("TEST-REGION-001", "2026-01-01", "legacy-v1", 1, 1, "reported_event"),
        )
        connection.execute(
            "INSERT INTO schema_migrations VALUES (?, ?, ?)",
            (1, "2026-01-01T00:00:00Z", "legacy schema"),
        )

    assert initialize_database(db_path) == DB_VERSION
    with transaction(db_path) as connection:
        row = connection.execute(
            "SELECT flood_label, label_status FROM daily_features WHERE data_version='legacy-v1'"
        ).fetchone()
        assert tuple(row) == (1, "reported_event")
        assert connection.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0] == 1

def test_daily_feature_schema_accepts_positive_negative_and_unknown_labels(tmp_path):
    db_path = tmp_path / "label-classes.sqlite"
    initialize_database(db_path)
    with transaction(db_path) as connection:
        RegionRepository.upsert_many(connection, [_test_region()])
        rows = [
            {"district_code": "TEST-REGION-001", "date": "2026-01-01", "flood_event_rows": 1,
             "flood_reported": 1, "flood_label": 1, "label_status": "reported_event"},
            {"district_code": "TEST-REGION-001", "date": "2026-01-02", "flood_event_rows": None,
             "flood_reported": None, "flood_label": 0, "label_status": "pseudo_absence_hydro"},
            {"district_code": "TEST-REGION-001", "date": "2026-01-03", "flood_event_rows": None,
             "flood_reported": None, "flood_label": -1, "label_status": "unknown_no_report"},
        ]
        FeatureRepository.upsert_daily_many(connection, "fixture-v2", rows)
        stored = connection.execute(
            "SELECT flood_label, label_status FROM daily_features WHERE data_version=? ORDER BY feature_date",
            ("fixture-v2",),
        ).fetchall()
    assert [(row["flood_label"], row["label_status"]) for row in stored] == [
        (1, "reported_event"), (0, "pseudo_absence_hydro"), (-1, "unknown_no_report")
    ]
