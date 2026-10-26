# Q5 — Tambahan harga di tiap tingkat rantai pasok

Dibuat otomatis oleh `python -m src.analysis.margin` pada 2026-10-26 15:08.
Median bulanan, Juli 2023 – Oktober 2026. Cakupan utama: kota dengan ketiga tingkat bernama sama; cakupan tambahan:
pasangan kota ↔ kabupaten sentra (`config.rantai_pasok`, PERLU_VERIFIKASI).

## Temuan (bahasa dashboard)
**Membeli langsung di tingkat produsen bisa 41% lebih murah daripada harga pasar untuk
cabai merah keriting** (median antar kota; harga produsen Rp 25.000/kg vs pasar Rp 40.750/kg).
Untuk telur ayam ras selisihnya hanya 10%.
Dibanding membeli di pedagang besar, membeli di produsen paling menghemat untuk cabai merah keriting, cabai rawit merah, daging ayam ras (tambahan harga di pedagang besar
29%, 16%, 15%); untuk bawang merah, telur ayam ras tambahan di pedagang besar hanya 9%, 3%.
Tindakan: jajaki pembelian langsung dari petani/pengepul di sentra untuk cabai merah keriting, cabai rawit merah, daging ayam ras; untuk bawang merah, telur ayam ras pedagang besar sudah dekat
dengan harga produsen.
Catatan: harga produsen jarang diperbarui, sehingga pada sebagian bulan tercatat lebih mahal daripada pedagang besar
(kolom terakhir). Angka ini perkiraan kasar.

## Per komoditas (median antar kota)
| Komoditas | Kota | Produsen | Pedagang besar | Pasar | Tambahan di pedagang besar | Tambahan di pasar | Lebih murah jika beli di produsen | Lebih murah jika beli di pedagang besar | Bulan produsen > pedagang besar |
|---|---|---|---|---|---|---|---|---|---|
| Cabai rawit merah | 13 | Rp 33.675 | Rp 40.062 | Rp 48.125 | 16% | 20% | 32% | 17% | 35% |
| Cabai merah keriting | 10 | Rp 25.000 | Rp 32.531 | Rp 40.750 | 29% | 29% | 41% | 22% | 21% |
| Bawang merah | 11 | Rp 24.000 | Rp 28.325 | Rp 37.312 | 9% | 30% | 31% | 23% | 30% |
| Daging ayam ras | 14 | Rp 27.462 | Rp 31.000 | Rp 35.725 | 15% | 13% | 21% | 12% | 31% |
| Telur ayam ras | 11 | Rp 24.350 | Rp 25.688 | Rp 27.481 | 3% | 7% | 10% | 7% | 33% |

