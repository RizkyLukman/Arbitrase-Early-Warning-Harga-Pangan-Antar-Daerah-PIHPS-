"""Tahap 1 — Akuisisi data harga PIHPS (Bank Indonesia).

Mengunduh respons JSON apa adanya ke data/raw/, satu file per
jenis pasar × komoditas × bulan. Detail endpoint: docs/data_access.md.

Contoh:
    python -m src.acquire --dry-run          # lihat rencana tanpa mengunduh
    python -m src.acquire --limit 4          # uji coba 4 request
    python -m src.acquire                    # unduh semua (bisa dilanjutkan jika terputus)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"

LOG_COLUMNS = [
    "waktu_unduh", "endpoint", "price_type_id", "comcat_id", "province_id",
    "start_date", "end_date", "status", "http_status", "n_rows", "n_kota",
    "n_tanggal", "n_nilai", "n_kosong", "bytes", "detik", "file", "error",
]

log = logging.getLogger("acquire")


# ---------- fungsi murni (diuji di tests/test_acquire.py) ----------

def cutoff_date(today: date) -> date:
    """Tanggal akhir data: H-2, karena data PIHPS bisa direvisi sampai hari berikutnya."""
    return today - timedelta(days=2)


def month_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Pecah rentang [start, end] menjadi potongan per bulan kalender."""
    chunks = []
    cur = start
    while cur <= end:
        last = date(cur.year, cur.month, monthrange(cur.year, cur.month)[1])
        chunks.append((cur, min(last, end)))
        cur = last + timedelta(days=1)
    return chunks


def raw_path(raw_dir: Path, price_type_id: int, comcat_id: str, start: date, end: date) -> Path:
    """Nama file memuat tanggal akhir, jadi bulan yang belum lengkap akan diunduh ulang di run berikutnya."""
    return Path(raw_dir) / f"pt{price_type_id}" / comcat_id / f"{start.isoformat()}_{end.isoformat()}.json"


def summarize_response(payload: dict) -> dict:
    rows = payload.get("data") or []
    tanggal = {k for r in rows for k in r if "/" in k}
    nilai = [v for r in rows for k, v in r.items() if "/" in k]
    kosong = sum(1 for v in nilai if v in ("-", "", None))
    return {
        "n_rows": len(rows),
        "n_kota": sum(1 for r in rows if r.get("level") == 2),
        "n_tanggal": len(tanggal),
        "n_nilai": len(nilai) - kosong,
        "n_kosong": kosong,
    }


# ---------- akses HTTP ----------

class PihpsClient:
    """Klien sopan: satu koneksi, jeda tetap antar request, retry dengan backoff."""

    def __init__(self, cfg: dict):
        src = cfg["sumber"]
        self.base = src["base_url"]
        self.delay = float(src["jeda_detik"])
        self.timeout = float(src["timeout_detik"])
        self.max_retry = int(src["max_retry"])
        self.session = requests.Session()
        self.session.headers["User-Agent"] = src["user_agent"]
        self._last = 0.0

    def get(self, endpoint: str, params: dict) -> requests.Response:
        last_err: Exception | None = None
        for attempt in range(self.max_retry + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.session.get(self.base + endpoint, params=params, timeout=self.timeout)
                self._last = time.monotonic()
                if r.status_code >= 500 or r.status_code == 429:
                    raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
                r.raise_for_status()
                r.json()  # pastikan respons valid sebelum disimpan
                return r
            except (requests.RequestException, ValueError) as e:
                self._last = time.monotonic()
                last_err = e
                if attempt < self.max_retry:
                    backoff = 5 * 2 ** attempt
                    log.warning("Gagal (%s), coba lagi %d detik lagi [%d/%d]", e, backoff, attempt + 1, self.max_retry)
                    time.sleep(backoff)
        raise last_err  # type: ignore[misc]


# ---------- penyimpanan ----------

def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(content)
    tmp.replace(path)


def append_log(log_path: Path, row: dict) -> None:
    new = not log_path.exists()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in LOG_COLUMNS})


