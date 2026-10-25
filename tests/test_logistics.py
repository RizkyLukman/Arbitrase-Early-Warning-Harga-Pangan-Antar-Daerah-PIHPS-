from pathlib import Path

import pandas as pd
import pytest

from src.logistics import biaya_logistik, cek_mpp, ongkos_angkut_rp_per_kg, tarif_tol_per_km

ROOT = Path(__file__).resolve().parents[1]

LOG = {
    "truk": {"tarif_per_km": 6000},
    "tol": {"porsi_jarak_tol": 1.0, "rute_referensi": {"a": {"tarif_rp": 1_000_000}, "b": {"tarif_rp": 400_000}}},
    "muatan_efektif_kg": {"com_16": {"kg": 3000}, "com_7": {"kg": 3500}},
    "premi_berpendingin": {"com_7": 0.4, "lainnya": 0.0},
    "penanganan": {"bongkar_muat_rp_per_kg": 150, "susut_pct": {"com_16": 0.05, "com_7": 0.01}},
    "batas_atas_mpp": {"ambang_peringatan": 0.5, "komoditas": {"com_16": {"mpp_pct": 40.0}, "com_7": {"mpp_pct": None}}},
}


def test_toll_rate_takes_highest_reference_per_km():
    jarak = pd.DataFrame({"rute_tol": ["a", "b"], "jarak_jalan_km": [500.0, 100.0]})
    nilai, detail = tarif_tol_per_km(LOG, jarak)
    assert nilai == pytest.approx(4000.0)  # 400.000 / 100 km > 1.000.000 / 500 km
    assert set(detail) == {"a", "b"}


def test_transport_cost_formula():
    o = ongkos_angkut_rp_per_kg(100.0, "com_16", LOG, tol_per_km=2000.0)
    # (6000*100 + 2000*100) / 3000 + 150
    assert o["ongkos_angkut_rp_per_kg"] == pytest.approx(800_000 / 3000 + 150)
    assert o["biaya_truk_rp"] == 600_000 and o["biaya_tol_rp"] == 200_000


def test_refrigerated_premium_only_for_chicken():
    ayam = ongkos_angkut_rp_per_kg(100.0, "com_7", LOG, tol_per_km=0.0)
    cabai = ongkos_angkut_rp_per_kg(100.0, "com_16", LOG, tol_per_km=0.0)
    assert ayam["biaya_truk_rp"] == pytest.approx(6000 * 1.4 * 100)
    assert cabai["biaya_truk_rp"] == pytest.approx(6000 * 100)


def test_total_logistics_cost_with_spoilage_and_multiplier():
    # ongkos 1000 Rp/kg, susut 5% dari harga sumber 40.000 = 2000 Rp/kg, pengali 1,5
    assert biaya_logistik(1000.0, 0.05, 40_000.0, 1.5) == pytest.approx((1000 + 2000) * 1.5)


def test_mpp_check_categories():
    assert cek_mpp(1000.0, "com_16", 40_000.0, LOG)["status_mpp"] == "ok"          # 1000 / (40% x 40.000) = 6%
    assert cek_mpp(9000.0, "com_16", 40_000.0, LOG)["status_mpp"] == "tinggi"      # 56%
    assert cek_mpp(17000.0, "com_16", 40_000.0, LOG)["status_mpp"] == "melebihi"   # 106%
    assert cek_mpp(1000.0, "com_7", 40_000.0, LOG)["status_mpp"] == "tanpa_mpp"


BIAYA = ROOT / "data" / "reference" / "biaya_rute.csv"


@pytest.mark.skipif(not BIAYA.exists(), reason="jalankan `python -m src.logistics` dulu")
def test_route_costs_cover_all_routes_and_respect_mpp():
    b = pd.read_csv(BIAYA)
    assert len(b) == 32 and b.ongkos_angkut_rp_per_kg.gt(0).all()
    assert (b.status_mpp != "melebihi").all()
