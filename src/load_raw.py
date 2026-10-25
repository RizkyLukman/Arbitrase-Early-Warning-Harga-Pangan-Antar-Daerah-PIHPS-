"""Membaca JSON mentah PIHPS (data/raw/) menjadi tabel panjang, TANPA cleaning.

Dipakai oleh notebook EDA dan oleh src/clean.py (Tahap 2).
Struktur file mentah dijelaskan di docs/data_access.md.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

JENIS_PASAR = {1: "Pasar Tradisional", 2: "Pasar Modern", 3: "Pedagang Besar", 4: "Produsen"}
LEVEL = {0: "nasional", 1: "provinsi", 2: "kota"}
KOSONG = {"-", ""}


@lru_cache(maxsize=None)
def _parse_date(key: str) -> pd.Timestamp:
    return pd.to_datetime(key, format="%d/%m/%Y")


def parse_price(value: str | None) -> float:
    """'58,750' -> 58750.0 (koma = pemisah ribuan). '-' / '' / None -> NaN."""
    if value is None or value.strip() in KOSONG:
        return math.nan
    return float(value.replace(",", ""))


def records_from_payload(payload: dict, jenis_pasar_id: int, komoditas_id: str) -> list[dict]:
    """Ubah satu respons GetGridDataKomoditas (format lebar) menjadi daftar baris panjang.

    Baris kota tidak membawa provinsi; provinsi diambil dari baris level 1 terakhir di atasnya.
    """
    out = []
    provinsi = None
    for row in payload.get("data") or []:
        level = row["level"]
        nama = row["name"].strip()
        if level == 1:
            provinsi = nama
        prov = provinsi if level == 2 else (nama if level == 1 else None)
        for key, val in row.items():
            if "/" not in key:
                continue
            harga = parse_price(val)
            out.append({
                "jenis_pasar_id": jenis_pasar_id, "komoditas_id": komoditas_id, "level": level,
                "provinsi": prov, "nama": nama, "tanggal": _parse_date(key),
                "harga": harga, "kosong": math.isnan(harga),
            })
    return out


def load_raw_long(raw_dir: str | Path) -> pd.DataFrame:
    """Baca semua data/raw/pt*/com_*/*.json -> satu DataFrame panjang."""
    recs = []
    for f in sorted(Path(raw_dir).glob("pt*/com_*/*.json")):
        jenis_pasar_id = int(f.parent.parent.name[2:])
        payload = json.loads(f.read_text(encoding="utf-8"))
        recs.extend(records_from_payload(payload, jenis_pasar_id, f.parent.name))
    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df


def load_regency_ref(raw_dir: str | Path) -> pd.DataFrame:
    """Tabel referensi kota per jenis pasar: jenis_pasar_id, provinsi_id, kota_id, nama."""
    rows = []
    for f in sorted((Path(raw_dir) / "ref").glob("regency_pt*_prov*.json")):
        stem = f.stem  # regency_pt1_prov14
        jenis_pasar_id = int(stem.split("_")[1][2:])
        provinsi_id = int(stem.split("prov")[1])
        for r in json.loads(f.read_text(encoding="utf-8"))["data"]:
            rows.append({"jenis_pasar_id": jenis_pasar_id, "provinsi_id": provinsi_id,
                         "kota_id": r["id"], "nama": r["name"].strip()})
    return pd.DataFrame(rows)


def load_commodity_ref(raw_dir: str | Path) -> pd.DataFrame:
    """Tabel referensi komoditas: komoditas_id, nama, kategori_id, satuan."""
    data = json.loads((Path(raw_dir) / "ref" / "commodity.json").read_text(encoding="utf-8"))["data"]
    df = pd.DataFrame(data).rename(columns={"id": "komoditas_id", "name": "nama", "cat_id": "kategori_id",
                                            "denomination": "satuan"})
    df["nama"] = df["nama"].str.strip()
    df = df[df.komoditas_id.str.startswith("com_")]
    return df[["komoditas_id", "nama", "kategori_id", "satuan"]].reset_index(drop=True)
