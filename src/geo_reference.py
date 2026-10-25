"""Referensi geografis: koordinat kota (untuk peta Power BI) & jarak jalan antar kota (untuk ongkos angkut).

Sumber:
    Koordinat : OpenStreetMap Nominatim (https://nominatim.openstreetmap.org), titik pusat wilayah administratif.
    Jarak     : OSRM demo server (https://router.project-osrm.org), rute mobil tercepat di jaringan jalan OSM.
Etika akses: User-Agent jelas, jeda >= 1,1 detik (kebijakan Nominatim maks 1 permintaan/detik), hasil di-cache.

Output:
    data/reference/kota_koordinat.csv  kota_id, kota, provinsi, lat, lon, sumber, osm_display_name, ...
    data/reference/jarak_rute.csv      kota_sumber_id, kota_tujuan_id, jarak_jalan_km, durasi_jam, sumber
    data/reference/titik_tol.csv       titik bantu untuk menghitung tarif tol per km
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "reference"
CACHE = ROOT / "data" / "raw" / "geo_cache.json"   # data/raw tidak di-commit
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
JAWA = {"lat": (-9.0, -5.5), "lon": (105.0, 115.0)}

log = logging.getLogger("geo")


# Kabupaten yang titik pusat wilayahnya tidak mewakili daratan utama -> pakai ibu kota kabupaten.
QUERY_OVERRIDE = {
    "Kab. Gresik": "Gresik, Kabupaten Gresik, Jawa Timur, Indonesia",  # pusat wilayah jatuh dekat Pulau Bawean
}


def query_name(kota: str, provinsi: str) -> str:
    """Nama PIHPS -> kueri Nominatim. 'Kab. Kediri' -> 'Kabupaten Kediri, Jawa Timur, Indonesia'."""
    if kota in QUERY_OVERRIDE:
        return QUERY_OVERRIDE[kota]
    k = kota.replace(" (Solo)", "")
    if k.startswith("Kab. "):
        k = "Kabupaten " + k[5:]
    if k == "Kota Jakarta Pusat":
        k = "Jakarta Pusat"
    return f"{k}, {provinsi}, Indonesia"


class Client:
    def __init__(self, user_agent: str):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = user_agent
        self.cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        self._last = 0.0

    def _get(self, url: str, params: dict | None = None) -> dict:
        key = url + json.dumps(params or {}, sort_keys=True)
        if key in self.cache:
            return self.cache[key]
        wait = 1.1 - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        r = self.s.get(url, params=params, timeout=60)
        self._last = time.monotonic()
        r.raise_for_status()
        self.cache[key] = r.json()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(self.cache), encoding="utf-8")
        return self.cache[key]

    def geocode(self, q: str) -> dict | None:
        res = self._get(NOMINATIM, {"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "id"})
        return res[0] if res else None

    def route(self, a: tuple[float, float], b: tuple[float, float]) -> dict:
        url = OSRM.format(lat1=a[0], lon1=a[1], lat2=b[0], lon2=b[1])
        res = self._get(url, {"overview": "false"})
        if res.get("code") != "Ok":
            raise RuntimeError(f"OSRM gagal: {res.get('code')}")
        return res["routes"][0]


def build(cfg: dict) -> None:
    c = Client(cfg["sumber"]["user_agent"] + " (geo reference)")
    harian = pd.read_parquet(ROOT / cfg["paths"]["interim"] / "harga_harian.parquet",
                             columns=["kota_id", "kota", "provinsi"]).drop_duplicates().sort_values("kota_id")
    rows = []
    for r in harian.itertuples():
        q = query_name(r.kota, r.provinsi)
        g = c.geocode(q)
        if g is None:
            raise RuntimeError(f"Koordinat tidak ditemukan: {q}")
        lat, lon = float(g["lat"]), float(g["lon"])
        ok = JAWA["lat"][0] <= lat <= JAWA["lat"][1] and JAWA["lon"][0] <= lon <= JAWA["lon"][1]
        rows.append({"kota_id": r.kota_id, "kota": r.kota, "provinsi": r.provinsi, "lat": round(lat, 5),
                     "lon": round(lon, 5), "kueri": q, "osm_display_name": g.get("display_name"),
                     "osm_type": g.get("osm_type"), "osm_id": g.get("osm_id"), "osm_category": g.get("category"),
                     "osm_addresstype": g.get("addresstype"), "di_pulau_jawa": ok,
                     "sumber": "OpenStreetMap Nominatim", "tanggal_ambil": date.today().isoformat()})
        log.info("%-25s %9.4f %9.4f %s", r.kota, lat, lon, "" if ok else "<-- DI LUAR JAWA?")
    koord = pd.DataFrame(rows)
    REF.mkdir(parents=True, exist_ok=True)
    koord.to_csv(REF / "kota_koordinat.csv", index=False)

    pos = koord.set_index("kota_id")[["lat", "lon"]]
    w = cfg["wilayah"]
    jarak = []
    for sid in w["kota_sumber"]:
        for tid in w["kota_tujuan"]:
            rt = c.route(tuple(pos.loc[sid]), tuple(pos.loc[tid]))
            jarak.append({"kota_sumber_id": sid, "kota_tujuan_id": tid,
                          "jarak_jalan_km": round(rt["distance"] / 1000, 1), "durasi_jam": round(rt["duration"] / 3600, 2),
                          "sumber": "OSRM (router.project-osrm.org), data jalan OpenStreetMap",
                          "tanggal_ambil": date.today().isoformat()})
    pd.DataFrame(jarak).to_csv(REF / "jarak_rute.csv", index=False)

    # Titik bantu tarif tol: gerbang tol dari sumber tarif (lihat config/biaya_logistik.yaml)
    titik = []
    for nama, q in cfg_logistik()["tol"]["titik_referensi"].items():
        g = c.geocode(q)
        if g is None:
            raise RuntimeError(f"Titik tol tidak ditemukan: {q}")
        titik.append({"titik": nama, "kueri": q, "lat": float(g["lat"]), "lon": float(g["lon"]),
                      "osm_display_name": g.get("display_name")})
    titik = pd.DataFrame(titik)
    tr = cfg_logistik()["tol"]["rute_referensi"]
    hasil = []
    for nama, ref in tr.items():
        a = titik.set_index("titik").loc[ref["dari"], ["lat", "lon"]]
        b = titik.set_index("titik").loc[ref["ke"], ["lat", "lon"]]
        rt = c.route(tuple(a), tuple(b))
        hasil.append({"rute_tol": nama, "jarak_jalan_km": round(rt["distance"] / 1000, 1)})
    titik.to_csv(REF / "titik_tol.csv", index=False)
    pd.DataFrame(hasil).to_csv(REF / "jarak_tol_referensi.csv", index=False)
    log.info("Selesai: %d kota, %d rute, %d rute tol referensi", len(koord), len(jarak), len(hasil))


def cfg_logistik() -> dict:
    return yaml.safe_load((ROOT / "config" / "biaya_logistik.yaml").read_text(encoding="utf-8"))


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    build(yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
