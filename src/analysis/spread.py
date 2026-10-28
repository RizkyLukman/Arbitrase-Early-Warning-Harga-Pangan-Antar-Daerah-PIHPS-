"""Q2 — Rute mana yang selisih harganya tetap untung setelah ongkos angkut, seberapa sering, dan berapa lama bertahan?

Per rute (kota sumber -> kota tujuan) x komoditas x minggu:
    harga_sumber   = harga PEDAGANG BESAR di kota sumber (nilai nyata terakhir minggu itu) — harga beli distributor
    harga_tujuan   = harga PASAR TRADISIONAL di kota tujuan (median hari nyata)
    spread_kotor   = harga_tujuan - harga_sumber                                      -> dashboard: "Selisih harga"
    biaya_logistik = (ongkos_angkut + susut_pct x harga_sumber) x pengali   (ASUMSI)  -> "Ongkos angkut (perkiraan)"
    spread_bersih  = spread_kotor - biaya_logistik                                    -> "Untung per kg"
Pengali 0,5 / 1 / 1,5 / 2 = uji sensitivitas. Rute LAYAK hanya jika tetap untung pada skenario konservatif (x1,5).

Input : data/interim/harga_mingguan.parquet, data/reference/biaya_rute.csv (src/logistics.py)
Output: data/interim/spread_mingguan.parquet, reports/tables/q2_*.csv, reports/figures/q2_*.png, reports/q2_rute.md
"""
from __future__ import annotations

import argparse
from datetime import datetime

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from src.analysis.common import (
    BLUE, GRAY, INK, INK2, LABEL_PENDEK, ORANGE, ROOT, TEAL, load_cfg, load_weekly, pct, rp, save_fig, save_table, style,
)

import matplotlib.pyplot as plt  # noqa: E402


def _col(prefix: str, p: float) -> str:
    return f"{prefix}_x{p:g}"


def weekly_spread(src: pd.DataFrame, dst: pd.DataFrame, biaya: dict, pengali: list[float],
                  kecualikan_usang: bool) -> pd.DataFrame:
    s = src[["minggu_akhir", "harga", "is_usang"]].rename(columns={"harga": "harga_sumber", "is_usang": "sumber_usang"})
    d = dst[["minggu_akhir", "harga"]].rename(columns={"harga": "harga_tujuan"})
    m = d.merge(s, on="minggu_akhir", how="outer").sort_values("minggu_akhir").reset_index(drop=True)
    m["sumber_usang"] = m.sumber_usang.astype("boolean").fillna(False).astype(bool)
    if kecualikan_usang:
        m.loc[m.sumber_usang, "harga_sumber"] = np.nan
    m["spread_kotor"] = m.harga_tujuan - m.harga_sumber
    m["ongkos_angkut"] = biaya["ongkos_angkut_rp_per_kg"]
    m["susut_rp"] = biaya["susut_pct"] * m.harga_sumber
    for p in pengali:
        m[_col("biaya_logistik", p)] = (m.ongkos_angkut + m.susut_rp) * p
        m[_col("spread_bersih", p)] = m.spread_kotor - m[_col("biaya_logistik", p)]
    return m


def run_lengths(flags: pd.Series) -> list[int]:
    """Panjang setiap rangkaian minggu untung (True) berturut-turut.

    False memutus rangkaian. Minggu tanpa data (None/NaN, mis. minggu Lebaran tanpa pencatatan) DILEWATI, tidak memutus:
    tidak ada bukti bahwa peluang hilang di minggu itu.
    """
    runs, c = [], 0
    for v in flags:
        if v is None or pd.isna(v):
            continue
        if bool(v):
            c += 1
        else:
            if c:
                runs.append(c)
            c = 0
    if c:
        runs.append(c)
    return runs


