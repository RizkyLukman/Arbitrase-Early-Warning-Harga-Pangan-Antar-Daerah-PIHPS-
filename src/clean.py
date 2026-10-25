"""Tahap 2 — Cleaning data harga PIHPS.

Input : data/raw/ (JSON mentah, dibaca lewat src/load_raw.py)
Output: data/interim/
    harga_harian.parquet     harga kota per hari kerja + semua penanda kualitas
    harga_nasional.parquet   rata-rata nasional per jenis pasar x komoditas x hari (pembanding)
    kualitas_data.csv        tabel kualitas data per jenis pasar x komoditas x kota (salinan: reports/kualitas_data.csv)
    libur_terdeteksi.csv     tanggal "hari libur diisi harga sebelumnya" yang terdeteksi dari data
        docs/cleaning_report.md  ringkasan angka cleaning (dibuat ulang setiap run)

Aturan & dasar penetapannya: notebooks/01_eda.ipynb, docs/data_profile.md. Ambang: config/config.yaml (cleaning).

Kolom harga di harga_harian:
    harga         nilai asli dari PIHPS (tidak pernah diubah)
    harga_bersih  nilai untuk analisis: hari libur & salah input dikosongkan, celah <= N hari kerja diisi
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.load_raw import JENIS_PASAR, load_commodity_ref, load_raw_long, load_regency_ref

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"
SERI = ["jenis_pasar_id", "komoditas_id", "kota_id"]
KUNCI = ["tanggal", "jenis_pasar_id", "kota_id", "komoditas_id"]

log = logging.getLogger("clean")


# ---------------------------------------------------------------- struktur
def dedupe_latest(df: pd.DataFrame) -> pd.DataFrame:
    """Satu nilai per (jenis pasar, komoditas, wilayah, tanggal): ambil dari file unduhan terbaru (data bisa direvisi)."""
    key = ["jenis_pasar_id", "komoditas_id", "level", "nama", "tanggal"]
    out = df.assign(_f=df["sumber_file"].astype(str)).sort_values("_f", kind="stable")
    return out.drop_duplicates(key, keep="last").drop(columns="_f")


def map_city_ids(kota: pd.DataFrame, ref: pd.DataFrame, drop_ids: list[int]) -> pd.DataFrame:
    """Petakan nama kota -> kota_id & provinsi_id per jenis pasar. Gagal jika ada nama yang tidak dikenal."""
    r = ref.drop_duplicates(["jenis_pasar_id", "nama"])[["jenis_pasar_id", "nama", "kota_id", "provinsi_id"]]
    out = kota.merge(r, on=["jenis_pasar_id", "nama"], how="left", validate="many_to_one")
    unknown = out.loc[out.kota_id.isna(), ["jenis_pasar_id", "nama"]].drop_duplicates()
    if len(unknown):
        raise ValueError(f"Nama kota tidak ada di referensi: {unknown.values.tolist()}")
    out = out[~out.kota_id.isin(drop_ids)].copy()
    out["kota_id"] = out.kota_id.astype(int)
    out["provinsi_id"] = out.provinsi_id.astype(int)
    return out


def complete_grid(kota: pd.DataFrame, tanggal: pd.DatetimeIndex) -> pd.DataFrame:
    """Lengkapi setiap seri ke semua tanggal kerja. Baris yang ditambahkan berisi harga NaN.

    PIHPS tidak menyertakan baris sebuah kota di bulan ketika kota itu tidak punya data sama sekali
    (mis. cabai merah keriting Kab. Jember Des 2023 - Mar 2026). Tanpa langkah ini, bulan yang hilang tidak
    terhitung sebagai kosong, dan pengisian celah / median bergulir "melompati" bulan tersebut.
    """
    atribut = [c for c in kota.columns if c not in ("tanggal", "harga", "kosong", "sumber_file")]
    seri = kota[atribut].drop_duplicates(SERI)
    if seri.duplicated(SERI).any():
        raise ValueError("Atribut seri tidak konsisten antar tanggal")
    grid = seri.merge(pd.DataFrame({"tanggal": tanggal}), how="cross")
    out = grid.merge(kota[SERI + ["tanggal", "harga"]], on=SERI + ["tanggal"], how="left", validate="one_to_one")
    return out


# ---------------------------------------------------------------- hari libur
def detect_holiday_dates(kota: pd.DataFrame, ambang: float) -> pd.DatetimeIndex:
    """Tanggal di mana > ambang seri pasar tradisional (id 1) harganya sama persis dengan hari sebelumnya.

    Pada hari libur PIHPS mengisi harga hari kerja terakhir (lihat notebooks/01_eda.ipynb §2).
    """
    trad = kota[kota.jenis_pasar_id == 1].sort_values(SERI + ["tanggal"])
    diff = trad.groupby(SERI, observed=True).harga.diff()
    v = trad.assign(sama=diff.eq(0))[diff.notna()]
    share = v.groupby("tanggal").sama.mean()
    return pd.DatetimeIndex(share[share > ambang].index, name="tanggal")


# ---------------------------------------------------------------- outlier
def _by(df: pd.DataFrame, cols: list[str]) -> list[pd.Series]:
    return [df[c] for c in cols]


def flag_outliers(df: pd.DataFrame, o: dict, value_col: str = "harga") -> pd.DataFrame:
    """Outlier dua tingkat (notebooks/01_eda.ipynb §5).

    Salah input -> is_outlier_flag (+ alasan_outlier), dikosongkan di harga_bersih:
        B rasio_ekstrem : x >= r x median bergulir seri itu, atau <= median / r
        C lintas_kota   : x >= r x median kota lain (jenis pasar, komoditas, tanggal sama), atau <= 1/r
    Penanda saja -> is_lonjakan_tajam (nilai tetap dipakai):
        A lonjakan tajam: |x - median| > max(k x MAD, d x median), hari sebelum & sesudah ada dan normal,
                          dan bukan salah input.
    """
    src = df.sort_values(SERI + ["tanggal"]).copy()
    x = src[value_col]
    w = o["jendela_median_hari"]
    roll = lambda s: s.rolling(w, center=True, min_periods=5).median()  # noqa: E731
    med = x.groupby(_by(src, SERI), observed=True).transform(roll)
    dev = (x - med).abs()
    mad = dev.groupby(_by(src, SERI), observed=True).transform(roll)

    menyimpang = (dev > np.maximum(o["k_mad"] * mad, o["lonjakan_deviasi_min"] * med)).where(x.notna())
    g = menyimpang.groupby(_by(src, SERI), observed=True)
    a = menyimpang.eq(True) & g.shift(1).eq(False) & g.shift(-1).eq(False)

    r = x / med
    b = (r >= o["rasio_ekstrem"]) | (r <= 1 / o["rasio_ekstrem"])
    med_lintas = x.groupby(_by(src, ["jenis_pasar_id", "komoditas_id", "tanggal"]), observed=True).transform("median")
    rl = x / med_lintas
    c = (rl >= o["rasio_lintas_kota"]) | (rl <= 1 / o["rasio_lintas_kota"])

    alasan = np.where(b & c, "rasio_ekstrem;lintas_kota", np.where(b, "rasio_ekstrem", np.where(c, "lintas_kota", "")))
    src["median_bergulir"] = med
    src["is_outlier_flag"] = (b | c).to_numpy()
    src["alasan_outlier"] = alasan
    src["is_lonjakan_tajam"] = (a & ~(b | c)).to_numpy()
    return src.loc[df.index]


# ---------------------------------------------------------------- celah & usang
def fill_short_gaps(df: pd.DataFrame, value_col: str, max_gap: int) -> tuple[pd.Series, pd.Series]:
    """Forward-fill celah (NaN berturut-turut) yang panjangnya <= max_gap hari kerja, per seri.

    Celah di awal seri (tanpa nilai sebelumnya) dan celah yang lebih panjang dibiarkan kosong.
    Mengembalikan (nilai_terisi, is_imputed) dengan index yang sama dengan df.
    """
    s = df.sort_values(SERI + ["tanggal"])
    x = s[value_col]
    keys = _by(s, SERI)
    isna = x.isna()
    run_id = (isna != isna.groupby(keys, observed=True).shift(fill_value=False)).cumsum()
    run_len = isna.groupby(run_id).transform("size")
    prev = x.groupby(keys, observed=True).ffill()
    imputed = isna & (run_len <= max_gap) & prev.notna()
    filled = x.where(~imputed, prev)
    return filled.loc[df.index], imputed.loc[df.index]


def stale_run_length(df: pd.DataFrame, value_col: str) -> pd.Series:
    """Berapa hari kerja berturut-turut harga sama persis dengan hari sebelumnya (0 = berubah / tidak ada data)."""
    s = df.sort_values(SERI + ["tanggal"])
    same = s[value_col].groupby(_by(s, SERI), observed=True).diff().eq(0)
    block = (~same).cumsum()
    run = same.astype(int).groupby(block).cumsum()
    return run.loc[df.index]


# ---------------------------------------------------------------- tabel kualitas
def _max_nan_run(x: pd.Series) -> int:
    m = np.concatenate([[0], x.isna().to_numpy().astype(int), [0]])
    d = np.diff(m)
    r = np.flatnonzero(d == -1) - np.flatnonzero(d == 1)
    return int(r.max()) if len(r) else 0


def build_quality_table(h: pd.DataFrame) -> pd.DataFrame:
    g = h.sort_values(SERI + ["tanggal"]).groupby(["jenis_pasar", "kualitas", "provinsi", "kota", "kota_id"],
                                                   observed=True)
    h = h.assign(_tgl_ada=h.tanggal.where(h.harga.notna()))
    g = h.sort_values(SERI + ["tanggal"]).groupby(["jenis_pasar", "kualitas", "provinsi", "kota", "kota_id"],
                                                   observed=True)
    q = g.agg(
        hari=("tanggal", "size"), data_pertama=("_tgl_ada", "min"), data_terakhir=("_tgl_ada", "max"),
        pct_kosong_asli=("harga", lambda s: s.isna().mean() * 100),
        hari_libur_isi=("is_libur_isi", "sum"), salah_input=("is_outlier_flag", "sum"),
        lonjakan_tajam=("is_lonjakan_tajam", "sum"), hari_diisi=("is_imputed", "sum"),
        pct_kosong_akhir=("harga_bersih", lambda s: s.isna().mean() * 100),
        celah_terpanjang_akhir=("harga_bersih", _max_nan_run),
        run_datar_maks=("run_datar", "max"), pct_usang=("is_usang", lambda s: s.mean() * 100),
    ).reset_index()
    return q.round({"pct_kosong_asli": 2, "pct_kosong_akhir": 2, "pct_usang": 1})


# ---------------------------------------------------------------- alur utama
def clean(cfg: dict) -> dict[str, pd.DataFrame]:
    c = cfg["cleaning"]
    raw = ROOT / cfg["paths"]["raw"]
    log.info("Memuat data mentah ...")
    df = load_raw_long(raw)
    n_awal = len(df)
    df = dedupe_latest(df)
    log.info("%d baris mentah, %d duplikat dibuang", n_awal, n_awal - len(df))

    # Referensi komoditas: komoditas = kategori (mis. "Cabai Merah"), kualitas = nama item ("Cabai Merah Keriting")
    kom_raw = json.loads((raw / "ref" / "commodity.json").read_text(encoding="utf-8"))["data"]
    kategori = {r["id"]: r["name"].strip() for r in kom_raw if r["id"].startswith("cat_")}
    kom = load_commodity_ref(raw)
    kom["komoditas"] = kom.kategori_id.map(kategori)
    kom = kom.rename(columns={"nama": "kualitas"}).set_index("komoditas_id")
    prov_ref = {r["id"]: r["name"].strip() for r in
                json.loads((raw / "ref" / "province.json").read_text(encoding="utf-8"))["data"]}

    # Pisahkan nasional (pembanding) dan kota; baris provinsi dibuang (= rata-rata kota)
    nasional = df[df.level == 0][["jenis_pasar_id", "komoditas_id", "tanggal", "harga"]].copy()
    kota = df[df.level == 2].drop(columns=["level"]).copy()
    kota = map_city_ids(kota, load_regency_ref(raw), c["duplikat_kota_dibuang"])
    beda = kota[kota.provinsi != kota.provinsi_id.map(prov_ref)]
    if len(beda):
        raise ValueError(f"Provinsi dari urutan baris tidak cocok dengan referensi: {beda[['nama', 'provinsi']].drop_duplicates().values.tolist()}")
    kota = kota.rename(columns={"nama": "kota"})
    semua_tanggal = pd.DatetimeIndex(sorted(df.tanggal.unique()))
    n_sebelum = len(kota)
    kota = complete_grid(kota, semua_tanggal)
    log.info("Grid dilengkapi: %d baris ditambahkan (bulan tanpa baris di data mentah)", len(kota) - n_sebelum)
    kota = kota.sort_values(SERI + ["tanggal"]).reset_index(drop=True)

    # 1) Hari libur yang diisi harga sebelumnya
    libur = detect_holiday_dates(kota, c["libur_ambang_tidak_berubah"])
    kota["is_libur_isi"] = kota.tanggal.isin(libur)
    kota["harga_kerja"] = kota.harga.where(~kota.is_libur_isi)

    # 2) Outlier dua tingkat, dihitung dari harga ASLI (bukan harga_kerja). Mengosongkan hari libur lebih dulu membuat
    #    jendela median kehilangan hari-hari harga lama, sehingga pada seri bertangga (produsen/pedagang besar) hari
    #    terakhir sebelum harga diperbarui salah tertandai. Salinan hari libur = harga hari sebelumnya, jadi tidak
    #    menciptakan lonjakan.
    kota = flag_outliers(kota, c["outlier"], "harga")
    kota["harga_bersih"] = kota.harga_kerja.where(~kota.is_outlier_flag)

    # 3) Isi celah pendek
    kota["harga_bersih"], kota["is_imputed"] = fill_short_gaps(kota, "harga_bersih", c["gap_ffill_maks_hari"])

    # 4) Data usang (dari harga asli: salinan hari libur memang melanjutkan harga yang sama)
    kota["run_datar"] = stale_run_length(kota, "harga")
    kota["is_usang"] = kota.run_datar >= c["usang_run_hari"]

    # Label
    kota["jenis_pasar"] = kota.jenis_pasar_id.map(JENIS_PASAR)
    kota["komoditas"] = kota.komoditas_id.map(kom.komoditas)
    kota["kualitas"] = kota.komoditas_id.map(kom.kualitas)
    kota["satuan"] = kota.komoditas_id.map(kom.satuan)
    harian = kota[[
        "tanggal", "jenis_pasar_id", "jenis_pasar", "provinsi_id", "provinsi", "kota_id", "kota",
        "komoditas_id", "komoditas", "kualitas", "satuan", "harga", "harga_bersih",
        "is_libur_isi", "is_outlier_flag", "alasan_outlier", "is_lonjakan_tajam", "is_imputed",
        "run_datar", "is_usang", "median_bergulir",
    ]].sort_values(KUNCI).reset_index(drop=True)

    # Nasional: tandai hari libur, isi celah pendek dengan aturan yang sama
    nasional["kota_id"] = 0
    nasional["is_libur_isi"] = nasional.tanggal.isin(libur)
    nasional["harga_kerja"] = nasional.harga.where(~nasional.is_libur_isi)
    nasional["harga_bersih"], nasional["is_imputed"] = fill_short_gaps(nasional, "harga_kerja", c["gap_ffill_maks_hari"])
    nasional["jenis_pasar"] = nasional.jenis_pasar_id.map(JENIS_PASAR)
    nasional["kualitas"] = nasional.komoditas_id.map(kom.kualitas)
    nasional = nasional.drop(columns=["kota_id", "harga_kerja"]).sort_values(
        ["jenis_pasar_id", "komoditas_id", "tanggal"]).reset_index(drop=True)

    kualitas = build_quality_table(harian)
    libur_df = pd.DataFrame({"tanggal": libur})
    return {"harian": harian, "nasional": nasional, "kualitas": kualitas, "libur": libur_df}


def write_report(out: dict[str, pd.DataFrame], cfg: dict, path: Path) -> None:
    h, q, lib = out["harian"], out["kualitas"], out["libur"]
    c = cfg["cleaning"]
    n = len(h)
    terisi_asli = h.harga.notna().sum()
    trad = h[h.jenis_pasar_id == 1]
    per_pasar = h.groupby("jenis_pasar", observed=True).agg(
        kota=("kota_id", "nunique"), baris=("harga", "size"),
        kosong_asli=("harga", lambda s: s.isna().mean() * 100),
        libur=("is_libur_isi", "mean"), salah_input=("is_outlier_flag", "sum"),
        lonjakan=("is_lonjakan_tajam", "sum"), diisi=("is_imputed", "sum"),
        kosong_akhir=("harga_bersih", lambda s: s.isna().mean() * 100),
        usang=("is_usang", lambda s: s.mean() * 100))
    per_pasar["libur"] *= 100
    outl = h[h.is_outlier_flag].groupby(["jenis_pasar", "kualitas", "kota", "alasan_outlier"], observed=True).agg(
        hari=("tanggal", "size"), mulai=("tanggal", "min"), selesai=("tanggal", "max"),
        harga_asli=("harga", "median"))
    tipis = q[q.pct_kosong_akhir > 10].sort_values("pct_kosong_akhir", ascending=False)

    def md_table(d: pd.DataFrame, fmt: dict | None = None) -> str:
        d = d.copy()
        for col, f in (fmt or {}).items():
            d[col] = d[col].map(f)
        cols = [str(x) for x in d.columns]
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, row in d.iterrows():
            lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
        return "\n".join(lines)

    pct = lambda v: f"{v:.2f}%"  # noqa: E731
    pp = per_pasar.reset_index()
    tgl = lambda v: pd.Timestamp(v).strftime("%Y-%m-%d")  # noqa: E731
    text = f"""# Laporan cleaning (Tahap 2)

