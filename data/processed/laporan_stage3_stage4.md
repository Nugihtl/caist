# Laporan Audit Stage 3 dan Stage 4 CAIST

## Hasil

- Batas RBI: **80 kecamatan**, EPSG:4326; Kabupaten Bandung 31, Kabupaten Bandung Barat 16, Kota Bandung 30, Kota Cimahi 3. Geometri null/kosong/invalid: **0**.
- Jaringan sungai OSM: **1,676** LineString EPSG:4326; geometri kosong/invalid: **0**.
- Panel fitur: **345,760 baris**, 4,322 tanggal, **2015-01-01–2026-10-31**; 80 kecamatan × tanggal unik; curah hujan kosong: **0**.
- Statistik spasial: **80 kecamatan**; elevasi, slope, proporsi 11 kelas WorldCover, panjang/kepadatan sungai, dan jarak dari titik representatif ke sungai tersedia tanpa nilai kosong. Jumlah proporsi tutupan lahan per kecamatan berkisar 1.000000–1.000000.
- BNPB: **340** baris mentah; 69 catatan berkode kabupaten/kota di luar wilayah dikeluarkan. Terbentuk **429 kecamatan-tanggal kejadian terlapor** dari 445 pencocokan sumber, setelah 16 duplikasi kecamatan-tanggal disatukan. Rentang catatan BNPB mentah 2015-01-04–2026-10-30; kejadian yang berhasil ditempatkan di kecamatan 2019-01-13–2026-10-30.
- **65 baris** dikecualikan dari pemetaan kecamatan: 62 tanpa teks kecamatan/desa dan sisanya tidak memiliki kecocokan RBI yang unik. Sebanyak 414 pencocokan bersumber dari desa RBI dan 31 dari nama kecamatan; 35 konflik kode induk tercatat dan diselesaikan berdasarkan lokasi RBI. Detail ada di `audit_bnpb_tidak_tercocok.csv`.
- Label dataset: **429 positif**, **125,942 pseudo-absence kering**, dan **219,389 unknown**. Dataset latih berisi **126,371** baris label 0/1.

## Interpretasi dan batasan

- CHIRPS sekitar 0,05° (sekitar 5,6 km); rerata zonal tidak menggambarkan variasi hujan skala lingkungan.
- SRTM diproyeksikan ke EPSG:32748; slope dihitung dari gradien DEM pada grid 30 m. WorldCover 2021 adalah tutupan lahan, bukan penggunaan lahan terkini.
- Label positif memakai kejadian BNPB yang cocok ke desa RBI atau kecamatan bernama. Kelas 0 hanya memakai pseudo-absence hidrometeorologi; 219,389 baris berlabel -1 dikecualikan dari dataset latih.
- URL dan tanggal unduh CHIRPS, BNPB, SRTM, serta WorldCover tidak tercatat di metadata lokal; manifest menandainya sebagai tidak tersedia. Tanggal penempatan RBI 19 November 2026 diinformasikan pengguna, sementara metadata lokal menunjukkan vintage sumber lebih lama.
- Input mentah tidak diubah. Proyeksi metrik untuk slope dan jaringan sungai menggunakan EPSG:32748.

## Keluaran

- `spatial/batas_kecamatan_bandung_raya.geojson`
- `fitur_spasial_kecamatan.csv`
- `fitur_harian_kecamatan.csv`
- `dataset_latih_kecamatan.csv` (label 0/1 saja; label -1 dikecualikan)
- `kejadian_banjir_kecamatan_harian.csv`
- `audit_bnpb_tidak_tercocok.csv`
- `manifest_data_ingestion.json`, `kamus_data_stage4.json`, `laporan_validasi_stage4.json`
