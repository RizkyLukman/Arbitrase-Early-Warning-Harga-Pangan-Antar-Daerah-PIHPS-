# Tahap 0 — Verifikasi akses data PIHPS

Tanggal pengecekan: **2026-10-25**. Semua temuan di bawah berasal dari uji langsung ke situs, bukan asumsi.

## Kesimpulan

**Data bisa diakses.** PIHPS menyediakan endpoint JSON publik yang bisa dipanggil dari Python (`requests`)
tanpa login, cookie, atau token. Tidak perlu Playwright.

## Endpoint

Base URL: `https://www.bi.go.id/hargapangan/WebSite/TabelHarga/`. Semua memakai method `GET`.
Respons berupa JSON `{"data": [...]}`.

### Referensi

| Endpoint | Parameter | Isi |
|---|---|---|
| `GetRefPriceType` | — | Jenis pasar: 1 Pasar Tradisional, 2 Pasar Modern, 3 Pedagang Besar, 4 Produsen |
| `GetRefCommodityAndCategory` | — | Kategori (`cat_1`…`cat_10`) dan komoditas (`com_1`…`com_21`) + satuan |
| `GetRefProvince` | — | 34 provinsi (id + nama) |
| `GetRefRegency` | `price_type_id`, `ref_prov_id` | Kota/kab per jenis pasar. **`ref_prov_id` wajib diisi**, kalau kosong hasilnya kosong |
| `GetRefMarket` | `ref_regency_id`, `price_type_id` | Daftar pasar per kota |

### Data harga

**A. `GetGridDataKomoditas`: dipakai untuk akuisisi.** Satu komoditas, semua kota sekaligus.

| Parameter | Nilai |
|---|---|
| `price_type_id` | 1–4 |
| `comcat_id` | **satu** id, mis. `com_14` (halaman hanya mengirim pilihan pertama) |
| `province_id` | kosong = semua; bisa dipisah koma, mis. `11,12,13,14,15,16` |
| `regency_id` | kosong |
| `showKota` | `true` → tampilkan baris per kota |
| `showPasar` | `false` |
| `tipe_laporan` | 1 Harian, 4 Mingguan, 5 Bulanan (6 = grafik). Kita pakai **1** dan agregasi sendiri |
| `start_date`, `end_date` | `YYYY-MM-DD` |

Bentuk respons (format lebar, satu kolom per tanggal):

```json
{"data":[
  {"no":"I","name":"Semua Provinsi","level":0,"01/09/2026":"71,400", ...},
  {"no":"II","name":"Jawa Barat","level":1, ...},
  {"no":1,"name":"Kota Bandung","level":2,"01/09/2026":"51,250", ...}
]}
```

- `level` 0 = nasional, 1 = provinsi, 2 = kota/kab.
- **Baris tidak membawa id kota**, hanya nama. Nama perlu dipetakan ke id lewat `GetRefRegency`.
- Beberapa nama punya spasi di ujung (`"Kab. Boyolali "`, `"Cabai Merah Keriting "`) → perlu `strip()`.

**B. `GetGridDataDaerah`: hanya untuk cek silang.** Parameter `comcat_id`, `province_id`, `regency_id`, `market_id`
menerima banyak id dipisah koma, **tetapi beberapa kota yang dipilih digabung menjadi satu rata-rata**, bukan
dipecah per kota. Tidak cocok untuk akuisisi per kota.

## Format nilai

- Tanggal di kolom: `DD/MM/YYYY`. Hanya hari kerja (Senin–Jumat), sesuai FAQ.
- Harga berupa string dengan **koma sebagai pemisah ribuan**: `"58,750"` = Rp 58.750.
  *(Berbeda dari brief, yang menyebut titik. Parser di `clean.py` harus mengikuti koma.)*
- Data kosong ditulis `"-"`.

## Batas rentang tanggal & waktu respons

| Uji | Hasil |
|---|---|
| 1 kota, 1 komoditas, 1 bulan | 0,3–0,8 detik |
| 1 kota, 1 komoditas, 1 tahun | 4 detik |
| 1 kota, 1 komoditas, 3 tahun | 37 detik (berhasil) |
| Semua kota, 1 komoditas, 1 bulan | 2–3 detik, ~70 KB |
| Semua kota, 1 komoditas, 3 bulan | 19 detik |
| Semua kota, 1 komoditas, 1 tahun | **timeout > 180 detik** |

