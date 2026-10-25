"""Q4 — Berapa minggu sebelum Idulfitri harga mulai naik signifikan, dan seberapa besar kenaikannya per komoditas?

Event study (pasar tradisional, harga mingguan):
    harga normal  = rata-rata harga minggu -12 s/d -9 sebelum Idulfitri, per kota x komoditas x tahun
    kenaikan      = harga minggu w / harga normal - 1, untuk w = -8 ... +4 (minggu 0 = minggu yang memuat Idulfitri)
    per tahun     = median kenaikan antar kota; rata-rata 3 tahun + rentang antar tahun (min-maks), bukan hanya rata-rata
    mulai naik    = minggu paling awal w <= -1 sehingga setiap minggu dari w sampai -1 kenaikannya >= ambang
                    pada >= min_tahun dari 3 tahun
    puncak        = minggu dengan rata-rata kenaikan tertinggi di jendela

Batasan: hanya 3 kali Idulfitri (2024, 2025, 2026); minggu 0 tahun 2024 & 2025 tanpa pencatatan (libur Lebaran);
kenaikan bisa bercampur dengan musim panen/hujan yang kebetulan berdekatan.

Output: reports/tables/q4_*.csv, reports/figures/q4_*.png, reports/q4_pola_idul_fitri.md
"""
from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from src.analysis.common import (
    BLUE, GRAY, INK, INK2, KOMODITAS_URUT, LABEL_PENDEK, ORANGE, ROOT, TEAL, load_cfg, load_weekly, save_fig, save_table,
    style,
)

import matplotlib.pyplot as plt  # noqa: E402


def event_relative(df: pd.DataFrame, baseline: tuple[int, int], window: tuple[int, int]) -> pd.Series:
    """df: satu seri (satu kota x komoditas x tahun) dengan kolom minggu_ke_idul_fitri & harga.
    Mengembalikan kenaikan relatif terhadap harga normal untuk setiap minggu di jendela (index = minggu)."""
    s = df.set_index("minggu_ke_idul_fitri").harga
    normal = s.loc[baseline[0]:baseline[1]].mean()
    idx = range(window[0], window[1] + 1)
    return (s.reindex(idx) / normal - 1) if pd.notna(normal) and normal > 0 else pd.Series(np.nan, index=idx)


def onset_week(tab: pd.DataFrame, ambang: float, min_tahun: int) -> int | None:
    """tab: index = minggu, kolom = tahun, nilai = kenaikan. Minggu paling awal (<= -1) yang memenuhi syarat sampai -1."""
    pra = tab.loc[:-1]
    memenuhi = (pra >= ambang).sum(axis=1) >= min_tahun
    hasil = None
    for w in sorted(pra.index, reverse=True):  # -1, -2, ... mundur selama syarat terpenuhi
        if memenuhi.loc[w]:
            hasil = int(w)
        else:
            break
    return hasil


def run(cfg: dict) -> dict:
    q = cfg["analisis"]["q4_musiman"]
    w = load_weekly(cfg)
    t = w[(w.jenis_pasar_id == q["jenis_pasar_id"]) & w.tahun_idul_fitri.notna()].copy()
    t["minggu_ke_idul_fitri"] = t.minggu_ke_idul_fitri.astype(int)
    t["tahun_idul_fitri"] = t.tahun_idul_fitri.astype(int)
    base, win = tuple(q["baseline_minggu"]), tuple(q["jendela_minggu"])
    rows = []
    for (kom, kota, th), g in t.groupby(["kualitas", "kota", "tahun_idul_fitri"]):
        rel = event_relative(g, base, win)
        rows += [{"kualitas": kom, "kota": kota, "tahun_idul_fitri": th, "minggu_ke_idul_fitri": m, "kenaikan": v}
                 for m, v in rel.items()]
    per_kota = pd.DataFrame(rows)
    per_tahun = (per_kota.groupby(["kualitas", "tahun_idul_fitri", "minggu_ke_idul_fitri"])
                 .agg(kenaikan_median_kota=("kenaikan", "median"), kota=("kenaikan", "count")).reset_index())
    ringkas = []
    for kom in KOMODITAS_URUT:
        tab = per_tahun[per_tahun.kualitas == kom].pivot(index="minggu_ke_idul_fitri", columns="tahun_idul_fitri",
                                                         values="kenaikan_median_kota")
        rata = tab.mean(axis=1)
        mulai = onset_week(tab, q["ambang_naik"], q["min_tahun_naik"])
        pk = rata.idxmax()
        pra = tab.loc[:-1]
        ringkas.append({
            "kualitas": kom, "mulai_naik_minggu": mulai,
            # mulai == awal jendela: harga sudah tinggi sejak minggu pertama yang diamati -> awal kenaikan sebenarnya
            # bisa lebih awal; dilaporkan sebagai ">= N minggu"
            "mulai_di_batas_jendela": mulai is not None and mulai == win[0],
            "tahun_konsisten": f"{int((tab.loc[-1] >= q['ambang_naik']).sum())} dari {tab.shape[1]}",
            "puncak_minggu": int(pk), "puncak_kenaikan_rata": float(rata.loc[pk]),
            "puncak_kenaikan_min_tahun": float(tab.loc[pk].min()), "puncak_kenaikan_maks_tahun": float(tab.loc[pk].max()),
            "kenaikan_minggu_min1_rata": float(rata.loc[-1]),
            "kenaikan_minggu_min1_per_tahun": "; ".join(f"{c}: {v:+.0%}" for c, v in tab.loc[-1].items()),
            "kenaikan_pra_lebaran_maks_rata": float(pra.mean(axis=1).max()),
            "kenaikan_minggu_plus4_rata": float(rata.loc[4]),
            "tahun_naik_di_minggu_min1": int((tab.loc[-1] >= q["ambang_naik"]).sum()),
        })
    rk = pd.DataFrame(ringkas)
    return {"per_kota": per_kota, "per_tahun": per_tahun, "ringkas": rk}


