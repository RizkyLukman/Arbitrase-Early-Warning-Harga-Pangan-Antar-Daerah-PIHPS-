# Ongkos angkut per rute — ASUMSI, bukan data

Dibuat otomatis oleh `python -m src.logistics` pada 2026-10-26 01:10. Jangan diedit manual.
Semua asumsi & sumbernya: `config/biaya_logistik.yaml`. Jarak jalan: OSRM / OpenStreetMap (`data/reference/jarak_rute.csv`).

## Parameter utama
- Truk CDD box 5.000 kg, tarif **Rp 6.000/km** (batas bawah tarif pasar Rp 6.000–19.000/km).
- Tol **Rp 1.851/km** (terbesar dari rute referensi: jakarta_surabaya_aptrindo: Rp 1.851/km; cikampek_kalikangkung_2025: Rp 1.774/km), seluruh jarak dianggap lewat tol.
- Muatan efektif: cabai 3.000 kg, bawang 4.500 kg, telur 4.000 kg, daging ayam 3.500 kg (truk berpendingin, tarif +40%).
- Bongkar-muat Rp 150/kg; susut cabai 5%, bawang merah 3%, telur 2%, ayam 1% dari harga di sumber.
- Harga sumber = median harga pedagang besar 52 minggu terakhir.

## Hasil per rute
| sumber | tujuan | komoditas | jarak (km) | ongkos angkut/kg | susut/kg | total x1 | total x1,5 | ongkos / MPP | cek MPP |
|---|---|---|---|---|---|---|---|---|---|
| Kota Tasikmalaya | Kota Jakarta Pusat | Cabai Merah Keriting | 262 | Rp 835 | Rp 2.000 | Rp 2.835 | Rp 4.253 | 5% | ok |
| Kota Tasikmalaya | Kota Bandung | Cabai Merah Keriting | 108 | Rp 434 | Rp 2.000 | Rp 2.434 | Rp 3.651 | 3% | ok |
| Kota Tasikmalaya | Kota Semarang | Cabai Merah Keriting | 327 | Rp 1.006 | Rp 2.000 | Rp 3.006 | Rp 4.509 | 6% | ok |
| Kota Tasikmalaya | Kota Surabaya | Cabai Merah Keriting | 621 | Rp 1.775 | Rp 2.000 | Rp 3.775 | Rp 5.662 | 10% | ok |
| Kota Tegal | Kota Jakarta Pusat | Bawang Merah Ukuran Sedang | 286 | Rp 649 | Rp 1.035 | Rp 1.684 | Rp 2.527 | 5% | ok |
| Kota Tegal | Kota Bandung | Bawang Merah Ukuran Sedang | 203 | Rp 504 | Rp 1.035 | Rp 1.539 | Rp 2.308 | 4% | ok |
| Kota Tegal | Kota Semarang | Bawang Merah Ukuran Sedang | 154 | Rp 419 | Rp 1.035 | Rp 1.454 | Rp 2.181 | 3% | ok |
| Kota Tegal | Kota Surabaya | Bawang Merah Ukuran Sedang | 463 | Rp 958 | Rp 1.035 | Rp 1.993 | Rp 2.990 | 7% | ok |
| Kota Kediri | Kota Jakarta Pusat | Cabai Rawit Merah | 688 | Rp 1.951 | Rp 2.612 | Rp 4.563 | Rp 6.845 | 9% | ok |
| Kota Kediri | Kota Bandung | Cabai Rawit Merah | 606 | Rp 1.735 | Rp 2.612 | Rp 4.347 | Rp 6.521 | 8% | ok |
| Kota Kediri | Kota Semarang | Cabai Rawit Merah | 257 | Rp 823 | Rp 2.612 | Rp 3.436 | Rp 5.153 | 4% | ok |
| Kota Kediri | Kota Surabaya | Cabai Rawit Merah | 119 | Rp 462 | Rp 2.612 | Rp 3.074 | Rp 4.612 | 2% | ok |
| Kota Kediri | Kota Jakarta Pusat | Telur Ayam Ras Segar | 688 | Rp 1.501 | Rp 474 | Rp 1.974 | Rp 2.961 | 31% | ok |
| Kota Kediri | Kota Bandung | Telur Ayam Ras Segar | 606 | Rp 1.338 | Rp 474 | Rp 1.812 | Rp 2.718 | 28% | ok |
| Kota Kediri | Kota Semarang | Telur Ayam Ras Segar | 257 | Rp 655 | Rp 474 | Rp 1.128 | Rp 1.692 | 14% | ok |
| Kota Kediri | Kota Surabaya | Telur Ayam Ras Segar | 119 | Rp 384 | Rp 474 | Rp 857 | Rp 1.286 | 8% | ok |
| Kota Kediri | Kota Jakarta Pusat | Daging Ayam Ras Segar | 688 | Rp 2.165 | Rp 355 | Rp 2.520 | Rp 3.780 | 25% | ok |
| Kota Kediri | Kota Bandung | Daging Ayam Ras Segar | 606 | Rp 1.923 | Rp 355 | Rp 2.278 | Rp 3.418 | 22% | ok |
| Kota Kediri | Kota Semarang | Daging Ayam Ras Segar | 257 | Rp 903 | Rp 355 | Rp 1.258 | Rp 1.887 | 10% | ok |
| Kota Kediri | Kota Surabaya | Daging Ayam Ras Segar | 119 | Rp 499 | Rp 355 | Rp 854 | Rp 1.281 | 6% | ok |
| Kab. Jember | Kota Jakarta Pusat | Cabai Rawit Merah | 948 | Rp 2.631 | Rp 2.650 | Rp 5.281 | Rp 7.922 | 12% | ok |
| Kab. Jember | Kota Bandung | Cabai Rawit Merah | 866 | Rp 2.415 | Rp 2.650 | Rp 5.065 | Rp 7.597 | 11% | ok |
| Kab. Jember | Kota Semarang | Cabai Rawit Merah | 514 | Rp 1.494 | Rp 2.650 | Rp 4.144 | Rp 6.216 | 7% | ok |
| Kab. Jember | Kota Surabaya | Cabai Rawit Merah | 206 | Rp 688 | Rp 2.650 | Rp 3.338 | Rp 5.007 | 3% | ok |
| Kab. Banyuwangi | Kota Jakarta Pusat | Cabai Rawit Merah | 1.016 | Rp 2.809 | Rp 2.638 | Rp 5.446 | Rp 8.169 | 12% | ok |
| Kab. Banyuwangi | Kota Bandung | Cabai Rawit Merah | 933 | Rp 2.593 | Rp 2.638 | Rp 5.230 | Rp 7.845 | 11% | ok |
| Kab. Banyuwangi | Kota Semarang | Cabai Rawit Merah | 582 | Rp 1.672 | Rp 2.638 | Rp 4.309 | Rp 6.464 | 7% | ok |
| Kab. Banyuwangi | Kota Surabaya | Cabai Rawit Merah | 273 | Rp 865 | Rp 2.638 | Rp 3.503 | Rp 5.254 | 4% | ok |
| Kota Probolinggo | Kota Jakarta Pusat | Bawang Merah Ukuran Sedang | 849 | Rp 1.631 | Rp 900 | Rp 2.531 | Rp 3.796 | 14% | ok |
| Kota Probolinggo | Kota Bandung | Bawang Merah Ukuran Sedang | 766 | Rp 1.487 | Rp 900 | Rp 2.387 | Rp 3.580 | 13% | ok |
| Kota Probolinggo | Kota Semarang | Bawang Merah Ukuran Sedang | 414 | Rp 873 | Rp 900 | Rp 1.773 | Rp 2.659 | 8% | ok |
| Kota Probolinggo | Kota Surabaya | Bawang Merah Ukuran Sedang | 102 | Rp 328 | Rp 900 | Rp 1.228 | Rp 1.842 | 3% | ok |

`ongkos / MPP` = ongkos angkut (tanpa susut) dibanding seluruh margin perdagangan & pengangkutan BPS dalam rupiah
(MPP% × harga sumber). `ok` ≤ 50%, `tinggi` > 50%,
`melebihi` > 100% (asumsi tidak masuk akal).

## Batasan
- Tarif truk & tol berasal dari halaman komersial dan berita, bukan tarif resmi; sebagian bertanggal lama.
- Muatan efektif, premi truk berpendingin, bongkar-muat, dan susut adalah asumsi analis tanpa sumber angka.
- Ketidakpastian ditangani dengan uji sensitivitas ×0.5, ×1, ×1.5, ×2;
  rekomendasi rute hanya valid jika tetap untung pada ×1.5.
