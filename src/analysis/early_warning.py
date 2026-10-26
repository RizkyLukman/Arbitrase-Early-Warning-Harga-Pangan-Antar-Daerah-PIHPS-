"""Q6 — Apakah aturan peringatan dini sederhana bisa mendeteksi lonjakan lebih awal, dan seberapa akurat (backtest)?

Definisi (pasar tradisional, harga mingguan per kota x komoditas):
    lonjakan  : minggu t di mana harga 4 minggu kemudian >= (1 + X) x harga minggu t; X = persentil 90 kenaikan 4 minggu
                per komoditas, dihitung dari DATA LATIH. Awal lonjakan (onset) = minggu pertama dari rangkaian itu.
                "Terlihat" = minggu pertama harga sudah >= (1 + X) x harga saat onset.
    peringatan (aturan brief, mudah dijelaskan):
        A. kenaikan mingguan di salah satu KOTA PENENTU ARAH (Q3) jauh di atas kebiasaan: zscore_return > 2
        B. sudah masuk masa N minggu sebelum Idulfitri (Q4), N = minggu mulai naik komoditas itu
        Aturan = A ATAU B. Komponen A & B juga dinilai terpisah.
    benar     : peringatan diikuti awal lonjakan dalam 0..4 minggu.
    pembanding: "sama seperti tahun lalu" (beri peringatan jika tahun lalu di minggu yang sama ada awal lonjakan dalam
                0..4 minggu) dan "selalu beri peringatan" (= frekuensi dasar lonjakan).
Backtest TANPA look-ahead: untuk tiap tahun uji T, X, kota penentu arah (Q3) dan N (Q4) dihitung ulang dari data < 1 Jan T.
zscore_return sendiri sudah hanya memakai 52 minggu sebelumnya (src/features.py).

Output: reports/tables/q6_*.csv, reports/figures/q6_*.png, reports/q6_peringatan_dini.md
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
from src.analysis.leadlag import market_leadership, prewhiten
from src.analysis.seasonality import event_relative, onset_week

import matplotlib.pyplot as plt  # noqa: E402


# ---------------------------------------------------------------- fungsi inti
def label_spikes(h: pd.Series, horizon: int, ambang: float) -> pd.DataFrame:
    """h: harga mingguan satu seri (index = minggu_akhir, berurutan). Menandai masa & awal lonjakan."""
    naik = h.shift(-horizon) / h - 1
    masa = (naik >= ambang).fillna(False)
    onset = masa & ~masa.shift(1, fill_value=False)
    terlihat = pd.Series(pd.NaT, index=h.index, dtype="datetime64[ns]")
    vals = h.to_numpy()
    for i in np.flatnonzero(onset.to_numpy()):
        for j in range(i + 1, min(i + horizon, len(vals) - 1) + 1):
            if not np.isnan(vals[j]) and vals[j] / vals[i] - 1 >= ambang:
                terlihat.iloc[i] = h.index[j]
                break
    return pd.DataFrame({"naik_h": naik, "masa": masa, "onset": onset, "minggu_terlihat": terlihat})


def evaluate_alerts(alert: pd.Series, onset: pd.Series, terlihat: pd.Series, window: int) -> dict:
    """alert, onset: bool per minggu (index sama, berurutan). Mengembalikan hitungan & lead time."""
    a = alert.to_numpy(bool)
    o = onset.to_numpy(bool)
    n = len(a)
    benar = sum(o[i:i + window + 1].any() for i in np.flatnonzero(a))
    terdeteksi, leads = 0, []
    for j in np.flatnonzero(o):
        cand = np.flatnonzero(a[max(0, j - window):j + 1])
        if len(cand):
            terdeteksi += 1
            first = max(0, j - window) + cand[0]
            if pd.notna(terlihat.iloc[j]):
                leads.append((terlihat.iloc[j] - alert.index[first]).days / 7)
    return {"peringatan": int(a.sum()), "peringatan_benar": int(benar), "lonjakan": int(o.sum()),
            "lonjakan_terdeteksi": int(terdeteksi), "lead_time_rata_minggu": float(np.mean(leads)) if leads else np.nan,
            "lead_times": leads, "minggu": n}


def seasonal_naive_alerts(onset: pd.Series, window: int) -> pd.Series:
    """Tebakan "sama seperti tahun lalu": peringatan di minggu i jika ada awal lonjakan di minggu i-52 .. i-52+window."""
    o = onset.to_numpy(bool)
    out = np.zeros(len(o), bool)
    for i in range(len(o)):
        lo = i - 52
        if lo + window >= 0:
            out[i] = o[max(0, lo):max(0, lo + window + 1)].any() if lo + window >= 0 else False
    return pd.Series(out, index=onset.index)


# ---------------------------------------------------------------- pelatihan per tahun uji (tanpa look-ahead)
def _train_params(t: pd.DataFrame, batas: pd.Timestamp, cfg: dict) -> dict:
    q, q3, q4 = cfg["analisis"]["q6_peringatan"], cfg["analisis"]["q3_leadlag"], cfg["analisis"]["q4_musiman"]
    latih = t[t.minggu_akhir < batas]
    par = {}
    for kom in KOMODITAS_URUT:
        d = latih[latih.kualitas == kom]
        # X: persentil kenaikan 4 minggu, hanya dari minggu yang 4 minggu ke depannya masih di dalam data latih
        naik = []
        for _, g in d.groupby("kota"):
            h = g.set_index("minggu_akhir").harga.sort_index()
            nk = h.shift(-q["horizon_minggu"]) / h - 1
            naik.append(nk.dropna())
        X = float(pd.concat(naik).quantile(q["persentil_lonjakan"]))
        # Kota penentu arah dari data latih
        R = d.pivot_table(index="minggu_akhir", columns="kota", values="log_return")
        m = market_leadership(prewhiten(R, q3["prewhitening_ar_lag"]), q3["lag_minggu"],
                              min(q3["min_minggu_bersama"], int(R.notna().sum().median() * 0.8)), q3["alpha_bh"],
                              q3["korelasi_sedang"])
        leaders = list(m[m.peran == "penentu arah"].kota)
        # Minggu mulai naik sebelum Idulfitri dari tahun Idulfitri di data latih
        e = d[d.tahun_idul_fitri.notna()].copy()
        N = None
        if len(e):
            e["minggu_ke_idul_fitri"] = e.minggu_ke_idul_fitri.astype(int)
            rows = []
            for (kota, th), g in e.groupby(["kota", "tahun_idul_fitri"]):
                rel = event_relative(g, tuple(q4["baseline_minggu"]), tuple(q4["jendela_minggu"]))
                rows += [{"tahun": int(th), "minggu": mm, "kenaikan": v} for mm, v in rel.items()]
            tab = pd.DataFrame(rows).groupby(["minggu", "tahun"]).kenaikan.median().unstack("tahun")
            N = onset_week(tab, q4["ambang_naik"], min(q4["min_tahun_naik"], tab.shape[1]))
        par[kom] = {"X": X, "leaders": leaders, "N": N, "tahun_idul_fitri_latih": int(e.tahun_idul_fitri.nunique()) if len(e) else 0}
    return par


def _signals(t: pd.DataFrame, kom: str, par: dict, q: dict) -> pd.DataFrame:
    """Sinyal per kota x minggu untuk satu komoditas: A (kota penentu arah), B (masa sebelum Idulfitri)."""
    d = t[t.kualitas == kom]
    z = d.pivot_table(index="minggu_akhir", columns="kota", values="zscore_return")
    p = par[kom]
    kal = d.drop_duplicates("minggu_akhir").set_index("minggu_akhir").minggu_ke_idul_fitri.sort_index()
    B = (kal >= p["N"]) & (kal <= -1) if p["N"] is not None else pd.Series(False, index=kal.index)
    B = B.fillna(False).astype(bool)
    out = []
    for kota in z.columns:
        lain = [L for L in p["leaders"] if L != kota and L in z.columns]
        if lain:
            zl = z[lain]
            A = (zl > q["ambang_zscore_kenaikan"]).any(axis=1)
            pemicu = zl.apply(lambda r: ", ".join(r.index[r > q["ambang_zscore_kenaikan"]]), axis=1)
        else:
            A = pd.Series(False, index=z.index)
            pemicu = pd.Series("", index=z.index)
        out.append(pd.DataFrame({"kota": kota, "minggu_akhir": z.index, "sinyal_A": A.values,
                                 "sinyal_B": B.reindex(z.index).fillna(False).values, "pemicu_A": pemicu.values}))
    return pd.concat(out, ignore_index=True)


def backtest(cfg: dict) -> dict:
    q = cfg["analisis"]["q6_peringatan"]
    w = load_weekly(cfg)
    t = w[w.jenis_pasar_id == q["jenis_pasar_id"]].copy()
    hasil, detail, params = [], [], []
    for T in q["tahun_uji"]:
        batas = pd.Timestamp(f"{T}-01-01")
        akhir_uji = min(pd.Timestamp(f"{T}-12-31"), t.minggu_akhir.max() - pd.Timedelta(weeks=q["horizon_minggu"]))
        par = _train_params(t, batas, cfg)
        for kom in KOMODITAS_URUT:
            p = par[kom]
            params.append({"tahun_uji": T, "kualitas": kom, "ambang_lonjakan": p["X"], "kota_penentu_arah": ", ".join(p["leaders"]),
                           "minggu_mulai_naik_idul_fitri": p["N"], "tahun_idul_fitri_di_latih": p["tahun_idul_fitri_latih"]})
            sig = _signals(t, kom, par, q)
            d = t[t.kualitas == kom]
            for kota, g in d.groupby("kota"):
                h = g.set_index("minggu_akhir").harga.sort_index()
                lab = label_spikes(h, q["horizon_minggu"], p["X"])
                s = sig[sig.kota == kota].set_index("minggu_akhir").reindex(lab.index)
                naive = seasonal_naive_alerts(lab.onset, q["jendela_benar_minggu"])
                uji = (lab.index >= batas) & (lab.index <= akhir_uji)
                aturan = {"A: kota penentu arah": s.sinyal_A.fillna(False).astype(bool),
                          "B: masa sebelum Idulfitri": s.sinyal_B.fillna(False).astype(bool)}
                aturan["A atau B (aturan brief)"] = aturan["A: kota penentu arah"] | aturan["B: masa sebelum Idulfitri"]
                aturan["pembanding: sama seperti tahun lalu"] = naive
                aturan["pembanding: selalu beri peringatan"] = pd.Series(True, index=lab.index)
                for nama, al in aturan.items():
                    r = evaluate_alerts(al[uji], lab.onset[uji], lab.minggu_terlihat[uji], q["jendela_benar_minggu"])
                    hasil.append({"tahun_uji": T, "kualitas": kom, "kota": kota, "aturan": nama,
                                  **{k: v for k, v in r.items() if k != "lead_times"}, "lead_times": r["lead_times"]})
                d_al = pd.DataFrame({"tahun_uji": T, "kualitas": kom, "kota": kota, "minggu_akhir": lab.index[uji],
                                     "harga": h[uji].values, "onset": lab.onset[uji].values,
                                     "sinyal_A": aturan["A: kota penentu arah"][uji].values,
                                     "sinyal_B": aturan["B: masa sebelum Idulfitri"][uji].values,
                                     "pemicu_A": s.pemicu_A[uji].fillna("").values})
                detail.append(d_al)
    return {"hasil": pd.DataFrame(hasil), "detail": pd.concat(detail, ignore_index=True), "params": pd.DataFrame(params)}


def summarize(h: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = h.groupby(keys)
    s = g.agg(peringatan=("peringatan", "sum"), peringatan_benar=("peringatan_benar", "sum"),
              lonjakan=("lonjakan", "sum"), lonjakan_terdeteksi=("lonjakan_terdeteksi", "sum"),
              minggu=("minggu", "sum")).reset_index()
    s["ketepatan"] = s.peringatan_benar / s.peringatan.replace(0, np.nan)       # precision
    s["tangkapan"] = s.lonjakan_terdeteksi / s.lonjakan.replace(0, np.nan)        # recall
    s["porsi_minggu_peringatan"] = s.peringatan / s.minggu
    leads = g.lead_times.apply(lambda x: [v for l in x for v in l])
    s["lead_time_rata_minggu"] = leads.apply(lambda l: float(np.mean(l)) if l else np.nan).values
    return s


# ---------------------------------------------------------------- peringatan terkini (untuk dashboard)
def current_alerts(cfg: dict) -> pd.DataFrame:
    """Latih dengan SEMUA data, lalu nilai minggu-minggu terakhir. Kolom alasan memakai bahasa dashboard."""
    q = cfg["analisis"]["q6_peringatan"]
    w = load_weekly(cfg)
    t = w[w.jenis_pasar_id == q["jenis_pasar_id"]].copy()
    batas = t.minggu_akhir.max() + pd.Timedelta(days=1)
    par = _train_params(t, batas, cfg)
    akhir = t.minggu_akhir.max()
    out = []
    for kom in KOMODITAS_URUT:
        s = _signals(t, kom, par, q)
        s = s[s.minggu_akhir > akhir - pd.Timedelta(weeks=8)].copy()
        s["kualitas"] = kom
        alasan = []
        for x in s.itertuples():
            a = []
            if x.sinyal_A:
                a.append(f"harga {LABEL_PENDEK[kom].lower()} di {x.pemicu_A} naik jauh di atas kebiasaan "
                         f"(kota yang harganya biasanya naik lebih dulu)")
            if x.sinyal_B:
                a.append(f"sudah masuk masa {abs(par[kom]['N'])} minggu sebelum Idulfitri, saat harga biasanya mulai naik")
            alasan.append("; ".join(a))
        s["alasan"] = alasan
        s["peringatan"] = s.sinyal_A | s.sinyal_B
        out.append(s)
    return pd.concat(out, ignore_index=True)[["minggu_akhir", "kualitas", "kota", "peringatan", "sinyal_A", "sinyal_B", "alasan"]]


# ---------------------------------------------------------------- grafik & laporan
def figures(ring: pd.DataFrame, detail: pd.DataFrame) -> dict:
    style()
    out = {}
    r = ring.set_index("aturan")
    urut = ["A atau B (aturan brief)", "A: kota penentu arah", "B: masa sebelum Idulfitri",
            "pembanding: sama seperti tahun lalu", "pembanding: selalu beri peringatan"]
    r = r.reindex(urut)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), sharey=True)
    warna = [TEAL, "#9fdcc4", "#9fdcc4", GRAY, GRAY]
    for ax, col, judul in [(axes[0], "ketepatan", "Peringatan yang terbukti benar (dari 10)"),
                           (axes[1], "tangkapan", "Lonjakan yang berhasil diperingatkan (dari 10)")]:
        ax.barh(range(len(r)), r[col] * 10, color=warna, height=0.6)
        for i, v in enumerate(r[col] * 10):
            if pd.notna(v):
                ax.text(v, i, f" {v:.1f}".replace(".", ","), va="center", fontsize=9, color=INK)
        ax.set_xlim(0, 10)
        ax.set_title(judul, fontsize=10)
    axes[0].set_yticks(range(len(r)), [x.replace("pembanding: ", "pembanding: ") for x in r.index], fontsize=9)
    axes[0].invert_yaxis()
    b = r.loc["A atau B (aturan brief)"]
    nv, al = r.loc["pembanding: sama seperti tahun lalu"], r.loc["pembanding: selalu beri peringatan"]
    lemah = (b.ketepatan <= al.ketepatan) or (b.ketepatan <= nv.ketepatan)
    lt = f"{b.lead_time_rata_minggu:.1f}".replace(".", ",")
    fig.suptitle(f"Peringatan dini menangkap {b.tangkapan * 10:.0f} dari 10 lonjakan harga, rata-rata {lt} minggu lebih awal"
                 + (";\ntetapi tebakan \"sama seperti tahun lalu\" lebih tepat (diuji pada data 2025–2026)" if lemah
                    else " (diuji pada data 2025–2026)"), x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    out["skor"] = save_fig(fig, "q6_skor_peringatan")

    # Timeline contoh: cabai rawit Jakarta Pusat
    d = detail[(detail.kualitas == "Cabai Rawit Merah") & (detail.kota == "Kota Jakarta Pusat")].sort_values("minggu_akhir")
    if len(d):
        fig, ax = plt.subplots(figsize=(11, 3.4))
        ax.plot(d.minggu_akhir, d.harga / 1000, color=TEAL, lw=2, label="harga cabai rawit, Jakarta Pusat")
        on = d[d.onset]
        for x in on.minggu_akhir:
            ax.axvspan(x, x + pd.Timedelta(weeks=4), color=ORANGE, alpha=0.15, lw=0)
        al = d[d.sinyal_A | d.sinyal_B]
        ax.scatter(al.minggu_akhir, al.harga / 1000, color=ORANGE, s=22, zorder=3, label="peringatan")
        ax.set_ylabel("Rp ribu/kg")
        ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9)
        ax.set_title("Peringatan (titik) vs masa lonjakan harga (area oranye), cabai rawit di Jakarta Pusat, 2025–2026")
        out["timeline"] = save_fig(fig, "q6_timeline_contoh")
    return out


def write_summary(ring: pd.DataFrame, per_kom: pd.DataFrame, per_tahun: pd.DataFrame, params: pd.DataFrame,
                  cur: pd.DataFrame, figs: dict, cfg: dict) -> None:
    q = cfg["analisis"]["q6_peringatan"]
    f10 = lambda v: "–" if pd.isna(v) else f"{v * 10:.1f}".replace(".", ",")  # noqa: E731
    fm = lambda v: "–" if pd.isna(v) else f"{v:.1f}".replace(".", ",")  # noqa: E731
    r = ring.set_index("aturan")
    b, nv, al = r.loc["A atau B (aturan brief)"], r.loc["pembanding: sama seperti tahun lalu"], r.loc["pembanding: selalu beri peringatan"]
    lebih_baik = (b.ketepatan > nv.ketepatan) and (b.tangkapan >= nv.tangkapan)
    vs_dasar = b.ketepatan / al.ketepatan
    rb = lambda v: f"{int(v):,}".replace(",", ".")  # noqa: E731
    tbl = "\n".join(f"| {k} | {f10(x.ketepatan)} | {f10(x.tangkapan)} | {fm(x.lead_time_rata_minggu)} | "
                    f"{x.porsi_minggu_peringatan:.0%} | {rb(x.peringatan)} | {rb(x.lonjakan)} |"
                    for k, x in r.iterrows())
    kom = per_kom[per_kom.aturan.isin(["A atau B (aturan brief)", "pembanding: sama seperti tahun lalu",
                                       "pembanding: selalu beri peringatan"])]
    kp = kom.pivot_table(index="kualitas", columns="aturan", values=["ketepatan", "tangkapan"]).reindex(KOMODITAS_URUT)
    ktbl = "\n".join(
        f"| {LABEL_PENDEK[k]} | {f10(kp.loc[k, ('ketepatan', 'A atau B (aturan brief)')])} | "
        f"{f10(kp.loc[k, ('tangkapan', 'A atau B (aturan brief)')])} | "
        f"{f10(kp.loc[k, ('ketepatan', 'pembanding: sama seperti tahun lalu')])} | "
        f"{f10(kp.loc[k, ('ketepatan', 'pembanding: selalu beri peringatan')])} |" for k in kp.index)
    pt = per_tahun[per_tahun.aturan == "A atau B (aturan brief)"]
    ttbl = "\n".join(f"| {int(x.tahun_uji)} | {f10(x.ketepatan)} | {f10(x.tangkapan)} | {fm(x.lead_time_rata_minggu)} |"
                     for x in pt.itertuples())
    ptbl = "\n".join(f"| {int(x.tahun_uji)} | {LABEL_PENDEK[x.kualitas]} | {x.ambang_lonjakan:.0%} | {x.kota_penentu_arah or '–'} | "
                     f"{'minggu ' + str(int(x.minggu_mulai_naik_idul_fitri)) if pd.notna(x.minggu_mulai_naik_idul_fitri) else '–'} |"
                     for x in params.itertuples())
    c = cur[cur.minggu_akhir == cur.minggu_akhir.max()]
    aktif = c[c.peringatan]
    akt = (aktif.groupby("kualitas").kota.apply(lambda s: f"{len(s)} kota").to_dict())
    kalimat_terkini = ("; ".join(f"{LABEL_PENDEK[k].lower()}: {v}" for k, v in akt.items()) if akt
                       else "tidak ada peringatan aktif")
    lebih_tepat_dari_dasar = b.ketepatan > al.ketepatan
    layak = lebih_baik and lebih_tepat_dari_dasar
    status_kalimat = "cukup layak dicoba" if layak else "tetapi belum layak dipakai sebagai pemicu pembelian"
    banding_dasar = (f"Ini lebih tepat daripada memberi peringatan setiap minggu ({f10(al.ketepatan)} dari 10)."
                     if lebih_tepat_dari_dasar else
                     f"Ini bahkan lebih rendah daripada memberi peringatan setiap minggu ({f10(al.ketepatan)} dari 10), "
                     f"artinya aturan ini belum lebih baik daripada tebakan acak.")
    banding_naive = ("kalah dari aturan ini" if lebih_baik else "justru lebih baik")
    tindakan = ("pakai peringatan sebagai pemicu untuk mengecek harga & stok; tetap tidak otomatis membeli." if layak else
                "jangan pakai aturan ini sebagai pemicu pembelian. Untuk sementara, pakai kalender pola tahun lalu dan pola "
                "Idulfitri (mis. bawang merah naik 4 minggu sebelum Lebaran) sebagai pengingat, dan harga di kota penentu "
                "arah hanya sebagai informasi tambahan.")
    text = f"""# Q6 — Peringatan dini & uji pada data lama

