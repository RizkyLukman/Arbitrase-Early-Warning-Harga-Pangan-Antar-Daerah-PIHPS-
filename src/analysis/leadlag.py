"""Q3 — Apakah ada kota "penentu arah" yang kenaikan harganya mendahului kota lain? Berapa jedanya?

Metode (pasar tradisional, log-return mingguan per kota x komoditas):
1. Uji stasioneritas ADF per seri log-return (syarat Granger).
2. Prewhitening: buang momentum tiap kota (regresi pada lag-nya sendiri 1..p). Tanpa ini, momentum + pergerakan
   bersamaan membuat sebagian besar pasangan kota tampak "saling mendahului" (semu) — dilaporkan sebagai pembanding.
3. Kota vs pasar: corr(kejutan_kota[t-k], rata-rata kejutan semua kota lain[t]) untuk k = 1..4, dan arah sebaliknya.
   Koreksi Benjamini-Hochberg per komoditas. Kota "penentu arah" = lolos BH, korelasi >= ambang "sedang", lebih kuat
   daripada arah sebaliknya. Kota "pengikut" = kebalikannya.
4. Per pasangan kota (untuk kota tujuan distributor): kota mana yang kejutannya mendahului kota tujuan (BH + asimetri).
5. Ringkasan per provinsi: rata-rata (mendahului - mengikuti) pasar pada jeda 1 minggu -> arah penyebaran harga.
6. Granger causality (pendukung saja) untuk kota penentu arah -> pasar.
PENTING: ini asosiasi statistik. Korelasi berjeda dan Granger BUKAN bukti sebab-akibat.

Output: reports/tables/q3_*.csv, reports/figures/q3_*.png, reports/q3_kota_penentu_arah.md
"""
from __future__ import annotations

import argparse
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

from src.analysis.common import (
    BLUE, GRAY, INK, INK2, KOMODITAS_URUT, LABEL_PENDEK, ORANGE, ROOT, TEAL, load_cfg, load_weekly, save_fig, save_table,
    style,
)

import matplotlib.pyplot as plt  # noqa: E402


# ---------------------------------------------------------------- fungsi inti
def lagged_corr(x: pd.Series, y: pd.Series, k: int) -> tuple[float, int, float]:
    """Korelasi Pearson antara x digeser k minggu (x[t-k]) dan y[t]. Mengembalikan (r, n, p-value)."""
    d = pd.concat([x.shift(k), y], axis=1).dropna()
    n = len(d)
    if n < 3 or d.iloc[:, 0].std() == 0 or d.iloc[:, 1].std() == 0:
        return np.nan, n, np.nan
    r, p = stats.pearsonr(d.iloc[:, 0], d.iloc[:, 1])
    return float(r), n, float(p)


def prewhiten(R: pd.DataFrame, p: int) -> pd.DataFrame:
    """Residual regresi tiap kolom pada lag-nya sendiri 1..p (OLS + konstanta). Menghapus momentum/autokorelasi
    sehingga korelasi silang berjeda mengukur apakah KEJUTAN di kota A mendahului kejutan di kota B."""
    out = {}
    for c in R.columns:
        x = R[c]
        X = pd.concat({f"l{k}": x.shift(k) for k in range(1, p + 1)}, axis=1)
        d = pd.concat([x.rename("y"), X], axis=1).dropna()
        if len(d) <= p + 5:
            out[c] = pd.Series(np.nan, index=R.index)
            continue
        A = np.column_stack([np.ones(len(d)), d.drop(columns="y").to_numpy()])
        beta, *_ = np.linalg.lstsq(A, d.y.to_numpy(), rcond=None)
        out[c] = pd.Series(d.y.to_numpy() - A @ beta, index=d.index).reindex(R.index)
    return pd.DataFrame(out)


