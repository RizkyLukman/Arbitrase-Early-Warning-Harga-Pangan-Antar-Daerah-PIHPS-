import json
import math

import pandas as pd

from src.load_raw import load_raw_long, load_regency_ref, parse_price, records_from_payload

PAYLOAD = {"data": [
    {"no": "I", "name": "Semua Provinsi", "level": 0, "01/03/2024": "67,900", "04/03/2024": "68,200"},
    {"no": "II", "name": "Jawa Tengah", "level": 1, "01/03/2024": "50,000", "04/03/2024": "-"},
    {"no": 1, "name": "Kab. Boyolali ", "level": 2, "01/03/2024": "1,250,000", "04/03/2024": "-"},
    {"no": "III", "name": "Jawa Timur", "level": 1, "01/03/2024": "40,000", "04/03/2024": "41,000"},
    {"no": 1, "name": "Kota Kediri", "level": 2, "01/03/2024": "39,500", "04/03/2024": "40,250"},
]}


def test_parse_price_comma_thousands_and_dash():
    assert parse_price("58,750") == 58750
    assert parse_price("1,250,000") == 1250000
    assert math.isnan(parse_price("-"))
    assert math.isnan(parse_price(""))
    assert math.isnan(parse_price(None))


def test_records_assign_province_from_row_order_and_strip_names():
    recs = pd.DataFrame(records_from_payload(PAYLOAD, 1, "com_16"))
    kota = recs[recs.level == 2]
    assert set(zip(kota.nama, kota.provinsi)) == {("Kab. Boyolali", "Jawa Tengah"), ("Kota Kediri", "Jawa Timur")}
    nasional = recs[recs.level == 0]
    assert nasional.provinsi.isna().all() and set(nasional.nama) == {"Semua Provinsi"}
    assert len(recs) == 5 * 2


def test_records_dates_and_missing_flag():
    recs = pd.DataFrame(records_from_payload(PAYLOAD, 1, "com_16"))
    row = recs[(recs.nama == "Kab. Boyolali") & (recs.tanggal == pd.Timestamp("2024-03-04"))].iloc[0]
    assert bool(row.kosong) and math.isnan(row.harga)


def test_load_raw_long_reads_folder_layout(tmp_path):
    f = tmp_path / "pt3" / "com_14" / "2024-03-01_2024-03-31.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps(PAYLOAD), encoding="utf-8")
    df = load_raw_long(tmp_path)
    assert set(df.jenis_pasar_id) == {3} and set(df.komoditas_id) == {"com_14"}
    assert df.tanggal.dtype.kind == "M"


def test_load_regency_ref(tmp_path):
    ref = tmp_path / "ref"
    ref.mkdir()
    (ref / "regency_pt1_prov14.json").write_text(json.dumps({"data": [{"id": 166, "name": "Kab. Boyolali "}]}))
    out = load_regency_ref(tmp_path)
    assert out.to_dict("records") == [{"jenis_pasar_id": 1, "provinsi_id": 14, "kota_id": 166, "nama": "Kab. Boyolali"}]
