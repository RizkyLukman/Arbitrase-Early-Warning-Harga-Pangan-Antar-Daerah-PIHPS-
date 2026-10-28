# Audit dashboard Excel

Dibuat otomatis oleh `python -m src.audit_dashboard` pada 2026-10-29 07:17. Nilai acuan dihitung langsung dari
`data/processed/` (minggu terakhir `20261023`), lalu dibandingkan dengan nilai sel bernama di workbook.

## Cek workbook `excel/Dashboard_pangan.xlsx`
- Nilai sel bernama cocok dengan acuan: **20 dari 20**
- Sel rumus bererror: **0**
- Sel rumus belum dihitung (jalankan `python -m src.recalc_excel`): 0
- Teks dengan istilah teknis terlarang: **0**

| nama | sel | di_dashboard | acuan | cocok | keterangan |
|---|---|---|---|---|---|
| kpi_beli_awal | Ringkasan!$C$6 | 0 | 0 | ✅ | komoditas perlu dibeli lebih awal |
| kpi_rute_untung | Ringkasan!$I$6 | 23 | 23 | ✅ | rute layak pada ongkos ×1.5 |
| kpi_kenaikan_tercepat | Ringkasan!$O$6 | 0.3689566155505896 | 0.36895661555058956 | ✅ | kenaikan 4 minggu Cabai merah keriting |
| kpi_peringatan_aktif | Ringkasan!$U$6 | 0 | 0 | ✅ | kota dengan peringatan aktif |
| kpi_selisih_nasional_rawit | Ringkasan!$AC$6 | -0.2728813559322034 | -0.2728813559322034 | ✅ | cabai rawit kota tujuan vs nasional |
| pilih_komoditas | Gejolak harga!$U$2 | Cabai rawit merah | Cabai rawit merah | ✅ | pilihan awal dropdown |
| kpi_kota_paling_tidak_stabil | Gejolak harga!$AG$12 | Kota Blitar | Kota Blitar | ✅ | kota paling tidak stabil, cabai rawit (rata-rata perubahan) |
| kpi_gejolak_kota_teratas | Gejolak harga!$AH$12 | 0.1767836230318658 | 0.17678362303186576 | ✅ | rata-rata perubahan per minggu kota teratas, cabai rawit |
| pengali_ongkos | Pindah stok!$AC$10 | 1.5 | 1.5 | ✅ | pengali ongkos awal |
| tambahan_ongkos | Pindah stok!$U$3 | 0 | 0 | ✅ | tambahan ongkos awal |
| kpi_rute_untung_dinamis | Pindah stok!$C$6 | 23 | 23 | ✅ | rute untung (dinamis) pada ×1.5 |
| kpi_rute_aman | Pindah stok!$I$6 | 9 | 9 | ✅ | rute aman |
| kpi_rute_margin_positif | Pindah stok!$AC$6 | 27 | 27 | ✅ | rute margin positif pada ×1.5 |
| kpi_margin_rute_terbaik | Pindah stok!$AC$7 | 21048.19 | 21048.190000000002 | ✅ | margin median rute terbaik |
| kpi_benar_dari_10 | Peringatan dini!$AC$5 | 1.2 | 1.2 | ✅ | peringatan benar dari 10 |
| kpi_tertangkap_dari_10 | Peringatan dini!$AC$6 | 2.4 | 2.4 | ✅ | lonjakan tertangkap dari 10 |
| kpi_lebih_awal | Peringatan dini!$AC$7 | 5.8 | 5.8 | ✅ | lebih awal (minggu) |
| kpi_benar_tahun_lalu | Peringatan dini!$AC$8 | 2.2 | 2.2 | ✅ | pola tahun lalu benar dari 10 |
| kpi_bawang_merah_mulai_naik | d_komoditas!$G$4 | -4 | -4 | ✅ | bawang merah mulai naik (minggu) |
| kpi_hemat_produsen_maks | Rantai pasok!$AC$5 | 0.4065021165629685 | 0.40650211656296853 | ✅ | hemat beli di produsen terbesar |

