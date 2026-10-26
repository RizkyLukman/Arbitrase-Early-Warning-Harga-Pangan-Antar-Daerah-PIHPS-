# Q3 — Kota penentu arah

Dibuat otomatis oleh `python -m src.analysis.leadlag` pada 2026-10-26 15:07.
Data: pasar tradisional, perubahan harga mingguan (log-return), Juli 2023 – Oktober 2026.
Metode: momentum tiap kota dibuang (prewhitening AR(4)), lalu kejutan harga tiap kota dibandingkan
dengan rata-rata semua kota lain pada jeda [1, 2, 3, 4] minggu; koreksi Benjamini–Hochberg (α = 0.05), korelasi
≥ 0.15 dan lebih kuat daripada arah sebaliknya. Granger hanya pendukung.
**Ini asosiasi statistik, bukan bukti sebab-akibat.**

## Temuan (bahasa dashboard)
**Kenaikan harga bawang merah di Kota Surakarta (Solo) biasanya disusul kota lain sekitar 1 minggu kemudian** (hubungan kuat). Untuk cabai rawit, kota yang harganya biasanya naik lebih dulu: Kota Surakarta (Solo), Kota Surabaya, Kota Kediri; kota di Jawa Barat dan DKI Jakarta cenderung menyusul. Tindakan: pantau harga di kota penentu arah setiap minggu; kenaikan di sana adalah sinyal untuk mengamankan stok di kota tujuan sekitar 1 minggu sebelum harga di sana ikut naik.

## Ringkasan per komoditas
| Komoditas | Kota | Seri stasioner (uji ADF) | Momentum mingguan (autokorelasi) | Bergerak di minggu yang sama (korelasi median) | Pasangan "mendahului": semu → setelah momentum dibuang | Kota penentu arah | Kota pengikut | Jeda (minggu) |
|---|---|---|---|---|---|---|---|---|
| Cabai rawit merah | 35 | 100% | 0,29 | 0,78 | 607 → 247 | 3 | 9 | 1 |
| Cabai merah keriting | 32 | 100% | 0,08 | 0,68 | 381 → 214 | 9 | 8 | 1 |
| Bawang merah | 35 | 100% | 0,30 | 0,57 | 628 → 507 | 17 | 18 | 1 |
| Bawang putih | 35 | 97% | 0,08 | 0,26 | 312 → 266 | 20 | 12 | 1 |
| Daging ayam ras | 35 | 100% | 0,03 | 0,62 | 330 → 289 | 10 | 17 | 1 |
| Telur ayam ras | 35 | 100% | 0,17 | 0,67 | 570 → 221 | 6 | 14 | 1 |

