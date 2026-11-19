"""Offline unit tests for the Stage 4 flood-label policy."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from src.data.spatial_preprocessing import _assign_flood_labels


def test_labels_use_event_window_and_dry_thresholds():
    dates = pd.date_range("2026-01-01", periods=12, freq="D")
    rows = []
    for code in ("D-A", "D-B"):
        for day in dates:
            rain = 1.0
            if code == "D-B" and day == pd.Timestamp("2026-01-12"):
                rain = 5.0
            rows.append({
                "district_code": code, "date": day, "precipitation_mm_day": rain,
                "flood_event_rows": 1 if code == "D-A" and day == pd.Timestamp("2026-01-07") else None,
            })
    daily = pd.DataFrame(rows)
    boundaries = gpd.GeoDataFrame({
        "district_code": ["D-A", "D-B"], "parent_code": ["P-1", "P-1"],
    }, geometry=[None, None])
    events = pd.DataFrame({
        "district_code": ["D-A"], "date": [pd.Timestamp("2026-01-07")],
    })
    report = {"unknown_parent_event_dates": [{"parent_code": "P-1", "date": "2026-01-07"}]}

    labeled = _assign_flood_labels(daily, boundaries, events, report)
    lookup = labeled.set_index(["district_code", "date"])["flood_label"]

    assert lookup[("D-A", pd.Timestamp("2026-01-07"))] == 1
    assert lookup[("D-A", pd.Timestamp("2026-01-04"))] == -1  # event within +/-3 days
    assert lookup[("D-A", pd.Timestamp("2026-01-11"))] == 0  # dry and outside event window
    assert lookup[("D-B", pd.Timestamp("2026-01-07"))] == -1  # parent-level unknown event
    assert lookup[("D-B", pd.Timestamp("2026-01-11"))] == 0
    assert lookup[("D-B", pd.Timestamp("2026-01-12"))] == -1  # daily rain >= 5 mm
    assert labeled.loc[labeled.flood_label == 0, "label_status"].eq("pseudo_absence_hydro").all()


def test_three_day_rain_threshold_is_strictly_below_ten_mm():
    dates = pd.date_range("2026-02-01", periods=4, freq="D")
    daily = pd.DataFrame({
        "district_code": ["D-A"] * 4, "date": dates,
        "precipitation_mm_day": [3.0, 3.0, 4.0, 4.0],
        "flood_event_rows": [None] * 4,
    })
    boundaries = gpd.GeoDataFrame({"district_code": ["D-A"], "parent_code": ["P-1"]}, geometry=[None])
    labeled = _assign_flood_labels(daily, boundaries, pd.DataFrame(columns=["district_code", "date"]), {"unknown_parent_event_dates": []})
    lookup = labeled.set_index("date")["flood_label"]

    assert lookup[pd.Timestamp("2026-02-03")] == -1  # trailing accumulation equals 10 mm, not below threshold
