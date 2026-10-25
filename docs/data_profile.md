# Profil data mentah PIHPS & rencana preprocessing

Tanggal profil: **2026-10-25**. Data: `data/raw/` hasil Tahap 1 (960 file JSON, 2023-07-03 s/d 2026-10-23,
6 provinsi Pulau Jawa, 4 jenis pasar × 6 komoditas). Semua angka di bawah berasal dari pemrosesan data mentah
tanpa cleaning.

**Sumber angka: [`notebooks/01_eda.ipynb`](../notebooks/01_eda.ipynb)** (kode, tabel, grafik, dan narasi lengkap).
Dokumen ini ringkasannya. Ambang batas yang dipakai ada di `config/config.yaml` bagian `cleaning`.

Ringkasan: **datanya lengkap dan formatnya rapi, tetapi ada empat jebakan** yang harus ditangani sebelum analisis:
(1) hari libur diisi harga hari sebelumnya, (2) harga di pasar modern, pedagang besar, dan produsen jarang berubah,
(3) ada salah input berupa lonjakan sehari dan pergeseran level, (4) satu kota tercatat dengan dua nama.

---

## 1. Struktur

| Aspek | Temuan | Implikasi preprocessing |
|---|---|---|
| Bentuk | Format lebar: 1 baris per wilayah, 1 kolom per tanggal (`DD/MM/YYYY`) | Ubah ke format panjang |
| Baris | `level` 0 = nasional, 1 = provinsi, 2 = kota/kab | Pisahkan: kota → `fact_harga`; nasional → pembanding |
| Baris nasional | **Terverifikasi** sama persis dengan permintaan nasional tanpa filter provinsi (cabai rawit, Mar 2024) | Rata-rata nasional tersedia gratis di setiap file. Tidak perlu unduhan tambahan |
| Baris provinsi | = rata-rata kota di provinsi itu (selisih median 0,01%, maks 0,11%) | Tidak perlu disimpan; bisa dihitung ulang |
| Provinsi sebuah kota | Tidak ada di baris kota, hanya dari urutan baris | Petakan lewat `data/raw/ref/regency_*.json` (nama → id → provinsi) |
| Nilai | 665.084 nilai, **semua** berformat bilangan bulat dengan koma ribuan (`58,750`), 0 gagal parse | Parser: hapus koma → integer Rupiah |
| Kosong | Ditulis `-` | → NaN |
| Tanggal | 865 tanggal = **semua** hari Senin–Jumat dalam rentang, termasuk hari libur nasional | Lihat §2.1 (hari libur) |
| Nama kota | 63 nama unik, semua ada di referensi; 6 nama berspasi di ujung (`Kab. Boyolali `, dst.) | `strip()` lalu petakan ke id |
| Duplikat kota | Pasar modern punya **"Kota Surakarta" (id 787)** dan **"Kota Surakarta (Solo)" (id 36)**; nilai identik 87% hari, korelasi 0,995 | Simpan id 36 (dipakai di semua jenis pasar), buang id 787 |
| Kota baru | Produsen Kota Blitar baru mulai 2026-01 | Tidak dipakai untuk analisis tren |

Cakupan kota Jawa: Tradisional 35 (cabai merah keriting 33), Modern 24, Pedagang Besar 23 (keriting 21),
Produsen 48 kab/kota (bawang putih: 0).

## 2. Kualitas

### 2.1 Hari libur diisi harga hari sebelumnya
- Pada hari biasa, rata-rata 56% seri pasar tradisional tidak berubah dari hari sebelumnya.
- Ada **72 hari kerja** di mana > 90% seri tidak berubah. Tanggalnya bertepatan dengan libur nasional dan cuti bersama,
  misalnya 17 Agustus, 25–26 Desember, 1 Januari, serta **seminggu penuh sekitar Idul Fitri**
  (2024-04-08 s/d 04-15, 2025-03-31 s/d 04-07, 2026-03-18 s/d 03-24).
- Artinya, nilai pada hari-hari itu **bukan hasil pencacahan**. BI mengisinya dengan harga hari kerja terakhir.
- **Dampak:** gejolak harga harian terlihat lebih kecil, dan **minggu Idul Fitri tampak datar** di data mingguan.
  Ini langsung memengaruhi pola musiman (Q4) dan peringatan dini (Q6).
- **Tindakan:** tandai `is_libur_isi`, lalu perlakukan sebagai kosong untuk perhitungan harian. Minggu dengan < 3 hari
  pencacahan nyata ditandai `minggu_tipis`. Daftar tanggal dideteksi dari data, lalu dicocokkan dengan
  `data/reference/hari_besar.csv` setelah file itu diverifikasi dari SKB.

### 2.2 Data kosong (baris kota)

| Komoditas | Tradisional | Modern | Pedagang Besar | Produsen |
|---|---|---|---|---|
| Telur ayam | 0,94% | 2,89% | 0,27% | 0,93% |
| Bawang merah | 0,94% | 4,11% | 0,29% | 1,71% |
| Bawang putih | 0,94% | 3,82% | 0,29% | – |
| Cabai merah keriting | 1,01% | 3,19% | 0,32% | 1,37% |
| Cabai rawit merah | 0,94% | 3,32% | 0,29% | 0,97% |
| Daging ayam | 0,94% | 3,03% | 0,29% | 1,08% |

