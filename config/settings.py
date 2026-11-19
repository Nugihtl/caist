"""Konfigurasi aplikasi CAIST."""

from __future__ import annotations

from pathlib import Path

# Identitas aplikasi
APP_NAME = "CAIST"
APP_VERSION = "0.1.0"
APP_ORG = "CAIST"
APP_DOMAIN = "caist.local"

# Jendela utama
WINDOW_TITLE = "CAIST — Prediksi Probabilitas Banjir Bandung Raya"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Path direktori
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
APP_DIR = ROOT_DIR / "app"
MAP_DIR = ROOT_DIR / "map"
SRC_DIR = ROOT_DIR / "src"
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

# Berkas peta dan database
MAP_FILE = MAP_DIR / "index.html"
DATABASE_PATH = DATA_DIR / "caist.sqlite"

# Wilayah Bandung Raya
BANDUNG_RAYA = {
    "nama": "Bandung Raya",
    "kecamatan": [
        "Kota Bandung",
        "Kabupaten Bandung",
        "Kabupaten Bandung Barat",
        "Kota Cimahi",
    ],
    "koordinat_pusat": [-6.9175, 107.6191],
    "zoom_awal": 11,
}

# Database
DB_VERSION = 1

# Sumber data (status integrasi)
DATA_SOURCES = {
    "CHIRPS": {"tipe": "curah_hujan", "tersedia": True},
    "BNPB": {"tipe": "riwayat_banjir", "tersedia": True},
    "BATAS_ADMINISTRASI": {"tipe": "batas_kecamatan", "tersedia": True},
    "NASA_SRTM": {"tipe": "elevasi_kemiringan", "tersedia": True},
    "ESA_WORLDCOVER": {"tipe": "tutupan_lahan", "tersedia": True},
    "OPENSTREETMAP": {"tipe": "jaringan_sungai", "tersedia": True},
    "BBWS_CITARUM_FFWS": {"tipe": "monitoring_realtime", "tersedia": False},
}
