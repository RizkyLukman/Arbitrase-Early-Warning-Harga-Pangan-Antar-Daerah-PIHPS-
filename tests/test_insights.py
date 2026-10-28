"""Tes src/insights.py: aturan tindakan & kalimat 'hal yang perlu diketahui' dari konteks satu komoditas."""
from __future__ import annotations

import numpy as np

from src.insights import pilih_hal, susun_tindakan

ICFG = {"ambang_naik_4_minggu": 0.15, "ambang_turun_4_minggu": -0.15, "ambang_selisih_nasional": 0.10,
        "minggu_sebelum_jendela": 2, "top_n_gejolak": 2, "min_hemat_produsen": 0.20, "jumlah_hal": 3}


def konteks(**over) -> dict:
    base = {"nama": "bawang merah", "minggu_ke_idul_fitri": None, "mulai_naik_minggu": -4,
            "kenaikan_minggu_min1_rata": 0.26, "rute_terbaik": None, "harga": 30_000.0, "pct_4w": 0.02,
            "selisih_nasional_pct": -0.05, "peringkat_gejolak": 3, "rata_perubahan_abs": 0.05,
            "hemat_produsen_pct": 0.31, "hemat_pedagang_besar_pct": 0.23, "n_kota_peringatan": 0,
            "kota_peringatan": "", "ketepatan_peringatan": 0.12}
    base.update(over)
    return base


def test_idul_fitri_window_gives_top_priority_action_with_numbers():
    rows = susun_tindakan(konteks(minggu_ke_idul_fitri=-3), ICFG)
    r = rows[0]
    assert r["tindakan"].startswith("Amankan stok") and r["beli_lebih_awal"]
    assert "3 minggu" in r["alasan_singkat"] and "26%" in r["alasan_singkat"]
    assert r["nilai"] == 0.26 and r["sumber"] == "q4_ringkasan"


def test_weeks_just_before_window_also_count_as_buy_early():
    rows = susun_tindakan(konteks(minggu_ke_idul_fitri=-6), ICFG)   # jendela mulai -4, 2 minggu lagi
    assert rows[0]["beli_lebih_awal"] and "2 minggu lagi" in rows[0]["alasan_singkat"]
    rows = susun_tindakan(konteks(minggu_ke_idul_fitri=-8), ICFG)   # 4 minggu lagi: belum
    assert not any(r["beli_lebih_awal"] for r in rows)


def test_no_window_for_commodity_without_consistent_rise():
    rows = susun_tindakan(konteks(minggu_ke_idul_fitri=-2, mulai_naik_minggu=None), ICFG)
    assert not any(r["beli_lebih_awal"] for r in rows)


def test_profitable_route_this_week_gives_move_stock_action():
    rute = {"kota_sumber": "Kota Tegal", "kota_tujuan": "Kota Jakarta Pusat", "untung_rp": 2676.0,
            "berturut": 12, "porsi_untung": 1.0, "rute_key": 7}
    rows = susun_tindakan(konteks(rute_terbaik=rute), ICFG)
    r = next(x for x in rows if x["tindakan"].startswith("Pindahkan stok"))
    assert "Kota Tegal" in r["tindakan"] and "Rp 2.676/kg" in r["alasan_singkat"] and "12 minggu" in r["alasan_singkat"]
    assert r["pindah_stok"] and r["rute_key"] == 7


def test_route_with_loss_this_week_is_not_recommended():
    rute = {"kota_sumber": "A", "kota_tujuan": "B", "untung_rp": -500.0, "berturut": 0, "porsi_untung": 0.9, "rute_key": 1}
    rows = susun_tindakan(konteks(rute_terbaik=rute), ICFG)
    assert not any(r["pindah_stok"] for r in rows)


def test_fast_rise_and_fall_are_described_with_comparison():
    naik = susun_tindakan(konteks(pct_4w=0.32), ICFG)
    assert any("naik 32%" in r["alasan_singkat"] and "4 minggu lalu" in r["alasan_singkat"] for r in naik)
    turun = susun_tindakan(konteks(pct_4w=-0.20), ICFG)
    assert any("turun 20%" in r["alasan_singkat"] for r in turun)


def test_producer_saving_action_only_above_threshold():
    assert any("produsen" in r["tindakan"] for r in susun_tindakan(konteks(hemat_produsen_pct=0.31), ICFG))
    assert not any("produsen" in r["tindakan"] for r in susun_tindakan(konteks(hemat_produsen_pct=0.10), ICFG))
    assert not any("produsen" in r["tindakan"] for r in susun_tindakan(konteks(hemat_produsen_pct=np.nan), ICFG))


def test_alert_is_information_only_with_accuracy_caveat():
    rows = susun_tindakan(konteks(n_kota_peringatan=2, kota_peringatan="Kota Kediri, Kota Surabaya"), ICFG)
    r = next(x for x in rows if "peringatan" in x["tindakan"].lower())
    assert "1,2 dari 10" in r["alasan_singkat"] and "Kota Kediri" in r["alasan_singkat"]


def test_quiet_week_gives_routine_action():
    rows = susun_tindakan(konteks(hemat_produsen_pct=0.05, peringkat_gejolak=5), ICFG)
    assert len(rows) == 1 and rows[0]["tindakan"] == "Beli rutin"
    assert "nasional" in rows[0]["alasan_singkat"]


def test_every_action_row_keeps_its_source_number():
    rows = susun_tindakan(konteks(minggu_ke_idul_fitri=-3, pct_4w=0.3, n_kota_peringatan=1, kota_peringatan="X"), ICFG)
    for r in rows:
        assert {"tindakan", "alasan_singkat", "nilai", "satuan", "pembanding", "sumber", "prioritas"} <= set(r)
        assert r["sumber"]


def test_pilih_hal_takes_top_n_distinct_by_priority_then_score():
    kandidat = [
        {"kalimat": "a", "prioritas": 3, "skor": 0.5, "komoditas_key": 1},
        {"kalimat": "b", "prioritas": 1, "skor": 0.1, "komoditas_key": 2},
        {"kalimat": "c", "prioritas": 2, "skor": 0.9, "komoditas_key": 3},
        {"kalimat": "d", "prioritas": 2, "skor": 0.2, "komoditas_key": 4},
    ]
    hal = pilih_hal(kandidat, 3)
    assert [h["kalimat"] for h in hal] == ["b", "c", "d"]
    assert [h["urutan"] for h in hal] == [1, 2, 3]
