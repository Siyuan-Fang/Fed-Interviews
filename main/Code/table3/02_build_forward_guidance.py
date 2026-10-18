#!/usr/bin/env python3
"""Build standardized forward-guidance factors for Table 3."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PACKAGE_ROOT / "Data" / "table3"
OUTPUT_DIR = INPUT_DIR

EVENTS = [
    "fomc_announcement",
    "baha_powell_79",
    "interviews_top100",
    "interviews_top200",
    "minutes",
]
PCA_VARIABLES = ["ED2", "ED3", "ED4"]


def ols_beta(y: np.ndarray, factor: np.ndarray) -> float:
    design = np.column_stack([np.ones(len(y)), factor])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    return float(beta[1])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for event in EVENTS:
        data = pd.read_csv(INPUT_DIR / f"reg_{event}.csv")
        pca_data = data[PCA_VARIABLES].dropna()
        values = pca_data.to_numpy(dtype=float)

        centered = values - values.mean(axis=0)
        scaled = centered / values.std(axis=0, ddof=1)
        _, _, vh = np.linalg.svd(scaled, full_matrices=False)
        first_pc = scaled @ vh[0]
        factor = first_pc / first_pc.std(ddof=1)

        ed2 = pca_data["ED2"].to_numpy(dtype=float)
        if ols_beta(ed2, factor) < 0:
            factor = -factor

        output = pd.DataFrame(
            {
                "date": pca_data.index.to_series().map(data["date"]).values,
                "factor": factor,
            }
        )
        output.to_csv(OUTPUT_DIR / f"factor_{event}.csv", index=False)
        print(f"wrote {event}: {len(output)} observations")


if __name__ == "__main__":
    main()
