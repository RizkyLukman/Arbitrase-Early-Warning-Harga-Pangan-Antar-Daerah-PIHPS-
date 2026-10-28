"""Peta latar Pulau Jawa untuk dashboard Excel (gelembung gejolak ditumpuk di atas gambar peta).

1. `python -m src.peta_jawa` : unduh batas provinsi Natural Earth 1:10m (domain publik, naturalearthdata.com) sekali ke
   data/raw/geo/, ambil provinsi di Pulau Jawa + tetangga yang masuk bingkai peta, simpan ke data/reference/peta_jawa.geojson.
2. `gambar_peta(path, lebar_px, tinggi_px)` : gambar PNG peta dengan bingkai bujur/lintang BINGKAI (dipakai src/build_excel_desain.py).
   Grafik gelembung di Excel memakai skala sumbu yang sama persis dengan BINGKAI agar titik kota jatuh di tempatnya.

Proyeksi: bujur/lintang biasa (equirectangular). Di lintang 6-9 derajat S distorsinya < 1%, cukup untuk peta ilustrasi.
"""
from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import requests

from src.analysis.common import ROOT

URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
RAW = ROOT / "data" / "raw" / "geo"
GEOJSON = ROOT / "data" / "reference" / "peta_jawa.geojson"
BINGKAI = (105.0, 114.8, -8.95, -5.75)   # bujur min, bujur maks, lintang min, lintang maks
JAWA = {"ID-BT", "ID-JK", "ID-JB", "ID-JT", "ID-YO", "ID-JI"}
TETANGGA = {"ID-LA", "ID-BA", "ID-SS"}   # digambar lebih pucat sebagai konteks


def unduh() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    z = RAW / Path(URL).name
    if not z.exists():
        r = requests.get(URL, timeout=120, headers={"User-Agent": "PIHPS-portfolio-map/1.0"})
        r.raise_for_status()
        z.write_bytes(r.content)
        time.sleep(1)
    with zipfile.ZipFile(z) as f:
        f.extractall(RAW)
    return RAW / "ne_10m_admin_1_states_provinces.shp"


def _cincin(shape) -> list[list[list[float]]]:
    """Pisahkan poligon pyshp ke daftar cincin, koordinat dibulatkan 3 desimal (~100 m)."""
    idx = list(shape.parts) + [len(shape.points)]
    out = []
    for a, b in zip(idx[:-1], idx[1:]):
        ring = [[round(x, 3), round(y, 3)] for x, y in shape.points[a:b]]
        ring = [p for i, p in enumerate(ring) if i == 0 or p != ring[i - 1]]
        if len(ring) >= 4:
            out.append(ring)
    return out


def buat_geojson() -> Path:
    import shapefile  # pyshp

    shp = unduh()
    fitur = []
    for sr in shapefile.Reader(str(shp), encoding="utf-8").iterShapeRecords():
        d = sr.record.as_dict()
        if d["iso_3166_2"] not in JAWA | TETANGGA:
            continue
        fitur.append({"type": "Feature",
                      "properties": {"provinsi": d["name"], "kode": d["iso_3166_2"], "jawa": d["iso_3166_2"] in JAWA},
                      "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in _cincin(sr.shape)]}})
    gj = {"type": "FeatureCollection", "sumber": "Natural Earth 1:10m Admin 1 (domain publik), " + URL,
          "catatan": "dibuat oleh python -m src.peta_jawa; hanya untuk gambar latar dashboard", "features": fitur}
    GEOJSON.write_text(json.dumps(gj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return GEOJSON


def gambar_peta(path: Path, lebar_px: int, tinggi_px: int, laut: str = "#FFFFFF", darat: str = "#E3EAE7",
                darat_tetangga: str = "#F0F3F2", garis: str = "#FFFFFF") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    dpi = 100
    fig = plt.figure(figsize=(lebar_px / dpi, tinggi_px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(laut)
    fig.patch.set_facecolor(laut)
    for f in gj["features"]:
        warna = darat if f["properties"]["jawa"] else darat_tetangga
        for poly in f["geometry"]["coordinates"]:
            ax.add_patch(Polygon(poly[0], closed=True, facecolor=warna, edgecolor=garis, linewidth=0.8))
    ax.set_xlim(BINGKAI[0], BINGKAI[1])
    ax.set_ylim(BINGKAI[2], BINGKAI[3])
    ax.axis("off")
    fig.savefig(path, dpi=dpi, facecolor=laut)
    plt.close(fig)
    return path


if __name__ == "__main__":
    p = buat_geojson()
    print(f"{p} ({p.stat().st_size / 1e3:.0f} KB)")