Dibuat otomatis oleh `python -m src.analysis.early_warning` pada {datetime.now():%Y-%m-%d %H:%M}.
Pasar tradisional, mingguan. Lonjakan = harga naik ≥ X% dalam {q['horizon_minggu']} minggu (X = persentil {q['persentil_lonjakan']:.0%}
dari data latih per komoditas). Peringatan benar = lonjakan dimulai 0–{q['jendela_benar_minggu']} minggu setelah peringatan.
Diuji pada data tahun {', '.join(map(str, q['tahun_uji']))}; setiap tahun uji hanya memakai pengetahuan dari data sebelumnya.

## Temuan (bahasa dashboard)
**Peringatan dini menangkap {b.tangkapan * 10:.0f} dari 10 lonjakan harga, rata-rata {fm(b.lead_time_rata_minggu)} minggu lebih awal — {status_kalimat}.**
Peringatan yang terbukti benar: {f10(b.ketepatan)} dari 10. {banding_dasar} Tebakan "sama seperti tahun lalu" {banding_naive}
({f10(nv.ketepatan)} dari 10 benar, menangkap {f10(nv.tangkapan)} dari 10).
Tindakan: {tindakan}

Peringatan minggu terakhir ({c.minggu_akhir.max():%d %b %Y}): {kalimat_terkini}.