Tidak ada batas tanggal di form. Batas praktisnya waktu respons server.
**Keputusan: potong per bulan** untuk endpoint semua kota.

## Rentang historis

| Periode | Data |
|---|---|
| Jan 2017 | kosong |
| Jun 2018 | ada, 91 kota, ~20% sel kosong |
| Jun 2019 | ada, 94 kota, ~15% kosong |
| Jun 2021 | ada, 99 kota, ~4% kosong |
| Sep 2026 | ada, 107 kota (cabai merah keriting) |

Jumlah kota bertambah dari waktu ke waktu. Kota baru punya riwayat lebih pendek, jadi ini perlu dicatat di tabel kualitas data.
Kualitas data di sekitar migrasi situs (2023) belum dicek; itu dilakukan di Tahap 2.

## Cakupan per jenis pasar (cabai merah keriting / komoditas lain, Sep 2026, seluruh Indonesia)

| Jenis pasar | Jumlah kota/kab |
|---|---|
| Pasar Tradisional | 107 |
| Pedagang Besar | 70 |
| Produsen | 44–75 tergantung komoditas (bawang merah 44, cabai rawit 62, telur 75) |

Produsen dicatat di tingkat **kabupaten sentra** (mis. Kab. Garut, Kab. Nganjuk, Kab. Kediri, Kab. Probolinggo),
bukan selalu di kota yang sama dengan pasar tradisional. Contoh: produsen cabai rawit tidak ada di *Kota* Kediri,
melainkan di *Kab.* Kediri. Analisis margin perlu memetakan kota ↔ kabupaten sentra di sekitarnya.

## Ketersediaan 10 kota usulan (hari kerja berisi data, Sep 2026, maks 22)

| Komoditas | Jenis pasar | Jakarta Pusat | Bandung | Semarang | Surabaya | Tasikmalaya | Tegal | Kediri | Jember | Banyuwangi | Probolinggo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Cabai merah keriting | Tradisional / Pedagang Besar | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | **–** | **–** |
| Cabai rawit merah | Tradisional / Pedagang Besar | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |
| Bawang merah | Tradisional / Pedagang Besar | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |
| Bawang putih | Tradisional / Pedagang Besar | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |
| Daging ayam ras | Tradisional / Pedagang Besar | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |
| Telur ayam ras | Tradisional / Pedagang Besar | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 22 |

`–` = kota tidak muncul untuk komoditas itu (bukan error). Banyuwangi dan Probolinggo diusulkan sebagai sumber
cabai rawit dan bawang merah, jadi ini tidak mengganggu.

ID kota: Jakarta Pusat 34, Bandung 27, Semarang 35, Surabaya 42, Tasikmalaya (Kota) 29, Tegal 37, Kediri (Kota) 44,
Jember (Kab.) 45, Banyuwangi (Kab.) 46, Probolinggo (Kota) 48.

## Tombol Download

Tombol **Download** hanya memanggil `exportToExcel` milik komponen tabel DevExtreme di browser. Artinya, ia mengekspor
tabel yang sedang tampil. Tidak ada endpoint file terpisah. Akuisisi cukup lewat endpoint JSON.

## Estimasi beban akuisisi

Potongan per bulan, semua kota, jeda 2 detik → ~5 detik per request.

| Skenario | Request | Perkiraan waktu |
|---|---|---|
| 6 komoditas × 4 jenis pasar × 40 bulan (Jul 2023–Okt 2026) | 960 | ~1,5 jam |
| 6 komoditas × 4 jenis pasar × 70 bulan (Jan 2021–Okt 2026) | 1.680 | ~2,5 jam |

Cache per file membuat proses bisa dilanjutkan jika terputus.

## Etika akses

- Jeda ≥ 2 detik antar request, satu koneksi (tanpa paralel).
- User-Agent jelas: `PIHPS-portfolio-research/0.1 (personal data-analysis portfolio project)`.
- Retry dengan backoff untuk timeout.
- Ambil data sampai H-2 karena data bisa direvisi sampai hari berikutnya.
