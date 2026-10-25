# Q2 — Rute pindah stok

Dibuat otomatis oleh `python -m src.analysis.spread` pada 2026-10-26 01:21.
Harga sumber = **pedagang besar** di kota sumber (harga beli distributor); harga tujuan = **pasar tradisional** di kota tujuan
(analisis utama, sesuai brief); mingguan, Juli 2023 – Oktober 2026. Ongkos angkut = **perkiraan, bukan data**
(`config/biaya_logistik.yaml`). Rute **layak** = pada ongkos ×1,5: untung pada ≥ 60% minggu
**dan** median untung > 0.

## Temuan (bahasa dashboard)
**23 rute masih untung setelah ongkos angkut; yang terbaik cabai rawit merah Kota Kediri → Kota Bandung.**
(Dari 32 rute yang diuji, dengan ongkos angkut ×1,5 perkiraan.) Di rute terbaik, harga di Kota Bandung rata-rata
Rp 26.450/kg lebih mahal daripada harga pedagang besar di Kota Kediri; setelah ongkos angkut
masih tersisa sekitar Rp 21.048/kg. Minggu untung: 10 dari 10.
Tindakan: prioritaskan rute yang layak; untuk rute lain, pindahkan stok hanya saat selisih minggu itu jauh di atas ongkos.

**Uji ketahanan:** jika stok dijual ke pedagang besar di kota tujuan (bukan dengan harga eceran), rute yang layak tinggal
**9 dari 32**. 9 rute layak di kedua cara hitung; inilah rekomendasi yang paling aman.

## Per komoditas (ongkos ×1,5)
| Komoditas | Rute layak (jual harga eceran) | Rute layak (jual ke pedagang besar) | Untung median terbaik/kg |
|---|---|---|---|
| Bawang merah | 8 dari 8 | 5 dari 8 | Rp 12.791 |
| Cabai rawit merah | 8 dari 12 | 4 dari 12 | Rp 21.048 |
| Telur ayam ras | 4 dari 4 | 0 dari 4 | Rp 1.486 |
| Cabai merah keriting | 2 dari 4 | 0 dari 4 | Rp 17.099 |
| Daging ayam ras | 1 dari 4 | 0 dari 4 | Rp 2.582 |

## Uji sensitivitas ongkos angkut (jual harga eceran)
| Pengali ongkos | Rute dengan median untung > 0 | Rute untung ≥ 60% minggu |
|---|---|---|
| ×0,5 | 30 | 29 |
| ×1 | 28 | 28 |
| ×1,5 | 27 | 23 |
| ×2 | 22 | 22 |