def pairwise_leadlag(R: pd.DataFrame, lags: list[int], min_n: int) -> pd.DataFrame:
    """Semua pasangan kota berurutan x jeda. R: baris = minggu, kolom = kota."""
    rows = []
    cols = list(R.columns)
    for a in cols:
        for b in cols:
            if a == b:
                continue
            r0, _, _ = lagged_corr(R[a], R[b], 0)
            for k in lags:
                r, n, p = lagged_corr(R[a], R[b], k)
                if n < min_n or np.isnan(p):
                    continue
                r_rev, _, _ = lagged_corr(R[b], R[a], k)
                rows.append({"leader": a, "follower": b, "lag": k, "r": r, "n": n, "p": p, "r_arah_sebaliknya": r_rev,
                             "r_lag0": r0})
    return pd.DataFrame(rows)


def significant_leads(pw: pd.DataFrame, alpha: float, min_r: float) -> pd.DataFrame:
    """Koreksi BH atas semua uji, lalu pilih pasangan yang bermakna & asimetris; satu jeda terbaik per pasangan."""
    if pw.empty:
        return pw.assign(q=[])
    pw = pw.copy()
    pw["q"] = multipletests(pw.p, alpha=alpha, method="fdr_bh")[1]
    s = pw[(pw.q <= alpha) & (pw.r >= min_r) & (pw.r > pw.r_arah_sebaliknya)]
    s = s.sort_values("r", ascending=False).drop_duplicates(["leader", "follower"])
    return s.sort_values(["leader", "follower"]).reset_index(drop=True)


def market_leadership(P: pd.DataFrame, lags: list[int], min_n: int, alpha: float, min_r: float) -> pd.DataFrame:
    """Setiap kota vs rata-rata semua kota lain ("pasar"). Peran: penentu arah / pengikut / netral."""
    rows = []
    for c in P.columns:
        pasar = P.drop(columns=c).mean(axis=1)
        for k in lags:
            r_l, n, p_l = lagged_corr(P[c], pasar, k)   # kota mendahului pasar
            r_f, _, p_f = lagged_corr(pasar, P[c], k)   # pasar mendahului kota
            if n >= min_n:
                rows.append({"kota": c, "lag": k, "n": n, "r_mendahului": r_l, "p_mendahului": p_l,
                             "r_mengikuti": r_f, "p_mengikuti": p_f})
    d = pd.DataFrame(rows)
    d["q_mendahului"] = multipletests(d.p_mendahului, method="fdr_bh")[1]
    d["q_mengikuti"] = multipletests(d.p_mengikuti, method="fdr_bh")[1]
    lead = d[(d.q_mendahului <= alpha) & (d.r_mendahului >= min_r) & (d.r_mendahului > d.r_mengikuti)]
    follow = d[(d.q_mengikuti <= alpha) & (d.r_mengikuti >= min_r) & (d.r_mengikuti > d.r_mendahului)]
    lead = lead.sort_values("r_mendahului", ascending=False).drop_duplicates("kota").set_index("kota")
    follow = follow.sort_values("r_mengikuti", ascending=False).drop_duplicates("kota").set_index("kota")
    lag1 = d[d.lag == 1].set_index("kota")
    out = []
    for c in P.columns:
        if c in lead.index:
            out.append({"kota": c, "peran": "penentu arah", "jeda": int(lead.loc[c, "lag"]),
                        "korelasi": float(lead.loc[c, "r_mendahului"]), "q": float(lead.loc[c, "q_mendahului"])})
        elif c in follow.index:
            out.append({"kota": c, "peran": "pengikut", "jeda": int(follow.loc[c, "lag"]),
                        "korelasi": float(follow.loc[c, "r_mengikuti"]), "q": float(follow.loc[c, "q_mengikuti"])})
        else:
            out.append({"kota": c, "peran": "netral", "jeda": None, "korelasi": np.nan, "q": np.nan})
        out[-1]["selisih_lag1"] = float(lag1.loc[c, "r_mendahului"] - lag1.loc[c, "r_mengikuti"]) if c in lag1.index else np.nan
    return pd.DataFrame(out)


def _adf_share(R: pd.DataFrame, alpha: float) -> float:
    ok = []
    for c in R.columns:
        x = R[c].dropna()
        if len(x) >= 30:
            with warnings.catch_warnings():  # statsmodels >= 0.15: peringatan perubahan format hasil adfuller
                warnings.simplefilter("ignore", FutureWarning)
                ok.append(adfuller(x, autolag="AIC")[1] < alpha)
    return float(np.mean(ok)) if ok else np.nan


