"""Offline tests for the Stage 3 GeoJSON loader and embedded map widget."""

from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import geopandas as gpd  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.gis.map_data import _load_layer  # noqa: E402

_QT_APP = QApplication.instance() or QApplication([])


def test_polygon_layer_filters_label_points(tmp_path):
    """Synthetic test-only GeoJSON: one polygon and one label point."""
    polygon = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
    frame = gpd.GeoDataFrame(
        {"name": ["Test area", "Label only"]},
        geometry=[polygon, Point(1, 1)],
        crs="EPSG:4326",
    )
    path = tmp_path / "synthetic_test_only.geojson"
    frame.to_file(path, driver="GeoJSON")

    result = _load_layer(path, {"Polygon", "MultiPolygon"})

    assert result["status"] == "available"
    assert result["count"] == 1
    assert all(
        feature["geometry"]["type"] in {"Polygon", "MultiPolygon"}
        for feature in result["geojson"]["features"]
    )


def test_invalid_polygon_is_reported_without_changing_raw_input(tmp_path):
    """Synthetic invalid geometry is rejected for explicit processed repair."""
    bow_tie = Polygon([(3, 0), (5, 2), (3, 2), (5, 0), (3, 0)])
    frame = gpd.GeoDataFrame(
        {"name": ["Invalid test polygon"]},
        geometry=[bow_tie],
        crs="EPSG:4326",
    )
    path = tmp_path / "synthetic_test_only.geojson"
    frame.to_file(path, driver="GeoJSON")

    result = _load_layer(path, {"Polygon", "MultiPolygon"})

    assert result["status"] == "error"
    assert "data/processed/spatial/" in result["message"]
    assert path.is_file()


def test_river_layer_keeps_line_features_only(tmp_path):
    """Synthetic test-only GeoJSON with a line and an unrelated point."""
    frame = gpd.GeoDataFrame(
        {"name": ["Test river", "Label only"]},
        geometry=[LineString([(107.5, -6.9), (107.6, -6.8)]), Point(107.55, -6.85)],
        crs="EPSG:4326",
    )
    path = tmp_path / "synthetic_test_only.geojson"
    frame.to_file(path, driver="GeoJSON")

    result = _load_layer(path, {"LineString", "MultiLineString"})

    assert result["status"] == "available"
    assert result["count"] == 1
    assert result["geojson"]["features"][0]["properties"]["name"] == "Test river"


def test_map_bridge_returns_only_fixed_payload(monkeypatch):
    """Bridge smoke check; it has no filesystem or arbitrary-code API."""
    from app.widgets import leaflet_map

    monkeypatch.setattr(
        leaflet_map, "load_map_payload", lambda: {"boundaries": None, "rivers": None}
    )
    bridge = leaflet_map._MapBridge(
        {"boundaries": {"count": 0}, "rivers": {"count": 0}}
    )

    payload = json.loads(bridge.getMapData())

    assert payload == {"boundaries": {"count": 0}, "rivers": {"count": 0}}
    assert not hasattr(bridge, "readFile")
    assert not hasattr(bridge, "runCommand")


def test_leaflet_widget_loads_local_map_without_network(monkeypatch):
    """Widget initialization is local-only; tile/CDN requests are not asserted."""
    from app.widgets import leaflet_map

    monkeypatch_payload = {
        "boundaries": {"status": "unavailable", "count": 0, "geojson": None},
        "rivers": {"status": "unavailable", "count": 0, "geojson": None},
        "coverage_note": "Test fixture only",
    }
    monkeypatch.setattr(leaflet_map, "load_map_payload", lambda: monkeypatch_payload)
    widget = leaflet_map.LeafletMapWidget()

    assert widget.view is not None
    assert widget.view.url().toLocalFile().endswith("map/index.html")
    assert widget.channel is not None


