"""Memotret tiap sheet dashboard ke PNG lewat Excel (COM, pywin32) untuk README dan cek visual tata letak.

Cara kerja: rentang terpakai tiap sheet (termasuk grafik) disalin sebagai gambar (CopyPicture), ditempel ke grafik kosong,
lalu diekspor ke PNG; tepi kosong di bawah/kanan dipangkas. Tidak butuh printer (ekspor PDF Excel butuh printer).
Workbook disalin dulu ke folder keluaran, jadi file asli boleh sedang terbuka di Excel.

    python -m src.screenshot_excel                                   # excel/Dashboard_pangan.xlsx -> excel/screenshots/
    python -m src.screenshot_excel --xlsx X --out folder
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from src.analysis.common import ROOT
from src.audit_dashboard import SHEET_DASHBOARD

XLSX = ROOT / "excel" / "Dashboard_pangan.xlsx"
OUT = ROOT / "excel" / "screenshots"
LATAR = [(243, 245, 244), (255, 255, 255)]   # latar sheet (BG di build_excel) dan sel di luar area dashboard


def _coba(fn, n: int = 5):
    """Clipboard kadang sibuk sesaat; ulangi beberapa kali."""
    for i in range(n):
        try:
            return fn()
        except Exception:
            if i == n - 1:
                raise
            time.sleep(1)


def pangkas(path: Path, margin: int = 16) -> None:
    from PIL import Image, ImageChops

    im = Image.open(path).convert("RGB")
    topeng = None
    for warna in LATAR:   # piksel konten = berbeda dari SEMUA warna latar
        m = ImageChops.difference(im, Image.new("RGB", im.size, warna)).convert("L").point(lambda v: 255 if v > 12 else 0)
        topeng = m if topeng is None else ImageChops.multiply(topeng, m)
    box = topeng.getbbox()
    if box:
        im = im.crop((0, 0, min(im.width, box[2] + margin), min(im.height, box[3] + margin)))
    im.save(path, optimize=True)


def potret(xlsx: Path, out: Path) -> list[Path]:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    out.mkdir(parents=True, exist_ok=True)
    salinan = out / "_salinan.xlsx"
    shutil.copy(xlsx, salinan)
    hasil = []
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = True        # CopyPicture butuh jendela yang digambar
    xl.DisplayAlerts = False
    try:
        wb = xl.Workbooks.Open(str(salinan.resolve()), ReadOnly=True)
        for i, nama in enumerate(SHEET_DASHBOARD, 1):
            ws = wb.Worksheets(nama)
            ws.Activate()
            xl.ActiveWindow.Zoom = 100   # pada zoom lain CopyPicture menggambar bentuk (bingkai, tombol) sedikit bergeser dari sel
            ur = ws.UsedRange
            r1, c1 = ur.Row + ur.Rows.Count - 1, ur.Column + ur.Columns.Count - 1
            for co in ws.ChartObjects():
                r1, c1 = max(r1, co.BottomRightCell.Row), max(c1, co.BottomRightCell.Column)
            rng = ws.Range(ws.Cells(1, 1), ws.Cells(r1, c1))
            _coba(lambda: rng.CopyPicture(1, 2))   # xlScreen, xlBitmap
            co = ws.ChartObjects().Add(0, 0, rng.Width, rng.Height)
            co.Activate()
            _coba(lambda: co.Chart.Paste())
            f = out / f"{i:02d}_{nama.lower().replace(' ', '_')}.png"
            co.Chart.Export(str(f.resolve()))
            co.Delete()
            pangkas(f)
            hasil.append(f)
        wb.Close(SaveChanges=False)
    finally:
        xl.Quit()
        pythoncom.CoUninitialize()
        salinan.unlink(missing_ok=True)
    return hasil


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--xlsx", default=str(XLSX))
    p.add_argument("--out", default=str(OUT))
    a = p.parse_args()
    for f in potret(Path(a.xlsx), Path(a.out)):
        print(f"{f.name} ({f.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
