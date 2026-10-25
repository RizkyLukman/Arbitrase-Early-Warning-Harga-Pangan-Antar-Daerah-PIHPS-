# Q4 — Pola harga sekitar Idulfitri

Dibuat otomatis oleh `python -m src.analysis.seasonality` pada 2026-10-26 01:34.
Pasar tradisional, harga mingguan, Idulfitri 2024 (10 Apr), 2025 (31 Mar), 2026 (21 Mar) menurut SKB.
Harga normal = rata-rata minggu -12 s/d -9. "Mulai naik" = setiap minggu sejak itu sampai minggu −1
harga ≥ 5% di atas harga normal (median antar kota) pada ≥ 2 dari 3 tahun.

## Temuan (bahasa dashboard)
**Harga bawang merah mulai naik 4 minggu sebelum Idulfitri, jadi stok perlu diamankan sebelum itu.** Seminggu sebelum Lebaran harganya rata-rata +26% dibanding harga normal (minggu −12 s/d −9). Komoditas lain yang naik konsisten: cabai rawit merah (≥ 8 minggu sebelum (sejak awal jendela), naik di 2 dari 3 tahun), daging ayam ras (6 minggu sebelum, naik di 2 dari 3 tahun).
Tidak naik konsisten: cabai merah keriting, bawang putih, telur ayam ras.
Pola ini masih perkiraan kasar karena baru ada 3 kali Idulfitri dalam data.

## Per komoditas
| Komoditas | Mulai naik | Tahun dengan kenaikan ≥ ambang di minggu −1 | Seminggu sebelum Lebaran (rata-rata; per tahun) | Puncak (rata-rata; rentang antar tahun) | 4 minggu setelah Lebaran |
|---|---|---|---|---|---|
| Cabai rawit merah | ≥ 8 minggu sebelum (sejak awal jendela) | 2 dari 3 | +39% (2024: -13%; 2025: +18%; 2026: +112%) | minggu -5: +56% (+14% s/d +111%) | -18% |
| Cabai merah keriting | tidak konsisten | 1 dari 3 | -2% (2024: -36%; 2025: -5%; 2026: +33%) | minggu 0: +12% (+12% s/d +12%) | -7% |
| Bawang merah | 4 minggu sebelum | 3 dari 3 | +26% (2024: +25%; 2025: +39%; 2026: +13%) | minggu 2: +53% (+8% s/d +102%) | +31% |
| Bawang putih | tidak konsisten | 1 dari 3 | +2% (2024: +4%; 2025: +5%; 2026: -2%) | minggu 1: +6% (-3% s/d +14%) | +3% |
| Daging ayam ras | 6 minggu sebelum | 2 dari 3 | +11% (2024: +16%; 2025: +0%; 2026: +16%) | minggu 0: +20% (+20% s/d +20%) | +0% |
| Telur ayam ras | tidak konsisten | 1 dari 3 | +3% (2024: +5%; 2025: -0%; 2026: +5%) | minggu -4: +11% (+6% s/d +19%) | +3% |

## Batasan
- Hanya 3 kali Idulfitri. Minggu Lebaran (minggu 0) tahun 2024 & 2025 tidak punya pencatatan sama sekali.
- Idulfitri bergeser ±11 hari tiap tahun, tetapi 3 tahun belum cukup untuk memisahkan efek Lebaran dari musim panen/hujan.
- Harga normal minggu −12 s/d −9 bisa terpengaruh peristiwa lain (mis. Imlek, awal tahun).

## File
- Tabel: `reports/tables/q4_pola_idul_fitri.csv` (komoditas × tahun × minggu), `q4_ringkasan.csv`, `q4_per_kota.csv`
- Grafik: `reports/figures/q4_pola_idul_fitri.png`
