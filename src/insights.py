"""Tahap 5 — Kalimat temuan untuk dashboard: "Tiga hal yang perlu diketahui minggu ini" & daftar tindakan per komoditas.

Disusun OTOMATIS dari hasil analisis Tahap 4 untuk minggu terakhir di data (brief §6.4), bukan ditulis tangan.
Setiap kalimat/tindakan menyimpan angka asalnya (nilai, satuan, pembanding, sumber tabel) agar bisa ditelusuri.
Bahasa mengikuti aturan §6.2–§6.3: apa yang terjadi → apa artinya → apa tindakannya; tanpa istilah teknis.

Input : data/interim/harga_mingguan.parquet, data/interim/spread_mingguan.parquet, reports/tables/q*.csv,
        config/config.yaml (bagian `insights`, `wilayah`, `analisis`), config/biaya_logistik.yaml (skenario konservatif)
Output: dipakai src/export_dashboard.py -> data/processed/fact_tindakan & fact_hal. Bisa dijalankan sendiri untuk melihat hasilnya:
        python -m src.insights
"""
from __future__ import annotations

import argparse
import math

import numpy as np
import pandas as pd

from src.analysis.common import KOMODITAS_URUT, LABEL_PENDEK, ROOT, TABLES, load_cfg, load_weekly, pct, rp