## Kota penentu arah (mendahului rata-rata kota lain)
| Komoditas | Kota | Provinsi | Jeda (minggu) | Korelasi | Didukung Granger |
|---|---|---|---|---|---|
| Cabai rawit merah | Kota Surakarta (Solo) | Jawa Tengah | 1 | 0,28 (sedang) | ya |
| Cabai rawit merah | Kota Surabaya | Jawa Timur | 1 | 0,28 (sedang) | ya |
| Cabai rawit merah | Kota Kediri | Jawa Timur | 1 | 0,26 (sedang) | ya |
| Cabai merah keriting | Kab. Cilacap | Jawa Tengah | 1 | 0,29 (sedang) | ya |
| Cabai merah keriting | Kota Semarang | Jawa Tengah | 1 | 0,28 (sedang) | ya |
| Cabai merah keriting | Kota Surakarta (Solo) | Jawa Tengah | 1 | 0,27 (sedang) | ya |
| Cabai merah keriting | Kab. Karanganyar | Jawa Tengah | 1 | 0,27 (sedang) | ya |
| Cabai merah keriting | Kab. Sragen | Jawa Tengah | 1 | 0,27 (sedang) | ya |
| Cabai merah keriting | Kota Tangerang | Banten | 1 | 0,25 (sedang) | ya |
| Cabai merah keriting | Kab. Klaten | Jawa Tengah | 1 | 0,25 (sedang) | ya |
| Cabai merah keriting | Kota Serang | Banten | 1 | 0,24 (sedang) | tidak |
| Cabai merah keriting | Kab. Wonogiri | Jawa Tengah | 1 | 0,24 (sedang) | ya |
| Bawang merah | Kota Surakarta (Solo) | Jawa Tengah | 1 | 0,51 (kuat) | ya |
| Bawang merah | Kota Tangerang | Banten | 1 | 0,47 (kuat) | ya |
| Bawang merah | Kab. Cilacap | Jawa Tengah | 1 | 0,47 (kuat) | ya |
| Bawang merah | Kota Serang | Banten | 1 | 0,45 (kuat) | ya |
| Bawang merah | Kota Cilegon | Banten | 1 | 0,43 (kuat) | ya |
| Bawang merah | Kota Kediri | Jawa Timur | 1 | 0,42 (kuat) | tidak |
| Bawang merah | Kota Bogor | Jawa Barat | 1 | 0,41 (kuat) | ya |
| Bawang merah | Kab. Sukoharjo | Jawa Tengah | 1 | 0,40 (kuat) | tidak |
| Bawang merah | Kab. Karanganyar | Jawa Tengah | 1 | 0,40 (kuat) | tidak |
| Bawang merah | Kota Bekasi | Jawa Barat | 1 | 0,37 (kuat) | tidak |
| Bawang merah | Kab. Cirebon | Jawa Barat | 1 | 0,37 (kuat) | tidak |
| Bawang merah | Kota Tegal | Jawa Tengah | 1 | 0,37 (kuat) | tidak |
| Bawang merah | Kota Surabaya | Jawa Timur | 1 | 0,36 (kuat) | tidak |
| Bawang merah | Kota Semarang | Jawa Tengah | 1 | 0,35 (kuat) | tidak |
| Bawang merah | Kota Sukabumi | Jawa Barat | 1 | 0,34 (kuat) | tidak |
| Bawang merah | Kota Cirebon | Jawa Barat | 1 | 0,33 (kuat) | ya |
| Bawang merah | Kab. Sumenep | Jawa Timur | 1 | 0,31 (kuat) | tidak |
| Bawang putih | Kota Tegal | Jawa Tengah | 1 | 0,45 (kuat) | ya |
| Bawang putih | Kota Surakarta (Solo) | Jawa Tengah | 1 | 0,44 (kuat) | ya |
| Bawang putih | Kab. Jember | Jawa Timur | 1 | 0,40 (kuat) | ya |
| Bawang putih | Kab. Kudus | Jawa Tengah | 2 | 0,40 (kuat) | ya |
| Bawang putih | Kota Probolinggo | Jawa Timur | 1 | 0,37 (kuat) | ya |
| Bawang putih | Kota Surabaya | Jawa Timur | 1 | 0,36 (kuat) | ya |
| Bawang putih | Kab. Wonogiri | Jawa Tengah | 1 | 0,36 (kuat) | ya |
| Bawang putih | Kota Kediri | Jawa Timur | 1 | 0,32 (kuat) | ya |
| Bawang putih | Kab. Karanganyar | Jawa Tengah | 1 | 0,32 (kuat) | ya |
| Bawang putih | Kab. Sumenep | Jawa Timur | 1 | 0,30 (sedang) | ya |
| Bawang putih | Kab. Cilacap | Jawa Tengah | 2 | 0,27 (sedang) | ya |
| Bawang putih | Kota Sukabumi | Jawa Barat | 1 | 0,27 (sedang) | ya |
| Bawang putih | Kota Bogor | Jawa Barat | 1 | 0,26 (sedang) | tidak |
| Bawang putih | Kota Semarang | Jawa Tengah | 1 | 0,26 (sedang) | tidak |
| Bawang putih | Kota Blitar | Jawa Timur | 2 | 0,23 (sedang) | ya |
| Bawang putih | Kab. Boyolali | Jawa Tengah | 1 | 0,23 (sedang) | tidak |
| Bawang putih | Kota Depok | Jawa Barat | 3 | 0,22 (sedang) | tidak |
| Bawang putih | Kab. Sukoharjo | Jawa Tengah | 1 | 0,22 (sedang) | tidak |
| Bawang putih | Kab. Cirebon | Jawa Barat | 1 | 0,22 (sedang) | tidak |
| Bawang putih | Kota Serang | Banten | 3 | 0,22 (sedang) | ya |
| Daging ayam ras | Kota Kediri | Jawa Timur | 1 | 0,34 (kuat) | ya |
| Daging ayam ras | Kota Probolinggo | Jawa Timur | 1 | 0,32 (kuat) | ya |
| Daging ayam ras | Kab. Tasikmalaya | Jawa Barat | 1 | 0,32 (kuat) | ya |
| Daging ayam ras | Kab. Cirebon | Jawa Barat | 1 | 0,31 (kuat) | ya |
| Daging ayam ras | Kota Cirebon | Jawa Barat | 1 | 0,29 (sedang) | ya |
| Daging ayam ras | Kota Tasikmalaya | Jawa Barat | 1 | 0,28 (sedang) | tidak |
| Daging ayam ras | Kab. Jember | Jawa Timur | 1 | 0,28 (sedang) | tidak |
| Daging ayam ras | Kota Malang | Jawa Timur | 1 | 0,27 (sedang) | ya |
| Daging ayam ras | Kota Semarang | Jawa Tengah | 1 | 0,25 (sedang) | tidak |
| Daging ayam ras | Kota Surakarta (Solo) | Jawa Tengah | 1 | 0,25 (sedang) | ya |
| Telur ayam ras | Kota Semarang | Jawa Tengah | 1 | 0,31 (kuat) | ya |
| Telur ayam ras | Kota Cirebon | Jawa Barat | 1 | 0,29 (sedang) | ya |
| Telur ayam ras | Kota Probolinggo | Jawa Timur | 1 | 0,28 (sedang) | ya |
| Telur ayam ras | Kota Malang | Jawa Timur | 1 | 0,28 (sedang) | ya |
| Telur ayam ras | Kab. Tasikmalaya | Jawa Barat | 1 | 0,27 (sedang) | tidak |
| Telur ayam ras | Kota Tegal | Jawa Tengah | 1 | 0,24 (sedang) | tidak |

