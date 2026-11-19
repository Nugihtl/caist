# CAIST

Aplikasi desktop untuk memprediksi probabilitas kejadian banjir di seluruh wilayah Bandung Raya (Kota Bandung, Kabupaten Bandung, Kabupaten Bandung Barat, dan Kota Cimahi).

## Fungsi utama

- **Real-time Monitoring:** informasi curah hujan, tinggi muka air, dan debit sungai dari stasiun pemantauan.
- **Flood Prediction:** prediksi probabilitas kejadian banjir per kecamatan dengan penilaian risiko pada peta interaktif.

## Tech stack

| Komponen | Teknologi |
|---|---|
| Bahasa | Python |
| Desktop GUI | PySide6 |
| Embedded browser | Qt WebEngine |
| Peta interaktif | Leaflet.js |
| Data processing | Pandas, NumPy |
| Machine learning | Scikit-learn |
| Geospatial | GeoPandas, Shapely, Pyogrio, PyProj, Rasterio |
| HTTP | Requests |
| Visualization | Matplotlib |
| Database | SQLite |
| Testing | Pytest |

## Struktur proyek

```
caist/
├── .gitignore
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── run.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── app/
│   ├── __init__.py
│   ├── pages/
│   │   └── __init__.py
│   └── widgets/
│       └── __init__.py
├── map/
│   ├── index.html
│   ├── css/
│   └── js/
└── src/
    ├── __init__.py
    ├── database/
    │   └── __init__.py
    ├── data/
    │   └── __init__.py
    └── gis/
        └── __init__.py
```

## Instalasi

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Menjalankan aplikasi

```bash
python run.py
```

## Pengujian

```bash
pytest
```

## Sumber data yang direncanakan

- CHIRPS: curah hujan.
- BNPB: riwayat kejadian banjir.
- Batas administrasi: batas kecamatan.
- NASA SRTM: elevasi dan kemiringan.
- ESA WorldCover: tutupan lahan.
- OpenStreetMap: jaringan sungai.
- BBWS Citarum FFWS: data monitoring (mekanisme akses otomatis belum dipastikan).

## Lisensi

Tidak ada lisensi yang ditetapkan.