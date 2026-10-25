"""Tes Tahap 2 — cleaning.

Bagian 1: tes unit tiap aturan cleaning (tabel kecil buatan tangan).
Bagian 2: tes hasil pada data/interim/harga_harian.parquet (dilewati jika belum dibuat).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.clean import (
    SERI, complete_grid, dedupe_latest, detect_holiday_dates, fill_short_gaps, flag_outliers, map_city_ids,
    stale_run_length,
)

ROOT = Path(__file__).resolve().parents[1]
OUTLIER_CFG = {"jendela_median_hari": 21, "k_mad": 5, "lonjakan_deviasi_min": 0.25,
               "rasio_ekstrem": 3, "rasio_lintas_kota": 5}


def seri(values, kota_id=1, jenis_pasar_id=1, komoditas_id="com_16", start="2024-01-01"):
    tgl = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({"jenis_pasar_id": jenis_pasar_id, "komoditas_id": komoditas_id, "kota_id": kota_id,
                         "tanggal": tgl, "harga_kerja": np.array(values, dtype=float)})


# ---------------------------------------------------------------- unit: struktur
def test_dedupe_keeps_value_from_latest_file():
    df = pd.DataFrame({
        "jenis_pasar_id": [1, 1], "komoditas_id": ["com_16"] * 2, "level": [2, 2], "nama": ["Kota A"] * 2,
        "tanggal": pd.to_datetime(["2026-10-01"] * 2), "harga": [100.0, 120.0],
        "sumber_file": ["2026-10-01_2026-10-23.json", "2026-10-01_2026-10-30.json"]})
    out = dedupe_latest(df)
    assert len(out) == 1 and out.harga.iloc[0] == 120.0


def test_map_city_ids_uses_price_type_specific_reference_and_drops_duplicates():
    kota = pd.DataFrame({"jenis_pasar_id": [2, 2, 1], "nama": ["Kota Surakarta", "Kota Surakarta (Solo)", "Kota X"]})
    ref = pd.DataFrame({"jenis_pasar_id": [2, 2, 1], "provinsi_id": [14, 14, 12],
                        "kota_id": [787, 36, 5], "nama": ["Kota Surakarta", "Kota Surakarta (Solo)", "Kota X"]})
    out = map_city_ids(kota, ref, drop_ids=[787])
    assert sorted(out.kota_id) == [5, 36]
    assert set(out.columns) >= {"kota_id", "provinsi_id"}


def test_map_city_ids_fails_loudly_on_unknown_name():
    kota = pd.DataFrame({"jenis_pasar_id": [1], "nama": ["Kota Tidak Ada"]})
    ref = pd.DataFrame({"jenis_pasar_id": [1], "provinsi_id": [12], "kota_id": [5], "nama": ["Kota X"]})
    with pytest.raises(ValueError, match="Kota Tidak Ada"):
        map_city_ids(kota, ref, drop_ids=[])


def test_complete_grid_adds_missing_months_as_nan():
    tgl = pd.bdate_range("2024-01-01", periods=6)
    kota = pd.DataFrame({"jenis_pasar_id": 1, "komoditas_id": "com_14", "kota_id": 45, "kota": "Kab. Jember",
                         "provinsi": "Jawa Timur", "provinsi_id": 16, "tanggal": tgl[[0, 1, 5]],
                         "harga": [10.0, 11.0, 12.0]})
    out = complete_grid(kota, tgl).sort_values("tanggal")
    assert len(out) == 6 and out.harga.isna().sum() == 3
    assert (out.kota == "Kab. Jember").all() and (out.provinsi_id == 16).all()


# ---------------------------------------------------------------- unit: hari libur
def test_detect_holiday_dates_when_almost_all_traditional_series_unchanged():
    frames = []
    for k in range(10):
        vals = [100 + i + k for i in range(10)]
        vals[5] = vals[4]  # hari ke-6: semua seri tidak berubah -> libur
        frames.append(seri(vals, kota_id=k))
    df = pd.concat(frames).rename(columns={"harga_kerja": "harga"})
    libur = detect_holiday_dates(df, ambang=0.9)
    assert list(libur) == [pd.bdate_range("2024-01-01", periods=10)[5]]


def test_detect_holiday_ignores_non_traditional_markets():
    df = pd.concat([seri([100] * 10, kota_id=k, jenis_pasar_id=4) for k in range(5)]).rename(
        columns={"harga_kerja": "harga"})
    assert len(detect_holiday_dates(df, ambang=0.9)) == 0


# ---------------------------------------------------------------- unit: outlier
def test_rule_b_flags_extreme_one_day_value_as_input_error():
    vals = [50_000 + (i % 3) * 500 for i in range(30)]
    vals[15] = 160_000
    out = flag_outliers(seri(vals), OUTLIER_CFG, "harga_kerja")
    row = out.iloc[15]
    assert row.is_outlier_flag and "rasio_ekstrem" in row.alasan_outlier
    assert out.is_outlier_flag.sum() == 1


def test_rule_a_marks_sharp_spike_but_not_as_input_error():
    vals = [50_000 + (i % 3) * 500 for i in range(30)]
    vals[15] = 80_000  # +60%: tajam, tapi < 3x
    out = flag_outliers(seri(vals), OUTLIER_CFG, "harga_kerja")
    assert out.is_lonjakan_tajam.iloc[15] and not out.is_outlier_flag.iloc[15]
    assert out.is_lonjakan_tajam.sum() == 1


def test_rule_a_needs_both_neighbours_present():
    vals = [50_000 + (i % 3) * 500 for i in range(30)]
    vals[0] = 80_000  # hari pertama: tidak ada tetangga sebelumnya
    out = flag_outliers(seri(vals), OUTLIER_CFG, "harga_kerja")
    assert not out.is_lonjakan_tajam.iloc[0]


def test_rule_c_flags_level_shift_against_other_cities():
    frames = [seri([20_000 + k * 100] * 30, kota_id=k, jenis_pasar_id=4) for k in range(1, 6)]
    garut = [20_000] * 10 + [3_000] * 20  # bertahan, tidak terdeteksi rasio terhadap dirinya sendiri di akhir
    frames.append(seri(garut, kota_id=99, jenis_pasar_id=4))
    out = flag_outliers(pd.concat(frames, ignore_index=True), OUTLIER_CFG, "harga_kerja")
    g = out[out.kota_id == 99]
    assert g.is_outlier_flag.iloc[10:].all() and not g.is_outlier_flag.iloc[:10].any()
    assert g.alasan_outlier.iloc[-1].startswith("lintas_kota") or "lintas_kota" in g.alasan_outlier.iloc[-1]
    assert not out[out.kota_id != 99].is_outlier_flag.any()


def test_flat_series_is_not_flagged():
    out = flag_outliers(seri([30_000] * 30), OUTLIER_CFG, "harga_kerja")
    assert not out.is_outlier_flag.any() and not out.is_lonjakan_tajam.any()


def test_stepped_series_with_holidays_is_not_flagged_when_using_raw_price():
    # Regresi: harga produsen datar lama lalu diperbarui (11.350 -> 39.000), dengan 6 hari libur (salinan) sebelum
    # perubahan. Dihitung dari harga asli, tidak boleh ada salah input. (Kasus nyata: produsen bawang Kab. Cirebon 2024-04.)
    vals = [11_350] * 20 + [39_000] * 20
    df = seri(vals, jenis_pasar_id=4)
    out = flag_outliers(df.rename(columns={"harga_kerja": "harga"}), OUTLIER_CFG, "harga")
    assert not out.is_outlier_flag.any()


# ---------------------------------------------------------------- unit: celah & usang
def test_fill_short_gaps_fills_up_to_max_and_leaves_longer_gaps():
    vals = [10, np.nan, np.nan, 13, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 20]
    df = seri(vals)
    filled, imputed = fill_short_gaps(df, "harga_kerja", max_gap=5)
    assert filled.tolist()[:4] == [10, 10, 10, 13]
    assert np.isnan(filled.iloc[4:10]).all()  # celah 6 hari: tidak diisi
    assert imputed.tolist()[:4] == [False, True, True, False] and not imputed.iloc[4:].any()


def test_fill_short_gaps_does_not_fill_leading_gap_or_cross_series():
    a = seri([np.nan, 5, 6], kota_id=1)
    b = seri([np.nan, np.nan, 7], kota_id=2)
    filled, imputed = fill_short_gaps(pd.concat([a, b], ignore_index=True), "harga_kerja", max_gap=5)
    assert np.isnan(filled.iloc[0]) and np.isnan(filled.iloc[3]) and np.isnan(filled.iloc[4])
    assert not imputed.any()


def test_stale_run_length_counts_consecutive_unchanged_days():
    df = seri([10, 10, 10, 11, 11, np.nan, 11])
    assert stale_run_length(df, "harga_kerja").tolist() == [0, 1, 2, 0, 1, 0, 0]


# ---------------------------------------------------------------- hasil: data/interim
HARIAN = ROOT / "data" / "interim" / "harga_harian.parquet"
needs_data = pytest.mark.skipif(not HARIAN.exists(), reason="jalankan `python -m src.clean` dulu")


@pytest.fixture(scope="module")
def harian():
    return pd.read_parquet(HARIAN)


@needs_data
def test_no_price_le_zero(harian):
    assert (harian.harga_bersih.dropna() > 0).all() and (harian.harga.dropna() > 0).all()


@needs_data
def test_no_duplicate_keys(harian):
    assert not harian.duplicated(["tanggal", "jenis_pasar_id", "kota_id", "komoditas_id"]).any()


@needs_data
def test_dates_are_weekdays_only(harian):
    assert (harian.tanggal.dt.day_of_week < 5).all()


@needs_data
def test_every_series_has_every_working_day(harian):
    n_tanggal = harian.tanggal.nunique()
    per_seri = harian.groupby(["jenis_pasar_id", "komoditas_id", "kota_id"]).tanggal.nunique()
    assert (per_seri == n_tanggal).all()


@needs_data
def test_every_city_has_id_and_province(harian):
    assert harian.kota_id.notna().all() and harian.provinsi.notna().all()
    assert 787 not in set(harian.kota_id)


@needs_data
def test_flags_are_consistent(harian):
    # nilai salah input & hari libur tidak boleh muncul di harga_bersih kecuali hasil isi celah
    assert harian.loc[harian.is_outlier_flag & ~harian.is_imputed, "harga_bersih"].isna().all()
    assert harian.loc[harian.is_libur_isi & ~harian.is_imputed, "harga_bersih"].isna().all()
    # is_imputed hanya pada baris yang memang terisi
    assert harian.loc[harian.is_imputed, "harga_bersih"].notna().all()
