#!/usr/bin/env python3
"""Regenerate the Table 1 matched event-window files."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PACKAGE_ROOT / "Data" / "common"
EVENTS_DIR = DATA_DIR / "events"
RAW_DIR = DATA_DIR / "raw"
AUX_DIR = DATA_DIR / "auxiliary"
OUTPUT_DIR = Path(
    os.environ.get(
        "MATCHED_OUT_DIR",
        DATA_DIR / "matched",
    )
)

ASSETS = ["ED2", "ED3", "ED4", "SP500"]

EVENT_CONFIGS = [
    {
        "name": "fomc_announcement",
        "file": "fomc_announcement.csv",
        "time_col": "Time",
        "title_col": "Event",
        "timezone": "Asia/Shanghai",
        "before": 10,
        "after": 20,
        "start_price": "open",
    },
    {
        "name": "baha_powell_79",
        "file": "baha_powell_79.csv",
        "time_col": "Time",
        "title_col": "Event",
        "timezone": "Asia/Shanghai",
        "before": 15,
        "after": 75,
        "start_price": "close",
    },
    {
        "name": "interviews_top100",
        "file": "interviews_top100.csv",
        "time_col": "Publish_Times",
        "title_col": "title",
        "timezone": None,
        "before": 15,
        "after": 75,
        "start_price": "close",
    },
    {
        "name": "interviews_top200",
        "file": "interviews_top200.csv",
        "time_col": "Publish_Times",
        "title_col": "title",
        "timezone": None,
        "before": 15,
        "after": 75,
        "start_price": "close",
    },
    {
        "name": "minutes",
        "file": "minutes.csv",
        "time_col": "Time",
        "title_col": "Event",
        "timezone": "Asia/Shanghai",
        "before": 10,
        "after": 50,
        "start_price": "close",
    },
]


def load_events(config: dict) -> pd.DataFrame:
    path = EVENTS_DIR / config["file"]
    df = pd.read_csv(path)

    if config["timezone"]:
        times = pd.to_datetime(df[config["time_col"]], format="%Y-%m-%d %H:%M:%S")
        times = times.dt.tz_localize(config["timezone"]).dt.tz_convert("UTC")
    else:
        times = pd.to_datetime(
            df[config["time_col"]], utc=True, format="%Y-%m-%d %H:%M:%S%z"
        )

    df["Publish_Times"] = times
    return df.dropna(subset=["Publish_Times"]).sort_values("Publish_Times").reset_index(drop=True)


def load_macro_releases() -> pd.Series:
    path = AUX_DIR / "macro_data_release_clean.csv"
    macro = pd.read_csv(path)
    times = pd.to_datetime(macro["Time"], format="%Y-%m-%d %H:%M:%S")
    times = times.dt.tz_localize("Asia/Shanghai").dt.tz_convert("UTC")
    return times.dropna().sort_values().reset_index(drop=True)


def load_futures(asset: str) -> pd.DataFrame:
    path = RAW_DIR / f"{asset}.csv"
    futures = pd.read_csv(path)
    futures["Datetime"] = pd.to_datetime(
        futures["ts_event"], utc=True, format="%Y-%m-%d %H:%M:%S%z"
    )
    return futures[["Datetime", "open", "close"]].sort_values("Datetime")


def build_after_times(
    event_times: pd.Series, macro_releases: pd.Series, after_minutes: int
) -> pd.Series:
    values = []
    for time in event_times:
        end_time = time + timedelta(minutes=after_minutes)
        overlapping = macro_releases[(macro_releases >= time) & (macro_releases <= end_time)]
        values.append(overlapping.min() if not overlapping.empty else end_time)
    return pd.to_datetime(pd.Series(values, index=event_times.index), utc=True)


def generate(config: dict, asset: str, macro_releases: pd.Series) -> pd.DataFrame:
    events = load_events(config)
    futures = load_futures(asset)

    events["15bf"] = events["Publish_Times"] - timedelta(minutes=config["before"])
    events["75aft"] = build_after_times(events["Publish_Times"], macro_releases, config["after"])

    before = pd.merge_asof(
        events,
        futures,
        left_on="15bf",
        right_on="Datetime",
        direction="nearest",
    )
    after = pd.merge_asof(
        events,
        futures.rename(columns={"Datetime": "Datetime2", "open": "open2", "close": "close2"}),
        left_on="75aft",
        right_on="Datetime2",
        direction="nearest",
    )

    out = pd.DataFrame(
        {
            "15bf": events["15bf"],
            "Datetime": before["Datetime"],
            "CLOSE": before[config["start_price"]],
            "75aft": events["75aft"],
            "Datetime2": after["Datetime2"],
            "CLOSE2": after["close2"],
            "Publish_Times": events["Publish_Times"],
            "title": events[config["title_col"]],
        }
    )
    out["change"] = np.log(out["CLOSE2"]) - np.log(out["CLOSE"])
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    macro_releases = load_macro_releases()

    for config in EVENT_CONFIGS:
        for asset in ASSETS:
            matched = generate(config, asset, macro_releases)
            output = OUTPUT_DIR / f"{config['name']}{asset}.csv"
            matched.to_csv(output, index=False, encoding="utf-8-sig")
            print(f"wrote {output} ({len(matched)} rows)")


if __name__ == "__main__":
    main()
