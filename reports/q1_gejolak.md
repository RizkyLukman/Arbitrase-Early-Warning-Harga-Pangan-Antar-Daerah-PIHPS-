# Q1 — Gejolak harga

Dibuat otomatis oleh `python -m src.analysis.volatility` pada 2026-10-26 01:21.
Data: pasar tradisional, harga mingguan (median hari nyata), 35 kota/kab di Pulau Jawa,
Juli 2023 – Oktober 2026. Ukuran utama: simpangan baku perubahan harga mingguan (log-return).

## Temuan (bahasa dashboard)
**Harga cabai rawit merah paling bergejolak, terutama di Kota Blitar, Kab. Sumenep, Kab. Cilacap.**
Harganya naik-turun rata-rata 13% per minggu (median antar kota), dibanding
2% untuk bawang putih.
Tindakan: pantau cabai setiap minggu dan siapkan stok penyangga; komoditas yang tenang cukup dipantau bulanan.

## Peringkat komoditas
| # | Komoditas | Gejolak mingguan (median kota) | Rentang antar kota | Rata-rata perubahan/minggu | 3 kota paling bergejolak |
|---|---|---|---|---|---|
| 1 | Cabai rawit merah | 16,4% | 11,8%–22,4% | 12,9% | Kota Blitar, Kab. Sumenep, Kab. Cilacap |
| 2 | Cabai merah keriting | 14,2% | 10,2%–18,3% | 10,3% | Kota Blitar, Kota Surakarta (Solo), Kab. Cilacap |
| 3 | Bawang merah | 7,8% | 5,6%–9,5% | 5,3% | Kota Blitar, Kota Surakarta (Solo), Kota Cilegon |
| 4 | Daging ayam ras | 3,5% | 2,2%–5,6% | 2,6% | Kab. Jember, Kab. Cilacap, Kab. Banyuwangi |
| 5 | Telur ayam ras | 3,2% | 2,4%–4,1% | 2,1% | Kota Blitar, Kota Probolinggo, Kota Cilegon |
| 6 | Bawang putih | 3,1% | 1,5%–4,6% | 1,7% | Kab. Banyuwangi, Kota Blitar, Kota Probolinggo |

**Catatan:** Kota Blitar (5 dari 6 komoditas), Kab. Cilacap (3 dari 6 komoditas) berulang kali masuk 3 kota paling bergejolak. Bisa mencerminkan kondisi pasar setempat, tetapi juga sampel PIHPS yang kecil (2 pasar × 2 pedagang per kota) sehingga harga lebih berisik. Perlakukan sebagai sinyal untuk dicek, bukan kesimpulan pasti.

## Konsistensi antar tahun (median gejolak mingguan antar kota)
| Komoditas | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| Cabai rawit merah | 12,1% | 17,4% | 18,7% | 14,9% |
| Cabai merah keriting | 13,9% | 15,9% | 14,7% | 12,3% |
| Bawang merah | 8,5% | 8,2% | 8,6% | 6,0% |
| Bawang putih | 3,2% | 2,0% | 2,4% | 3,8% |
| Daging ayam ras | 3,1% | 3,4% | 3,2% | 4,3% |
| Telur ayam ras | 2,8% | 3,3% | 3,1% | 3,3% |

2023 = Juli–Desember; 2026 = Januari–Oktober.

## Pasar tradisional vs pasar modern (pembanding, dengan catatan)
| Komoditas | Gejolak tradisional | Gejolak modern | Minggu tanpa perubahan (tradisional) | Minggu tanpa perubahan (modern) |
|---|---|---|---|---|
| Cabai rawit merah | 16,4% | 11,0% | 5% | 40% |
| Cabai merah keriting | 14,2% | 9,0% | 7% | 50% |
| Bawang merah | 7,8% | 6,4% | 21% | 48% |
| Bawang putih | 3,1% | 4,1% | 44% | 62% |
| Daging ayam ras | 3,5% | 3,4% | 19% | 62% |
| Telur ayam ras | 3,2% | 3,0% | 20% | 22% |

Catatan: pasar modern hanya diperbarui Selasa–Rabu dan banyak minggu tanpa perubahan sama sekali, sehingga gejolaknya
tampak lebih rendah. Perbedaan ini sebagian besar mencerminkan cara pencatatan, bukan harga yang benar-benar lebih stabil.

## File
- Tabel: `reports/tables/q1_gejolak_per_kota.csv`, `q1_gejolak_per_komoditas.csv`, `q1_gejolak_per_tahun.csv`,
  `q1_tradisional_vs_modern.csv`
- Grafik: `reports/figures/q1_gejolak_per_komoditas.png`, `reports/figures/q1_heatmap_kota_komoditas.png`