def _granger_p(df: pd.DataFrame, cause: str, effect: str, maxlag: int) -> float:
    d = df[[effect, cause]].dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = grangercausalitytests(d, maxlag=maxlag)  # statsmodels >= 0.15 tidak lagi menerima argumen verbose
    return float(min(res[k][0]["ssr_ftest"][1] for k in res))


# ---------------------------------------------------------------- alur utama
def run(cfg: dict) -> dict:
    q = cfg["analisis"]["q3_leadlag"]
    tujuan = list(cfg["wilayah"]["kota_tujuan"].values())
    w = load_weekly(cfg)
    t = w[w.jenis_pasar_id == q["jenis_pasar_id"]]
    prov = t.drop_duplicates("kota").set_index("kota").provinsi
    kom_rows, peran_all, pasangan_all, target_rows = [], [], [], []
    for kom in KOMODITAS_URUT:
        R = t[t.kualitas == kom].pivot_table(index="minggu_akhir", columns="kota", values="log_return")
        P = prewhiten(R, q["prewhitening_ar_lag"])
        n_kota = R.shape[1]
        sig_semu = significant_leads(pairwise_leadlag(R, q["lag_minggu"], q["min_minggu_bersama"]),
                                     q["alpha_bh"], q["korelasi_sedang"])
        sig = significant_leads(pairwise_leadlag(P, q["lag_minggu"], q["min_minggu_bersama"]),
                                q["alpha_bh"], q["korelasi_sedang"]).assign(kualitas=kom)
        m = market_leadership(P, q["lag_minggu"], q["min_minggu_bersama"], q["alpha_bh"], q["korelasi_sedang"])
        m = m.assign(kualitas=kom, provinsi=m.kota.map(prov))
        m["kekuatan"] = np.where(m.korelasi >= q["korelasi_kuat"], "kuat",
                                 np.where(m.korelasi >= q["korelasi_sedang"], "sedang", ""))
        # Granger (pendukung): kota penentu arah -> rata-rata kota lain (log-return mentah)
        g = []
        for c in m.kota:
            if (m.set_index("kota").loc[c, "peran"] == "penentu arah"):
                df = pd.DataFrame({"kota": R[c], "pasar": R.drop(columns=c).mean(axis=1)})
                g.append(_granger_p(df, "kota", "pasar", q["granger_maxlag"]) < q["alpha_bh"])
            else:
                g.append(None)
        m["granger_mendukung"] = g
        peran_all.append(m)
        pasangan_all.append(sig)
        for kt in tujuan:
            if kt not in R.columns:
                continue
            s = sig[sig.follower == kt].sort_values("r", ascending=False).head(q["top_n_per_kota_tujuan"])
            for x in s.itertuples():
                target_rows.append({"kualitas": kom, "kota_tujuan": kt, "pantau_kota": x.leader, "provinsi": prov[x.leader],
                                    "jeda": int(x.lag), "korelasi": float(x.r),
                                    "kekuatan": "kuat" if x.r >= q["korelasi_kuat"] else "sedang"})
        kom_rows.append({
            "kualitas": kom, "kota": n_kota, "pasangan_diuji": n_kota * (n_kota - 1),
            "porsi_seri_stasioner_adf": _adf_share(R, q["adf_alpha"]),
            "autokorelasi_lag1_median": float(R.apply(lambda x: x.autocorr(1)).median()),
            "korelasi_lag0_median": float(R.corr(min_periods=q["min_minggu_bersama"])
                                          .where(~np.eye(n_kota, dtype=bool)).stack().median()),
            "pasangan_mendahului_semu": len(sig_semu),
            "pasangan_mendahului_setelah_prewhitening": len(sig),
            "kota_penentu_arah": int((m.peran == "penentu arah").sum()),
            "kota_pengikut": int((m.peran == "pengikut").sum()),
            "jeda_dominan_minggu": int(m[m.peran == "penentu arah"].jeda.mode().iloc[0]) if (m.peran == "penentu arah").any() else None,
        })
    peran = pd.concat(peran_all, ignore_index=True)
    provinsi = (peran.groupby(["kualitas", "provinsi"]).selisih_lag1.mean().unstack("kualitas")
                .reindex(columns=KOMODITAS_URUT))
    return {"kom": pd.DataFrame(kom_rows), "peran": peran, "pasangan": pd.concat(pasangan_all, ignore_index=True),
            "tujuan": pd.DataFrame(target_rows), "provinsi": provinsi}