## Nilai acuan — Ringkasan
- Komoditas perlu dibeli lebih awal: **0**
- Rute untung (ongkos ×1.5): **23 dari 32**; rute aman: **9**; untung minggu ini: **28**
- Kenaikan tercepat: **Cabai merah keriting +37%** (Rp 69,575/kg)
- Cabai rawit kota tujuan vs nasional: **-27%**
- Peringatan aktif: **0 kota**

| nama | harga | perubahan_4m | harga_nasional | selisih_nasional_pct |
|---|---|---|---|---|
| Daging ayam ras | 38775.0 | -0.0532 | 40350.0 | -0.039 |
| Telur ayam ras | 25350.0 | -0.0362 | 29650.0 | -0.145 |
| Bawang merah | 33125.0 | 0.0217 | 37150.0 | -0.1083 |
| Bawang putih | 39000.0 | 0.0 | 38500.0 | 0.013 |
| Cabai merah keriting | 69575.0 | 0.369 | 87100.0 | -0.2012 |
| Cabai rawit merah | 75075.0 | 0.0188 | 103250.0 | -0.2729 |

- Tindakan (fact_tindakan):

| komoditas_key | prioritas | tindakan | alasan_singkat |
|---|---|---|---|
| 7 | 2 | Pindahkan stok Kota Kediri → Kota Bandung | daging ayam ras: untung Rp 4.840/kg setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 58 minggu berturut-turut; untung hanya jika dijual dengan harga eceran |
| 7 | 4 | Jajaki beli langsung di produsen | daging ayam ras: 21% lebih murah daripada harga pasar (12% dibanding pedagang besar); harga produsen jarang diperbarui, jadi angka ini perkiraan kasar |
| 10 | 2 | Pindahkan stok Kota Kediri → Kota Surabaya | telur ayam ras: untung Rp 3.052/kg setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 27 minggu berturut-turut; untung hanya jika dijual dengan harga eceran |
| 11 | 2 | Pindahkan stok Kota Tegal → Kota Jakarta Pusat | bawang merah: untung Rp 12.496/kg setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 81 minggu berturut-turut |
| 11 | 4 | Jajaki beli langsung di produsen | bawang merah: 31% lebih murah daripada harga pasar (23% dibanding pedagang besar); harga produsen jarang diperbarui, jadi angka ini perkiraan kasar |
| 12 | 7 | Beli rutin | bawang putih: tidak ada sinyal khusus minggu ini; harga di kota tujuan Rp 39.000/kg, 1% di atas rata-rata nasional |
| 14 | 2 | Pindahkan stok Kota Tasikmalaya → Kota Bandung | cabai merah keriting: untung Rp 27.324/kg setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 5 minggu berturut-turut; untung hanya jika dijual dengan harga eceran |
| 14 | 3 | Pantau ketat, harga sedang naik cepat | cabai merah keriting di kota tujuan Rp 69.575/kg, naik 37% dibanding 4 minggu lalu; beli secukupnya |
| 14 | 4 | Jajaki beli langsung di produsen | cabai merah keriting: 41% lebih murah daripada harga pasar (22% dibanding pedagang besar); harga produsen jarang diperbarui, jadi angka ini perkiraan kasar |
| 14 | 6 | Pantau setiap minggu | cabai merah keriting: komoditas paling tidak stabil ke-2, harganya berubah rata-rata 10% per minggu; siapkan stok penyangga |
| 16 | 2 | Pindahkan stok Kota Kediri → Kota Bandung | cabai rawit merah: untung Rp 32.823/kg setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 33 minggu berturut-turut |
| 16 | 4 | Jajaki beli langsung di produsen | cabai rawit merah: 32% lebih murah daripada harga pasar (17% dibanding pedagang besar); harga produsen jarang diperbarui, jadi angka ini perkiraan kasar |
| 16 | 6 | Pantau setiap minggu | cabai rawit merah: komoditas paling tidak stabil ke-1, harganya berubah rata-rata 13% per minggu; siapkan stok penyangga |

