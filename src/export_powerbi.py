"""Tahap 5 — Export star schema untuk Power BI ke data/processed/ (parquet + csv).

Input : data/interim/ (Tahap 2–3), data/reference/, reports/tables/q*.csv (Tahap 4), src/insights.py (kalimat dashboard),
        config/config.yaml (bagian `export`, `wilayah`, `analisis`), config/biaya_logistik.yaml.
Output: data/processed/*.parquet & *.csv, docs/export_powerbi_report.md (ringkasan otomatis).

Kunci (integer, untuk relasi di Power BI):
    tanggal_key   = YYYYMMDD; minggu_key = tanggal_key hari Jumat minggu itu (relasi ke dim_tanggal)
    kota_key      = kota_id PIHPS;  komoditas_key = angka di belakang "com_";  jenis_pasar_key = price_type_id
    rute_key      = nomor urut rute (kota sumber -> kota tujuan x komoditas), lihat dim_rute

Tabel fakta (angka) dan dimensi (label & filter): lihat FAKTA_KUNCI dan build(). Kolom teks untuk layar
(fact_tindakan, fact_hal, fact_alert.alasan) memakai bahasa dashboard (brief §6.2–§6.3).
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src import insights
from src.analysis.common import KOMODITAS_URUT, LABEL_PENDEK, ROOT, TABLES, load_cfg

log = logging.getLogger("export")

NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
              "November", "Desember"]
NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
CATATAN_PASAR = {1: "dicatat setiap hari kerja", 2: "diperbarui ~Selasa-Rabu, sering tidak berubah",
                 3: "diperbarui ~Kamis (seminggu sekali)", 4: "diperbarui sesekali; harga bisa usang"}

DIM_KUNCI = {"dim_tanggal": "tanggal_key", "dim_kota": "kota_key", "dim_komoditas": "komoditas_key",
             "dim_jenis_pasar": "jenis_pasar_key", "dim_rute": "rute_key"}
_K = {"kota_key": "dim_kota", "komoditas_key": "dim_komoditas"}
FAKTA_KUNCI = {
    "fact_harga": {"tanggal_key": "dim_tanggal", "jenis_pasar_key": "dim_jenis_pasar", **_K},
    "fact_harga_mingguan": {"minggu_key": "dim_tanggal", "jenis_pasar_key": "dim_jenis_pasar", **_K},
    "fact_spread": {"minggu_key": "dim_tanggal", "rute_key": "dim_rute"},
    "fact_rute_sensitivitas": {"rute_key": "dim_rute"},
    "fact_alert": {"minggu_key": "dim_tanggal", **_K},
    "fact_tindakan": {"minggu_key": "dim_tanggal", "komoditas_key": "dim_komoditas"},
    "fact_hal": {"minggu_key": "dim_tanggal", "komoditas_key": "dim_komoditas"},
    "fact_gejolak": _K,
    "fact_penentu_arah": _K,
    "fact_pantau_kota_tujuan": {"kota_tujuan_key": "dim_kota", "pantau_kota_key": "dim_kota", "komoditas_key": "dim_komoditas"},
    "fact_pola_idul_fitri": {"komoditas_key": "dim_komoditas"},
    "fact_margin": _K,
    "dim_rute": {"kota_sumber_key": "dim_kota", "kota_tujuan_key": "dim_kota", "komoditas_key": "dim_komoditas"},
}


# ---------------------------------------------------------------- kunci & pemeriksaan (fungsi murni, diuji)
def tanggal_key(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s)
    return (s.dt.year * 10000 + s.dt.month * 100 + s.dt.day).astype("int64")


def komoditas_key(komoditas_id: str) -> int:
    return int(str(komoditas_id).split("_")[1])


def check_integrity(tables: dict[str, pd.DataFrame], kunci: dict[str, dict[str, str]]) -> list[str]:
    """Daftar masalah: kunci dimensi tidak unik, atau kunci fakta yang tidak ada di dimensinya. Kosong = OK."""
    masalah = []
    dims = {d for m in kunci.values() for d in m.values()}
    for d in sorted(dims):
        if d not in tables:
            masalah.append(f"{d}: tabel tidak ada")
            continue
        kol = DIM_KUNCI.get(d, next(k for m in kunci.values() for k, v in m.items() if v == d))
        if tables[d][kol].duplicated().any():
            masalah.append(f"{d}: kunci {kol} tidak unik")
    for f, m in kunci.items():
        if f not in tables:
            masalah.append(f"{f}: tabel tidak ada")
            continue
        for kol, d in m.items():
            if d not in tables:
                continue
            dk = DIM_KUNCI.get(d, kol)
            nilai = tables[f][kol].dropna()
            hilang = ~nilai.isin(tables[d][dk])
            if hilang.any():
                masalah.append(f"{f}.{kol}: {int(hilang.sum())} nilai tidak ada di {d}")
    return masalah


def build_dim_tanggal(start: pd.Timestamp, end: pd.Timestamp, kal: pd.DataFrame, hari_besar: pd.DataFrame) -> pd.DataFrame:
    """Semua hari kalender start..end + atribut minggu (W-FRI) & hari besar."""
    d = pd.DataFrame({"tanggal": pd.date_range(start, end, freq="D")})
    d["tanggal_key"] = tanggal_key(d.tanggal)
    d["minggu_akhir"] = d.tanggal.dt.to_period("W-FRI").dt.end_time.dt.normalize()
    d["minggu_key"] = tanggal_key(d.minggu_akhir)
    d["tahun"] = d.tanggal.dt.year
    d["bulan"] = d.tanggal.dt.month
    d["nama_bulan"] = d.bulan.map(lambda m: NAMA_BULAN[m - 1])
    d["tahun_bulan"] = d.tanggal.dt.strftime("%Y-%m")
    d["hari"] = d.tanggal.dt.day_of_week.map(lambda i: NAMA_HARI[i])
    d["is_hari_kerja"] = d.tanggal.dt.day_of_week < 5
    k = kal[["minggu_akhir", "minggu_ke_idul_fitri", "tahun_idul_fitri", "ada_libur_hari_besar", "nama_hari_besar"]].rename(
        columns={"ada_libur_hari_besar": "minggu_ada_libur_hari_besar", "nama_hari_besar": "minggu_nama_hari_besar"})
    d = d.merge(k, on="minggu_akhir", how="left")
    d["minggu_ke_idul_fitri"] = d.minggu_ke_idul_fitri.astype("Int64")
    d["tahun_idul_fitri"] = d.tahun_idul_fitri.astype("Int64")
    d["minggu_ada_libur_hari_besar"] = d.minggu_ada_libur_hari_besar.astype("boolean").fillna(False).astype(bool)
    d["minggu_nama_hari_besar"] = d.minggu_nama_hari_besar.fillna("")
    nama = pd.Series("", index=d.index)
    for r in hari_besar.itertuples():
        m = (d.tanggal >= r.libur_mulai) & (d.tanggal <= r.libur_selesai)
        nama = nama.where(~m | (nama != ""), r.nama)
    d["is_libur_hari_besar"] = nama != ""
    d["nama_hari_besar"] = nama
    d["is_hari_idul_fitri"] = d.tanggal.isin(hari_besar[hari_besar.jenis == "idul_fitri"].tanggal)
    return d


# ---------------------------------------------------------------- pembangun tabel
def _tabel(nama: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / f"{nama}.csv")


def _kota_key_dari_nama(dim_kota: pd.DataFrame, nama: pd.Series) -> pd.Series:
    m = dim_kota.set_index("kota").kota_key
    out = nama.map(m)
    if out.isna().any():
        raise ValueError(f"Nama kota tidak dikenal: {sorted(nama[out.isna()].unique())}")
    return out.astype("int64")


def _kom_key_dari_kualitas(dim_kom: pd.DataFrame, kualitas: pd.Series) -> pd.Series:
    m = dim_kom.set_index("kualitas").komoditas_key
    out = kualitas.map(m)
    if out.isna().any():
        raise ValueError(f"Komoditas tidak dikenal: {sorted(kualitas[out.isna()].unique())}")
    return out.astype("int64")


def build(cfg: dict, lcfg: dict) -> dict[str, pd.DataFrame]:
    ecfg, wil, q2cfg = cfg["export"], cfg["wilayah"], cfg["analisis"]["q2_rute"]
    kons = lcfg["sensitivitas"]["skenario_konservatif"]
    interim, ref = ROOT / cfg["paths"]["interim"], ROOT / cfg["paths"]["reference"]
    h = pd.read_parquet(interim / "harga_harian.parquet")
    w = pd.read_parquet(interim / "harga_mingguan.parquet")
    kal = pd.read_parquet(interim / "kalender_mingguan.parquet")
    sp = pd.read_parquet(interim / "spread_mingguan.parquet")
    hb = pd.read_csv(ref / "hari_besar.csv", parse_dates=["tanggal", "libur_mulai", "libur_selesai"])
    koord = pd.read_csv(ref / "kota_koordinat.csv")
    biaya = pd.read_csv(ref / "biaya_rute.csv")
    T: dict[str, pd.DataFrame] = {}

    # ---- dimensi
    T["dim_tanggal"] = build_dim_tanggal(h.tanggal.min(), h.tanggal.max(), kal, hb)

    kota = (h.drop_duplicates("kota_id")[["kota_id", "kota", "provinsi_id", "provinsi"]]
            .merge(koord[["kota_id", "lat", "lon"]], on="kota_id", how="left").rename(columns={"kota_id": "kota_key"}))
    kota["pulau"] = "Jawa"
    kota["is_kota_tujuan"] = kota.kota_key.isin(list(wil["kota_tujuan"]))
    kota["is_kota_sumber"] = kota.kota_key.isin(list(wil["kota_sumber"]))
    sumber_kom = {int(k): ", ".join(LABEL_PENDEK[cfg["komoditas_fokus"][c]].lower() for c in v["komoditas"])
                  for k, v in wil["kota_sumber"].items()}
    kota["komoditas_sumber"] = kota.kota_key.map(sumber_kom).fillna("")
    # Peran kota per komoditas (Q3). Untuk bawang merah/putih ada 17-20 kota "penentu arah" (hubungan lemah), jadi untuk
    # label kota di dashboard hanya N teratas per komoditas (korelasi terbesar) yang dihitung sebagai penentu arah.
    peran3 = _tabel("q3_peran_kota")
    lead = peran3[peran3.peran == "penentu arah"].copy()
    lead["peringkat"] = lead.groupby("kualitas").korelasi.rank(ascending=False, method="first").astype(int)
    peran3 = peran3.merge(lead[["kota", "kualitas", "peringkat"]], on=["kota", "kualitas"], how="left")
    top_n = cfg["analisis"]["q3_leadlag"]["top_n_penentu_arah_dashboard"]
    pa = (lead[lead.peringkat <= top_n].groupby("kota").kualitas
          .apply(lambda s: ", ".join(LABEL_PENDEK[x].lower() for x in KOMODITAS_URUT if x in set(s))))
    kota["penentu_arah_untuk"] = kota.kota.map(pa).fillna("")
    kota["is_penentu_arah"] = kota.penentu_arah_untuk != ""
    kota["peran"] = np.select([kota.is_kota_tujuan, kota.is_kota_sumber, kota.is_penentu_arah],
                              ["kota tujuan", "kota sumber", "kota penentu arah"], "lainnya")
    kota["status_kota_sumber"] = np.where(kota.is_kota_sumber, "PERLU_VERIFIKASI (pilihan dari pengetahuan umum)", "")
    T["dim_kota"] = kota.sort_values("kota_key").reset_index(drop=True)

    kom = h.drop_duplicates("komoditas_id")[["komoditas_id", "komoditas", "kualitas", "satuan"]].copy()
    kom["komoditas_key"] = kom.komoditas_id.map(komoditas_key)
    kom["nama_dashboard"] = kom.kualitas.map(LABEL_PENDEK)
    kom["urutan"] = kom.kualitas.map({k: i + 1 for i, k in enumerate(KOMODITAS_URUT)})
    rute_kom = {c for v in wil["kota_sumber"].values() for c in v["komoditas"]}
    kom["dianalisis_rutenya"] = kom.komoditas_id.isin(rute_kom)
    q1 = _tabel("q1_gejolak_per_komoditas").set_index("kualitas")
    q4 = _tabel("q4_ringkasan").set_index("kualitas")
    q5 = _tabel("q5_per_komoditas").set_index("kualitas")
    kom["peringkat_gejolak"] = kom.kualitas.map(q1.peringkat).astype("Int64")
    kom["gejolak_mingguan_median"] = kom.kualitas.map(q1.gejolak_median)
    kom["rata_perubahan_per_minggu"] = kom.kualitas.map(q1.rata_perubahan_abs_median)
    kom["idulfitri_mulai_naik_minggu"] = kom.kualitas.map(q4.mulai_naik_minggu).astype("Int64")
    kom["idulfitri_naik_di_batas_jendela"] = kom.kualitas.map(q4.mulai_di_batas_jendela).astype("boolean").fillna(False).astype(bool)
    kom["idulfitri_kenaikan_minggu_min1"] = kom.kualitas.map(q4.kenaikan_minggu_min1_rata)
    kom["idulfitri_tahun_konsisten"] = kom.kualitas.map(q4.tahun_konsisten).fillna("")
    kom["idulfitri_puncak_minggu"] = kom.kualitas.map(q4.puncak_minggu).astype("Int64")
    kom["idulfitri_puncak_kenaikan"] = kom.kualitas.map(q4.puncak_kenaikan_rata)
    kom["hemat_beli_produsen_pct"] = kom.kualitas.map(q5.hemat_beli_produsen_pct)
    kom["hemat_beli_pedagang_besar_pct"] = kom.kualitas.map(q5.hemat_beli_pedagang_besar_pct)
    kom["modern_vs_tradisional_pct"] = kom.kualitas.map(q5.selisih_modern_vs_tradisional_pct)
    T["dim_komoditas"] = kom.sort_values("urutan").reset_index(drop=True)

    T["dim_jenis_pasar"] = pd.DataFrame({"jenis_pasar_key": list(cfg["jenis_pasar"]),
                                         "jenis_pasar": list(cfg["jenis_pasar"].values())}).assign(
        catatan=lambda d: d.jenis_pasar_key.map(CATATAN_PASAR))

    # ---- rute
    q2 = _tabel("q2_rute_ringkasan")
    q2 = q2[q2.tujuan_jenis_pasar_id == q2cfg["harga_tujuan_jenis_pasar_id"]].copy()
    RUTE = ["kota_sumber_id", "kota_tujuan_id", "komoditas_id"]
    r = q2[q2.pengali == kons].sort_values(["komoditas_id", "kota_sumber_id", "kota_tujuan_id"]).reset_index(drop=True)
    r["rute_key"] = np.arange(1, len(r) + 1)
    r = r.merge(biaya[RUTE + ["ongkos_angkut_rp_per_kg", "susut_pct", "muatan_efektif_kg", "status_mpp"]], on=RUTE, how="left")
    dr = pd.DataFrame({
        "rute_key": r.rute_key, "kota_sumber_key": r.kota_sumber_id, "kota_tujuan_key": r.kota_tujuan_id,
        "komoditas_key": r.komoditas_id.map(komoditas_key), "rute": r.kota_sumber + " → " + r.kota_tujuan,
        "nama_rute": r.kualitas.map(LABEL_PENDEK) + ": " + r.kota_sumber + " → " + r.kota_tujuan,
        "jarak_jalan_km": r.jarak_jalan_km, "ongkos_angkut_rp_per_kg": r.ongkos_angkut_rp_per_kg, "susut_pct": r.susut_pct,
        "muatan_efektif_kg": r.muatan_efektif_kg, "cek_batas_atas_mpp": r.status_mpp,
        "layak": r.layak_konservatif.astype(bool),
        "layak_jika_jual_ke_pedagang_besar": r.layak_jika_jual_ke_pedagang_besar.astype(bool),
        "porsi_minggu_untung": r.porsi_minggu_untung, "minggu_untung_dari_10": (r.porsi_minggu_untung * 10).round(1),
        "median_untung_rp_per_kg": r.median_untung_rp_per_kg, "median_selisih_harga_rp_per_kg": r.selisih_kotor_median_rp_per_kg,
        "median_ongkos_rp_per_kg": r.biaya_logistik_median_rp_per_kg,
        "rata_bertahan_minggu": r.persistensi_rata_minggu, "bertahan_terlama_minggu": r.persistensi_maks_minggu,
        "minggu_untung_berturut_terakhir": r.minggu_untung_berturut_terakhir,
        "untung_dari_10_minggu_terakhir": r.untung_dari_jendela,
        "median_untung_jual_ke_pedagang_besar": r.median_untung_jual_ke_pedagang_besar,
        "n_minggu": r.n_minggu, "pengali_ongkos_acuan": kons,
    })
    dr["status"] = np.select([dr.layak & dr.layak_jika_jual_ke_pedagang_besar, dr.layak],
                             ["layak, juga jika dijual ke pedagang besar (paling aman)", "layak hanya jika dijual dengan harga eceran"],
                             "tidak layak")
    dr["catatan_ongkos"] = "ongkos angkut = perkiraan, bukan data"
    T["dim_rute"] = dr
    kunci_rute = r[RUTE + ["rute_key"]]

    sens = q2.merge(kunci_rute, on=RUTE)
    T["fact_rute_sensitivitas"] = pd.DataFrame({
        "rute_key": sens.rute_key, "pengali_ongkos": sens.pengali, "porsi_minggu_untung": sens.porsi_minggu_untung,
        "median_untung_rp_per_kg": sens.median_untung_rp_per_kg, "median_ongkos_rp_per_kg": sens.biaya_logistik_median_rp_per_kg,
        "rata_bertahan_minggu": sens.persistensi_rata_minggu}).sort_values(["rute_key", "pengali_ongkos"]).reset_index(drop=True)

    s = sp[sp.tujuan_jenis_pasar_id == q2cfg["harga_tujuan_jenis_pasar_id"]].merge(kunci_rute, on=RUTE)
    s = s[s.harga_tujuan.notna() | s.harga_sumber.notna()]
    T["fact_spread"] = pd.DataFrame({
        "minggu_key": tanggal_key(s.minggu_akhir), "rute_key": s.rute_key, "harga_sumber": s.harga_sumber,
        "harga_tujuan": s.harga_tujuan, "selisih_harga": s.spread_kotor, "ongkos_angkut": s.ongkos_angkut, "susut_rp": s.susut_rp,
        "ongkos_total_x1": s["biaya_logistik_x1"], "untung_per_kg_x1": s["spread_bersih_x1"],
        "ongkos_total_x1_5": s["biaya_logistik_x1.5"], "untung_per_kg_x1_5": s["spread_bersih_x1.5"],
        "untung_per_kg_x2": s["spread_bersih_x2"], "sumber_usang": s.sumber_usang,
    }).sort_values(["rute_key", "minggu_key"]).reset_index(drop=True)

    # ---- harga
    hh = h[h.harga_bersih.notna() | h.is_outlier_flag] if ecfg["fact_harga_hanya_berharga"] else h
    T["fact_harga"] = pd.DataFrame({
        "tanggal_key": tanggal_key(hh.tanggal), "kota_key": hh.kota_id, "komoditas_key": hh.komoditas_id.map(komoditas_key),
        "jenis_pasar_key": hh.jenis_pasar_id, "harga": hh.harga_bersih, "harga_asli": hh.harga,
        "is_imputed": hh.is_imputed, "is_outlier_flag": hh.is_outlier_flag, "is_lonjakan_tajam": hh.is_lonjakan_tajam,
        "is_libur_isi": hh.is_libur_isi, "is_usang": hh.is_usang,
    }).reset_index(drop=True)

    ww = w[w.harga.notna()]
    T["fact_harga_mingguan"] = pd.DataFrame({
        "minggu_key": tanggal_key(ww.minggu_akhir), "kota_key": ww.kota_id, "komoditas_key": ww.komoditas_id.map(komoditas_key),
        "jenis_pasar_key": ww.jenis_pasar_id, "harga": ww.harga, "n_hari_nyata": ww.n_hari_nyata,
        "perubahan_wow": ww.pct_wow, "perubahan_4m": ww.pct_4w, "perubahan_yoy": ww.pct_yoy,
        "rata4m": ww.harga_ma4, "rata12m": ww.harga_ma12, "gejolak_4m": ww.vol_4, "gejolak_12m": ww.vol_12,
        "kenaikan_vs_kebiasaan": ww.zscore_return, "harga_nasional": ww.harga_nasional,
        "selisih_nasional_rp": ww.selisih_nasional_rp, "selisih_nasional_pct": ww.selisih_nasional_pct,
        "minggu_tipis": ww.minggu_tipis, "is_usang": ww.is_usang, "is_seri_dikecualikan": ww.is_seri_dikecualikan,
    }).reset_index(drop=True)

    # ---- hasil analisis untuk halaman dashboard
    dk, dkom = T["dim_kota"], T["dim_komoditas"]
    g = _tabel("q1_gejolak_per_kota")
    T["fact_gejolak"] = pd.DataFrame({
        "kota_key": g.kota_id, "komoditas_key": _kom_key_dari_kualitas(dkom, g.kualitas), "gejolak_mingguan": g.gejolak_mingguan,
        "rata_perubahan_per_minggu": g.rata_perubahan_abs, "koef_variasi": g.cv, "peringkat_dalam_komoditas": g.peringkat_dalam_komoditas,
        "harga_rata": g.harga_rata, "harga_min": g.harga_min, "harga_maks": g.harga_maks,
        "kenaikan_mingguan_terbesar": g.kenaikan_mingguan_maks, "n_minggu": g.n_minggu_return})

    p = peran3
    T["fact_penentu_arah"] = pd.DataFrame({
        "kota_key": _kota_key_dari_nama(dk, p.kota), "komoditas_key": _kom_key_dari_kualitas(dkom, p.kualitas), "peran": p.peran,
        "jeda_minggu": p.jeda.astype("Int64"), "korelasi": p.korelasi, "hubungan": p.kekuatan.fillna(""),
        "peringkat_penentu_arah": p.peringkat.astype("Int64"), "tampil_di_dashboard": (p.peringkat <= top_n).fillna(False).astype(bool),
        "didukung_uji_tambahan": p.granger_mendukung.astype("boolean")})

    pt = _tabel("q3_pantau_untuk_kota_tujuan")
    T["fact_pantau_kota_tujuan"] = pd.DataFrame({
        "kota_tujuan_key": _kota_key_dari_nama(dk, pt.kota_tujuan), "pantau_kota_key": _kota_key_dari_nama(dk, pt.pantau_kota),
        "komoditas_key": _kom_key_dari_kualitas(dkom, pt.kualitas), "jeda_minggu": pt.jeda, "korelasi": pt.korelasi, "hubungan": pt.kekuatan})

    q4p = _tabel("q4_pola_idul_fitri")
    T["fact_pola_idul_fitri"] = pd.DataFrame({
        "komoditas_key": _kom_key_dari_kualitas(dkom, q4p.kualitas), "tahun_idul_fitri": q4p.tahun_idul_fitri,
        "minggu_ke_idul_fitri": q4p.minggu_ke_idul_fitri, "kenaikan_vs_harga_normal": q4p.kenaikan_median_kota, "n_kota": q4p.kota})

    m = _tabel("q5_per_kota")
    T["fact_margin"] = pd.DataFrame({
        "kota_key": _kota_key_dari_nama(dk, m.kota), "komoditas_key": _kom_key_dari_kualitas(dkom, m.kualitas), "cakupan": m.cakupan,
        "harga_produsen_dari": m.produsen_dari, "n_bulan": m.bulan, "harga_produsen": m.produsen, "harga_pedagang_besar": m.pedagang_besar,
        "harga_pasar": m.tradisional, "tambahan_di_pedagang_besar_pct": m.tambahan_pedagang_besar_pct,
        "tambahan_di_pasar_pct": m.tambahan_eceran_pct, "tambahan_total_pct": m.tambahan_total_pct,
        "hemat_beli_produsen_pct": m.hemat_beli_produsen_pct, "hemat_beli_pedagang_besar_pct": m.hemat_beli_pedagang_besar_pct,
        "porsi_bulan_produsen_lebih_mahal": m.porsi_bulan_produsen_lebih_mahal})

    u = _tabel("q6_skor_ringkas")
    label = {"A atau B (aturan brief)": "Peringatan dini (aturan yang diuji)", "A: kota penentu arah": "Hanya dari kota penentu arah",
             "B: masa sebelum Idulfitri": "Hanya dari masa sebelum Idulfitri",
             "pembanding: sama seperti tahun lalu": "Pembanding: tebakan \"sama seperti tahun lalu\"",
             "pembanding: selalu beri peringatan": "Pembanding: selalu beri peringatan"}
    T["fact_uji_peringatan"] = pd.DataFrame({
        "aturan": u.aturan.map(label).fillna(u.aturan), "urutan": np.arange(1, len(u) + 1),
        "benar_dari_10": (u.ketepatan * 10).round(1), "tertangkap_dari_10": (u.tangkapan * 10).round(1),
        "lebih_awal_minggu": u.lead_time_rata_minggu.round(1), "porsi_minggu_peringatan": u.porsi_minggu_peringatan,
        "jumlah_peringatan": u.peringatan, "jumlah_lonjakan": u.lonjakan, "tahun_uji": ", ".join(map(str, cfg["analisis"]["q6_peringatan"]["tahun_uji"]))})

    # ---- peringatan: riwayat tahun uji + 8 minggu terkini
    uji = _tabel("q6_peringatan_uji")
    uji["minggu_akhir"] = pd.to_datetime(uji.minggu_akhir)
    cur = _tabel("q6_peringatan_terkini")
    cur["minggu_akhir"] = pd.to_datetime(cur.minggu_akhir)
    cur = cur[cur.minggu_akhir > uji.minggu_akhir.max()]
    uji["pemicu_A"] = uji.pemicu_A.fillna("")
    alasan_uji = []
    for x in uji.itertuples():
        a = []
        if x.sinyal_A:
            a.append(f"harga {LABEL_PENDEK[x.kualitas].lower()} di {x.pemicu_A} naik jauh di atas kebiasaan (kota yang harganya biasanya naik lebih dulu)")
        if x.sinyal_B:
            a.append("sudah masuk masa sebelum Idulfitri, saat harga biasanya mulai naik")
        alasan_uji.append("; ".join(a))
    al = pd.concat([
        pd.DataFrame({"minggu_akhir": uji.minggu_akhir, "kualitas": uji.kualitas, "kota": uji.kota,
                      "peringatan": uji.sinyal_A | uji.sinyal_B, "sinyal_kota_penentu_arah": uji.sinyal_A,
                      "sinyal_masa_idulfitri": uji.sinyal_B, "awal_lonjakan": uji.onset, "masa_lonjakan": uji.masa,
                      "harga": uji.harga, "alasan": alasan_uji, "sumber": "uji data lama (aturan dilatih tanpa tahun itu)"}),
        pd.DataFrame({"minggu_akhir": cur.minggu_akhir, "kualitas": cur.kualitas, "kota": cur.kota, "peringatan": cur.peringatan,
                      "sinyal_kota_penentu_arah": cur.sinyal_A, "sinyal_masa_idulfitri": cur.sinyal_B,
                      "awal_lonjakan": pd.NA, "masa_lonjakan": pd.NA, "harga": np.nan, "alasan": cur.alasan.fillna(""),
                      "sumber": "terkini (belum bisa dinilai benar/salah)"}),
    ], ignore_index=True)
    T["fact_alert"] = pd.DataFrame({
        "minggu_key": tanggal_key(al.minggu_akhir), "kota_key": _kota_key_dari_nama(dk, al.kota),
        "komoditas_key": _kom_key_dari_kualitas(dkom, al.kualitas), "peringatan": al.peringatan.astype(bool),
        "sinyal_kota_penentu_arah": al.sinyal_kota_penentu_arah.astype(bool), "sinyal_masa_idulfitri": al.sinyal_masa_idulfitri.astype(bool),
        "awal_lonjakan": al.awal_lonjakan.astype("boolean"), "masa_lonjakan": al.masa_lonjakan.astype("boolean"),
        "harga": al.harga, "alasan": al.alasan, "sumber": al.sumber,
    }).sort_values(["komoditas_key", "kota_key", "minggu_key"]).reset_index(drop=True)

    # ---- kalimat dashboard (src/insights.py)
    ins = insights.build(cfg, lcfg)
    t = ins["tindakan"].merge(kunci_rute, on=RUTE, how="left")
    T["fact_tindakan"] = pd.DataFrame({
        "minggu_key": tanggal_key(t.minggu_akhir), "komoditas_key": t.komoditas_id.map(komoditas_key), "prioritas": t.prioritas,
        "tindakan": t.tindakan, "alasan_singkat": t.alasan_singkat, "beli_lebih_awal": t.beli_lebih_awal, "pindah_stok": t.pindah_stok,
        "rute_key": t.rute_key.astype("Int64"), "nilai": t.nilai, "satuan": t.satuan, "pembanding": t.pembanding, "sumber": t.sumber})
    hal = ins["hal"]
    T["fact_hal"] = pd.DataFrame({
        "minggu_key": tanggal_key(hal.minggu_akhir), "urutan": hal.urutan, "komoditas_key": hal.komoditas_id.map(komoditas_key),
        "kalimat": hal.kalimat, "nilai": hal.nilai, "satuan": hal.satuan, "pembanding": hal.pembanding, "sumber": hal.sumber})

    # ---- info untuk catatan kaki dashboard ("Data per [tanggal]")
    log_unduh = pd.read_csv(ROOT / cfg["paths"]["log_unduhan"], usecols=["waktu_unduh"])
    T["dim_info"] = pd.DataFrame([
        {"kunci": "data_terakhir", "nilai": f"{h.tanggal.max():%Y-%m-%d}", "keterangan": "tanggal data terakhir (H-2 dari pengambilan)"},
        {"kunci": "minggu_terakhir", "nilai": f"{w.minggu_akhir.max():%Y-%m-%d}", "keterangan": "minggu terakhir (berakhir Jumat)"},
        {"kunci": "data_pertama", "nilai": f"{h.tanggal.min():%Y-%m-%d}", "keterangan": "awal periode analisis"},
        {"kunci": "tanggal_pengambilan", "nilai": str(pd.to_datetime(log_unduh.waktu_unduh).max().date()),
         "keterangan": "data PIHPS bisa direvisi oleh Bank Indonesia"},
        {"kunci": "sumber", "nilai": "PIHPS Nasional, Bank Indonesia (bi.go.id/hargapangan)", "keterangan": "pasar tradisional, modern, pedagang besar, produsen; Pulau Jawa"},
        {"kunci": "ongkos_angkut", "nilai": "perkiraan, bukan data", "keterangan": "asumsi analis (config/biaya_logistik.yaml); diuji 0,5x-2x"},
        {"kunci": "pengali_ongkos_acuan", "nilai": f"{kons:g}", "keterangan": "rute disebut layak hanya jika tetap untung pada pengali ini"},
        {"kunci": "tanggal_export", "nilai": f"{datetime.now():%Y-%m-%d}", "keterangan": "python -m src.export_powerbi"},
    ])
    return T


# ---------------------------------------------------------------- tulis & laporan
def write(T: dict[str, pd.DataFrame], out_dir: Path, formats: list[str]) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for nama, df in T.items():
        rec = {"tabel": nama, "baris": len(df), "kolom": len(df.columns)}
        if "parquet" in formats:
            p = out_dir / f"{nama}.parquet"
            df.to_parquet(p, index=False)
            rec["parquet_mb"] = p.stat().st_size / 1e6
        if "csv" in formats:
            p = out_dir / f"{nama}.csv"
            df.to_csv(p, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
            rec["csv_mb"] = p.stat().st_size / 1e6
        rows.append(rec)
    return pd.DataFrame(rows)


def write_report(uk: pd.DataFrame, masalah: list[str], T: dict[str, pd.DataFrame], cfg: dict, path: Path) -> None:
    ecfg = cfg["export"]
    info = T["dim_info"].set_index("kunci").nilai
    besar = uk[uk.filter(like="_mb").max(axis=1) > ecfg["peringatan_ukuran_mb"]]
    lines = ["| Tabel | Baris | Kolom | Parquet (MB) | CSV (MB) | Isi |", "|---|---|---|---|---|---|"]
    isi = {
        "fact_harga": "harga harian per kota × komoditas × jenis pasar + penanda kualitas",
        "fact_harga_mingguan": "harga mingguan + perubahan (WoW, 4 minggu, YoY), gejolak, selisih vs nasional",
        "fact_spread": "per minggu × rute: selisih harga, ongkos angkut (perkiraan), susut, untung per kg (×1, ×1,5, ×2)",
        "fact_rute_sensitivitas": "per rute × pengali ongkos 0,5–2: porsi minggu untung, median untung",
        "fact_alert": "per minggu × kota × komoditas: peringatan, sinyal, awal & masa lonjakan (tahun uji + 8 minggu terkini), alasan",
        "fact_tindakan": "daftar tindakan per komoditas minggu terakhir (src/insights.py), dengan angka asal",
        "fact_hal": "\"Tiga hal yang perlu diketahui minggu ini\" (src/insights.py), dengan angka asal",
        "fact_gejolak": "gejolak harga per kota × komoditas (pasar tradisional)",
        "fact_penentu_arah": "peran kota (penentu arah / pengikut / netral) per komoditas, jeda, kekuatan hubungan",
        "fact_pantau_kota_tujuan": "kota yang perlu dipantau untuk tiap kota tujuan",
        "fact_pola_idul_fitri": "kenaikan vs harga normal per minggu ke Idulfitri × tahun × komoditas",
        "fact_margin": "tambahan harga produsen → pedagang besar → pasar per kota × komoditas",
        "fact_uji_peringatan": "hasil uji peringatan dini pada data lama (benar/tertangkap dari 10, lebih awal)",
        "dim_tanggal": "kalender harian + minggu (W-FRI), minggu ke Idulfitri, hari besar",
        "dim_kota": "kota: provinsi, koordinat, peran (tujuan / sumber / penentu arah)",
        "dim_komoditas": "komoditas: nama dashboard, satuan, ringkasan gejolak, pola Idulfitri, hemat beli di produsen",
        "dim_jenis_pasar": "4 jenis pasar + catatan cara pencatatan",
        "dim_rute": "rute pindah stok: jarak, ongkos (perkiraan), status layak, minggu untung dari 10",
        "dim_info": "tanggal data, tanggal pengambilan, sumber, catatan asumsi (untuk catatan kaki dashboard)",
    }
    for x in uk.itertuples():
        lines.append(f"| `{x.tabel}` | {x.baris:,} | {x.kolom} | {getattr(x, 'parquet_mb', float('nan')):.2f} | "
                     f"{getattr(x, 'csv_mb', float('nan')):.2f} | {isi.get(x.tabel, '')} |")
    text = f"""# Export Power BI (Tahap 5)

