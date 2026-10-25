"""Tahap 3 — Feature engineering: dari harga harian bersih ke tabel mingguan siap analisis.

Input : data/interim/harga_harian.parquet, data/interim/harga_nasional.parquet (Tahap 2),
        data/reference/hari_besar.csv (tanggal resmi SKB), config/config.yaml (bagian `features`)
Output: data/interim/
    harga_mingguan.parquet     satu baris = kota x komoditas x jenis pasar x minggu (W-FRI) + fitur
    nasional_mingguan.parquet  rata-rata nasional mingguan per jenis pasar x komoditas + fitur
    kalender_mingguan.parquet  minggu, minggu_ke_idul_fitri, penanda hari besar
        docs/features_report.md   ringkasan otomatis

Harga mingguan dihitung HANYA dari pengamatan nyata (harga_bersih yang bukan is_imputed):
    median   : median hari nyata (pasar tradisional, dicatat setiap hari)
    terakhir : nilai nyata terakhir minggu itu (pedagang besar ~Kamis, modern ~Selasa-Rabu, produsen sesekali)
Alasan: notebooks/02_cleaning.ipynb §7.2.

Fitur per seri (tanpa look-ahead kecuali kolom yang memang membandingkan dengan masa lalu):
    log_return, pct_wow (vs minggu lalu), pct_yoy (vs 52 minggu lalu), pct_4w (vs 4 minggu lalu),
    harga_ma{w}, vol_{w} (std log_return w minggu),
    zscore (LEVEL harga vs rata-rata & std 52 minggu SEBELUMNYA),
    zscore_return (KENAIKAN mingguan vs log_return 52 minggu SEBELUMNYA; aturan peringatan Q6),
    selisih_nasional_rp / _pct, minggu_ke_idul_fitri.
"""
from __future__ import annotations

import argparse
import logging
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"
SERI = ["jenis_pasar_id", "komoditas_id", "kota_id"]
FREQ = "W-FRI"

log = logging.getLogger("features")


# ---------------------------------------------------------------- agregasi mingguan
def weekly_aggregate(df: pd.DataFrame, agg_map: dict, seri: list[str], min_hari: int, freq: str = FREQ) -> pd.DataFrame:
    """Satu harga per seri x minggu dari pengamatan nyata. Grid lengkap: setiap seri punya setiap minggu.

    Kolom keluaran: seri..., minggu, minggu_akhir, metode, harga, n_hari_nyata, tanggal_nilai, is_usang, minggu_tipis.
    """
    d = df.assign(minggu=df.tanggal.dt.to_period(freq))
    nyata = d[d.harga_bersih.notna() & ~d.is_imputed.astype(bool)].sort_values(seri + ["tanggal"])
    metode = d.jenis_pasar_id.map(agg_map)
    if metode.isna().any():
        raise ValueError(f"agregasi_mingguan tidak mengatur jenis pasar: {sorted(d.jenis_pasar_id[metode.isna()].unique())}")

    key = seri + ["minggu"]
    g = nyata.groupby(key, observed=True)
    stat = pd.DataFrame({
        "median": g.harga_bersih.median(), "terakhir": g.harga_bersih.last(),
        "n_hari_nyata": g.size(), "tanggal_nilai": g.tanggal.max(), "is_usang": g.is_usang.last(),
    }).reset_index()

    semua_minggu = pd.period_range(d.tanggal.min(), d.tanggal.max(), freq=freq)
    grid = d[seri].drop_duplicates().merge(pd.DataFrame({"minggu": semua_minggu}), how="cross")
    out = grid.merge(stat, on=key, how="left")
    out["metode"] = out.jenis_pasar_id.map(agg_map)
    out["harga"] = np.where(out.metode == "median", out["median"], out["terakhir"])
    out["n_hari_nyata"] = out.n_hari_nyata.fillna(0).astype(int)
    out["is_usang"] = out.is_usang.astype("boolean").fillna(False).astype(bool)
    out["minggu_tipis"] = np.where(out.metode == "median", out.n_hari_nyata < min_hari, out.n_hari_nyata == 0)
    out["minggu_akhir"] = out.minggu.dt.end_time.dt.normalize()
    cols = seri + ["minggu", "minggu_akhir", "metode", "harga", "n_hari_nyata", "tanggal_nilai", "is_usang", "minggu_tipis"]
    return out[cols].sort_values(seri + ["minggu"]).reset_index(drop=True)