# ---------------------------------------------------------------- grafik & laporan
def figures(res: dict, cfg: dict) -> dict:
    style()
    out = {}
    pr = res["peran"]
    # 1) Kota penentu arah per komoditas
    pa = pr[pr.peran == "penentu arah"].sort_values("korelasi", ascending=False).groupby("kualitas").head(3)
    if len(pa):
        pa = pa.assign(_o=pa.kualitas.map({k: i for i, k in enumerate(KOMODITAS_URUT)})).sort_values(["_o", "korelasi"],
                                                                                                      ascending=[False, True])
        fig, ax = plt.subplots(figsize=(9, max(3, 0.3 * len(pa) + 1.2)))
        warna = [TEAL if x == "kuat" else "#9fdcc4" for x in pa.kekuatan]
        ax.barh(range(len(pa)), pa.korelasi, color=warna, height=0.7)
        ax.set_yticks(range(len(pa)), [f"{LABEL_PENDEK[x.kualitas]}: {x.kota}" for x in pa.itertuples()], fontsize=8)
        for i, x in enumerate(pa.itertuples()):
            ax.text(x.korelasi, i, f"  {int(x.jeda)} minggu lebih dulu, hubungan {x.kekuatan}", va="center", fontsize=7, color=INK2)
        ax.set_xlim(0, pa.korelasi.max() * 1.6)
        ax.set_xlabel("kekuatan hubungan dengan pergerakan rata-rata kota lain (korelasi); 3 kota teratas per komoditas")
        top = pr[pr.peran == "penentu arah"].sort_values("korelasi").iloc[-1]
        ax.set_title(f"Kenaikan harga {LABEL_PENDEK[top.kualitas].lower()} di {top.kota} biasanya disusul kota lain\n"
                     f"sekitar {int(top.jeda)} minggu kemudian")
        ax.grid(axis="y", visible=False)
        out["penentu"] = save_fig(fig, "q3_kota_penentu_arah")
    # 2) Arah penyebaran per provinsi
    p = res["provinsi"]
    urut = p.mean(axis=1).sort_values(ascending=False).index
    p = p.loc[urut]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("menyusul_dulu", [BLUE, "#f7f7f5", ORANGE])  # brief: biru vs oranye
    fig, ax = plt.subplots(figsize=(9, 3.8))
    lim = np.nanmax(np.abs(p.values))
    im = ax.imshow(p.values, cmap=cmap, vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(p.shape[1]), [LABEL_PENDEK[c] for c in p.columns], rotation=25, ha="right")
    ax.set_yticks(range(p.shape[0]), p.index)
    ax.grid(False)
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:+.2f}".replace(".", ","), ha="center", va="center", fontsize=8,
                        color="white" if abs(v) > lim * 0.6 else INK)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cb.set_ticks([-lim * 0.8, 0, lim * 0.8], labels=["menyusul", "netral", "naik\nlebih dulu"])
    cab = res["provinsi"]["Cabai Rawit Merah"].dropna().sort_values()
    ax.set_title(f"Harga cabai rawit biasanya naik dulu di {cab.index[-1]}, lalu menyusul di {cab.index[0]}")
    out["provinsi"] = save_fig(fig, "q3_arah_per_provinsi")
    return out


