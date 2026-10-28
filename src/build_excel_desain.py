"""Tahap 6, versi desain: dashboard Excel yang mengikuti mockup "Dashboard Harga Pangan" (menu kiri gelap, kartu putih,
band Fakta dan Keputusan, peta Pulau Jawa).

Output: excel/Dashboard_pangan.xlsx (dashboard yang dipublikasikan). src/build_excel.py adalah versi klasik tanpa tata letak
desain; fungsinya dipakai ulang di sini. Data, sel input, dan 20 nama sel audit (kpi_*) sama dengan versi lama,
jadi src/audit_dashboard.py tetap berlaku.

Batasan Excel tanpa makro: pengali ongkos kirim dipilih lewat tombol pilihan Form Control (dipasang lewat Excel oleh
pasang_objek_excel; tanpa makro), komoditas di Gejolak harga lewat dropdown, tanpa slider, kartu bersudut siku. Peta = gambar latar (src/peta_jawa.py, Natural Earth) + grafik gelembung transparan dengan skala bujur/lintang
yang sama persis.

    python -m src.build_excel_desain            # tulis excel/Dashboard_pangan.xlsx
    python -m src.build_excel_desain --out X    # ke path lain (dipakai tes)
"""
from __future__ import annotations

import argparse
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.chart import AreaChart, BarChart, BubbleChart, LineChart, Reference, Series
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.series import SeriesLabel, StrRef
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.image import Image
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.text import CharacterProperties, Font as DFont, Paragraph, ParagraphProperties
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from src.analysis.common import KOMODITAS_URUT, LABEL_PENDEK, ROOT, load_cfg
from src.build_excel import BULAN, BULAN_SUMBU, PCT, RP, muat, nama, q, rp, sumbu_bulan, tabel_data
from src.peta_jawa import BINGKAI, gambar_peta

OUT = ROOT / "excel" / "Dashboard_pangan.xlsx"
FONT = "Arial"
# warna (mockup): teal = utama/untung, biru = turun/lebih murah, oranye = naik/peringatan
TEAL, TEAL_MUDA, HIJAU_MENU = "0B7A57", "DDF3E8", "1FA971"
ORANGE, ORANGE_TXT, ORANGE_MUDA, ORANGE_PUCAT = "EB6834", "C2410C", "FDE4D8", "F6B79B"
BLUE, GRAY, GRAY_MUDA, GARIS = "2A78D6", "B4BDB9", "EEF1F0", "E3E8E6"
INK, MUTED, DARK, DARK_KOTAK, HIJAU_BAND, SIDEBAR_SUB = "15201D", "6B7A75", "0F2A26", "1E3D37", "7FE0B5", "9FB8B1"
BG, WHITE, KUNING = "F3F5F4", "FFFFFF", "FFF3C4"
LATAR = "E6F2EC"       # panel hijau muda di belakang kartu (selaras dengan hijau menu); sudut bulat dibuat pasang_objek_excel
GARIS_KARTU = "CFE0D8"
RADIUS = 9             # radius sudut kartu & panel (pt)

# grid: A = menu kiri, B = jarak, C..Z = 24 kolom isi, AA = margin kanan, AC.. = kolom bantu tersembunyi
LEBAR_MENU, LEBAR_JARAK, LEBAR_KOL = 26, 2.5, 6.29
PX_KOL = int(LEBAR_KOL * 7)          # 44 px
TINGGI_BARIS = 20                    # pt (26,7 px)
PX_BARIS = TINGGI_BARIS * 4 / 3
N_BARIS = 44
EMU = 9525

MENU = [("ringkasan", "Ringkasan"), ("gejolak", "Gejolak harga"), ("rute", "Pindah stok"), ("peringatan", "Peringatan dini"),
        ("pola", "Pola musiman"), ("rantai", "Rantai pasok"), ("metode", "Catatan metode")]
NAMA_SHEET = dict(MENU)
LABEL_MENU = {"ringkasan": "Ringkasan", "gejolak": "Peta gejolak harga", "rute": "Peluang pindah stok", "peringatan": "Peringatan dini",
              "pola": "Pola musiman", "rantai": "Rantai pasok dan margin", "metode": "Catatan metode"}
# kota yang diberi label di peta + posisi label (t/b/l/r) agar tidak bertumpuk; kota lain tetap tampil sebagai gelembung
LABEL_PETA = {"Kota Jakarta Pusat": "t", "Kota Bandung": "b", "Kota Tegal": "t", "Kota Semarang": "t", "Kab. Cilacap": "b",
              "Kota Surakarta (Solo)": "b", "Kota Kediri": "l", "Kota Blitar": "b", "Kota Surabaya": "t", "Kab. Sumenep": "t",
              "Kab. Banyuwangi": "r", "Kab. Jember": "b"}
BULAN_PENUH = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
PENDEK = {"Cabai rawit merah": "Cabai rawit", "Cabai merah keriting": "Cabai keriting", "Bawang merah": "Bawang merah",
          "Bawang putih": "Bawang putih", "Daging ayam ras": "Daging ayam", "Telur ayam ras": "Telur"}


# ---------------------------------------------------------------- dasar
def kol(k: int) -> str:
    """Kolom isi ke-k (1..24) -> huruf kolom Excel (C..Z)."""
    return get_column_letter(2 + k)


def singkat(kota: str) -> str:
    return kota.replace("Kota ", "").replace("Kab. ", "").replace(" (Solo)", "")


def f_singkat(expr: str) -> str:
    return f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({expr},"Kota ",""),"Kab. ","")," (Solo)","")'


def angka_teks(expr: str, desimal: int = 0) -> str:
    """Rumus teks angka gaya Indonesia (titik ribuan, koma desimal), tidak bergantung bahasa Excel."""
    if desimal == 0:
        return f'SUBSTITUTE(FIXED({expr},0),",",".")'
    return f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(FIXED({expr},{desimal}),",","#"),".",","),"#",".")'


def desimal(x: float, n: int = 1) -> str:
    return f"{x:,.{n}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def persen(x: float, tanda: bool = False) -> str:
    s = f"{x:+.0%}" if tanda else f"{x:.0%}"
    return s.replace("-", "−") if tanda else s


def bersihkan(teks: str) -> str:
    """Ganti simbol pada kalimat otomatis (src/insights.py) dengan kata: '×1,5' -> '1,5 kali', '→' -> 'ke'."""
    import re
    teks = re.sub(r"×\s?(\d+(?:,\d+)?)", r"\1 kali", teks)
    teks = teks.replace(" → ", " ke ").replace("→", " ke ").replace("Kota ", "").replace("Kab. ", "").replace(" · ", ", ")
    return teks.replace("lebih murah daripada di ", "lebih murah daripada harga pasar di ")


def font(size=10, bold=False, color=INK, italic=False, underline=None) -> Font:
    return Font(name=FONT, size=size, bold=bold, color=color, italic=italic, underline=underline)


def isi(color: str) -> PatternFill:
    return PatternFill("solid", start_color=color, end_color=color)


_MIRIP_ANGKA = __import__("re").compile(r"^[+\-]?[\d.,]+%?$")
_RIBUAN = __import__("re").compile(r"^-?\d{1,3}(\.\d{3})+$")
_PERSEN = __import__("re").compile(r"^[+\-]?\d+%$")
FMT_RIBUAN = '[>=1000]#"."000;[<=-1000]-#"."000;0'   # 33675 -> 33.675 di Excel bahasa apa pun


def tulis(ws, k: int, r: int, value, size=10, bold=False, color=INK, wrap=False, align="left", valign="center", fmt=None,
          bg=None, k2: int | None = None, r2: int | None = None, indent: int = 2, italic=False):
    """Tulis ke sel isi (kolom ke-k, baris r), opsional digabung sampai (k2, r2)."""
    k2, r2 = k2 or k, r2 or r
    if bg:
        for rr in range(r, r2 + 1):
            for kk in range(k, k2 + 1):
                ws[f"{kol(kk)}{rr}"].fill = isi(bg)
    if (k2, r2) != (k, r):
        ws.merge_cells(f"{kol(k)}{r}:{kol(k2)}{r2}")
    c = ws[f"{kol(k)}{r}"]
    if isinstance(value, str) and _RIBUAN.match(value):
        value, fmt = int(value.replace(".", "")), FMT_RIBUAN
    elif isinstance(value, str) and _PERSEN.match(value):
        fmt = "+0%;-0%;0%" if value.startswith("+") else "0%"
        value = int(value.rstrip("%")) / 100
    elif isinstance(value, str) and _MIRIP_ANGKA.match(value):
        value = f'="{value}"'
    c.value = value
    c.font = font(size, bold, color, italic)
    c.alignment = Alignment(horizontal=align, vertical=valign, wrap_text=wrap, indent=indent if align == "left" else 0)
    if fmt:
        c.number_format = fmt
    return c


def kaya(*bagian: tuple[str, int, bool, str]) -> CellRichText:
    """Teks dengan beberapa gaya: (teks, ukuran, tebal, warna)."""
    return CellRichText(*[TextBlock(InlineFont(rFont=FONT, sz=sz, b=b, color=c), t) for t, sz, b, c in bagian])


class Halaman:
    """Satu sheet dashboard: kanvas, kartu, dan bingkai jarak antar kartu (dipasang terakhir, setelah semua sel digabung)."""

    def __init__(self, wb: Workbook, key: str, info: dict):
        self.ws = ws = wb.create_sheet(NAMA_SHEET[key])
        self.key, self.kartu_list, self.bingkai = key, [], []
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.sheet_view.zoomScale = 85
        ws.sheet_properties.tabColor = TEAL if key != "metode" else GRAY
        ws.column_dimensions["A"].width = LEBAR_MENU
        ws.column_dimensions["B"].width = LEBAR_JARAK
        for k in range(1, 25):
            ws.column_dimensions[kol(k)].width = LEBAR_KOL
        ws.column_dimensions["AA"].width = LEBAR_JARAK
        ws.row_dimensions[1].height = 8
        for r in range(2, N_BARIS + 1):
            ws.row_dimensions[r].height = TINGGI_BARIS
        ws.row_dimensions[2].height = ws.row_dimensions[3].height = 23
        for r in range(1, N_BARIS + 1):
            ws[f"A{r}"].fill = isi(DARK)
            for c in range(2, 28):
                ws.cell(r, c).fill = isi(LATAR)
        self._menu(info)
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    def _menu(self, info: dict) -> None:
        ws = self.ws
        ws["A2"].value, ws["A3"].value = "Harga Pangan", "Pengadaan, Pulau Jawa"
        ws["A2"].font, ws["A3"].font = font(13, True, WHITE), font(9, False, SIDEBAR_SUB)
        for a in ("A2", "A3"):
            ws[a].alignment = Alignment(indent=1, vertical="center")
        for i, (key, _) in enumerate(MENU):
            r = 5 + 2 * i
            ws.merge_cells(f"A{r}:A{r + 1}")
            c = ws[f"A{r}"]
            c.value = LABEL_MENU[key]
            c.hyperlink = f"#'{NAMA_SHEET[key]}'!A1"
            aktif = key == self.key
            c.font = font(10, aktif, WHITE)
            c.alignment = Alignment(indent=1, vertical="center")
            for rr in (r, r + 1):
                ws[f"A{rr}"].fill = isi(DARK)   # menu aktif = bentuk hijau bersudut bulat (pasang_objek_excel)
                ws[f"A{rr}"].border = Border(top=Side("thick", color=DARK) if rr == r else None,
                                             bottom=Side("thick", color=DARK) if rr == r + 1 else None)
        ws["A36"].value = f"Data per {info['tgl_data']}"
        ws["A37"].value = "PIHPS, Bank Indonesia"
        for a in ("A36", "A37"):
            ws[a].font = font(8, False, SIDEBAR_SUB)
            ws[a].alignment = Alignment(indent=1, vertical="center")

    def kartu(self, k0: int, r0: int, k1: int, r1: int, warna: str = WHITE, jarak: str = LATAR) -> None:
        for r in range(r0, r1 + 1):
            for k in range(k0, k1 + 1):
                self.ws[f"{kol(k)}{r}"].fill = isi(warna)
        self.kartu_list.append((k0, r0, k1, r1, jarak))
        if jarak == LATAR and r1 > r0:   # kartu utama & band (bukan kotak kecil di dalam kartu, bukan chip 1 baris)
            self.bingkai.append((k0, r0, k1, r1, warna == WHITE))

    def judul(self, formula_atau_teks, k1: int = 16) -> None:
        tulis(self.ws, 1, 2, formula_atau_teks, 14, True, INK, wrap=True, k2=k1, r2=3, indent=0, valign="top")

    def chip(self, k0: int, k1: int, r: int, teks, bg: str = GRAY_MUDA, color: str = INK, bold: bool = False, size: int = 9) -> None:
        tulis(self.ws, k0, r, teks, size, bold, color, align="center", bg=bg, k2=k1)
        self.kartu_list.append((k0, r, k1, r, LATAR))

    def pasang_bingkai(self) -> None:
        """Garis tebal warna latar di tepi tiap kartu = jarak antar kartu (Excel tidak punya kartu bersudut)."""
        ws = self.ws
        for k0, r0, k1, r1, warna in self.kartu_list:
            s = Side("thick", color=warna)
            for r in range(r0, r1 + 1):
                for k in range(k0, k1 + 1):
                    c = ws[f"{kol(k)}{r}"]
                    b = c.border
                    c.border = Border(left=s if k == k0 else b.left, right=s if k == k1 else b.right,
                                      top=s if r == r0 else b.top, bottom=s if r == r1 else b.bottom)

    def kpi(self, k0: int, k1: int, r0: int, label: str, nilai, satuan: str = "", sub=None, warna: str = INK, fmt=None,
            lebar_nilai: int = 2, bg: str = WHITE) -> str:
        """Kartu angka: label (r0), angka besar + satuan (r0+1..r0+2), keterangan (r0+3..r0+4). Mengembalikan sel angka."""
        ws = self.ws
        self.kartu(k0, r0, k1, r0 + 4, bg)
        tulis(ws, k0, r0, label.upper(), 8, True, MUTED, k2=k1, valign="bottom")
        kn = k0 + lebar_nilai - 1
        tulis(ws, k0, r0 + 1, nilai, 22, True, warna, fmt=fmt, k2=kn, r2=r0 + 2)
        if satuan:
            tulis(ws, kn + 1, r0 + 1, satuan, 10, False, MUTED, k2=k1, r2=r0 + 2, indent=1)
        if sub is not None:
            tulis(ws, k0, r0 + 3, sub, 8, False, MUTED, wrap=True, k2=k1, r2=r0 + 4, valign="top")
        return f"{kol(k0)}{r0 + 1}"

    def band(self, r0: int, butir: list[tuple[str, str]], catatan: str | None = None) -> None:
        """Band 'Fakta dan keputusan': 3 kotak, fakta di atas, keputusan bernomor di bawah."""
        ws = self.ws
        self.kartu(1, r0, 24, r0 + 6, DARK)
        for k in range(1, 25):   # garis tebal latar di baris atas band: tanpa ini 1 piksel warna band terlihat di atas tepinya
            c = ws[f"{kol(k)}{r0 - 1}"]
            c.border = Border(left=c.border.left, right=c.border.right, top=c.border.top, bottom=Side("thick", color=LATAR))
        tulis(ws, 1, r0 + 1, "FAKTA DAN KEPUTUSAN", 9, True, HIJAU_BAND, wrap=True, k2=2, r2=r0 + 5, indent=1)
        for i, (fakta, kep) in enumerate(butir):
            k0 = 3 + 7 * i   # kotak di kolom 3-9, 10-16, 17-23; kolom 24 = jarak kanan, sama rapi dengan tepi atas & bawah
            k1 = k0 + 6
            self.kartu(k0, r0 + 1, k1, r0 + 5, DARK_KOTAK, jarak=DARK)
            tulis(ws, k0, r0 + 1, kaya(("Fakta  ", 9, True, HIJAU_BAND), (fakta, 9, False, "DCE6E3")), wrap=True,
                  k2=k1, r2=r0 + 3, valign="top")
            tulis(ws, k0, r0 + 4, kaya((f"{i + 1}   ", 10, True, HIJAU_BAND), (kep, 10, True, WHITE)), wrap=True,
                  k2=k1, r2=r0 + 5, valign="top")
            for k in range(k0, k1 + 1):   # garis pemisah fakta dan keputusan
                ws[f"{kol(k)}{r0 + 3}"].border = Border(bottom=Side("thin", color="3C5A54"))
        if catatan:
            tulis(ws, 1, r0 + 7, catatan, 8, False, MUTED, k2=24, indent=0)

    def baris_tabel(self, r: int, k0: int, k1: int) -> None:
        for k in range(k0, k1 + 1):
            self.ws[f"{kol(k)}{r}"].border = Border(bottom=Side("thin", color=GARIS))

    def sel_bantu(self, r: int, formula, fmt=None) -> str:
        """Sel angka tersembunyi (kolom AC) untuk nama audit; angka yang sama tampil sebagai teks di kartu."""
        c = self.ws[f"AC{r}"]
        c.value = formula
        if fmt:
            c.number_format = fmt
        return f"$AC${r}"

    def sembunyikan_bantu(self, dari: int = 29, sampai: int = 60) -> None:
        for c in range(dari, sampai + 1):
            self.ws.column_dimensions[get_column_letter(c)].hidden = True


