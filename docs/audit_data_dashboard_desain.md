# Audit data: dashboard versi desain

Tanggal: 2026-10-29. Objek: `excel/Dashboard_pangan.xlsx` (data per 23 Oktober 2026).
Tujuan: memastikan angka yang tampil benar, dan kesimpulan di layar tidak menyesatkan pengambil keputusan.

## Cara audit

1. Semua sel berisi angka atau kalimat di enam halaman dibaca dari workbook yang sudah dihitung ulang oleh Excel (sekitar 120 sel).
2. Angka dihitung ulang **secara independen** langsung dari `data/interim/harga_mingguan.parquet` dan `data/reference/biaya_rute.csv`,
   tanpa memakai fungsi di `src/`. Definisi mengikuti skrip analisis: ongkos = (ongkos angkut + susut × harga sumber) × pengali;
   rute layak = margin tengah > 0 dan untung minimal 6 dari 10 minggu; peringatan benar = diikuti awal lonjakan dalam 0 sampai 4 minggu.
3. Setiap judul, fakta, dan keputusan dibaca ulang: apakah angkanya mendukung kalimatnya, dan apakah pembandingnya adil.
4. Pemeriksaan 20 sel audit (`src/audit_dashboard.py`) tetap 20/20 cocok, 0 rumus error.

## Hasil hitung ulang: 34 dari 35 angka cocok

Cocok: harga cabai rawit di kota tujuan (Rp 75.075) dan nasional (Rp 103.250), selisih 27%, kenaikan 4 minggu cabai keriting 37%
(Rp 69.575); 23 rute layak, 9 rute aman, 28 rute untung minggu ini, margin positif 30/28/27/22 per pengali; rute terbaik Kediri ke
Bandung (selisih Rp 26.450, margin Rp 21.048, untung 9,7 dari 10 minggu, 33 minggu berturut-turut, margin minggu ini Rp 32.823, jika
dijual ke pedagang besar Rp 3.461); margin minggu ini empat rute lain; rata-rata perubahan mingguan cabai rawit 13%, keriting 10%,
telur 2%; nilai heatmap (contoh Blitar 22,4%, Bandung 11,8%); Blitar masuk 3 teratas di 5 dari 6 komoditas; 6 peringatan di Jakarta
dan tidak satu pun diikuti lonjakan; pola Lebaran bawang merah (+25%, +39%, +13%; rata-rata +26%) dan cabai rawit (−13%, +18%, +112%);
hemat cabai keriting di Tegal 52%.

Uji ketahanan tambahan: hemat beli di produsen cabai keriting tetap sekitar 42% bila hanya memakai kota yang punya data produsen
sendiri (tanpa pasangan kabupaten yang belum diverifikasi). Tiga kota paling bergejolak untuk cabai rawit sama (Blitar, Cilacap,
Sumenep) baik diukur dengan simpangan baku maupun rata-rata perubahan.

## Temuan

### Tinggi: bisa mendorong keputusan yang terlalu optimistis

**T1. Untung pindah stok dibandingkan dengan harga eceran.** Ringkasan menampilkan "Dampak +Rp 32.823/kg" untuk cabai rawit Kediri
ke Bandung, dan band keputusan menulis "Rp 32.823/kg lebih murah daripada di Bandung". Angka ini adalah margin *minggu ini* bila dijual
dengan *harga pasar eceran*. Dua hal membuatnya terlalu tinggi untuk dipakai sebagai harapan:
- minggu ini luar biasa: margin tengah rute ini Rp 21.048/kg, minggu ini 1,6 kali lipat;
- distributor biasanya tidak menjual dengan harga eceran. Bila dijual ke pedagang besar di Bandung, untung tipikalnya hanya
  **Rp 3.461/kg** (sekitar sepersepuluhnya).
Hal yang sama berlaku untuk Tegal ke Jakarta (Rp 12.496/kg minggu ini; Rp 2.676/kg bila dijual ke pedagang besar).
*Usulan:* ganti judul kolom menjadi "Untung per kg minggu ini (harga pasar)", dan tambahkan angka pedagang besar di fakta
("Bila dijual ke pedagang besar, untung tipikalnya Rp 3.461/kg"). Kalimat "lebih murah daripada di Bandung" menjadi
"lebih murah daripada harga pasar di Bandung".

