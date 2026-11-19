"""Integration checks for the Stage 3-5 data-backed desktop UI."""

from __future__ import annotations

import os

import pytest

from config.settings import BOUNDARIES_FILE, DATABASE_PATH, MAP_FILE, RIVERS_FILE, ROOT_DIR
from src.database.ui_readers import load_ui_snapshot
from src.gis.map_data import load_map_payload

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_actual_database_and_dataset_inventory_are_connected():
    if not DATABASE_PATH.is_file():
        pytest.skip("Requires prepared local Stage 5 database data/caist.sqlite")
    snapshot = load_ui_snapshot()
    assert snapshot["connected"], snapshot.get("error")
    assert len(snapshot["regions"]) == 80
    assert snapshot["history"]["source_rows"] > 0
    assert snapshot["daily"]["rows"] > 0
    assert len(snapshot["datasets"]) == 6
    assert all(row["status"] == "Terintegrasi" for row in snapshot["datasets"])


def test_prediction_selector_uses_all_database_regions():
    if not DATABASE_PATH.is_file():
        pytest.skip("Requires prepared local Stage 5 database data/caist.sqlite")
    from PySide6.QtWidgets import QApplication
    from app.pages.prediction_page import PredictionPage

    app = QApplication.instance() or QApplication([])
    page = PredictionPage(data_snapshot=load_ui_snapshot())
    assert page.wilayah_combo.count() == 80
    assert len({page.wilayah_combo.itemData(i) for i in range(80)}) == 80
    page.close()
    app.processEvents()


def test_map_payload_contains_local_boundary_and_river_layers():
    if not BOUNDARIES_FILE.is_file() or not RIVERS_FILE.is_file():
        pytest.skip("Requires prepared local Stage 3 boundary and river GeoJSON files")
    payload = load_map_payload()
    assert payload["boundaries"]["status"] == "available"
    assert payload["boundaries"]["count"] == 80
    assert payload["rivers"]["status"] == "available"
    assert payload["rivers"]["count"] > 0
    assert "80 kecamatan" in payload["coverage_note"]


def test_leaflet_assets_are_loaded_from_project_files():
    html = MAP_FILE.read_text(encoding="utf-8")
    assert 'vendor/leaflet.css' in html
    assert 'vendor/leaflet.js' in html
    assert 'https://unpkg.com/leaflet' not in html
    for asset in ("leaflet.css", "leaflet.js", "LICENSE"):
        assert (ROOT_DIR / "map" / "vendor" / asset).is_file()
