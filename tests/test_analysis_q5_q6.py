from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.early_warning import evaluate_alerts, label_spikes, seasonal_naive_alerts
from src.analysis.margin import margins

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- Q5
def test_margins_between_levels():
    df = pd.DataFrame({"produsen": [20_000.0, 25_000.0], "pedagang_besar": [25_000.0, 24_000.0],
                       "tradisional": [30_000.0, 30_000.0]})
    m = margins(df)
    assert m.tambahan_pedagang_besar_pct.iloc[0] == pytest.approx(0.25)
    assert m.tambahan_eceran_pct.iloc[0] == pytest.approx(0.20)
    assert m.tambahan_total_pct.iloc[0] == pytest.approx(0.50)
    assert m.hemat_beli_produsen_vs_eceran_pct.iloc[0] == pytest.approx(1 - 20_000 / 30_000)
    assert m.produsen_lebih_mahal.tolist() == [False, True]   # inversi ditandai, bukan dibuang


# ---------------------------------------------------------------- Q6
def weekly(prices, start="2025-01-03"):
    return pd.Series(prices, index=pd.date_range(start, periods=len(prices), freq="W-FRI"), dtype=float)


def test_label_spikes_onset_and_hit_week():
    # harga datar 100, lalu naik ke 130 (>= 25% dalam 4 minggu baru tercapai mulai minggu ke-3)
    h = weekly([100, 100, 100, 100, 110, 120, 130, 130, 130, 130, 130])
    lab = label_spikes(h, horizon=4, ambang=0.25)
    on = lab[lab.onset]
    assert len(on) == 1 and on.index[0] == h.index[2]            # 100 (minggu 2) -> 130 (minggu 6): +30%
    assert lab.loc[h.index[2], "minggu_terlihat"] == h.index[6]  # pertama kali >= +25% di atas harga awal


def test_evaluate_alerts_precision_recall_and_lead_time():
    idx = pd.date_range("2025-01-03", periods=20, freq="W-FRI")
    onset = pd.Series(False, index=idx)
    onset.iloc[[5, 15]] = True
    terlihat = pd.Series(pd.NaT, index=idx)
    terlihat.iloc[5], terlihat.iloc[15] = idx[7], idx[17]
    alert = pd.Series(False, index=idx)
    alert.iloc[[3, 10]] = True   # minggu 3: 2 minggu sebelum onset 5 (benar); minggu 10: tidak ada onset 10..14 (salah)
    r = evaluate_alerts(alert, onset, terlihat, window=4)
    assert r["peringatan"] == 2 and r["peringatan_benar"] == 1
    assert r["lonjakan"] == 2 and r["lonjakan_terdeteksi"] == 1
    assert r["lead_time_rata_minggu"] == pytest.approx(4.0)   # terlihat minggu 7 - peringatan pertama minggu 3


def test_seasonal_naive_repeats_last_years_spike_timing():
    idx = pd.date_range("2024-01-05", periods=110, freq="W-FRI")
    onset = pd.Series(False, index=idx)
    onset.iloc[10] = True
    a = seasonal_naive_alerts(onset, window=4)
    assert a.iloc[62] and a.iloc[58]       # 52 minggu setelah t=10..6 -> ada onset tahun lalu dalam 0..4 minggu ke depan
    assert not a.iloc[30] and not a.iloc[64]
