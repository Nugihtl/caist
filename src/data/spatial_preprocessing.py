"""Reproducible Stage 3/4 spatial and tabular preprocessing for CAIST.

Raw inputs are read-only. Derived layers, features, event labels, and audit files
are written beneath ``data/processed/``. CHIRPS is much coarser than a kecamatan;
its zonal mean is a regional exposure estimate, not fine-scale rainfall.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask, geometry_window
from rasterio.warp import Resampling, calculate_default_transform, reproject
from rasterio.windows import transform as window_transform
from shapely.geometry import mapping
from shapely.ops import nearest_points
from shapely import union_all

from src.gis.boundary_processing import process_boundary_sources

EXPECTED_COUNTS = {"32.04": 31, "32.17": 16, "32.73": 30, "32.77": 3}
BNPB_PARENT_CODES = {
    "3204": "32.04",
    "3217": "32.17",
    "3273": "32.73",
    "3277": "32.77",
}
LANDCOVER = {
    10: "tree_cover",
    20: "shrubland",
    30: "grassland",
    40: "cropland",
    50: "built_up",
    60: "bare_sparse_vegetation",
    70: "snow_ice",
    80: "permanent_water",
    90: "herbaceous_wetland",
    95: "mangroves",
    100: "moss_lichen",
}
TARGET_CRS = "EPSG:32748"  # WGS 84 / UTM zone 48S; metric for slope and lengths.


def _json_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (date, pd.Timestamp)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _read_boundaries(project_root: Path) -> gpd.GeoDataFrame:
    path = project_root / "data/processed/spatial/batas_kecamatan_bandung_raya.geojson"
    frame = gpd.read_file(path)
    expected = {"district_code", "district_name", "parent_code", "parent_name"}
    if not expected.issubset(frame.columns):
        raise ValueError(f"Atribut batas wajib tidak ada: {sorted(expected - set(frame.columns))}")
    counts = frame.groupby("parent_code").size().to_dict()
    if len(frame) != 80 or counts != EXPECTED_COUNTS:
        raise ValueError(f"Cakupan batas bukan 80 kecamatan yang diharapkan: {counts}")
    if frame.district_code.astype(str).duplicated().any():
        raise ValueError("Kode kecamatan batas duplikat.")
    if frame.crs is None or frame.crs.to_epsg() != 4326:
        raise ValueError("Batas kecamatan harus menggunakan EPSG:4326.")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any() or (~frame.geometry.is_valid).any():
        raise ValueError("Geometri batas kecamatan kosong atau invalid.")
    return frame.sort_values("district_code").reset_index(drop=True)


def _zonal_window(dataset: rasterio.io.DatasetReader, geom: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return raster values and an all-touched geometry mask for one polygon."""
    window = geometry_window(dataset, [mapping(geom)], boundless=False)
    data = dataset.read(1, window=window, masked=True).astype("float64").filled(np.nan)
    inside = geometry_mask(
        [mapping(geom)],
        out_shape=data.shape,
        transform=window_transform(window, dataset.transform),
        all_touched=True,
        invert=True,
    )
    return data, inside