# ---------------------------------------------------------------- grafik
def cp(sz: int, color: str = MUTED, bold: bool = False) -> CharacterProperties:
    return CharacterProperties(sz=sz * 100, b=bold, solidFill=color, latin=DFont(typeface=FONT))


def teks_grafik(sz: int = 8, color: str = MUTED) -> RichText:
    return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp(sz, color)), endParaRPr=cp(sz, color))])


def polos(chart, sumbu_x: bool = True, sumbu_y: bool = True, grid: bool = True) -> None:
    """Grafik minimalis: tanpa bingkai & latar, tanpa judul (judul = sel di atasnya), sumbu kecil Arial, grid tipis."""
    chart.title = None
    chart.roundedCorners = False
    chart.graphical_properties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    chart.plot_area.graphicalProperties = GraphicalProperties(noFill=True)
    chart.visible_cells_only = False
    chart.legend = None
    for ax, tampil in ((chart.x_axis, sumbu_x), (chart.y_axis, sumbu_y)):
        ax.delete = not tampil
        ax.txPr = teks_grafik()
        ax.spPr = GraphicalProperties(ln=LineProperties(solidFill=GARIS))
        ax.majorGridlines = None
    if grid:
        chart.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="EDF0EF")))


def taruh(ws, obj, k: int, r: int, w_px: float, h_px: float, dx: float = 0, dy: float = 0) -> None:
    """Pasang grafik/gambar di kolom isi ke-k, baris r, dengan geser (px) dan ukuran (px) presisi."""
    obj.anchor = OneCellAnchor(_from=AnchorMarker(col=1 + k, colOff=int(dx * EMU), row=r - 1, rowOff=int(dy * EMU)),
                               ext=XDRPositiveSize2D(int(w_px * EMU), int(h_px * EMU)))
    (ws.add_image if isinstance(obj, Image) else ws.add_chart)(obj)


def garis(s, warna: str, tebal: int = 22000, putus: bool = False) -> None:
    s.smooth = False
    s.graphicalProperties.line.solidFill = warna
    s.graphicalProperties.line.width = tebal
    if putus:
        s.graphicalProperties.line.dashStyle = "dash"
    s.marker.symbol = "none"


# ---------------------------------------------------------------- build
def _rgb(hex6: str) -> int:
    """Warna hex 'RRGGBB' -> angka warna COM Excel (urutan BGR)."""
    r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
    return r + g * 256 + b * 65536


def _potong_sudut(ws, x: float, y: float, r: float, pojok: str, warna: str, nama: str):
    """Shape kecil = area antara sudut persegi dan seperempat lingkaran, diwarnai seperti latar di luarnya.
    Ditaruh di pojok kartu berwarna sel, sehingga kartu tampak bersudut bulat tanpa menutupi isinya (pojok selalu kosong)."""
    k = 0.5523   # titik kendali Bezier untuk seperempat lingkaran
    sx, sy = {"tl": (1, 1), "tr": (-1, 1), "bl": (1, -1), "br": (-1, -1)}[pojok]
    fb = ws.Shapes.BuildFreeform(0, x, y)
    fb.AddNodes(0, 0, x + sx * r, y)
    fb.AddNodes(1, 1, x + sx * r * (1 - k), y, x, y + sy * r * (1 - k), x, y + sy * r)
    fb.AddNodes(0, 0, x, y)
    sh = fb.ConvertToShape()
    sh.Fill.ForeColor.RGB = _rgb(warna)
    sh.Line.Visible = 0
    sh.Shadow.Visible = 0
    sh.Placement = 1
    sh.Name = nama
    return sh


def pasang_objek_excel(path: Path, rancangan: dict) -> bool:
    """Lewat Excel (COM, Windows), pasang yang tidak bisa dibuat openpyxl:
    1. garis tepi bersudut bulat di setiap kartu utama (tanpa isian, jadi isi sel tetap terlihat dan bisa diklik);
    2. menu aktif sebagai persegi panjang hijau bersudut bulat, menjorok dari tepi menu;
    3. 4 tombol pilihan (Form Control) pengali ongkos di sheet Pindah stok; memilihnya menulis nomor 1-4 ke sel AC9.
    Semuanya tanpa makro. Mengembalikan False bila Excel/pywin32 tidak ada (dashboard tetap jalan, tanpa bentuk & tombol)."""
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError:
        print("PERINGATAN: pywin32 tidak ada; bingkai, menu bulat, dan tombol pengali ongkos tidak dipasang.")
        return False
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    try:
        wb = xl.Workbooks.Open(str(path.resolve()))
        for nama_sheet, r in rancangan.items():
            ws = wb.Worksheets(nama_sheet)
            # panel hijau muda (sel B1:AA{N}) bersudut bulat: kiri menempel menu gelap, kanan & bawah latar putih
            a, b = ws.Range(f"B1"), ws.Range(f"AA{N_BARIS}")
            x0, y0, x1, y1 = a.Left, a.Top, b.Left + b.Width, b.Top + b.Height
            for pj, px, py, wr in (("tl", x0, y0, DARK), ("bl", x0, y1, DARK), ("tr", x1, y0, WHITE), ("br", x1, y1, WHITE)):
                _potong_sudut(ws, px, py, RADIUS * 1.5, pj, wr, f"panel_{pj}")
            for k0, r0, k1, r1, garis in r["bingkai"]:
                a, b = ws.Range(f"{kol(k0)}{r0}"), ws.Range(f"{kol(k1)}{r1}")
                x, y = a.Left + 2, a.Top + 2
                w, h = b.Left + b.Width - a.Left - 4, b.Top + b.Height - a.Top - 4
                rad = min(RADIUS, w / 2, h / 2)
                # potongan mulai dari pojok sel (menutupi sisa warna kartu di tepi sel); radius +2 pt = busur sepusat dengan garis tepi
                cx0, cy0, cx1, cy1 = a.Left, a.Top, b.Left + b.Width, b.Top + b.Height
                for pj, px, py in (("tl", cx0, cy0), ("tr", cx1, cy0), ("bl", cx0, cy1), ("br", cx1, cy1)):
                    _potong_sudut(ws, px, py, rad + 2, pj, LATAR, f"sudut_{k0}_{r0}_{pj}")
                if garis:   # kartu putih diberi garis tepi tipis
                    sh = ws.Shapes.AddShape(5, x, y, w, h)   # 5 = rounded rectangle
                    sh.Fill.Visible = 0
                    sh.Line.ForeColor.RGB = _rgb(GARIS_KARTU)
                    sh.Line.Weight = 1
                    sh.Adjustments.SetItem(1, rad / min(w, h))
                    sh.Shadow.Visible = 0
                    sh.Placement = 1
                    sh.Name = f"bingkai_{k0}_{r0}"
            if r.get("menu"):
                baris, label = r["menu"]
                m = ws.Range(f"A{baris}:A{baris + 1}")
                sh = ws.Shapes.AddShape(5, m.Left + 6, m.Top + 4, m.Width - 12, m.Height - 8)
                sh.Fill.ForeColor.RGB = _rgb(HIJAU_MENU)
                sh.Line.Visible = 0
                sh.Shadow.Visible = 0
                sh.Adjustments.SetItem(1, 0.25)
                tf = sh.TextFrame2
                tf.VerticalAnchor = 3          # tengah
                tf.MarginLeft, tf.MarginRight = 7, 2
                tf.WordWrap = 0
                tr = tf.TextRange
                tr.Text = label
                tr.ParagraphFormat.Alignment = 1   # kiri
                tr.Font.Name, tr.Font.Size, tr.Font.Bold = FONT, (10 if len(label) <= 20 else 9), 1
                tr.Font.Fill.ForeColor.RGB = _rgb(WHITE)
                sh.Placement = 1
                sh.Name = "menu_aktif"
        ws = wb.Worksheets(NAMA_SHEET["rute"])
        awal = int(ws.Range("AC9").Value)
        for j, t in enumerate(["0,5x", "1x", "1,5x", "2x"]):
            c = ws.Range(f"{kol(21 + j)}2")
            ob = ws.OptionButtons().Add(c.Left + 3, c.Top + 1, c.Width - 4, c.Height - 2)
            ob.Caption = t
            ob.LinkedCell = "$AC$9"
            ob.Placement = 2   # ikut bergeser dengan sel, ukuran tetap
            ob.PrintObject = False
            if j + 1 == awal:
                ob.Value = 1   # xlOn
        wb.Save()
        wb.Close(SaveChanges=False)
    finally:
        xl.Quit()
        pythoncom.CoUninitialize()
    return True


