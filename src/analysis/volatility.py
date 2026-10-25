"""Q1 — Komoditas mana yang paling bergejolak, dan di kota mana?

Ukuran gejolak (per kota x komoditas, pasar tradisional, data mingguan):
    gejolak_mingguan    std log-return mingguan (ukuran utama; tidak terpengaruh tren harga)
    rata_perubahan_abs  rata-rata |perubahan % minggu ke minggu|  -> bahasa dashboard: "harga rata-rata berubah x% per minggu"
    cv                  koefisien variasi harga (std / rata-rata) sepanjang periode (dipengaruhi tren & musim)

Output: reports/tables/q1_*.csv, reports/figures/q1_*.png, reports/q1_gejolak.md
"""
from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from src.analysis.common import (
    BLUE, GRAY, INK, INK2, KOMODITAS_URUT, LABEL_PENDEK, ORANGE, ROOT, TEAL, load_cfg, load_weekly, pct, save_fig,
    save_table, style,
)

import matplotlib.pyplot as plt  # noqa: E402  (backend diatur di common)


def series_volatility(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = df.groupby(keys, observed=True)
    out = g.agg(
        n_minggu_return=("log_return", "count"),
        gejolak_mingguan=("log_return", "std"),
        rata_perubahan_abs=("pct_wow", lambda s: s.abs().mean()),
        harga_rata=("harga", "mean"),
        harga_std=("harga", "std"),
        harga_min=("harga", "min"),
        harga_maks=("harga", "max"),
        kenaikan_mingguan_maks=("pct_wow", "max"),
    ).reset_index()
    out["cv"] = out.harga_std / out.harga_rata
    return out


def run(cfg: dict) -> dict:
    q = cfg["analisis"]["q1_gejolak"]
    w = load_weekly(cfg)
    trad = w[w.jenis_pasar_id == q["jenis_pasar_id"]]
    keys = ["provinsi", "kota_id", "kota", "kualitas"]

    per_seri = series_volatility(trad, keys)
    per_seri = per_seri[per_seri.n_minggu_return >= q["min_minggu"]].copy()
    per_seri["peringkat_dalam_komoditas"] = per_seri.groupby("kualitas").gejolak_mingguan.rank(ascending=False).astype(int)

    per_kom = per_seri.groupby("kualitas").agg(
        kota=("kota", "size"),
        gejolak_median=("gejolak_mingguan", "median"),
        gejolak_min=("gejolak_mingguan", "min"),
        gejolak_maks=("gejolak_mingguan", "max"),
        rata_perubahan_abs_median=("rata_perubahan_abs", "median"),
        cv_median=("cv", "median"),
    ).reindex(KOMODITAS_URUT).dropna(how="all").reset_index()
    per_kom = per_kom.sort_values("gejolak_median", ascending=False).reset_index(drop=True)
    per_kom["peringkat"] = np.arange(1, len(per_kom) + 1)
    teratas = (per_seri.sort_values("gejolak_mingguan", ascending=False).groupby("kualitas").head(q["top_n_kota"])
               .sort_values(["kualitas", "gejolak_mingguan"], ascending=[True, False]))
    per_kom["kota_paling_bergejolak"] = per_kom.kualitas.map(
        teratas.groupby("kualitas").kota.apply(lambda s: ", ".join(s.head(3))))

    # Gejolak per tahun: apakah urutan komoditas stabil?
    trad_tahun = trad.assign(tahun=trad.minggu_akhir.dt.year)
    per_tahun = (series_volatility(trad_tahun, ["tahun", "kota", "kualitas"])
                 .query("n_minggu_return >= 20").groupby(["tahun", "kualitas"]).gejolak_mingguan.median()
                 .unstack("tahun").reindex(KOMODITAS_URUT).reset_index())

    # Pembanding: pasar modern (diberi catatan: jarang diperbarui)
    mod = w[w.jenis_pasar_id == q["pembanding_jenis_pasar_id"]]
    per_seri_mod = series_volatility(mod, keys)
    datar = lambda d: d.groupby("kualitas").pct_wow.apply(lambda s: (s == 0).mean())  # noqa: E731
    banding = pd.DataFrame({
        "gejolak_median_tradisional": per_seri.groupby("kualitas").gejolak_mingguan.median(),
        "gejolak_median_modern": per_seri_mod.groupby("kualitas").gejolak_mingguan.median(),
        "porsi_minggu_tanpa_perubahan_tradisional": datar(trad),
        "porsi_minggu_tanpa_perubahan_modern": datar(mod),
    }).reindex(KOMODITAS_URUT).reset_index().rename(columns={"index": "kualitas"})

    return {"per_seri": per_seri, "per_kom": per_kom, "teratas": teratas, "per_tahun": per_tahun, "banding": banding}


def figures(res: dict) -> dict:
    style()
    out = {}
    pk, ps = res["per_kom"], res["per_seri"]
    teratas_kom = pk.kualitas.iloc[0]

    # 1) Sebaran gejolak antar kota per komoditas (dot plot, median ditandai)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    urut = list(pk.kualitas)[::-1]
    for i, k in enumerate(urut):
        v = ps[ps.kualitas == k].gejolak_mingguan * 100
        ax.scatter(v, np.full(len(v), i) + np.random.default_rng(i).uniform(-0.15, 0.15, len(v)), s=14,
                   color=ORANGE if k == teratas_kom else TEAL, alpha=0.55, edgecolor="none")
        ax.plot([v.median()] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
    ax.set_yticks(range(len(urut)), [LABEL_PENDEK[k] for k in urut])
    ax.set_xlabel("naik-turun harga dari minggu ke minggu (%), satu titik = satu kota; garis = median")
    ax.set_xlim(left=0)
    ax.set_title(f"Harga {LABEL_PENDEK[teratas_kom].lower()} paling bergejolak, terutama di "
                 f"{pk.kota_paling_bergejolak.iloc[0].split(', ')[0]}")
    out["dotplot"] = save_fig(fig, "q1_gejolak_per_komoditas")

    # 2) Heatmap kota x komoditas
    hm = ps.pivot_table(index="kota", columns="kualitas", values="gejolak_mingguan").reindex(columns=list(pk.kualitas))
    hm = hm.loc[hm.mean(axis=1).sort_values(ascending=False).index] * 100
    fig, ax = plt.subplots(figsize=(7.5, 10))
    im = ax.imshow(hm.values, cmap="Blues", aspect="auto", vmin=0)
    ax.set_xticks(range(hm.shape[1]), [LABEL_PENDEK[c] for c in hm.columns], rotation=30, ha="right")
    ax.set_yticks(range(hm.shape[0]), [k.replace("Kota ", "").replace("Kab. ", "Kab. ") for k in hm.index], fontsize=8)
    ax.grid(False)
    for i in range(hm.shape[0]):
        for j in range(hm.shape[1]):
            val = hm.iat[i, j]
            if pd.notna(val):
                ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if val > np.nanmax(hm.values) * 0.6 else INK)
    # Judul dari data: apakah kota PALING TENANG untuk 2 komoditas teratas masih lebih bergejolak daripada
    # kota PALING BERGEJOLAK untuk 3 komoditas terbawah?
    atas, bawah = list(pk.kualitas[:2]), list(pk.kualitas[-3:])
    min_atas = ps[ps.kualitas.isin(atas)].gejolak_mingguan.min()
    maks_bawah = ps[ps.kualitas.isin(bawah)].gejolak_mingguan.max()
    lingkup = "di semua kota" if min_atas > maks_bawah else "di sebagian besar kota"
    nama = lambda ks: ", ".join(LABEL_PENDEK[k].lower() for k in ks)  # noqa: E731
    ax.set_title(f"{nama(atas).capitalize()} bergejolak {lingkup};\n{nama(bawah)} relatif tenang")
    fig.colorbar(im, ax=ax, shrink=0.6, label="naik-turun harga per minggu (%)")
    out["heatmap"] = save_fig(fig, "q1_heatmap_kota_komoditas")
    return out


def write_summary(res: dict, figs: dict) -> None:
    pk, b, pt = res["per_kom"], res["banding"], res["per_tahun"]
    a = pk.iloc[0]
    baris = []
    for r in pk.itertuples():
        baris.append(f"| {r.peringkat} | {LABEL_PENDEK[r.kualitas]} | {pct(r.gejolak_median, 1)} | "
                     f"{pct(r.gejolak_min, 1)}–{pct(r.gejolak_maks, 1)} | {pct(r.rata_perubahan_abs_median, 1)} | "
                     f"{r.kota_paling_bergejolak} |")
    banding = "\n".join(
        f"| {LABEL_PENDEK[r.kualitas]} | {pct(r.gejolak_median_tradisional, 1)} | {pct(r.gejolak_median_modern, 1)} | "
        f"{pct(r.porsi_minggu_tanpa_perubahan_tradisional)} | {pct(r.porsi_minggu_tanpa_perubahan_modern)} |"
        for r in b.itertuples())
    tahun_cols = [c for c in pt.columns if c != "kualitas"]
    per_tahun = "\n".join(
        f"| {LABEL_PENDEK[r['kualitas']]} | " + " | ".join(pct(r[c], 1) if pd.notna(r[c]) else "–" for c in tahun_cols) + " |"
        for _, r in pt.iterrows())
    top3 = res["teratas"].groupby("kualitas").head(3)
    sering = top3.kota.value_counts()
    sering = sering[sering >= 3]
    catatan_kota = ""
    if len(sering):
        daftar = ", ".join(f"{k} ({v} dari {top3.kualitas.nunique()} komoditas)" for k, v in sering.items())
        catatan_kota = (f"\n**Catatan:** {daftar} berulang kali masuk 3 kota paling bergejolak. Bisa mencerminkan kondisi "
                        "pasar setempat, tetapi juga sampel PIHPS yang kecil (2 pasar × 2 pedagang per kota) sehingga harga "
                        "lebih berisik. Perlakukan sebagai sinyal untuk dicek, bukan kesimpulan pasti.\n")
    text = f"""# Q1 — Gejolak harga

Dibuat otomatis oleh `python -m src.analysis.volatility` pada {datetime.now():%Y-%m-%d %H:%M}.
Data: pasar tradisional, harga mingguan (median hari nyata), {int(pk.kota.max())} kota/kab di Pulau Jawa,
Juli 2023 – Oktober 2026. Ukuran utama: simpangan baku perubahan harga mingguan (log-return).

## Temuan (bahasa dashboard)
**Harga {LABEL_PENDEK[a.kualitas].lower()} paling bergejolak, terutama di {a.kota_paling_bergejolak}.**
Harganya naik-turun rata-rata {pct(a.rata_perubahan_abs_median, 0)} per minggu (median antar kota), dibanding
{pct(pk.iloc[-1].rata_perubahan_abs_median, 0)} untuk {LABEL_PENDEK[pk.iloc[-1].kualitas].lower()}.
Tindakan: pantau cabai setiap minggu dan siapkan stok penyangga; komoditas yang tenang cukup dipantau bulanan.

## Peringkat komoditas
| # | Komoditas | Gejolak mingguan (median kota) | Rentang antar kota | Rata-rata perubahan/minggu | 3 kota paling bergejolak |
|---|---|---|---|---|---|
{chr(10).join(baris)}
{catatan_kota}
## Konsistensi antar tahun (median gejolak mingguan antar kota)
| Komoditas | {' | '.join(str(c) for c in tahun_cols)} |
|---|{'---|' * len(tahun_cols)}
{per_tahun}

2023 = Juli–Desember; 2026 = Januari–Oktober.

## Pasar tradisional vs pasar modern (pembanding, dengan catatan)
| Komoditas | Gejolak tradisional | Gejolak modern | Minggu tanpa perubahan (tradisional) | Minggu tanpa perubahan (modern) |
|---|---|---|---|---|
{banding}

Catatan: pasar modern hanya diperbarui Selasa–Rabu dan banyak minggu tanpa perubahan sama sekali, sehingga gejolaknya
tampak lebih rendah. Perbedaan ini sebagian besar mencerminkan cara pencatatan, bukan harga yang benar-benar lebih stabil.

## File
- Tabel: `reports/tables/q1_gejolak_per_kota.csv`, `q1_gejolak_per_komoditas.csv`, `q1_gejolak_per_tahun.csv`,
  `q1_tradisional_vs_modern.csv`
- Grafik: `reports/figures/{figs['dotplot'].name}`, `reports/figures/{figs['heatmap'].name}`
"""
    (ROOT / "reports" / "q1_gejolak.md").write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, _ = load_cfg()
    res = run(cfg)
    save_table(res["per_seri"].sort_values(["kualitas", "peringkat_dalam_komoditas"]), "q1_gejolak_per_kota")
    save_table(res["per_kom"], "q1_gejolak_per_komoditas")
    save_table(res["per_tahun"], "q1_gejolak_per_tahun")
    save_table(res["banding"], "q1_tradisional_vs_modern")
    figs = figures(res)
    write_summary(res, figs)
    print(res["per_kom"][["peringkat", "kualitas", "gejolak_median", "rata_perubahan_abs_median", "kota_paling_bergejolak"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