def fetch_references(client: PihpsClient, cfg: dict, raw_dir: Path) -> None:
    """Simpan tabel referensi (id ↔ nama). Dibutuhkan untuk memetakan nama kota ke id di Tahap 2."""
    ref_dir = raw_dir / "ref"
    jobs = [("GetRefPriceType", {}, "price_type.json"),
            ("GetRefCommodityAndCategory", {}, "commodity.json"),
            ("GetRefProvince", {}, "province.json")]
    for pt in cfg["jenis_pasar"]:
        for prov in cfg["wilayah"]["provinsi_id"]:
            jobs.append(("GetRefRegency", {"price_type_id": pt, "ref_prov_id": prov}, f"regency_pt{pt}_prov{prov}.json"))
    for endpoint, params, name in jobs:
        path = ref_dir / name
        if path.exists():
            continue
        r = client.get(endpoint, params)
        write_atomic(path, r.content)
        log.info("Referensi: %s", name)


# ---------- alur utama ----------

def plan_jobs(cfg: dict, raw_dir: Path, today: date, only_pt=None, only_com=None) -> list[dict]:
    start = date.fromisoformat(cfg["periode"]["tanggal_mulai"])
    end_cfg = cfg["periode"]["tanggal_selesai"]
    end = cutoff_date(today) if end_cfg == "auto_h_minus_2" else date.fromisoformat(end_cfg)
    province = ",".join(str(p) for p in cfg["wilayah"]["provinsi_id"])
    jobs = []
    for pt in cfg["jenis_pasar"]:
        if only_pt and pt not in only_pt:
            continue
        for com in cfg["komoditas_fokus"] | (cfg.get("komoditas_opsional") or {}):
            if only_com and com not in only_com:
                continue
            for s, e in month_chunks(start, end):
                jobs.append({"price_type_id": pt, "comcat_id": com, "province_id": province,
                             "start": s, "end": e, "path": raw_path(raw_dir, pt, com, s, e)})
    return jobs


def run(args: argparse.Namespace) -> None:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw_dir = ROOT / cfg["paths"]["raw"]
    log_path = ROOT / cfg["paths"]["log_unduhan"]
    endpoint = cfg["sumber"]["endpoint_harga"]

    jobs = plan_jobs(cfg, raw_dir, date.today(), args.pt, args.com)
    todo = [j for j in jobs if not j["path"].exists()]
    log.info("Rencana: %d file, %d sudah ada, %d akan diunduh", len(jobs), len(jobs) - len(todo), len(todo))
    if args.limit:
        todo = todo[: args.limit]
    if args.dry_run:
        for j in todo[:20]:
            log.info("  %s", j["path"].relative_to(ROOT))
        return

    client = PihpsClient(cfg)
    fetch_references(client, cfg, raw_dir)

    n_ok = n_err = 0
    for i, j in enumerate(todo, 1):
        params = {
            "price_type_id": j["price_type_id"], "comcat_id": j["comcat_id"],
            "province_id": j["province_id"], "regency_id": "",
            "showKota": "true", "showPasar": "false",
            "tipe_laporan": cfg["sumber"]["tipe_laporan"],
            "start_date": j["start"].isoformat(), "end_date": j["end"].isoformat(),
        }
        row = {"waktu_unduh": datetime.now().isoformat(timespec="seconds"), "endpoint": endpoint,
               "price_type_id": j["price_type_id"], "comcat_id": j["comcat_id"], "province_id": j["province_id"],
               "start_date": params["start_date"], "end_date": params["end_date"],
               "file": j["path"].relative_to(ROOT).as_posix()}
        t0 = time.monotonic()
        try:
            r = client.get(endpoint, params)
            write_atomic(j["path"], r.content)
            row.update(status="ok", http_status=r.status_code, bytes=len(r.content), **summarize_response(r.json()))
            n_ok += 1
        except Exception as e:  # dicatat, lalu lanjut ke file berikutnya
            row.update(status="error", error=str(e)[:300])
            n_err += 1
        row["detik"] = round(time.monotonic() - t0, 1)
        append_log(log_path, row)
        log.info("[%d/%d] %s pt%s %s %s -> %s (%s baris, %s s)", i, len(todo), row["status"], j["price_type_id"],
                 j["comcat_id"], params["start_date"][:7], j["path"].name, row.get("n_rows", "-"), row["detik"])

    log.info("Selesai: %d berhasil, %d gagal. Jalankan ulang untuk mencoba yang gagal.", n_ok, n_err)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="tampilkan rencana tanpa mengunduh")
    p.add_argument("--limit", type=int, help="batasi jumlah request (untuk uji coba)")
    p.add_argument("--pt", type=int, nargs="*", help="hanya jenis pasar ini (1-4)")
    p.add_argument("--com", nargs="*", help="hanya komoditas ini (mis. com_14)")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    run(p.parse_args())


if __name__ == "__main__":
    main()