# ---------------------------------------------------------------- fitur seri
def add_series_features(w: pd.DataFrame, f: dict, seri: list[str] = SERI) -> pd.DataFrame:
    """Fitur per seri. Mengasumsikan setiap seri punya minggu berurutan (grid lengkap)."""
    w = w.sort_values(seri + ["minggu"]).copy()
    by = [w[c] for c in seri]
    h = w.harga
    prev = h.groupby(by, observed=True).shift(1)
    w["log_return"] = np.log(h / prev)
    w["pct_wow"] = h / prev - 1
    w["pct_yoy"] = h / h.groupby(by, observed=True).shift(f["yoy_lag_minggu"]) - 1
    # Perubahan N minggu terakhir (brief Q6: lonjakan = kenaikan >= X% dalam 4 minggu). Melihat ke BELAKANG saja.
    w[f"pct_{f['perubahan_lag_minggu']}w"] = h / h.groupby(by, observed=True).shift(f["perubahan_lag_minggu"]) - 1
    # z-score KENAIKAN mingguan (brief Q6: "z-score kenaikan mingguan > 2"): log_return minggu ini dibanding
    # rata-rata & std log_return N minggu SEBELUMNYA (tanpa minggu berjalan, tanpa look-ahead).
    lr_lalu = w.log_return.groupby(by, observed=True).shift(1)
    rb, rm = f["zscore_return_baseline_minggu"], f["zscore_return_min_minggu"]
    lr_mean = lr_lalu.groupby(by, observed=True).transform(lambda s: s.rolling(rb, min_periods=rm).mean())
    lr_std = lr_lalu.groupby(by, observed=True).transform(lambda s: s.rolling(rb, min_periods=rm).std())
    w["zscore_return"] = (w.log_return - lr_mean) / lr_std.replace(0, np.nan)
    for win in f["rolling_minggu"]:
        mp = max(2, math.ceil(win / 2))
        w[f"harga_ma{win}"] = h.groupby(by, observed=True).transform(lambda s: s.rolling(win, min_periods=mp).mean())
        w[f"vol_{win}"] = w.log_return.groupby(by, observed=True).transform(lambda s: s.rolling(win, min_periods=mp).std())
    nb, nm = f["zscore_baseline_minggu"], f["zscore_min_minggu"]
    lalu = h.groupby(by, observed=True).shift(1)  # baseline TIDAK memuat minggu berjalan
    mean = lalu.groupby(by, observed=True).transform(lambda s: s.rolling(nb, min_periods=nm).mean())
    std = lalu.groupby(by, observed=True).transform(lambda s: s.rolling(nb, min_periods=nm).std())
    w["zscore"] = (h - mean) / std.replace(0, np.nan)
    return w


# ---------------------------------------------------------------- kalender
def build_calendar(minggu: pd.PeriodIndex, hari_besar: pd.DataFrame, jendela: tuple[int, int]) -> pd.DataFrame:
    """Tabel minggu: minggu_ke_idul_fitri (minggu 0 = minggu yang memuat tanggal Idulfitri) & penanda hari besar."""
    kal = pd.DataFrame({"minggu": minggu})
    kal["minggu_akhir"] = kal.minggu.dt.end_time.dt.normalize()
    kal["minggu_mulai_kerja"] = kal.minggu_akhir - pd.Timedelta(days=4)  # Senin
    kal["tahun"] = kal.minggu_akhir.dt.year
    kal["bulan"] = kal.minggu_akhir.dt.month

    lo, hi = jendela
    kal["minggu_ke_idul_fitri"] = np.nan
    kal["tahun_idul_fitri"] = np.nan
    ordinal = np.array([p.ordinal for p in kal.minggu])
    for _, r in hari_besar[hari_besar.jenis == "idul_fitri"].iterrows():
        nol = pd.Period(r.tanggal, freq=minggu.freq).ordinal
        off = ordinal - nol
        m = (off >= lo) & (off <= hi) & kal.minggu_ke_idul_fitri.isna().to_numpy()
        kal.loc[m, "minggu_ke_idul_fitri"] = off[m]
        kal.loc[m, "tahun_idul_fitri"] = r.tanggal.year

    nama, ada = [], []
    for _, k in kal.iterrows():
        hit = hari_besar[(hari_besar.libur_mulai <= k.minggu_akhir) & (hari_besar.libur_selesai >= k.minggu_mulai_kerja)]
        ada.append(len(hit) > 0)
        nama.append("; ".join(hit.nama))
    kal["ada_libur_hari_besar"] = ada
    kal["nama_hari_besar"] = nama
    kal["minggu_ke_idul_fitri"] = kal.minggu_ke_idul_fitri.astype("Int64")
    kal["tahun_idul_fitri"] = kal.tahun_idul_fitri.astype("Int64")
    return kal