def figures(res: dict, cfg: dict) -> dict:
    style()
    q = cfg["analisis"]["q4_musiman"]
    pt, rk = res["per_tahun"], res["ringkas"].set_index("kualitas")
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True)
    for ax, kom in zip(axes.flat, KOMODITAS_URUT):
        tab = pt[pt.kualitas == kom].pivot(index="minggu_ke_idul_fitri", columns="tahun_idul_fitri",
                                           values="kenaikan_median_kota") * 100
        ax.fill_between(tab.index, tab.min(axis=1), tab.max(axis=1), color=TEAL, alpha=0.18, lw=0, label="rentang 3 tahun")
        ax.plot(tab.index, tab.mean(axis=1), color=TEAL, lw=2.2, label="rata-rata 3 tahun")
        ax.axhline(0, color=GRAY, lw=1)
        ax.axhline(q["ambang_naik"] * 100, color=INK2, lw=0.8, ls=":")
        ax.axvline(0, color=INK2, lw=0.8, ls="--")
        r = rk.loc[kom]
        if pd.notna(r.mulai_naik_minggu):
            ax.axvspan(r.mulai_naik_minggu, -0.5, color=ORANGE, alpha=0.12, lw=0)
            judul = (f"{LABEL_PENDEK[kom]}: naik sejak ≤ minggu {int(r.mulai_naik_minggu)}" if r.mulai_di_batas_jendela
                     else f"{LABEL_PENDEK[kom]}: naik mulai minggu {int(r.mulai_naik_minggu)}")
        else:
            judul = f"{LABEL_PENDEK[kom]}: tidak naik konsisten"
        ax.set_title(judul, fontsize=10)
        ax.set_xticks(range(-8, 5, 2))
    for ax in axes[1]:
        ax.set_xlabel("minggu ke Idulfitri (0 = minggu Lebaran)")
    for ax in axes[:, 0]:
        ax.set_ylabel("% vs harga normal")
    axes.flat[0].legend(frameon=False, fontsize=8, loc="upper left")
    naik = rk[rk.mulai_naik_minggu.notna()]
    if len(naik):
        paling = naik.sort_values(["tahun_naik_di_minggu_min1", "mulai_naik_minggu"], ascending=[False, True]).iloc[0]
        fig.suptitle(f"Harga {LABEL_PENDEK[paling.name].lower()} mulai naik {abs(int(paling.mulai_naik_minggu))} minggu "
                     f"sebelum Idulfitri; {len(naik)} dari 6 komoditas naik menjelang Lebaran di ≥ 2 dari 3 tahun",
                     x=0.01, ha="left", fontweight="bold", fontsize=12)
    else:
        fig.suptitle("Tidak ada komoditas yang naik konsisten menjelang Idulfitri", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    return {"pola": save_fig(fig, "q4_pola_idul_fitri")}


def _mulai_label(x) -> str:
    if pd.isna(x.mulai_naik_minggu):
        return "tidak konsisten"
    n = abs(int(x.mulai_naik_minggu))
    return f"≥ {n} minggu sebelum (sejak awal jendela)" if x.mulai_di_batas_jendela else f"{n} minggu sebelum"


def write_summary(res: dict, figs: dict, cfg: dict) -> None:
    q = cfg["analisis"]["q4_musiman"]
    rk = res["ringkas"]
    p = lambda v: "–" if pd.isna(v) else f"{v:+.0%}".replace(".", ",")  # noqa: E731
    tbl = "\n".join(
        f"| {LABEL_PENDEK[x.kualitas]} | {_mulai_label(x)} | {x.tahun_konsisten} | "
        f"{p(x.kenaikan_minggu_min1_rata)} ({x.kenaikan_minggu_min1_per_tahun}) | minggu {x.puncak_minggu}: {p(x.puncak_kenaikan_rata)} "
        f"({p(x.puncak_kenaikan_min_tahun)} s/d {p(x.puncak_kenaikan_maks_tahun)}) | {p(x.kenaikan_minggu_plus4_rata)} |"
        for x in rk.itertuples())
    naik = rk[rk.mulai_naik_minggu.notna()].copy()
    # Kalimat utama: komoditas yang paling KONSISTEN (naik di minggu -1 pada tahun terbanyak), lalu yang paling awal
    naik["_n"] = naik.tahun_naik_di_minggu_min1
    naik = naik.sort_values(["_n", "mulai_naik_minggu"], ascending=[False, True])
    if len(naik):
        a = naik.iloc[0]
        kal = (f"**Harga {LABEL_PENDEK[a.kualitas].lower()} mulai naik {abs(int(a.mulai_naik_minggu))} minggu sebelum Idulfitri, "
               f"jadi stok perlu diamankan sebelum itu.** Seminggu sebelum Lebaran harganya rata-rata {p(a.kenaikan_minggu_min1_rata)} "
               f"dibanding harga normal (minggu −12 s/d −9). Komoditas lain yang naik konsisten: "
               f"{', '.join(f'{LABEL_PENDEK[x.kualitas].lower()} ({_mulai_label(x)}, naik di {x.tahun_konsisten} tahun)' for x in naik.iloc[1:].itertuples()) or 'tidak ada'}.")
    else:
        kal = "**Tidak ada komoditas yang harganya naik konsisten menjelang Idulfitri pada ketiga tahun.**"
    tidak = rk[rk.mulai_naik_minggu.isna()].kualitas
    text = f"""# Q4 — Pola harga sekitar Idulfitri

Dibuat otomatis oleh `python -m src.analysis.seasonality` pada {datetime.now():%Y-%m-%d %H:%M}.
Pasar tradisional, harga mingguan, Idulfitri 2024 (10 Apr), 2025 (31 Mar), 2026 (21 Mar) menurut SKB.
Harga normal = rata-rata minggu {q['baseline_minggu'][0]} s/d {q['baseline_minggu'][1]}. "Mulai naik" = setiap minggu sejak itu sampai minggu −1
harga ≥ {q['ambang_naik']:.0%} di atas harga normal (median antar kota) pada ≥ {q['min_tahun_naik']} dari 3 tahun.

## Temuan (bahasa dashboard)
{kal}
{('Tidak naik konsisten: ' + ', '.join(LABEL_PENDEK[k].lower() for k in tidak) + '.') if len(tidak) else ''}
Pola ini masih perkiraan kasar karena baru ada 3 kali Idulfitri dalam data.

## Per komoditas
| Komoditas | Mulai naik | Tahun dengan kenaikan ≥ ambang di minggu −1 | Seminggu sebelum Lebaran (rata-rata; per tahun) | Puncak (rata-rata; rentang antar tahun) | 4 minggu setelah Lebaran |
|---|---|---|---|---|---|
{tbl}

## Batasan
- Hanya 3 kali Idulfitri. Minggu Lebaran (minggu 0) tahun 2024 & 2025 tidak punya pencatatan sama sekali.
- Idulfitri bergeser ±11 hari tiap tahun, tetapi 3 tahun belum cukup untuk memisahkan efek Lebaran dari musim panen/hujan.
- Harga normal minggu −12 s/d −9 bisa terpengaruh peristiwa lain (mis. Imlek, awal tahun).

## File
- Tabel: `reports/tables/q4_pola_idul_fitri.csv` (komoditas × tahun × minggu), `q4_ringkasan.csv`, `q4_per_kota.csv`
- Grafik: `reports/figures/{figs['pola'].name}`
"""
    (ROOT / "reports" / "q4_pola_idul_fitri.md").write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, _ = load_cfg()
    res = run(cfg)
    save_table(res["per_tahun"], "q4_pola_idul_fitri")
    save_table(res["ringkas"], "q4_ringkasan")
    save_table(res["per_kota"], "q4_per_kota")
    figs = figures(res, cfg)
    write_summary(res, figs, cfg)
    print(res["ringkas"].to_string(index=False))


if __name__ == "__main__":
    main()
