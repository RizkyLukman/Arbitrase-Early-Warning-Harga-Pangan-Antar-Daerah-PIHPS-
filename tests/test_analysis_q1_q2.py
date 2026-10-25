from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.spread import is_layak, route_metrics, run_lengths, weekly_spread
from src.analysis.volatility import series_volatility

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- Q1
def test_series_volatility_metrics():
    harga = [100.0, 110.0, 99.0, 108.9, 98.01]
    lr = np.log(pd.Series(harga)).diff()
    df = pd.DataFrame({"kota": "A", "kualitas": "Cabai", "minggu_akhir": pd.date_range("2024-01-05", periods=5, freq="W-FRI"),
                       "harga": harga, "log_return": lr, "pct_wow": pd.Series(harga).pct_change()})
    m = series_volatility(df, ["kota", "kualitas"]).iloc[0]
    assert m.n_minggu_return == 4
    assert m.gejolak_mingguan == pytest.approx(lr.std())
    assert m.rata_perubahan_abs == pytest.approx(pd.Series(harga).pct_change().abs().mean())
    assert m.cv == pytest.approx(np.std(harga, ddof=1) / np.mean(harga))


# ---------------------------------------------------------------- Q2
def test_run_lengths_break_on_loss_but_skip_missing_weeks():
    s = pd.Series([True, True, np.nan, True, False, True, True, True])
    assert run_lengths(s) == [3, 3]


def test_weekly_spread_net_of_logistics_and_multiplier():
    minggu = pd.date_range("2024-01-05", periods=3, freq="W-FRI")
    src = pd.DataFrame({"minggu_akhir": minggu, "harga": [40_000.0, 40_000.0, 50_000.0], "is_usang": [False, True, False]})
    dst = pd.DataFrame({"minggu_akhir": minggu, "harga": [50_000.0, 60_000.0, 52_000.0]})
    biaya = {"ongkos_angkut_rp_per_kg": 1_000.0, "susut_pct": 0.05}
    s = weekly_spread(src, dst, biaya, [1.0, 2.0], kecualikan_usang=True)
    w1 = s.iloc[0]
    assert w1.spread_kotor == 10_000
    assert w1.biaya_logistik_x1 == pytest.approx(1_000 + 0.05 * 40_000)
    assert w1.spread_bersih_x1 == pytest.approx(10_000 - 3_000)
    assert w1.spread_bersih_x2 == pytest.approx(10_000 - 6_000)
    assert np.isnan(s.iloc[1].spread_bersih_x1)  # minggu sumber usang dikecualikan
    assert s.iloc[2].spread_bersih_x1 == pytest.approx(2_000 - 3_500)


def test_route_metrics_counts_persistence_and_last_window():
    minggu = pd.date_range("2024-01-05", periods=8, freq="W-FRI")
    nilai = [500, 800, -100, 300, 400, 600, np.nan, 700]
    s = pd.DataFrame({"minggu_akhir": minggu, "spread_bersih_x1": nilai})
    m = route_metrics(s, 1.0, jendela=5)
    assert m["n_minggu"] == 7
    assert m["porsi_minggu_untung"] == pytest.approx(6 / 7)
    assert m["median_untung_rp_per_kg"] == pytest.approx(np.nanmedian(nilai))
    assert m["persistensi_rata_minggu"] == pytest.approx((2 + 4) / 2)  # minggu kosong dilewati: [2, 4]
    assert m["persistensi_maks_minggu"] == 4
    assert m["untung_dari_jendela"] == 4 and m["jendela_berdata"] == 4  # 5 minggu terakhir, 1 kosong
    assert m["minggu_untung_berturut_terakhir"] == 1


def test_route_is_feasible_only_if_profitable_in_conservative_scenario():
    cfg = {"layak_min_porsi_minggu_untung": 0.6, "layak_median_untung_positif": True}
    assert is_layak({"porsi_minggu_untung": 0.7, "median_untung_rp_per_kg": 100.0}, cfg)
    assert not is_layak({"porsi_minggu_untung": 0.5, "median_untung_rp_per_kg": 100.0}, cfg)
    assert not is_layak({"porsi_minggu_untung": 0.9, "median_untung_rp_per_kg": -1.0}, cfg)


# ---------------------------------------------------------------- hasil
Q2 = ROOT / "reports" / "tables" / "q2_rute_ringkasan.csv"


@pytest.mark.skipif(not Q2.exists(), reason="jalankan `python -m src.analysis.spread` dulu")
def test_q2_summary_has_all_routes_and_scenarios():
    r = pd.read_csv(Q2)
    assert r.groupby("pengali").size().eq(32).all()
    assert set(r.pengali) == {0.5, 1.0, 1.5, 2.0}
    # untung tidak boleh naik saat ongkos dinaikkan
    p = r.pivot_table(index=["kota_sumber", "kota_tujuan", "kualitas"], columns="pengali", values="median_untung_rp_per_kg")
    assert (p[0.5] >= p[1.0]).all() and (p[1.0] >= p[1.5]).all() and (p[1.5] >= p[2.0]).all()
