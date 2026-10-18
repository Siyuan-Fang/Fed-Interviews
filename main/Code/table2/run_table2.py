#!/usr/bin/env python3
"""Generate Table 2 from shared matched event-window files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MATCHED_DIR = PACKAGE_ROOT / "Data" / "common" / "matched"
OVERTIME_PATH = PACKAGE_ROOT / "Data" / "table2" / "overtime_sum_variance.csv"
OUTPUT_DIR = PACKAGE_ROOT / "Tables" / "table2"

EVENTS = [
    ("fomc_announcement", "fomc_announcement", "FOMC announcements"),
    ("baha_powell_79", "baha_powell_79", "Chair speeches"),
    ("interviews_top100", "interviews_top100", "Interviews (Top 100)"),
    ("interviews_top200", "interviews_top200", "Interviews (Top 200)"),
    ("minutes", "minutes_", "Minutes"),
]
ASSETS = ["ED2", "ED3", "ED4", "SP500"]

START_DATE = pd.Timestamp("2019-01-01", tz="UTC")
END_DATE = pd.Timestamp("2024-07-31 23:59:59", tz="UTC")


def load_filtered_count(event_key: str, asset: str) -> int:
    path = MATCHED_DIR / f"{event_key}{asset}.csv"
    df = pd.read_csv(path)
    times = pd.to_datetime(df["Publish_Times"], utc=True)
    changes = pd.to_numeric(df["change"], errors="coerce")
    mask = (times >= START_DATE) & (times <= END_DATE)
    return int(changes[mask].notna().sum())


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    overtime = pd.read_csv(OVERTIME_PATH)
    rows = []

    for event_key, overtime_col, event_label in EVENTS:
        panel_a = {}
        panel_b = {}
        for asset in ASSETS:
            overtime_subset = overtime[overtime["ED"] == f"{asset}.csv"]
            sum_abs = pd.to_numeric(
                overtime_subset[overtime_col], errors="coerce"
            ).sum()
            count = load_filtered_count(event_key, asset)
            panel_a[asset] = sum_abs * 100
            panel_b[asset] = sum_abs / count * 10000 if count else float("nan")

        rows.append(
            {"Panel": "A", "Event": event_label, **panel_a}
        )
        rows.append(
            {"Panel": "B", "Event": event_label, **panel_b}
        )

    table = pd.DataFrame(rows)
    table.to_csv(OUTPUT_DIR / "table2.csv", index=False)

    md_lines = [
        "# Table 2",
        "",
        "Panel A is the sum of absolute changes in percentage points.",
        "Panel B is the mean absolute change per announcement in basis points.",
        "",
        "| Panel | Event | ED2 | ED3 | ED4 | SP500 |",
        "|:---:|---|---:|---:|---:|---:|",
    ]
    for _, row in table.iterrows():
        values = [f"{row[asset]:.2f}" for asset in ASSETS]
        md_lines.append(
            f"| {row['Panel']} | {row['Event']} | " + " | ".join(values) + " |"
        )

    (OUTPUT_DIR / "table2.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_DIR / 'table2.csv'}")
    print(f"wrote {OUTPUT_DIR / 'table2.md'}")


if __name__ == "__main__":
    main()
