"""Reduce the channel scrapes to clips that name a Fed official, with exact timestamps.

The flat channel scrape returns no upload date, so each shortlisted clip is queried
individually. Shortlisting first keeps that to a few hundred requests.

Usage: python shortlist_clips.py [datadir] [-o OUT.csv]
"""

import argparse
import time
from pathlib import Path

import pandas as pd
import yt_dlp

from roster import speaker_of
from scrape_channels import CSV_NAMES

FIELDS = ["outlet", "speaker", "title", "url", "upload_date_utc", "duration", "view_count"]

REQUEST_PAUSE = 1.0


def shortlist(datadir):
    """Clips whose title names a roster official, one row per clip."""
    frames = []
    for outlet, name in CSV_NAMES.items():
        path = datadir / name
        if not path.exists():
            print(f"  ! missing {path.name}")
            continue
        clips = pd.read_csv(path)
        clips["speaker"] = clips["title"].map(speaker_of)
        hits = clips[clips["speaker"].notna()].assign(outlet=outlet)
        print(f"{outlet:<10} {len(hits):>5} of {len(clips):>7} titles name an official")
        frames.append(hits)
    return pd.concat(frames, ignore_index=True).drop_duplicates("url")


def upload_time(url, ydl):
    """Exact upload timestamp in UTC, or None if the clip is gone or private."""
    try:
        info = ydl.extract_info(url, download=False)
    except Exception as exc:
        print(f"  ! {url}: {str(exc)[:70]}")
        return None
    if not info or not info.get("timestamp"):
        return None
    return pd.to_datetime(info["timestamp"], unit="s", utc=True).tz_localize(None)


def resolve_dates(clips):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        stamps = []
        for i, url in enumerate(clips["url"], 1):
            stamps.append(upload_time(url, ydl))
            if i % 25 == 0:
                print(f"  resolved {i}/{len(clips)}")
            time.sleep(REQUEST_PAUSE)
    return clips.assign(upload_date_utc=stamps)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("datadir", type=Path, nargs="?", default=Path("../../data"))
    p.add_argument("-o", "--out", type=Path, default=Path("clip_candidates.csv"))
    args = p.parse_args()

    clips = shortlist(args.datadir)
    print(f"shortlist: {len(clips)} clips; resolving upload dates")
    clips = resolve_dates(clips)

    resolved = clips.dropna(subset=["upload_date_utc"])
    resolved[FIELDS].to_csv(args.out, index=False)
    print(f"wrote {args.out} ({len(resolved)} of {len(clips)} clips dated)")


if __name__ == "__main__":
    main()