- 4.165 celah: 3.306 sepanjang 1 hari, 389 sepanjang 2 hari, 239 sepanjang 4 hari. **185 celah > 5 hari kerja**, terpanjang 39.
- Pola khusus:
  - Pasar modern: dua periode ketika 60–70% seri kosong bersamaan, yaitu 2023-11-29 s/d 12-07 dan 2026-09-30 s/d 10-05
    (kemungkinan gangguan pelaporan).
  - **Pasar modern Kab. Banyuwangi bawang merah/putih kosong 33–36%** → tidak dipakai.
  - Produsen: celah 21–23 hari (sebulan penuh) di beberapa kabupaten (Pandeglang, Serang, Sumedang, Garut, Tegal, Malang).
  - Pasar tradisional cabai merah keriting Kab. Jember: celah 23 hari.
- Tidak ada seri yang 100% kosong; tidak ada tanggal yang kosong di semua kota sekaligus.
- **Tindakan (sesuai brief):** celah ≤ 5 hari kerja → forward-fill + `is_imputed`. Celah lebih panjang dibiarkan NaN.

### 2.3 Harga jarang berubah (data "macet")

% hari harga sama persis dengan hari sebelumnya:

| Komoditas | Tradisional | Modern | Pedagang Besar | Produsen |
|---|---|---|---|---|
| Cabai rawit merah | 38% | 88% | 83% | 96% |
| Cabai merah keriting | 45% | 90% | 84% | 96% |
| Daging ayam | 62% | 93% | 88% | 96% |
| Telur ayam | 65% | 85% | 86% | 96% |
| Bawang merah | 65% | 91% | 87% | 96% |
| Bawang putih | 80% | 93% | 90% | – |

- Seri dengan harga tidak berubah ≥ 60 hari kerja berturut-turut: Tradisional 16, Modern 59, Pedagang Besar 13, Produsen 49.
  Terpanjang: 272 hari kerja (daging ayam pasar modern Kota Malang).
- **Dampak:**
  - Hanya **pasar tradisional** yang cukup "hidup" untuk analisis gejolak (Q1) dan kota penentu arah (Q3).
  - Perbandingan gejolak pasar tradisional vs modern (Q1) akan bias: modern terlihat stabil karena datanya jarang diperbarui,
    belum tentu karena harganya memang stabil. Harus ditulis sebagai batasan.
  - Untuk selisih harga (Q2) dan tambahan harga (Q5), pedagang besar dan produsen tetap bisa dipakai karena yang dibutuhkan
    adalah **level** harga, bukan perubahannya. Tetapi level bisa usang.
- **Tindakan:** hitung `run_datar` (hari berturut-turut tanpa perubahan) per titik data. Tandai `is_usang` jika ≥ 60 hari kerja
  (ambang di config). Laporkan di tabel kualitas data.

### 2.4 Lonjakan & salah input
- Perubahan harian > 40%: 1.610 dari 525.445 (0,3%).
- **Lonjakan sehari lalu kembali** (kandidat salah input): 11 kasus. Contoh:
  bawang merah Kab. Wonogiri 2026-05-20 Rp 143.750 (median sekitar Rp 46.750);
  cabai rawit Kab. Banyumas 2025-04-23 Rp 258.750 (median Rp 78.750); cabai rawit Kota Sukabumi 2025-12-15 Rp 264.250.
- **Pergeseran level** yang tidak tertangkap aturan lonjakan: produsen bawang merah Kab. Garut turun dari Rp 15.000 ke
  **Rp 3.000/kg** sejak 2025-03-25 dan bertahan. Pedagang besar cabai merah keriting Kota Blitar Rp 6.500/kg (Des 2024).
- **Lonjakan regional yang kemungkinan nyata:** cabai merah keriting 2025-06-20 di Kota Serang, Cilegon, Tangerang
  (+50–100%, turun bertahap beberapa hari). Terjadi di beberapa kota sekaligus.
- **Aturan brief (|x − median| > 5×MAD) terlalu sensitif untuk data ini:** menandai 7.766 titik (1,47% harga terisi),
  karena MAD ≈ 0 pada seri yang datar.
- **Tindakan: aturan dua tingkat** (ambang di config, diuji di notebook §5):

  | Aturan | Tingkat | Definisi | Hasil |
  |---|---|---|---|
  | A. Lonjakan tajam | penanda saja, nilai tetap dipakai | deviasi > max(5×MAD, 25%) dari median bergulir 21 hari, hari sebelum & sesudah normal | 117 titik, hampir semua cabai di pasar tradisional |
  | B. Rasio ekstrem | salah input → dikosongkan | harga ≥ 3× atau ≤ ⅓ median bergulir seri itu | 4 titik (Wonogiri ×2, Banyumas, Sukabumi) |
  | C. Lintas kota | salah input → dikosongkan | harga ≥ 5× atau ≤ ⅕ median kota lain (komoditas, jenis pasar & hari sama) | 23 titik (produsen bawang merah Garut, sebulan) |

  Total yang dikosongkan: **27 titik (0,005%)**. Nilai asli selalu disimpan.
