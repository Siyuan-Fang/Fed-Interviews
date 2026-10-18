#!/usr/bin/env python3
"""Generate Table 1 summary statistics from the committed matched files."""

from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MATCHED_DIR = PACKAGE_ROOT / "Data" / "common" / "matched"
OUTPUT_DIR = PACKAGE_ROOT / "Tables" / "table1"

EVENTS = [
    ("fomc_announcement", "FOMC announcements"),
    ("baha_powell_79", "Chair speeches"),
    ("interviews_top100", "Interviews (Top 100)"),
    ("interviews_top200", "Interviews (Top 200)"),
    ("minutes", "Minutes"),
]
ASSETS = ["ED2", "ED4", "SP500"]
METRICS = ["std", "min", "max", "mean"]


def read_changes(event_key: str, asset: str) -> pd.Series:
    path = MATCHED_DIR / f"{event_key}{asset}.csv"
    df = pd.read_csv(path)
    return pd.to_numeric(df["change"], errors="coerce").dropna() * 10000


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    event_keys = [key for key, _ in EVENTS]
    event_labels = [label for _, label in EVENTS]

    data = {
        event_key: {
            asset: read_changes(event_key, asset)
            for asset in ASSETS
        }
        for event_key in event_keys
    }

    rows = []

    counts = [len(data[event_key]["ED2"]) for event_key in event_keys]
    rows.append({"Metric": "Number", "Asset": "", **dict(zip(event_labels, counts))})

    for metric in METRICS:
        for asset in ASSETS:
            values = [
                getattr(data[event_key][asset], metric)()
                for event_key in event_keys
            ]
            rows.append(
                {"Metric": metric.capitalize(), "Asset": asset, **dict(zip(event_labels, values))}
            )

    table = pd.DataFrame(rows)
    table.to_csv(OUTPUT_DIR / "table1.csv", index=False)

    md_lines = [
        "# Table 1",
        "",
        "Interest rates are in basis points. SP500 is 10000 times the log change.",
        "",
        "| Metric | Asset | " + " | ".join(event_labels) + " |",
        "|---|:---|" + "---:|" * len(event_labels),
    ]
    for _, row in table.iterrows():
        values = []
        for label in event_labels:
            value = row[label]
            values.append(f"{value:.2f}" if row["Metric"] != "Number" else f"{int(value)}")
        md_lines.append(
            f"| {row['Metric']} | {row['Asset']} | " + " | ".join(values) + " |"
        )

    (OUTPUT_DIR / "table1.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_DIR / 'table1.csv'}")
    print(f"wrote {OUTPUT_DIR / 'table1.md'}")


if __name__ == "__main__":
    main()
