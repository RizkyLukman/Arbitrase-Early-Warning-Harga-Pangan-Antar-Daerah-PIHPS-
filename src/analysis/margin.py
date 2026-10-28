"""Q5 — Berapa tambahan harga dari produsen -> pedagang besar -> pasar tradisional/modern per kota?

Data mingguan diringkas menjadi median BULANAN per kota x komoditas x tingkat (harga produsen jarang diperbarui; audit
pasca-cleaning: produsen > pedagang besar pada 31% kota-hari). Dua cakupan:
    utama    : kota yang punya ketiga tingkat dengan NAMA SAMA (sesuai brief: "analisis hanya kota yang lengkap")
    tambahan : pasangan kota (pedagang besar + pasar) <-> kabupaten sentra (produsen), config rantai_pasok,
               berlabel PERLU_VERIFIKASI
Ukuran per kota x komoditas x bulan:
    tambahan_pedagang_besar_pct = pedagang_besar / produsen - 1
    tambahan_eceran_pct         = tradisional / pedagang_besar - 1
    tambahan_total_pct          = tradisional / produsen - 1
    hemat_beli_produsen_vs_eceran_pct = 1 - produsen / tradisional   -> "x% lebih murah daripada harga pasar"
    hemat_beli_pedagang_besar_vs_eceran_pct = 1 - pedagang_besar / tradisional
    hemat_beli_produsen_vs_pedagang_besar_pct = 1 - 1 / (1 + tambahan_pedagang_besar_pct)
        (pembanding sumber beli distributor saat ini; dihitung dari nilai tengah tambahan di pedagang besar per kota/komoditas)

Output: reports/tables/q5_*.csv, reports/figures/q5_*.png, reports/q5_margin.md
"""
from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from src.analysis.common import (
    BLUE, GRAY, INK, INK2, KOMODITAS_URUT, LABEL_PENDEK, ORANGE, ROOT, TEAL, load_cfg, load_weekly, rp, save_fig,
    save_table, style,
)

import matplotlib.pyplot as plt  # noqa: E402