def route_metrics(s: pd.DataFrame, pengali: float, jendela: int) -> dict:
    s = s.sort_values("minggu_akhir")
    v = s[_col("spread_bersih", pengali)]
    ada = v.notna()
    untung = (v > 0).where(ada)
    runs = run_lengths([bool(x) if pd.notna(x) else None for x in untung])
    akhir = v.iloc[-jendela:]
    berturut = 0
    for x in v.iloc[::-1]:
        if pd.notna(x) and x > 0:
            berturut += 1
        else:
            break
    return {
        "n_minggu": int(ada.sum()),
        "porsi_minggu_untung": float((v[ada] > 0).mean()) if ada.any() else np.nan,
        "median_untung_rp_per_kg": float(v.median()) if ada.any() else np.nan,
        "rata_untung_rp_per_kg": float(v.mean()) if ada.any() else np.nan,
        "persistensi_rata_minggu": float(np.mean(runs)) if runs else 0.0,
        "persistensi_maks_minggu": int(max(runs)) if runs else 0,
        "untung_dari_jendela": int((akhir > 0).sum()),
        "jendela_berdata": int(akhir.notna().sum()),
        "minggu_untung_berturut_terakhir": berturut,
        "untung_minggu_terakhir_rp_per_kg": float(v.iloc[-1]) if pd.notna(v.iloc[-1]) else np.nan,
    }


def is_layak(m: dict, q: dict) -> bool:
    ok = m["porsi_minggu_untung"] >= q["layak_min_porsi_minggu_untung"]
    if q.get("layak_median_untung_positif", True):
        ok = ok and m["median_untung_rp_per_kg"] > 0
    return bool(ok)


RUTE = ["kota_sumber_id", "kota_tujuan_id", "komoditas_id"]


