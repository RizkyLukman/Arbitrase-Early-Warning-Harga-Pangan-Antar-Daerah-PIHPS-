# Dashboard Excel: cara membangun, memakai, dan mengaudit

File: `excel/Dashboard_pangan.xlsx`, dibuat oleh `python -m src.build_excel_desain` dari `data/processed/`. Tujuh halaman untuk
pembaca (Ringkasan, Peta gejolak harga, Peluang pindah stok, Peringatan dini, Pola musiman, Rantai pasok dan margin, Catatan metode)
ditambah sheet data `d_*` yang disembunyikan. Bahasa di layar mengikuti `excel/glosarium.md`: judul = kesimpulan, setiap angka
punya pembanding, ongkos kirim selalu "perkiraan", dan setiap halaman ditutup band **Fakta dan keputusan**.

## 1. Membangun ulang (setelah data diperbarui)

```bash
python -m src.export_dashboard          # data/processed/ (19 tabel)
python -m src.peta_jawa                 # sekali: batas provinsi Natural Earth -> data/reference/peta_jawa.geojson
python -m src.build_excel_desain        # tulis workbook, lalu pasang tombol & bentuk lewat Excel
python -m src.recalc_excel excel/Dashboard_pangan.xlsx               # hitung ulang lewat Excel, simpan nilai
python -m src.audit_dashboard --xlsx excel/Dashboard_pangan.xlsx     # bandingkan dengan nilai acuan
python -m src.screenshot_excel          # PNG tiap halaman -> excel/screenshots/ (untuk README & cek visual)
```

Langkah Excel (tombol, bentuk, hitung ulang, screenshot) memakai Excel di Windows lewat pywin32. openpyxl menulis rumus tanpa hasil
dan tidak bisa membuat form control atau bentuk. Tanpa Excel, file tetap jalan (Excel menghitung saat dibuka) tetapi tanpa tombol dan
sudut bulat. `src/build_excel.py` adalah versi klasik tanpa tata letak desain; fungsinya dipakai ulang oleh `build_excel_desain`.

## 2. Memakai dashboard

| Halaman | Interaksi | Yang berubah |
|---|---|---|
| Peta gejolak harga | sel kuning di kanan atas: pilih komoditas (daftar) | judul, peta gelembung, grafik 10 kota operasional; heatmap tetap semua komoditas |
| Peluang pindah stok | tombol 0,5x / 1x / 1,5x / 2x (pengali ongkos kirim) dan sel kuning tambahan ongkos Rp/kg | judul, kartu, tabel 10 rute terurut, grafik rute terbaik |
| Lainnya | tidak ada input; angka dari hasil analisis | - |

- **Tombol pengali:** Form Control (option button) yang menulis nomor pilihan 1 sampai 4 ke sel AC9; AC10 = pengali (nama
  `pengali_ongkos`). Tidak butuh makro. Dipasang oleh `pasang_objek_excel` setelah file ditulis.
- **Rumus:** hanya fungsi Excel klasik (SUMIFS, INDEX/MATCH, LARGE, SUMPRODUCT, CHOOSE) supaya terbuka di Excel 2016 ke atas.
- **Panel, kartu, dan menu bersudut bulat:** latar halaman = panel hijau muda (#E6F2EC) setinggi menu; kartu putih dan band gelap
  di atasnya. Semua warna berasal dari warna sel (ikut zoom dan skala layar). Sudut bulat dibuat dengan bentuk kecil "potongan sudut"
  berwarna sama dengan latar di luarnya (`_potong_sudut`), ditambah garis tepi rounded rectangle tanpa isian untuk kartu putih; menu
  aktif = rounded rectangle hijau berisi teks. Bentuk berisi warna besar tidak dipakai karena Excel selalu menggambarnya di atas sel
  (menutupi angka); gambar latar sheet tidak dipakai karena tidak ikut zoom.
- **Peta:** gambar latar dari `src/peta_jawa.py` (bujur 105,0 sampai 114,8; lintang -8,95 sampai -5,75) ditambah grafik gelembung
  transparan dengan skala sumbu yang sama. Label hanya untuk kota di `LABEL_PETA` (kota tujuan, kota sumber utama, kota paling
  bergejolak). Jika batas peta diubah, ubah `BINGKAI` saja; gambar dan sumbu ikut.
- **Ukuran gejolak:** rata-rata perubahan harga per minggu per kota. Nama sel `ukuran_gejolak` memberi tahu `audit_dashboard` untuk
  memakai nilai acuan yang sesuai.
- **Pembanding:** untung pindah stok di Ringkasan memakai harga pasar dan selalu disertai untung bila dijual ke pedagang besar; hemat
  beli di produsen ditampilkan dibanding pedagang besar dan dibanding harga pasar.

## 3. Audit (wajib sebelum dinyatakan selesai)

1. `audit_dashboard --xlsx` mencetak **Cocok: n/20**: nilai 20 sel bernama (`kpi_*`, daftar di halaman Catatan metode) vs nilai acuan
   yang dihitung langsung dari `data/processed/`, jumlah sel rumus bererror, dan teks berisi istilah teknis. Laporan:
   `docs/audit_dashboard_report.md`. Target: 20/20, 0 error, 0 istilah.
2. Audit data terpisah: angka yang tampil dihitung ulang langsung dari `data/interim/` (`docs/audit_data_dashboard_desain.md`).
3. Uji interaksi: ganti komoditas di Peta gejolak harga, judul dan grafik ikut berubah; klik tombol 0,5x / 1x / 1,5x / 2x, rute untung
   29 / 28 / 23 / 22 dan rute dengan margin positif 30 / 28 / 27 / 22 (sama dengan `reports/q2_rute.md`).
4. Keputusan tidak menyesatkan: setiap keputusan merujuk angka di halaman yang sama, menyebut batasannya (ongkos perkiraan, hanya
   eceran, 3 Lebaran, 2 tahun uji), dan tidak lebih kuat daripada temuan di `reports/q*.md`.
5. Bahasa: tanpa simbol panah, titik tengah, tanda pengali, atau garis panjang; `tests/test_build_excel_desain.py` menjaga aturan ini.
6. Cek visual: `screenshot_excel` (zoom 100%, agar bentuk sejajar dengan sel) lalu periksa PNG, atau buka di Excel.

## 4. Batasan versi Excel ini
- Angka hasil analisis (median per rute, gejolak, uji peringatan) adalah data di sheet `d_*`, bukan dihitung ulang di Excel; yang
  dihitung ulang di Excel hanya skenario ongkos kirim dan pemilihan komoditas.
- Kartu bersudut bulat adalah tampilan; band "Fakta dan keputusan" juga bersudut bulat, kotak kecil di dalam kartu bersudut siku.
- Peta adalah ilustrasi (proyeksi bujur/lintang biasa), bukan peta GIS.
