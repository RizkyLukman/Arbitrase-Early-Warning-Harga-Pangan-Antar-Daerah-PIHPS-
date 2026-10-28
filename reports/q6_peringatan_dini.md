# Q6 — Peringatan dini & uji pada data lama

Dibuat otomatis oleh `python -m src.analysis.early_warning` pada 2026-10-29 02:11.
Pasar tradisional, mingguan. Lonjakan = harga naik ≥ X% dalam 4 minggu (X = persentil 90%
dari data latih per komoditas). Peringatan benar = lonjakan dimulai 0–4 minggu setelah peringatan.
Diuji pada data tahun 2025, 2026; setiap tahun uji hanya memakai pengetahuan dari data sebelumnya.

## Temuan (bahasa dashboard)
**Peringatan dini menangkap 2 dari 10 lonjakan harga, rata-rata 5,8 minggu lebih awal — tetapi belum layak dipakai sebagai pemicu pembelian.**
Peringatan yang terbukti benar: 1,2 dari 10. Ini bahkan lebih rendah daripada memberi peringatan setiap minggu (1,6 dari 10), artinya aturan ini belum lebih baik daripada tebakan acak. Tebakan "sama seperti tahun lalu" justru lebih baik
(2,2 dari 10 benar, menangkap 4,2 dari 10).
Tindakan: jangan pakai aturan ini sebagai pemicu pembelian. Untuk sementara, pakai kalender pola tahun lalu dan pola Idulfitri (mis. bawang merah naik 4 minggu sebelum Lebaran) sebagai pengingat, dan harga di kota penentu arah hanya sebagai informasi tambahan.

Peringatan minggu terakhir (23 Oct 2026): tidak ada peringatan aktif.

## Hasil uji (2025–2026 digabung)
| Aturan | Benar (dari 10 peringatan) | Lonjakan tertangkap (dari 10) | Datang lebih awal (minggu) | Minggu dengan peringatan | Peringatan | Lonjakan |
|---|---|---|---|---|---|---|
| A atau B (aturan brief) | 1,2 | 2,4 | 5,8 | 13% | 2.379 | 667 |
| A: kota penentu arah | 1,4 | 2,3 | 5,8 | 10% | 1.853 | 667 |
| B: masa sebelum Idulfitri | 0,3 | 0,1 | 5,7 | 3% | 560 | 667 |
| pembanding: sama seperti tahun lalu | 2,2 | 4,2 | 5,8 | 18% | 3.435 | 667 |
| pembanding: selalu beri peringatan | 1,6 | 10,0 | 7,2 | 100% | 18.837 | 667 |

"Selalu beri peringatan" = frekuensi dasar: berapa persen minggu memang diikuti lonjakan dalam 4 minggu.

## Per tahun uji (aturan brief)
| Tahun uji | Benar (dari 10) | Tertangkap (dari 10) | Lebih awal (minggu) |
|---|---|---|---|
| 2025 | 0,7 | 1,7 | 6,1 |
| 2026 | 1,9 | 3,3 | 5,6 |

## Per komoditas (2025–2026)
| Komoditas | Aturan brief: benar | Aturan brief: tertangkap | Tahun lalu: benar | Selalu: benar |
|---|---|---|---|---|
| Cabai rawit merah | 0,3 | 0,6 | 1,6 | 1,4 |
| Cabai merah keriting | 1,6 | 1,1 | 2,7 | 1,5 |
| Bawang merah | 0,7 | 3,5 | 0,5 | 1,0 |
| Bawang putih | 1,8 | 8,1 | 1,9 | 1,4 |
| Daging ayam ras | 1,5 | 2,0 | 1,9 | 2,9 |
| Telur ayam ras | 0,1 | 0,3 | 4,5 | 1,5 |