Dibuat otomatis oleh `python -m src.clean` pada {datetime.now():%Y-%m-%d %H:%M}. Jangan diedit manual.
Aturan & alasannya: `notebooks/01_eda.ipynb`, `docs/data_profile.md`. Ambang: `config/config.yaml` bagian `cleaning`.

## Ringkasan
- Rentang: **{tgl(h.tanggal.min())} s/d {tgl(h.tanggal.max())}**, {h.tanggal.nunique()} hari kerja, 6 provinsi Pulau Jawa.
- Baris kota × hari: **{n:,}** ({h.kota_id.nunique()} kota/kab, {h.komoditas_id.nunique()} komoditas, 4 jenis pasar).
  Harga asli terisi {terisi_asli:,} ({terisi_asli / n:.2%}).
- Kota dibuang karena duplikat: id {c['duplikat_kota_dibuang']} ("Kota Surakarta" pasar modern; dipakai id 36).
- **Hari libur diisi harga sebelumnya:** {len(lib)} tanggal terdeteksi (> {c['libur_ambang_tidak_berubah']:.0%} seri
  pasar tradisional tidak berubah) → `is_libur_isi`, dikosongkan di `harga_bersih`. Daftar: `data/interim/libur_terdeteksi.csv`.
- **Salah input** (aturan B/C): **{int(h.is_outlier_flag.sum())} titik** → `is_outlier_flag`, dikosongkan di `harga_bersih`.
- **Lonjakan tajam** (aturan A, penanda saja): {int(h.is_lonjakan_tajam.sum())} titik → `is_lonjakan_tajam`, nilai tetap dipakai.
- **Celah ≤ {c['gap_ffill_maks_hari']} hari kerja diisi** (forward-fill): {int(h.is_imputed.sum()):,} titik → `is_imputed`.
- **Kosong akhir** di `harga_bersih`: {h.harga_bersih.isna().mean():.2%} (pasar tradisional {trad.harga_bersih.isna().mean():.2%}).
- **Data usang** (harga tetap ≥ {c['usang_run_hari']} hari kerja): {h.is_usang.mean():.2%} titik → `is_usang`.