## Kota pengikut (harganya biasanya menyusul kota lain)
- Cabai rawit merah: Kota Bandung, Kota Sukabumi, Kab. Tasikmalaya, Kab. Kudus, Kab. Cirebon, Kota Cirebon
- Cabai merah keriting: Kota Tasikmalaya, Kota Malang, Kab. Tasikmalaya, Kota Bandung, Kota Sukabumi, Kota Jakarta Pusat
- Bawang merah: Kab. Banyuwangi, Kab. Boyolali, Kab. Jember, Kab. Kudus, Kota Madiun, Kab. Tasikmalaya
- Bawang putih: Kab. Tasikmalaya, Kota Tangerang, Kota Cilegon, Kota Yogyakarta, Kota Madiun, Kab. Banyumas
- Daging ayam ras: Kab. Kudus, Kab. Sumenep, Kota Bogor, Kota Madiun, Kab. Klaten, Kota Depok
- Telur ayam ras: Kab. Kudus, Kab. Sumenep, Kota Bekasi, Kota Blitar, Kab. Klaten, Kab. Banyuwangi

## Arah penyebaran per provinsi
Rata-rata (mendahului − mengikuti) pada jeda 1 minggu. Positif = provinsi yang harganya biasanya naik lebih dulu.

| Provinsi | Cabai rawit merah | Cabai merah keriting | Bawang merah | Bawang putih | Daging ayam ras | Telur ayam ras |
|---|---|---|---|---|---|---|
| Jawa Tengah | 0,03 | 0,14 | 0,01 | 0,11 | -0,05 | 0,01 |
| Jawa Timur | 0,17 | -0,07 | -0,15 | 0,10 | 0,04 | 0,01 |
| Banten | 0,02 | 0,12 | 0,31 | -0,35 | -0,04 | -0,13 |
| DI Yogyakarta | -0,02 | 0,08 | -0,07 | -0,11 | -0,03 | 0,09 |
| Jawa Barat | -0,30 | -0,22 | 0,04 | -0,09 | -0,02 | 0,01 |
| DKI Jakarta | -0,15 | -0,24 | -0,02 | -0,09 | -0,12 | -0,10 |