- Tiga hal (fact_hal):
  1. Cabai rawit merah di Kota Kediri masih Rp 32.823/kg lebih murah daripada di Kota Bandung setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 33 minggu berturut-turut. Tindakan: pertimbangkan memindahkan stok selama selisih ini bertahan.
  2. Cabai merah keriting di Kota Tasikmalaya masih Rp 27.324/kg lebih murah daripada di Kota Bandung setelah dikurangi ongkos kirim ×1,5 (perkiraan kami), sudah 5 minggu berturut-turut. Tindakan: pertimbangkan memindahkan stok selama selisih ini bertahan.
  3. Harga cabai merah keriting di kota tujuan Rp 69.575/kg, naik 37% dibanding 4 minggu lalu dan 20% di bawah rata-rata nasional. Artinya pasokan sedang ketat. Tindakan: beli secukupnya dan pantau setiap minggu.

## Nilai acuan — Peluang pindah stok
- Rute dengan median margin > 0 per pengali: ×0.5: 30 (layak 29) · ×1: 28 (layak 28) · ×1.5: 27 (layak 23) · ×2: 22 (layak 22)
- Rute terbaik: **Cabai rawit merah: Kota Kediri → Kota Bandung** — margin median Rp 21,048/kg, selisih Rp 26,450,
  untung 9.7 dari 10 minggu, 33 minggu berturut-turut, jika jual ke pedagang besar Rp 3,461

| nama_rute | median_selisih_harga_rp_per_kg | median_ongkos_rp_per_kg | median_untung_rp_per_kg | minggu_untung_dari_10 | status |
|---|---|---|---|---|---|
| Cabai rawit merah: Kota Kediri → Kota Bandung | 26450.0 | 5414.0 | 21048.0 | 10.0 | layak, juga jika dijual ke pedagang besar (paling aman) |
| Cabai rawit merah: Kab. Jember → Kota Bandung | 27200.0 | 6435.0 | 20853.0 | 10.0 | layak, juga jika dijual ke pedagang besar (paling aman) |
| Cabai rawit merah: Kota Kediri → Kota Jakarta Pusat | 26000.0 | 5739.0 | 20174.0 | 10.0 | layak, juga jika dijual ke pedagang besar (paling aman) |
| Cabai rawit merah: Kab. Jember → Kota Jakarta Pusat | 26150.0 | 6760.0 | 19378.0 | 10.0 | layak, juga jika dijual ke pedagang besar (paling aman) |
| Cabai merah keriting: Kota Tasikmalaya → Kota Bandung | 20500.0 | 3538.0 | 17099.0 | 10.0 | layak hanya jika dijual dengan harga eceran |
| Cabai rawit merah: Kab. Banyuwangi → Kota Bandung | 22750.0 | 6889.0 | 15411.0 | 9.0 | layak hanya jika dijual dengan harga eceran |
| Cabai rawit merah: Kab. Banyuwangi → Kota Jakarta Pusat | 22575.0 | 7213.0 | 14887.0 | 10.0 | layak hanya jika dijual dengan harga eceran |
| Bawang merah: Kota Tegal → Kota Jakarta Pusat | 15000.0 | 2324.0 | 12791.0 | 10.0 | layak, juga jika dijual ke pedagang besar (paling aman) |
| Bawang merah: Kota Probolinggo → Kota Jakarta Pusat | 16000.0 | 3706.0 | 12444.0 | 10.0 | layak hanya jika dijual dengan harga eceran |
| Bawang merah: Kota Tegal → Kota Bandung | 13750.0 | 2105.0 | 11665.0 | 10.0 | layak, juga jika dijual ke pedagang besar (paling aman) |

## Nilai acuan — Gejolak
| gejolak | perubahan | nama |
|---|---|---|
| 0.035 | 0.0256 | Daging ayam ras |
| 0.0319 | 0.0212 | Telur ayam ras |
| 0.0778 | 0.0532 | Bawang merah |
| 0.031 | 0.0166 | Bawang putih |
| 0.1416 | 0.1027 | Cabai merah keriting |
| 0.1645 | 0.1293 | Cabai rawit merah |

