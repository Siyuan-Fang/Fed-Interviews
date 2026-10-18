#!/usr/bin/env python
"""Reproduce Figure 1: histograms of announcement effects."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MATCHED_DIR = PACKAGE_ROOT / "Data" / "common" / "matched"
OUTPUT_DIR = PACKAGE_ROOT / "Figures" / "figure1"

ASSETS = ["ED2", "ED4", "SP500"]
EVENTS = [
    ("fomc_announcement", "FOMC Announcement effects"),
    ("baha_powell_79", "Fed Chair effects"),
    ("interviews_top100", "Fed Presidents effects(100)"),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data_list = []
    titles = []
    for asset in ASSETS:
        for event_key, event_title in EVENTS:
            path = MATCHED_DIR / f"{event_key}{asset}.csv"
            matched = pd.read_csv(path)
            data_list.append(pd.to_numeric(matched["change"], errors="coerce").dropna() * 100)
            titles.append(f"{event_title}, {asset}")

    fig, axes = plt.subplots(3, 3, figsize=(9, 10), tight_layout=True)
    for index, ax in enumerate(axes.flat):
        ax.hist(data_list[index], bins=15, color="skyblue", edgecolor="black")
        ax.set_title(titles[index])
        ax.set_xlim(-0.2, 0.2) if index < 6 else ax.set_xlim(-2, 2)

    output = OUTPUT_DIR / "figure1.png"
    fig.savefig(output, dpi=100)
    plt.close(fig)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
