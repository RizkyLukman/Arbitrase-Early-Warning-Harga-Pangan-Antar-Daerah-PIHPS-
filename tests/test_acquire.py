from datetime import date

from src.acquire import cutoff_date, month_chunks, raw_path, summarize_response


def test_cutoff_is_two_days_before_today():
    assert cutoff_date(date(2026, 10, 25)) == date(2026, 10, 23)


def test_month_chunks_full_months():
    chunks = month_chunks(date(2023, 7, 1), date(2023, 9, 30))
    assert chunks == [
        (date(2023, 7, 1), date(2023, 7, 31)),
        (date(2023, 8, 1), date(2023, 8, 31)),
        (date(2023, 9, 1), date(2023, 9, 30)),
    ]


def test_month_chunks_partial_last_month_and_leap_year():
    chunks = month_chunks(date(2024, 2, 1), date(2024, 3, 13))
    assert chunks == [
        (date(2024, 2, 1), date(2024, 2, 29)),
        (date(2024, 3, 1), date(2024, 3, 13)),
    ]


def test_month_chunks_start_mid_month():
    assert month_chunks(date(2023, 7, 15), date(2023, 7, 20)) == [(date(2023, 7, 15), date(2023, 7, 20))]


def test_raw_path_contains_end_date_so_partial_month_is_refetched(tmp_path):
    p = raw_path(tmp_path, 1, "com_14", date(2026, 10, 1), date(2026, 10, 23))
    assert p == tmp_path / "pt1" / "com_14" / "2026-10-01_2026-10-23.json"


def test_summarize_response_counts_rows_cities_and_values():
    payload = {"data": [
        {"no": "I", "name": "Semua Provinsi", "level": 0, "01/09/2026": "71,400", "02/09/2026": "71,300"},
        {"no": "II", "name": "Jawa Barat", "level": 1, "01/09/2026": "60,850", "02/09/2026": "-"},
        {"no": 1, "name": "Kota Bandung", "level": 2, "01/09/2026": "73,450", "02/09/2026": "-"},
    ]}
    s = summarize_response(payload)
    assert s == {"n_rows": 3, "n_kota": 1, "n_tanggal": 2, "n_nilai": 4, "n_kosong": 2}


def test_summarize_empty_response():
    assert summarize_response({"data": []}) == {"n_rows": 0, "n_kota": 0, "n_tanggal": 0, "n_nilai": 0, "n_kosong": 0}
