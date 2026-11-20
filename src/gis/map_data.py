"""Load and validate local GeoJSON layers for the Stage 3 map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd

from config.settings import BOUNDARIES_FILE, RIVERS_FILE

_LAYER_TYPES = {
    "boundaries": {"Polygon", "MultiPolygon"},
    "rivers": {"LineString", "MultiLineString"},
}


def _load_layer(path: Path, allowed_types: set[str]) -> dict[str, Any]:
    if not path.is_file():
        return {
            "status": "unavailable",
            "message": "File sumber layer tidak ditemukan.",
            "count": 0,
            "geojson": None,
        }

    try:
        frame = gpd.read_file(path)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Gagal membaca {path.name}: {exc}",
            "count": 0,
            "geojson": None,
        }

    if frame.crs is None:
        frame = frame.set_crs("EPSG:4326")
    elif frame.crs.to_epsg() != 4326:
        return {
            "status": "error",
            "message": (
                f"{path.name} is not EPSG:4326; reproject a derived copy under "
                "data/processed/spatial/ before display."
            ),
            "count": 0,
            "geojson": None,
        }

    geometry = frame.geometry
    keep = (
        geometry.notna() & ~geometry.is_empty & geometry.geom_type.isin(allowed_types)
    )
    frame = frame.loc[keep].copy()
    if frame.empty:
        return {
            "status": "unavailable",
            "message": (
                f"Tidak ada geometri {', '.join(sorted(allowed_types))} "
                "yang dapat ditampilkan."
            ),
            "count": 0,
            "geojson": None,
        }

    invalid_count = int((~frame.geometry.is_valid).sum())
    if invalid_count:
        return {
            "status": "error",
            "message": (
                f"{invalid_count} geometri invalid; perbaiki secara terkontrol "
                "dan simpan turunannya di data/processed/spatial/."
            ),
            "count": 0,
            "geojson": None,
        }

    return {
        "status": "available",
        "message": f"{len(frame)} fitur; EPSG:4326",
        "count": len(frame),
        "geojson": json.loads(frame.to_json(drop_id=False)),
    }


def _coverage_note(boundaries: dict[str, Any]) -> str:
    """Describe complete coverage only when the data itself proves it."""
    if boundaries.get("status") != "available":
        return "Cakupan batas kecamatan belum tersedia."

    features = (boundaries.get("geojson") or {}).get("features", [])
    expected = {"32.04": 31, "32.17": 16, "32.73": 30, "32.77": 3}
    parent_names = {
        "32.04": "Bandung",
        "32.17": "Bandung Barat",
        "32.73": "Kota Bandung",
        "32.77": "Kota Cimahi",
    }
    codes = []
    counts: dict[str, int] = {}
    names: dict[str, str] = {}
    for feature in features:
        properties = feature.get("properties") or {}
        district_code = properties.get("district_code")
        parent_code = str(properties.get("parent_code", ""))
        parent_name = properties.get("parent_name")
        if not district_code or not parent_code or not parent_name:
            return "Atribut kode/nama kecamatan dan wilayah induk tidak lengkap."
        codes.append(district_code)
        counts[parent_code] = counts.get(parent_code, 0) + 1
        names[parent_code] = parent_name

    if (
        len(features) == 80
        and len(set(codes)) == 80
        and counts == expected
        and names == parent_names
    ):
        return (
            "Cakupan tervalidasi: 80 kecamatan (Kabupaten Bandung 31, "
            "Kabupaten Bandung Barat 16, Kota Bandung 30, Kota Cimahi 3)."
        )
    return "Cakupan belum tervalidasi terhadap 80 kode kecamatan yang diharapkan."


def load_map_payload() -> dict[str, Any]:
    """Return validated layers; the bridge never exposes arbitrary file access."""
    boundaries = _load_layer(BOUNDARIES_FILE, _LAYER_TYPES["boundaries"])
    rivers = _load_layer(RIVERS_FILE, _LAYER_TYPES["rivers"])
    return {
        "boundaries": boundaries,
        "rivers": rivers,
        "coverage_note": _coverage_note(boundaries),
    }
