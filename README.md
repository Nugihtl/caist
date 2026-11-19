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

## GIS Map Integration (Stage 3)

Dashboard menampilkan Leaflet dalam Qt WebEngine. Batas kecamatan berasal dari data lokal RBI Skala 1:25.000 BIG dalam `data/raw/boundaries/`; jaringan sungai berasal dari `data/raw/osm/jaringan_sungai_bandung_raya.geojson`. Data raw tidak diubah.

### Audit batas administrasi

- Dua Shapefile `RBI25K_ADMINISTRASI_AR.shp` di `kota_bandung/` dan `kota_cimahi/` berisi masing-masing 7 dan 6 poligon area administrasi. Field `WADMKC` kosong, sehingga keduanya berada pada level kabupaten/kota, bukan kecamatan. Shapefile dibaca dan diaudit, tetapi tidak dipakai untuk geometri kecamatan.
- GDB Kabupaten Bandung memiliki layer `ADMINISTRASI_AR_KECAMATAN` dengan 129 fitur; GDB Kabupaten Bandung Barat memiliki layer yang sama dengan 79 fitur. Layer tersebut sudah berisi poligon kecamatan/multipoligon dengan kode kecamatan `KDCPUM`, kode induk `KDPKAB`, nama kecamatan `WADMKC`, dan nama induk `WADMKK`.
- GDB pertama mencakup 31 Kabupaten Bandung, 15 Bandung Barat, 30 Kota Bandung, dan 3 Kota Cimahi. GDB kedua mencakup 13 Kabupaten Bandung, 16 Bandung Barat, 18 Kota Bandung, dan 3 Kota Cimahi. Pemilihan berdasarkan kode induk menghindari salinan tumpang tindih dari dua GDB; geometri tidak perlu dissolve.
- Tanggal unduh/penempatan lokal yang diinformasikan adalah 19 November 2026. Namun nama GDB berakhiran 20221231 dan metadata fitur terpilih bernilai TASWIL1000020221227_DATA_BATAS_DESAKELURAHAN; Shapefile kota memuat TASWIL2500020210531_DATA_BATAS_KABKOTA. Jadi tanggal 2026 adalah tanggal akuisisi, bukan tahun pemutakhiran sumber. Field metadata GDB juga menyebut seri desa/kelurahan, sedangkan layer yang dipakai bernama ADMINISTRASI_AR_KECAMATAN dan memiliki kode/nama kecamatan; catatan asal-usul ini dipertahankan untuk ditelusuri bila vintage data menjadi syarat.
- Layer hasil berisi tepat 80 kode kecamatan unik: Kabupaten Bandung 31, Kabupaten Bandung Barat 16, Kota Bandung 30, dan Kota Cimahi 3. Tidak ada geometri null, kosong, atau invalid. Kode dan nama wilayah induk ikut disimpan untuk audit dan popup.
- CRS GDB terbaca sebagai compound WGS 84 + EGM2008 (EPSG:9518). Hasil ditransformasi ke EPSG:4326 dan koordinat Z dibuang untuk GeoJSON/Leaflet. Extent hasil: `[107.181935683, -7.309770642, 107.938432276, -6.688514904]`.
- Hasil olahan: `data/processed/spatial/batas_kecamatan_bandung_raya.geojson`. Jalankan `python -m src.gis.boundary_processing` untuk membangun ulang dari data raw; validasi jumlah wilayah dan geometri dijalankan sebelum output ditulis.

Layer sungai terbaca sebagai 1.676 LineString di EPSG:4326, dengan extent `[107.2469663, -7.3152211, 107.8718023, -6.81259]`. Nilai `waterway`: 1.264 stream, 256 river, 156 canal; 1.276 fitur tidak memiliki nama. Tidak ditemukan geometri null/kosong/invalid atau ID duplikat pada audit sebelumnya.

