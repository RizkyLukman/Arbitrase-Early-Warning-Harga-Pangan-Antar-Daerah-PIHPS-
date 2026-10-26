# Audit Tahap 4 — Apakah analisis menjawab Q1–Q6, dan apakah angkanya bisa dipertanggungjawabkan?

Tanggal audit: **2026-10-26**, sebelum Tahap 5 (export Power BI). Yang diaudit: `src/analysis/*.py`, `reports/q1–q6_*.md`,
`reports/tables/`, `reports/figures/`. Data: `data/interim/` (hasil Tahap 2–3).

## Ringkasan

| | Pertanyaan | Terjawab? | Jawaban singkat (bahasa dashboard) | Bukti |
|---|---|---|---|---|
| Q1 | Komoditas & kota paling bergejolak | ✅ ya | Cabai rawit paling bergejolak (naik-turun ±13%/minggu), terutama di Kota Blitar; telur, ayam, bawang putih relatif tenang | `reports/q1_gejolak.md` |
| Q2 | Rute yang tetap untung setelah ongkos angkut, seberapa sering, berapa lama | ✅ ya | 23 dari 32 rute untung dengan ongkos 1,5×; 9 rute tetap untung bahkan jika dijual ke pedagang besar; terbaik cabai rawit Kediri → Bandung | `reports/q2_rute.md` |
| Q3 | Kota "penentu arah" & jedanya | ✅ ya, hubungan lemah–sedang | Cabai rawit naik dulu di Surakarta, Surabaya, Kediri; Jawa Barat & Jakarta menyusul ±1 minggu kemudian | `reports/q3_kota_penentu_arah.md` |
| Q4 | Berapa minggu sebelum Idulfitri harga naik & seberapa besar | ✅ ya, perkiraan kasar | Bawang merah naik mulai 4 minggu sebelum Lebaran, konsisten 3/3 tahun, +26% seminggu sebelum Lebaran | `reports/q4_pola_idul_fitri.md` |
| Q5 | Tambahan harga produsen → pedagang besar → pasar tradisional/modern | ✅ ya, perkiraan kasar | Beli di produsen 41% lebih murah daripada harga pasar untuk cabai keriting; telur hanya 10% | `reports/q5_margin.md` |
| Q6 | Apakah peringatan dini sederhana akurat (uji data lama) | ✅ ya — jawabannya **tidak** | Aturan brief menangkap 2 dari 10 lonjakan, tetapi hanya 1,2 dari 10 peringatan benar; kalah dari tebakan "sama seperti tahun lalu" | `reports/q6_peringatan_dini.md` |

Jawaban Q6 yang negatif **bukan kegagalan analisis**. Brief meminta: "Jika aturan tidak lebih baik dari baseline,
laporkan apa adanya." Itu yang dilakukan.

## 1. Hitung ulang independen (tanpa memakai `src/analysis`)

Angka kunci dihitung ulang dengan kode terpisah, langsung dari `data/interim/harga_mingguan.parquet`
(Q3: prewhitening ulang dengan OLS `statsmodels` & korelasi `scipy`).

| Angka di laporan | Dilaporkan | Hitung ulang | Hasil |
|---|---|---|---|
| Q1 gejolak mingguan cabai rawit (median kota) | 0,1645 | 0,1645 | ✅ |
| Q1 gejolak bawang putih / telur | 0,0310 / 0,0319 | 0,0310 / 0,0319 | ✅ |
| Q2 Kediri → Bandung cabai rawit: selisih harga median | Rp 26.450 | Rp 26.450 | ✅ |
| Q2 Kediri → Bandung: untung median ongkos ×1,5 | Rp 21.048 | Rp 21.048 | ✅ |
| Q2 Kediri → Bandung: porsi minggu untung | 0,9708 | 0,9708 | ✅ |
| Q2 jumlah rute layak ×1,5 | 23 | 23 | ✅ |
| Q3 penentu arah cabai rawit | Kediri, Surabaya, Surakarta | Kediri, Surabaya, Surakarta | ✅ |
| Q4 bawang merah minggu −1 (2024 / 2025 / 2026) | +25,2% / +38,9% / +12,7% | sama | ✅ |
| Q5 cabai keriting: lebih murah di produsen (median kota) | 40,7% | 40,7% | ✅ |
| Q5 Kota Tegal cabai keriting (satu kota, dari mentah bulanan) | 51,9% | 51,9% | ✅ |
| Q6 frekuensi dasar lonjakan cabai rawit 2026 | 0,0762 | 0,0762 | ✅ |

**Kesimpulan: tidak ada angka yang dikarang; semua angka kunci dapat direproduksi.**

## 2. Kesesuaian metode dengan brief