## Per kota
| Komoditas | Kota | Harga produsen dari | Cakupan | Bulan | Tambahan di pedagang besar | Tambahan di pasar | Lebih murah di produsen | Bulan produsen > pedagang besar |
|---|---|---|---|---|---|---|---|---|
| Bawang merah | Kab. Jember | Kab. Jember | utama | 40 | 68% | 26% | 53% | 0% |
| Bawang merah | Kota Cirebon | Kab. Cirebon | tambahan* | 40 | 29% | 47% | 50% | 18% |
| Bawang merah | Kota Malang | Kab. Malang | tambahan* | 40 | 10% | 60% | 46% | 28% |
| Bawang merah | Kota Kediri | Kab. Nganjuk | tambahan* | 40 | 7% | 71% | 45% | 40% |
| Bawang merah | Kota Tegal | Kota Tegal | utama | 40 | 33% | 30% | 42% | 10% |
| Bawang merah | Kota Probolinggo | Kab. Probolinggo | tambahan* | 40 | 18% | 22% | 31% | 18% |
| Bawang merah | Kota Yogyakarta | Kota Yogyakarta | utama | 40 | 9% | 24% | 31% | 28% |
| Bawang merah | Kota Semarang | Kota Semarang | utama | 40 | 9% | 21% | 28% | 25% |
| Bawang merah | Kota Tasikmalaya | Kab. Garut | tambahan* | 40 | -7% | 39% | 24% | 52% |
| Bawang merah | Kab. Cilacap | Kab. Cilacap | utama | 40 | -9% | 31% | 17% | 62% |
| Bawang merah | Kota Sukabumi | Kota Sukabumi | utama | 40 | -0% | 19% | 15% | 50% |
| Cabai merah keriting | Kota Tegal | Kota Tegal | utama | 40 | 61% | 28% | 52% | 5% |
| Cabai merah keriting | Kota Semarang | Kota Semarang | utama | 40 | 44% | 30% | 45% | 22% |
| Cabai merah keriting | Kab. Banyumas | Kab. Banyumas | utama | 40 | 26% | 41% | 44% | 20% |
| Cabai merah keriting | Kota Tasikmalaya | Kab. Tasikmalaya | tambahan* | 40 | 31% | 34% | 42% | 22% |
| Cabai merah keriting | Kota Cirebon | Kab. Cirebon | tambahan* | 40 | 41% | 26% | 41% | 12% |
| Cabai merah keriting | Kota Yogyakarta | Kota Yogyakarta | utama | 40 | 35% | 23% | 40% | 15% |
| Cabai merah keriting | Kota Malang | Kota Malang | utama | 40 | 16% | 37% | 38% | 25% |
| Cabai merah keriting | Kota Kediri | Kab. Kediri | tambahan* | 40 | 19% | 33% | 36% | 32% |
| Cabai merah keriting | Kota Blitar | Kab. Blitar | tambahan* | 40 | 18% | 12% | 31% | 25% |
| Cabai merah keriting | Kota Sukabumi | Kota Sukabumi | utama | 40 | 14% | 15% | 24% | 30% |
| Cabai rawit merah | Kota Tegal | Kota Tegal | utama | 40 | 40% | 21% | 41% | 15% |
| Cabai rawit merah | Kota Semarang | Kota Semarang | utama | 40 | 33% | 16% | 40% | 28% |
| Cabai rawit merah | Kota Cirebon | Kab. Cirebon | tambahan* | 40 | 28% | 22% | 39% | 32% |
| Cabai rawit merah | Kota Tasikmalaya | Kab. Tasikmalaya | tambahan* | 40 | 14% | 37% | 38% | 38% |
| Cabai rawit merah | Kota Tasikmalaya | Kab. Garut | tambahan* | 40 | 16% | 37% | 36% | 35% |
| Cabai rawit merah | Kab. Banyumas | Kab. Banyumas | utama | 40 | 8% | 35% | 33% | 45% |
| Cabai rawit merah | Kota Yogyakarta | Kota Yogyakarta | utama | 40 | 13% | 20% | 32% | 38% |
| Cabai rawit merah | Kota Kediri | Kab. Kediri | tambahan* | 40 | 19% | 23% | 31% | 40% |
| Cabai rawit merah | Kota Malang | Kota Malang | utama | 40 | 19% | 20% | 28% | 38% |
| Cabai rawit merah | Kota Malang | Kab. Malang | tambahan* | 40 | 15% | 20% | 28% | 32% |
| Cabai rawit merah | Kota Blitar | Kab. Blitar | tambahan* | 40 | 15% | 15% | 28% | 42% |
| Cabai rawit merah | Kab. Jember | Kab. Jember | utama | 40 | 17% | 13% | 23% | 32% |
| Cabai rawit merah | Kota Sukabumi | Kota Sukabumi | utama | 40 | 13% | 13% | 22% | 38% |
| Daging ayam ras | Kota Cirebon | Kab. Cirebon | tambahan* | 40 | 38% | 14% | 37% | 0% |
| Daging ayam ras | Kota Madiun | Kota Madiun | utama | 40 | 42% | 7% | 35% | 0% |
| Daging ayam ras | Kota Blitar | Kab. Blitar | tambahan* | 40 | 56% | -2% | 34% | 0% |
| Daging ayam ras | Kota Yogyakarta | Kota Yogyakarta | utama | 40 | 27% | 18% | 33% | 0% |
| Daging ayam ras | Kota Tasikmalaya | Kota Tasikmalaya | utama | 40 | 12% | 34% | 32% | 5% |
| Daging ayam ras | Kota Tasikmalaya | Kab. Tasikmalaya | tambahan* | 40 | 12% | 34% | 32% | 2% |
| Daging ayam ras | Kota Bogor | Kota Bogor | utama | 40 | 18% | 11% | 24% | 28% |
| Daging ayam ras | Kota Malang | Kab. Malang | tambahan* | 40 | 22% | 1% | 19% | 0% |
| Daging ayam ras | Kab. Jember | Kab. Jember | utama | 40 | 20% | 0% | 16% | 5% |
| Daging ayam ras | Kab. Cilacap | Kab. Cilacap | utama | 40 | -34% | 61% | 6% | 100% |
| Daging ayam ras | Kota Semarang | Kota Semarang | utama | 40 | 3% | 2% | 6% | 12% |
| Daging ayam ras | Kota Tegal | Kota Tegal | utama | 40 | -37% | 62% | 3% | 98% |
| Daging ayam ras | Kota Sukabumi | Kota Sukabumi | utama | 40 | -10% | 12% | 2% | 85% |
| Daging ayam ras | Kab. Banyumas | Kab. Banyumas | utama | 40 | -35% | 52% | -1% | 100% |
| Telur ayam ras | Kota Blitar | Kab. Blitar | tambahan* | 40 | -0% | 17% | 15% | 50% |
| Telur ayam ras | Kab. Banyumas | Kab. Banyumas | utama | 40 | 7% | 6% | 12% | 18% |
| Telur ayam ras | Kota Malang | Kab. Malang | tambahan* | 40 | 5% | 9% | 12% | 32% |
| Telur ayam ras | Kota Cirebon | Kab. Cirebon | tambahan* | 40 | 5% | 7% | 11% | 25% |
| Telur ayam ras | Kota Yogyakarta | Kota Yogyakarta | utama | 40 | 3% | 8% | 11% | 32% |
| Telur ayam ras | Kota Tasikmalaya | Kab. Tasikmalaya | tambahan* | 40 | 8% | 4% | 10% | 15% |
| Telur ayam ras | Kota Semarang | Kota Semarang | utama | 40 | 1% | 9% | 8% | 40% |
| Telur ayam ras | Kota Sukabumi | Kota Sukabumi | utama | 40 | 3% | 5% | 8% | 35% |
| Telur ayam ras | Kab. Jember | Kab. Jember | utama | 40 | 5% | 2% | 7% | 18% |
| Telur ayam ras | Kab. Cilacap | Kab. Cilacap | utama | 40 | -1% | 9% | 6% | 55% |
| Telur ayam ras | Kota Bogor | Kota Bogor | utama | 40 | 2% | 5% | 5% | 40% |

