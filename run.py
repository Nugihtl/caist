"""Titik masuk aplikasi CAIST."""

from __future__ import annotations

import argparse
import importlib
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow

DEPENDENCIES = [
    ("PySide6.QtWidgets", "PySide6.QtWidgets"),
    ("PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineWidgets"),
    ("pandas", "Pandas"),
    ("numpy", "NumPy"),
    ("sklearn", "Scikit-learn"),
    ("geopandas", "GeoPandas"),
    ("shapely", "Shapely"),
    ("pyogrio", "Pyogrio"),
    ("pyproj", "PyProj"),
    ("rasterio", "Rasterio"),
    ("requests", "Requests"),
    ("matplotlib", "Matplotlib"),
    ("sqlite3", "sqlite3"),
]


def check_dependencies() -> list[tuple[str, str, str]]:
    """Verifikasi impor setiap dependensi dan kembalikan (nama, modul, status)."""
    hasil: list[tuple[str, str, str]] = []
    for modul, nama in DEPENDENCIES:
        try:
            importlib.import_module(modul)
            status = "PASS"
        except Exception as exc:  # noqa: BLE001
            status = f"FAIL ({exc})"
        hasil.append((nama, modul, status))
    return hasil


def main() -> int:
    parser = argparse.ArgumentParser(prog="CAIST")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifikasi inisialisasi aplikasi tanpa menampilkan jendela.",
    )
    args = parser.parse_args()

    if args.check:
        print("=" * 60)
        print("CAIST — Verifikasi Inisialisasi Stage 1")
        print("Python:", sys.version)
        print("=" * 60)
        semua_lulus = True
        for nama, modul, status in check_dependencies():
            print(f"[{status}] {nama} ({modul})")
            if status != "PASS":
                semua_lulus = False
        print("=" * 60)
        print("Hasil:", "SEMUA PASS" if semua_lulus else "ADA YANG GAGAL")
        return 0 if semua_lulus else 1

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