def _synthetic_admin_rows(codes, start=0):
    """Build test-only kecamatan geometries and RBI-shaped attributes."""
    from shapely.geometry import box

    rows = []
    for offset, (code, district, parent_code, parent) in enumerate(codes, start):
        x = 107.0 + offset * 0.001
        rows.append(
            {
                "KDCPUM": code,
                "KDPKAB": parent_code,
                "WADMKC": district,
                "WADMKK": parent,
                "WADMPR": "Jawa Barat",
                "NAMOBJ": district,
                "METADATA": "synthetic_test_only",
                "geometry": box(x, -7.0, x + 0.0005, -6.9995),
            }
        )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def test_rbi_kecamatan_builder_selects_exact_eighty_features():
    """Synthetic test-only inputs mimic the two GDB source coverage patterns."""
    from src.gis.boundary_processing import (
        EXPECTED_COUNTS,
        build_bandung_raya_layer,
    )

    names = {
        "32.04": ("Bandung", 31),
        "32.17": ("Bandung Barat", 16),
        "32.73": ("Kota Bandung", 30),
        "32.77": ("Kota Cimahi", 3),
    }
    primary_rows = []
    secondary_rows = []
    for parent_code, (parent, count) in names.items():
        for number in range(1, count + 1):
            district_code = f"{parent_code}.{number:02d}"
            item = (
                district_code,
                f"Kecamatan {number}",
                parent_code,
                parent,
            )
            if parent_code == "32.17":
                secondary_rows.append(item)
            else:
                primary_rows.append(item)

    result = build_bandung_raya_layer(
        _synthetic_admin_rows(primary_rows),
        _synthetic_admin_rows(secondary_rows, start=len(primary_rows)),
    )

    assert len(result) == sum(EXPECTED_COUNTS.values()) == 80
    assert result["district_code"].is_unique
    assert result.crs.to_epsg() == 4326
    assert result.geom_type.isin({"Polygon", "MultiPolygon"}).all()
    assert result.groupby("parent_code").size().to_dict() == EXPECTED_COUNTS


def test_rbi_kecamatan_builder_rejects_incomplete_source():
    """The builder must not label an incomplete set as complete."""
    import pytest

    from src.gis.boundary_processing import build_bandung_raya_layer

    primary = _synthetic_admin_rows([("32.04.01", "Test", "32.04", "Bandung")])
    secondary = _synthetic_admin_rows([("32.17.01", "Test", "32.17", "Bandung Barat")])

    with pytest.raises(ValueError, match="Target kecamatan tidak lengkap"):
        build_bandung_raya_layer(primary, secondary)


def test_coverage_note_only_confirms_complete_verified_parent_counts():
    from src.gis.map_data import _coverage_note

    counts = {"32.04": 31, "32.17": 16, "32.73": 30, "32.77": 3}
    names = {
        "32.04": "Bandung",
        "32.17": "Bandung Barat",
        "32.73": "Kota Bandung",
        "32.77": "Kota Cimahi",
    }
    features = []
    for parent_code, count in counts.items():
        for number in range(count):
            features.append(
                {
                    "properties": {
                        "district_code": f"{parent_code}.{number:02d}",
                        "parent_code": parent_code,
                        "parent_name": names[parent_code],
                    }
                }
            )
    layer = {"status": "available", "geojson": {"features": features}}

    assert "80 kecamatan" in _coverage_note(layer)
    layer["geojson"]["features"].pop()
    assert "belum tervalidasi" in _coverage_note(layer)


def test_rbi_kecamatan_builder_rejects_duplicate_geometries():
    import pytest

    from src.gis.boundary_processing import build_bandung_raya_layer

    primary_codes = []
    secondary_codes = []
    for parent_code, (parent, count) in {
        "32.04": ("Bandung", 31),
        "32.17": ("Bandung Barat", 16),
        "32.73": ("Kota Bandung", 30),
        "32.77": ("Kota Cimahi", 3),
    }.items():
        target = secondary_codes if parent_code == "32.17" else primary_codes
        target.extend(
            (f"{parent_code}.{number:02d}", f"Kecamatan {number}", parent_code, parent)
            for number in range(1, count + 1)
        )
    primary = _synthetic_admin_rows(primary_codes)
    primary.at[1, "geometry"] = primary.geometry.iloc[0]

    with pytest.raises(ValueError, match="duplikat"):
        build_bandung_raya_layer(
            primary,
            _synthetic_admin_rows(secondary_codes, start=len(primary_codes)),
        )
