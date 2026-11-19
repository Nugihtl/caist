"""Idempotently import validated Stage 4 products into SQLite."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from config.settings import DATA_DIR, DATABASE_PATH
from src.database.connection import transaction
from src.database.repositories import (
    DataSyncLogRepository,
    FeatureRepository,
    FloodEventRepository,
    RegionRepository,
)
from src.database.schema import initialize_database

EXPECTED_REGION_COUNTS = {"32.04": 31, "32.17": 16, "32.73": 30, "32.77": 3}
CHUNK_SIZE = 1000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _csv_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def _number(value: str | None, kind: type = float) -> Any:
    if value is None or not value.strip():
        return None
    if kind is int:
        numeric = float(value)
        if not numeric.is_integer():
            raise ValueError(f"Expected an integer value, got {value!r}.")
        return int(numeric)
    return kind(value)


def _region_rows(path: Path) -> list[dict[str, Any]]:
    geojson = json.loads(path.read_text(encoding="utf-8"))
    features = geojson.get("features", [])
    counts: dict[str, int] = {}
    rows = []
    seen = set()
    created_at = _utc_now()
    for feature in features:
        props = feature.get("properties") or {}
        code = str(props.get("district_code", ""))
        parent = str(props.get("parent_code", ""))
        if not code or not props.get("district_name") or not parent:
            raise ValueError("GeoJSON batas memiliki kode/nama kecamatan atau kode induk kosong.")
        if code in seen:
            raise ValueError(f"Kode kecamatan duplikat pada GeoJSON: {code}")
        seen.add(code)
        counts[parent] = counts.get(parent, 0) + 1
        rows.append({
            "region_id": code,
            "region_name": props["district_name"],
            "parent_code": parent,
            "parent_name": props["parent_name"],
            "province_name": props.get("province_name"),
            "created_at_utc": created_at,
        })
    if len(rows) != 80 or counts != EXPECTED_REGION_COUNTS:
        raise ValueError(f"Referensi wilayah bukan cakupan 80 kecamatan: rows={len(rows)}, counts={counts}")
    return rows


def _chunks(rows: Iterator[dict[str, Any]], chunk_size: int = CHUNK_SIZE) -> Iterator[list[dict[str, Any]]]:
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _static_rows(path: Path) -> Iterator[dict[str, Any]]:
    numeric_fields = {
        "elevation_mean_m", "elevation_median_m", "elevation_p10_m", "slope_mean_deg",
        "landcover_10_tree_cover_share", "landcover_20_shrubland_share",
        "landcover_30_grassland_share", "landcover_40_cropland_share",
        "landcover_50_built_up_share", "landcover_60_bare_sparse_vegetation_share",
        "landcover_70_snow_ice_share", "landcover_80_permanent_water_share",
        "landcover_90_herbaceous_wetland_share", "landcover_95_mangroves_share",
        "landcover_100_moss_lichen_share", "landcover_share_sum", "river_length_km",
        "river_density_km_per_km2", "representative_point_to_river_km",
    }
    for row in _csv_rows(path):
        normalized = dict(row)
        for name in numeric_fields:
            normalized[name] = _number(row.get(name))
        yield normalized


def _daily_rows(path: Path) -> Iterator[dict[str, Any]]:
    numeric_fields = ("precipitation_mm_day", "chirps_pixel_count", "flood_event_rows", "flood_label")
    for row in _csv_rows(path):
        normalized = dict(row)
        for name in numeric_fields:
            normalized[name] = _number(row.get(name), int if name != "precipitation_mm_day" else float)
        reported = (row.get("flood_reported") or "").strip().lower()
        normalized["flood_reported"] = None if not reported else int(reported in {"true", "1"})
        yield normalized


def _event_rows(path: Path) -> Iterator[dict[str, Any]]:
    for row in _csv_rows(path):
        normalized = dict(row)
        normalized["source_event_rows"] = _number(row.get("source_event_rows"), int)
        yield normalized


def _count_csv_rows(path: Path) -> int:
    return sum(1 for _ in _csv_rows(path))


def _count_excluded_audit_rows(path: Path) -> int:
    """Count excluded BNPB audit rows, while allowing the audit to retain matches."""
    rows = list(_csv_rows(path))
    if not rows or "training_included" not in rows[0]:
        return len(rows)
    return sum((row.get("training_included") or "").strip().lower() not in {"true", "1", "yes"} for row in rows)


def import_stage4_outputs(
    processed_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate and upsert Stage 4 outputs in one SQLite transaction.

    Re-running this function for the same data version updates matching records
    instead of duplicating them. Unmatched BNPB records stay in their audit CSV.
    """
    root = Path(processed_dir) if processed_dir is not None else DATA_DIR / "processed"
    path_db = Path(db_path) if db_path is not None else DATABASE_PATH
    boundary_path = root / "spatial" / "batas_kecamatan_bandung_raya.geojson"
    static_path = root / "fitur_spasial_kecamatan.csv"
    daily_path = root / "fitur_harian_kecamatan.csv"
    events_path = root / "kejadian_banjir_kecamatan_harian.csv"
    unmatched_path = root / "audit_bnpb_tidak_tercocok.csv"
    manifest_path = root / "manifest_data_ingestion.json"
    validation_path = root / "laporan_validasi_stage4.json"
    required_files = [
        boundary_path, static_path, daily_path, events_path, unmatched_path,
        manifest_path, validation_path,
    ]
    missing = [str(path.relative_to(root)) for path in required_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Output Stage 4 wajib tidak ditemukan: {missing}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if validation.get("status") != "passed" or validation.get("boundary_count") != 80:
        raise ValueError("Laporan validasi Stage 4 tidak menyatakan 80 batas lolos.")
    data_version = str(manifest.get("generated_at_local_date", "")).strip()
    if not data_version:
        raise ValueError("Manifest Stage 4 tidak memiliki generated_at_local_date.")
    regions = _region_rows(boundary_path)
    static_count = _count_csv_rows(static_path)
    daily_count = _count_csv_rows(daily_path)
    event_rows = list(_event_rows(events_path))
    event_count = len(event_rows)
    audit_rows_count = _count_csv_rows(unmatched_path)
    unmatched_count = _count_excluded_audit_rows(unmatched_path)
    if static_count != validation.get("static_rows"):
        raise ValueError("Jumlah fitur statis tidak sesuai laporan validasi Stage 4.")
    if daily_count != validation.get("daily_rows"):
        raise ValueError("Jumlah fitur harian tidak sesuai laporan validasi Stage 4.")
    if event_count != validation.get("bnpb", {}).get("matched_district_day_events"):
        raise ValueError("Jumlah kejadian tidak sesuai laporan validasi Stage 4.")
    if unmatched_count != validation.get("bnpb", {}).get("unmatched_target_admin_count"):
        raise ValueError("Jumlah catatan BNPB tak cocok tidak sesuai laporan Stage 4.")
    bnpb_report = manifest.get("bnpb", {})
    excluded_external = int(bnpb_report.get("excluded_non_bandung_raya_rows", 0))
    source_bnpb_rows = int(bnpb_report.get("raw_rows", 0))
    started_at = _utc_now()

    initialize_database(path_db)
    written = 0
    try:
        with transaction(path_db) as connection:
            written += RegionRepository.upsert_many(connection, regions)
            for batch in _chunks(_static_rows(static_path)):
                written += FeatureRepository.upsert_static_many(connection, data_version, batch)
            for batch in _chunks(_daily_rows(daily_path)):
                written += FeatureRepository.upsert_daily_many(connection, data_version, batch)
            for batch in _chunks(iter(event_rows)):
                written += FloodEventRepository.upsert_many(connection, data_version, batch)
            # Same-day reruns may have fewer verified locations than an earlier
            # pass. Remove stale event keys for this data version after upsert.
            connection.execute("CREATE TEMP TABLE stage4_event_keys (region_id TEXT, event_date TEXT, PRIMARY KEY(region_id, event_date))")
            connection.executemany(
                "INSERT INTO stage4_event_keys(region_id, event_date) VALUES (?, ?)",
                [(row["district_code"], row["date"]) for row in event_rows],
            )
            connection.execute(
                """DELETE FROM flood_events AS event
                WHERE data_version=? AND NOT EXISTS (
                    SELECT 1 FROM stage4_event_keys AS incoming
                    WHERE incoming.region_id=event.region_id AND incoming.event_date=event.event_date
                )""",
                (data_version,),
            )

            label_counts = connection.execute(
                """SELECT label_status, COUNT(*) AS count FROM daily_features
                WHERE data_version=? GROUP BY label_status""",
                (data_version,),
            ).fetchall()
            label_counts = {row["label_status"]: row["count"] for row in label_counts}
            positive_count = connection.execute(
                "SELECT COUNT(*) AS count FROM daily_features WHERE data_version=? AND flood_reported=1",
                (data_version,),
            ).fetchone()["count"]
            class_counts = {
                row["flood_label"]: row["count"]
                for row in connection.execute(
                    "SELECT flood_label, COUNT(*) AS count FROM daily_features WHERE data_version=? GROUP BY flood_label",
                    (data_version,),
                ).fetchall()
            }
            negative_count = class_counts.get(0, 0)
            unknown_count = class_counts.get(-1, 0)
            stored_event_count = connection.execute(
                "SELECT COUNT(*) AS count FROM flood_events WHERE data_version=?", (data_version,)
            ).fetchone()["count"]
            if (
                stored_event_count != event_count
                or sum(label_counts.values()) != daily_count
                or positive_count != event_count
                or class_counts.get(1, 0) != event_count
                or label_counts.get("pseudo_absence_hydro", 0) != negative_count
                or label_counts.get("unknown_no_report", 0) != unknown_count
                or negative_count + unknown_count + event_count != daily_count
            ):
                raise ValueError("Label harian 1/0/-1 tidak konsisten dengan event dan kebijakan Stage 4.")

            finished_at = _utc_now()
            details = {
                "data_version": data_version,
                "source_period": [manifest.get("chirps", {}).get("sources", [{}])[0].get("date_start"),
                                  manifest.get("chirps", {}).get("sources", [{}])[-1].get("date_end")],
                "unmatched_bnpb_rows_not_loaded": unmatched_count,
                "non_bandung_raya_bnpb_rows_filtered": excluded_external,
                "pseudo_absence_labels": negative_count,
                "unknown_flood_labels_minus_one": unknown_count,
                "training_rows_labels_0_or_1": negative_count + event_count,
            }
            sync_id = DataSyncLogRepository.insert(connection, {
                "source": "stage4_processed_files",
                "started_at_utc": started_at,
                "finished_at_utc": finished_at,
                "status": "succeeded_with_warnings" if unmatched_count else "succeeded",
                "records_read": static_count + daily_count + event_count + source_bnpb_rows,
                "records_written": written,
                "records_rejected": unmatched_count,
                "details_json": json.dumps(details, ensure_ascii=False, sort_keys=True),
            })
    except Exception as exc:
        with transaction(path_db) as connection:
            DataSyncLogRepository.insert(connection, {
                "source": "stage4_processed_files",
                "started_at_utc": started_at,
                "finished_at_utc": _utc_now(),
                "status": "failed",
                "records_read": 0,
                "records_written": 0,
                "records_rejected": 0,
                "details_json": json.dumps({"data_version": data_version}),
                "error_message": str(exc)[:1000],
            })
        raise

    return {
        "database": str(path_db),
        "data_version": data_version,
        "regions": len(regions),
        "static_features": static_count,
        "daily_features": daily_count,
        "flood_events": event_count,
        "unmatched_bnpb_not_loaded": unmatched_count,
        "bnpb_audit_rows": audit_rows_count,
        "non_region_bnpb_rows_filtered": excluded_external,
        "records_written": written,
        "sync_id": sync_id,
    }
