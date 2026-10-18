#!/usr/bin/env python3
"""Prepare Table 3 regression inputs from shared matched files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MATCHED_DIR = PACKAGE_ROOT / "Data" / "common" / "matched"
OUTPUT_DIR = PACKAGE_ROOT / "Data" / "table3"

EVENTS = [
    "fomc_announcement",
    "baha_powell_79",
    "interviews_top100",
    "interviews_top200",
    "minutes",
]
ASSETS = ["ED2", "ED3", "ED4", "SP500"]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for event in EVENTS:
        first = pd.read_csv(MATCHED_DIR / f"{event}ED2.csv")
        data = pd.DataFrame(
            {
                "date": pd.to_datetime(first["Publish_Times"], utc=True),
                "ED2": pd.to_numeric(first["change"], errors="coerce"),
            }
        )

        for asset in ASSETS[1:]:
            matched = pd.read_csv(MATCHED_DIR / f"{event}{asset}.csv")
            data[asset] = pd.to_numeric(matched["change"], errors="coerce").to_numpy()

        data = data.sort_values("date").reset_index(drop=True)
        data["date"] = data["date"].dt.strftime("%Y-%m-%d")
        output = OUTPUT_DIR / f"reg_{event}.csv"
        data.to_csv(output, index=False)
        print(f"wrote {output.relative_to(PACKAGE_ROOT)} ({len(data)} rows)")


if __name__ == "__main__":
    main()