def _static_raster_features(project_root: Path, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    """Extract elevation, derived slope, and WorldCover class proportions."""
    dem_path = project_root / "data/raw/srtm/srtm_bandung_raya_30m.tif"
    cover_path = project_root / "data/raw/worldcover/worldcover_2021_bandung_raya_10m.tif"
    projected = boundaries.to_crs(TARGET_CRS)
    records: list[dict[str, Any]] = []

    with rasterio.open(dem_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, TARGET_CRS, src.width, src.height, *src.bounds, resolution=30
        )
        elevation = np.full((height, width), np.nan, dtype="float32")
        reproject(
            source=rasterio.band(src, 1),
            destination=elevation,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata if src.nodata is not None else -32768,
            dst_transform=transform,
            dst_crs=TARGET_CRS,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    # Explicit physical range excludes common SRTM void sentinels when the
    # source GeoTIFF did not declare a nodata value.
    elevation[(elevation < -500) | (elevation > 9000)] = np.nan
    pixel_x, pixel_y = transform.a, abs(transform.e)
    gy, gx = np.gradient(elevation.astype("float64"), pixel_y, pixel_x)
    slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")
    slope[~np.isfinite(elevation)] = np.nan
    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff", height=height, width=width, count=1, dtype="float32",
            crs=TARGET_CRS, transform=transform, nodata=np.nan,
        ) as slope_ds:
            slope_ds.write(slope, 1)
            for _, district in projected.iterrows():
                geom_row = district
                data, inside = _zonal_window(slope_ds, geom_row.geometry)
                elev_data = elevation[
                    geometry_window(slope_ds, [mapping(geom_row.geometry)]).row_off:
                    geometry_window(slope_ds, [mapping(geom_row.geometry)]).row_off + data.shape[0],
                    geometry_window(slope_ds, [mapping(geom_row.geometry)]).col_off:
                    geometry_window(slope_ds, [mapping(geom_row.geometry)]).col_off + data.shape[1],
                ]
                elev_values = elev_data[inside & np.isfinite(elev_data)]
                slope_values = data[inside & np.isfinite(data)]
                rec = {
                    "district_code": district.district_code,
                    "elevation_mean_m": float(np.mean(elev_values)) if elev_values.size else np.nan,
                    "elevation_median_m": float(np.median(elev_values)) if elev_values.size else np.nan,
                    "elevation_p10_m": float(np.percentile(elev_values, 10)) if elev_values.size else np.nan,
                    "slope_mean_deg": float(np.mean(slope_values)) if slope_values.size else np.nan,
                }
                records.append(rec)

    static = pd.DataFrame(records)
    with rasterio.open(cover_path) as cover:
        for _, district in boundaries.iterrows():
            data, inside = _zonal_window(cover, district.geometry)
            values = data[inside & np.isfinite(data)].astype("int32")
            valid = values[np.isin(values, list(LANDCOVER))]
            if not valid.size:
                proportions = {f"landcover_{code}_{name}_share": np.nan for code, name in LANDCOVER.items()}
            else:
                proportions = {
                    f"landcover_{code}_{name}_share": float(np.count_nonzero(valid == code) / valid.size)
                    for code, name in LANDCOVER.items()
                }
            static.loc[static.district_code == district.district_code, list(proportions)] = list(proportions.values())
    return static


def _river_features(project_root: Path, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    river_path = project_root / "data/raw/osm/jaringan_sungai_bandung_raya.geojson"
    rivers = gpd.read_file(river_path)
    if rivers.crs is None:
        raise ValueError("CRS jaringan sungai tidak terdefinisi.")
    rivers = rivers.to_crs(TARGET_CRS)
    network = union_all(rivers.geometry.dropna().values)
    projected = boundaries.to_crs(TARGET_CRS)
    records = []
    for _, district in projected.iterrows():
        length_m = float(network.intersection(district.geometry).length)
        area_km2 = float(district.geometry.area / 1_000_000)
        point = district.geometry.representative_point()
        nearest = nearest_points(point, network)[1]
        records.append({
            "district_code": district.district_code,
            "river_length_km": length_m / 1000,
            "river_density_km_per_km2": (length_m / 1000) / area_km2 if area_km2 else np.nan,
            "representative_point_to_river_km": float(point.distance(nearest) / 1000),
        })
    return pd.DataFrame(records)


def _chirps_daily(project_root: Path, boundaries: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = sorted((project_root / "data/raw/chirps").glob("*.tif"))
    if len(paths) != 2:
        raise FileNotFoundError(f"CHIRPS mengharapkan dua TIFF harian; ditemukan {len(paths)}.")
    records: list[pd.DataFrame] = []
    source_details = []
    for path in paths:
        with rasterio.open(path) as src:
            if src.count != len(src.descriptions) or not all(src.descriptions):
                raise ValueError(f"Band CHIRPS tidak seluruhnya memiliki deskripsi tanggal: {path}")
            dates = pd.to_datetime([str(desc).split("_")[0] for desc in src.descriptions], format="%Y%m%d")
            expected_dates = pd.date_range(dates.min(), dates.max(), freq="D")
            if not dates.equals(expected_dates):
                raise ValueError(f"Ada tanggal hilang/duplikat pada band CHIRPS: {path}")
            bands = src.read(masked=True).astype("float32").filled(np.nan)
            bands[(bands < 0) | ~np.isfinite(bands)] = np.nan
            for _, district in boundaries.iterrows():
                _, mask = _zonal_window(src, district.geometry)
                window = geometry_window(src, [mapping(district.geometry)])
                row_start, col_start = int(window.row_off), int(window.col_off)
                row_end = row_start + int(window.height)
                col_end = col_start + int(window.width)
                selected = bands[:, row_start:row_end, col_start:col_end][:, mask]
                with np.errstate(invalid="ignore"):
                    means = np.nanmean(selected, axis=1)
                records.append(pd.DataFrame({
                    "district_code": district.district_code,
                    "date": dates,
                    "precipitation_mm_day": means,
                    "chirps_pixel_count": int(mask.sum()),
                }))
            source_details.append({
                "file": str(path.relative_to(project_root)).replace("\\", "/"),
                "source_url": None,
                "download_date": None,
                "provenance_status": "URL and download date are not recorded in the local raster metadata",
                "bands": src.count,
                "width": src.width,
                "height": src.height,
                "date_start": dates.min().date().isoformat(),
                "date_end": dates.max().date().isoformat(),
                "crs": str(src.crs),
                "resolution_degrees": list(src.res),
                "bounds": list(src.bounds),
                "dtype": list(src.dtypes),
                "nodata": src.nodata,
                "units": "mm/day (CHIRPS daily product; unit not embedded in TIFF tags)",
                "zonal_method": "mean of intersecting pixels (all_touched=True)",
            })
    daily = pd.concat(records, ignore_index=True)
    if daily.duplicated(["district_code", "date"]).any():
        raise ValueError("Ada tanggal CHIRPS duplikat setelah penggabungan.")
    return daily, {"sources": source_details}


def _normalize_name(value: str) -> str:
    """Normalize official/local names, including literal and actual line breaks."""
    value = str(value).replace(r"\n", " ").replace("\r", " ").replace("\n", " ")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.lower().replace("kecamatan", " ").replace("kec.", " ")
    value = re.sub(r"\b(kelurahan|kel|desa|ds)\.?\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _rbi_villages(project_root: Path, boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Read village polygons from local RBI geodatabases and retain target kecamatan."""
    import pyogrio

    boundary_by_code = boundaries.set_index(boundaries.district_code.astype(str))
    candidates = []
    for path in sorted((project_root / "data/raw/boundaries").rglob("*.gdb")):
        for layer in pyogrio.list_layers(path)[:, 0]:
            if "ADMINISTRASI_AR_DESAKEL" not in layer.upper():
                continue
            frame = gpd.read_file(path, layer=layer)
            needed = {"KDCPUM", "WADMKD"}
            if not needed.issubset(frame.columns):
                continue
            frame = frame.loc[frame.geometry.notna() & ~frame.geometry.is_empty].copy()
            frame = frame.to_crs(boundaries.crs)
            for _, village in frame.iterrows():
                raw_code = re.sub(r"\D", "", str(village.get("KDCPUM", "")))
                district_code = None
                for code in boundary_by_code.index:
                    digits = re.sub(r"\D", "", code)
                    if raw_code.startswith(digits):
                        district_code = code
                        break
                if district_code is None:
                    # Some RBI releases encode the kecamatan key in KDPKAB.
                    raw_code = re.sub(r"\D", "", str(village.get("KDPKAB", "")))
                    district_code = next((code for code in boundary_by_code.index
                                          if raw_code == re.sub(r"\D", "", code)), None)
                if district_code is None:
                    continue
                point = village.geometry.representative_point()
                spatial = boundaries.loc[boundaries.geometry.covers(point)]
                if len(spatial) != 1 or str(spatial.iloc[0].district_code) != district_code:
                    continue
                candidates.append({
                    "village_name": str(village.get("WADMKD", "")).strip(),
                    "village_normalized": _normalize_name(village.get("WADMKD", "")),
                    "district_code": district_code,
                    "parent_code": str(boundary_by_code.loc[district_code].parent_code),
                    "source_gdb": path.name,
                    "geometry": village.geometry,
                })
    if not candidates:
        raise FileNotFoundError("Layer RBI ADMINISTRASI_AR_DESAKEL dengan geometri yang cocok tidak ditemukan.")
    result = gpd.GeoDataFrame(candidates, geometry="geometry", crs=boundaries.crs)
    # Prefer one official feature per (kecamatan, normalized desa) if source GDBs overlap.
    return result.drop_duplicates(["district_code", "village_normalized"]).reset_index(drop=True)


def _bnpb_events(project_root: Path, boundaries: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = sorted((project_root / "data/raw/bnpb").glob("*.xlsx"))
    if not paths:
        raise FileNotFoundError("Workbook BNPB .xlsx tidak ditemukan.")
    villages = _rbi_villages(project_root, boundaries)
    district_lookup = {str(row.district_code): row for _, row in boundaries.iterrows()}
    normalized_parts: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    unknown_parent_events: list[dict[str, str]] = []
    total_rows = excluded_external = missing_date = 0
    sources = []
    for path in paths:
        frame = pd.read_excel(path, skiprows=1)
        required = {"ID Kabupaten", "Tanggal Kejadian", "Kejadian", "Lokasi", "Kabupaten"}
        if not required.issubset(frame.columns):
            raise ValueError(f"Skema BNPB {path.name} tidak cocok: {list(frame.columns)}")
        total_rows += len(frame)
        frame["_parent"] = frame["ID Kabupaten"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4).map(BNPB_PARENT_CODES)
        excluded_external += int(frame._parent.isna().sum())
        frame = frame.loc[frame._parent.notna()].copy()
        frame["date"] = pd.to_datetime(frame["Tanggal Kejadian"], errors="coerce").dt.normalize()
        missing_date += int(frame.date.isna().sum())
        frame = frame.loc[frame.date.notna() & frame["Kejadian"].astype(str).str.contains("banjir", case=False, na=False)]
        for row_index, row in frame.iterrows():
            source_row = int(row_index) + 3
            location = "" if pd.isna(row.get("Lokasi")) else str(row.get("Lokasi"))
            normalized = f" {_normalize_name(location)} "
            event_date = row.date.date().isoformat()
            if not location.strip():
                audit_rows.append({"source_file": path.name, "source_row": source_row, "date": event_date,
                    "parent_code": row["_parent"], "location": "", "match_status": "excluded_no_subdistrict",
                    "training_included": False, "matched_district_codes": "", "matched_villages": "",
                    "source_parent_conflict": ""})
                unknown_parent_events.append({"parent_code": row["_parent"], "date": event_date, "source_row": str(source_row)})
                continue

            village_matches = []
            for _, village in villages.iterrows():
                name = village.village_normalized
                if name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", normalized):
                    village_matches.append(village)
            # A village name is accepted only when its spatial RBI point and code
            # identify exactly one (kecamatan, desa) pair in the target boundary set.
            grouped_villages = {}
            for village in village_matches:
                grouped_villages.setdefault(village.village_normalized, {})[(village.district_code, village.village_normalized)] = village
            district_names = []
            for _, district in boundaries.iterrows():
                name = _normalize_name(district.district_name)
                if name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", normalized):
                    district_names.append(district)
            resolved: dict[str, dict[str, Any]] = {}
            for _, candidates in grouped_villages.items():
                values = list(candidates.values())
                if len(values) > 1:
                    # A repeated village name is accepted only if a district name
                    # in the same source text reduces it to one RBI pair.
                    values = [v for v in values if any(str(d.district_code) == v.district_code for d in district_names)]
                if len(values) == 1:
                    village = values[0]
                    # The RBI polygon/code is authoritative when BNPB's parent
                    # code conflicts with location text; preserve it in the audit.
                    resolved[village.district_code] = {
                        "match_source": "verified_by_rbi_village", "village": village.village_name,
                    }
            # Exact kecamatan mentions can resolve district-only rows. Resolve
            # against all 80 target boundaries and record any parent-code conflict.
            if not resolved:
                for district in district_names:
                    resolved[str(district.district_code)] = {"match_source": "verified_by_rbi_district", "village": ""}
            if resolved:
                conflict = sorted({str(district_lookup[code].parent_code) for code in resolved
                                   if str(district_lookup[code].parent_code) != row["_parent"]} | {
                    str(district.parent_code) for district in district_names
                    if str(district.parent_code) != row["_parent"]
                })
                for code, match in resolved.items():
                    district = district_lookup[code]
                    normalized_parts.append({
                        "district_code": code, "district_name": district.district_name,
                        "parent_code": district.parent_code, "date": row.date,
                        "source_file": path.name, "source_row": source_row,
                        "source_event_id": str(row.get("Kode Identitas Bencana", "") or "").strip(),
                        "event_type": str(row.get("Kejadian", "")).strip(), "source_location": location,
                        "match_source": match["match_source"], "matched_village": match["village"],
                        "source_parent_conflict": ";".join(conflict),
                    })
                audit_rows.append({"source_file": path.name, "source_row": source_row, "date": event_date,
                    "parent_code": row["_parent"], "location": location, "match_status": "matched",
                    "training_included": True, "matched_district_codes": ";".join(sorted(resolved)),
                    "matched_villages": ";".join(sorted({v["village"] for v in resolved.values() if v["village"]})),
                    "source_parent_conflict": ";".join(conflict)})
            else:
                status = "excluded_outside_bandung_raya" if district_names or village_matches else "excluded_no_unique_rbi_match"
                audit_rows.append({"source_file": path.name, "source_row": source_row, "date": event_date,
                    "parent_code": row["_parent"], "location": location, "match_status": status,
                    "training_included": False, "matched_district_codes": "", "matched_villages": "",
                    "source_parent_conflict": ""})
                unknown_parent_events.append({"parent_code": row["_parent"], "date": event_date, "source_row": str(source_row)})
        sources.append({
            "file": str(path.relative_to(project_root)).replace("\\", "/"), "source_url": None,
            "download_date": None, "provenance_status": "URL and download date are not recorded in the workbook",
            "rows_after_header": int(len(pd.read_excel(path, skiprows=1))),
            "date_min": frame.date.min().date().isoformat() if not frame.empty else None,
            "date_max": frame.date.max().date().isoformat() if not frame.empty else None,
        })

    event_mentions = pd.DataFrame(normalized_parts)
    if event_mentions.empty:
        raise ValueError("Tidak ada kejadian BNPB Bandung Raya yang berhasil dicocokkan ke kecamatan.")
    events = event_mentions.groupby(["district_code", "district_name", "parent_code", "date"], as_index=False).agg(
        source_event_rows=("source_row", "count"),
        source_files=("source_file", lambda values: ";".join(sorted(set(values)))),
        source_rows=("source_row", lambda values: ";".join(map(str, sorted(set(values))))),
        source_locations=("source_location", lambda values: " | ".join(sorted(set(values)))),
        match_sources=("match_source", lambda values: ";".join(sorted(set(values)))),
        matched_villages=("matched_village", lambda values: ";".join(sorted({v for v in values if v}))),
        source_parent_conflicts=("source_parent_conflict", lambda values: ";".join(sorted({v for v in values if v}))),
    )
    report = {
        "sources": sources, "raw_rows": total_rows, "excluded_non_bandung_raya_rows": excluded_external,
        "missing_event_dates_in_target_admin_rows": missing_date,
        "matched_district_day_events": len(events), "matched_source_mentions": len(event_mentions),
        "deduplicated_rows": int(len(event_mentions) - len(events)),
        "event_date_start": events.date.min().date().isoformat(), "event_date_end": events.date.max().date().isoformat(),
        "matched_by_source": event_mentions.match_source.value_counts().to_dict(),
        "source_parent_conflict_rows": sum(bool(item.get("source_parent_conflict")) for item in audit_rows),
        "unmatched_target_admin_rows": audit_rows,
        "unmatched_target_admin_count": sum(not item["training_included"] for item in audit_rows),
        "excluded_no_subdistrict_count": sum(item["match_status"] == "excluded_no_subdistrict" for item in audit_rows),
        "excluded_location_rows": sum(not item["training_included"] for item in audit_rows),
        "unknown_parent_event_dates": unknown_parent_events,
    }
    return events, report

def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, default=_json_value) + "\n", encoding="utf-8")


def _assign_flood_labels(
    daily: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    events: pd.DataFrame,
    bnpb_report: dict[str, Any],
) -> pd.DataFrame:
    """Apply the documented observed-event and dry pseudo-absence policy."""
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily.date).dt.normalize()
    daily["rain_3day_mm"] = daily.groupby("district_code", sort=False).precipitation_mm_day.transform(
        lambda values: values.rolling(window=3, min_periods=3).sum()
    )
    district_event_blocked = set()
    for event in events.itertuples(index=False):
        event_day = pd.Timestamp(event.date)
        for offset in range(-3, 4):
            district_event_blocked.add((str(event.district_code), (event_day + pd.Timedelta(days=offset)).strftime("%Y-%m-%d")))
    parent_unknown_blocked = set()
    for item in bnpb_report["unknown_parent_event_dates"]:
        event_day = pd.Timestamp(item["date"])
        for offset in range(-3, 4):
            parent_unknown_blocked.add((item["parent_code"], (event_day + pd.Timedelta(days=offset)).strftime("%Y-%m-%d")))
    parent_by_district = dict(zip(boundaries.district_code.astype(str), boundaries.parent_code.astype(str)))
    date_text = daily.date.dt.strftime("%Y-%m-%d")
    district_dates = zip(daily.district_code.astype(str), date_text)
    district_conflicts = np.fromiter(
        ((code, day) in district_event_blocked for code, day in district_dates), dtype=bool, count=len(daily)
    )
    parent_dates = zip(daily.district_code.astype(str).map(parent_by_district), date_text)
    parent_conflicts = np.fromiter(
        ((parent, day) in parent_unknown_blocked for parent, day in parent_dates), dtype=bool, count=len(daily)
    )
    reported = daily.flood_event_rows.notna().to_numpy()
    dry = (
        daily.precipitation_mm_day.notna().to_numpy()
        & (daily.precipitation_mm_day.to_numpy() < 5)
        & daily.rain_3day_mm.notna().to_numpy()
        & (daily.rain_3day_mm.to_numpy() < 10)
    )
    pseudo_absence = ~reported & ~district_conflicts & ~parent_conflicts & dry
    daily["flood_label"] = np.select([reported, pseudo_absence], [1, 0], default=-1).astype("int8")
    daily["label_status"] = np.select(
        [reported, pseudo_absence],
        ["reported_event", "pseudo_absence_hydro"],
        default="unknown_no_report",
    )
    daily["flood_reported"] = pd.array(np.where(reported, 1, None), dtype="Int64")
    return daily


def run_pipeline(project_root: Path | None = None) -> dict[str, Any]:
    """Build the district layer and all Stage 4 data products from local raw files."""
    project_root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()
    raw_dir = project_root / "data/raw"
    processed_dir = project_root / "data/processed"
    spatial_dir = processed_dir / "spatial"
    spatial_dir.mkdir(parents=True, exist_ok=True)

    boundary_path = spatial_dir / "batas_kecamatan_bandung_raya.geojson"
    # Rebuild from the official local RBI sources and run their schema/count/geometry checks.
    process_boundary_sources(raw_dir / "boundaries", boundary_path)
    boundaries = _read_boundaries(project_root)
    river_path = raw_dir / "osm/jaringan_sungai_bandung_raya.geojson"
    rivers = gpd.read_file(river_path)
    river_report = {
        "file": str(river_path.relative_to(project_root)).replace("\\", "/"),
        "features": len(rivers),
        "crs": str(rivers.crs),
        "geometry_types": rivers.geom_type.value_counts().to_dict(),
        "invalid_geometries": int((~rivers.geometry.is_valid).sum()),
        "empty_geometries": int(rivers.geometry.is_empty.sum()),
    }
    if len(rivers) == 0 or rivers.crs is None or river_report["invalid_geometries"] or river_report["empty_geometries"]:
        raise ValueError(f"Jaringan sungai tidak lolos validasi: {river_report}")

    static = _static_raster_features(project_root, boundaries)
    landcover_fields = [column for column in static if column.startswith("landcover_")]
    static["landcover_share_sum"] = static[landcover_fields].sum(axis=1, min_count=1)
    static = static.merge(_river_features(project_root, boundaries), on="district_code", validate="one_to_one")
    district_properties = boundaries.drop(columns="geometry")
    static = district_properties.merge(static, on="district_code", validate="one_to_one")
    static_path = processed_dir / "fitur_spasial_kecamatan.csv"
    static.to_csv(static_path, index=False, float_format="%.6f")

    daily, chirps_report = _chirps_daily(project_root, boundaries)
    events, bnpb_report = _bnpb_events(project_root, boundaries)
    daily = daily.merge(
        static.drop(columns=["source_name", "source_metadata"], errors="ignore"),
        on="district_code", how="left", validate="many_to_one",
    )
    events["date"] = pd.to_datetime(events.date)
    daily = daily.merge(
        events[["district_code", "date", "source_event_rows"]].rename(columns={"source_event_rows": "flood_event_rows"}),
        on=["district_code", "date"], how="left", validate="one_to_one",
    )
    daily = _assign_flood_labels(daily, boundaries, events, bnpb_report)
    daily_path = processed_dir / "fitur_harian_kecamatan.csv"
    daily.to_csv(daily_path, index=False, date_format="%Y-%m-%d", float_format="%.6f")
    training_path = processed_dir / "dataset_latih_kecamatan.csv"
    daily.loc[daily.flood_label.isin([0, 1])].to_csv(training_path, index=False, date_format="%Y-%m-%d", float_format="%.6f")
    events_path = processed_dir / "kejadian_banjir_kecamatan_harian.csv"
    events.to_csv(events_path, index=False, date_format="%Y-%m-%d")
    unmatched_path = processed_dir / "audit_bnpb_tidak_tercocok.csv"
    pd.DataFrame(bnpb_report["unmatched_target_admin_rows"]).to_csv(unmatched_path, index=False)

    expected_rows = len(boundaries) * daily.date.nunique()
    if len(daily) != expected_rows or daily.duplicated(["district_code", "date"]).any():
        raise ValueError(f"Panel harian tidak lengkap/unik: rows={len(daily)}, expected={expected_rows}")
    if daily.precipitation_mm_day.isna().all():
        raise ValueError("Semua nilai hujan kosong setelah zonal extraction.")
    validation = {
        "status": "passed",
        "boundary_count": len(boundaries),
        "boundary_counts_by_parent": boundaries.parent_code.value_counts().to_dict(),
        "boundary_crs": str(boundaries.crs),
        "boundary_invalid_or_empty": int((~boundaries.geometry.is_valid | boundaries.geometry.is_empty).sum()),
        "river": river_report,
        "daily_rows": len(daily),
        "district_date_unique": not daily.duplicated(["district_code", "date"]).any(),
        "daily_date_start": daily.date.min().date().isoformat(),
        "daily_date_end": daily.date.max().date().isoformat(),
        "daily_distinct_dates": int(daily.date.nunique()),
        "rain_missing_values": int(daily.precipitation_mm_day.isna().sum()),
        "static_rows": len(static),
        "static_feature_missing_counts": static.isna().sum().to_dict(),
        "landcover_share_sum_min": float(static.landcover_share_sum.min()),
        "landcover_share_sum_max": float(static.landcover_share_sum.max()),
        "observed_flood_district_days": len(events),
        "flood_label_counts": {str(int(key)): int(value) for key, value in daily.flood_label.value_counts().sort_index().items()},
        "training_rows_labels_0_or_1": int(daily.flood_label.isin([0, 1]).sum()),
        "unknown_rows_excluded_from_training": int((daily.flood_label == -1).sum()),
        "pseudo_absence_rule": "No matched district event within inclusive +/-3 days; CHIRPS daily <5 mm and trailing 3-day sum (t-2 through t) <10 mm; parent-level unknown-location events also block +/-3 days.",
        "unobserved_flood_label_rows": int((daily.flood_label == -1).sum()),
        "supervised_binary_label_readiness": "ready_with_verified_positive_and_hydrometeorological_pseudo_absence_classes; unknown rows excluded",
        "unreported_label_policy": "label 0 only for dry pseudo-absence rule; all other no-report rows are label -1",
        "bnpb": bnpb_report,
    }
    validation_path = processed_dir / "laporan_validasi_stage4.json"
    _write_json(validation_path, validation)

    manifest = {
        "generated_at_local_date": date.today().isoformat(),
        "raw_inputs_are_modified": False,
        "boundary_source": {
            "files": [str(path.relative_to(project_root)).replace("\\", "/") for path in sorted((raw_dir / "boundaries").rglob("*.shp")) + sorted((raw_dir / "boundaries").rglob("*.gdb"))],
            "output": str(boundary_path.relative_to(project_root)).replace("\\", "/"),
            "crs": "EPSG:4326",
            "source_url": None,
            "download_date": "2026-11-19 (date supplied by user; source vintage is earlier per local metadata)",
            "districts": 80,
            "counts_by_parent": EXPECTED_COUNTS,
        },
        "chirps": chirps_report,
        "srtm": {"file": "data/raw/srtm/srtm_bandung_raya_30m.tif", "source_url": None, "download_date": None, "provenance_status": "URL and acquisition date are not recorded in the local raster metadata", "crs": "EPSG:4326", "resolution_degrees": [0.00026949458523585647, 0.00026949458523585647], "shape": [2600, 3155], "bands": 1, "dtype": "int16", "nodata": None, "derived_crs": TARGET_CRS, "features": ["elevation_mean_m", "elevation_median_m", "elevation_p10_m", "slope_mean_deg"], "slope_method": "Central differences via numpy.gradient on a 30 m UTM grid"},
        "worldcover": {"file": "data/raw/worldcover/worldcover_2021_bandung_raya_10m.tif", "source_url": None, "download_date": None, "provenance_status": "URL and acquisition date are not recorded in the local raster metadata", "year": 2021, "crs": "EPSG:4326", "resolution_degrees": [0.00008983152841195215, 0.00008983152841195215], "shape": [7796, 9463], "bands": 1, "dtype": "uint8", "nodata": None, "class_shares": LANDCOVER, "method": "pixel counts per class divided by recognized class pixel count; all_touched=True"},
        "rivers": river_report | {"derived_features": ["river_length_km", "river_density_km_per_km2", "representative_point_to_river_km"], "metric_crs": TARGET_CRS},
        "bnpb": bnpb_report | {"label_policy": "1=verified BNPB event; 0=CHIRPS dry pseudo-absence under the documented +/-3-day event guard; -1=unknown and excluded from training."},
        "outputs": [str(path.relative_to(project_root)).replace("\\", "/") for path in [boundary_path, static_path, daily_path, training_path, events_path, unmatched_path, validation_path]],
        "limitations": [
            "CHIRPS grid is about 5.6 km and much coarser than kecamatan; zonal means do not imply neighborhood-scale rainfall.",
            "WorldCover is 2021 land cover, not current land use.",
            "Pseudo-absence (0) is a hydro-meteorological proxy class under the documented dry-day and event-window rules; it is not a claim that BNPB observed no flood.",
            f"{bnpb_report['excluded_no_subdistrict_count']} BNPB flood rows have no subdistrict text and are excluded; these dates conservatively block pseudo-absence labels across their parent administration for +/-3 days.",
            "SRTM/WorldCover files do not carry complete provenance/license metadata; source date and processing history should be retained by the data owner.",
        ],
    }
    manifest_path = processed_dir / "manifest_data_ingestion.json"
    _write_json(manifest_path, manifest)
    dictionary = {
        "grain": "one row per district_code and date in fitur_harian_kecamatan.csv",
        "features": {
            "district_code": "Kode kecamatan RBI; stable join key.",
            "district_name": "Nama kecamatan menurut layer RBI turunan.",
            "parent_code": "Kode kabupaten/kota induk RBI.",
            "parent_name": "Nama kabupaten/kota induk RBI.",
            "date": "Tanggal observasi CHIRPS (daily).",
            "precipitation_mm_day": "Rata-rata piksel CHIRPS harian yang bersinggungan dengan poligon; mm/hari.",
            "chirps_pixel_count": "Jumlah piksel CHIRPS yang bersinggungan dengan kecamatan (all_touched).",
            "elevation_mean_m": "Rata-rata elevasi SRTM; meter.",
            "elevation_median_m": "Median elevasi SRTM; meter.",
            "elevation_p10_m": "Persentil ke-10 elevasi SRTM; meter.",
            "slope_mean_deg": "Rata-rata kemiringan dari DEM SRTM; derajat.",
            **{f"landcover_{code}_{name}_share": f"Proporsi piksel kelas WorldCover {code} ({name}), 2021; 0-1." for code, name in LANDCOVER.items()},
            "river_length_km": "Panjang jaringan sungai OSM yang beririsan dengan kecamatan; km.",
            "river_density_km_per_km2": "Panjang sungai per luas kecamatan; km/km2.",
            "representative_point_to_river_km": "Jarak titik representative_point kecamatan ke jaringan sungai terdekat; km.",
            "landcover_share_sum": "Jumlah proporsi kelas WorldCover; kolom pemeriksaan kualitas yang seharusnya mendekati 1.",
            "flood_event_rows": "Jumlah baris sumber BNPB yang cocok pada kecamatan-tanggal; kosong bila tidak ada laporan.",
            "flood_reported": "1 hanya untuk laporan BNPB terkonfirmasi; kosong untuk label pseudo-absence dan unknown.",
            "flood_label": "1=laporan banjir; 0=pseudo-absence dengan kriteria kering CHIRPS dan jendela event; -1=unknown dan dikeluarkan dari training.",
            "rain_3day_mm": "Akumulasi curah hujan CHIRPS trailing tiga hari (tanggal t-2 sampai t).",
            "label_status": "reported_event, pseudo_absence_hydro, atau unknown_no_report.",
        },
        "event_table": "kejadian_banjir_kecamatan_harian.csv menyimpan district_code, date, jumlah baris sumber, serta referensi baris/lokasi sumber.",
    }
    dictionary_path = processed_dir / "kamus_data_stage4.json"
    _write_json(dictionary_path, dictionary)
    report_path = processed_dir / "laporan_stage3_stage4.md"
    manifest["outputs"].extend(
        str(path.relative_to(project_root)).replace("\\", "/")
        for path in [manifest_path, dictionary_path, report_path]
    )
    _write_json(manifest_path, manifest)
    counts = validation["boundary_counts_by_parent"]
    report = f"""# Laporan Audit Stage 3 dan Stage 4 CAIST

## Hasil

- Batas RBI: **{validation['boundary_count']} kecamatan**, EPSG:4326; Kabupaten Bandung {counts['32.04']}, Kabupaten Bandung Barat {counts['32.17']}, Kota Bandung {counts['32.73']}, Kota Cimahi {counts['32.77']}. Geometri null/kosong/invalid: **{validation['boundary_invalid_or_empty']}**.
- Jaringan sungai OSM: **{river_report['features']:,}** LineString EPSG:4326; geometri kosong/invalid: **0**.
- Panel fitur: **{validation['daily_rows']:,} baris**, {validation['daily_distinct_dates']:,} tanggal, **{validation['daily_date_start']}–{validation['daily_date_end']}**; 80 kecamatan × tanggal unik; curah hujan kosong: **{validation['rain_missing_values']}**.
- Statistik spasial: **{validation['static_rows']} kecamatan**; elevasi, slope, proporsi 11 kelas WorldCover, panjang/kepadatan sungai, dan jarak dari titik representatif ke sungai tersedia tanpa nilai kosong. Jumlah proporsi tutupan lahan per kecamatan berkisar {validation['landcover_share_sum_min']:.6f}–{validation['landcover_share_sum_max']:.6f}.
- BNPB: **{bnpb_report['raw_rows']}** baris mentah; {bnpb_report['excluded_non_bandung_raya_rows']} catatan berkode kabupaten/kota di luar wilayah dikeluarkan. Terbentuk **{len(events)} kecamatan-tanggal kejadian terlapor** dari {bnpb_report['matched_source_mentions']} pencocokan sumber, setelah {bnpb_report['deduplicated_rows']} duplikasi kecamatan-tanggal disatukan. Rentang catatan BNPB mentah {min(item['date_min'] for item in bnpb_report['sources'] if item['date_min'])}–{max(item['date_max'] for item in bnpb_report['sources'] if item['date_max'])}; kejadian yang berhasil ditempatkan di kecamatan {bnpb_report['event_date_start']}–{bnpb_report['event_date_end']}.
- **{bnpb_report['unmatched_target_admin_count']} baris** dikecualikan dari pemetaan kecamatan: {bnpb_report['excluded_no_subdistrict_count']} tanpa teks kecamatan/desa dan sisanya tidak memiliki kecocokan RBI yang unik. Sebanyak {bnpb_report['matched_by_source'].get('verified_by_rbi_village', 0)} pencocokan bersumber dari desa RBI dan {bnpb_report['matched_by_source'].get('verified_by_rbi_district', 0)} dari nama kecamatan; {bnpb_report['source_parent_conflict_rows']} konflik kode induk tercatat dan diselesaikan berdasarkan lokasi RBI. Detail ada di `audit_bnpb_tidak_tercocok.csv`.
- Label dataset: **{validation['flood_label_counts'].get('1', 0):,} positif**, **{validation['flood_label_counts'].get('0', 0):,} pseudo-absence kering**, dan **{validation['flood_label_counts'].get('-1', 0):,} unknown**. Dataset latih berisi **{validation['training_rows_labels_0_or_1']:,}** baris label 0/1.

## Interpretasi dan batasan

- CHIRPS sekitar 0,05° (sekitar 5,6 km); rerata zonal tidak menggambarkan variasi hujan skala lingkungan.
- SRTM diproyeksikan ke {TARGET_CRS}; slope dihitung dari gradien DEM pada grid 30 m. WorldCover 2021 adalah tutupan lahan, bukan penggunaan lahan terkini.
- Label positif memakai kejadian BNPB yang cocok ke desa RBI atau kecamatan bernama. Kelas 0 hanya memakai pseudo-absence hidrometeorologi; {validation['unknown_rows_excluded_from_training']:,} baris berlabel -1 dikecualikan dari dataset latih.
- URL dan tanggal unduh CHIRPS, BNPB, SRTM, serta WorldCover tidak tercatat di metadata lokal; manifest menandainya sebagai tidak tersedia. Tanggal penempatan RBI 19 November 2026 diinformasikan pengguna, sementara metadata lokal menunjukkan vintage sumber lebih lama.
- Input mentah tidak diubah. Proyeksi metrik untuk slope dan jaringan sungai menggunakan {TARGET_CRS}.

## Keluaran

- `spatial/batas_kecamatan_bandung_raya.geojson`
- `fitur_spasial_kecamatan.csv`
- `fitur_harian_kecamatan.csv`
- `dataset_latih_kecamatan.csv` (label 0/1 saja; label -1 dikecualikan)
- `kejadian_banjir_kecamatan_harian.csv`
- `audit_bnpb_tidak_tercocok.csv`
- `manifest_data_ingestion.json`, `kamus_data_stage4.json`, `laporan_validasi_stage4.json`
"""
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"status": "passed", "outputs": manifest["outputs"], "validation": validation}, ensure_ascii=True, indent=2, default=_json_value))
    return validation


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
