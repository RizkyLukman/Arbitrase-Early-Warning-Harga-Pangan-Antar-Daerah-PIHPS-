from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.leadlag import lagged_corr, market_leadership, pairwise_leadlag, prewhiten, significant_leads
from src.analysis.seasonality import event_relative, onset_week

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- Q3
def synthetic_returns(n=170, seed=0):
    rng = np.random.default_rng(seed)
    a = pd.Series(rng.normal(0, 1, n))
    b = 0.7 * a.shift(2) + rng.normal(0, 0.5, n)  # B mengikuti A dengan jeda 2 minggu
    c = pd.Series(rng.normal(0, 1, n))             # C tidak berhubungan
    return pd.DataFrame({"A": a, "B": b, "C": c})


def test_lagged_corr_finds_the_true_lag():
    R = synthetic_returns()
    r2, n2, p2 = lagged_corr(R.A, R.B, 2)
    r1, _, _ = lagged_corr(R.A, R.B, 1)
    assert r2 > 0.6 and p2 < 1e-10 and r2 > abs(r1)
    assert n2 == R[["A", "B"]].assign(A=R.A.shift(2)).dropna().shape[0]


def test_pairwise_and_bh_identify_leader_direction_and_lag():
    R = prewhiten(synthetic_returns(), 4)  # alur yang sama dengan run(): prewhitening dulu
    pw = pairwise_leadlag(R, lags=[1, 2, 3, 4], min_n=100)
    sig = significant_leads(pw, alpha=0.05, min_r=0.15)
    assert list(zip(sig.leader, sig.follower, sig.lag)) == [("A", "B", 2)]


def test_prewhitening_removes_spurious_lead_from_shared_momentum():
    # Dua kota bergerak bersama mengikuti faktor bersama yang punya momentum (AR(1)), TANPA ada yang mendahului.
    rng = np.random.default_rng(7)
    n, f = 170, np.zeros(170)
    for i in range(1, n):
        f[i] = 0.6 * f[i - 1] + rng.normal()
    R = pd.DataFrame({"A": f + rng.normal(0, 0.3, n), "B": f + rng.normal(0, 0.3, n)})
    mentah = pairwise_leadlag(R, [1, 2, 3, 4], 100)
    assert mentah[mentah.lag == 1].r.min() > 0.3            # tanpa prewhitening: korelasi berjeda tampak kuat (semu)
    bersih = significant_leads(pairwise_leadlag(prewhiten(R, 4), [1, 2, 3, 4], 100), alpha=0.05, min_r=0.15)
    assert bersih.empty


def test_market_leadership_finds_city_that_moves_before_the_rest():
    # Kota L bergerak dulu; 8 kota lain menyusul 1 minggu kemudian; kota X independen.
    rng = np.random.default_rng(11)
    n = 170
    lead = pd.Series(rng.normal(0, 1, n))
    cols = {"L": lead, "X": pd.Series(rng.normal(0, 1, n))}
    for i in range(8):
        cols[f"F{i}"] = 0.6 * lead.shift(1) + rng.normal(0, 0.6, n)
    m = market_leadership(pd.DataFrame(cols), lags=[1, 2, 3, 4], min_n=100, alpha=0.05, min_r=0.15)
    peran = m.set_index("kota").peran
    assert peran["L"] == "penentu arah" and m.set_index("kota").loc["L", "jeda"] == 1
    assert peran["X"] == "netral"


def test_no_lead_detected_between_independent_series():
    R = synthetic_returns(seed=3)[["A", "C"]]
    sig = significant_leads(pairwise_leadlag(R, [1, 2, 3, 4], 100), alpha=0.05, min_r=0.15)
    assert sig.empty


# ---------------------------------------------------------------- Q4
def test_event_relative_uses_baseline_mean_of_weeks_minus12_to_minus9():
    minggu = list(range(-12, 5))
    harga = [100, 100, 100, 100] + [100, 102, 104, 106, 110, 115, 120, 125, 0, 118, 110, 105, 100]
    df = pd.DataFrame({"minggu_ke_idul_fitri": minggu, "harga": harga})
    df.loc[df.minggu_ke_idul_fitri == 0, "harga"] = np.nan
    rel = event_relative(df, baseline=(-12, -9), window=(-8, 4))
    assert rel.loc[-1] == pytest.approx(0.25) and rel.loc[-8] == pytest.approx(0.0)
    assert np.isnan(rel.loc[0]) and list(rel.index) == list(range(-8, 5))


def test_onset_requires_threshold_in_enough_years_until_week_minus1():
    weeks = list(range(-8, 5))
    tab = pd.DataFrame({  # baris = minggu, kolom = tahun, nilai = kenaikan vs harga normal
        2024: [0, 0, .01, .06, .08, .07, .10, .12, np.nan, .1, .05, 0, 0],
        2025: [0, .02, .03, .05, .06, .09, .11, .15, np.nan, .1, .02, 0, 0],
        2026: [0, 0, 0, .01, .02, .03, .04, .06, .05, .02, 0, 0, 0],
    }, index=weeks)
    assert onset_week(tab, ambang=0.05, min_tahun=2) == -5
    assert onset_week(tab, ambang=0.20, min_tahun=2) is None


# ---------------------------------------------------------------- hasil
Q4 = ROOT / "reports" / "tables" / "q4_pola_idul_fitri.csv"


@pytest.mark.skipif(not Q4.exists(), reason="jalankan `python -m src.analysis.seasonality` dulu")
def test_q4_table_covers_all_commodities_years_and_window():
    t = pd.read_csv(Q4)
    assert t.kualitas.nunique() == 6 and set(t.tahun_idul_fitri) == {2024, 2025, 2026}
    assert t.minggu_ke_idul_fitri.min() == -8 and t.minggu_ke_idul_fitri.max() == 4