**T2. "Rute aman di semua skenario" terlalu kuat.** Sembilan rute itu diuji aman pada ongkos 1,5 kali, juga bila dijual ke pedagang
besar. Pada ongkos 2 kali **dan** dijual ke pedagang besar, margin tengahnya masih positif, tetapi tiga rute hanya untung kurang dari
6 dari 10 minggu: Kediri ke Bandung (5,9), Jember ke Bandung (5,3), Probolinggo ke Bandung (5,5). Enam rute lain tetap 6 dari 10 atau
lebih. *Usulan:* label menjadi "Rute aman (ongkos 1,5 kali, juga bila dijual ke pedagang besar)", dan tambahkan "6 rute tetap aman
walau ongkos kirim dua kali perkiraan". Ini juga ada di versi lama dashboard.

**T3. Hemat beli di produsen dibandingkan dengan harga eceran.** Judul Rantai pasok: "menghemat sampai 41% untuk cabai keriting".
Pembandingnya harga pasar eceran, padahal sumber beli perusahaan saat ini adalah pedagang besar. Dibanding pedagang besar, hemat
membeli di produsen (nilai tengah antar kota) adalah: cabai keriting 20%, bawang merah 16%, cabai rawit 15%, ayam 13%, telur 4%.
Angka itu masih belum termasuk biaya mengumpulkan dari banyak petani. *Usulan:* judul memakai pembanding pedagang besar ("Beli langsung
di produsen sekitar 20% lebih murah daripada pedagang besar untuk cabai keriting"), angka 41% tetap di tabel sebagai pembanding harga
pasar.

**T4. Kalimat yang bertentangan di halaman Peringatan dini.** Fakta keputusan 2 menulis "pola musiman lebih bisa dipegang", padahal
grafik di halaman yang sama menunjukkan aturan "hanya masa menjelang Lebaran" paling buruk (benar 0,3 dari 10). Keduanya mengukur hal
berbeda: kalender Lebaran berguna untuk jadwal beli (bawang merah naik 3 dari 3 tahun), tetapi tidak untuk menebak lonjakan mingguan.
*Usulan:* "Kalender Lebaran berguna untuk jadwal beli bawang merah (naik 3 dari 3 tahun), tetapi tidak untuk menebak lonjakan
mingguan: aturan 'masa menjelang Lebaran' hanya benar 0,3 dari 10." Ini juga ada di versi lama dashboard.

### Sedang: angka atau label kurang tepat

**S1. Dua ukuran gejolak tercampur di halaman Gejolak harga.** Judul memakai rata-rata perubahan mingguan (cabai rawit 13%), sedangkan
peta, grafik 10 kota, dan heatmap memakai simpangan baku perubahan mingguan (Blitar 22%). Pembaca akan membaca "Blitar berubah 22% per
minggu", padahal rata-rata perubahannya 18%. *Usulan:* tampilkan rata-rata perubahan per kota di seluruh halaman (urutan tiga kota
teratas tidak berubah), atau beri label jelas bahwa angka kota adalah ukuran naik-turun, bukan rata-rata perubahan. Pilihan pertama
perlu menyesuaikan nilai acuan `kpi_gejolak_kota_teratas` di `src/audit_dashboard.py`.

**S2. Kolom "Ongkos kirim" di tabel rute dihitung sebagai selisih dikurangi margin.** Karena keduanya nilai tengah, hasil
pengurangannya bukan nilai tengah ongkos. Selisihnya sampai Rp 450/kg: Banyuwangi ke Bandung tampil Rp 7.339, seharusnya Rp 6.889;
Probolinggo ke Jakarta tampil Rp 3.556, seharusnya Rp 3.706; Kediri ke Bandung tampil Rp 5.402, seharusnya Rp 5.414. *Usulan:* ambil
nilai tengah ongkos langsung dan tetap ikut pengali serta tambahan ongkos. Ini juga ada di versi lama dashboard.

**S3. "Ayam, telur, dan bawang putih hanya berubah 2% sampai 3% per minggu di semua kota".** Angka 2 sampai 3% adalah nilai tengah
antar kota. Per kota rentangnya 0,6% sampai 4,2% (tertinggi ayam di Jember). Kesimpulannya tetap benar karena cabai di kota paling
tenang pun 7,5% (cabai keriting) dan 8,6% (cabai rawit). *Usulan:* "rata-rata 2 sampai 3% per minggu; di kota paling bergejolak pun paling tinggi 4%, jauh di bawah cabai
(paling rendah 7,5%)."

