"""Assemble the interview dataset from the calendar export and the clip shortlist.

For each scheduled appearance: identify the speaker, the programme on air and its
start time, then attach the YouTube clip of the appearance where one exists.

Usage: python build_dataset.py CALENDAR.xlsx [CLIPS.csv] [-o OUT.xlsx]
"""

import argparse
from pathlib import Path

import pandas as pd

from roster import speaker_of
from schedules import programme

EASTERN = "US/Eastern"

# Days either side of the scheduled appearance in which a clip is still a candidate.
MATCH_WINDOW = 1

# The calendar export labels outlets inconsistently across vintages.
MEDIA_ALIASES = {"Bloomberg": "BLOOMBERG", "Fox": "FBC", "FBN": "FBC"}

CLIP_COLS = ["upload_date_utc", "speaker", "media", "title", "url", "duration", "view_count"]

COLUMNS = [
    "Datetime", "Datetime_UTC", "Country Code", "Index", "Media", "Programmes",
    "Event", "Person", "Programme_Start_UTC", *CLIP_COLS,
]


def _naive_utc(values):
    """Parse to UTC and drop the offset, so calendar and clip times subtract cleanly."""
    return pd.to_datetime(values, utc=True, errors="coerce").dt.tz_localize(None)


def add_programme_columns(df):
    eastern = df["Datetime_UTC"].dt.tz_localize("UTC").dt.tz_convert(EASTERN)
    df["Programmes"] = [programme(m, t) for m, t in zip(df["Media"], eastern)]
    df["Programme_Start_UTC"] = df["Datetime_UTC"].dt.floor("h")
    return df


def match_clip(row, clips):
    """The clip by this speaker on this outlet closest to the appointment, or None."""
    gap = (clips["upload_date_utc"] - row["Datetime_UTC"]).abs()
    hits = clips[
        (clips["outlet"] == row["Media"])
        & (clips["speaker"] == row["Person"])
        & (gap <= pd.Timedelta(days=MATCH_WINDOW))
    ]
    if hits.empty:
        return None

    best = hits.loc[gap.loc[hits.index].idxmin()]
    return {
        "upload_date_utc": best["upload_date_utc"],
        "speaker": best["speaker"],
        "media": row["Media"],
        "title": best["title"],
        "url": best["url"],
        "duration": best["duration"],
        "view_count": best["view_count"],
    }


def build(calendar_path, clips_path):
    df = pd.read_excel(calendar_path)
    df["Datetime_UTC"] = pd.to_datetime(df["Datetime_UTC"])
    df["Media"] = df["Media"].replace(MEDIA_ALIASES)
    print(f"calendar: {len(df)} scheduled appearances")

    df["Person"] = df["Event"].map(speaker_of)
    unnamed = df["Person"].isna().sum()
    if unnamed:
        print(f"  ! {unnamed} rows name no roster official")

    df = add_programme_columns(df)
    print(f"programmes: {df['Programmes'].notna().sum()} rows fall in a scheduled slot")

    clips = pd.read_csv(clips_path)
    clips["upload_date_utc"] = _naive_utc(clips["upload_date_utc"])
    matches = pd.DataFrame(
        [match_clip(row, clips) or {} for _, row in df.iterrows()],
        index=df.index, columns=CLIP_COLS,
    )
    df = pd.concat([df.drop(columns=CLIP_COLS, errors="ignore"), matches], axis=1)
    print(f"clips: {df['url'].notna().sum()} of {len(df)} appearances matched")

    return df.reindex(columns=COLUMNS)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("calendar", type=Path, help="calendar export (.xlsx)")
    p.add_argument("clips", type=Path, nargs="?", default=Path("clip_candidates.csv"))
    p.add_argument("-o", "--out", type=Path, default=Path("data_summary_5_media.xlsx"))
    args = p.parse_args()

    df = build(args.calendar, args.clips)
    df.to_excel(args.out, index=False)
    print(f"wrote {args.out} ({len(df)} rows x {len(df.columns)} cols)")


if __name__ == "__main__":
    main()
