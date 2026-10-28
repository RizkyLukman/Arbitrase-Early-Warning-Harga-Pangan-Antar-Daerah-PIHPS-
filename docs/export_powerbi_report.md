# Export Power BI (Tahap 5)

Dibuat otomatis oleh `python -m src.export_powerbi` pada 2026-10-29 02:21. Jangan diedit manual.
Folder: `data/processed/` (parquet, csv). Kunci & relasi: lihat docstring `src/export_powerbi.py`.

## Ringkasan
- Data per **2026-10-23** (diambil 2026-10-25); minggu terakhir **2026-10-23**.
- 19 tabel, total 654,587 baris. Ukuran terbesar: 33.4 MB.
- Pemeriksaan integritas kunci: **OK**.
- Ongkos angkut di `fact_spread`/`dim_rute` = **perkiraan, bukan data**; komponen disimpan terpisah (ongkos tetap + susut)
  supaya untung per kg bisa dihitung ulang di Power BI dengan what-if parameter.
- Peringatan dini (`fact_alert`) diekspor sebagai **informasi**, bukan pemicu pembelian (Q6: benar 1,2 dari 10).

## Tabel
| Tabel | Baris | Kolom | Parquet (MB) | CSV (MB) | Isi |
|---|---|---|---|---|---|
| `dim_tanggal` | 1,209 | 17 | 0.03 | 0.12 | kalender harian + minggu (W-FRI), minggu ke Idulfitri, hari besar |
| `dim_kota` | 62 | 14 | 0.01 | 0.01 | kota: provinsi, koordinat, peran (tujuan / sumber / penentu arah) |
| `dim_komoditas` | 6 | 20 | 0.01 | 0.00 | komoditas: nama dashboard, satuan, ringkasan gejolak, pola Idulfitri, hemat beli di produsen |
| `dim_jenis_pasar` | 4 | 3 | 0.00 | 0.00 | 4 jenis pasar + catatan cara pencatatan |
| `dim_rute` | 32 | 27 | 0.02 | 0.01 | rute pindah stok: jarak, ongkos (perkiraan), status layak, minggu untung dari 10 |
| `fact_rute_sensitivitas` | 128 | 6 | 0.01 | 0.01 | per rute × pengali ongkos 0,5–2: porsi minggu untung, median untung |
| `fact_spread` | 5,472 | 13 | 0.18 | 0.62 | per minggu × rute: selisih harga, ongkos angkut (perkiraan), susut, untung per kg (×1, ×1,5, ×2) |
| `fact_harga` | 522,207 | 11 | 1.32 | 33.36 | harga harian per kota × komoditas × jenis pasar + penanda kualitas |
| `fact_harga_mingguan` | 105,010 | 20 | 4.82 | 21.39 | harga mingguan + perubahan (WoW, 4 minggu, YoY), gejolak, selisih vs nasional |
| `fact_gejolak` | 207 | 11 | 0.02 | 0.03 | gejolak harga per kota × komoditas (pasar tradisional) |
| `fact_penentu_arah` | 207 | 9 | 0.01 | 0.01 | peran kota (penentu arah / pengikut / netral) per komoditas, jeda, kekuatan hubungan |
| `fact_pantau_kota_tujuan` | 56 | 6 | 0.00 | 0.00 | kota yang perlu dipantau untuk tiap kota tujuan |
| `fact_pola_idul_fitri` | 234 | 5 | 0.01 | 0.01 | kenaikan vs harga normal per minggu ke Idulfitri × tahun × komoditas |
| `fact_margin` | 59 | 14 | 0.01 | 0.01 | tambahan harga produsen → pedagang besar → pasar per kota × komoditas |
| `fact_uji_peringatan` | 5 | 9 | 0.01 | 0.00 | hasil uji peringatan dini pada data lama (benar/tertangkap dari 10, lebih awal) |
| `fact_alert` | 19,665 | 11 | 0.05 | 2.27 | per minggu × kota × komoditas: peringatan, sinyal, awal & masa lonjakan (tahun uji + 8 minggu terkini), alasan |
| `fact_tindakan` | 13 | 12 | 0.01 | 0.00 | daftar tindakan per komoditas minggu terakhir (src/insights.py), dengan angka asal |
| `fact_hal` | 3 | 8 | 0.01 | 0.00 | "Tiga hal yang perlu diketahui minggu ini" (src/insights.py), dengan angka asal |
| `dim_info` | 8 | 3 | 0.00 | 0.00 | tanggal data, tanggal pengambilan, sumber, catatan asumsi (untuk catatan kaki dashboard) |

## Relasi (fakta → dimensi)
- `fact_harga`: `tanggal_key` → `dim_tanggal`, `jenis_pasar_key` → `dim_jenis_pasar`, `kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `fact_harga_mingguan`: `minggu_key` → `dim_tanggal`, `jenis_pasar_key` → `dim_jenis_pasar`, `kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `fact_spread`: `minggu_key` → `dim_tanggal`, `rute_key` → `dim_rute`
- `fact_rute_sensitivitas`: `rute_key` → `dim_rute`
- `fact_alert`: `minggu_key` → `dim_tanggal`, `kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `fact_tindakan`: `minggu_key` → `dim_tanggal`, `komoditas_key` → `dim_komoditas`
- `fact_hal`: `minggu_key` → `dim_tanggal`, `komoditas_key` → `dim_komoditas`
- `fact_gejolak`: `kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `fact_penentu_arah`: `kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `fact_pantau_kota_tujuan`: `kota_tujuan_key` → `dim_kota`, `pantau_kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `fact_pola_idul_fitri`: `komoditas_key` → `dim_komoditas`
- `fact_margin`: `kota_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`
- `dim_rute`: `kota_sumber_key` → `dim_kota`, `kota_tujuan_key` → `dim_kota`, `komoditas_key` → `dim_komoditas`

`minggu_key` berelasi ke `dim_tanggal.tanggal_key` (hari Jumat minggu itu); di Power BI buat relasi kedua yang tidak aktif
atau tabel `dim_minggu` = `dim_tanggal` yang difilter `tanggal_key = minggu_key`.

## File yang melebihi 10 MB
- `fact_harga`: parquet 1.3 MB, csv 33.4 MB
- `fact_harga_mingguan`: parquet 4.8 MB, csv 21.4 MB

## Kalimat dashboard minggu terakhir (fact_hal)
1. Cabai rawit merah di Kota Kediri masih Rp 32.823/kg lebih murah daripada di Kota Bandung setelah ongkos angkut ×1,5 (perkiraan), sudah 33 minggu berturut-turut. Tindakan: pertimbangkan memindahkan stok selama selisih ini bertahan.
2. Cabai merah keriting di Kota Tasikmalaya masih Rp 27.324/kg lebih murah daripada di Kota Bandung setelah ongkos angkut ×1,5 (perkiraan), sudah 5 minggu berturut-turut. Tindakan: pertimbangkan memindahkan stok selama selisih ini bertahan.
3. Harga cabai merah keriting di kota tujuan Rp 69.575/kg, naik 37% dibanding 4 minggu lalu dan 20% di bawah rata-rata nasional. Artinya pasokan sedang ketat. Tindakan: beli secukupnya dan pantau setiap minggu.