**S4. Keputusan "tunda rute dengan margin di bawah Rp 1.000/kg" tidak dijelaskan faktanya.** Data mendukungnya: tepat lima rute
dengan margin di bawah Rp 1.000/kg berubah rugi bila ongkos kirim dua kali perkiraan, dan inilah penyebab margin positif turun dari 27
menjadi 22. *Usulan:* tulis hubungan itu di fakta.

### Ringan

- **R1.** "Sekitar 5 kali lipat telur": cabai rawit 6 kali, cabai keriting 5 kali. Usulan: "5 sampai 6 kali lipat".
- **R2.** Judul grafik rute terbaik ("9,7 dari 10 minggu") dihitung dari Juli 2023 sampai Oktober 2026, sedangkan grafiknya hanya
  52 minggu terakhir. Usulan: tambahkan "sejak Juli 2023".
- **R3.** Untuk cabai keriting, tabel saran Ringkasan menampilkan "Beli secukupnya", bukan "Pindahkan stok". Alasannya, rute
  keriting hanya untung bila dijual eceran dan harganya sedang naik cepat. Aturan tampilan ini belum tertulis di Catatan metode.
- **R4.** Label angka di grafik batang mengikuti bahasa Excel pembaca ("1.2" di Excel berbahasa Inggris), sedangkan kartu memakai
  "1,2". Kosmetik.

## Dampak ke memo dan README (hanya dicatat, belum diubah)

- Memo rekomendasi 1 menulis "jika ongkos kirim 2 kali perkiraan, kesembilan rute masih untung 8 sampai 10 dari 10 minggu". Ini benar
  hanya bila dijual dengan harga pasar; bila dijual ke pedagang besar, enam dari sembilan rute yang tetap untung minimal 6 dari 10 minggu
  (lihat T2). Angka hemat Rp 1.400 sampai 6.900/kg di memo sudah memakai pembanding pedagang besar, jadi sudah konservatif.
- Memo rekomendasi 3 dan README menyebut hemat 41/32/21% "daripada pasar". Pembandingnya tertulis, tetapi pembaca bisa mengira itu
  penghematan dibanding sumber beli sekarang (lihat T3).
- Memo rekomendasi 5 sebaiknya menegaskan bahwa kalender Lebaran untuk jadwal beli, bukan untuk menebak lonjakan (lihat T4).

## Yang tidak diaudit ulang di sini

Backtest peringatan dini (benar 1,2, terdeteksi 2,4, lebih awal 5,8 minggu) dan uji kota yang naik lebih dulu tidak dihitung ulang dari
nol. Keduanya sudah diaudit di `docs/audit_analisis.md`, dan nilainya di dashboard cocok dengan `data/processed/`.

## Status perbaikan (2026-10-29)

Semua temuan di atas sudah diperbaiki di `src/build_excel_desain.py`. Memo, README, laporan analisis, dan dashboard versi lama tidak
diubah.

