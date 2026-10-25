"""Utilitas bersama untuk skrip analisis Tahap 4."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures"

# Warna (brief §6.4): teal = utama/untung, biru = turun/lebih murah, oranye = naik/peringatan; abu = konteks
TEAL, BLUE, ORANGE, GRAY = "#1baf7a", "#2a78d6", "#eb6834", "#a3a29c"
INK, INK2 = "#0b0b0b", "#52514e"

KOMODITAS_URUT = ["Cabai Rawit Merah", "Cabai Merah Keriting", "Bawang Merah Ukuran Sedang",
                  "Bawang Putih Ukuran Sedang", "Daging Ayam Ras Segar", "Telur Ayam Ras Segar"]
LABEL_PENDEK = {"Cabai Rawit Merah": "Cabai rawit merah", "Cabai Merah Keriting": "Cabai merah keriting",
                "Bawang Merah Ukuran Sedang": "Bawang merah", "Bawang Putih Ukuran Sedang": "Bawang putih",
                "Daging Ayam Ras Segar": "Daging ayam ras", "Telur Ayam Ras Segar": "Telur ayam ras"}


def load_cfg() -> tuple[dict, dict]:
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    lcfg = yaml.safe_load((ROOT / "config" / "biaya_logistik.yaml").read_text(encoding="utf-8"))
    return cfg, lcfg


def load_weekly(cfg: dict, include_excluded: bool = False) -> pd.DataFrame:
    w = pd.read_parquet(ROOT / cfg["paths"]["interim"] / "harga_mingguan.parquet")
    return w if include_excluded else w[~w.is_seri_dikecualikan].copy()


def save_table(df: pd.DataFrame, name: str) -> Path:
    TABLES.mkdir(parents=True, exist_ok=True)
    p = TABLES / f"{name}.csv"
    df.to_csv(p, index=False)
    return p


def style() -> None:
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.edgecolor": GRAY, "axes.labelcolor": INK2, "xtick.color": INK2,
        "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "figure.dpi": 120, "figure.facecolor": "white",
        "savefig.bbox": "tight",
    })


def save_fig(fig, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    p = FIGURES / f"{name}.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def rp(v: float) -> str:
    return f"Rp {v:,.0f}".replace(",", ".")


def pct(v: float, d: int = 0) -> str:
    return f"{v * 100:.{d}f}%".replace(".", ",")
