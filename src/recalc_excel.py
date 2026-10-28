"""Menghitung ulang workbook lewat Excel (COM, pywin32) dan menyimpan nilai hasil rumus ke dalam file.

openpyxl menulis rumus tanpa nilai cache; tanpa langkah ini pembaca lain (pandas, openpyxl data_only, audit) melihat None.
Hanya di Windows dengan Excel terpasang. Excel dibuka tanpa jendela, file ditulis ulang di tempat.

    python -m src.recalc_excel excel/Dashboard_pangan.xlsx
Keluaran JSON: {"status": "success"|"errors_found", "total_formulas", "total_errors", "errors": [{"sheet","cell","value"}...]}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ERROR_CODES = {-2146826281: "#DIV/0!", -2146826246: "#N/A", -2146826259: "#NAME?", -2146826288: "#NULL!",
               -2146826252: "#NUM!", -2146826265: "#REF!", -2146826273: "#VALUE!", -2146826287: "#SPILL!"}


def recalc(path: Path, abaikan_na: bool = True) -> dict:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.ScreenUpdating = False
    errors, n_formula = [], 0
    try:
        wb = xl.Workbooks.Open(str(path.resolve()), UpdateLinks=0, ReadOnly=False)
        xl.CalculateFullRebuild()
        for ws in wb.Worksheets:
            ur = ws.UsedRange
            formulas = ur.Formula
            values = ur.Value
            if not isinstance(formulas, tuple):
                formulas, values = ((formulas,),), ((values,),)
            r0, c0 = ur.Row, ur.Column
            for i, row in enumerate(formulas):
                for j, f in enumerate(row):
                    if isinstance(f, str) and f.startswith("="):
                        n_formula += 1
                        v = values[i][j]
                        if isinstance(v, int) and v in ERROR_CODES:
                            code = ERROR_CODES[v]
                            if abaikan_na and code == "#N/A":
                                continue  # NA() disengaja untuk celah grafik
                            errors.append({"sheet": ws.Name, "cell": ws.Cells(r0 + i, c0 + j).Address(False, False), "value": code})
        wb.Save()
        wb.Close(SaveChanges=False)
    finally:
        xl.Quit()
        pythoncom.CoUninitialize()
    return {"status": "success" if not errors else "errors_found", "total_formulas": n_formula, "total_errors": len(errors), "errors": errors[:100]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path")
    a = p.parse_args()
    try:
        hasil = recalc(Path(a.path))
    except ImportError:
        hasil = {"error": "pywin32 tidak terpasang (pip install pywin32)"}
    except Exception as e:  # COM gagal: Excel tidak ada / file terkunci
        hasil = {"error": str(e)[:300]}
    print(json.dumps(hasil, ensure_ascii=False, indent=1))
    if "error" in hasil:
        sys.exit(1)


if __name__ == "__main__":
    main()
