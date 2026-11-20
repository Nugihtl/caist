"""Read-only application queries used by the CAIST desktop UI."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config.settings import DATABASE_PATH, RIVERS_FILE, BOUNDARIES_FILE


def _connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"Database tidak ditemukan: {path}")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def load_ui_snapshot(
    db_path: str | Path | None = None,
    boundaries_path: str | Path | None = None,
    rivers_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load one consistent read-only snapshot; missing/invalid data stays explicit."""
    database = Path(db_path) if db_path is not None else DATABASE_PATH
    boundaries_file = Path(boundaries_path) if boundaries_path is not None else BOUNDARIES_FILE
    rivers_file = Path(rivers_path) if rivers_path is not None else RIVERS_FILE
    result: dict[str, Any] = {
        "connected": False, "error": None, "data_version": None, "regions": [],
        "history": {"district_days": 0, "source_rows": 0, "date_start": None, "date_end": None},
        "daily": {"rows": 0, "date_start": None, "date_end": None},
        "datasets": [],
    }
    try:
        connection = _connect_readonly(database)
        try:
            version_row = connection.execute(
                "SELECT data_version FROM daily_features ORDER BY data_version DESC LIMIT 1"
            ).fetchone()
            if version_row is None:
                raise ValueError("Database belum memiliki fitur harian Stage 4.")
            version = str(version_row["data_version"])
            regions = [dict(row) for row in connection.execute(
                "SELECT region_id AS district_code, region_name AS district_name, parent_code, parent_name "
                "FROM regions ORDER BY parent_code, region_name"
            )]
            daily = dict(connection.execute(
                "SELECT COUNT(*) AS rows, MIN(feature_date) AS date_start, MAX(feature_date) AS date_end "
                "FROM daily_features WHERE data_version=?", (version,)
            ).fetchone())
            history = dict(connection.execute(
                "SELECT COUNT(*) AS district_days, COALESCE(SUM(source_event_rows),0) AS source_rows, "
                "MIN(event_date) AS date_start, MAX(event_date) AS date_end "
                "FROM flood_events WHERE data_version=?", (version,)
            ).fetchone())
            static = connection.execute(
                "SELECT COUNT(*) AS rows, COUNT(elevation_mean_m) AS elevation_rows, "
                "COUNT(slope_mean_deg) AS slope_rows, COUNT(landcover_share_sum) AS cover_rows, "
                "COUNT(river_length_km) AS river_rows FROM region_static_features WHERE data_version=?", (version,)
            ).fetchone()
            parent_counts = {row["parent_code"]: row["count"] for row in connection.execute(
                "SELECT parent_code, COUNT(*) AS count FROM regions GROUP BY parent_code"
            )}
            result.update({
                "connected": True, "data_version": version, "regions": regions,
                "daily": daily, "history": history, "parent_counts": parent_counts,
                "static": dict(static),
            })
        finally:
            connection.close()
    except (sqlite3.Error, OSError, ValueError) as exc:
        result["error"] = str(exc)
        return result

    try:
        boundaries = json.loads(boundaries_file.read_text(encoding="utf-8"))
        boundary_count = len(boundaries.get("features", []))
        boundary_detail = f"{boundary_count:,} poligon kecamatan; EPSG:4326; " + ", ".join(
            f"{parent}: {count}" for parent, count in sorted(result["parent_counts"].items())
        )
        boundary_ok = boundary_count == len(result["regions"]) == 80
    except (OSError, ValueError, TypeError):
        boundary_count, boundary_detail, boundary_ok = 0, "GeoJSON batas tidak ditemukan atau tidak terbaca.", False

    try:
        river_geojson = json.loads(rivers_file.read_text(encoding="utf-8"))
        river_count = len(river_geojson.get("features", []))
        river_detail = f"{river_count:,} fitur garis GeoJSON; fitur turunan sungai per kecamatan: {result['static']['river_rows']:,}."
        river_ok = river_count > 0 and result["static"]["river_rows"] == 80
    except (OSError, ValueError, TypeError):
        river_count, river_detail, river_ok = 0, "GeoJSON jaringan sungai tidak ditemukan atau tidak terbaca.", False

    daily = result["daily"]
    history = result["history"]
    static = result["static"]
    dataset_rows = [
        ("CHIRPS", "Curah hujan harian", daily["rows"] > 0,
         f"{daily['rows']:,} baris kecamatan-hari; {daily['date_start']} s.d. {daily['date_end']} ({len(result['regions'])} kecamatan)."),
        ("BNPB", "Riwayat banjir", history["district_days"] > 0,
         f"{history['district_days']:,} kecamatan-hari kejadian dari {history['source_rows']:,} baris sumber; {history['date_start']} s.d. {history['date_end']}."),
        ("BOUNDARIES", "Batas administrasi", boundary_ok, boundary_detail),
        ("SRTM", "Elevasi dan slope", static["rows"] == 80 and static["elevation_rows"] == 80 and static["slope_rows"] == 80,
         f"{static['elevation_rows']:,} ringkasan elevasi dan {static['slope_rows']:,} ringkasan slope; 80 kecamatan."),
        ("WORLDCOVER", "Tutupan lahan ESA WorldCover", static["rows"] == 80 and static["cover_rows"] == 80,
         f"{static['cover_rows']:,} ringkasan kecamatan; proporsi 11 kelas tutupan lahan, tahun 2021."),
        ("RIVERS", "Jaringan sungai OpenStreetMap", river_ok, river_detail),
    ]
    result["datasets"] = [
        {"key": key, "name": name, "status": "Terintegrasi" if available else "Belum tersedia",
         "status_level": "success" if available else "unavailable", "detail": detail}
        for key, name, available, detail in dataset_rows
    ]
    return result