## Per jenis pasar
{md_table(pp, {"kosong_asli": pct, "libur": pct, "kosong_akhir": pct, "usang": pct})}

Kolom: `kosong_asli` = % harga asli kosong; `libur` = % baris pada hari libur; `salah_input`, `lonjakan`, `diisi` = jumlah titik;
`kosong_akhir` = % `harga_bersih` kosong setelah cleaning; `usang` = % titik dengan harga tetap ≥ {c['usang_run_hari']} hari kerja.

## Salah input yang dikosongkan
{md_table(outl.reset_index(), {"mulai": tgl, "selesai": tgl, "harga_asli": lambda v: f"Rp {v:,.0f}"})}

## Seri dengan > 10% kosong setelah cleaning
Seri ini tetap disimpan, tetapi perlu dipertimbangkan sebelum dipakai di analisis.

{md_table(tipis[["jenis_pasar", "kualitas", "kota", "pct_kosong_akhir", "celah_terpanjang_akhir"]], {"pct_kosong_akhir": pct})}

## File keluaran
| File | Isi |
|---|---|
| `data/interim/harga_harian.parquet` | harga kota per hari kerja + penanda kualitas ({n:,} baris) |
| `data/interim/harga_nasional.parquet` | rata-rata nasional per jenis pasar × komoditas × hari ({len(out['nasional']):,} baris) |
| `data/interim/kualitas_data.csv` | tabel kualitas per jenis pasar × komoditas × kota ({len(q)} seri); salinan publik di `reports/kualitas_data.csv` |
| `data/interim/libur_terdeteksi.csv` | {len(lib)} tanggal hari libur yang terdeteksi |
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    out = clean(cfg)
    interim = ROOT / cfg["paths"]["interim"]
    interim.mkdir(parents=True, exist_ok=True)
    out["harian"].to_parquet(interim / "harga_harian.parquet", index=False)
    out["nasional"].to_parquet(interim / "harga_nasional.parquet", index=False)
    out["kualitas"].to_csv(interim / "kualitas_data.csv", index=False)
    (ROOT / "reports").mkdir(exist_ok=True)
    out["kualitas"].to_csv(ROOT / "reports" / "kualitas_data.csv", index=False)  # salinan publik (data/interim tidak di-push)
    out["libur"].to_csv(interim / "libur_terdeteksi.csv", index=False)
    write_report(out, cfg, ROOT / "docs" / "cleaning_report.md")
    h = out["harian"]
    log.info("Selesai: %d baris, %d hari libur, %d salah input, %d lonjakan tajam, %d diisi, %.2f%% kosong akhir",
             len(h), len(out["libur"]), h.is_outlier_flag.sum(), h.is_lonjakan_tajam.sum(), h.is_imputed.sum(),
             100 * h.harga_bersih.isna().mean())


if __name__ == "__main__":
    main()