def build(out: Path = OUT, tombol: bool = False) -> Path:
    cfg, lcfg = load_cfg()
    T = muat()
    kom, kota, rute = T["dim_komoditas"], T["dim_kota"], T["dim_rute"]
    info_t = T["dim_info"].set_index("kunci").nilai
    akhir = int(T["fact_harga_mingguan"].minggu_key.max())
    m_akhir = pd.to_datetime(str(akhir), format="%Y%m%d")
    m_awal = m_akhir - pd.Timedelta(days=4)
    label_minggu = f"Minggu {m_awal.day}-{m_akhir.day} {BULAN[m_akhir.month - 1]} {m_akhir.year}"
    tgl = lambda s: (lambda d: f"{d.day} {BULAN[d.month - 1]} {d.year}")(pd.to_datetime(s))   # noqa: E731
    info = {"tgl_data": tgl(info_t["data_terakhir"]), "tgl_ambil": tgl(info_t["tanggal_pengambilan"])}
    kons = lcfg["sensitivitas"]["skenario_konservatif"]
    kons_t = desimal(kons, 1).rstrip("0").rstrip(",")
    urut_kom = [LABEL_PENDEK[k] for k in KOMODITAS_URUT]
    nama_kota = kota.set_index("kota_key").kota
    tujuan_keys = list(cfg["wilayah"]["kota_tujuan"])
    sumber_keys = list(cfg["wilayah"]["kota_sumber"])
    operasional = [nama_kota[k] for k in tujuan_keys + sumber_keys]
    kom_idx = kom.set_index("nama_dashboard")

    wb = Workbook()
    wb.remove(wb.active)
    H = {key: Halaman(wb, key, info) for key, _ in MENU}

    # ---------- sheet data (sama dengan versi lama + kolom tampilan)
    d_kom = kom[["komoditas_key", "nama_dashboard", "satuan", "peringkat_gejolak", "rata_perubahan_per_minggu", "gejolak_mingguan_median",
                 "idulfitri_mulai_naik_minggu", "idulfitri_kenaikan_minggu_min1", "idulfitri_tahun_konsisten", "idulfitri_puncak_minggu",
                 "idulfitri_puncak_kenaikan", "hemat_beli_produsen_pct", "hemat_beli_pedagang_besar_pct", "modern_vs_tradisional_pct"]].copy()
    d_kom = d_kom.set_index("nama_dashboard").loc[urut_kom].reset_index()
    R_kom = tabel_data(wb, "d_komoditas", d_kom, "d_komoditas", {c: PCT for c in d_kom.columns if c.endswith("_pct") or c in
                       ("rata_perubahan_per_minggu", "gejolak_mingguan_median", "idulfitri_kenaikan_minggu_min1", "idulfitri_puncak_kenaikan")})
    R_kota = tabel_data(wb, "d_kota", kota[["kota_key", "kota", "provinsi", "lat", "lon", "peran", "komoditas_sumber", "penentu_arah_untuk"]], "d_kota")
    g = T["fact_gejolak"][["kota", "komoditas", "gejolak_mingguan", "rata_perubahan_per_minggu", "peringkat_dalam_komoditas"]]
    R_gej = tabel_data(wb, "d_gejolak", g, "d_gejolak", {"gejolak_mingguan": "0.0%", "rata_perubahan_per_minggu": PCT})
    d_rute = rute[["rute_key", "nama_rute", "komoditas_key", "kota_sumber_key", "kota_tujuan_key", "jarak_jalan_km", "median_selisih_harga_rp_per_kg",
                   "ongkos_angkut_rp_per_kg", "susut_pct", "median_ongkos_rp_per_kg", "median_untung_rp_per_kg", "porsi_minggu_untung",
                   "minggu_untung_dari_10", "rata_bertahan_minggu", "minggu_untung_berturut_terakhir", "layak", "layak_jika_jual_ke_pedagang_besar",
                   "median_untung_jual_ke_pedagang_besar", "status"]].copy()
    nk = kom.set_index("komoditas_key").nama_dashboard
    d_rute["nama_pendek"] = [f"{PENDEK[nk[a]]}, {singkat(nama_kota[b])} ke {singkat(nama_kota[c])}"
                             for a, b, c in zip(d_rute.komoditas_key, d_rute.kota_sumber_key, d_rute.kota_tujuan_key)]
    d_rute["risiko"] = d_rute.apply(lambda r: "aman" if r.layak and r.layak_jika_jual_ke_pedagang_besar else ("hanya eceran" if r.layak else "tidak layak"), axis=1)
    # ongkos dasar (ongkos angkut + susut, pengali 1) per rute, dan uji: tetap aman pada ongkos 2 kali bila dijual ke pedagang besar
    hm = T["fact_harga_mingguan"]
    pbt = hm[hm.jenis_pasar_key == 3][["kota_key", "komoditas_key", "minggu_key", "harga"]].rename(columns={"kota_key": "kota_tujuan_key", "harga": "harga_pb_tujuan"})
    spx = (T["fact_spread"].merge(d_rute[["rute_key", "kota_tujuan_key", "komoditas_key"]], on="rute_key")
           .merge(pbt, on=["kota_tujuan_key", "komoditas_key", "minggu_key"], how="left"))
    spx["biaya_dasar"] = spx.ongkos_angkut + spx.susut_rp
    d_rute["median_ongkos_dasar"] = d_rute.rute_key.map(spx.groupby("rute_key").biaya_dasar.median())
    # tahan ongkos 2 kali bila dijual ke pedagang besar: hasil analisis Q2 (src/analysis/spread.py, reports/q2_rute.md)
    d_rute["aman_ongkos_2x"] = (d_rute.risiko == "aman") & d_rute.rute_key.map(rute.set_index("rute_key").tahan_ongkos_maks_jual_ke_pedagang_besar).astype(bool)
    n_tahan = int(d_rute.aman_ongkos_2x.sum())
    R_rute = tabel_data(wb, "d_rute", d_rute, "d_rute", {"porsi_minggu_untung": PCT})
    sens = T["fact_rute_sensitivitas"].copy()
    R_sens = tabel_data(wb, "d_sensitivitas", sens, "d_sensitivitas", {"porsi_minggu_untung": PCT})
    sp = T["fact_spread"][["rute_key", "minggu_key", "harga_sumber", "harga_tujuan", "selisih_harga", "ongkos_angkut", "susut_rp"]].copy()
    sp["minggu"] = pd.to_datetime(sp.minggu_key.astype(str), format="%Y%m%d")
    sp["kunci"] = sp.rute_key.astype(str) + "|" + sp.minggu_key.astype(str)
    R_sp = tabel_data(wb, "d_spread", sp, "d_spread", {"minggu": "yyyy-mm-dd"})
    uji = T["fact_uji_peringatan"].sort_values("urutan")
    R_uji = tabel_data(wb, "d_uji_peringatan", uji[["urutan", "aturan", "benar_dari_10", "tertangkap_dari_10", "lebih_awal_minggu", "porsi_minggu_peringatan",
                                                   "jumlah_peringatan", "jumlah_lonjakan"]], "d_uji_peringatan", {"porsi_minggu_peringatan": PCT})
    al = T["fact_alert"]
    al = al[(al.kota_key == 34) & (al.komoditas_key == 16) & al.harga.notna()].sort_values("minggu_key").reset_index(drop=True)
    puncak = float(al.harga.max()) * 1.08
    dj = pd.DataFrame({"minggu": pd.to_datetime(al.minggu_key.astype(str), format="%Y%m%d"), "harga": al.harga,
                       "harga_saat_peringatan": al.harga.where(al.peringatan.astype(bool)),
                       "masa_lonjakan": [puncak if bool(x) else 0 for x in al.masa_lonjakan.fillna(False)],
                       "awal_lonjakan": al.awal_lonjakan.fillna(False).astype(bool), "alasan": al.alasan})
    tabel_data(wb, "d_peringatan_jakarta", dj, "d_peringatan_jakarta", {"minggu": "yyyy-mm-dd", "harga": "#,##0", "harga_saat_peringatan": "#,##0", "masa_lonjakan": "#,##0"})
    pi = T["fact_pola_idul_fitri"]
    mulai_map = d_kom.set_index("nama_dashboard").idulfitri_mulai_naik_minggu
    pola_rows = []
    for k in urut_kom:
        tb = pi[pi.komoditas == k].pivot(index="minggu_ke_idul_fitri", columns="tahun_idul_fitri", values="kenaikan_vs_harga_normal").reindex(range(-8, 5))
        mulai = mulai_map[k]
        for m in tb.index:
            lo, hi = tb.loc[m].min(), tb.loc[m].max()
            pola_rows.append({"komoditas": k, "minggu_ke_lebaran": int(m), "rata_rata": tb.loc[m].mean(), "terendah": lo, "tertinggi": hi,
                              "rentang": hi - lo if pd.notna(hi) else None,
                              "masa_kenaikan": 1 if pd.notna(mulai) and int(mulai) <= m <= -1 else 0,
                              **{f"th_{int(c)}": tb.loc[m, c] for c in tb.columns}})
    pola = pd.DataFrame(pola_rows)
    tabel_data(wb, "d_pola_lebaran", pola, "d_pola_lebaran", {c: PCT for c in pola.columns if c not in ("komoditas", "minggu_ke_lebaran", "masa_kenaikan")})
    m = T["fact_margin"]
    m = m.assign(urut=m.komoditas.map({k: i for i, k in enumerate(urut_kom)})).sort_values(["urut", "hemat_beli_produsen_pct"], ascending=[True, False])
    tabel_data(wb, "d_margin", m[["komoditas", "kota", "cakupan", "harga_produsen_dari", "n_bulan", "harga_produsen", "harga_pedagang_besar", "harga_pasar",
                                  "tambahan_di_pedagang_besar_pct", "tambahan_di_pasar_pct", "hemat_beli_produsen_pct", "hemat_beli_pedagang_besar_pct",
                                  "porsi_bulan_produsen_lebih_mahal"]], "d_margin", {"harga_produsen": RP, "harga_pedagang_besar": RP, "harga_pasar": RP})
    mk = (m.groupby("komoditas").agg(kota=("kota", "size"), harga_produsen=("harga_produsen", "median"), harga_pedagang_besar=("harga_pedagang_besar", "median"),
                                     harga_pasar=("harga_pasar", "median"), margin_pedagang_besar=("tambahan_di_pedagang_besar_pct", "median"),
                                     margin_pasar=("tambahan_di_pasar_pct", "median"), hemat_produsen=("hemat_beli_produsen_pct", "median"),
                                     hemat_pedagang_besar=("hemat_beli_pedagang_besar_pct", "median"),
                                     produsen_usang=("porsi_bulan_produsen_lebih_mahal", "median"))
          .reindex([k for k in urut_kom if k != "Bawang putih"]).reset_index())
    mk["tambahan_pedagang_besar_rp"] = mk.harga_pedagang_besar - mk.harga_produsen
    mk["tambahan_pasar_rp"] = mk.harga_pasar - mk.harga_pedagang_besar
    mk["modern_vs_tradisional"] = mk.komoditas.map(kom_idx.modern_vs_tradisional_pct)
    mk["label"] = mk.komoditas.map(PENDEK)
    mk["hemat_vs_pb"] = mk.komoditas.map(kom_idx.hemat_produsen_vs_pedagang_besar_pct)   # hasil analisis Q5 (reports/q5_margin.md)
    R_mk = tabel_data(wb, "d_margin_komoditas", mk, "d_margin_komoditas", {"margin_pedagang_besar": PCT, "margin_pasar": PCT, "hemat_produsen": PCT,
                      "hemat_pedagang_besar": PCT, "modern_vs_tradisional": "+0%;-0%;0%", "hemat_vs_pb": PCT})
    tind = T["fact_tindakan"].sort_values(["komoditas_key", "prioritas"])
    tabel_data(wb, "d_tindakan_semua", tind[["komoditas", "prioritas", "tindakan", "alasan_singkat", "nilai", "satuan", "pembanding", "sumber"]], "d_tindakan_semua")
    w = T["fact_harga_mingguan"]
    wt = w[(w.jenis_pasar_key == 1) & w.kota_key.isin(tujuan_keys)]
    ht = wt.groupby(["komoditas", "minggu_key"]).agg(harga_kota_tujuan=("harga", "median"), harga_nasional=("harga_nasional", "median"),
                                                     perubahan_4m=("perubahan_4m", "median")).reset_index()
    ht["minggu"] = pd.to_datetime(ht.minggu_key.astype(str), format="%Y%m%d")
    ht["selisih_vs_nasional"] = ht.harga_kota_tujuan / ht.harga_nasional - 1
    ht = ht[["komoditas", "minggu_key", "minggu", "harga_kota_tujuan", "harga_nasional", "selisih_vs_nasional", "perubahan_4m"]]
    R_ht = tabel_data(wb, "d_harga_tujuan", ht, "d_harga_tujuan", {"minggu": "yyyy-mm-dd", "harga_kota_tujuan": "#,##0", "harga_nasional": "#,##0", "selisih_vs_nasional": PCT, "perubahan_4m": PCT})
    cari_ht = lambda kk, kolom: f"INDEX({R_ht[kolom]},MATCH(\"{kk}|{akhir}\",INDEX({R_ht['komoditas']}&\"|\"&{R_ht['minggu_key']},0),0))"   # noqa: E731
    uji_i = uji.set_index("urutan")

    # ================================================================ RINGKASAN
    h = H["ringkasan"]; ws = h.ws; RS = q(NAMA_SHEET["ringkasan"])
    ht_akhir = ht[ht.minggu_key == akhir].set_index("komoditas")
    tercepat = ht_akhir.perubahan_4m.idxmax()
    n_layak, n_aman = int(rute.layak.sum()), int((rute.layak & rute.layak_jika_jual_ke_pedagang_besar).sum())
    sp_akhir = sp[sp.minggu_key == akhir]
    untung_minggu_ini = int(((sp_akhir.selisih_harga - (sp_akhir.ongkos_angkut + sp_akhir.susut_rp) * kons) > 0).sum())
    al_semua = T["fact_alert"]
    n_peringatan = int(al_semua[(al_semua.minggu_key == al_semua.minggu_key.max()) & al_semua.peringatan].kota_key.nunique())
    benar_bulat = int(round(uji_i.loc[1, "benar_dari_10"]))
    h.judul(f'=IF(kpi_beli_awal=0,"Minggu ini belum ada komoditas yang perlu dibeli lebih awal; ","Minggu ini "&kpi_beli_awal&" komoditas perlu dibeli lebih awal; ")&kpi_rute_untung&" rute pindah stok masih memberi margin"')
    h.chip(17, 21, 2, label_minggu, TEAL_MUDA, TEAL, True)
    h.chip(22, 24, 2, "Pasar tradisional")
    nama(wb, "kpi_beli_awal", f"{RS}!${kol(1)}$6")
    h.kpi(1, 6, 5, "Perlu dibeli lebih awal", f'=COUNTIF({q("d_tindakan_semua")}!$C$2:$C$200,"Amankan stok*")+COUNTIF({q("d_tindakan_semua")}!$C$2:$C$200,"Beli lebih awal*")',
          "komoditas", "Lebaran masih jauh; kenaikan musiman belum mulai." if not tind.beli_lebih_awal.any() else "Sudah masuk masa menjelang Lebaran.", fmt="0")
    nama(wb, "kpi_rute_untung", f"{RS}!${kol(7)}$6")
    h.kpi(7, 12, 5, "Rute pindah stok yang untung", f"=COUNTIF({R_rute['layak']},TRUE)", "dari 32",
          f"{n_aman} rute aman pada ongkos {kons_t} kali, {n_tahan} tetap aman pada 2 kali. {untung_minggu_ini} rute untung minggu ini.", TEAL, "0")
    nama(wb, "kpi_kenaikan_tercepat", f"{RS}!${kol(13)}$6")
    h.kpi(13, 18, 5, "Kenaikan tercepat", f"={cari_ht(tercepat, 'perubahan_4m')}", PENDEK[tercepat].lower(),
          f"Dibanding 4 minggu lalu; sekarang Rp {rp(ht_akhir.loc[tercepat, 'harga_kota_tujuan'])}/kg di kota tujuan.", ORANGE_TXT, "+0%;-0%;0%", lebar_nilai=3)
    nama(wb, "kpi_peringatan_aktif", f"{RS}!${kol(19)}$6")
    h.kpi(19, 24, 5, "Peringatan dini aktif", n_peringatan, "kota", f"Sistem ini baru benar {benar_bulat} dari 10 kali, belum bisa diandalkan.", fmt="0")
    # saran per komoditas
    h.kartu(1, 10, 14, 19)
    tulis(ws, 1, 11, "Yang kami sarankan untuk tiap komoditas", 11, True, k2=14)
    for k0, k1, t in ((1, 4, "Komoditas"), (5, 11, "Saran"), (12, 14, "Angka minggu ini")):
        tulis(ws, k0, 12, t, 8, True, MUTED, k2=k1)
    h.baris_tabel(12, 1, 14)
    rute_by_key = d_rute.set_index("rute_key")
    for i, kk in enumerate(urut_kom):
        r = 13 + i
        rows = tind[tind.komoditas == kk].sort_values("prioritas")
        pindah = rows[rows.pindah_stok.astype(bool)]
        naik = rows[rows.tindakan.str.startswith("Pantau ketat")]
        awal = rows[rows.beli_lebih_awal.astype(bool)]
        aman = bool(len(pindah)) and bool(rute_by_key.loc[int(pindah.iloc[0].rute_key), "layak_jika_jual_ke_pedagang_besar"])
        if len(awal):
            pil, detail, dampak, bgp, fgp, fgd = "Amankan stok", "menjelang Lebaran", "kenaikan musiman", ORANGE_MUDA, ORANGE_TXT, ORANGE_TXT
        elif len(pindah) and (aman or not len(naik)):
            r_ = rute_by_key.loc[int(pindah.iloc[0].rute_key)]
            pil = "Pindahkan stok" if aman else "Pindahkan, jual eceran"
            bgp, fgp = (TEAL_MUDA, TEAL) if aman else (GRAY_MUDA, INK)
            detail = f"{singkat(nama_kota[r_.kota_sumber_key])} ke {singkat(nama_kota[r_.kota_tujuan_key])}"
            dampak, fgd = f"+Rp {rp(pindah.iloc[0].nilai)}/kg", TEAL
        elif len(naik):
            pil, bgp, fgp, detail = "Beli secukupnya", ORANGE_MUDA, ORANGE_TXT, "harga sedang naik"
            dampak, fgd = f"{persen(naik.iloc[0].nilai, True)} (4 minggu)", ORANGE_TXT
        else:
            t0 = rows.iloc[0]
            pil, bgp, fgp, detail = "Beli rutin", GRAY_MUDA, INK, "tidak ada sinyal khusus"
            dampak, fgd = (f"{persen(abs(t0.nilai))} {'di atas' if t0.nilai >= 0 else 'di bawah'} nasional", INK) if "nasional" in str(t0.satuan) else ("", INK)
        tulis(ws, 1, r, kk, 10, True, k2=4)
        tulis(ws, 5, r, pil, 8, True, fgp, align="center", bg=bgp, k2=7)
        h.kartu_list.append((5, r, 7, r, WHITE))   # tepi putih = label tampak seperti pil
        tulis(ws, 8, r, detail, 9, False, INK, k2=11)
        tulis(ws, 12, r, dampak, 10, True, fgd, k2=14, indent=0)
        h.baris_tabel(r, 1, 14)
    contoh = rute_by_key.loc[int(tind[tind.pindah_stok.astype(bool)].merge(d_rute[d_rute.risiko == "aman"][["rute_key"]], on="rute_key").sort_values("nilai").iloc[-1].rute_key)]
    tulis(ws, 1, 19, f"Untung dihitung dengan harga pasar; bila dijual ke pedagang besar jauh lebih kecil "
                     f"({contoh.nama_pendek.split(', ', 1)[1]}: Rp {rp(contoh.median_untung_jual_ke_pedagang_besar)}/kg).", 7, False, MUTED, k2=14, valign="top")
    # tiga hal yang perlu diketahui (kalimat dari src/insights.py, simbol diganti kata)
    h.kartu(1, 20, 14, 26)
    tulis(ws, 1, 20, "Tiga hal yang perlu diketahui minggu ini", 11, True, k2=14, valign="bottom")
    for i, kal in enumerate(T["fact_hal"].sort_values("urutan").kalimat.head(3)):
        # 3 kalimat x 2 baris = baris 21-26, tetap di dalam kartu (baris 27 sudah band keputusan)
        tulis(ws, 1, 21 + 2 * i, f"{i + 1}. {bersihkan(kal)}", 9, False, INK, wrap=True, k2=14, r2=22 + 2 * i, valign="top")
    # grafik harga kota tujuan vs nasional
    h.kartu(15, 10, 24, 26)
    sel_sel = h.sel_bantu(6, f"={cari_ht('Cabai rawit merah', 'selisih_vs_nasional')}", "+0%;-0%;0%")
    nama(wb, "kpi_selisih_nasional_rawit", f"{RS}!{sel_sel}")
    tulis(ws, 15, 11, f'="Harga cabai rawit di kota tujuan kita "&TEXT(ABS({sel_sel}),"0%")&IF({sel_sel}<0," lebih murah"," lebih mahal")&" daripada rata-rata nasional"',
          11, True, wrap=True, k2=24, r2=12, valign="top")
    tulis(ws, 15, 13, kaya(("Ribu rupiah per kg, 52 minggu terakhir:  ", 8, False, MUTED), ("kota tujuan", 8, True, TEAL), ("  dan  ", 8, False, MUTED),
                           ("nasional", 8, True, "8A9691")), k2=24)
    sub_ht = ht[ht.komoditas == "Cabai rawit merah"].tail(52)
    i0, i1 = ht.index.get_loc(sub_ht.index[0]) + 2, ht.index.get_loc(sub_ht.index[-1]) + 2
    wsd = wb["d_harga_tujuan"]
    ch = LineChart()
    ch.add_data(Reference(wsd, min_col=4, min_row=i0, max_col=5, max_row=i1), titles_from_data=False)
    ch.set_categories(Reference(wsd, min_col=3, min_row=i0, max_row=i1))
    garis(ch.series[0], TEAL, 26000); garis(ch.series[1], GRAY, 18000)
    sumbu_bulan(ch, tiap=3)
    polos(ch)
    ch.y_axis.numFmt = '#,##0,"rb"'
    taruh(ws, ch, 15, 14, 10 * PX_KOL - 12, 8 * PX_BARIS, dx=4)
    for j, (k0, k1, lab, f_) in enumerate([(15, 17, "Kota tujuan", f'="Rp "&{angka_teks(cari_ht("Cabai rawit merah", "harga_kota_tujuan"))}'),
                                           (18, 20, "Nasional", f'="Rp "&{angka_teks(cari_ht("Cabai rawit merah", "harga_nasional"))}'),
                                           (21, 24, "Dibanding 4 minggu lalu", f'=TEXT({cari_ht("Cabai rawit merah", "perubahan_4m")},"+0%;-0%;0%")')]):
        h.kartu(k0, 22, k1, 25, BG, jarak=WHITE)
        tulis(ws, k0, 22, lab.upper(), 7, True, MUTED, k2=k1, valign="bottom", wrap=True)
        tulis(ws, k0, 23, f_, 13, True, INK, k2=k1, r2=24)
    # keputusan dari data minggu ini: amankan stok -> pindah stok (rute aman dulu) -> harga naik cepat
    kep = []
    for t_ in tind[tind.beli_lebih_awal.astype(bool)].itertuples():
        alasan = bersihkan(t_.alasan_singkat.split(": ", 1)[-1])
        kep.append((alasan[:1].upper() + alasan[1:] + ".", f"{t_.tindakan}: {PENDEK[t_.komoditas].lower()}."))
    pin = tind[tind.pindah_stok.astype(bool)].merge(rute[["rute_key", "layak_jika_jual_ke_pedagang_besar", "minggu_untung_berturut_terakhir", "kota_sumber_key", "kota_tujuan_key",
                                                         "median_untung_jual_ke_pedagang_besar"]], on="rute_key")
    pin = pin.sort_values(["layak_jika_jual_ke_pedagang_besar", "nilai"], ascending=False)
    for t_ in pin.head(2).itertuples():
        a, b, kk = singkat(nama_kota[t_.kota_sumber_key]), singkat(nama_kota[t_.kota_tujuan_key]), PENDEK[t_.komoditas]
        fakta = (f"{kk} di {a} Rp {rp(t_.nilai)}/kg lebih murah daripada harga pasar di {b} setelah ongkos kirim, "
                 f"{int(t_.minggu_untung_berturut_terakhir)} minggu berturut-turut. "
                 + (f"Bila dijual ke pedagang besar, untung tipikalnya Rp {rp(t_.median_untung_jual_ke_pedagang_besar)}/kg."
                    if t_.layak_jika_jual_ke_pedagang_besar else "Hanya untung jika dijual eceran."))
        kep.append((fakta, f"Pindahkan stok {kk.lower()} dari {a} ke {b} minggu ini."))
    naik = ht_akhir.loc[tercepat, "perubahan_4m"]
    if naik >= cfg["insights"]["ambang_naik_4_minggu"]:
        kep.append((f"Harga {PENDEK[tercepat].lower()} naik {naik:.0%} dalam 4 minggu, sekarang Rp {rp(ht_akhir.loc[tercepat, 'harga_kota_tujuan'])}/kg.",
                    f"Beli {PENDEK[tercepat].lower()} secukupnya dulu; tunda pembelian dalam jumlah besar."))
    else:
        kep.append((f"Kenaikan 4 minggu tertinggi hanya {naik:.0%} ({PENDEK[tercepat].lower()}).", "Lanjutkan pembelian dengan pola rutin."))
    h.band(27, kep[:3], f"Ongkos kirim adalah perkiraan kami, bukan tarif aktual. Harga di pasar belum tentu harga jual kita. "
                        f"Data PIHPS Bank Indonesia, diambil {info['tgl_ambil']}.")

    # ================================================================ GEJOLAK HARGA
    h = H["gejolak"]; ws = h.ws; GJ = q(NAMA_SHEET["gejolak"])
    kota_all = sorted(g.kota.unique())
    n_k = len(kota_all)
    rA, rZ = 12, 12 + n_k - 1
    tulis(ws, 17, 2, "Komoditas:", 9, True, MUTED, align="right", k2=18)
    tulis(ws, 19, 2, "Cabai rawit merah", 10, True, INK, bg=KUNING, k2=24)
    tulis(ws, 17, 3, "Ganti komoditas lewat daftar di sel kuning.", 8, False, MUTED, align="right", k2=24)
    dv = DataValidation(type="list", formula1=f"={R_kom['nama_dashboard']}", allow_blank=False)
    ws.add_data_validation(dv); dv.add(f"{kol(19)}2")
    nama(wb, "pilih_komoditas", f"{GJ}!${kol(19)}$2")
    # bantu semua kota (AD..AH): kota | nilai | pengurut | kota urut | nilai urut
    for i, k in enumerate(kota_all):
        r = rA + i
        ws[f"AD{r}"] = k
        ws[f"AE{r}"] = f"=IF(COUNTIFS({R_gej['kota']},AD{r},{R_gej['komoditas']},pilih_komoditas)=0,-1,SUMIFS({R_gej['rata_perubahan_per_minggu']},{R_gej['kota']},AD{r},{R_gej['komoditas']},pilih_komoditas))"
        ws[f"AF{r}"] = f"=AE{r}+ROW()/1000000000"
        ws[f"AG{r}"] = f"=INDEX($AD${rA}:$AD${rZ},MATCH(LARGE($AF${rA}:$AF${rZ},{i + 1}),$AF${rA}:$AF${rZ},0))"
        ws[f"AH{r}"] = f"=INDEX($AE${rA}:$AE${rZ},MATCH(LARGE($AF${rA}:$AF${rZ},{i + 1}),$AF${rA}:$AF${rZ},0))"
        ws[f"AH{r}"].number_format = "0.0%"
    nama(wb, "kpi_kota_paling_tidak_stabil", f"{GJ}!$AG${rA}")
    ws["AC5"] = "rata_perubahan"   # penanda untuk src/audit_dashboard.py: angka kota di halaman ini = rata-rata perubahan per minggu
    nama(wb, "ukuran_gejolak", f"{GJ}!$AC$5")
    nama(wb, "kpi_gejolak_kota_teratas", f"{GJ}!$AH${rA}")
    # bantu kota operasional (AJ..AN)
    oA, oZ = 12, 12 + len(operasional) - 1
    for i, k in enumerate(operasional):
        r = oA + i
        ws[f"AJ{r}"] = k
        ws[f"AK{r}"] = f"=INDEX($AE${rA}:$AE${rZ},MATCH(AJ{r},$AD${rA}:$AD${rZ},0))"
        ws[f"AL{r}"] = f"=AK{r}+ROW()/1000000000"
        ws[f"AM{r}"] = (f"=INDEX($AJ${oA}:$AJ${oZ},MATCH(LARGE($AL${oA}:$AL${oZ},{i + 1}),$AL${oA}:$AL${oZ},0))"
                        f"&IF(INDEX($AK${oA}:$AK${oZ},MATCH(LARGE($AL${oA}:$AL${oZ},{i + 1}),$AL${oA}:$AL${oZ},0))<0,\" (tidak ada data)\",\"\")")
        ws[f"AN{r}"] = f"=IF(LARGE($AL${oA}:$AL${oZ},{i + 1})<0,NA(),INDEX($AK${oA}:$AK${oZ},MATCH(LARGE($AL${oA}:$AL${oZ},{i + 1}),$AL${oA}:$AL${oZ},0)))"
        ws[f"AN{r}"].number_format = "0%"
    # judul halaman
    h.judul(f'=pilih_komoditas&IF(INDEX({R_kom["peringkat_gejolak"]},MATCH(pilih_komoditas,{R_kom["nama_dashboard"]},0))=1," paling tidak stabil",'
            f'", peringkat "&INDEX({R_kom["peringkat_gejolak"]},MATCH(pilih_komoditas,{R_kom["nama_dashboard"]},0))&" dari 6 dalam gejolak harga")'
            f'&": harganya berubah rata-rata "&TEXT(INDEX({R_kom["rata_perubahan_per_minggu"]},MATCH(pilih_komoditas,{R_kom["nama_dashboard"]},0)),"0%")'
            f'&" setiap minggu, terutama di "&{f_singkat(f"$AG${rA}")}')
    # peta
    h.kartu(1, 5, 14, 16)
    tulis(ws, 1, 6, f'="Gejolak terbesar di "&{f_singkat(f"$AG${rA}")}&", "&{f_singkat(f"$AG${rA + 1}")}&", dan "&{f_singkat(f"$AG${rA + 2}")}',
          11, True, k2=10)
    tulis(ws, 11, 6, "Besar gelembung = besar gejolak", 8, False, MUTED, align="right", k2=14)
    tulis(ws, 1, 16, "Label hanya untuk kota tujuan, kota sumber utama, dan kota paling bergejolak; gelembung tanpa label adalah kota lain.",
          7, False, MUTED, k2=14)
    top3 = (g[g.komoditas == "Cabai rawit merah"].sort_values("rata_perubahan_per_minggu", ascending=False).kota.head(3).tolist())
    fokus = [k for k in LABEL_PETA if k in kota_all]
    kota_xy = kota.set_index("kota")
    pA = 12
    for i, k in enumerate(kota_all):
        r = pA + i
        ws[f"AP{r}"] = k
        ws[f"AQ{r}"] = float(kota_xy.loc[k, "lon"])
        ws[f"AR{r}"] = float(kota_xy.loc[k, "lat"])
        nilai = f"INDEX($AE${rA}:$AE${rZ},MATCH(AP{r},$AD${rA}:$AD${rZ},0))"
        ws[f"AS{r}"] = f"=IF(OR({nilai}<0,{'TRUE' if k in fokus else 'FALSE'}),NA(),{nilai}*100)"
        ws[f"AT{r}"] = f"=IF({nilai}<0,NA(),{nilai}*100)"
        ws[f"AU{r}"] = f'={f_singkat(f"AP{r}")}&IF({nilai}<0,"",": "&TEXT({nilai},"0%"))'
    map_w = 14 * PX_KOL - 20
    map_h = round(map_w * (BINGKAI[3] - BINGKAI[2]) / (BINGKAI[1] - BINGKAI[0]))
    tmpdir = Path(tempfile.mkdtemp())
    png = gambar_peta(tmpdir / "peta_jawa.png", map_w, map_h)
    taruh(ws, Image(str(png)), 1, 7, map_w, map_h, dx=10, dy=12)
    bub = BubbleChart()
    s0 = Series(values=Reference(ws, min_col=44, min_row=pA, max_row=pA + n_k - 1), xvalues=Reference(ws, min_col=43, min_row=pA, max_row=pA + n_k - 1),
                zvalues=Reference(ws, min_col=45, min_row=pA, max_row=pA + n_k - 1), title="Kota lain")
    bub.series.append(s0)
    for k in fokus:
        r = pA + kota_all.index(k)
        s = Series(values=Reference(ws, min_col=44, min_row=r), xvalues=Reference(ws, min_col=43, min_row=r), zvalues=Reference(ws, min_col=46, min_row=r))
        s.tx = SeriesLabel(strRef=StrRef(f"{GJ}!$AU${r}"))
        s.dLbls = DataLabelList(showSerName=True, showVal=False, showCatName=False, showBubbleSize=False, showLegendKey=False, showPercent=False,
                                dLblPos=LABEL_PETA[k], txPr=teks_grafik(8, INK))
        bub.series.append(s)
    for i, s in enumerate(bub.series):
        s.graphicalProperties = GraphicalProperties(solidFill=ORANGE_PUCAT if i else "F9D3C2", ln=LineProperties(solidFill=ORANGE if i else ORANGE_PUCAT, w=12700))
    polos(bub, sumbu_x=False, sumbu_y=False, grid=False)
    bub.x_axis.scaling.min, bub.x_axis.scaling.max = BINGKAI[0], BINGKAI[1]
    bub.y_axis.scaling.min, bub.y_axis.scaling.max = BINGKAI[2], BINGKAI[3]
    bub.bubbleScale = 45
    bub.plot_area.layout = Layout(manualLayout=ManualLayout(layoutTarget="inner", xMode="edge", yMode="edge", x=0, y=0, w=1, h=1))
    taruh(ws, bub, 1, 7, map_w, map_h, dx=10, dy=12)
    # 10 kota operasional
    h.kartu(15, 5, 24, 16)
    tulis(ws, 15, 6, f'="Di 10 kota operasional kita, harga paling banyak berubah di "&{f_singkat(f"$AM${oA}")}&" ("&TEXT($AN${oA},"0%")&" per minggu)"', 11, True, wrap=True, k2=24, r2=7, valign="top")
    bc = BarChart(); bc.type = "bar"; bc.gapWidth = 45
    bc.add_data(Reference(ws, min_col=40, min_row=oA, max_row=oZ), titles_from_data=False)
    bc.set_categories(Reference(ws, min_col=39, min_row=oA, max_row=oZ))
    s = bc.series[0]
    s.graphicalProperties = GraphicalProperties(solidFill=ORANGE_PUCAT, ln=LineProperties(noFill=True))
    for i in range(3):
        s.dPt.append(DataPoint(idx=i, spPr=GraphicalProperties(solidFill=ORANGE, ln=LineProperties(noFill=True))))
    s.dLbls = DataLabelList(showVal=True, showSerName=False, showCatName=False, showLegendKey=False, dLblPos="outEnd", numFmt="0%", txPr=teks_grafik(8, INK))
    polos(bc, sumbu_x=True, sumbu_y=False, grid=False)
    bc.x_axis.scaling.orientation = "maxMin"
    bc.x_axis.spPr = GraphicalProperties(ln=LineProperties(noFill=True))
    bc.x_axis.txPr = teks_grafik(8, INK)
    taruh(ws, bc, 15, 8, 10 * PX_KOL - 12, 8.6 * PX_BARIS, dx=4)
    # heatmap kota x komoditas (semua komoditas, tidak ikut pilihan)
    gp = g.pivot(index="kota", columns="komoditas", values="rata_perubahan_per_minggu")
    baris_hm = list(dict.fromkeys(top3 + operasional))
    baris_hm = sorted(baris_hm, key=lambda k: -(gp.loc[k, "Cabai rawit merah"] if pd.notna(gp.loc[k, "Cabai rawit merah"]) else 0))
    r_hm0 = 17
    r_hm1 = r_hm0 + 3 + len(baris_hm)
    h.kartu(1, r_hm0, 24, r_hm1)
    tulis(ws, 1, r_hm0 + 1, "Cabai tidak stabil di semua kota; ayam, telur, dan bawang putih stabil di mana pun", 11, True, k2=24)
    lebar = [(5, 7), (8, 10), (11, 14), (15, 17), (18, 20), (21, 24)]
    tulis(ws, 1, r_hm0 + 2, "Kota", 8, True, MUTED, k2=4)
    for (k0, k1), kk in zip(lebar, urut_kom):
        tulis(ws, k0, r_hm0 + 2, PENDEK[kk], 8, True, MUTED, align="center", k2=k1)
    for i, kt in enumerate(baris_hm):
        r = r_hm0 + 3 + i
        tulis(ws, 1, r, kt, 9, False, INK, k2=4)
        for (k0, k1), kk in zip(lebar, urut_kom):
            v = gp.loc[kt, kk] if kk in gp.columns else None
            tulis(ws, k0, r, float(v) if pd.notna(v) else "–", 9, False, INK, align="center", fmt="0%", k2=k1)
    ws.conditional_formatting.add(f"{kol(5)}{r_hm0 + 3}:{kol(24)}{r_hm1}", ColorScaleRule(start_type="num", start_value=0.01, start_color="FFFFFF",
                                  end_type="num", end_value=0.18, end_color="EF8A5E"))
    tulis(ws, 1, r_hm1, f"Angka = rata-rata perubahan harga per minggu. Daftar: 3 kota paling tidak stabil untuk cabai rawit dan 10 kota operasional "
                        f"(4 kota tujuan, 6 kota sumber). Tanda – berarti komoditas itu tidak tercatat di kota tersebut.", 8, False, MUTED, k2=24, valign="center")
    # band
    rk = d_kom.set_index("nama_dashboard").rata_perubahan_per_minggu
    tenang = ["Daging ayam ras", "Telur ayam ras", "Bawang putih"]
    lo, hi = min(rk[t] for t in tenang), max(rk[t] for t in tenang)
    kali = sorted([rk["Cabai merah keriting"] / rk["Telur ayam ras"], rk["Cabai rawit merah"] / rk["Telur ayam ras"]])
    kali_t = f"{kali[0]:.0f}" if round(kali[0]) == round(kali[1]) else f"{kali[0]:.0f} sampai {kali[1]:.0f}"
    per_kota_tenang = g[g.komoditas.isin(tenang)].rata_perubahan_per_minggu.max()
    per_kota_cabai = g[g.komoditas.isin(["Cabai rawit merah", "Cabai merah keriting"])].rata_perubahan_per_minggu.min()
    top3_count = (g.assign(rk=g.groupby("komoditas").rata_perubahan_per_minggu.rank(ascending=False)).query("rk <= 3").kota.value_counts())
    sering, n_sering = top3_count.index[0], int(top3_count.iloc[0])
    h.band(r_hm1 + 1, [
        (f"Harga cabai rawit dan cabai keriting berubah {rk['Cabai rawit merah']:.0%} dan {rk['Cabai merah keriting']:.0%} per minggu, "
         f"sekitar {kali_t} kali lipat telur.", "Pantau harga kedua cabai setiap minggu dan siapkan stok cadangan."),
        (f"Ayam, telur, dan bawang putih rata-rata berubah {lo:.0%} sampai {hi:.0%} per minggu. Di kota paling bergejolak pun paling tinggi "
         f"{per_kota_tenang:.0%}, jauh di bawah cabai (paling rendah {desimal(per_kota_cabai * 100)}%).", "Cukup dipantau bulanan; beli dengan pola rutin."),
        (f"{singkat(sering)} masuk tiga kota paling tidak stabil di {n_sering} dari 6 komoditas, padahal datanya hanya dari 2 pasar.",
         f"Cek harga {singkat(sering)} di lapangan sebelum dipakai untuk keputusan.")],
        "Gejolak di halaman ini adalah rata-rata besarnya perubahan harga dari minggu ke minggu di pasar tradisional, Juli 2023 sampai Oktober 2026. "
        "Peta latar: Natural Earth.")

    # ================================================================ PINDAH STOK
    h = H["rute"]; ws = h.ws; PS = q(NAMA_SHEET["rute"])
    h.kartu(15, 2, 24, 3)
    tulis(ws, 15, 2, kaya(("Ongkos kirim  ", 9, True, INK), ("perkiraan kami", 8, False, ORANGE_TXT)), k2=18)
    # pengali ongkos dipilih lewat tombol (Form Control option button, dipasang lewat Excel oleh pasang_objek_excel):
    # tombol menulis nomor pilihan 1-4 ke AC9; AC10 = pengali (nama pengali_ongkos); U2 menampilkannya sebagai teks
    PILIHAN_PENGALI = [(0.5, "0,5x"), (1, "1x"), (1.5, "1,5x"), (2, "2x")]
    ws["AC9"] = [v for v, _ in PILIHAN_PENGALI].index(kons) + 1
    ws["AC10"] = "=CHOOSE(AC9," + ",".join(str(v) for v, _ in PILIHAN_PENGALI) + ")"
    tulis(ws, 19, 2, "=CHOOSE(AC9," + ",".join(f'"{t[:-1]} kali"' for _, t in PILIHAN_PENGALI) + ")", 10, True, INK, align="center", bg=GRAY_MUDA, k2=20)
    for j, (v, t) in enumerate(PILIHAN_PENGALI):
        c = tulis(ws, 21 + j, 2, None, 8, True, INK, align="center", bg=GRAY_MUDA)   # latar tombol; teksnya milik tombol
        ws.conditional_formatting.add(c.coordinate, FormulaRule(formula=[f"pengali_ongkos={v}"], fill=isi(TEAL_MUDA)))
    tulis(ws, 15, 3, "Tambahan ongkos (Rp/kg)", 9, True, INK, k2=18)
    tulis(ws, 19, 3, 0, 10, True, INK, align="center", fmt="#,##0", bg=KUNING, k2=20)
    tulis(ws, 21, 3, "Klik tombol; sel kuning bisa diisi.", 7, False, MUTED, k2=24, indent=0)
    nama(wb, "pengali_ongkos", f"{PS}!$AC$10"); nama(wb, "tambahan_ongkos", f"{PS}!${kol(19)}$3")
    # bantu per rute (AD..AM, baris 12..43)
    n_r = len(d_rute)
    b0, b1 = 12, 12 + n_r - 1
    for i in range(n_r):
        r = b0 + i
        ws[f"AD{r}"] = f"=INDEX({R_rute['rute_key']},{i + 1})"
        ws[f"AE{r}"] = f"=INDEX({R_rute['nama_pendek']},{i + 1})"
        ws[f"AF{r}"] = f"=INDEX({R_rute['median_selisih_harga_rp_per_kg']},{i + 1})"
        ws[f"AH{r}"] = (f"=INDEX({R_sens['median_untung_rp_per_kg']},MATCH(AD{r}&\"|\"&pengali_ongkos,INDEX({R_sens['rute_key']}&\"|\"&{R_sens['pengali_ongkos']},0),0))"
                        f"-tambahan_ongkos*pengali_ongkos")
        ws[f"AI{r}"] = (f"=10*SUMPRODUCT(({R_sp['rute_key']}=AD{r})*ISNUMBER({R_sp['selisih_harga']})*(({R_sp['selisih_harga']}-({R_sp['ongkos_angkut']}+{R_sp['susut_rp']}+tambahan_ongkos)*pengali_ongkos)>0))"
                        f"/SUMPRODUCT(({R_sp['rute_key']}=AD{r})*ISNUMBER({R_sp['selisih_harga']}))")
        ws[f"AK{r}"] = f"=INDEX({R_rute['risiko']},{i + 1})"
        ws[f"AR{r}"] = f"=(INDEX({R_rute['median_ongkos_dasar']},{i + 1})+tambahan_ongkos)*pengali_ongkos"   # nilai tengah ongkos pada skenario
        ws[f"AL{r}"] = f"=AH{r}+ROW()/1000000"
        ws[f"AG{r}"] = f"=INDEX($AE${b0}:$AE${b1},MATCH(LARGE($AL${b0}:$AL${b1},{i + 1}),$AL${b0}:$AL${b1},0))"
        ws[f"AJ{r}"] = f"=INDEX($AH${b0}:$AH${b1},MATCH(LARGE($AL${b0}:$AL${b1},{i + 1}),$AL${b0}:$AL${b1},0))"
        ws[f"AM{r}"] = f"=INDEX($AD${b0}:$AD${b1},MATCH(LARGE($AL${b0}:$AL${b1},{i + 1}),$AL${b0}:$AL${b1},0))"
    cari_r = lambda kolom, urut: f"INDEX(${kolom}${b0}:${kolom}${b1},MATCH(INDEX($AM${b0}:$AM${b1},{urut}),$AD${b0}:$AD${b1},0))"   # noqa: E731
    pengali_t = f'SUBSTITUTE({angka_teks("pengali_ongkos", 1)},",0","")'   # 1,5 / 1 / 2 / 0,5
    h.judul(f'=kpi_rute_untung_dinamis&" dari 32 rute pindah stok masih untung setelah ongkos kirim; margin tertinggi "&LOWER(LEFT($AG${b0},1))&MID($AG${b0},2,200)&", Rp "&{angka_teks(f"$AJ${b0}")}&"/kg"', k1=14)
    nama(wb, "kpi_rute_untung_dinamis", f"{PS}!${kol(1)}$6")
    h.kpi(1, 6, 5, "Rute yang untung", f"=SUMPRODUCT(($AH${b0}:$AH${b1}>0)*($AI${b0}:$AI${b1}>=6))", "dari 32",
          f'="Untung minimal 6 dari 10 minggu pada ongkos kirim "&{pengali_t}&" kali perkiraan."', TEAL, "0")
    nama(wb, "kpi_rute_aman", f"{PS}!${kol(7)}$6")
    h.kpi(7, 12, 5, "Rute aman", f"=COUNTIFS({R_rute['layak']},TRUE,{R_rute['layak_jika_jual_ke_pedagang_besar']},TRUE)", "rute",
          f"Untung juga bila dijual ke pedagang besar (ongkos {kons_t} kali); {n_tahan} di antaranya tetap aman pada ongkos 2 kali.", TEAL, "0")
    h.kpi(13, 18, 5, "Untung minggu ini", f"=SUMPRODUCT(({R_sp['minggu_key']}={akhir})*ISNUMBER({R_sp['selisih_harga']})*(({R_sp['selisih_harga']}-({R_sp['ongkos_angkut']}+{R_sp['susut_rp']}+tambahan_ongkos)*pengali_ongkos)>0))",
          "rute", f"{label_minggu}, pada skenario di sel kuning.", INK, "0")
    sens_f = lambda p: f"COUNTIFS({R_sens['pengali_ongkos']},{p},{R_sens['median_untung_rp_per_kg']},\">0\")"   # noqa: E731
    h.kpi(19, 24, 5, "Jika ongkos kirim 0,5 / 1 / 1,5 / 2 kali", f'={sens_f(0.5)}&" / "&{sens_f(1)}&" / "&{sens_f(1.5)}&" / "&{sens_f(2)}', "",
          "Jumlah rute dengan margin positif di tiap skenario.", INK, lebar_nilai=6)
    ws[f"{kol(19)}6"].font = font(18, True, INK)
    nama(wb, "kpi_rute_margin_positif", f"{PS}!{h.sel_bantu(6, f'=COUNTIF($AH${b0}:$AH${b1},\">0\")', '0')}")
    nama(wb, "kpi_margin_rute_terbaik", f"{PS}!{h.sel_bantu(7, f'=$AJ${b0}', '#,##0')}")
    # tabel 10 rute
    h.kartu(1, 10, 14, 26)
    tulis(ws, 1, 11, f'="10 rute dengan margin terbesar per kg (ongkos kirim "&{pengali_t}&" kali perkiraan)"', 11, True, k2=14)
    kolom_t = [(1, 5, "Rute", "left"), (6, 7, "Selisih harga", "right"), (8, 9, "Ongkos kirim", "right"), (10, 11, "Margin per kg", "right"),
               (12, 12, "Minggu untung", "center"), (13, 14, "Risiko", "center")]
    for k0, k1, t, al_ in kolom_t:
        tulis(ws, k0, 12, t, 8, True, MUTED, wrap=True, align=al_, k2=k1, r2=13, valign="bottom")
    h.baris_tabel(13, 1, 14)
    for i in range(10):
        r = 14 + i
        tulis(ws, 1, r, f"=INDEX($AG${b0}:$AG${b1},{i + 1})", 8, wrap=True, k2=5)
        tulis(ws, 6, r, f"={angka_teks(cari_r('AF', i + 1))}", 9, align="right", k2=7)
        tulis(ws, 8, r, f"={angka_teks(cari_r('AR', i + 1))}", 9, align="right", k2=9)
        tulis(ws, 10, r, f"={angka_teks(f'INDEX($AJ${b0}:$AJ${b1},{i + 1})')}", 9, True, TEAL, align="right", k2=11)
        tulis(ws, 12, r, f"={angka_teks(cari_r('AI', i + 1), 1)}", 9, align="center")
        c = tulis(ws, 13, r, f"={cari_r('AK', i + 1)}", 8, True, INK, align="center", bg=GRAY_MUDA, k2=14)
        h.baris_tabel(r, 1, 12)
    rng = f"{kol(13)}14:{kol(14)}23"
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"aman"'], fill=isi(TEAL_MUDA), font=Font(color=TEAL, bold=True)))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"tidak layak"'], fill=isi(ORANGE_MUDA), font=Font(color=ORANGE_TXT, bold=True)))
    tulis(ws, 1, 25, f"Minggu untung: dari 10 minggu. Aman: tetap untung walau dijual ke pedagang besar (ongkos {kons_t} kali). Hanya eceran: untung hanya bila "
                     "dijual dengan harga pasar. Selisih, ongkos, dan margin adalah nilai tengah masing-masing, jadi selisih dikurangi ongkos tidak persis sama "
                     "dengan margin. Ke-32 rute ada di sheet data d_rute.", 7, False, MUTED, wrap=True, k2=14, r2=26, valign="top")
    # grafik rute terbaik
    h.kartu(15, 10, 24, 26)
    tulis(ws, 15, 11, f'=INDEX($AG${b0}:$AG${b1},1)&": selisih harga di atas ongkos kirim pada "&{angka_teks(cari_r("AI", 1), 1)}&" dari 10 minggu sejak {BULAN_PENUH[pd.to_datetime(info_t['data_pertama']).month - 1]} {pd.to_datetime(info_t['data_pertama']).year}"',
          11, True, wrap=True, k2=24, r2=12, valign="top")
    tulis(ws, 15, 13, kaya(("Ribu rupiah per kg, 52 minggu terakhir:  ", 8, False, MUTED), ("selisih harga", 8, True, TEAL), ("  dan  ", 8, False, MUTED),
                           ("ongkos kirim pada skenario", 8, True, ORANGE_TXT)), k2=24)
    minggu_52 = sorted(sp.minggu_key.unique())[-52:]
    for i, mkey in enumerate(minggu_52):
        r = 12 + i
        ws[f"AO{r}"] = pd.to_datetime(str(mkey), format="%Y%m%d").to_pydatetime(); ws[f"AO{r}"].number_format = BULAN_SUMBU
        key = f"$AM${b0}&\"|{mkey}\""
        ws[f"AP{r}"] = f"=IFERROR(INDEX({R_sp['selisih_harga']},MATCH({key},{R_sp['kunci']},0)),NA())"
        ws[f"AQ{r}"] = f"=IFERROR((INDEX({R_sp['ongkos_angkut']},MATCH({key},{R_sp['kunci']},0))+INDEX({R_sp['susut_rp']},MATCH({key},{R_sp['kunci']},0))+tambahan_ongkos)*pengali_ongkos,NA())"
    lc = LineChart()
    lc.add_data(Reference(ws, min_col=42, min_row=12, max_col=43, max_row=63), titles_from_data=False)
    lc.set_categories(Reference(ws, min_col=41, min_row=12, max_row=63))
    garis(lc.series[0], TEAL, 24000); garis(lc.series[1], ORANGE, 20000, putus=True)
    sumbu_bulan(lc, tiap=3)
    polos(lc)
    lc.y_axis.numFmt = '#,##0,"rb"'
    taruh(ws, lc, 15, 14, 10 * PX_KOL - 12, 8 * PX_BARIS, dx=4)
    kunci_akhir = f'$AM${b0}&"|{akhir}"'
    for k0, k1, lab, f_ in [(15, 17, "Margin minggu ini", f'=IFERROR("Rp "&{angka_teks(f"INDEX({R_sp["selisih_harga"]},MATCH({kunci_akhir},{R_sp["kunci"]},0))-(INDEX({R_sp["ongkos_angkut"]},MATCH({kunci_akhir},{R_sp["kunci"]},0))+INDEX({R_sp["susut_rp"]},MATCH({kunci_akhir},{R_sp["kunci"]},0))+tambahan_ongkos)*pengali_ongkos")},"tidak ada data")'),
                            (18, 20, "Untung beruntun", f'=INDEX({R_rute["minggu_untung_berturut_terakhir"]},MATCH($AM${b0},{R_rute["rute_key"]},0))&" minggu"'),
                            (21, 24, "Jika dijual ke pedagang besar", f'="Rp "&{angka_teks(f"INDEX({R_rute["median_untung_jual_ke_pedagang_besar"]},MATCH($AM${b0},{R_rute["rute_key"]},0))")}')]:
        h.kartu(k0, 22, k1, 25, BG, jarak=WHITE)
        tulis(ws, k0, 22, lab.upper(), 7, True, MUTED, k2=k1, valign="bottom", wrap=True)
        tulis(ws, k0, 23, f_, 13, True, TEAL if k0 != 18 else INK, k2=k1, r2=24)
    tulis(ws, 15, 25, f"Dua kotak terakhir dihitung pada ongkos kirim {kons_t} kali perkiraan.", 7, False, MUTED, k2=24)
    # band
    aman_df = d_rute[d_rute.risiko == "aman"]
    asal_aman = {PENDEK[nk[kk]].lower(): sorted({singkat(nama_kota[s]) for s in grp.kota_sumber_key}) for kk, grp in aman_df.groupby("komoditas_key")}
    eceran_saja = [PENDEK[nk[kk]].lower() for kk, grp in d_rute[d_rute.layak].groupby("komoditas_key") if not (grp.risiko == "aman").any()]
    gab = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " dan " + xs[-1]   # noqa: E731
    pos = sens[sens.median_untung_rp_per_kg > 0].groupby("pengali_ongkos").size()
    sk = sens.pivot(index="rute_key", columns="pengali_ongkos", values="median_untung_rp_per_kg")
    berbalik = sk[(sk[kons] > 0) & (sk[2.0] <= 0)]
    ambang = 1000 * -(-berbalik[kons].max() // 1000) if len(berbalik) else 0
    di_bawah = sk[(sk[kons] > 0) & (sk[kons] < ambang)]
    fakta3 = (f"{len(berbalik)} rute dengan margin di bawah Rp {rp(ambang)}/kg berubah rugi bila ongkos kirim dua kali perkiraan; "
              f"rute dengan margin positif turun dari {pos.get(kons, 0)} menjadi {pos.get(2.0, 0)}."
              if len(berbalik) and len(di_bawah) == len(berbalik) else
              f"Jika ongkos kirim ternyata dua kali perkiraan, rute dengan margin positif turun dari {pos.get(kons, 0)} menjadi {pos.get(2.0, 0)}.")
    h.band(27, [
        (f"{len(aman_df)} rute tetap untung walau dijual ke pedagang besar: " + "; ".join(f"{k} dari {gab(v)}" for k, v in asal_aman.items())
         + f". {n_tahan} di antaranya tetap aman walau ongkos kirim dua kali perkiraan.",
         f"Jalankan {len(aman_df)} rute ini lebih dulu, mulai dari {n_tahan} rute yang paling tahan kenaikan ongkos."),
        (f"Rute {gab(eceran_saja)} hanya untung jika dijual eceran. Tidak ada yang bertahan jika dijual ke pedagang besar.",
         "Gunakan rute ini hanya untuk memasok gerai sendiri."),
        (fakta3, f"Tunda rute yang marginnya di bawah Rp {rp(ambang)}/kg." if ambang else "Pantau rute dengan margin tipis setiap bulan.")],
        "Harga beli: pedagang besar di kota asal. Harga jual: pasar tradisional di kota tujuan. Nilai tengah mingguan Juli 2023 sampai Oktober 2026. "
        "Ongkos kirim adalah perkiraan kami; untuk cabai, susut 5% adalah komponen terbesar.")

    # ================================================================ PERINGATAN DINI
    h = H["peringatan"]; ws = h.ws; PD = q(NAMA_SHEET["peringatan"])
    nb = h.sel_bantu(5, f"=INDEX({R_uji['benar_dari_10']},1)", "0.0"); nama(wb, "kpi_benar_dari_10", f"{PD}!{nb}")
    nt = h.sel_bantu(6, f"=INDEX({R_uji['tertangkap_dari_10']},1)", "0.0"); nama(wb, "kpi_tertangkap_dari_10", f"{PD}!{nt}")
    nl = h.sel_bantu(7, f"=INDEX({R_uji['lebih_awal_minggu']},1)", "0.0"); nama(wb, "kpi_lebih_awal", f"{PD}!{nl}")
    np_ = h.sel_bantu(8, f"=INDEX({R_uji['benar_dari_10']},4)", "0.0"); nama(wb, "kpi_benar_tahun_lalu", f"{PD}!{np_}")
    h.judul(f'=IF({nb}<{np_},"Sistem peringatan dini belum bisa diandalkan: hanya "&TEXT({nb},"0")&" dari 10 peringatan yang terbukti benar",'
            f'"Peringatan dini terbukti benar "&{angka_teks(nb, 1)}&" dari 10 kali, lebih baik daripada pola tahun lalu")')
    tahun_uji = sorted({int(t) for t in str(uji.tahun_uji.iloc[0]).replace(",", " ").split() if t.isdigit()}) if "tahun_uji" in uji else []
    label_uji = f"{tahun_uji[0]}-{tahun_uji[-1]}" if tahun_uji else "2025-2026"
    h.chip(19, 24, 2, f"Diuji pada data {label_uji}")
    selalu = uji_i.loc[5]
    h.kpi(1, 6, 5, "Peringatan yang benar", f"={angka_teks(nb, 1)}", "dari 10",
          f"Lebih buruk daripada memberi peringatan setiap minggu ({desimal(selalu.benar_dari_10)}).", ORANGE_TXT, lebar_nilai=2)
    h.kpi(7, 12, 5, "Lonjakan yang terdeteksi", f"={angka_teks(nt, 1)}", "dari 10", f"Dari {int(uji_i.loc[1, 'jumlah_lonjakan'])} lonjakan harga.", lebar_nilai=2)
    h.kpi(13, 18, 5, "Datang lebih awal", f"={angka_teks(nl, 1)}", "minggu",
          f"Angka ini tidak berarti sendirian; tebakan asal pun {desimal(selalu.lebih_awal_minggu)} minggu.", lebar_nilai=2)
    h.kpi(19, 24, 5, "Pembanding: pola tahun lalu", f"={angka_teks(np_, 1)}", "dari 10 benar",
          f"Mendeteksi {desimal(uji_i.loc[4, 'tertangkap_dari_10'])} dari 10 lonjakan, lebih baik daripada sistem.", TEAL, lebar_nilai=2)
    # aturan
    h.kartu(1, 10, 12, 26)
    tulis(ws, 1, 11, "Peringatan yang benar (dari 10): semua versi aturan kalah dari pola tahun lalu" if uji_i.loc[[1, 2, 3], "benar_dari_10"].max() < uji_i.loc[4, "benar_dari_10"]
          else "Peringatan yang benar (dari 10) per versi aturan", 11, True, wrap=True, k2=12, r2=12, valign="top")
    label_aturan = {1: "Sistem peringatan dini", 2: "Hanya kota yang naik lebih dulu", 3: "Hanya masa menjelang Lebaran",
                    4: "Pola tahun lalu", 5: "Peringatan setiap minggu"}
    for i in range(5):
        ws[f"AE{12 + i}"] = label_aturan[i + 1]
        ws[f"AF{12 + i}"] = f"=INDEX({R_uji['benar_dari_10']},{i + 1})"
        ws[f"AG{12 + i}"] = f'=AE{12 + i}&"  ("&{angka_teks(f"AF{12 + i}", 1)}&")"'   # label + angka; label data grafik ikut bahasa Excel
    bc2 = BarChart(); bc2.type = "bar"; bc2.gapWidth = 50
    bc2.add_data(Reference(ws, min_col=32, min_row=12, max_row=16), titles_from_data=False)
    bc2.set_categories(Reference(ws, min_col=33, min_row=12, max_row=16))
    s = bc2.series[0]
    s.graphicalProperties = GraphicalProperties(solidFill=ORANGE_PUCAT, ln=LineProperties(noFill=True))
    for idx, wv in ((0, ORANGE), (3, TEAL), (4, GRAY)):
        s.dPt.append(DataPoint(idx=idx, spPr=GraphicalProperties(solidFill=wv, ln=LineProperties(noFill=True))))
    polos(bc2, sumbu_x=True, sumbu_y=False, grid=False)
    bc2.x_axis.scaling.orientation = "maxMin"
    bc2.x_axis.spPr = GraphicalProperties(ln=LineProperties(noFill=True))
    bc2.x_axis.txPr = teks_grafik(8, INK)
    taruh(ws, bc2, 1, 13, 12 * PX_KOL - 12, 5 * PX_BARIS, dx=4)
    tulis(ws, 1, 19, "Kota yang harganya naik lebih dulu (selisih 1 minggu)", 11, True, k2=12)
    for k0, k1, t in ((1, 3, "Komoditas"), (4, 9, "3 kota teratas"), (10, 12, "Hubungan")):
        tulis(ws, k0, 20, t, 8, True, MUTED, k2=k1)
    h.baris_tabel(20, 1, 12)
    pa = T["fact_penentu_arah"]
    pa = pa[pa.tampil_di_dashboard].sort_values(["komoditas_key", "peringkat_penentu_arah"])
    for i, kk in enumerate(urut_kom):
        r = 21 + i
        sub = pa[pa.komoditas == kk].head(3)
        hub = sorted(set(sub.hubungan), key=["kuat", "sedang", "lemah"].index) if len(sub) else []
        tulis(ws, 1, r, PENDEK[kk], 9, k2=3)
        tulis(ws, 4, r, ", ".join(singkat(x) for x in sub.kota), 9, k2=9)
        tulis(ws, 10, r, " sampai ".join(hub) if len(hub) > 1 else (hub[0] if hub else "–"), 9, k2=12)
        h.baris_tabel(r, 1, 12)
    # contoh Jakarta
    n_al = int(dj.harga_saat_peringatan.notna().sum())
    awal_idx = set(dj.index[dj.awal_lonjakan])
    tepat = sum(any((i + d) in awal_idx for d in range(1, 5)) for i in dj.index[dj.harga_saat_peringatan.notna()])
    h.kartu(13, 10, 24, 26)
    tulis(ws, 13, 11, f"Contoh Jakarta Pusat: {n_al} peringatan dalam 2 tahun, " + ("tidak satu pun tepat sebelum lonjakan" if tepat == 0 else f"{tepat} di antaranya tepat sebelum lonjakan"),
          11, True, wrap=True, k2=24, r2=12, valign="top")
    tulis(ws, 13, 13, kaya(("Harga cabai rawit, ribu rupiah per kg:  ", 8, False, MUTED), ("titik = minggu dengan peringatan", 8, True, ORANGE_TXT),
                           ("  arsir = masa lonjakan", 8, True, "D98E6E")), k2=24)
    wsa = wb["d_peringatan_jakarta"]
    n_j = len(dj) + 1
    ar = AreaChart()
    ar.add_data(Reference(wsa, min_col=4, min_row=2, max_row=n_j), titles_from_data=False)
    ar.set_categories(Reference(wsa, min_col=1, min_row=2, max_row=n_j))
    ar.series[0].graphicalProperties = GraphicalProperties(solidFill="FBE3D9", ln=LineProperties(noFill=True))
    tl = LineChart()
    tl.add_data(Reference(wsa, min_col=2, min_row=2, max_col=3, max_row=n_j), titles_from_data=False)
    garis(tl.series[0], TEAL, 22000)
    s = tl.series[1]
    s.graphicalProperties.line.noFill = True
    s.marker.symbol = "circle"; s.marker.size = 7
    s.marker.graphicalProperties = GraphicalProperties(solidFill=ORANGE_TXT, ln=LineProperties(solidFill=ORANGE_TXT))
    sumbu_bulan(ar, tiap=3); sumbu_bulan(tl, tiap=3)
    polos(ar); polos(tl)
    ar.y_axis.numFmt = '#,##0,"rb"'
    ar.y_axis.scaling.min, ar.y_axis.scaling.max = 0, puncak
    tl.y_axis.scaling.min, tl.y_axis.scaling.max = 0, puncak
    ar += tl
    taruh(ws, ar, 13, 14, 12 * PX_KOL - 12, 8 * PX_BARIS, dx=4)
    for k0, k1, lab, nilai_t in [(13, 17, "Peringatan minggu ini", f"Tidak ada ({n_peringatan} kota)" if n_peringatan == 0 else f"{n_peringatan} kota"),
                                 (18, 24, "Arti peringatan", "Harga naik tajam di kota yang biasanya naik lebih dulu, atau sudah masuk masa menjelang Lebaran.")]:
        h.kartu(k0, 22, k1, 25, BG, jarak=WHITE)
        tulis(ws, k0, 22, lab.upper(), 7, True, MUTED, k2=k1, valign="bottom")
        tulis(ws, k0, 23, nilai_t, 12 if k0 == 13 else 9, k0 == 13, INK, wrap=True, k2=k1, r2=25, valign="top")
    kd = d_kom.set_index("nama_dashboard").idulfitri_mulai_naik_minggu
    h.band(27, [
        (f"Peringatan sistem hanya benar {desimal(uji_i.loc[1, 'benar_dari_10'])} dari 10 kali. Pola sederhana \"sama seperti tahun lalu\" benar {desimal(uji_i.loc[4, 'benar_dari_10'])} dari 10.",
         "Jangan jadikan peringatan dini dasar pembelian."),
        (f"Kalender Lebaran berguna untuk jadwal beli: bawang merah naik {abs(int(kd['Bawang merah']))} minggu sebelum Lebaran, "
         f"{d_kom.set_index('nama_dashboard').idulfitri_tahun_konsisten['Bawang merah']} tahun. Untuk menebak lonjakan mingguan, aturan "
         f"\"masa menjelang Lebaran\" hanya benar {desimal(uji_i.loc[3, 'benar_dari_10'])} dari 10.",
         "Pakai kalender Lebaran untuk jadwal beli, bukan sebagai pemicu peringatan."),
        ("Kota yang naik lebih dulu hanya mendahului 1 minggu, dan untuk kedua cabai hubungannya hanya sedang.",
         "Pantau kota tersebut sebagai informasi tambahan, bukan pemicu beli.")],
        "Lonjakan adalah kenaikan harga di atas ambang dalam 4 minggu. Baru 2 tahun data uji, hasil masih perkiraan. "
        "Hubungan antarkota bersifat statistik, bukan sebab-akibat.")

    # ================================================================ POLA MUSIMAN
    h = H["pola"]; ws = h.ws
    kolom_k = "idulfitri_mulai_naik_minggu"
    kol_mulai = R_kom[kolom_k].split("!$")[1].split("$")[0]
    nama(wb, "kpi_bawang_merah_mulai_naik", f"{q('d_komoditas')}!${kol_mulai}${2 + urut_kom.index('Bawang merah')}")
    h.judul(f'="Bawang merah naik "&TEXT(INDEX({R_kom["idulfitri_kenaikan_minggu_min1"]},MATCH("Bawang merah",{R_kom["nama_dashboard"]},0)),"0%")'
            f'&" menjelang Lebaran dan mulai naik "&ABS(INDEX({R_kom[kolom_k]},MATCH("Bawang merah",{R_kom["nama_dashboard"]},0)))&" minggu sebelumnya; stok harus masuk sebelum itu"')
    tulis(ws, 17, 2, kaya(("Garis: rata-rata 3 tahun.  ", 8, False, MUTED), ("Pita hijau: rentang antar tahun.  ", 8, False, TEAL),
                          ("Arsir: masa kenaikan.", 8, False, "D98E6E")), k2=24, r2=3, align="right", wrap=True, valign="top")
    _dk = d_kom.set_index("nama_dashboard")
    urutan_pola = sorted(urut_kom, key=lambda k: (pd.isna(mulai_map[k]), -int(str(_dk.idulfitri_tahun_konsisten[k])[0]),
                                                  -float(_dk.idulfitri_kenaikan_minggu_min1[k]) if pd.notna(_dk.idulfitri_kenaikan_minggu_min1[k]) else 0))
    wsp = wb["d_pola_lebaran"]
    kolp = {c: i + 1 for i, c in enumerate(pola.columns)}
    dk = d_kom.set_index("nama_dashboard")
    for i, kk in enumerate(urutan_pola):
        k0 = 1 + (i % 3) * 8
        r0 = 5 + (i // 3) * 11
        k1, r1 = k0 + 7, r0 + 10
        h.kartu(k0, r0, k1, r1)
        mulai, kons_th = mulai_map[kk], dk.loc[kk, "idulfitri_tahun_konsisten"]
        batas = bool(kom_idx.loc[kk, "idulfitri_naik_di_batas_jendela"]) if "idulfitri_naik_di_batas_jendela" in kom_idx else False
        if pd.isna(mulai):
            pil, bgp, fgp = f"tidak konsisten, {kons_th} tahun", GRAY_MUDA, INK
        elif batas:
            pil, bgp, fgp = f"tinggi sejak {abs(int(mulai))} minggu, {kons_th} tahun", ORANGE_MUDA, ORANGE_TXT
        else:
            pil, bgp, fgp = f"naik {abs(int(mulai))} minggu sebelum, {kons_th} tahun", TEAL_MUDA, TEAL
        tulis(ws, k0, r0 + 1, PENDEK[kk], 10, True, k2=k0 + 2)
        tulis(ws, k0 + 3, r0 + 1, pil, 8, True, fgp, align="center", bg=bgp, k2=k1)
        sub = pola[(pola.komoditas == kk) & (pola.minggu_ke_lebaran == -1)].iloc[0]
        per_th = ", ".join(f"{c[3:]} {persen(sub[c], True)}" for c in pola.columns if c.startswith("th_") and pd.notna(sub[c]))
        tulis(ws, k0, r0 + 2, f"Seminggu sebelum Lebaran rata-rata {persen(dk.loc[kk, 'idulfitri_kenaikan_minggu_min1'], True)} ({per_th}).",
              8, False, MUTED, wrap=True, k2=k1, r2=r0 + 3, valign="top")
        rp0 = 2 + urut_kom.index(kk) * 13
        rp1 = rp0 + 12
        ar = AreaChart(); ar.grouping = "stacked"
        ar.add_data(Reference(wsp, min_col=kolp["terendah"], min_row=rp0, max_row=rp1), titles_from_data=False)
        ar.add_data(Reference(wsp, min_col=kolp["rentang"], min_row=rp0, max_row=rp1), titles_from_data=False)
        ar.set_categories(Reference(wsp, min_col=kolp["minggu_ke_lebaran"], min_row=rp0, max_row=rp1))
        ar.series[0].graphicalProperties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
        ar.series[1].graphicalProperties = GraphicalProperties(solidFill="CFEDE0", ln=LineProperties(noFill=True))
        ln = LineChart()
        ln.add_data(Reference(wsp, min_col=kolp["rata_rata"], min_row=rp0, max_row=rp1), titles_from_data=False)
        garis(ln.series[0], TEAL, 26000)
        bm = BarChart(); bm.gapWidth = 0
        bm.add_data(Reference(wsp, min_col=kolp["masa_kenaikan"], min_row=rp0, max_row=rp1), titles_from_data=False)
        bm.series[0].graphicalProperties = GraphicalProperties(solidFill="FBE3D9", ln=LineProperties(noFill=True))
        bm.y_axis.axId = 200
        bm.y_axis.scaling.min, bm.y_axis.scaling.max = 0, 1
        bm.y_axis.crosses = "max"
        for c_ in (ar, ln, bm):
            polos(c_, sumbu_x=False, sumbu_y=c_ is not bm, grid=False)
        ar.y_axis.numFmt = "0%"
        seri_k = pola[pola.komoditas == kk]
        import math
        lo_, hi_ = min(0.0, float(seri_k.terendah.min())), max(0.1, float(seri_k.tertinggi.max()))
        unit = 0.1 if hi_ - lo_ <= 0.4 else (0.2 if hi_ - lo_ <= 1.0 else 0.5)
        ymin, ymax = math.floor(lo_ / unit) * unit, math.ceil(hi_ / unit) * unit
        ar.y_axis.scaling.min, ar.y_axis.scaling.max, ar.y_axis.majorUnit = ymin, ymax, unit
        ln.y_axis.scaling.min, ln.y_axis.scaling.max = ymin, ymax
        bm.x_axis.crossAx = 200
        ar.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="E6EBE9")))
        bm.y_axis.delete = True
        bm += ar
        bm += ln
        combo = bm
        taruh(ws, combo, k0, r0 + 4, 8 * PX_KOL - 12, 5.4 * PX_BARIS, dx=4)
        tulis(ws, k0, r1, "8 minggu sebelum", 7, False, MUTED, k2=k0 + 2, valign="top")
        tulis(ws, k0 + 5, r1, "Lebaran", 7, True, MUTED, align="center", valign="top")
        tulis(ws, k0 + 6, r1, "4 minggu sesudah", 7, False, MUTED, align="right", k2=k1, valign="top")
    rr = dk.idulfitri_kenaikan_minggu_min1
    tidak = [PENDEK[k].lower() for k in urut_kom if pd.isna(mulai_map[k])]
    per_th_bm = pola[(pola.komoditas == "Bawang merah") & (pola.minggu_ke_lebaran == -1)].iloc[0]
    n_th_bm = sum(1 for c in pola.columns if c.startswith("th_") and pd.notna(per_th_bm[c]))
    h.band(27, [
        (f"Bawang merah naik {rr['Bawang merah']:.0%} seminggu sebelum Lebaran, {dk.loc['Bawang merah', 'idulfitri_tahun_konsisten']} tahun. "
         f"Kenaikan mulai {abs(int(mulai_map['Bawang merah']))} minggu sebelumnya.", f"Amankan stok bawang merah paling lambat {abs(int(mulai_map['Bawang merah']))} minggu sebelum Lebaran."),
        (f"Ayam naik {abs(int(mulai_map['Daging ayam ras']))} minggu sebelum Lebaran ({dk.loc['Daging ayam ras', 'idulfitri_tahun_konsisten']} tahun). "
         "Cabai rawit sudah tinggi sejak 8 minggu sebelumnya, tetapi tiap tahun berbeda jauh.",
         f"Beli ayam {abs(int(mulai_map['Daging ayam ras']))} minggu sebelum; beli cabai rawit bertahap, jangan sekaligus."),
        (f"{gab([t.capitalize() if j == 0 else t for j, t in enumerate(tidak)])} tidak menunjukkan kenaikan yang konsisten menjelang Lebaran.",
         "Tidak perlu stok lebih awal untuk ketiga komoditas ini.")],
        f"Kenaikan diukur terhadap harga normal 9 sampai 12 minggu sebelum Lebaran, nilai tengah antar kota, pasar tradisional. "
        f"Baru {n_th_bm} kali Lebaran (2024 sampai 2026), hasil masih perkiraan kasar.")

    # ================================================================ RANTAI PASOK
    h = H["rantai"]; ws = h.ws; RT = q(NAMA_SHEET["rantai"])
    hemat_rng = R_mk["hemat_produsen"]
    nama(wb, "kpi_hemat_produsen_maks", f"{RT}!{h.sel_bantu(5, f'=MAX({hemat_rng})', PCT)}")
    hv = R_mk["hemat_vs_pb"]
    h.judul(f'="Beli langsung di produsen sekitar "&TEXT(MAX({hv}),"0%")&" lebih murah daripada pedagang besar untuk "&LOWER(INDEX({R_mk["label"]},MATCH(MAX({hv}),{hv},0)))'
            f'&"; untuk "&LOWER(INDEX({R_mk["label"]},MATCH(MIN({hv}),{hv},0)))&" hanya "&TEXT(MIN({hv}),"0%")')
    h.chip(17, 24, 2, "Harga produsen jarang diperbarui; angka ini perkiraan", ORANGE_MUDA, ORANGE_TXT, size=8)
    h.kartu(1, 5, 14, 26)
    tulis(ws, 1, 6, "Kenaikan harga di setiap tingkat rantai pasok", 11, True, k2=14)
    tulis(ws, 1, 7, kaya(("Ribu rupiah per kg:  ", 8, False, MUTED), ("harga produsen (petani/peternak)", 8, True, "8A9691"), ("  tambahan di pedagang besar", 8, True, BLUE),
                         ("  tambahan di pasar", 8, True, ORANGE_TXT)), k2=14)
    wsm = wb["d_margin_komoditas"]
    kolm = {c: i + 1 for i, c in enumerate(mk.columns)}
    sb = BarChart(); sb.type = "bar"; sb.grouping = "stacked"; sb.overlap = 100; sb.gapWidth = 55
    for c_ in ("harga_produsen", "tambahan_pedagang_besar_rp", "tambahan_pasar_rp"):
        sb.add_data(Reference(wsm, min_col=kolm[c_], min_row=2, max_row=len(mk) + 1), titles_from_data=False)
    sb.set_categories(Reference(wsm, min_col=kolm["label"], min_row=2, max_row=len(mk) + 1))
    for s_, cl in zip(sb.series, [GRAY, BLUE, ORANGE]):
        s_.graphicalProperties = GraphicalProperties(solidFill=cl, ln=LineProperties(noFill=True))
    polos(sb, sumbu_x=True, sumbu_y=True, grid=False)
    sb.x_axis.scaling.orientation = "maxMin"; sb.y_axis.crosses = "max"; sb.y_axis.numFmt = '#,##0,"rb"'
    sb.x_axis.spPr = GraphicalProperties(ln=LineProperties(noFill=True)); sb.x_axis.txPr = teks_grafik(8, INK)
    taruh(ws, sb, 1, 8, 14 * PX_KOL - 12, 5.6 * PX_BARIS, dx=4)
    kolom_m = [(1, 2, "Komoditas", "komoditas", "left"), (3, 4, "Produsen", "harga_produsen", "right"), (5, 6, "Pedagang besar", "harga_pedagang_besar", "right"),
               (7, 7, "Pasar", "harga_pasar", "right"), (8, 9, "Margin pedagang besar", "margin_pedagang_besar", "right"), (10, 10, "Margin pasar", "margin_pasar", "right"),
               (11, 12, "Hemat vs pedagang besar", "hemat_vs_pb", "right"), (13, 14, "Hemat vs harga pasar", "hemat_produsen", "right")]
    for k0, k1, t, _, a_ in kolom_m:
        tulis(ws, k0, 14, t, 7, True, MUTED, wrap=True, align=a_, k2=k1, r2=15, valign="bottom")
    h.baris_tabel(15, 1, 14)
    for i, row in mk.iterrows():
        r = 16 + i
        for k0, k1, _, c_, a_ in kolom_m:
            v = row[c_]
            if c_ == "komoditas":
                t, cl, b = PENDEK[v], INK, False
            elif c_.startswith("harga"):
                t, cl, b = rp(v), INK, False
            else:
                t, cl, b = f"{v:.0%}", TEAL if c_ == "hemat_vs_pb" else INK, c_ == "hemat_vs_pb"
            tulis(ws, k0, r, t, 9, b, cl, align=a_, k2=k1, indent=1)
        h.baris_tabel(r, 1, 14)
    tulis(ws, 1, 22, "Pasar modern lebih mahal daripada pasar tradisional", 10, True, k2=14)
    lebar_m = [(1, 3), (4, 6), (7, 9), (10, 12), (13, 14)]
    for (k0, k1), row in zip(lebar_m, mk.itertuples()):
        v = row.modern_vs_tradisional
        h.kartu(k0, 23, k1, 25, BG, jarak=WHITE)
        tulis(ws, k0, 23, row.label.upper(), 7, True, MUTED, k2=k1, valign="bottom")
        tulis(ws, k0, 24, persen(v, True), 13, True, ORANGE_TXT if v > 0 else BLUE, k2=k1, r2=25)
    # per kota cabai keriting
    h.kartu(15, 5, 24, 26)
    ck = m[m.komoditas == "Cabai merah keriting"].rename(columns={"hemat_produsen_vs_pedagang_besar_pct": "hemat_vs_pb"})
    ck = ck.sort_values("hemat_vs_pb", ascending=False).head(10)
    tulis(ws, 15, 6, f"Cabai keriting per kota: beli di produsen paling hemat di {singkat(ck.kota.iloc[0])}, {ck.hemat_vs_pb.iloc[0]:.0%} di bawah pedagang besar",
          11, True, wrap=True, k2=24, r2=7, valign="top")
    kolom_c = [(15, 16, "Kota", "left"), (17, 19, "Sumber harga produsen", "left"), (20, 21, "Produsen", "right"), (22, 22, "Pasar", "right"),
               (23, 23, "Hemat vs ped. besar", "right"), (24, 24, "Hemat vs pasar", "right")]
    for k0, k1, t, a_ in kolom_c:
        tulis(ws, k0, 8, t, 7, True, MUTED, align=a_, wrap=True, k2=k1, r2=9, valign="bottom")
    h.baris_tabel(9, 15, 24)
    for i, row in enumerate(ck.itertuples()):
        r = 10 + i
        bintang = "*" if "tambahan" in str(row.cakupan) else ""
        tulis(ws, 15, r, singkat(row.kota), 9, k2=16)
        tulis(ws, 17, r, f"{row.harga_produsen_dari}{bintang}", 8, k2=19)
        tulis(ws, 20, r, rp(row.harga_produsen), 9, align="right", k2=21)
        tulis(ws, 22, r, rp(row.harga_pasar), 9, align="right")
        tulis(ws, 23, r, f"{row.hemat_vs_pb:.0%}", 9, True, TEAL, align="right")
        tulis(ws, 24, r, f"{row.hemat_beli_produsen_pct:.0%}", 9, False, INK, align="right")
        h.baris_tabel(r, 15, 24)
    tulis(ws, 15, 10 + len(ck), "* Harga produsen dari kabupaten di sekitar kota; masih perlu diverifikasi. Rp per kg, nilai tengah bulanan. "
                                "Ped. besar = pedagang besar.", 7, False, MUTED, wrap=True, k2=24, r2=11 + len(ck), valign="top")
    usang = m.assign(b=m.porsi_bulan_produsen_lebih_mahal * m.n_bulan).groupby("komoditas").agg(b=("b", "sum"), n=("n_bulan", "sum"))
    usang = (usang.b / usang.n).drop("Bawang putih", errors="ignore")
    usang_lo, usang_hi = usang.min(), usang.max()
    for k0, k1, lab, nil, ket in [(15, 17, "Kota dengan data lengkap", f"{int(mk.kota.min())} sampai {int(mk.kota.max())}", "kota per komoditas"),
                                  (18, 21, "Harga produsen usang", f"{usang_lo * 100:.0f} sampai {usang_hi:.0%}", "bulan tercatat di atas pedagang besar"),
                                  (22, 24, "Bawang putih", "Tidak ada", "data produsen (impor)")]:
        h.kartu(k0, 22, k1, 25, BG, jarak=WHITE)
        tulis(ws, k0, 22, lab.upper(), 7, True, MUTED, k2=k1, valign="bottom", wrap=True)
        tulis(ws, k0, 23, nil, 13, True, INK, k2=k1)
        tulis(ws, k0, 24, ket, 7, False, MUTED, wrap=True, k2=k1, r2=25, valign="top")
    mki = mk.set_index("komoditas")
    hemat3 = mki.loc[["Cabai merah keriting", "Cabai rawit merah", "Daging ayam ras"]]
    mod = mki.modern_vs_tradisional[["Cabai rawit merah", "Cabai merah keriting", "Bawang merah"]]
    h.band(27, [
        (f"Dibanding pedagang besar, harga produsen {', '.join(f'{v:.0%}' for v in hemat3.hemat_vs_pb[:-1])} dan {hemat3.hemat_vs_pb.iloc[-1]:.0%} lebih murah "
         f"untuk cabai keriting, cabai rawit, dan ayam (dibanding harga pasar {', '.join(f'{v:.0%}' for v in hemat3.hemat_produsen[:-1])} dan "
         f"{hemat3.hemat_produsen.iloc[-1]:.0%}). Belum termasuk biaya mengumpulkan dari petani.",
         "Jajaki pembelian langsung dari produsen untuk ketiga komoditas ini."),
        (f"Untuk bawang merah dan telur, pedagang besar hanya {mki.loc['Bawang merah', 'margin_pedagang_besar']:.0%} dan "
         f"{mki.loc['Telur ayam ras', 'margin_pedagang_besar']:.0%} di atas harga produsen.", "Tetap beli bawang merah dan telur lewat pedagang besar."),
        (f"Pasar modern {mod.min():.0%} sampai {mod.max():.0%} lebih mahal daripada pasar tradisional untuk cabai dan bawang merah.",
         "Keluarkan pasar modern dari daftar sumber pembelian.")],
        "Harga produsen belum termasuk biaya mengumpulkan dari banyak petani. Nilai tengah bulanan Juli 2023 sampai Oktober 2026.")

    # ================================================================ CATATAN METODE
    h = H["metode"]; ws = h.ws
    h.judul("Catatan metode, sumber, dan batasan")
    baris = [
        ("Sumber data", f"PIHPS Nasional, Bank Indonesia (bi.go.id/hargapangan): pasar tradisional, pasar modern, pedagang besar, dan produsen di Pulau Jawa, "
                        f"{info_t['data_pertama']} sampai {info_t['data_terakhir']}, diambil {info_t['tanggal_pengambilan']}. Data bisa direvisi BI."),
        ("Cara membaca", "Judul tiap halaman adalah kesimpulan. Tiap angka diberi pembanding: 4 minggu lalu, rata-rata nasional, ongkos kirim, atau jumlah minggu dari 10. "
                         "Sel kuning adalah input yang boleh diubah. Pengali ongkos kirim di halaman Pindah stok dipilih dengan tombol (tanpa makro)."),
        ("Ongkos kirim", f"Perkiraan, bukan data: tarif truk box 5 ton, tol, bongkar muat, dan susut (cabai 5%, bawang merah 3%, telur 2%, ayam 1%). "
                         f"Rute disebut untung hanya bila tetap untung pada ongkos {kons_t} kali perkiraan."),
        ("Gejolak harga", "Di dashboard: rata-rata besarnya perubahan harga persen dari minggu ke minggu per kota dan komoditas, pasar tradisional. "
                          "Analisis (notebook 04) juga memakai simpangan baku perubahan mingguan (log-return) untuk peringkat; tiga kota teratas sama."),
        ("Tabel saran", "Saran per komoditas di Ringkasan memakai tindakan prioritas tertinggi dari analisis. Bila rute pindah stok hanya untung dengan harga eceran "
                        "dan harganya sedang naik cepat, yang ditampilkan adalah \"Beli secukupnya\". Untung pindah stok dihitung dengan harga pasar di kota tujuan."),
        ("Pindah stok", "Selisih harga = harga pasar tradisional kota tujuan dikurangi harga pedagang besar kota sumber (nilai tengah mingguan). "
                        "Margin = selisih dikurangi (ongkos kirim + susut + tambahan) dikali pengali. Rute aman = tetap untung bila dijual ke pedagang besar di kota tujuan "
                        f"pada ongkos {kons_t} kali; tahan 2 kali = tetap untung minimal 6 dari 10 minggu bila dijual ke pedagang besar dengan ongkos 2 kali."),
        ("Kota yang naik lebih dulu", "Korelasi silang perubahan harga mingguan setelah efek momentum dibuang, kota dibanding rata-rata kota lain, jeda 1 sampai 4 minggu, "
                                      "dengan koreksi uji berganda Benjamini-Hochberg. Ini kaitan statistik, bukan sebab-akibat."),
        ("Peringatan dini", "Peringatan = kenaikan mingguan jauh di atas kebiasaan (z lebih dari 2) di kota yang naik lebih dulu, atau sudah masuk masa sebelum Lebaran. "
                            "Lonjakan = kenaikan 4 minggu di atas persentil 90. Diuji pada 2025 dan 2026 tanpa melihat data tahun uji."),
        ("Pola Lebaran", "Harga minggu -8 sampai +4 dibanding harga normal (rata-rata minggu -12 sampai -9), nilai tengah antar kota, 3 kali Lebaran (2024 sampai 2026). "
                         "Mulai naik = setiap minggu sampai minggu -1 minimal 5% di atas normal pada 2 dari 3 tahun."),
        ("Rantai pasok", "Nilai tengah bulanan produsen, pedagang besar, dan pasar tradisional untuk kota yang punya ketiga tingkat; sebagian kota memakai harga produsen "
                         "kabupaten di sekitarnya (perlu diverifikasi). Harga produsen jarang diperbarui."),
        ("Peta", "Garis pantai dan batas provinsi: Natural Earth 1:10m (domain publik). Titik kota: OpenStreetMap Nominatim. Gelembung ditumpuk di atas gambar peta "
                 "dengan skala bujur dan lintang yang sama."),
        ("Batasan", "Sampel PIHPS kecil (2 pasar dan 2 pedagang per kota). Harga eceran belum tentu harga jual distributor. Volume dan stok tidak diketahui. "
                    "Baru 3 kali Lebaran. Kota sumber dipilih dari pengetahuan umum (perlu diverifikasi)."),
        ("Reproduksi dan audit", "Semua angka berasal dari skrip Python (src/) lewat data/processed/ ke sheet d_* di workbook ini (python -m src.build_excel_desain). "
                                 "Audit: python -m src.audit_dashboard --xlsx."),
        ("Nama sel untuk audit", "kpi_beli_awal, kpi_rute_untung, kpi_kenaikan_tercepat, kpi_peringatan_aktif, "
                                 "kpi_selisih_nasional_rawit, pilih_komoditas, kpi_kota_paling_tidak_stabil, kpi_gejolak_kota_teratas, pengali_ongkos, tambahan_ongkos, "
                                 "kpi_rute_untung_dinamis, kpi_rute_aman, kpi_rute_margin_positif, kpi_margin_rute_terbaik, kpi_benar_dari_10, kpi_tertangkap_dari_10, "
                                 "kpi_lebih_awal, kpi_benar_tahun_lalu, kpi_bawang_merah_mulai_naik, kpi_hemat_produsen_maks."),
    ]
    tinggi = [3 if len(v) > 300 else 2 for _, v in baris]
    h.kartu(1, 5, 24, 4 + sum(tinggi))
    r = 5
    for (k_, v), n in zip(baris, tinggi):
        tulis(ws, 1, r, k_, 10, True, k2=5, r2=r + n - 1, valign="top")
        tulis(ws, 6, r, v, 9, False, INK, wrap=True, k2=24, r2=r + n - 1, valign="top")
        h.baris_tabel(r + n - 1, 1, 24)
        r += n
    tulis(ws, 1, r + 1, f"Dibuat {datetime.now():%Y-%m-%d %H:%M} oleh python -m src.build_excel_desain", 8, False, MUTED, k2=24, indent=0)

    rancangan = {}
    for i, hh in enumerate(H.values()):
        hh.pasang_bingkai()
        hh.sembunyikan_bantu()
        rancangan[hh.ws.title] = {"bingkai": hh.bingkai, "menu": (5 + 2 * i, LABEL_MENU[hh.key])}
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    gambar_di_bawah(out)
    if tombol:
        pasang_objek_excel(out, rancangan)
    return out


def gambar_di_bawah(path: Path) -> None:
    """openpyxl menulis grafik lebih dulu lalu gambar, sehingga gambar menutupi grafik. Pindahkan anchor gambar ke awal
    tiap drawing XML agar peta jadi latar dan gelembung tampil di atasnya."""
    import re
    import shutil
    import zipfile

    tmp = path.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("xl/drawings/drawing") and item.filename.endswith(".xml"):
                xml = data.decode("utf-8")
                anchors = re.findall(r"<(?:xdr:)?oneCellAnchor>.*?</(?:xdr:)?oneCellAnchor>", xml, flags=re.S)
                pics = [a for a in anchors if ":pic>" in a or "<pic>" in a]
                if pics:
                    for a in pics:
                        xml = xml.replace(a, "", 1)
                    pertama = next(a for a in anchors if a not in pics)
                    i = xml.find(pertama)
                    xml = xml[:i] + "".join(pics) + xml[i:]
                    data = xml.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(OUT))
    a = p.parse_args()
    out = build(Path(a.out), tombol=True)
    print(f"Dashboard ditulis: {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
