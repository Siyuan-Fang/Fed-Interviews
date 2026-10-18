#!/usr/bin/env python3
"""Estimate Table 3 Panel A with HC0 robust standard errors."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PACKAGE_ROOT / "Data" / "table3"
OUTPUT_DIR = PACKAGE_ROOT / "Tables" / "table3"

EVENTS = [
    ("fomc_announcement", "FOMC announcements"),
    ("baha_powell_79", "Chair speeches"),
    ("interviews_top100", "Interviews (Top 100)"),
    ("interviews_top200", "Interviews (Top 200)"),
    ("minutes", "Minutes"),
]
ASSETS = ["ED2", "ED3", "ED4", "SP500"]


def ols_hc0(y: np.ndarray, factor: np.ndarray) -> tuple[float, float]:
    design = np.column_stack([np.ones(len(y)), factor])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    residuals = y - design @ beta
    inverse_xtx = np.linalg.inv(design.T @ design)
    meat = design.T @ np.diag(residuals**2) @ design
    covariance = inverse_xtx @ meat @ inverse_xtx
    return float(beta[1]), float(np.sqrt(covariance[1, 1]))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    for event_key, event_label in EVENTS:
        data = pd.read_csv(DATA_DIR / f"reg_{event_key}.csv")
        factor = pd.read_csv(DATA_DIR / f"factor_{event_key}.csv")["factor"].to_numpy()

        for asset in ASSETS:
            values = data[asset].to_numpy(dtype=float)
            coefficient, standard_error = ols_hc0(values, factor)
            records.append(
                {
                    "event": event_label,
                    "asset": asset,
                    "coefficient": coefficient * 10000,
                    "standard_error": standard_error * 10000,
                }
            )

    table = pd.DataFrame(records)
    table.to_csv(OUTPUT_DIR / "table3_panel_a.csv", index=False)

    md_lines = [
        "# Table 3 Panel A",
        "",
        "Coefficients and HC0 standard errors are reported in basis points per",
        "one-standard-deviation forward-guidance factor.",
        "",
        "| Event | ED2 | ED3 | ED4 | SP500 |",
        "|---|---:|---:|---:|---:|",
    ]
    for event_key, event_label in EVENTS:
        cells = []
        for asset in ASSETS:
            row = table[
                (table["event"] == event_label) & (table["asset"] == asset)
            ].iloc[0]
            cells.append(
                f"{row['coefficient']:.2f}<br>({row['standard_error']:.2f})"
            )
        md_lines.append(f"| {event_label} | " + " | ".join(cells) + " |")

    (OUTPUT_DIR / "table3_panel_a.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUTPUT_DIR / 'table3_panel_a.csv'}")
    print(f"wrote {OUTPUT_DIR / 'table3_panel_a.md'}")


if __name__ == "__main__":
    main()
