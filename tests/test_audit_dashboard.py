"""Tes src/audit_dashboard.py: nilai acuan konsisten dengan data/processed dan pemetaan sel bernama lengkap."""
from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.common import load_cfg
from src.audit_dashboard import PROCESSED, nilai_acuan, pemetaan_acuan


@pytest.fixture(scope="module")
def acuan():
    if not (PROCESSED / "fact_harga.parquet").exists():
        pytest.skip("data/processed/ belum dibuat")
    cfg, lcfg = load_cfg()
    return nilai_acuan(cfg, lcfg)


def test_nilai_acuan_matches_exported_tables(acuan):
    dr = pd.read_parquet(PROCESSED / "dim_rute.parquet")
    assert acuan["ringkasan"]["rute_layak_kons"] == int(dr.layak.sum())
    assert acuan["rute"]["per_pengali"][acuan["rute"]["pengali_acuan"]]["layak"] == int(dr.layak.sum())  # dihitung ulang dari komponen
    assert len(acuan["ringkasan"]["hal"]) == 3
    assert acuan["peringatan"]["layak_operasional"] is False   # Q6: aturan kalah dari pola tahun lalu


def test_route_count_falls_as_cost_multiplier_rises(acuan):
    s = acuan["rute"]["per_pengali"]
    vals = [s[p]["median_positif"] for p in sorted(s)]
    assert vals == sorted(vals, reverse=True)


def test_pemetaan_acuan_covers_every_named_kpi(acuan):
    from src.build_excel import build  # noqa: F401  (hanya memastikan modul terimpor)
    peta = pemetaan_acuan(acuan)
    assert len(peta) >= 20
    for name, (target, tol, ket) in peta.items():
        assert ket and (tol is None or tol >= 0)
        assert target is not None