| Q | Permintaan brief | Status |
|---|---|---|
| Q1 | CV & std log-return per komoditas × kota; ranking; heatmap; tradisional vs modern | ✅ semua (CV di `q1_gejolak_per_kota.csv`) |
| Q2 | spread bersih = tujuan − sumber − biaya; % minggu > 0; median; persistensi; sensitivitas ×0,5–×2; layak hanya jika untung ×1,5; harga pedagang besar di sumber, disebut eksplisit | ✅ semua + uji ketahanan tambahan (jual ke pedagang besar) |
| Q3 | korelasi silang lag 0–4; ADF sebelum Granger; Granger hanya pendukung & ≠ kausalitas; koreksi BH; daftar leader + lag + kuat/sedang | ✅ semua + prewhitening (perbaikan metode, lihat §3) |
| Q4 | event study, baseline minggu −12..−9, minggu −8..+4, rata-rata per tahun + variasi antar tahun; "mulai naik minggu −N, puncak +Y%" | ✅ semua; STL (opsional) tidak dikerjakan |
| Q5 | margin % produsen → pedagang besar → pasar per kota × komoditas × minggu; hanya kota lengkap; catat cakupan | ✅ (dipakai median **bulanan** karena harga produsen jarang diperbarui; + pasangan kabupaten sentra berlabel PERLU_VERIFIKASI; + pasar modern) |
| Q6 | lonjakan ≥ X% dalam 4 minggu, X dari distribusi (p90); aturan z-score kenaikan > 2 di kota leader ATAU jendela Idulfitri; backtest latih ≤ T uji T+1 tanpa look-ahead; precision, recall, lead time; pembanding seasonal naive; lapor apa adanya | ✅ semua; X, kota penentu arah, dan jendela Idulfitri dihitung ulang dari data latih per tahun uji |

## 3. Masalah yang ditemukan & diperbaiki selama Tahap 4

| # | Masalah | Dampak jika dibiarkan | Perbaikan |
|---|---|---|---|
| 1 | Q2: persistensi "57 minggu" = artefak minggu Lebaran yang kosong memutus rangkaian | angka menyesatkan | minggu tanpa data dilewati; "hampir selalu" untuk ≥ 95% minggu untung |
| 2 | Q2: harga tujuan = eceran (memuat margin pengecer) | untung rute terlalu optimistis | uji ketahanan jual ke pedagang besar → 9 dari 32 rute tetap layak |
| 3 | Q3: momentum + pergerakan bersamaan → 26–53% pasangan kota tampak "saling mendahului" | hampir semua kota disebut penentu arah (semu) | prewhitening AR(4) + uji kota vs rata-rata pasar; tes khusus |
| 4 | Q4: cabai rawit "mulai naik minggu −8" padahal −8 = batas jendela | kesan presisi palsu | ditulis "≥ 8 minggu (sejak awal jendela)" + jumlah tahun konsisten |
| 5 | Q6: kalimat "0,7× lebih tepat" padahal aturan **lebih buruk** dari peringatan setiap minggu | kesimpulan terbalik | kalimat & vonis dihitung dari data: "belum layak dipakai sebagai pemicu pembelian" |
| 6 | Q6: "datang x minggu lebih awal" bersifat mekanis (tebakan "selalu" pun 7,2 minggu) | angka tampak bagus padahal tidak bermakna sendirian | catatan wajib dibaca bersama ketepatan |
| 7 | Q5: "telur & ayam hanya sedikit lebih murah"; "pedagang besar dekat dengan produsen untuk telur & ayam" | salah untuk daging ayam (21% & 15%) | kalimat dihitung dari data (telur saja; daging ayam masuk kelompok "hemat besar") |
| 8 | Q5: "pasar modern jauh di atas pasar tradisional" | salah untuk telur (−1%) | kalimat dihitung dari data |
| 9 | Q1: "pasar modern tampak lebih tenang" | salah untuk bawang putih | "5 dari 6 komoditas (kecuali bawang putih)" |
| 10 | Q3: "harga antar kota terutama bergerak bersamaan" | salah untuk bawang putih | "5 dari 6 komoditas; pengecualian: bawang putih" |
| 11 | Q3: hasil uji ADF tidak tampil di laporan; Q5: pasar modern belum diringkas | permintaan brief belum lengkap | kolom ADF ditambahkan; tabel pasar modern vs tradisional ditambahkan |
| 12 | Format: desimal titik di tabel Q6, label tanggal bertumpuk (Q5), legenda menutupi garis (Q6) | keterbacaan | diperbaiki |

Semua judul grafik & kalimat temuan kini dihitung dari data (dicek ulang dengan pencarian teks tetap di `src/analysis/`).

## 4. Keterbatasan yang tetap ada (wajib ditulis di memo & README)
- **Ongkos angkut = asumsi**, bukan data (sumber & alasan di `config/biaya_logistik.yaml`). Untuk cabai, asumsi susut 5% adalah komponen terbesar.
- **Q4 & Q6** hanya punya 3 kali Idulfitri dan 2 tahun uji → perkiraan kasar.
- **Q3** = asosiasi statistik, bukan sebab-akibat; jeda hanya ±1 minggu.
- **Q5** harga produsen jarang diperbarui (21–35% bulan tercatat lebih mahal daripada pedagang besar).
- Harga eceran ≠ harga jual distributor; volume & ketersediaan stok tidak diketahui.
- Sampel PIHPS kecil (2 pasar per kota); Kota Blitar sering muncul paling bergejolak — bisa efek sampel.

## 5. Kesimpulan audit
Keenam pertanyaan terjawab dengan angka yang dapat direproduksi. Tidak ditemukan angka karangan. Klaim yang sebelumnya
ditulis tetap dan tidak sepenuhnya benar (7 kasus) sudah diperbaiki menjadi kalimat yang dihitung dari data. Siap lanjut ke
Tahap 5 (export Power BI), dengan catatan Q6 dilaporkan sebagai "belum layak operasional".
