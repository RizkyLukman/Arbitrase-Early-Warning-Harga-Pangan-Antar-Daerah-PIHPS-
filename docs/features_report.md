# Laporan feature engineering (Tahap 3)

Dibuat otomatis oleh `python -m src.features` pada 2026-10-26 00:56. Jangan diedit manual.
Parameter: `config/config.yaml` bagian `features`. Tanggal hari besar: `data/reference/hari_besar.csv`.

## Ringkasan
- **173 minggu** (W-FRI) dari 2023-07-07 s/d 2026-10-23;
  619 seri kota × komoditas × jenis pasar → **107,087 baris** `harga_mingguan`.
- 8 seri ditandai
  `is_seri_dikecualikan` (bolong / kasus batas, lihat config); tetap disimpan.
- Harga mingguan hanya dari pengamatan nyata. Cara: 1=median, 2=terakhir, 3=terakhir, 4=terakhir
  (1 tradisional, 2 modern, 3 pedagang besar, 4 produsen).
- Fitur: log_return, pct_wow, pct_yoy (52 minggu), pct_4w,
  rata-rata bergerak & gejolak [4, 12] minggu,
  zscore level harga vs 52 minggu sebelumnya (min 26),
  zscore_return kenaikan mingguan vs 52 minggu sebelumnya
  (min 26), selisih vs nasional, minggu_ke_idul_fitri [-12, 4].
- Pasar tradisional, minggu dengan `zscore_return` > 2 (calon peringatan Q6):
  3.1% dari seluruh seri-minggu.

## Per jenis pasar (seri yang dipakai)
| jenis_pasar | seri | metode | minggu_ada_harga | minggu_tipis | rata_hari_nyata |
|---|---|---|---|---|---|
| Pasar Modern | 130 | terakhir | 98.7% | 1.3% | 4.44 |
| Pasar Tradisional | 207 | median | 98.8% | 2.3% | 4.57 |
| Pedagang Besar | 136 | terakhir | 98.8% | 1.2% | 4.57 |
| Produsen | 138 | terakhir | 98.1% | 1.9% | 4.53 |

## Gejolak mingguan pasar tradisional (pratinjau Q1)
Simpangan baku perubahan harga mingguan (log-return), semua kota digabung. Angka awal; analisis lengkap di Tahap 4.

| kualitas | std log-return mingguan (%) |
|---|---|
| Cabai Rawit Merah | 16.68 |
| Cabai Merah Keriting | 14.4 |
| Bawang Merah Ukuran Sedang | 7.85 |
| Daging Ayam Ras Segar | 3.7 |
| Telur Ayam Ras Segar | 3.23 |
| Bawang Putih Ukuran Sedang | 3.13 |

## Jendela Idulfitri (minggu −12 s/d +4)
| tahun_idul_fitri | minggu_pertama | minggu_terakhir | jumlah |
|---|---|---|---|
| 2024 | 2024-01-19 | 2024-05-10 | 17 |
| 2025 | 2025-01-10 | 2025-05-02 | 17 |
| 2026 | 2026-01-02 | 2026-04-24 | 17 |

Minggu 0 = minggu (Sabtu–Jumat) yang memuat tanggal Idulfitri menurut SKB.

## File keluaran
| File | Baris |
|---|---|
| `data/interim/harga_mingguan.parquet` | 107,087 |
| `data/interim/nasional_mingguan.parquet` | 4,152 |
| `data/interim/kalender_mingguan.parquet` | 173 |