\* tambahan = harga produsen diambil dari kabupaten sentra di sekitar kota (PERLU_VERIFIKASI).

## Pasar modern dibanding pasar tradisional (kota yang sama)
| Komoditas | Kota | Harga pasar modern vs pasar tradisional (median) |
|---|---|---|
| Cabai rawit merah | 21 | 69% |
| Cabai merah keriting | 20 | 82% |
| Bawang merah | 21 | 57% |
| Daging ayam ras | 22 | 20% |
| Telur ayam ras | 23 | -1% |

Pasar modern jauh lebih mahal daripada pasar tradisional untuk cabai rawit merah, cabai merah keriting, bawang merah, daging ayam ras; untuk telur ayam ras harganya hampir sama. Pasar modern bukan sumber pembelian yang lebih murah.

## Batasan
- Harga produsen di PIHPS jarang diperbarui (±96% hari tidak berubah); dipakai median bulanan, tetapi tetap bisa usang.
- Cakupan kota terbatas (6–11 kota per komoditas); bawang putih tidak punya data produsen di Jawa.
- Harga produsen = harga di tingkat petani/peternak, belum termasuk biaya mengumpulkan & mengangkut dari banyak petani.

## File
- Tabel: `reports/tables/q5_per_komoditas.csv`, `q5_per_kota.csv`, `q5_bulanan.csv`, `q5_tren.csv`
- Grafik: `reports/figures/q5_tambahan_harga_per_tingkat.png`, `reports/figures/q5_tren_tambahan_harga.png`