# ---------------------------------------------------------------- alur utama
def build(cfg: dict) -> dict[str, pd.DataFrame]:
    f, c = cfg["features"], cfg["cleaning"]
    interim = ROOT / cfg["paths"]["interim"]
    harian = pd.read_parquet(interim / "harga_harian.parquet")
    nasional = pd.read_parquet(interim / "harga_nasional.parquet")
    hb = pd.read_csv(ROOT / cfg["paths"]["reference"] / "hari_besar.csv",
                     parse_dates=["tanggal", "libur_mulai", "libur_selesai"])
    agg = {int(k): v for k, v in f["agregasi_mingguan"].items()}

    # Kota
    w = weekly_aggregate(harian, agg, SERI, c["minggu_min_hari_nyata"], f["frekuensi"])
    w = add_series_features(w, f)
    atribut = harian.drop_duplicates(SERI)[SERI + ["jenis_pasar", "provinsi_id", "provinsi", "kota", "komoditas",
                                                  "kualitas", "satuan"]]
    w = w.merge(atribut, on=SERI, how="left")
    ex = pd.DataFrame(f["seri_dikecualikan"]).rename(columns={"alasan": "alasan_dikecualikan"})
    w = w.merge(ex, on=SERI, how="left")
    w["is_seri_dikecualikan"] = w.alasan_dikecualikan.notna()
    w["alasan_dikecualikan"] = w.alasan_dikecualikan.fillna("")

    # Nasional (jenis pasar yang sama, cara agregasi yang sama)
    nas = nasional.assign(kota_id=0, is_usang=False)
    nw = weekly_aggregate(nas, agg, SERI, c["minggu_min_hari_nyata"], f["frekuensi"])
    nw = add_series_features(nw, f).drop(columns="kota_id")
    nw = nw.merge(nasional.drop_duplicates(["jenis_pasar_id", "komoditas_id"])[
        ["jenis_pasar_id", "komoditas_id", "jenis_pasar", "kualitas"]], on=["jenis_pasar_id", "komoditas_id"])
    ref = nw[["jenis_pasar_id", "komoditas_id", "minggu", "harga"]].rename(columns={"harga": "harga_nasional"})
    w = w.merge(ref, on=["jenis_pasar_id", "komoditas_id", "minggu"], how="left")
    w["selisih_nasional_rp"] = w.harga - w.harga_nasional
    w["selisih_nasional_pct"] = w.harga / w.harga_nasional - 1

    # Kalender & minggu ke Idulfitri
    kal = build_calendar(pd.period_range(harian.tanggal.min(), harian.tanggal.max(), freq=f["frekuensi"]),
                         hb, tuple(f["idul_fitri_jendela"]))
    w = w.merge(kal[["minggu", "minggu_ke_idul_fitri", "tahun_idul_fitri", "ada_libur_hari_besar"]], on="minggu", how="left")
    nw = nw.merge(kal[["minggu", "minggu_ke_idul_fitri", "tahun_idul_fitri"]], on="minggu", how="left")

    urut = SERI + ["jenis_pasar", "provinsi_id", "provinsi", "kota", "komoditas", "kualitas", "satuan",
                   "minggu", "minggu_akhir", "metode", "harga", "n_hari_nyata", "tanggal_nilai", "minggu_tipis", "is_usang",
                   "log_return", "pct_wow", "pct_yoy"]
    urut += [x for x in w.columns if x.startswith(("harga_ma", "vol_"))]
    urut += [f"pct_{f['perubahan_lag_minggu']}w", "zscore", "zscore_return",
             "harga_nasional", "selisih_nasional_rp", "selisih_nasional_pct",
             "minggu_ke_idul_fitri", "tahun_idul_fitri", "ada_libur_hari_besar", "is_seri_dikecualikan", "alasan_dikecualikan"]
    w = w[urut].sort_values(SERI + ["minggu"]).reset_index(drop=True)
    for t in (w, nw, kal):
        t["minggu"] = t.minggu.astype(str)  # parquet/Power BI tidak mengenal Period
    return {"mingguan": w, "nasional": nw, "kalender": kal}


