# Laporan cleaning (Tahap 2)

Dibuat otomatis oleh `python -m src.clean` pada 2026-10-26 00:19. Jangan diedit manual.
Aturan & alasannya: `notebooks/01_eda.ipynb`, `docs/data_profile.md`. Ambang: `config/config.yaml` bagian `cleaning`.

## Ringkasan
- Rentang: **2023-07-03 s/d 2026-10-23**, 865 hari kerja, 6 provinsi Pulau Jawa.
- Baris kota × hari: **535,435** (62 kota/kab, 6 komoditas, 4 jenis pasar).
  Harga asli terisi 525,239 (98.10%).
- Kota dibuang karena duplikat: id [787] ("Kota Surakarta" pasar modern; dipakai id 36).
- **Hari libur diisi harga sebelumnya:** 72 tanggal terdeteksi (> 90% seri
  pasar tradisional tidak berubah) → `is_libur_isi`, dikosongkan di `harga_bersih`. Daftar: `data/interim/libur_terdeteksi.csv`.
- **Salah input** (aturan B/C): **27 titik** → `is_outlier_flag`, dikosongkan di `harga_bersih`.
- **Lonjakan tajam** (aturan A, penanda saja): 113 titik → `is_lonjakan_tajam`, nilai tetap dipakai.
- **Celah ≤ 5 hari kerja diisi** (forward-fill): 39,538 titik → `is_imputed`.
- **Kosong akhir** di `harga_bersih`: 2.48% (pasar tradisional 1.85%).
- **Data usang** (harga tetap ≥ 60 hari kerja): 0.87% titik → `is_usang`.

## Per jenis pasar
| jenis_pasar | kota | baris | kosong_asli | libur | salah_input | lonjakan | diisi | kosong_akhir | usang |
|---|---|---|---|---|---|---|---|---|---|
| Pasar Modern | 23 | 117640 | 4.66% | 8.32% | 0 | 9 | 10462 | 3.77% | 1.92% |
| Pasar Tradisional | 35 | 179920 | 1.29% | 8.32% | 4 | 101 | 12635 | 1.85% | 0.16% |
| Pedagang Besar | 23 | 117640 | 0.29% | 8.32% | 0 | 3 | 8142 | 1.59% | 0.92% |
| Produsen | 48 | 120235 | 1.71% | 8.32% | 23 | 0 | 8299 | 3.01% | 0.84% |

Kolom: `kosong_asli` = % harga asli kosong; `libur` = % baris pada hari libur; `salah_input`, `lonjakan`, `diisi` = jumlah titik;
`kosong_akhir` = % `harga_bersih` kosong setelah cleaning; `usang` = % titik dengan harga tetap ≥ 60 hari kerja.

## Salah input yang dikosongkan
| jenis_pasar | kualitas | kota | alasan_outlier | hari | mulai | selesai | harga_asli |
|---|---|---|---|---|---|---|---|
| Pasar Tradisional | Bawang Merah Ukuran Sedang | Kab. Wonogiri | rasio_ekstrem | 1 | 2026-05-20 | 2026-05-20 | Rp 143,750 |
| Pasar Tradisional | Cabai Rawit Merah | Kab. Banyumas | rasio_ekstrem | 1 | 2025-04-23 | 2025-04-23 | Rp 258,750 |
| Pasar Tradisional | Cabai Rawit Merah | Kab. Wonogiri | rasio_ekstrem | 1 | 2023-12-29 | 2023-12-29 | Rp 232,500 |
| Pasar Tradisional | Cabai Rawit Merah | Kota Sukabumi | rasio_ekstrem | 1 | 2025-12-15 | 2025-12-15 | Rp 264,250 |
| Produsen | Bawang Merah Ukuran Sedang | Kab. Garut | lintas_kota | 23 | 2025-03-25 | 2025-04-24 | Rp 3,000 |

## Seri dengan > 10% kosong setelah cleaning
Seri ini tetap disimpan, tetapi perlu dipertimbangkan sebelum dipakai di analisis.

| jenis_pasar | kualitas | kota | pct_kosong_akhir | celah_terpanjang_akhir |
|---|---|---|---|---|
| Pasar Modern | Cabai Rawit Merah | Kab. Banyuwangi | 89.83% | 777 |
| Produsen | Daging Ayam Ras Segar | Kota Blitar | 77.34% | 669 |
| Pasar Tradisional | Cabai Merah Keriting | Kab. Jember | 72.95% | 631 |
| Pasar Modern | Bawang Merah Ukuran Sedang | Kab. Banyuwangi | 65.09% | 382 |
| Pasar Modern | Bawang Putih Ukuran Sedang | Kab. Banyuwangi | 62.54% | 382 |
| Pasar Modern | Bawang Merah Ukuran Sedang | Kab. Cilacap | 12.83% | 69 |

## File keluaran
| File | Isi |
|---|---|
| `data/interim/harga_harian.parquet` | harga kota per hari kerja + penanda kualitas (535,435 baris) |
| `data/interim/harga_nasional.parquet` | rata-rata nasional per jenis pasar × komoditas × hari (20,760 baris) |
| `data/interim/kualitas_data.csv` | tabel kualitas per jenis pasar × komoditas × kota (619 seri); salinan publik di `reports/kualitas_data.csv` |
| `data/interim/libur_terdeteksi.csv` | 72 tanggal hari libur yang terdeteksi |