- Kenapa ambang C = 5× dan bukan 3×: pada 3×, harga produsen cabai yang memang anjlok saat panen raya di beberapa
  kabupaten (mis. Magelang, Rembang, Gresik) dan pasar modern Kota Blitar ikut tertangkap, padahal itu bukan salah input.
- Kenapa A hanya penanda: lonjakan sehari 25–100% pada cabai sering nyata (contoh lonjakan regional Banten 2025-06-20).

### 2.5 Kewajaran level harga
Median (Rp/kg): Produsen < Pedagang Besar < Tradisional < Modern untuk semua komoditas.
Contoh cabai rawit merah: 33.000 → 42.000 → 51.200 → 90.200. Urutan rantai pasok masuk akal.

## 3. Kecocokan dengan tujuan analisis

| Pertanyaan | Data yang dipakai | Status | Catatan |
|---|---|---|---|
| Q1 Gejolak | Tradisional, 35 kota | ✅ Cukup | Modern hanya sebagai pembanding berbatasan (lihat §2.3) |
| Q2 Selisih antar kota | Pedagang besar di kota sumber, tradisional di kota tujuan | ✅ Lengkap | Semua 6 kota sumber & 4 kota tujuan terisi ≥ 851 dari 865 hari |
| Q3 Kota penentu arah | Tradisional mingguan, 35 kota | ✅ Cukup | 173 minggu |
| Q4 Pola Idul Fitri | Tradisional mingguan | ⚠️ Terbatas | Hanya 3 Idul Fitri; minggu Idul Fitri terisi harga sebelum libur (§2.1) |
| Q5 Tambahan harga | Produsen + pedagang besar + tradisional | ⚠️ Terbatas | Kota dengan ketiga level (nama sama): cabai keriting 6, cabai rawit 7, bawang merah 6, daging ayam 11, telur 7, **bawang putih 0** |
| Q6 Peringatan dini | Tradisional mingguan | ⚠️ Terbatas | Uji pada data baru hanya bisa untuk 2025 dan 2026 |

Data mingguan pasar tradisional (W-FRI, **setelah hari libur dikeluarkan**): 173 minggu, 35.445 kombinasi seri-minggu.
427 di antaranya (1,2%) punya < 3 hari pencacahan nyata (`minggu_tipis`). **Dua minggu tidak punya pencacahan nyata
sama sekali**, yaitu minggu Lebaran 2024-04-06 s/d 04-12 dan 2025-03-29 s/d 04-04. Untuk pola Idul Fitri (Q4),
minggu-minggu ini harus dianggap kosong, bukan "harga stabil".

## 4. Rencana preprocessing (Tahap 2–3)

1. **Parse** JSON → format panjang: `tanggal, jenis_pasar, provinsi, kota_id, kota, komoditas, harga`.
   Baris level 0 disimpan terpisah sebagai harga nasional. Baris level 1 dibuang.
2. **Standarisasi kota**: `strip()`, petakan nama → id lewat referensi, buang duplikat Surakarta id 787.
3. **Tandai hari libur** (`is_libur_isi`) → NaN untuk perhitungan harian.
4. **Tandai outlier dua tingkat** (§2.4): salah input (B/C) → NaN pada versi bersih; lonjakan tajam (A) → penanda saja.
5. **Isi celah ≤ 5 hari kerja** (forward-fill, `is_imputed`); celah lebih panjang tetap NaN.
6. **Tandai data usang** (`is_usang`, run datar ≥ 60 hari kerja).
7. **Tabel kualitas data** per kota × komoditas × jenis pasar: % kosong, % diisi, jumlah outlier, run datar terpanjang.
8. **Tes** (`tests/test_clean.py`): harga > 0, tidak ada duplikat kunci, tanggal hanya hari kerja,
   tidak ada nama kota tanpa id.
9. **Mingguan** (Tahap 3): median hari dengan data nyata per minggu W-FRI. Minggu dengan < 3 hari nyata → `minggu_tipis`.

## 5. Rekomendasi (detail di notebook §8)

1. **Surakarta pasar modern:** pakai id 36, buang id 787.
2. **Hari libur yang diisi harga sebelumnya:** tandai `is_libur_isi`, perlakukan sebagai kosong.
3. **Outlier dua tingkat** (§2.4) menggantikan aturan 5×MAD murni dari brief.
4. **Tambahan harga (Q5):** analisis utama hanya kota dengan ketiga level bernama sama (sesuai brief); analisis tambahan
   memasangkan kota ↔ kabupaten sentra di sekitarnya (mis. Kota Kediri ↔ Kab. Kediri, Kota Probolinggo ↔ Kab. Probolinggo,
   Kota Tasikmalaya ↔ Kab. Garut), berlabel `PERLU_VERIFIKASI`.

Status: rekomendasi, **menunggu konfirmasi user sebelum Tahap 2**.
