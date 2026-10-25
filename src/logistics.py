"""Ongkos angkut per rute (ASUMSI, bukan data) untuk analisis selisih harga antar kota (Q2).

Input : config/biaya_logistik.yaml (asumsi + sumber), config/config.yaml (kota sumber & tujuan),
        data/reference/jarak_rute.csv & jarak_tol_referensi.csv (src/geo_reference.py),
        data/interim/harga_mingguan.parquet (harga pedagang besar di kota sumber, untuk susut & cek MPP)
Output: data/reference/biaya_rute.csv   komponen ongkos per rute x komoditas + cek batas atas MPP BPS
        docs/biaya_logistik_report.md    ringkasan otomatis

Rumus (lihat config/biaya_logistik.yaml):
    ongkos_angkut = (tarif_truk/km x (1 + premi_berpendingin) x jarak + tarif_tol/km x porsi_tol x jarak) / muatan
                    + bongkar_muat                                                               [Rp/kg]
    biaya_logistik = (ongkos_angkut + susut_pct x harga_sumber) x pengali_sensitivitas           [Rp/kg]
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("logistics")


def tarif_tol_per_km(lcfg: dict, jarak_ref: pd.DataFrame) -> tuple[float, dict]:
    """Tarif tol per km = nilai terbesar (konservatif) dari rute referensi: tarif_rp / jarak jalan."""
    j = jarak_ref.set_index("rute_tol").jarak_jalan_km
    detail = {k: v["tarif_rp"] / j[k] for k, v in lcfg["tol"]["rute_referensi"].items()}
    return max(detail.values()), detail


def ongkos_angkut_rp_per_kg(jarak_km: float, komoditas_id: str, lcfg: dict, tol_per_km: float) -> dict:
    premi = lcfg["premi_berpendingin"].get(komoditas_id, lcfg["premi_berpendingin"].get("lainnya", 0.0))
    muatan = lcfg["muatan_efektif_kg"][komoditas_id]["kg"]
    truk = lcfg["truk"]["tarif_per_km"] * (1 + premi) * jarak_km
    tol = tol_per_km * lcfg["tol"]["porsi_jarak_tol"] * jarak_km
    bongkar = lcfg["penanganan"]["bongkar_muat_rp_per_kg"]
    return {"biaya_truk_rp": truk, "biaya_tol_rp": tol, "muatan_efektif_kg": muatan, "premi_berpendingin": premi,
            "bongkar_muat_rp_per_kg": bongkar, "ongkos_angkut_rp_per_kg": (truk + tol) / muatan + bongkar}


def biaya_logistik(ongkos_angkut: float, susut_pct: float, harga_sumber: float, pengali: float = 1.0) -> float:
    """Total biaya logistik Rp/kg untuk satu skenario sensitivitas. Dipakai juga oleh src/analysis/spread.py."""
    return (ongkos_angkut + susut_pct * harga_sumber) * pengali


def cek_mpp(ongkos_angkut: float, komoditas_id: str, harga_sumber: float, lcfg: dict) -> dict:
    """Bandingkan ongkos angkut dengan MPP BPS dalam rupiah (MPP% x harga sumber).

    ok: <= ambang (default 50%) MPP; tinggi: > ambang; melebihi: > 100% MPP (asumsi tidak masuk akal); tanpa_mpp.
    """
    m = lcfg["batas_atas_mpp"]["komoditas"].get(komoditas_id, {}).get("mpp_pct")
    if m is None:
        return {"mpp_pct": None, "mpp_rp_per_kg": None, "porsi_dari_mpp": None, "status_mpp": "tanpa_mpp"}
    mpp_rp = m / 100 * harga_sumber
    porsi = ongkos_angkut / mpp_rp
    ambang = lcfg["batas_atas_mpp"]["ambang_peringatan"]
    status = "melebihi" if porsi > 1 else ("tinggi" if porsi > ambang else "ok")
    return {"mpp_pct": m, "mpp_rp_per_kg": mpp_rp, "porsi_dari_mpp": porsi, "status_mpp": status}


def build(cfg: dict, lcfg: dict) -> tuple[pd.DataFrame, dict]:
    ref = ROOT / cfg["paths"]["reference"]
    jarak = pd.read_csv(ref / "jarak_rute.csv")
    tol_km, tol_detail = tarif_tol_per_km(lcfg, pd.read_csv(ref / "jarak_tol_referensi.csv"))
    w = pd.read_parquet(ROOT / cfg["paths"]["interim"] / "harga_mingguan.parquet")
    akhir = w.minggu_akhir.max()
    pb = w[(w.jenis_pasar_id == 3) & (w.minggu_akhir > akhir - pd.Timedelta(weeks=52))]
    harga_sumber = pb.groupby(["kota_id", "komoditas_id"]).harga.median()
    nama = w.drop_duplicates("kota_id").set_index("kota_id").kota
    kual = w.drop_duplicates("komoditas_id").set_index("komoditas_id").kualitas

    rows = []
    for sid, s in cfg["wilayah"]["kota_sumber"].items():
        for com in s["komoditas"]:
            hs = harga_sumber.get((sid, com))
            for tid in cfg["wilayah"]["kota_tujuan"]:
                km = jarak[(jarak.kota_sumber_id == sid) & (jarak.kota_tujuan_id == tid)].jarak_jalan_km.iloc[0]
                o = ongkos_angkut_rp_per_kg(km, com, lcfg, tol_km)
                susut = lcfg["penanganan"]["susut_pct"][com]
                row = {"kota_sumber_id": sid, "kota_sumber": nama[sid], "kota_tujuan_id": tid, "kota_tujuan": nama[tid],
                       "komoditas_id": com, "kualitas": kual[com], "jarak_jalan_km": km, "tarif_tol_per_km": tol_km, **o,
                       "susut_pct": susut, "harga_sumber_median_52m": hs, "susut_rp_per_kg": susut * hs,
                       "biaya_logistik_x1_rp_per_kg": biaya_logistik(o["ongkos_angkut_rp_per_kg"], susut, hs, 1.0)}
                row.update(cek_mpp(o["ongkos_angkut_rp_per_kg"], com, hs, lcfg))
                for p in lcfg["sensitivitas"]["pengali"]:
                    row[f"biaya_logistik_x{p:g}_rp_per_kg"] = biaya_logistik(o["ongkos_angkut_rp_per_kg"], susut, hs, p)
                row["status"] = "ASUMSI"
                rows.append(row)
    out = pd.DataFrame(rows)
    num = out.select_dtypes("number").columns.difference(["kota_sumber_id", "kota_tujuan_id"])
    out[num] = out[num].round(2)
    return out, {"tarif_tol_per_km": tol_km, "tol_detail": tol_detail}


def write_report(b: pd.DataFrame, meta: dict, lcfg: dict, path: Path) -> None:
    def md(d: pd.DataFrame) -> str:
        cols = [str(c) for c in d.columns]
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False)]
        return "\n".join(lines)

    rp = lambda v: f"Rp {v:,.0f}".replace(",", ".")  # noqa: E731
    t = b[["kota_sumber", "kota_tujuan", "kualitas", "jarak_jalan_km", "ongkos_angkut_rp_per_kg", "susut_rp_per_kg",
           "biaya_logistik_x1_rp_per_kg", "biaya_logistik_x1.5_rp_per_kg", "porsi_dari_mpp", "status_mpp"]].copy()
    for c in ("ongkos_angkut_rp_per_kg", "susut_rp_per_kg", "biaya_logistik_x1_rp_per_kg", "biaya_logistik_x1.5_rp_per_kg"):
        t[c] = t[c].map(rp)
    t["porsi_dari_mpp"] = t.porsi_dari_mpp.map(lambda v: "–" if pd.isna(v) else f"{v:.0%}")
    t["jarak_jalan_km"] = t.jarak_jalan_km.map(lambda v: f"{v:,.0f}".replace(",", "."))
    t.columns = ["sumber", "tujuan", "komoditas", "jarak (km)", "ongkos angkut/kg", "susut/kg", "total x1", "total x1,5",
                 "ongkos / MPP", "cek MPP"]
    tol = "; ".join(f"{k}: {rp(v)}/km" for k, v in meta["tol_detail"].items())
    text = f"""# Ongkos angkut per rute — ASUMSI, bukan data