| Temuan | Perbaikan |
|---|---|
| T1 | Kolom "Dampak" menjadi "Angka minggu ini", dengan catatan di bawah tabel bahwa untung pindah stok dihitung dengan harga pasar, plus contoh untung tipikal bila dijual ke pedagang besar (Kediri ke Bandung Rp 3.461/kg). Fakta di band dan kalimat "tiga hal" kini menulis "lebih murah daripada harga pasar di ..." dan menyebut untung bila dijual ke pedagang besar. |
| T2 | Label "Rute aman di semua skenario" menjadi "Rute aman", dengan keterangan "6 di antaranya tetap aman pada ongkos 2 kali" (dihitung dari data: untung minimal 6 dari 10 minggu bila dijual ke pedagang besar dengan ongkos 2 kali). Keputusan band: mulai dari 6 rute yang paling tahan kenaikan ongkos. |
| T3 | Judul Rantai pasok memakai pembanding pedagang besar: "sekitar 22% lebih murah daripada pedagang besar untuk cabai keriting; untuk telur hanya 3%". Tabel menampilkan dua kolom: hemat dibanding pedagang besar dan dibanding harga pasar. Angka hemat dibanding pedagang besar diturunkan dari kolom margin pedagang besar (1 dikurangi 1/(1 + margin)) supaya konsisten dengan tabel; hasilnya cabai keriting 22%, cabai rawit 14%, ayam 13%, bawang merah 9%, telur 3%. Angka di bagian T3 di atas (20/16/15/13/4%) memakai cara hitung lain (rasio nilai tengah harga) dan tidak dipakai. |
| T4 | Fakta keputusan 2 Peringatan dini: kalender Lebaran berguna untuk jadwal beli, tetapi aturan "masa menjelang Lebaran" hanya benar 0,3 dari 10 untuk menebak lonjakan. Keputusan: pakai kalender untuk jadwal beli, bukan pemicu peringatan. |
| S1 | Seluruh halaman Gejolak harga memakai satu ukuran: rata-rata perubahan per minggu (peta, grafik 10 kota, heatmap, band). Workbook diberi penanda `ukuran_gejolak` agar `src/audit_dashboard.py` membandingkan dengan nilai acuan yang sesuai. |
| S2 | Kolom ongkos kirim = nilai tengah ongkos (ongkos angkut + susut + tambahan) pada pengali terpilih; ikut berubah saat sel kuning diubah. |
| S3, S4, R1 | Kalimat band dihitung dari data: "paling tinggi 4% ... cabai paling rendah 7,5%", "5 rute dengan margin di bawah Rp 1.000/kg berubah rugi bila ongkos kirim dua kali perkiraan", "5 sampai 6 kali lipat telur". |
| R2 | Judul grafik rute terbaik ditambah "sejak Juli 2023". |
| R3 | Catatan metode menjelaskan aturan tampilan tabel saran dan definisi "tahan 2 kali". |
| R4 | Angka di grafik batang Peringatan dini dipindah ke label kategori dengan format Indonesia ("(1,2)"). |

**Audit ulang setelah perbaikan:** 20/20 sel audit cocok, 0 rumus error, 0 istilah teknis (848 rumus). Hitung ulang independen untuk
angka yang berubah: **98 dari 98 cocok** (10 nilai ongkos, 75 sel heatmap, jumlah rute aman dan tahan 2 kali, lima rute yang berbalik
rugi, angka kalimat band, judul Rantai pasok). Uji ketahanan: hemat dibanding pedagang besar bila hanya memakai kota dengan produsen
sendiri: cabai keriting 23%, cabai rawit 14%, bawang merah 8%, telur 3%, ayam 7% (ayam lebih rendah karena tanpa pasangan kabupaten;
angka dashboard 13% bergantung pada pasangan kabupaten yang belum diverifikasi). Uji sel input: ongkos rute terbaik 5.414 pada 1,5 kali,
7.219 pada 2 kali, 8.414 bila ditambah Rp 2.000/kg; jumlah rute untung 23, 22, 15.

## Penyelarasan dengan laporan analisis (2026-10-29)

Dua angka baru di dashboard kini dihitung di skrip analisis, bukan di skrip dashboard, sehingga bisa ditelusuri:
- "6 rute tetap aman walau ongkos kirim dua kali perkiraan": `src/analysis/spread.py`, kolom
  `tahan_ongkos_maks_jual_ke_pedagang_besar` di `reports/tables/q2_rute_ringkasan.csv`, kalimat "uji paling berat" di
  `reports/q2_rute.md`, lalu `data/processed/dim_rute`. Analisis membuang minggu dengan harga sumber usang, sehingga Kediri ke
  Bandung tercatat 5,8 dari 10 minggu (hitung ulang tanpa pengecualian itu 5,9); jumlah rutenya sama, 6.
- "Hemat dibanding pedagang besar 22/14/13/9/3%": `src/analysis/margin.py`, kolom `hemat_beli_produsen_vs_pedagang_besar_pct`
  di `reports/tables/q5_per_komoditas.csv` dan `q5_per_kota.csv`, kalimat temuan `reports/q5_margin.md`, lalu
  `data/processed/dim_komoditas` dan `fact_margin`.
Setelah ekspor ulang dan build ulang: 20/20 sel audit, hitung ulang independen 98/98. Memo dan README sudah memakai pembanding
yang sama.
