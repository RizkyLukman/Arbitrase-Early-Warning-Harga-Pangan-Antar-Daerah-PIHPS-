"""Tes src/export_powerbi.py: kunci, dim_tanggal, pemeriksaan integritas, dan (jika ada) hasil export di data/processed/."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.export_powerbi import FAKTA_KUNCI, build_dim_tanggal, check_integrity, komoditas_key, tanggal_key

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def test_tanggal_key_is_yyyymmdd_int():
    s = pd.Series(pd.to_datetime(["2026-10-23", "2023-07-03"]))
    assert tanggal_key(s).tolist() == [20261023, 20230703]


def test_komoditas_key_strips_prefix():
    assert komoditas_key("com_16") == 16 and komoditas_key("com_7") == 7


def test_dim_tanggal_covers_every_calendar_day_with_friday_week_key():
    kal = pd.DataFrame({"minggu_akhir": pd.to_datetime(["2024-04-05", "2024-04-12"]),
                        "minggu_ke_idul_fitri": pd.array([-1, 0], dtype="Int64"),
                        "tahun_idul_fitri": pd.array([2024, 2024], dtype="Int64"),
                        "ada_libur_hari_besar": [False, True], "nama_hari_besar": ["", "Idulfitri 1445 H"]})
    hb = pd.DataFrame({"tanggal": pd.to_datetime(["2024-04-10"]), "jenis": ["idul_fitri"], "nama": ["Idulfitri 1445 H"],
                       "libur_mulai": pd.to_datetime(["2024-04-08"]), "libur_selesai": pd.to_datetime(["2024-04-15"])})
    d = build_dim_tanggal(pd.Timestamp("2024-04-01"), pd.Timestamp("2024-04-12"), kal, hb)
    assert len(d) == 12 and d.tanggal_key.is_unique
    assert d.loc[d.tanggal == "2024-04-06", "is_hari_kerja"].item() is False       # Sabtu
    assert d.loc[d.tanggal == "2024-04-08", "minggu_key"].item() == 20240412     # Senin -> Jumat minggu itu
    assert d.loc[d.tanggal == "2024-04-10", "minggu_ke_idul_fitri"].item() == 0
    assert d.loc[d.tanggal == "2024-04-10", "is_libur_hari_besar"].item() and d.loc[d.tanggal == "2024-04-10", "nama_hari_besar"].item()
    assert not d.loc[d.tanggal == "2024-04-02", "is_libur_hari_besar"].item()


def test_check_integrity_reports_orphan_and_duplicate_keys():
    t = {"dim_kota": pd.DataFrame({"kota_key": [1, 1]}),
         "dim_komoditas": pd.DataFrame({"komoditas_key": [16]}),
         "fact_x": pd.DataFrame({"kota_key": [1, 2], "komoditas_key": [16, 16]})}
    masalah = check_integrity(t, {"fact_x": {"kota_key": "dim_kota", "komoditas_key": "dim_komoditas"}})
    assert any("dim_kota" in m and "unik" in m for m in masalah)
    assert any("fact_x" in m and "kota_key" in m for m in masalah)
    assert check_integrity({"dim_kota": pd.DataFrame({"kota_key": [1]}),
                            "fact_x": pd.DataFrame({"kota_key": [1]})}, {"fact_x": {"kota_key": "dim_kota"}}) == []


# ---------------------------------------------------------------- hasil export (dilewati jika belum ada)
@pytest.fixture(scope="module")
def tabel():
    if not (PROCESSED / "fact_harga.parquet").exists():
        pytest.skip("data/processed/ belum dibuat (python -m src.export_powerbi)")
    return {p.stem: pd.read_parquet(p) for p in PROCESSED.glob("*.parquet")}


def test_exported_tables_exist(tabel):
    wajib = {"fact_harga", "fact_harga_mingguan", "fact_spread", "fact_alert", "fact_tindakan", "fact_hal",
             "dim_tanggal", "dim_kota", "dim_komoditas", "dim_jenis_pasar", "dim_rute"}
    assert wajib <= set(tabel)


def test_exported_keys_are_consistent(tabel):
    assert check_integrity(tabel, FAKTA_KUNCI) == []


def test_fact_harga_matches_interim(tabel):
    h = pd.read_parquet(ROOT / "data" / "interim" / "harga_harian.parquet")
    f = tabel["fact_harga"]
    assert not f.duplicated(["tanggal_key", "kota_key", "komoditas_key", "jenis_pasar_key"]).any()
    assert (f.harga.dropna() > 0).all()
    assert f[f.harga.isna()].is_outlier_flag.all()        # harga kosong hanya pada salah input yang dikosongkan
    x = h[(h.kota_id == 34) & (h.komoditas_id == "com_16") & (h.jenis_pasar_id == 1)].set_index("tanggal").harga_bersih.dropna()
    y = f[(f.kota_key == 34) & (f.komoditas_key == 16) & (f.jenis_pasar_key == 1)].set_index("tanggal_key").harga.dropna()
    assert len(x) == len(y) and (x.to_numpy() == y.sort_index().to_numpy()).all()


def test_fact_spread_components_reproduce_net_profit(tabel):
    s = tabel["fact_spread"]
    untung = s.selisih_harga - (s.ongkos_angkut + s.susut_rp) * 1.5
    assert (untung - s.untung_per_kg_x1_5).abs().max() < 1e-6


def test_dashboard_text_columns_have_no_technical_terms(tabel):
    teks = pd.concat([tabel["fact_tindakan"].alasan_singkat, tabel["fact_tindakan"].tindakan, tabel["fact_hal"].kalimat,
                      tabel["fact_alert"].alasan.dropna()]).str.lower()
    for kata in ["spread", "z-score", "zscore", "granger", "lag ", "precision", "recall", "fact_", "dim_", "log-return"]:
        assert not teks.str.contains(kata, regex=False).any(), kata