def margins(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["tambahan_pedagang_besar_pct"] = df.pedagang_besar / df.produsen - 1
    out["tambahan_eceran_pct"] = df.tradisional / df.pedagang_besar - 1
    out["tambahan_total_pct"] = df.tradisional / df.produsen - 1
    out["hemat_beli_produsen_vs_eceran_pct"] = 1 - df.produsen / df.tradisional
    out["hemat_beli_pedagang_besar_vs_eceran_pct"] = 1 - df.pedagang_besar / df.tradisional
    out["produsen_lebih_mahal"] = df.produsen > df.pedagang_besar
    out["tambahan_pedagang_besar_rp"] = df.pedagang_besar - df.produsen
    out["tambahan_eceran_rp"] = df.tradisional - df.pedagang_besar
    if "modern" in df:
        out["selisih_modern_vs_tradisional_pct"] = df.modern / df.tradisional - 1
    return out


def _monthly(w: pd.DataFrame) -> pd.DataFrame:
    return (w.assign(bulan=w.minggu_akhir.dt.to_period("M"))
            .groupby(["kota_id", "kota", "komoditas_id", "kualitas", "jenis_pasar_id", "bulan"])
            .agg(harga=("harga", "median"), usang=("is_usang", "mean")).reset_index())


def run(cfg: dict) -> dict:
    q, rp_cfg = cfg["analisis"]["q5_margin"], cfg["rantai_pasok"]
    w = load_weekly(cfg)
    m = _monthly(w)
    nama_pt = {q["produsen_jenis_pasar_id"]: "produsen", q["pedagang_besar_jenis_pasar_id"]: "pedagang_besar",
               q["tradisional_jenis_pasar_id"]: "tradisional", q["modern_jenis_pasar_id"]: "modern"}
    m["tingkat"] = m.jenis_pasar_id.map(nama_pt)
    lebar = m.pivot_table(index=["kota_id", "kota", "komoditas_id", "kualitas", "bulan"], columns="tingkat",
                          values="harga").reset_index()
    usang_prod = m[m.tingkat == "produsen"].set_index(["kota_id", "komoditas_id", "bulan"]).usang

    # Utama: nama sama
    utama = lebar.dropna(subset=["produsen", "pedagang_besar", "tradisional"]).assign(cakupan="utama (kota sama)")
    utama["produsen_dari"] = utama.kota
    # Tambahan: pasangan kota <-> kabupaten sentra
    tamb = []
    for p in rp_cfg["pasangan_kota_kabupaten"]:
        for com in p["komoditas"]:
            kota = lebar[(lebar.kota_id == p["kota_id"]) & (lebar.komoditas_id == com)].drop(columns=["produsen"], errors="ignore")
            prod = lebar[(lebar.kota_id == p["produsen_kota_id"]) & (lebar.komoditas_id == com)][["bulan", "produsen"]]
            x = kota.merge(prod, on="bulan").assign(cakupan="tambahan (kabupaten sentra, PERLU_VERIFIKASI)",
                                                    produsen_dari=p["produsen"])
            tamb.append(x)
    tamb = pd.concat(tamb, ignore_index=True).dropna(subset=["produsen", "pedagang_besar", "tradisional"])
    semua = margins(pd.concat([utama, tamb], ignore_index=True))
    semua["porsi_bulan_produsen_usang"] = [usang_prod.get((k, c, b), np.nan) for k, c, b in
                                           zip(semua.kota_id, semua.komoditas_id, semua.bulan)]

    # Per kota x komoditas x cakupan
    per_kota = (semua.groupby(["cakupan", "kualitas", "kota", "produsen_dari"])
                .agg(bulan=("bulan", "count"),
                     produsen=("produsen", "median"), pedagang_besar=("pedagang_besar", "median"),
                     tradisional=("tradisional", "median"),
                     tambahan_pedagang_besar_pct=("tambahan_pedagang_besar_pct", "median"),
                     tambahan_eceran_pct=("tambahan_eceran_pct", "median"),
                     tambahan_total_pct=("tambahan_total_pct", "median"),
                     hemat_beli_produsen_pct=("hemat_beli_produsen_vs_eceran_pct", "median"),
                     hemat_beli_pedagang_besar_pct=("hemat_beli_pedagang_besar_vs_eceran_pct", "median"),
                     porsi_bulan_produsen_lebih_mahal=("produsen_lebih_mahal", "mean"))
                .reset_index())
    per_kota = per_kota[per_kota.bulan >= q["min_bulan_lengkap"]]
    per_kota["hemat_beli_produsen_vs_pedagang_besar_pct"] = 1 - 1 / (1 + per_kota.tambahan_pedagang_besar_pct)
    # Per komoditas (cakupan utama + tambahan digabung, kota sebagai unit)
    per_kom = (per_kota.groupby("kualitas")
               .agg(kota=("kota", "size"), produsen=("produsen", "median"), pedagang_besar=("pedagang_besar", "median"),
                    tradisional=("tradisional", "median"),
                    tambahan_pedagang_besar_pct=("tambahan_pedagang_besar_pct", "median"),
                    tambahan_eceran_pct=("tambahan_eceran_pct", "median"),
                    tambahan_total_pct=("tambahan_total_pct", "median"),
                    hemat_beli_produsen_pct=("hemat_beli_produsen_pct", "median"),
                    hemat_beli_pedagang_besar_pct=("hemat_beli_pedagang_besar_pct", "median"),
                    porsi_bulan_produsen_lebih_mahal=("porsi_bulan_produsen_lebih_mahal", "mean"))
               .reindex(KOMODITAS_URUT).dropna(how="all").reset_index())
    per_kom["hemat_beli_produsen_vs_pedagang_besar_pct"] = 1 - 1 / (1 + per_kom.tambahan_pedagang_besar_pct)
    # Pasar modern vs tradisional (brief Q5: "pasar tradisional/modern"), kota dengan kedua harga
    mv = lebar.dropna(subset=["modern", "tradisional"]).assign(r=lambda d: d.modern / d.tradisional - 1)
    mk = mv.groupby(["kualitas", "kota"]).r.median().groupby(level=0).agg(["median", "size"])
    per_kom["selisih_modern_vs_tradisional_pct"] = per_kom.kualitas.map(mk["median"])
    per_kom["kota_modern"] = per_kom.kualitas.map(mk["size"])
    # Tren tambahan harga per bulan (median antar kota)
    tren = (semua.groupby(["kualitas", "bulan"])[["tambahan_pedagang_besar_pct", "tambahan_eceran_pct"]].median()
            .reset_index())
    tren["bulan"] = tren.bulan.astype(str)
    semua["bulan"] = semua.bulan.astype(str)
    return {"bulanan": semua, "per_kota": per_kota, "per_kom": per_kom, "tren": tren}


def figures(res: dict) -> dict:
    style()
    pk = res["per_kom"].copy()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    y = np.arange(len(pk))
    ax.barh(y, pk.produsen / 1000, color=GRAY, height=0.6, label="harga produsen")
    ax.barh(y, (pk.pedagang_besar - pk.produsen) / 1000, left=pk.produsen / 1000, color=BLUE, height=0.6,
            label="+ tambahan di pedagang besar")
    ax.barh(y, (pk.tradisional - pk.pedagang_besar) / 1000, left=pk.pedagang_besar / 1000, color=ORANGE, height=0.6,
            label="+ tambahan di pasar (eceran)")
    for i, x in enumerate(pk.itertuples()):
        ax.text(x.tradisional / 1000, i, f"  produsen {x.hemat_beli_produsen_vs_pedagang_besar_pct:.0%} di bawah pedagang besar, "
                f"{x.hemat_beli_produsen_pct:.0%} di bawah pasar", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, [LABEL_PENDEK[k] for k in pk.kualitas])
    ax.invert_yaxis()
    ax.set_xlim(0, pk.tradisional.max() / 1000 * 1.75)
    ax.set_xlabel("Rp ribu/kg (median antar kota & bulan)")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    top = pk.sort_values("hemat_beli_produsen_vs_pedagang_besar_pct").iloc[-1]
    low = pk.sort_values("hemat_beli_produsen_vs_pedagang_besar_pct").iloc[0]
    ax.set_title(f"Beli langsung di produsen sekitar {top.hemat_beli_produsen_vs_pedagang_besar_pct:.0%} lebih murah daripada pedagang besar\n"
                 f"untuk {LABEL_PENDEK[top.kualitas].lower()}; untuk {LABEL_PENDEK[low.kualitas].lower()} hanya "
                 f"{low.hemat_beli_produsen_vs_pedagang_besar_pct:.0%}")
    ax.grid(axis="y", visible=False)
    out = {"tingkat": save_fig(fig, "q5_tambahan_harga_per_tingkat")}

    t = res["tren"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), sharey=True)
    for ax, col, judul in [(axes[0], "tambahan_pedagang_besar_pct", "produsen → pedagang besar"),
                           (axes[1], "tambahan_eceran_pct", "pedagang besar → pasar")]:
        for kom, warna in [("Cabai Rawit Merah", ORANGE), ("Bawang Merah Ukuran Sedang", TEAL), ("Telur Ayam Ras Segar", BLUE)]:
            s = t[t.kualitas == kom]
            ax.plot(pd.PeriodIndex(s.bulan, freq="M").to_timestamp(), s[col] * 100, color=warna, lw=1.8,
                    label=LABEL_PENDEK[kom])
        ax.axhline(0, color=GRAY, lw=1)
        ax.set_title(f"Tambahan harga {judul}", fontsize=10)
        import matplotlib.dates as mdates
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    axes[0].set_ylabel("% (median antar kota)")
    axes[0].legend(frameon=False, fontsize=8)
    sd = t.groupby("kualitas")[["tambahan_pedagang_besar_pct", "tambahan_eceran_pct"]].std()
    n_lebih = int((sd.tambahan_pedagang_besar_pct > sd.tambahan_eceran_pct).sum())
    judul = ("Tambahan harga di tingkat pedagang besar lebih naik-turun daripada di tingkat pasar"
             if n_lebih == len(sd) else
             f"Tambahan harga di tingkat pedagang besar lebih naik-turun untuk {n_lebih} dari {len(sd)} komoditas")
    fig.suptitle(judul, x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    out["tren"] = save_fig(fig, "q5_tren_tambahan_harga")
    return out


def write_summary(res: dict, figs: dict) -> None:
    pk, pc = res["per_kom"], res["per_kota"]
    pp = lambda v: "–" if pd.isna(v) else f"{v:.0%}"  # noqa: E731
    tbl = "\n".join(
        f"| {LABEL_PENDEK[x.kualitas]} | {int(x.kota)} | {rp(x.produsen)} | {rp(x.pedagang_besar)} | {rp(x.tradisional)} | "
        f"{pp(x.tambahan_pedagang_besar_pct)} | {pp(x.tambahan_eceran_pct)} | {pp(x.hemat_beli_produsen_pct)} | "
        f"{pp(x.hemat_beli_pedagang_besar_pct)} | {pp(x.hemat_beli_produsen_vs_pedagang_besar_pct)} | {pp(x.porsi_bulan_produsen_lebih_mahal)} |"
        for x in pk.itertuples())
    kota_tbl = "\n".join(
        f"| {LABEL_PENDEK[x.kualitas]} | {x.kota} | {x.produsen_dari} | {'utama' if x.cakupan.startswith('utama') else 'tambahan*'} | "
        f"{x.bulan} | {pp(x.tambahan_pedagang_besar_pct)} | {pp(x.tambahan_eceran_pct)} | {pp(x.hemat_beli_produsen_pct)} | "
        f"{pp(x.hemat_beli_produsen_vs_pedagang_besar_pct)} | {pp(x.porsi_bulan_produsen_lebih_mahal)} |"
        for x in pc.sort_values(["kualitas", "hemat_beli_produsen_pct"], ascending=[True, False]).itertuples())
    top = pk.sort_values("hemat_beli_produsen_pct").iloc[-1]
    low = pk.sort_values("hemat_beli_produsen_pct").iloc[0]
    top_pb = pk.sort_values("hemat_beli_produsen_vs_pedagang_besar_pct").iloc[-1]
    low_pb = pk.sort_values("hemat_beli_produsen_vs_pedagang_besar_pct").iloc[0]
    urut_pb = pk.sort_values("tambahan_pedagang_besar_pct", ascending=False)
    besar_k = urut_pb[urut_pb.tambahan_pedagang_besar_pct >= 0.15]
    kecil_k = urut_pb[urut_pb.tambahan_pedagang_besar_pct < 0.10]
    besar = ", ".join(LABEL_PENDEK[k].lower() for k in besar_k.kualitas) or "–"
    tbesar = ", ".join(f"{v:.0%}" for v in besar_k.tambahan_pedagang_besar_pct) or "–"
    kecil = ", ".join(LABEL_PENDEK[k].lower() for k in kecil_k.kualitas) or "–"
    tkecil = ", ".join(f"{v:.0%}" for v in kecil_k.tambahan_pedagang_besar_pct) or "–"
    mk = pk.dropna(subset=["selisih_modern_vs_tradisional_pct"])
    mahal = mk[mk.selisih_modern_vs_tradisional_pct >= 0.10]
    mirip = mk[mk.selisih_modern_vs_tradisional_pct.abs() < 0.10]
    modern_kalimat = (
        (f"Pasar modern jauh lebih mahal daripada pasar tradisional untuk "
         f"{', '.join(LABEL_PENDEK[k].lower() for k in mahal.kualitas)}" if len(mahal) else "")
        + (f"; untuk {', '.join(LABEL_PENDEK[k].lower() for k in mirip.kualitas)} harganya hampir sama" if len(mirip) else "")
        + ". Pasar modern bukan sumber pembelian yang lebih murah.")
    mod = "\n".join(f"| {LABEL_PENDEK[x.kualitas]} | {int(x.kota_modern)} | {pp(x.selisih_modern_vs_tradisional_pct)} |"
                    for x in pk.dropna(subset=["selisih_modern_vs_tradisional_pct"]).itertuples())
    text = f"""# Q5 — Tambahan harga di tiap tingkat rantai pasok

Dibuat otomatis oleh `python -m src.analysis.margin` pada {datetime.now():%Y-%m-%d %H:%M}.
Median bulanan, Juli 2023 – Oktober 2026. Cakupan utama: kota dengan ketiga tingkat bernama sama; cakupan tambahan:
pasangan kota ↔ kabupaten sentra (`config.rantai_pasok`, PERLU_VERIFIKASI).

## Temuan (bahasa dashboard)
**Dibanding pedagang besar (sumber beli distributor saat ini), membeli langsung di produsen sekitar
{top_pb.hemat_beli_produsen_vs_pedagang_besar_pct:.0%} lebih murah untuk {LABEL_PENDEK[top_pb.kualitas].lower()}**; untuk
{LABEL_PENDEK[low_pb.kualitas].lower()} hanya {low_pb.hemat_beli_produsen_vs_pedagang_besar_pct:.0%}.
Dibanding harga pasar eceran, selisihnya lebih besar: {top.hemat_beli_produsen_pct:.0%} untuk {LABEL_PENDEK[top.kualitas].lower()}
(median antar kota; harga produsen {rp(top.produsen)}/kg vs pasar {rp(top.tradisional)}/kg), {low.hemat_beli_produsen_pct:.0%} untuk
{LABEL_PENDEK[low.kualitas].lower()}. Angka pembanding pedagang besar inilah yang relevan untuk keputusan pengadaan.
Dibanding membeli di pedagang besar, membeli di produsen paling menghemat untuk {besar} (tambahan harga di pedagang besar
{tbesar}); untuk {kecil} tambahan di pedagang besar hanya {tkecil}.
Tindakan: jajaki pembelian langsung dari petani/pengepul di sentra untuk {besar}; untuk {kecil} pedagang besar sudah dekat
dengan harga produsen.
Catatan: harga produsen jarang diperbarui, sehingga pada sebagian bulan tercatat lebih mahal daripada pedagang besar
(kolom terakhir). Angka ini perkiraan kasar.

## Per komoditas (median antar kota)
| Komoditas | Kota | Produsen | Pedagang besar | Pasar | Tambahan di pedagang besar | Tambahan di pasar | Lebih murah jika beli di produsen (vs pasar) | Lebih murah jika beli di pedagang besar (vs pasar) | Produsen vs pedagang besar | Bulan produsen > pedagang besar |
|---|---|---|---|---|---|---|---|---|---|---|
{tbl}

## Per kota
| Komoditas | Kota | Harga produsen dari | Cakupan | Bulan | Tambahan di pedagang besar | Tambahan di pasar | Lebih murah di produsen (vs pasar) | Produsen vs pedagang besar | Bulan produsen > pedagang besar |
|---|---|---|---|---|---|---|---|---|---|
{kota_tbl}

\\* tambahan = harga produsen diambil dari kabupaten sentra di sekitar kota (PERLU_VERIFIKASI).

## Pasar modern dibanding pasar tradisional (kota yang sama)
| Komoditas | Kota | Harga pasar modern vs pasar tradisional (median) |
|---|---|---|
{mod}

{modern_kalimat}

## Batasan
- Harga produsen di PIHPS jarang diperbarui (±96% hari tidak berubah); dipakai median bulanan, tetapi tetap bisa usang.
- Cakupan kota terbatas ({int(pk.kota.min())}–{int(pk.kota.max())} kota per komoditas, sebagian lewat pasangan kabupaten yang belum
  diverifikasi); bawang putih tidak punya data produsen di Jawa.
- Harga produsen = harga di tingkat petani/peternak, belum termasuk biaya mengumpulkan & mengangkut dari banyak petani.

## File
- Tabel: `reports/tables/q5_per_komoditas.csv`, `q5_per_kota.csv`, `q5_bulanan.csv`, `q5_tren.csv`
- Grafik: {', '.join(f'`reports/figures/{p.name}`' for p in figs.values())}
"""
    (ROOT / "reports" / "q5_margin.md").write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, _ = load_cfg()
    res = run(cfg)
    save_table(res["per_kom"], "q5_per_komoditas")
    save_table(res["per_kota"], "q5_per_kota")
    save_table(res["bulanan"], "q5_bulanan")
    save_table(res["tren"], "q5_tren")
    figs = figures(res)
    write_summary(res, figs)
    print(res["per_kom"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