def _compute(w: pd.DataFrame, biaya: pd.DataFrame, q: dict, pengali: list[float], kons: float,
             tujuan_pt: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    spreads, ringkas = [], []
    for b in biaya.itertuples():
        src = w[(w.kota_id == b.kota_sumber_id) & (w.jenis_pasar_id == q["harga_sumber_jenis_pasar_id"])
                & (w.komoditas_id == b.komoditas_id)]
        dst = w[(w.kota_id == b.kota_tujuan_id) & (w.jenis_pasar_id == tujuan_pt) & (w.komoditas_id == b.komoditas_id)]
        s = weekly_spread(src, dst, b._asdict(), pengali, q["kecualikan_minggu_sumber_usang"])
        ident = {"kota_sumber_id": b.kota_sumber_id, "kota_sumber": b.kota_sumber, "kota_tujuan_id": b.kota_tujuan_id,
                 "kota_tujuan": b.kota_tujuan, "komoditas_id": b.komoditas_id, "kualitas": b.kualitas,
                 "jarak_jalan_km": b.jarak_jalan_km, "tujuan_jenis_pasar_id": tujuan_pt}
        spreads.append(s.assign(**ident))
        for p in pengali:
            m = route_metrics(s, p, q["jendela_terakhir_minggu"])
            ringkas.append({**ident, "pengali": p, **m, "minggu_sumber_usang": int(s.sumber_usang.sum()),
                            "selisih_kotor_median_rp_per_kg": float(s.spread_kotor.median()),
                            "biaya_logistik_median_rp_per_kg": float(s[_col("biaya_logistik", p)].median()),
                            "layak": is_layak(m, q) if p == kons else None})
    r = pd.DataFrame(ringkas)
    k = r[r.pengali == kons][RUTE + ["layak"]].rename(columns={"layak": "layak_konservatif"})
    r = r.drop(columns="layak").merge(k, on=RUTE)
    r["layak_konservatif"] = r.layak_konservatif.astype(bool)
    return pd.concat(spreads, ignore_index=True), r


def run(cfg: dict, lcfg: dict) -> dict:
    q = cfg["analisis"]["q2_rute"]
    pengali = lcfg["sensitivitas"]["pengali"]
    kons = lcfg["sensitivitas"]["skenario_konservatif"]
    w = load_weekly(cfg)
    biaya = pd.read_csv(ROOT / cfg["paths"]["reference"] / "biaya_rute.csv")
    sp, r = _compute(w, biaya, q, pengali, kons, q["harga_tujuan_jenis_pasar_id"])
    # Uji ketahanan: jual dengan harga pedagang besar di kota tujuan
    _, alt = _compute(w, biaya, q, pengali, kons, q["uji_ketahanan_tujuan_jenis_pasar_id"])
    alt_k = alt[alt.pengali == kons][RUTE + ["layak_konservatif", "median_untung_rp_per_kg", "porsi_minggu_untung",
                                             "selisih_kotor_median_rp_per_kg"]]
    alt_k = alt_k.rename(columns={"layak_konservatif": "layak_jika_jual_ke_pedagang_besar",
                                  "median_untung_rp_per_kg": "median_untung_jual_ke_pedagang_besar",
                                  "porsi_minggu_untung": "porsi_untung_jual_ke_pedagang_besar",
                                  "selisih_kotor_median_rp_per_kg": "selisih_kotor_ke_pedagang_besar"})
    r = r.merge(alt_k, on=RUTE, how="left")
    # Uji paling berat: ongkos pengali tertinggi DAN dijual ke pedagang besar di kota tujuan
    p_maks = max(pengali)
    alt_m = alt[alt.pengali == p_maks][RUTE + ["median_untung_rp_per_kg", "porsi_minggu_untung"]].copy()
    alt_m["layak_jual_pb_ongkos_maks"] = [is_layak({"porsi_minggu_untung": a, "median_untung_rp_per_kg": b}, q)
                                          for a, b in zip(alt_m.porsi_minggu_untung, alt_m.median_untung_rp_per_kg)]
    alt_m = alt_m.rename(columns={"median_untung_rp_per_kg": "median_untung_jual_pb_ongkos_maks",
                                  "porsi_minggu_untung": "porsi_untung_jual_pb_ongkos_maks"})
    r = r.merge(alt_m, on=RUTE, how="left")
    r["tahan_ongkos_maks_jual_ke_pedagang_besar"] = (r.layak_konservatif & r.layak_jika_jual_ke_pedagang_besar.fillna(False).astype(bool)
                                                     & r.layak_jual_pb_ongkos_maks.fillna(False).astype(bool))
    per_kom = (r[r.pengali == kons].groupby("kualitas")
               .agg(rute=("layak_konservatif", "size"), rute_layak=("layak_konservatif", "sum"),
                    rute_layak_jual_ke_pedagang_besar=("layak_jika_jual_ke_pedagang_besar", "sum"),
                    median_untung_terbaik=("median_untung_rp_per_kg", "max"))
               .reset_index())
    sens = (r.groupby("pengali").apply(lambda d: pd.Series({
        "rute_untung_median_positif": int((d.median_untung_rp_per_kg > 0).sum()),
        "rute_untung_60pct_minggu": int((d.porsi_minggu_untung >= q["layak_min_porsi_minggu_untung"]).sum())}),
        include_groups=False).reset_index())
    return {"spread": sp, "ringkas": r, "per_kom": per_kom, "sens": sens, "kons": kons, "p_maks": p_maks}


def figures(res: dict) -> dict:
    style()
    out = {}
    r, kons, sp = res["ringkas"], res["kons"], res["spread"]
    k = r[r.pengali == kons].sort_values("median_untung_rp_per_kg")
    n_layak = int(k.layak_konservatif.sum())
    terbaik = k[k.layak_konservatif].iloc[-1] if n_layak else k.iloc[-1]

    # 1) Semua rute: untung per kg (median) pada skenario konservatif
    fig, ax = plt.subplots(figsize=(9, 9))
    label = [f"{LABEL_PENDEK[x.kualitas]}: {x.kota_sumber.replace('Kota ', '')} → {x.kota_tujuan.replace('Kota ', '')}"
             for x in k.itertuples()]
    TEAL_MUDA = "#9fdcc4"
    warna = [TEAL if (a and b) else (TEAL_MUDA if a else GRAY)
             for a, b in zip(k.layak_konservatif, k.layak_jika_jual_ke_pedagang_besar)]
    ax.barh(range(len(k)), k.median_untung_rp_per_kg / 1000, color=warna, height=0.7)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(range(len(k)), label, fontsize=8)
    for i, x in enumerate(k.itertuples()):
        neg = x.median_untung_rp_per_kg < 0
        ax.text(0 if neg else x.median_untung_rp_per_kg / 1000, i, f"  {x.porsi_minggu_untung * 10:.0f}/10 minggu ",
                va="center", ha="left", fontsize=7, color=INK2)
    lo, hi = ax.get_xlim()
    ax.set_xlim(lo, hi * 1.08)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=TEAL, label="layak, juga jika dijual ke pedagang besar (paling aman)"),
                       Patch(color=TEAL_MUDA, label="layak hanya jika dijual dengan harga eceran"),
                       Patch(color=GRAY, label="tidak layak")], frameon=False, loc="lower right", fontsize=8)
    ax.set_xlabel(f"untung per kg setelah ongkos angkut (Rp ribu, median mingguan), ongkos {_x(kons)} (perkiraan)")
    ax.set_title(f"{n_layak} dari {len(k)} rute masih untung setelah ongkos angkut {_x(kons)}; yang terbaik\n"
                 f"{LABEL_PENDEK[terbaik.kualitas].lower()} {terbaik.kota_sumber} → {terbaik.kota_tujuan}")
    ax.grid(axis="y", visible=False)
    out["rute"] = save_fig(fig, "q2_rute_untung_konservatif")

    # 2) Rute terbaik: selisih harga vs garis ongkos
    s = sp[(sp.kota_sumber_id == terbaik.kota_sumber_id) & (sp.kota_tujuan_id == terbaik.kota_tujuan_id)
           & (sp.komoditas_id == terbaik.komoditas_id)].sort_values("minggu_akhir")
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot(s.minggu_akhir, s.spread_kotor / 1000, color=TEAL, lw=2, label="selisih harga (tujuan − sumber)")
    ax.plot(s.minggu_akhir, s[_col("biaya_logistik", 1.0)] / 1000, color=INK2, lw=1.2, ls="--", label="ongkos angkut ×1 (perkiraan)")
    ax.plot(s.minggu_akhir, s[_col("biaya_logistik", kons)] / 1000, color=ORANGE, lw=1.5, ls="--",
            label=f"ongkos angkut {_x(kons)} (perkiraan)")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_ylabel("Rp ribu/kg")
    ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    seberapa = "hampir selalu" if terbaik.porsi_minggu_untung >= 0.95 else "biasanya"
    ax.set_title(f"{LABEL_PENDEK[terbaik.kualitas]} {terbaik.kota_sumber} → {terbaik.kota_tujuan}: selisih harga {seberapa} "
                 f"di atas ongkos angkut\n(untung pada {terbaik.porsi_minggu_untung:.0%} minggu dengan ongkos {_x(kons)})")
    out["terbaik"] = save_fig(fig, "q2_rute_terbaik_selisih_vs_ongkos")
    return out