def write_report(out: dict[str, pd.DataFrame], cfg: dict, path: Path) -> None:
    w, kal = out["mingguan"], out["kalender"]
    f = cfg["features"]
    pakai = w[~w.is_seri_dikecualikan]
    per = pakai.groupby("jenis_pasar").agg(
        seri=("kota_id", lambda s: s.size), metode=("metode", "first"),
        minggu_ada_harga=("harga", lambda s: s.notna().mean() * 100),
        minggu_tipis=("minggu_tipis", lambda s: s.mean() * 100),
        rata_hari_nyata=("n_hari_nyata", "mean"))
    per["seri"] = (pakai.groupby("jenis_pasar")[SERI].apply(lambda d: d.drop_duplicates().shape[0]))
    trad = pakai[pakai.jenis_pasar_id == 1]
    vol = (trad.groupby("kualitas").log_return.std() * 100).sort_values(ascending=False)
    if_ = kal.dropna(subset=["minggu_ke_idul_fitri"]).groupby("tahun_idul_fitri").agg(
        minggu_pertama=("minggu_akhir", "min"), minggu_terakhir=("minggu_akhir", "max"), jumlah=("minggu", "size"))

    def md_table(d: pd.DataFrame) -> str:
        cols = [str(x) for x in d.columns]
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in d.itertuples(index=False)]
        return "\n".join(lines)

    perr = per.reset_index()
    for col in ("minggu_ada_harga", "minggu_tipis"):
        perr[col] = perr[col].map(lambda v: f"{v:.1f}%")
    perr["rata_hari_nyata"] = perr.rata_hari_nyata.map(lambda v: f"{v:.2f}")
    volr = vol.round(2).rename("std log-return mingguan (%)").reset_index()
    ifr = if_.reset_index()
    for col in ("minggu_pertama", "minggu_terakhir"):
        ifr[col] = ifr[col].dt.strftime("%Y-%m-%d")
    text = f"""# Laporan feature engineering (Tahap 3)

Dibuat otomatis oleh `python -m src.features` pada {datetime.now():%Y-%m-%d %H:%M}. Jangan diedit manual.
Parameter: `config/config.yaml` bagian `features`. Tanggal hari besar: `data/reference/hari_besar.csv`.

## Ringkasan
- **{w.minggu.nunique()} minggu** (W-FRI) dari {w.minggu_akhir.min():%Y-%m-%d} s/d {w.minggu_akhir.max():%Y-%m-%d};
  {w[SERI].drop_duplicates().shape[0]} seri kota × komoditas × jenis pasar → **{len(w):,} baris** `harga_mingguan`.
- {int(w[SERI + ['is_seri_dikecualikan']].drop_duplicates().is_seri_dikecualikan.sum())} seri ditandai
  `is_seri_dikecualikan` (bolong / kasus batas, lihat config); tetap disimpan.
- Harga mingguan hanya dari pengamatan nyata. Cara: {', '.join(f'{k}={v}' for k, v in f['agregasi_mingguan'].items())}
  (1 tradisional, 2 modern, 3 pedagang besar, 4 produsen).
- Fitur: log_return, pct_wow, pct_yoy ({f['yoy_lag_minggu']} minggu), pct_{f['perubahan_lag_minggu']}w,
  rata-rata bergerak & gejolak {f['rolling_minggu']} minggu,
  zscore level harga vs {f['zscore_baseline_minggu']} minggu sebelumnya (min {f['zscore_min_minggu']}),
  zscore_return kenaikan mingguan vs {f['zscore_return_baseline_minggu']} minggu sebelumnya
  (min {f['zscore_return_min_minggu']}), selisih vs nasional, minggu_ke_idul_fitri {f['idul_fitri_jendela']}.
- Pasar tradisional, minggu dengan `zscore_return` > 2 (calon peringatan Q6):
  {(w[(w.jenis_pasar_id == 1) & ~w.is_seri_dikecualikan].zscore_return > 2).mean():.1%} dari seluruh seri-minggu.

## Per jenis pasar (seri yang dipakai)
{md_table(perr)}

## Gejolak mingguan pasar tradisional (pratinjau Q1)
Simpangan baku perubahan harga mingguan (log-return), semua kota digabung. Angka awal; analisis lengkap di Tahap 4.

{md_table(volr)}

## Jendela Idulfitri (minggu −12 s/d +4)
{md_table(ifr)}

Minggu 0 = minggu (Sabtu–Jumat) yang memuat tanggal Idulfitri menurut SKB.

## File keluaran
| File | Baris |
|---|---|
| `data/interim/harga_mingguan.parquet` | {len(w):,} |
| `data/interim/nasional_mingguan.parquet` | {len(out['nasional']):,} |
| `data/interim/kalender_mingguan.parquet` | {len(kal):,} |
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    out = build(cfg)
    interim = ROOT / cfg["paths"]["interim"]
    out["mingguan"].to_parquet(interim / "harga_mingguan.parquet", index=False)
    out["nasional"].to_parquet(interim / "nasional_mingguan.parquet", index=False)
    out["kalender"].to_parquet(interim / "kalender_mingguan.parquet", index=False)
    write_report(out, cfg, ROOT / "docs" / "features_report.md")
    w = out["mingguan"]
    log.info("Selesai: %d baris mingguan, %d minggu, %d seri, %.1f%% minggu berharga",
             len(w), w.minggu.nunique(), w[SERI].drop_duplicates().shape[0], 100 * w.harga.notna().mean())


if __name__ == "__main__":
    main()
