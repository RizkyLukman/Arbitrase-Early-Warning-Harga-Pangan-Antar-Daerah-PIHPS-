"""Tes Tahap 3 — feature engineering.

Bagian 1: tes unit (tabel kecil buatan tangan).
Bagian 2: tes hasil pada data/interim/harga_mingguan.parquet (dilewati jika belum dibuat).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.features import add_series_features, build_calendar, weekly_aggregate

ROOT = Path(__file__).resolve().parents[1]
SERI = ["jenis_pasar_id", "komoditas_id", "kota_id"]


def harian(values, jenis_pasar_id=1, imputed=None, start="2026-10-12", kota_id=1):
    tgl = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({
        "tanggal": tgl, "jenis_pasar_id": jenis_pasar_id, "komoditas_id": "com_16", "kota_id": kota_id,
        "harga_bersih": np.array(values, dtype=float),
        "is_imputed": imputed if imputed is not None else [False] * len(values),
        "is_usang": False,
    })


AGG = {1: "median", 2: "terakhir", 3: "terakhir", 4: "terakhir"}


# ---------------------------------------------------------------- agregasi mingguan
def test_traditional_market_uses_median_of_real_days_only():
    df = harian([100, 200, 300, 999, np.nan], imputed=[False, False, False, True, False])
    w = weekly_aggregate(df, AGG, SERI, min_hari=3)
    assert w.harga.iloc[0] == 200 and w.n_hari_nyata.iloc[0] == 3 and not w.minggu_tipis.iloc[0]


def test_wholesale_uses_last_real_value_of_week():
    # pola nyata pedagang besar: Senin-Rabu salinan minggu lalu, Kamis harga baru
    df = harian([64_000, 64_000, 64_000, 48_000, 48_000], jenis_pasar_id=3)
    w = weekly_aggregate(df, AGG, SERI, min_hari=3)
    assert w.harga.iloc[0] == 48_000
    assert w.tanggal_nilai.iloc[0] == pd.Timestamp("2026-10-16")


def test_last_value_ignores_imputed_days():
    df = harian([64_000, 64_000, 64_000, 48_000, 50_000], jenis_pasar_id=3, imputed=[False, False, False, False, True])
    w = weekly_aggregate(df, AGG, SERI, min_hari=3)
    assert w.harga.iloc[0] == 48_000


def test_week_without_real_observation_is_nan_and_thin():
    df = harian([np.nan] * 5 + [10, 11, 12, 13, 14])
    w = weekly_aggregate(df, AGG, SERI, min_hari=3).sort_values("minggu")
    assert np.isnan(w.harga.iloc[0]) and w.minggu_tipis.iloc[0] and w.n_hari_nyata.iloc[0] == 0
    assert w.harga.iloc[1] == 12


def test_week_ends_on_friday():
    w = weekly_aggregate(harian([1, 2, 3, 4, 5]), AGG, SERI, min_hari=3)
    assert w.minggu_akhir.iloc[0] == pd.Timestamp("2026-10-16") and w.minggu_akhir.iloc[0].day_name() == "Friday"


# ---------------------------------------------------------------- fitur seri
def mingguan(values, start="2024-01-05"):
    minggu = pd.period_range(start, periods=len(values), freq="W-FRI")
    return pd.DataFrame({"jenis_pasar_id": 1, "komoditas_id": "com_16", "kota_id": 1, "minggu": minggu,
                         "harga": np.array(values, dtype=float)})


FCFG = {"rolling_minggu": [4, 12], "yoy_lag_minggu": 52, "zscore_baseline_minggu": 52, "zscore_min_minggu": 26,
        "perubahan_lag_minggu": 4, "zscore_return_baseline_minggu": 52, "zscore_return_min_minggu": 26}


def test_pct_4w_compares_with_four_weeks_earlier():
    f = add_series_features(mingguan([100, 101, 102, 103, 130, 104]), FCFG)
    assert f.pct_4w.iloc[4] == pytest.approx(0.30)
    assert f.pct_4w.iloc[:4].isna().all()


def test_zscore_return_measures_unusual_weekly_increase_without_look_ahead():
    rng = np.random.default_rng(1)
    harga = list(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 60))))
    harga.append(harga[-1] * 1.30)  # kenaikan 30% dalam seminggu
    a = add_series_features(mingguan(harga), FCFG)
    lr = np.log(pd.Series(harga)).diff()
    base = lr.iloc[:-1].dropna().iloc[-52:]
    assert a.zscore_return.iloc[-1] == pytest.approx((np.log(1.30) - base.mean()) / base.std())
    assert a.zscore_return.iloc[-1] > 2
    harga2 = harga.copy()
    harga2[-1] = harga[-1] * 3  # ubah minggu terakhir: tidak boleh mengubah minggu sebelumnya
    b = add_series_features(mingguan(harga2), FCFG)
    assert a.zscore_return.iloc[:-1].equals(b.zscore_return.iloc[:-1])


def test_log_return_and_wow_only_between_consecutive_weeks():
    f = add_series_features(mingguan([100, 110, np.nan, 121]), FCFG)
    assert f.log_return.iloc[1] == pytest.approx(np.log(1.1))
    assert f.pct_wow.iloc[1] == pytest.approx(0.10)
    assert np.isnan(f.log_return.iloc[3])  # minggu sebelumnya kosong -> tidak dihitung
    assert np.isnan(f.log_return.iloc[0])


def test_yoy_uses_52_week_lag():
    vals = [100.0] * 52 + [125.0]
    f = add_series_features(mingguan(vals), FCFG)
    assert f.pct_yoy.iloc[52] == pytest.approx(0.25) and f.pct_yoy.iloc[:52].isna().all()


def test_zscore_has_no_look_ahead():
    rng = np.random.default_rng(0)
    vals = list(100 + rng.normal(0, 5, 80))
    a = add_series_features(mingguan(vals), FCFG)
    vals2 = vals.copy()
    vals2[70] = 10_000  # ubah masa depan
    b = add_series_features(mingguan(vals2), FCFG)
    assert a.zscore.iloc[:70].equals(b.zscore.iloc[:70])
    assert a.zscore.iloc[:26].isna().all() and a.zscore.iloc[26:].notna().all()


def test_zscore_excludes_current_week_from_baseline():
    vals = [100.0, 102.0] * 20 + [200.0]
    f = add_series_features(mingguan(vals), FCFG)
    base = pd.Series(vals[-41:-1]).iloc[-52:]
    assert f.zscore.iloc[-1] == pytest.approx((200 - base.mean()) / base.std())


def test_rolling_volatility_is_std_of_log_returns():
    vals = [100, 110, 100, 110, 100, 110]
    f = add_series_features(mingguan(vals), FCFG)
    lr = np.log(pd.Series(vals, dtype=float)).diff()
    assert f.vol_4.iloc[-1] == pytest.approx(lr.iloc[-4:].std())


# ---------------------------------------------------------------- kalender
HB = pd.DataFrame({
    "tanggal": pd.to_datetime(["2024-04-10", "2026-03-21"]), "jenis": "idul_fitri",
    "nama": ["Idulfitri 1445 H", "Idulfitri 1447 H"],
    "libur_mulai": pd.to_datetime(["2024-04-08", "2026-03-20"]),
    "libur_selesai": pd.to_datetime(["2024-04-15", "2026-03-24"]),
})


def test_weeks_to_idul_fitri_counts_from_week_containing_the_date():
    kal = build_calendar(pd.period_range("2023-12-01", "2026-06-30", freq="W-FRI"), HB, (-12, 4)).set_index("minggu_akhir")
    assert kal.loc["2024-04-12", "minggu_ke_idul_fitri"] == 0
    assert kal.loc["2024-01-19", "minggu_ke_idul_fitri"] == -12
    assert kal.loc["2024-05-10", "minggu_ke_idul_fitri"] == 4
    assert pd.isna(kal.loc["2024-05-17", "minggu_ke_idul_fitri"])
    assert kal.loc["2026-03-27", "minggu_ke_idul_fitri"] == 0  # Idulfitri hari Sabtu -> minggu yang berakhir Jumat berikutnya
    assert kal.loc["2024-04-12", "tahun_idul_fitri"] == 2024


def test_calendar_marks_holiday_weeks():
    kal = build_calendar(pd.period_range("2024-03-29", "2024-04-26", freq="W-FRI"), HB, (-12, 4)).set_index("minggu_akhir")
    assert kal.loc["2024-04-12", "ada_libur_hari_besar"] and kal.loc["2024-04-19", "ada_libur_hari_besar"]
    assert not kal.loc["2024-04-26", "ada_libur_hari_besar"]


# ---------------------------------------------------------------- hasil: data/interim
MINGGUAN = ROOT / "data" / "interim" / "harga_mingguan.parquet"
needs_data = pytest.mark.skipif(not MINGGUAN.exists(), reason="jalankan `python -m src.features` dulu")


@pytest.fixture(scope="module")
def mg():
    return pd.read_parquet(MINGGUAN)


@needs_data
def test_weekly_keys_unique_and_grid_complete(mg):
    assert not mg.duplicated(SERI + ["minggu_akhir"]).any()
    assert (mg.groupby(SERI).minggu_akhir.nunique() == mg.minggu_akhir.nunique()).all()


@needs_data
def test_supply_chain_pairs_have_data_at_all_three_levels(mg):
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    ada = mg[mg.harga.notna()].groupby(["jenis_pasar_id", "kota_id", "komoditas_id"]).size()
    for p in cfg["rantai_pasok"]["pasangan_kota_kabupaten"]:
        assert p["status"] == "PERLU_VERIFIKASI"
        for com in p["komoditas"]:
            for pt, kid in [(4, p["produsen_kota_id"]), (3, p["kota_id"]), (1, p["kota_id"])]:
                assert ada.get((pt, kid, com), 0) >= 100, (p["kota"], p["produsen"], com, pt)


@needs_data
def test_weekly_prices_positive_and_fridays(mg):
    assert (mg.harga.dropna() > 0).all()
    assert (mg.minggu_akhir.dt.day_of_week == 4).all()