## Hasil uji (2025–2026 digabung)
| Aturan | Benar (dari 10 peringatan) | Lonjakan tertangkap (dari 10) | Datang lebih awal (minggu) | Minggu dengan peringatan | Peringatan | Lonjakan |
|---|---|---|---|---|---|---|
{tbl}

"Selalu beri peringatan" = frekuensi dasar: berapa persen minggu memang diikuti lonjakan dalam {q['jendela_benar_minggu']} minggu.

## Per tahun uji (aturan brief)
| Tahun uji | Benar (dari 10) | Tertangkap (dari 10) | Lebih awal (minggu) |
|---|---|---|---|
{ttbl}

## Per komoditas (2025–2026)
| Komoditas | Aturan brief: benar | Aturan brief: tertangkap | Tahun lalu: benar | Selalu: benar |
|---|---|---|---|---|
{ktbl}

## Parameter yang dipelajari dari data latih (tanpa melihat tahun uji)
| Tahun uji | Komoditas | Ambang lonjakan (4 minggu) | Kota penentu arah | Mulai naik sebelum Idulfitri |
|---|---|---|---|---|
{ptbl}

## Batasan
- Hanya 2 tahun uji; tahun uji 2025 dilatih dengan 1 kali Idulfitri saja (2024).
- Lonjakan didefinisikan secara statistik (persentil 90), bukan dari pengalaman pengadaan nyata.
- Kota penentu arah hanya memberi ±1 minggu waktu tambahan; peringatan tidak memprediksi besarnya kenaikan.
- "Lebih awal" dihitung dari peringatan pertama (0–{q['jendela_benar_minggu']} minggu sebelum lonjakan dimulai) sampai harga
  sudah naik X%; nilainya maksimal sekitar {2 * q['jendela_benar_minggu']} minggu. Tebakan "selalu beri peringatan" pun mendapat
  {fm(al.lead_time_rata_minggu)} minggu, jadi angka ini hanya bermakna jika dibaca bersama "peringatan yang terbukti benar".