def write_summary(res: dict, figs: dict, cfg: dict) -> None:
    q = cfg["analisis"]["q3_leadlag"]
    kom, pr, tj, pv = res["kom"], res["peran"], res["tujuan"], res["provinsi"]
    f2 = lambda v: "–" if pd.isna(v) else f"{v:.2f}".replace(".", ",")  # noqa: E731
    tk = "\n".join(
        f"| {LABEL_PENDEK[x.kualitas]} | {x.kota} | {x.porsi_seri_stasioner_adf:.0%} | {f2(x.autokorelasi_lag1_median)} | "
        f"{f2(x.korelasi_lag0_median)} | "
        f"{x.pasangan_mendahului_semu} → {x.pasangan_mendahului_setelah_prewhitening} | {x.kota_penentu_arah} | {x.kota_pengikut} | "
        f"{'–' if x.jeda_dominan_minggu is None or pd.isna(x.jeda_dominan_minggu) else int(x.jeda_dominan_minggu)} |"
        for x in kom.itertuples())
    pa = pr[pr.peran == "penentu arah"].copy()
    pa["_o"] = pa.kualitas.map({k: i for i, k in enumerate(KOMODITAS_URUT)})
    tl = "\n".join(f"| {LABEL_PENDEK[x.kualitas]} | {x.kota} | {x.provinsi} | {int(x.jeda)} | {f2(x.korelasi)} ({x.kekuatan}) | "
                   f"{'ya' if x.granger_mendukung else 'tidak'} |" for x in pa.sort_values(["_o", "korelasi"],
                                                                                          ascending=[True, False]).itertuples())
    pg = pr[pr.peran == "pengikut"].copy()
    pg["_o"] = pg.kualitas.map({k: i for i, k in enumerate(KOMODITAS_URUT)})
    pengikut = "\n".join(f"- {LABEL_PENDEK[k]}: " + ", ".join(g.sort_values("korelasi", ascending=False).kota.head(6))
                         for k, g in pg.sort_values("_o").groupby("kualitas", sort=False))
    tt = "\n".join(f"| {x.kota_tujuan} | {LABEL_PENDEK[x.kualitas]} | {x.pantau_kota} ({x.provinsi}) | {x.jeda} | {x.kekuatan} |"
                   for x in tj.sort_values(["kota_tujuan", "kualitas", "korelasi"], ascending=[True, True, False]).itertuples()) \
        if len(tj) else "| – | – | – | – | – |"
    pvt = "\n".join(f"| {prov} | " + " | ".join(f2(v) for v in row) + " |" for prov, row in
                    pv.loc[pv.mean(axis=1).sort_values(ascending=False).index].iterrows())
    lead_med = pa.groupby("kualitas").korelasi.median()
    bs = kom.set_index("kualitas").korelasi_lag0_median
    bersama = [k for k in bs.index if k in lead_med.index and bs[k] > lead_med[k]]
    tidak = [k for k in bs.index if k not in bersama]
    bersamaan_txt = (f"Untuk {len(bersama)} dari {len(bs)} komoditas, harga antar kota terutama **bergerak bersamaan di minggu yang "
                     f"sama** (korelasi minggu yang sama lebih tinggi daripada korelasi 'mendahului')"
                     + (f"; pengecualian: {', '.join(LABEL_PENDEK[k].lower() for k in tidak)}" if tidak else "")
                     + ". Pola \"mendahului\" hanya menambah sekitar 1 minggu waktu antisipasi, dengan hubungan lemah–sedang.")
    if len(pa):
        top = pa.sort_values("korelasi").iloc[-1]
        cab = pa[pa.kualitas == "Cabai Rawit Merah"].sort_values("korelasi", ascending=False)
        kal = (f"**Kenaikan harga {LABEL_PENDEK[top.kualitas].lower()} di {top.kota} biasanya disusul kota lain sekitar "
               f"{int(top.jeda)} minggu kemudian** (hubungan {top.kekuatan}).")
        if len(cab):
            ps = pv["Cabai Rawit Merah"].dropna().sort_values()
            menyusul = [p for p in ps.index[:2] if ps[p] < 0]
            kal += f" Untuk cabai rawit, kota yang harganya biasanya naik lebih dulu: {', '.join(cab.kota)}"
            kal += (f"; kota di {' dan '.join(menyusul)} cenderung menyusul." if menyusul else ".")
        kal += (" Tindakan: pantau harga di kota penentu arah setiap minggu; kenaikan di sana adalah sinyal untuk mengamankan "
                "stok di kota tujuan sekitar 1 minggu sebelum harga di sana ikut naik.")
    else:
        kal = "**Tidak ada kota yang secara konsisten mendahului pasar.**"
    text = f"""# Q3 — Kota penentu arah

Dibuat otomatis oleh `python -m src.analysis.leadlag` pada {datetime.now():%Y-%m-%d %H:%M}.
Data: pasar tradisional, perubahan harga mingguan (log-return), Juli 2023 – Oktober 2026.
Metode: momentum tiap kota dibuang (prewhitening AR({q['prewhitening_ar_lag']})), lalu kejutan harga tiap kota dibandingkan
dengan rata-rata semua kota lain pada jeda {q['lag_minggu']} minggu; koreksi Benjamini–Hochberg (α = {q['alpha_bh']}), korelasi
≥ {q['korelasi_sedang']} dan lebih kuat daripada arah sebaliknya. Granger hanya pendukung.
**Ini asosiasi statistik, bukan bukti sebab-akibat.**

## Temuan (bahasa dashboard)
{kal}

## Ringkasan per komoditas
| Komoditas | Kota | Seri stasioner (uji ADF) | Momentum mingguan (autokorelasi) | Bergerak di minggu yang sama (korelasi median) | Pasangan "mendahului": semu → setelah momentum dibuang | Kota penentu arah | Kota pengikut | Jeda (minggu) |
|---|---|---|---|---|---|---|---|---|
{tk}

## Kota penentu arah (mendahului rata-rata kota lain)
| Komoditas | Kota | Provinsi | Jeda (minggu) | Korelasi | Didukung Granger |
|---|---|---|---|---|---|
{tl}

## Kota pengikut (harganya biasanya menyusul kota lain)
{pengikut}

## Arah penyebaran per provinsi
Rata-rata (mendahului − mengikuti) pada jeda 1 minggu. Positif = provinsi yang harganya biasanya naik lebih dulu.

| Provinsi | {' | '.join(LABEL_PENDEK[c] for c in pv.columns)} |
|---|{'---|' * pv.shape[1]}
{pvt}

## Untuk kota tujuan: kota yang perlu dipantau
Dari uji per pasangan kota (setelah momentum dibuang), maksimal {q['top_n_per_kota_tujuan']} kota per kota tujuan × komoditas.

| Kota tujuan | Komoditas | Pantau harga di | Jeda (minggu) | Hubungan |
|---|---|---|---|---|
{tt}

## Cara membaca & batasan
- {bersamaan_txt}
- Tanpa membuang momentum, ratusan pasangan kota tampak saling mendahului (kolom "semu"); angka itu tidak dipakai.
- Granger causality hanya pendukung dan **bukan** bukti bahwa harga di satu kota menyebabkan kenaikan di kota lain.
- Sampel PIHPS kecil (2 pasar per kota), harga berisik; kota "pengikut" bisa juga berarti pencatatannya terlambat.

## File
- Tabel: `reports/tables/q3_ringkasan_per_komoditas.csv`, `q3_peran_kota.csv`, `q3_arah_per_provinsi.csv`,
  `q3_pantau_untuk_kota_tujuan.csv`, `q3_pasangan_bermakna.csv`
- Grafik: {', '.join(f'`reports/figures/{p.name}`' for p in figs.values())}
"""
    (ROOT / "reports" / "q3_kota_penentu_arah.md").write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, _ = load_cfg()
    res = run(cfg)
    save_table(res["kom"], "q3_ringkasan_per_komoditas")
    save_table(res["peran"], "q3_peran_kota")
    save_table(res["provinsi"].reset_index(), "q3_arah_per_provinsi")
    save_table(res["tujuan"], "q3_pantau_untuk_kota_tujuan")
    save_table(res["pasangan"], "q3_pasangan_bermakna")
    figs = figures(res, cfg)
    write_summary(res, figs, cfg)
    print(res["kom"].to_string(index=False))
    print(res["peran"][res["peran"].peran == "penentu arah"][["kualitas", "kota", "jeda", "korelasi", "kekuatan",
                                                               "granger_mendukung"]].to_string(index=False))


if __name__ == "__main__":
    main()