## Parameter yang dipelajari dari data latih (tanpa melihat tahun uji)
| Tahun uji | Komoditas | Ambang lonjakan (4 minggu) | Kota penentu arah | Mulai naik sebelum Idulfitri |
|---|---|---|---|---|
| 2025 | Cabai rawit merah | 73% | Kota Surabaya, Kota Surakarta (Solo) | – |
| 2025 | Cabai merah keriting | 46% | – | – |
| 2025 | Bawang merah | 35% | Kab. Cilacap, Kab. Cirebon, Kab. Karanganyar, Kab. Wonogiri, Kota Bogor, Kota Cilegon, Kota Serang, Kota Surakarta (Solo), Kota Tangerang | minggu -1 |
| 2025 | Bawang putih | 8% | Kab. Cirebon, Kab. Jember, Kab. Sumenep, Kab. Wonogiri, Kota Cirebon, Kota Madiun, Kota Probolinggo, Kota Sukabumi, Kota Surabaya | – |
| 2025 | Daging ayam ras | 7% | – | minggu -6 |
| 2025 | Telur ayam ras | 10% | – | minggu -8 |
| 2026 | Cabai rawit merah | 83% | Kota Surabaya, Kota Surakarta (Solo) | – |
| 2026 | Cabai merah keriting | 47% | Kab. Cilacap, Kab. Klaten | – |
| 2026 | Bawang merah | 32% | Kab. Cilacap, Kab. Cirebon, Kab. Karanganyar, Kab. Sukoharjo, Kab. Sumenep, Kota Bekasi, Kota Bogor, Kota Cilegon, Kota Cirebon, Kota Jakarta Pusat, Kota Kediri, Kota Semarang, Kota Serang, Kota Sukabumi, Kota Surabaya, Kota Surakarta (Solo), Kota Tangerang, Kota Tegal | minggu -1 |
| 2026 | Bawang putih | 6% | Kab. Boyolali, Kab. Cilacap, Kab. Cirebon, Kab. Jember, Kab. Karanganyar, Kab. Klaten, Kab. Sukoharjo, Kab. Sumenep, Kab. Wonogiri, Kota Blitar, Kota Bogor, Kota Cirebon, Kota Jakarta Pusat, Kota Kediri, Kota Malang, Kota Probolinggo, Kota Semarang, Kota Sukabumi, Kota Surabaya, Kota Surakarta (Solo) | – |
| 2026 | Daging ayam ras | 8% | Kab. Cilacap, Kab. Cirebon, Kab. Tasikmalaya, Kota Cirebon, Kota Kediri, Kota Probolinggo, Kota Tasikmalaya | – |
| 2026 | Telur ayam ras | 9% | – | – |

## Batasan
- Hanya 2 tahun uji; tahun uji 2025 dilatih dengan 1 kali Idulfitri saja (2024).
- Lonjakan didefinisikan secara statistik (persentil 90), bukan dari pengalaman pengadaan nyata.
- Kota penentu arah hanya memberi ±1 minggu waktu tambahan; peringatan tidak memprediksi besarnya kenaikan.
- "Lebih awal" dihitung dari peringatan pertama (0–4 minggu sebelum lonjakan dimulai) sampai harga
  sudah naik X%; nilainya maksimal sekitar 8 minggu. Tebakan "selalu beri peringatan" pun mendapat
  7,2 minggu, jadi angka ini hanya bermakna jika dibaca bersama "peringatan yang terbukti benar".

## File
- Tabel: `reports/tables/q6_skor_ringkas.csv`, `q6_skor_per_komoditas.csv`, `q6_skor_per_tahun.csv`, `q6_parameter_latih.csv`,
  `q6_peringatan_uji.csv` (per kota × minggu di tahun uji: sinyal, awal & masa lonjakan),
  `q6_peringatan_terkini.csv` (8 minggu terakhir, kolom alasan berbahasa dashboard)
- Grafik: `reports/figures/q6_skor_peringatan.png`, `reports/figures/q6_timeline_contoh.png`