## File
- Tabel: `reports/tables/q6_skor_ringkas.csv`, `q6_skor_per_komoditas.csv`, `q6_skor_per_tahun.csv`, `q6_parameter_latih.csv`,
  `q6_peringatan_terkini.csv` (8 minggu terakhir, kolom alasan berbahasa dashboard)
- Grafik: {', '.join(f'`reports/figures/{p.name}`' for p in figs.values())}
"""
    (ROOT / "reports" / "q6_peringatan_dini.md").write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, _ = load_cfg()
    bt = backtest(cfg)
    h = bt["hasil"]
    ring = summarize(h, ["aturan"])
    per_kom = summarize(h, ["aturan", "kualitas"])
    per_tahun = summarize(h, ["aturan", "tahun_uji"])
    cur = current_alerts(cfg)
    save_table(ring.drop(columns=[], errors="ignore"), "q6_skor_ringkas")
    save_table(per_kom, "q6_skor_per_komoditas")
    save_table(per_tahun, "q6_skor_per_tahun")
    save_table(bt["params"], "q6_parameter_latih")
    save_table(cur, "q6_peringatan_terkini")
    figs = figures(ring, bt["detail"])
    write_summary(ring, per_kom, per_tahun, bt["params"], cur, figs, cfg)
    print(ring.round(3).to_string(index=False))
    print(bt["params"].to_string(index=False))


if __name__ == "__main__":
    main()