| nama | kota | gejolak_mingguan |
|---|---|---|
| Cabai rawit merah | Kota Blitar | 0.2242 |
| Cabai merah keriting | Kota Blitar | 0.1831 |
| Bawang merah | Kota Blitar | 0.0945 |
| Daging ayam ras | Kab. Jember | 0.056 |
| Bawang putih | Kab. Banyuwangi | 0.0456 |
| Telur ayam ras | Kota Blitar | 0.0407 |

## Nilai acuan — Peringatan dini
- Benar 1.2 dari 10 · tertangkap 2.4 · lebih awal 5.8 minggu ·
  pola tahun lalu benar 2.2 (tertangkap 4.2) · selalu 1.6
- **Layak operasional: TIDAK** → keputusan di dashboard harus "jangan jadikan pemicu pembelian"

| nama | kota | jeda_minggu | hubungan |
|---|---|---|---|
| Daging ayam ras | Kota Kediri | 1 | kuat |
| Daging ayam ras | Kota Probolinggo | 1 | kuat |
| Daging ayam ras | Kab. Tasikmalaya | 1 | kuat |
| Telur ayam ras | Kota Semarang | 1 | kuat |
| Telur ayam ras | Kota Cirebon | 1 | sedang |
| Telur ayam ras | Kota Probolinggo | 1 | sedang |
| Bawang merah | Kota Surakarta (Solo) | 1 | kuat |
| Bawang merah | Kota Tangerang | 1 | kuat |
| Bawang merah | Kab. Cilacap | 1 | kuat |
| Bawang putih | Kota Tegal | 1 | kuat |
| Bawang putih | Kota Surakarta (Solo) | 1 | kuat |
| Bawang putih | Kab. Jember | 1 | kuat |
| Cabai merah keriting | Kab. Cilacap | 1 | sedang |
| Cabai merah keriting | Kota Semarang | 1 | sedang |
| Cabai merah keriting | Kota Surakarta (Solo) | 1 | sedang |
| Cabai rawit merah | Kota Surakarta (Solo) | 1 | sedang |
| Cabai rawit merah | Kota Surabaya | 1 | sedang |
| Cabai rawit merah | Kota Kediri | 1 | sedang |

## Nilai acuan — Pola musiman
| nama_dashboard | idulfitri_mulai_naik_minggu | idulfitri_kenaikan_minggu_min1 | idulfitri_tahun_konsisten | idulfitri_puncak_minggu | idulfitri_puncak_kenaikan |
|---|---|---|---|---|---|
| Cabai rawit merah | -8 | 0.388 | 2 dari 3 | -5 | 0.56 |
| Cabai merah keriting | None | -0.0245 | 1 dari 3 | 0 | 0.124 |
| Bawang merah | -4 | 0.2562 | 3 dari 3 | 2 | 0.528 |
| Bawang putih | None | 0.0241 | 1 dari 3 | 1 | 0.0642 |
| Daging ayam ras | -6 | 0.1061 | 2 dari 3 | 0 | 0.2014 |
| Telur ayam ras | None | 0.0328 | 1 dari 3 | -4 | 0.1083 |

## Nilai acuan — Rantai pasok
| hemat_produsen | hemat_pb | margin_pb | margin_pasar | nama |
|---|---|---|---|---|
| 0.2126 | 0.1162 | 0.1516 | 0.1315 | Daging ayam ras |
| 0.103 | 0.067 | 0.0298 | 0.0718 | Telur ayam ras |
| 0.3084 | 0.231 | 0.0938 | 0.3005 | Bawang merah |
| 0.4065 | 0.2225 | 0.2884 | 0.2863 | Cabai merah keriting |
| 0.3162 | 0.1672 | 0.1633 | 0.201 | Cabai rawit merah |

| nama_dashboard | modern_vs_tradisional_pct |
|---|---|
| Cabai rawit merah | 0.6857 |
| Cabai merah keriting | 0.8172 |
| Bawang merah | 0.5711 |
| Bawang putih | nan |
| Daging ayam ras | 0.2005 |
| Telur ayam ras | -0.0075 |

## Pemeriksaan manual (keputusan tidak menyesatkan)
| Halaman | Keputusan | Angka pendukung tampil di halaman yang sama? | Batasan disebut? | Tidak melebihi temuan Q1–Q6? |
|---|---|---|---|---|
| | | | | |