Dibuat otomatis oleh `python -m src.logistics` pada {datetime.now():%Y-%m-%d %H:%M}. Jangan diedit manual.
Semua asumsi & sumbernya: `config/biaya_logistik.yaml`. Jarak jalan: OSRM / OpenStreetMap (`data/reference/jarak_rute.csv`).

## Parameter utama
- Truk CDD box 5.000 kg, tarif **{rp(lcfg['truk']['tarif_per_km'])}/km** (batas bawah tarif pasar Rp 6.000–19.000/km).
- Tol **{rp(meta['tarif_tol_per_km'])}/km** (terbesar dari rute referensi: {tol}), seluruh jarak dianggap lewat tol.
- Muatan efektif: cabai 3.000 kg, bawang 4.500 kg, telur 4.000 kg, daging ayam 3.500 kg (truk berpendingin, tarif +40%).
- Bongkar-muat {rp(lcfg['penanganan']['bongkar_muat_rp_per_kg'])}/kg; susut cabai 5%, bawang merah 3%, telur 2%, ayam 1% dari harga di sumber.
- Harga sumber = median harga pedagang besar 52 minggu terakhir.

## Hasil per rute
{md(t)}

`ongkos / MPP` = ongkos angkut (tanpa susut) dibanding seluruh margin perdagangan & pengangkutan BPS dalam rupiah
(MPP% × harga sumber). `ok` ≤ {lcfg['batas_atas_mpp']['ambang_peringatan']:.0%}, `tinggi` > {lcfg['batas_atas_mpp']['ambang_peringatan']:.0%},
`melebihi` > 100% (asumsi tidak masuk akal).

## Batasan
- Tarif truk & tol berasal dari halaman komersial dan berita, bukan tarif resmi; sebagian bertanggal lama.
- Muatan efektif, premi truk berpendingin, bongkar-muat, dan susut adalah asumsi analis tanpa sumber angka.
- Ketidakpastian ditangani dengan uji sensitivitas ×{', ×'.join(f'{p:g}' for p in lcfg['sensitivitas']['pengali'])};
  rekomendasi rute hanya valid jika tetap untung pada ×{lcfg['sensitivitas']['skenario_konservatif']:g}.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    lcfg = yaml.safe_load((ROOT / "config" / "biaya_logistik.yaml").read_text(encoding="utf-8"))
    b, meta = build(cfg, lcfg)
    b.to_csv(ROOT / cfg["paths"]["reference"] / "biaya_rute.csv", index=False)
    write_report(b, meta, lcfg, ROOT / "docs" / "biaya_logistik_report.md")
    log.info("Selesai: %d rute x komoditas | tol %.0f Rp/km | status MPP: %s", len(b), meta["tarif_tol_per_km"],
             b.status_mpp.value_counts().to_dict())


if __name__ == "__main__":
    main()