Dibuat otomatis oleh `python -m src.export_powerbi` pada {datetime.now():%Y-%m-%d %H:%M}. Jangan diedit manual.
Folder: `data/processed/` ({', '.join(ecfg['format'])}). Kunci & relasi: lihat docstring `src/export_powerbi.py`.

## Ringkasan
- Data per **{info['data_terakhir']}** (diambil {info['tanggal_pengambilan']}); minggu terakhir **{info['minggu_terakhir']}**.
- {len(T)} tabel, total {uk.baris.sum():,} baris. Ukuran terbesar: {uk.filter(like='_mb').max().max():.1f} MB.
- Pemeriksaan integritas kunci: **{'OK' if not masalah else 'ADA MASALAH'}**{'' if not masalah else ' — ' + '; '.join(masalah)}.
- Ongkos angkut di `fact_spread`/`dim_rute` = **perkiraan, bukan data**; komponen disimpan terpisah (ongkos tetap + susut)
  supaya untung per kg bisa dihitung ulang di Power BI dengan what-if parameter.
- Peringatan dini (`fact_alert`) diekspor sebagai **informasi**, bukan pemicu pembelian (Q6: benar 1,2 dari 10).

## Tabel
{chr(10).join(lines)}

## Relasi (fakta → dimensi)
{chr(10).join(f'- `{f}`: ' + ', '.join(f'`{k}` → `{d}`' for k, d in m.items()) for f, m in FAKTA_KUNCI.items())}

