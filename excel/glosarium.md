# Glosarium: istilah analisis → bahasa dashboard

Dashboard, memo rekomendasi, dan bagian hasil di README memakai kolom kanan. Istilah teknis (kolom kiri) hanya dipakai di
notebook, README bagian metode, tooltip "cara membaca", atau halaman tersembunyi "Catatan metode".

| Istilah teknis (notebook/README) | Di dashboard |
|---|---|
| Volatilitas / koefisien variasi / std. log-return | Gejolak harga / seberapa besar harga naik-turun dari minggu ke minggu |
| Spread kotor | Selisih harga |
| Spread bersih | Untung per kg (setelah ongkos angkut) |
| Biaya logistik (asumsi) | Ongkos angkut (perkiraan) |
| Sensitivity ×0,5 … ×2 | "Kalau ongkos ternyata 0,5× … 2×" |
| % minggu spread > 0 | Minggu untung: [x] dari 10 |
| Persistensi | Peluang biasanya bertahan [x] minggu |
| Kota leader / lead-lag | Kota penentu arah / kota yang harganya biasanya naik lebih dulu |
| Lag | Jeda (minggu) |
| Korelasi + q-value (BH) | Hubungan: kuat / sedang (hanya yang bukan kebetulan ditampilkan) |
| Alert / z-score > 2 | Peringatan / harga naik jauh di atas kebiasaan |
| Precision | Peringatan yang terbukti benar: [x] dari 10 |
| Recall | Lonjakan yang berhasil diperingatkan: [x] dari 10 |
| Lead time | Peringatan datang [x] minggu lebih awal |
| Baseline seasonal naive | Tebakan "sama seperti tahun lalu" |
| Event study / baseline minggu −12 s/d −9 | Pola harga sekitar Idulfitri / dibanding harga normal |
| Margin produsen → pedagang besar → eceran | Tambahan harga di tiap tingkat |
| Backtest pada tahun T+1 | Diuji pada data tahun [tahun] |
| Data ≤ H-2 | Data per [tanggal] |

## Padanan nama kolom di `data/processed/`

| Kolom | Arti di dashboard |
|---|---|
| `fact_spread.selisih_harga` | Selisih harga (harga di kota tujuan − harga pedagang besar di kota sumber) |
| `fact_spread.ongkos_angkut`, `susut_rp` | Komponen ongkos angkut (perkiraan): ongkos tetap per rute + susut yang ikut harga |
| `fact_spread.untung_per_kg_x1_5` | Untung per kg setelah ongkos angkut ×1,5 (skenario konservatif) |
| `dim_rute.minggu_untung_dari_10` | Minggu untung: [x] dari 10 |
| `dim_rute.rata_bertahan_minggu` | Peluang biasanya bertahan [x] minggu |
| `fact_harga_mingguan.gejolak_4m` / `gejolak_12m` | Seberapa besar harga naik-turun dalam 4 / 12 minggu terakhir |
| `fact_harga_mingguan.kenaikan_vs_kebiasaan` | Seberapa jauh kenaikan minggu ini di atas kebiasaan 52 minggu sebelumnya (> 2 = jauh di atas kebiasaan) |
| `fact_penentu_arah.peran`, `jeda_minggu`, `hubungan` | Kota penentu arah / pengikut; jeda (minggu); hubungan kuat / sedang |
| `fact_uji_peringatan.benar_dari_10` | Peringatan yang terbukti benar: [x] dari 10 |
| `fact_uji_peringatan.tertangkap_dari_10` | Lonjakan yang berhasil diperingatkan: [x] dari 10 |
| `fact_uji_peringatan.lebih_awal_minggu` | Peringatan datang [x] minggu lebih awal |
| `fact_pola_idul_fitri.kenaikan_vs_harga_normal` | Kenaikan dibanding harga normal (rata-rata minggu −12 s/d −9 sebelum Idulfitri) |
| `fact_margin.tambahan_di_pedagang_besar_pct` / `tambahan_di_pasar_pct` | Tambahan harga di tiap tingkat |
| `fact_margin.hemat_beli_produsen_pct` | Lebih murah [x]% jika membeli langsung di produsen |
| `dim_info.data_terakhir` | Data per [tanggal] |