def _ada(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _dari10(v: float) -> str:
    return f"{v * 10:.1f}".replace(".", ",")


# ---------------------------------------------------------------- aturan tindakan (fungsi murni, diuji)
def susun_tindakan(k: dict, icfg: dict) -> list[dict]:
    """Daftar tindakan untuk satu komoditas minggu ini, berurutan prioritas (1 = paling penting).

    k (konteks) berisi: nama, minggu_ke_idul_fitri, mulai_naik_minggu, kenaikan_minggu_min1_rata, rute_terbaik,
    harga, pct_4w, selisih_nasional_pct, peringkat_gejolak, rata_perubahan_abs, hemat_produsen_pct,
    hemat_pedagang_besar_pct, n_kota_peringatan, kota_peringatan, ketepatan_peringatan.
    """
    nama = k["nama"]
    rows: list[dict] = []

    def tambah(prio, tindakan, alasan, nilai, satuan, pembanding, sumber, **flags):
        rows.append({"prioritas": prio, "tindakan": tindakan, "alasan_singkat": alasan, "nilai": nilai, "satuan": satuan,
                     "pembanding": pembanding, "sumber": sumber, "beli_lebih_awal": False, "pindah_stok": False,
                     "rute_key": None, **flags})

    # 1) Masa menjelang Idulfitri (Q4): di dalam jendela kenaikan, atau jendela dimulai <= N minggu lagi
    mk, mulai = k.get("minggu_ke_idul_fitri"), k.get("mulai_naik_minggu")
    if _ada(mk) and _ada(mulai):
        mk, mulai = int(mk), int(mulai)
        naik = k.get("kenaikan_minggu_min1_rata")
        naik_txt = f"; seminggu sebelum Lebaran biasanya {pct(naik)} di atas harga normal" if _ada(naik) else ""
        if mulai <= mk <= -1:
            tambah(1, "Amankan stok sebelum Idulfitri",
                   f"{nama}: Idulfitri {abs(mk)} minggu lagi, harga biasanya sudah mulai naik sejak {abs(mulai)} minggu "
                   f"sebelumnya{naik_txt}", naik, "kenaikan vs harga normal", "harga normal (minggu -12 s/d -9)",
                   "q4_ringkasan", beli_lebih_awal=True)
        elif mulai - icfg["minggu_sebelum_jendela"] <= mk < mulai:
            tambah(1, "Beli lebih awal sebelum harga naik",
                   f"{nama}: kenaikan menjelang Idulfitri biasanya mulai {abs(mulai)} minggu sebelum Lebaran, "
                   f"yaitu {mulai - mk} minggu lagi{naik_txt}", naik, "kenaikan vs harga normal",
                   "harga normal (minggu -12 s/d -9)", "q4_ringkasan", beli_lebih_awal=True)

    # 2) Rute pindah stok yang untung minggu ini (Q2)
    r = k.get("rute_terbaik")
    if r and _ada(r.get("untung_rp")) and r["untung_rp"] > 0:
        bert = f", sudah {r['berturut']} minggu berturut-turut" if r.get("berturut", 0) >= 2 else ""
        catatan = "; untung hanya jika dijual dengan harga eceran" if r.get("aman") is False else ""
        tambah(2, f"Pindahkan stok {r['kota_sumber']} → {r['kota_tujuan']}",
               f"{nama}: untung {rp(r['untung_rp'])}/kg setelah dikurangi ongkos kirim ×1,5 (perkiraan kami){bert}{catatan}",
               r["untung_rp"], "Rp/kg", "ongkos kirim ×1,5 (perkiraan kami)", "fact_spread", pindah_stok=True,
               rute_key=r.get("rute_key"))

    # 3) Harga di kota tujuan bergerak cepat vs 4 minggu lalu
    p4 = k.get("pct_4w")
    if _ada(p4):
        if p4 >= icfg["ambang_naik_4_minggu"]:
            tambah(3, "Pantau ketat, harga sedang naik cepat",
                   f"{nama} di kota tujuan {rp(k['harga'])}/kg, naik {pct(p4)} dibanding 4 minggu lalu; beli secukupnya",
                   p4, "perubahan vs 4 minggu lalu", "4 minggu lalu", "fact_harga_mingguan")
        elif p4 <= icfg["ambang_turun_4_minggu"]:
            tambah(3, "Harga sedang turun, pertimbangkan menambah stok",
                   f"{nama} di kota tujuan {rp(k['harga'])}/kg, turun {pct(-p4)} dibanding 4 minggu lalu; "
                   f"tambah stok hanya jika bisa disimpan", p4, "perubahan vs 4 minggu lalu", "4 minggu lalu",
                   "fact_harga_mingguan")

    # 4) Beli langsung di produsen (Q5)
    hp = k.get("hemat_produsen_pct")
    if _ada(hp) and hp >= icfg["min_hemat_produsen"]:
        hpb = k.get("hemat_pedagang_besar_pct")
        banding = f" ({pct(hpb)} dibanding pedagang besar)" if _ada(hpb) else ""
        tambah(4, "Jajaki beli langsung di produsen",
               f"{nama}: {pct(hp)} lebih murah daripada harga pasar{banding}; harga produsen jarang diperbarui, "
               f"jadi angka ini perkiraan kasar", hp, "lebih murah vs harga pasar", "harga pasar tradisional", "q5_per_komoditas")

    # 5) Peringatan dini aktif (Q6) — informasi saja, aturan belum terbukti akurat
    n = k.get("n_kota_peringatan", 0) or 0
    if n > 0:
        kt = k.get("ketepatan_peringatan")
        akurasi = f"; dalam uji data lama peringatan ini benar {_dari10(kt)} dari 10 kali" if _ada(kt) else ""
        tambah(5, f"Informasi: peringatan dini aktif di {n} kota",
               f"{nama}: harga naik jauh di atas kebiasaan di {k.get('kota_peringatan', '')}{akurasi}; cek harga, "
               f"jangan otomatis membeli", n, "kota", "kebiasaan 52 minggu sebelumnya", "fact_alert")

    # 6) Komoditas paling bergejolak (Q1)
    pr = k.get("peringkat_gejolak")
    if _ada(pr) and pr <= icfg["top_n_gejolak"]:
        tambah(6, "Pantau setiap minggu",
               f"{nama}: komoditas paling tidak stabil ke-{int(pr)}, harganya berubah rata-rata "
               f"{pct(k['rata_perubahan_abs'])} per minggu; siapkan stok penyangga", k["rata_perubahan_abs"],
               "rata-rata perubahan per minggu", "komoditas lain", "q1_gejolak_per_komoditas")

    if not rows:
        sn = k.get("selisih_nasional_pct")
        if _ada(sn):
            arah = "di atas" if sn >= 0 else "di bawah"
            vs = f", {pct(abs(sn))} {arah} rata-rata nasional"
        else:
            vs = ", rata-rata nasional tidak tersedia"
        tambah(7, "Beli rutin", f"{nama}: tidak ada sinyal khusus minggu ini; harga di kota tujuan {rp(k['harga'])}/kg{vs}",
               sn, "selisih vs nasional", "rata-rata nasional", "fact_harga_mingguan")
    return sorted(rows, key=lambda x: x["prioritas"])


def pilih_hal(kandidat: list[dict], n: int, maks_per_jenis: int = 2) -> list[dict]:
    """Pilih n kalimat: prioritas terkecil dulu, lalu skor terbesar. Komoditas berbeda diutamakan, dan satu jenis
    kalimat (mis. rute) maksimal `maks_per_jenis` agar tiga kalimat tidak seragam; sisanya diisi urutan berikutnya."""
    urut = sorted(kandidat, key=lambda x: (x["prioritas"], -x.get("skor", 0)))
    pilih, dipakai, per_jenis = [], set(), {}
    for x in urut:
        j = x.get("jenis")
        if (x.get("komoditas_key"), j) in dipakai or (j is not None and per_jenis.get(j, 0) >= maks_per_jenis):
            continue
        pilih.append(x)
        dipakai.add((x.get("komoditas_key"), j))
        per_jenis[j] = per_jenis.get(j, 0) + 1
        if len(pilih) == n:
            break
    for x in urut:
        if len(pilih) == n:
            break
        if x not in pilih:
            pilih.append(x)
    return [{**x, "urutan": i + 1} for i, x in enumerate(pilih)]


# ---------------------------------------------------------------- konteks dari hasil analisis
def _kalimat_hal(k: dict, rows: list[dict], icfg: dict) -> list[dict]:
    """Kandidat kalimat "hal yang perlu diketahui" untuk satu komoditas (apa → artinya → tindakan)."""
    nama, out = k["nama"], []
    harga = k.get("harga")
    for r in rows:
        if r["beli_lebih_awal"]:
            mk = int(k["minggu_ke_idul_fitri"])
            naik = k.get("kenaikan_minggu_min1_rata")
            naik_txt = f" dan seminggu sebelum Lebaran rata-rata {pct(naik)} di atas harga normal" if _ada(naik) else ""
            out.append({"jenis": "idulfitri", "prioritas": 1, "skor": -mk, "kalimat":
                        f"Idulfitri {abs(mk)} minggu lagi. Harga {nama} biasanya mulai naik {abs(int(k['mulai_naik_minggu']))} "
                        f"minggu sebelumnya{naik_txt}. Tindakan: amankan stok {nama} sekarang, sebelum kenaikan dimulai.",
                        "nilai": r["nilai"], "satuan": r["satuan"], "pembanding": r["pembanding"], "sumber": r["sumber"]})
        elif r["pindah_stok"]:
            rt = k["rute_terbaik"]
            bert = f", sudah {rt['berturut']} minggu berturut-turut" if rt.get("berturut", 0) >= 2 else ""
            out.append({"jenis": "rute", "prioritas": 2, "skor": rt["untung_rp"] / harga if _ada(harga) and harga else 0, "kalimat":
                        f"{nama[0].upper() + nama[1:]} di {rt['kota_sumber']} masih {rp(rt['untung_rp'])}/kg lebih murah daripada di "
                        f"{rt['kota_tujuan']} setelah dikurangi ongkos kirim ×1,5 (perkiraan kami){bert}. Tindakan: pertimbangkan memindahkan "
                        f"stok selama selisih ini bertahan.", "nilai": r["nilai"], "satuan": r["satuan"],
                        "pembanding": r["pembanding"], "sumber": r["sumber"]})
        elif r["prioritas"] == 3:
            p4, sn = k["pct_4w"], k.get("selisih_nasional_pct")
            vs = ""
            if _ada(sn) and abs(sn) >= icfg["ambang_selisih_nasional"]:
                vs = f" dan {pct(abs(sn))} {'di atas' if sn > 0 else 'di bawah'} rata-rata nasional"
            if p4 > 0:
                kal = (f"Harga {nama} di kota tujuan {rp(harga)}/kg, naik {pct(p4)} dibanding 4 minggu lalu{vs}. "
                       f"Artinya pasokan sedang ketat. Tindakan: beli secukupnya dan pantau setiap minggu.")
            else:
                kal = (f"Harga {nama} di kota tujuan {rp(harga)}/kg, turun {pct(-p4)} dibanding 4 minggu lalu{vs}. "
                       f"Artinya harga sedang murah. Tindakan: tambah stok hanya jika bisa disimpan.")
            out.append({"jenis": "harga_bergerak", "prioritas": 2, "skor": abs(p4), "kalimat": kal, "nilai": r["nilai"], "satuan": r["satuan"],
                        "pembanding": r["pembanding"], "sumber": r["sumber"]})
        elif r["prioritas"] == 5:
            kt = k.get("ketepatan_peringatan")
            akurasi = f" dalam uji data lama, peringatan ini benar hanya {_dari10(kt)} dari 10 kali." if _ada(kt) else ""
            out.append({"jenis": "peringatan", "prioritas": 3, "skor": k["n_kota_peringatan"], "kalimat":
                        f"Peringatan dini aktif untuk {nama} di {k['n_kota_peringatan']} kota ({k['kota_peringatan']}). "
                        f"Ini hanya informasi:{akurasi} Tindakan: cek harga di kota itu, jangan otomatis membeli.",
                        "nilai": r["nilai"], "satuan": r["satuan"], "pembanding": r["pembanding"], "sumber": r["sumber"]})
        elif r["prioritas"] == 4:
            out.append({"jenis": "produsen", "prioritas": 4, "skor": k["hemat_produsen_pct"], "kalimat":
                        f"Membeli {nama} langsung di produsen {pct(k['hemat_produsen_pct'])} lebih murah daripada harga pasar"
                        + (f" ({pct(k['hemat_pedagang_besar_pct'])} dibanding pedagang besar)" if _ada(k.get("hemat_pedagang_besar_pct")) else "")
                        + ". Angka ini perkiraan kasar karena harga produsen jarang diperbarui. Tindakan: jajaki pembelian "
                        "langsung di sentra produksi.", "nilai": r["nilai"], "satuan": r["satuan"],
                        "pembanding": r["pembanding"], "sumber": r["sumber"]})
        elif r["prioritas"] == 6:
            tenang = k.get("komoditas_paling_tenang")
            vs = f", dibanding {pct(tenang['rata_perubahan_abs'])} untuk {tenang['nama']}" if tenang else ""
            out.append({"jenis": "gejolak", "prioritas": 4, "skor": k["rata_perubahan_abs"], "kalimat":
                        f"{nama[0].upper() + nama[1:]} tetap komoditas paling tidak stabil ke-{int(k['peringkat_gejolak'])}: harganya "
                        f"berubah rata-rata {pct(k['rata_perubahan_abs'])} per minggu{vs}. Tindakan: pantau setiap minggu dan "
                        f"siapkan stok penyangga.", "nilai": r["nilai"], "satuan": r["satuan"], "pembanding": r["pembanding"],
                        "sumber": r["sumber"]})
    return out


def _tabel(nama: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / f"{nama}.csv")


def konteks_minggu_ini(cfg: dict, lcfg: dict) -> tuple[pd.Timestamp, dict[str, dict]]:
    """Konteks per komoditas (kunci = kualitas) untuk minggu terakhir di data."""
    icfg, kons = cfg["insights"], lcfg["sensitivitas"]["skenario_konservatif"]
    w = load_weekly(cfg)
    akhir = w.minggu_akhir.max()
    tujuan_ids = list(cfg["wilayah"]["kota_tujuan"])
    t = w[(w.jenis_pasar_id == icfg["jenis_pasar_id"]) & (w.minggu_akhir == akhir)]
    tj = t[t.kota_id.isin(tujuan_ids)]
    q1, q4, q5 = _tabel("q1_gejolak_per_komoditas").set_index("kualitas"), _tabel("q4_ringkasan").set_index("kualitas"), \
        _tabel("q5_per_komoditas").set_index("kualitas")
    q2 = _tabel("q2_rute_ringkasan")
    q2 = q2[(q2.pengali == kons) & (q2.tujuan_jenis_pasar_id == cfg["analisis"]["q2_rute"]["harga_tujuan_jenis_pasar_id"])]
    sp = pd.read_parquet(ROOT / cfg["paths"]["interim"] / "spread_mingguan.parquet")
    sp = sp[(sp.minggu_akhir == akhir) & (sp.tujuan_jenis_pasar_id == cfg["analisis"]["q2_rute"]["harga_tujuan_jenis_pasar_id"])]
    q6s = _tabel("q6_skor_ringkas").set_index("aturan")
    ketepatan = float(q6s.loc["A atau B (aturan brief)", "ketepatan"])
    q6c = _tabel("q6_peringatan_terkini", )
    q6c["minggu_akhir"] = pd.to_datetime(q6c.minggu_akhir)
    q6c = q6c[(q6c.minggu_akhir == akhir) & q6c.peringatan]
    tenang = q1.sort_values("peringkat").iloc[-1]
    paling_tenang = {"nama": LABEL_PENDEK[tenang.name].lower(), "rata_perubahan_abs": float(tenang.rata_perubahan_abs_median)}

    out = {}
    for kom in KOMODITAS_URUT:
        d = tj[tj.kualitas == kom]
        mk = t[t.kualitas == kom].minggu_ke_idul_fitri.dropna()
        rute = None
        r = q2[(q2.kualitas == kom) & q2.layak_konservatif]
        if len(r):
            s = sp[sp.kualitas == kom][["kota_sumber_id", "kota_tujuan_id", f"spread_bersih_x{kons:g}"]]
            r = r.merge(s, on=["kota_sumber_id", "kota_tujuan_id"], how="inner")
            r = r[r[f"spread_bersih_x{kons:g}"] > 0].sort_values(["layak_jika_jual_ke_pedagang_besar", f"spread_bersih_x{kons:g}"],
                                                                 ascending=False)
            if len(r):
                x = r.iloc[0]
                rute = {"kota_sumber": x.kota_sumber, "kota_tujuan": x.kota_tujuan, "untung_rp": float(x[f"spread_bersih_x{kons:g}"]),
                        "berturut": int(x.minggu_untung_berturut_terakhir), "porsi_untung": float(x.porsi_minggu_untung),
                        "aman": bool(x.layak_jika_jual_ke_pedagang_besar),
                        "kota_sumber_id": int(x.kota_sumber_id), "kota_tujuan_id": int(x.kota_tujuan_id), "komoditas_id": x.komoditas_id}
        al = q6c[q6c.kualitas == kom]
        out[kom] = {
            "nama": LABEL_PENDEK[kom].lower(), "komoditas_id": d.komoditas_id.iloc[0] if len(d) else None,
            "minggu_ke_idul_fitri": int(mk.iloc[0]) if len(mk) else None,
            "mulai_naik_minggu": None if pd.isna(q4.loc[kom, "mulai_naik_minggu"]) else int(q4.loc[kom, "mulai_naik_minggu"]),
            "kenaikan_minggu_min1_rata": float(q4.loc[kom, "kenaikan_minggu_min1_rata"]),
            "rute_terbaik": rute,
            "harga": float(d.harga.median()) if len(d) else np.nan,
            "pct_4w": float(d.pct_4w.median()) if len(d) else np.nan,
            "selisih_nasional_pct": float(d.selisih_nasional_pct.median()) if len(d) else np.nan,
            "peringkat_gejolak": int(q1.loc[kom, "peringkat"]), "rata_perubahan_abs": float(q1.loc[kom, "rata_perubahan_abs_median"]),
            "komoditas_paling_tenang": paling_tenang,
            "hemat_produsen_pct": float(q5.loc[kom, "hemat_beli_produsen_pct"]) if kom in q5.index else np.nan,
            "hemat_pedagang_besar_pct": float(q5.loc[kom, "hemat_beli_pedagang_besar_pct"]) if kom in q5.index else np.nan,
            "n_kota_peringatan": int(len(al)), "kota_peringatan": ", ".join(sorted(al.kota)), "ketepatan_peringatan": ketepatan,
        }
    return akhir, out


def build(cfg: dict, lcfg: dict) -> dict[str, pd.DataFrame]:
    """tindakan: satu baris per komoditas x tindakan; hal: n kalimat terpilih. Kolom kunci: minggu_akhir, komoditas_id."""
    icfg = cfg["insights"]
    akhir, ctx = konteks_minggu_ini(cfg, lcfg)
    tindakan, kandidat = [], []
    for kom, k in ctx.items():
        rows = susun_tindakan(k, icfg)
        for r in rows:
            rt = k["rute_terbaik"] if r["pindah_stok"] else None
            tindakan.append({"minggu_akhir": akhir, "komoditas_id": k["komoditas_id"], "kualitas": kom, **r,
                             "kota_sumber_id": rt["kota_sumber_id"] if rt else None,
                             "kota_tujuan_id": rt["kota_tujuan_id"] if rt else None})
        for h in _kalimat_hal(k, rows, icfg):
            kandidat.append({**h, "komoditas_key": k["komoditas_id"], "kualitas": kom})
    hal = pilih_hal(kandidat, icfg["jumlah_hal"])
    hal_df = pd.DataFrame([{"minggu_akhir": akhir, "urutan": h["urutan"], "komoditas_id": h["komoditas_key"], "kualitas": h["kualitas"],
                            "kalimat": h["kalimat"], "nilai": h["nilai"], "satuan": h["satuan"], "pembanding": h["pembanding"],
                            "sumber": h["sumber"]} for h in hal])
    t_df = pd.DataFrame(tindakan).drop(columns=["rute_key"])
    return {"tindakan": t_df, "hal": hal_df}


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    cfg, lcfg = load_cfg()
    out = build(cfg, lcfg)
    pd.set_option("display.width", 200, "display.max_colwidth", 160)
    print(f"Minggu: {out['tindakan'].minggu_akhir.iloc[0]:%Y-%m-%d}\n")
    print("== Hal yang perlu diketahui")
    for h in out["hal"].itertuples():
        print(f"{h.urutan}. {h.kalimat}")
    print("\n== Daftar tindakan per komoditas")
    print(out["tindakan"][["kualitas", "prioritas", "tindakan", "alasan_singkat"]].to_string(index=False))


if __name__ == "__main__":
    main()