`minggu_key` berelasi ke `dim_tanggal.tanggal_key` (hari Jumat minggu itu); di Power BI buat relasi kedua yang tidak aktif
atau tabel `dim_minggu` = `dim_tanggal` yang difilter `tanggal_key = minggu_key`.

## File yang melebihi {ecfg['peringatan_ukuran_mb']} MB
{chr(10).join(f'- `{x.tabel}`: parquet {getattr(x, "parquet_mb", 0):.1f} MB, csv {getattr(x, "csv_mb", 0):.1f} MB' for x in besar.itertuples()) if len(besar) else '- tidak ada'}

## Kalimat dashboard minggu terakhir (fact_hal)
{chr(10).join(f'{x.urutan}. {x.kalimat}' for x in T['fact_hal'].itertuples())}
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg, lcfg = load_cfg()
    T = build(cfg, lcfg)
    masalah = check_integrity(T, FAKTA_KUNCI)
    for m in masalah:
        log.error("Integritas: %s", m)
    out_dir = ROOT / cfg["paths"]["processed"]
    uk = write(T, out_dir, cfg["export"]["format"])
    write_report(uk, masalah, T, cfg, ROOT / "docs" / "export_powerbi_report.md")
    log.info("Selesai: %d tabel, %s baris, integritas %s", len(T), f"{uk.baris.sum():,}", "OK" if not masalah else "GAGAL")
    print(uk.to_string(index=False))
    if masalah:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