def _x(p: float) -> str:
    return f"×{p:g}".replace(".", ",")


def _dari10(porsi: float) -> str:
    return f"{porsi * 10:.1f}".replace(".", ",") + " dari 10"


def _bertahan(porsi: float, rata: float) -> str:
    return "hampir selalu" if porsi >= 0.95 else f"{rata:.0f} minggu".replace(".", ",")


def write_summary(res: dict, figs: dict, cfg: dict) -> None:
    r, kons, pk, sens, p_maks = res["ringkas"], res["kons"], res["per_kom"], res["sens"], res["p_maks"]
    q = cfg["analisis"]["q2_rute"]
    k = r[r.pengali == kons].sort_values("median_untung_rp_per_kg", ascending=False)
    lay = k[k.layak_konservatif]
    t = lay.iloc[0] if len(lay) else k.iloc[0]
    n_alt = int(k.layak_jika_jual_ke_pedagang_besar.sum())
    keduanya = k[k.layak_konservatif & k.layak_jika_jual_ke_pedagang_besar]
    tahan = keduanya[keduanya.tahan_ongkos_maks_jual_ke_pedagang_besar]
    goyah = keduanya[~keduanya.tahan_ongkos_maks_jual_ke_pedagang_besar]
    nm = lambda x: f"{LABEL_PENDEK[x.kualitas].lower()} {x.kota_sumber} ke {x.kota_tujuan}"  # noqa: E731
    goyah_t = "; ".join(f"{nm(x)} ({_dari10(x.porsi_untung_jual_pb_ongkos_maks)} minggu)" for x in goyah.itertuples())
    km_ = r[r.pengali == kons].set_index(RUTE).median_untung_rp_per_kg
    mx_ = r[r.pengali == p_maks].set_index(RUTE).median_untung_rp_per_kg
    berbalik = km_[(km_ > 0) & (mx_.reindex(km_.index) <= 0)]
    tipis = km_[(km_ > 0) & (km_ < 1000 * -(-berbalik.max() // 1000))] if len(berbalik) else km_.iloc[:0]
    balik_t = (f"{len(berbalik)} rute berubah rugi bila ongkos {_x(p_maks)}; semuanya bermargin di bawah "
               f"{rp(1000 * -(-berbalik.max() // 1000))}/kg pada ongkos {_x(kons)}."
               if len(berbalik) and len(tipis) == len(berbalik) else f"{len(berbalik)} rute berubah rugi bila ongkos {_x(p_maks)}.")
    km = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    tabel = "\n".join(
        f"| {LABEL_PENDEK[x.kualitas]} | {x.kota_sumber} → {x.kota_tujuan} | {km(x.jarak_jalan_km)} | "
        f"{rp(x.selisih_kotor_median_rp_per_kg)} | {rp(x.biaya_logistik_median_rp_per_kg)} | {rp(x.median_untung_rp_per_kg)} | "
        f"{_dari10(x.porsi_minggu_untung)} | {_bertahan(x.porsi_minggu_untung, x.persistensi_rata_minggu)} | "
        f"{x.untung_dari_jendela}/{x.jendela_berdata} | {'✅ layak' if x.layak_konservatif else '—'} | "
        f"{rp(x.median_untung_jual_ke_pedagang_besar)} ({'✅' if x.layak_jika_jual_ke_pedagang_besar else '—'}) | "
        f"{'✅' if x.tahan_ongkos_maks_jual_ke_pedagang_besar else '—'} |"
        for x in k.itertuples())
    s_tbl = "\n".join(f"| {_x(x.pengali)} | {x.rute_untung_median_positif} | {x.rute_untung_60pct_minggu} |"
                      for x in sens.itertuples())
    kom = "\n".join(f"| {LABEL_PENDEK[x.kualitas]} | {x.rute_layak} dari {x.rute} | {x.rute_layak_jual_ke_pedagang_besar} dari {x.rute} | "
                    f"{rp(x.median_untung_terbaik)} |" for x in pk.sort_values("rute_layak", ascending=False).itertuples())
    text = f"""# Q2 — Rute pindah stok

Dibuat otomatis oleh `python -m src.analysis.spread` pada {datetime.now():%Y-%m-%d %H:%M}.
Harga sumber = **pedagang besar** di kota sumber (harga beli distributor); harga tujuan = **pasar tradisional** di kota tujuan
(analisis utama, sesuai brief); mingguan, Juli 2023 – Oktober 2026. Ongkos angkut = **perkiraan, bukan data**
(`config/biaya_logistik.yaml`). Rute **layak** = pada ongkos {_x(kons)}: untung pada ≥ {q['layak_min_porsi_minggu_untung']:.0%} minggu
**dan** median untung > 0.

## Temuan (bahasa dashboard)
**{len(lay)} rute masih untung setelah ongkos angkut; yang terbaik {LABEL_PENDEK[t.kualitas].lower()} {t.kota_sumber} → {t.kota_tujuan}.**
(Dari {len(k)} rute yang diuji, dengan ongkos angkut {_x(kons)} perkiraan.) Di rute terbaik, harga di {t.kota_tujuan} rata-rata
{rp(t.selisih_kotor_median_rp_per_kg)}/kg lebih mahal daripada harga pedagang besar di {t.kota_sumber}; setelah ongkos angkut
masih tersisa sekitar {rp(t.median_untung_rp_per_kg)}/kg. Minggu untung: {_dari10(t.porsi_minggu_untung)}.
Tindakan: prioritaskan rute yang layak; untuk rute lain, pindahkan stok hanya saat selisih minggu itu jauh di atas ongkos.

**Uji ketahanan:** jika stok dijual ke pedagang besar di kota tujuan (bukan dengan harga eceran), rute yang layak tinggal
**{n_alt} dari {len(k)}**. {len(keduanya)} rute layak di kedua cara hitung; inilah rekomendasi yang paling aman.
Uji paling berat (ongkos {_x(p_maks)} **dan** dijual ke pedagang besar): **{len(tahan)} dari {len(keduanya)}** rute itu tetap layak.
Yang tidak lagi untung minimal {q['layak_min_porsi_minggu_untung'] * 10:.0f} dari 10 minggu: {goyah_t or '–'}.

## Per komoditas (ongkos {_x(kons)})
| Komoditas | Rute layak (jual harga eceran) | Rute layak (jual ke pedagang besar) | Untung median terbaik/kg |
|---|---|---|---|
{kom}

## Uji sensitivitas ongkos angkut (jual harga eceran)
| Pengali ongkos | Rute dengan median untung > 0 | Rute untung ≥ {q['layak_min_porsi_minggu_untung']:.0%} minggu |
|---|---|---|
{s_tbl}

{balik_t}

## Semua rute (ongkos {_x(kons)}, diurutkan dari untung terbesar)
| Komoditas | Rute | Jarak (km) | Selisih harga | Ongkos {_x(kons)} | Untung/kg | Minggu untung | Bertahan | 10 minggu terakhir | Status | Untung/kg jika jual ke pedagang besar | Tahan ongkos {_x(p_maks)} + jual ke pedagang besar |
|---|---|---|---|---|---|---|---|---|---|---|---|
{tabel}

Semua angka adalah median mingguan. "Bertahan" = rata-rata panjang rangkaian minggu untung berturut-turut (minggu tanpa
data dilewati); "hampir selalu" = untung pada ≥ 95% minggu.

## Batasan
- Ongkos angkut adalah asumsi (tarif truk, tol, muatan, susut); lihat `docs/biaya_logistik_report.md`.
- Harga eceran di kota tujuan belum tentu harga jual yang bisa didapat distributor (lihat uji ketahanan);
  volume & ketersediaan stok tidak diketahui.
- Harga pedagang besar dicatat ~seminggu sekali (Kamis) dan bisa usang; minggu dengan harga sumber usang dikecualikan.

## File
- Tabel: `reports/tables/q2_rute_ringkasan.csv` (rute × skenario), `q2_per_komoditas.csv`, `q2_sensitivitas.csv`
- Data mingguan per rute: `data/interim/spread_mingguan.parquet`
- Grafik: `reports/figures/{figs['rute'].name}`, `reports/figures/{figs['terbaik'].name}`
"""
    (ROOT / "reports" / "q2_rute.md").write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, lcfg = load_cfg()
    res = run(cfg, lcfg)
    res["spread"].to_parquet(ROOT / cfg["paths"]["interim"] / "spread_mingguan.parquet", index=False)
    save_table(res["ringkas"], "q2_rute_ringkasan")
    save_table(res["per_kom"], "q2_per_komoditas")
    save_table(res["sens"], "q2_sensitivitas")
    figs = figures(res)
    write_summary(res, figs, cfg)
    print(res["sens"].to_string(index=False))
    print(res["per_kom"].to_string(index=False))


if __name__ == "__main__":
    main()