## Semua rute (ongkos ×1,5, diurutkan dari untung terbesar)
| Komoditas | Rute | Jarak (km) | Selisih harga | Ongkos ×1,5 | Untung/kg | Minggu untung | Bertahan | 10 minggu terakhir | Status | Untung/kg jika jual ke pedagang besar |
|---|---|---|---|---|---|---|---|---|---|---|
| Cabai rawit merah | Kota Kediri → Kota Bandung | 606 | Rp 26.450 | Rp 5.414 | Rp 21.048 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 3.461 (✅) |
| Cabai rawit merah | Kab. Jember → Kota Bandung | 866 | Rp 27.200 | Rp 6.435 | Rp 20.853 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 2.428 (✅) |
| Cabai rawit merah | Kota Kediri → Kota Jakarta Pusat | 688 | Rp 26.000 | Rp 5.739 | Rp 20.174 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 6.949 (✅) |
| Cabai rawit merah | Kab. Jember → Kota Jakarta Pusat | 948 | Rp 26.150 | Rp 6.760 | Rp 19.378 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 6.653 (✅) |
| Cabai merah keriting | Kota Tasikmalaya → Kota Bandung | 108 | Rp 20.500 | Rp 3.538 | Rp 17.099 | 10 dari 10 | hampir selalu | 9/10 | ✅ layak | Rp -4.401 (—) |
| Cabai rawit merah | Kab. Banyuwangi → Kota Bandung | 933 | Rp 22.750 | Rp 6.889 | Rp 15.411 | 9 dari 10 | 14 minggu | 10/10 | ✅ layak | Rp -2.314 (—) |
| Cabai rawit merah | Kab. Banyuwangi → Kota Jakarta Pusat | 1.016 | Rp 22.575 | Rp 7.213 | Rp 14.887 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 1.549 (—) |
| Bawang merah | Kota Tegal → Kota Jakarta Pusat | 286 | Rp 15.000 | Rp 2.324 | Rp 12.791 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 2.676 (✅) |
| Bawang merah | Kota Probolinggo → Kota Jakarta Pusat | 849 | Rp 16.000 | Rp 3.706 | Rp 12.444 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 979 (—) |
| Bawang merah | Kota Tegal → Kota Bandung | 203 | Rp 13.750 | Rp 2.105 | Rp 11.665 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 2.670 (✅) |
| Cabai merah keriting | Kota Tasikmalaya → Kota Jakarta Pusat | 262 | Rp 15.150 | Rp 4.140 | Rp 10.760 | 9 dari 10 | 20 minggu | 3/10 | ✅ layak | Rp -1.628 (—) |
| Bawang merah | Kota Probolinggo → Kota Bandung | 766 | Rp 13.500 | Rp 3.490 | Rp 10.061 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp 1.420 (✅) |
| Bawang merah | Kota Probolinggo → Kota Surabaya | 102 | Rp 6.750 | Rp 1.752 | Rp 5.245 | 9 dari 10 | 23 minggu | 10/10 | ✅ layak | Rp 2.973 (✅) |
| Bawang merah | Kota Probolinggo → Kota Semarang | 414 | Rp 7.750 | Rp 2.569 | Rp 5.221 | 9 dari 10 | 25 minggu | 10/10 | ✅ layak | Rp -1.699 (—) |
| Bawang merah | Kota Tegal → Kota Semarang | 154 | Rp 6.750 | Rp 1.979 | Rp 4.791 | 9 dari 10 | 20 minggu | 10/10 | ✅ layak | Rp -1.029 (—) |
| Bawang merah | Kota Tegal → Kota Surabaya | 463 | Rp 6.250 | Rp 2.787 | Rp 3.663 | 9 dari 10 | 13 minggu | 10/10 | ✅ layak | Rp 1.578 (✅) |
| Cabai rawit merah | Kota Kediri → Kota Semarang | 257 | Rp 7.750 | Rp 4.047 | Rp 3.403 | 8 dari 10 | 7 minggu | 10/10 | ✅ layak | Rp -2.735 (—) |
| Cabai rawit merah | Kab. Jember → Kota Semarang | 514 | Rp 8.500 | Rp 5.054 | Rp 3.321 | 7 dari 10 | 6 minggu | 10/10 | ✅ layak | Rp -3.191 (—) |
| Daging ayam ras | Kota Kediri → Kota Bandung | 606 | Rp 6.000 | Rp 3.395 | Rp 2.582 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp -1.410 (—) |
| Telur ayam ras | Kota Kediri → Kota Surabaya | 119 | Rp 2.800 | Rp 1.311 | Rp 1.486 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp -386 (—) |
| Telur ayam ras | Kota Kediri → Kota Bandung | 606 | Rp 4.100 | Rp 2.743 | Rp 1.307 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp -1.175 (—) |
| Telur ayam ras | Kota Kediri → Kota Semarang | 257 | Rp 2.750 | Rp 1.717 | Rp 1.082 | 10 dari 10 | hampir selalu | 10/10 | ✅ layak | Rp -1.292 (—) |
| Cabai rawit merah | Kota Kediri → Kota Surabaya | 119 | Rp 4.500 | Rp 3.505 | Rp 895 | 5 dari 10 | 3 minggu | 7/10 | — | Rp -6.543 (—) |
| Telur ayam ras | Kota Kediri → Kota Jakarta Pusat | 688 | Rp 3.700 | Rp 2.986 | Rp 699 | 9 dari 10 | 14 minggu | 10/10 | ✅ layak | Rp -1.871 (—) |
| Cabai rawit merah | Kab. Jember → Kota Surabaya | 206 | Rp 4.250 | Rp 3.845 | Rp 243 | 5 dari 10 | 3 minggu | 7/10 | — | Rp -6.295 (—) |
| Daging ayam ras | Kota Kediri → Kota Jakarta Pusat | 688 | Rp 3.850 | Rp 3.758 | Rp 87 | 5 dari 10 | 4 minggu | 4/10 | — | Rp -5.750 (—) |
| Daging ayam ras | Kota Kediri → Kota Surabaya | 119 | Rp 1.250 | Rp 1.259 | Rp 6 | 5 dari 10 | 4 minggu | 8/10 | — | Rp -12.259 (—) |
| Cabai rawit merah | Kab. Banyuwangi → Kota Semarang | 582 | Rp 5.250 | Rp 5.508 | Rp -470 | 5 dari 10 | 2 minggu | 6/10 | — | Rp -7.645 (—) |
| Daging ayam ras | Kota Kediri → Kota Semarang | 257 | Rp 750 | Rp 1.865 | Rp -1.070 | 2 dari 10 | 2 minggu | 1/10 | — | Rp -1.645 (—) |
| Cabai merah keriting | Kota Tasikmalaya → Kota Semarang | 327 | Rp 2.250 | Rp 4.397 | Rp -2.184 | 4 dari 10 | 3 minggu | 0/10 | — | Rp -11.509 (—) |
| Cabai rawit merah | Kab. Banyuwangi → Kota Surabaya | 273 | Rp 250 | Rp 4.298 | Rp -4.086 | 2 dari 10 | 2 minggu | 4/10 | — | Rp -10.748 (—) |
| Cabai merah keriting | Kota Tasikmalaya → Kota Surabaya | 621 | Rp -1.250 | Rp 5.550 | Rp -6.787 | 1 dari 10 | 2 minggu | 0/10 | — | Rp -14.050 (—) |

Semua angka adalah median mingguan. "Bertahan" = rata-rata panjang rangkaian minggu untung berturut-turut (minggu tanpa
data dilewati); "hampir selalu" = untung pada ≥ 95% minggu.

## Batasan
- Ongkos angkut adalah asumsi (tarif truk, tol, muatan, susut); lihat `docs/biaya_logistik_report.md`.
- Harga eceran di kota tujuan belum tentu harga jual yang bisa didapat distributor (lihat uji ketahanan);
  volume & ketersediaan stok tidak diketahui.
- Harga pedagang besar dicatat ~seminggu sekali (Kamis) dan bisa usang; minggu dengan harga sumber usang dikecualikan.

## File
- Tabel: `reports/tables/q2_rute_ringkasan.csv` (rute × skenario), `q2_per_komoditas.csv`, `q2_sensitivitas.csv`
- Data mingguan per rute: `data/interim/spread_mingguan.parquet`
- Grafik: `reports/figures/q2_rute_untung_konservatif.png`, `reports/figures/q2_rute_terbaik_selisih_vs_ongkos.png`