Peta menyediakan basemap OpenStreetMap, atribusi, zoom/pan, fit bounds, layer control, popup atribut sumber, legenda, dan status data. Leaflet.js 1.9.4 dan asetnya disimpan lokal di `map/vendor/` beserta lisensi. Basemap OpenStreetMap tetap online dan memerlukan internet; layer batas dan sungai tetap tampil dari data lokal saat basemap tidak tersedia. Belum ada prediksi atau choropleth risiko pada tahap ini. Tes memakai fixture sintetis berlabel test dan tidak meminta tile server.

## Data Ingestion & Spatial Preprocessing (Stage 4)

Jalankan pipeline dari root proyek setelah memasang `requirements.txt`:

```bash
python -m src.data.spatial_preprocessing
```

Pipeline membangun ulang batas 80 kecamatan dari GDB RBI lokal, memvalidasi layer sungai, mengekstrak elevasi/slope SRTM, proporsi kelas tutupan lahan WorldCover, curah hujan harian CHIRPS, serta statistik sungai OSM. Hasil tabel, manifest, kamus data, audit BNPB, dan laporan validasi ditulis di `data/processed/`; file dalam `data/raw/` hanya dibaca.

Panel `fitur_harian_kecamatan.csv` memiliki satu baris per `district_code` dan tanggal CHIRPS, total 345.760 baris untuk 80 kecamatan pada 2015-01-01 s.d. 2026-10-31. Dari 340 baris BNPB mentah, 69 catatan di luar Bandung Raya dikeluarkan; 62 catatan tanpa teks lokasi diberi `excluded_no_subdistrict` dan dikecualikan dari training. Lokasi yang cocok dengan desa RBI ditandai `verified_by_rbi_village`; konflik kode induk diselesaikan memakai kecocokan lokasi RBI. Rinciannya ada di `audit_bnpb_tidak_tercocok.csv` dan `laporan_stage3_stage4.md`.

Label harian: `1` untuk kejadian BNPB terverifikasi; `0` hanya untuk pseudo-absence ketika tidak ada kejadian dalam jendela inklusif +/-3 hari, hujan harian CHIRPS <5 mm dan akumulasi trailing tiga hari <10 mm; `-1` untuk hari tanpa laporan yang tidak memenuhi kondisi kering. Kejadian tingkat kabupaten/kota yang lokasinya tidak dapat ditempatkan juga memblokir pseudo-absence pada kecamatan induk selama jendela +/-3 hari. Hasil saat ini: 429 positif, 125.942 pseudo-absence, 219.389 unknown; dataset latih biner berisi 126.371 baris (`0` dan `1`), unknown dikecualikan. CHIRPS beresolusi sekitar 5,6 km, sehingga statistiknya tidak mewakili variasi hujan skala kecamatan kecil.

## SQLite Data Layer (Stage 5)

Inisialisasi schema dan impor idempotent keluaran Stage 4:

```bash
python -m src.database
```

SQLite menggunakan `data/caist.sqlite` (diabaikan Git). Schema version 2 dicatat di `schema_migrations`; akses database melalui transaction manager dan repository di `src/database/`. Tabel fitur memisahkan fitur statis per kecamatan dan fitur harian per kecamatan-tanggal; `flood_label` menyimpan `1`, `0`, atau `-1` beserta status label. Kejadian yang tidak dapat ditempatkan tidak dimasukkan sebagai event kecamatan. Import ulang untuk `data_version` yang sama bersifat idempotent. Pada database lokal yang diaudit: integritas SQLite `ok`, 0 pelanggaran foreign key, 80 kecamatan, 345.760 fitur harian, dan 429 kecamatan-hari kejadian.

UI Stage 5 membaca snapshot database dalam mode read-only. Dashboard menampilkan jumlah wilayah dan ringkasan BNPB; Data Wilayah menunjukkan jumlah/cakupan enam dataset utama; dropdown Prediksi menggunakan 80 kecamatan. File SQLite dan dataset besar tetap perlu disediakan terpisah pada checkout baru karena data mentah/olah tidak didorong ke Git.

## Lisensi

Tidak ada lisensi yang ditetapkan.