## Untuk kota tujuan: kota yang perlu dipantau
Dari uji per pasangan kota (setelah momentum dibuang), maksimal 3 kota per kota tujuan × komoditas.

| Kota tujuan | Komoditas | Pantau harga di | Jeda (minggu) | Hubungan |
|---|---|---|---|---|
| Kota Bandung | Bawang merah | Kab. Cilacap (Jawa Tengah) | 1 | kuat |
| Kota Bandung | Bawang merah | Kota Surabaya (Jawa Timur) | 1 | kuat |
| Kota Bandung | Bawang merah | Kab. Karanganyar (Jawa Tengah) | 1 | kuat |
| Kota Bandung | Bawang putih | Kota Serang (Banten) | 1 | sedang |
| Kota Bandung | Bawang putih | Kota Tegal (Jawa Tengah) | 2 | sedang |
| Kota Bandung | Bawang putih | Kota Cirebon (Jawa Barat) | 2 | sedang |
| Kota Bandung | Cabai merah keriting | Kab. Klaten (Jawa Tengah) | 1 | kuat |
| Kota Bandung | Cabai merah keriting | Kota Tangerang (Banten) | 1 | kuat |
| Kota Bandung | Cabai merah keriting | Kab. Cilacap (Jawa Tengah) | 1 | kuat |
| Kota Bandung | Cabai rawit merah | Kota Serang (Banten) | 1 | kuat |
| Kota Bandung | Cabai rawit merah | Kota Blitar (Jawa Timur) | 1 | kuat |
| Kota Bandung | Cabai rawit merah | Kota Cilegon (Banten) | 1 | kuat |
| Kota Bandung | Daging ayam ras | Kab. Cirebon (Jawa Barat) | 1 | kuat |
| Kota Bandung | Daging ayam ras | Kota Malang (Jawa Timur) | 1 | kuat |
| Kota Bandung | Daging ayam ras | Kota Kediri (Jawa Timur) | 1 | kuat |
| Kota Bandung | Telur ayam ras | Kota Probolinggo (Jawa Timur) | 1 | kuat |
| Kota Bandung | Telur ayam ras | Kota Semarang (Jawa Tengah) | 1 | sedang |
| Kota Bandung | Telur ayam ras | Kota Cirebon (Jawa Barat) | 1 | sedang |
| Kota Jakarta Pusat | Bawang merah | Kota Serang (Banten) | 1 | kuat |
| Kota Jakarta Pusat | Bawang merah | Kab. Sukoharjo (Jawa Tengah) | 1 | kuat |
| Kota Jakarta Pusat | Bawang merah | Kota Bogor (Jawa Barat) | 1 | kuat |
| Kota Jakarta Pusat | Bawang putih | Kab. Kudus (Jawa Tengah) | 2 | kuat |
| Kota Jakarta Pusat | Bawang putih | Kab. Cilacap (Jawa Tengah) | 2 | kuat |
| Kota Jakarta Pusat | Bawang putih | Kota Surakarta (Solo) (Jawa Tengah) | 1 | kuat |
| Kota Jakarta Pusat | Cabai merah keriting | Kab. Karanganyar (Jawa Tengah) | 1 | kuat |
| Kota Jakarta Pusat | Cabai merah keriting | Kab. Klaten (Jawa Tengah) | 1 | kuat |
| Kota Jakarta Pusat | Cabai merah keriting | Kab. Sragen (Jawa Tengah) | 1 | kuat |
| Kota Jakarta Pusat | Cabai rawit merah | Kota Kediri (Jawa Timur) | 1 | kuat |
| Kota Jakarta Pusat | Cabai rawit merah | Kota Surakarta (Solo) (Jawa Tengah) | 1 | sedang |
| Kota Jakarta Pusat | Cabai rawit merah | Kab. Cilacap (Jawa Tengah) | 1 | sedang |
| Kota Jakarta Pusat | Daging ayam ras | Kab. Cirebon (Jawa Barat) | 1 | kuat |
| Kota Jakarta Pusat | Daging ayam ras | Kota Cirebon (Jawa Barat) | 1 | kuat |
| Kota Jakarta Pusat | Daging ayam ras | Kota Kediri (Jawa Timur) | 1 | kuat |
| Kota Jakarta Pusat | Telur ayam ras | Kota Semarang (Jawa Tengah) | 1 | kuat |
| Kota Jakarta Pusat | Telur ayam ras | Kota Probolinggo (Jawa Timur) | 1 | sedang |
| Kota Jakarta Pusat | Telur ayam ras | Kab. Tasikmalaya (Jawa Barat) | 1 | sedang |
| Kota Semarang | Bawang merah | Kota Cilegon (Banten) | 1 | sedang |
| Kota Semarang | Bawang merah | Kota Sukabumi (Jawa Barat) | 1 | sedang |
| Kota Semarang | Bawang merah | Kota Tangerang (Banten) | 1 | sedang |
| Kota Semarang | Daging ayam ras | Kab. Tasikmalaya (Jawa Barat) | 1 | kuat |
| Kota Semarang | Daging ayam ras | Kota Serang (Banten) | 1 | sedang |
| Kota Semarang | Daging ayam ras | Kota Cirebon (Jawa Barat) | 1 | sedang |
| Kota Surabaya | Bawang merah | Kota Surakarta (Solo) (Jawa Tengah) | 1 | kuat |
| Kota Surabaya | Bawang merah | Kota Serang (Banten) | 1 | kuat |
| Kota Surabaya | Bawang merah | Kota Tangerang (Banten) | 1 | kuat |
| Kota Surabaya | Bawang putih | Kab. Sukoharjo (Jawa Tengah) | 1 | kuat |
| Kota Surabaya | Bawang putih | Kab. Wonogiri (Jawa Tengah) | 1 | sedang |
| Kota Surabaya | Bawang putih | Kota Kediri (Jawa Timur) | 1 | sedang |
| Kota Surabaya | Cabai merah keriting | Kota Semarang (Jawa Tengah) | 1 | sedang |
| Kota Surabaya | Cabai merah keriting | Kab. Sragen (Jawa Tengah) | 1 | sedang |
| Kota Surabaya | Cabai merah keriting | Kab. Cilacap (Jawa Tengah) | 1 | sedang |
| Kota Surabaya | Daging ayam ras | Kab. Cirebon (Jawa Barat) | 1 | sedang |
| Kota Surabaya | Daging ayam ras | Kota Kediri (Jawa Timur) | 1 | sedang |
| Kota Surabaya | Daging ayam ras | Kota Tasikmalaya (Jawa Barat) | 1 | sedang |
| Kota Surabaya | Telur ayam ras | Kota Semarang (Jawa Tengah) | 1 | sedang |
| Kota Surabaya | Telur ayam ras | Kota Probolinggo (Jawa Timur) | 1 | sedang |

## Cara membaca & batasan
- Untuk 5 dari 6 komoditas, harga antar kota terutama **bergerak bersamaan di minggu yang sama** (korelasi minggu yang sama lebih tinggi daripada korelasi 'mendahului'); pengecualian: bawang putih. Pola "mendahului" hanya menambah sekitar 1 minggu waktu antisipasi, dengan hubungan lemah–sedang.
- Tanpa membuang momentum, ratusan pasangan kota tampak saling mendahului (kolom "semu"); angka itu tidak dipakai.
- Granger causality hanya pendukung dan **bukan** bukti bahwa harga di satu kota menyebabkan kenaikan di kota lain.
- Sampel PIHPS kecil (2 pasar per kota), harga berisik; kota "pengikut" bisa juga berarti pencatatannya terlambat.

## File
- Tabel: `reports/tables/q3_ringkasan_per_komoditas.csv`, `q3_peran_kota.csv`, `q3_arah_per_provinsi.csv`,
  `q3_pantau_untuk_kota_tujuan.csv`, `q3_pasangan_bermakna.csv`
- Grafik: `reports/figures/q3_kota_penentu_arah.png`, `reports/figures/q3_arah_per_provinsi.png`
