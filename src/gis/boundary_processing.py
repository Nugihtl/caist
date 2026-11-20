"""Build the Bandung Raya kecamatan layer from official RBI KUGI geodatabases."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import force_2d

EXPECTED_COUNTS = {"32.04": 31, "32.17": 16, "32.73": 30, "32.77": 3}
PARENT_NAMES = {
    "32.04": "Bandung",
    "32.17": "Bandung Barat",
    "32.73": "Kota Bandung",
    "32.77": "Kota Cimahi",
}
SOURCE_LAYER = "ADMINISTRASI_AR_KECAMATAN"
OUTPUT_FIELDS = [
    "district_code",
    "district_name",
    "parent_code",
    "parent_name",
    "province_name",
    "source_name",
    "source_metadata",
    "geometry",
]


def build_bandung_raya_layer(
    kab_bandung: gpd.GeoDataFrame,
    kab_bandung_barat: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Select the complete preferred kecamatan set and normalize it for Leaflet."""
    required = {"KDCPUM", "KDPKAB", "WADMKC", "WADMKK", "WADMPR", "NAMOBJ"}
    for label, frame in (
        ("Kabupaten Bandung GDB", kab_bandung),
        ("Kabupaten Bandung Barat GDB", kab_bandung_barat),
    ):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} missing required fields: {sorted(missing)}")
        if frame.crs is None:
            raise ValueError(f"{label} has no CRS.")

    bandung_codes = set(EXPECTED_COUNTS) - {"32.17"}
    selected = pd.concat(
        [
            kab_bandung.loc[
                kab_bandung["KDPKAB"].astype(str).isin(bandung_codes)
            ].copy(),
            kab_bandung_barat.loc[
                kab_bandung_barat["KDPKAB"].astype(str).eq("32.17")
            ].copy(),
        ],
        ignore_index=True,
    )
    selected = gpd.GeoDataFrame(selected, geometry="geometry", crs=kab_bandung.crs)

    actual = selected.groupby("KDPKAB")["KDCPUM"].nunique().to_dict()
    normalized_actual = {str(code): count for code, count in actual.items()}
    if len(selected) != 80 or normalized_actual != EXPECTED_COUNTS:
        raise ValueError(
            "Target kecamatan tidak lengkap atau duplikat: "
            f"rows={len(selected)}, counts={normalized_actual}, "
            f"expected={EXPECTED_COUNTS}"
        )
    if selected["KDCPUM"].isna().any() or selected["KDCPUM"].duplicated().any():
        raise ValueError("Kode kecamatan kosong atau duplikat.")
    if selected["WADMKC"].isna().any() or selected["WADMKK"].isna().any():
        raise ValueError("Nama kecamatan atau kabupaten/kota induk kosong.")

    parent_names = selected.groupby("KDPKAB")["WADMKK"].first().astype(str).to_dict()
    if {str(code): name for code, name in parent_names.items()} != PARENT_NAMES:
        raise ValueError(f"Nama wilayah induk tidak sesuai kode: {parent_names}")

    allowed = {"Polygon", "MultiPolygon"}
    if not selected.geom_type.isin(allowed).all():
        raise ValueError("Layer kecamatan berisi geometri non-poligon.")
    if (
        selected.geometry.isna().any()
        or selected.geometry.is_empty.any()
        or (~selected.geometry.is_valid).any()
    ):
        raise ValueError("Geometri kecamatan kosong atau invalid.")
    if selected.geometry.duplicated().any():
        raise ValueError("Geometri kecamatan duplikat.")

    selected = selected.to_crs("EPSG:4326")
    selected.geometry = selected.geometry.map(force_2d)
    selected = selected.rename(
        columns={
            "KDCPUM": "district_code",
            "KDPKAB": "parent_code",
            "WADMKC": "district_name",
            "WADMKK": "parent_name",
            "WADMPR": "province_name",
            "NAMOBJ": "source_name",
            "METADATA": "source_metadata",
        }
    )
    selected["parent_code"] = selected["parent_code"].astype(str)
    return selected[OUTPUT_FIELDS]


def process_boundary_sources(
    boundaries_dir: Path, output_path: Path
) -> gpd.GeoDataFrame:
    """Audit RBI Shapefiles, read the two GDB district layers, and write GeoJSON."""
    boundaries_dir = Path(boundaries_dir)
    bandung_gdbs = list((boundaries_dir / "kab_bandung").glob("*.gdb"))
    bandung_barat_gdbs = list((boundaries_dir / "kab_bandung_barat").glob("*.gdb"))
    if len(bandung_gdbs) != 1 or len(bandung_barat_gdbs) != 1:
        raise FileNotFoundError(
            "Expected one GDB in kab_bandung and one in kab_bandung_barat."
        )

    for folder in ("kota_bandung", "kota_cimahi"):
        shapefiles = list((boundaries_dir / folder).glob("RBI25K_ADMINISTRASI_AR.shp"))
        if len(shapefiles) != 1:
            raise FileNotFoundError(f"Expected RBI25K_ADMINISTRASI_AR.shp in {folder}.")
        admin = gpd.read_file(shapefiles[0])
        if "WADMKC" not in admin or admin["WADMKC"].notna().any():
            raise ValueError(f"{shapefiles[0]} is not a kabupaten/kota-level layer.")
        print(
            f"Audit {shapefiles[0]}: {len(admin)} area features; "
            "WADMKC kosong, jadi bukan layer kecamatan."
        )

    bandung = gpd.read_file(bandung_gdbs[0], layer=SOURCE_LAYER)
    bandung_barat = gpd.read_file(bandung_barat_gdbs[0], layer=SOURCE_LAYER)
    output = build_bandung_raya_layer(bandung, bandung_barat)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_file(output_path, driver="GeoJSON")
    print(
        f"Wrote {len(output)} kecamatan to {output_path}; "
        f"EPSG:4326; counts={EXPECTED_COUNTS}; "
        f"bounds={output.total_bounds.tolist()}"
    )
    return output


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    process_boundary_sources(
        project_root / "data" / "raw" / "boundaries",
        project_root
        / "data"
        / "processed"
        / "spatial"
        / "batas_kecamatan_bandung_raya.geojson",
    )


if __name__ == "__main__":
    main()
