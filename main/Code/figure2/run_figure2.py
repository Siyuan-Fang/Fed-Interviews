#!/usr/bin/env python
"""Reproduce Figure 2: rolling importance by announcement type."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PACKAGE_ROOT / "Data" / "table2" / "overtime_sum_variance.csv"
OUTPUT_DIR = PACKAGE_ROOT / "Figures" / "figure2"

ASSETS = ["ED2.csv", "ED3.csv", "ED4.csv", "SP500.csv"]
EVENT_COLUMNS = [
    "fomc_announcement",
    "baha_powell_79",
    "interviews_top100",
    "interviews_top200",
    "minutes_",
]
PLOT_NAMES = [
    "FOMC Announcements",
    "Fed Chair Speeches",
    "Interviews(Top100)",
    "Interviews(Top200)",
    "Minutes",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(INPUT_FILE)

    for source, target in zip(EVENT_COLUMNS, PLOT_NAMES):
        data[target] = data[source]

    fig, axes = plt.subplots(2, 2, figsize=(9, 10), tight_layout=True)

    for index, ax in enumerate(axes.flat):
        asset_data = data[data["ED"] == ASSETS[index]].copy()
        asset_data["Datetime"] = pd.to_datetime(
            asset_data["mouthfomc_announcement"]
        )

        for name in PLOT_NAMES:
            asset_data[f"rolling_{name}"] = (
                asset_data[[name]].rolling(window=6).sum()
            )
            ax.plot(
                asset_data["Datetime"],
                asset_data[f"rolling_{name}"],
                label=name,
            )

        ax.set_title(ASSETS[index][:-4])
        if index == 0:
            ax.legend()

    output = OUTPUT_DIR / "figure2.png"
    fig.savefig(output, dpi=100)
    plt.close(fig)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
