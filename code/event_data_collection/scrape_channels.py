"""Scrape video metadata from each network's YouTube channel.

Writes one CSV per outlet: title, url, upload_date, duration, view_count.
Usage: python scrape_channels.py [outdir]
"""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp

CHANNELS = {
    "BLOOMBERG": "https://www.youtube.com/@markets",
    "CNBC": "https://www.youtube.com/@CNBCtelevision",
    "FBC": "https://www.youtube.com/@FoxBusiness",
    "CNN": "https://www.youtube.com/@CNN",
    "Yahoo": "https://www.youtube.com/@YahooFinance",
}

CSV_NAMES = {
    "BLOOMBERG": "bloomberg_videos.csv",
    "CNBC": "cnbc_videos.csv",
    "FBC": "fox_business_videos.csv",
    "CNN": "cnn_videos.csv",
    "Yahoo": "yahoo_finance_videos.csv",
}

FIELDS = ["title", "url", "upload_date", "duration", "view_count"]

YDL_OPTS = {
    "extract_flat": True,
    "ignoreerrors": True,
    "quiet": True,
    "no_warnings": True,
    "retries": 3,
}


def scrape(channel_url):
    """Yield one metadata dict per video on the channel's videos and streams tabs."""
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        for tab in ("videos", "streams"):
            info = ydl.extract_info(f"{channel_url}/{tab}", download=False)
            for entry in (info or {}).get("entries") or []:
                if not entry or not entry.get("id"):
                    continue
                yield {
                    "title": entry.get("title"),
                    "url": f"https://www.youtube.com/watch?v={entry['id']}",
                    "upload_date": _upload_date(entry),
                    "duration": entry.get("duration"),
                    "view_count": entry.get("view_count"),
                }


def _upload_date(entry):
    """Normalise to YYYY-MM-DD; flat extraction often gives a timestamp only."""
    if entry.get("timestamp"):
        return datetime.fromtimestamp(entry["timestamp"], timezone.utc).strftime("%Y-%m-%d")
    raw = entry.get("upload_date")
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}" if raw and len(raw) == 8 else None


def main(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for outlet, url in CHANNELS.items():
        rows = list(scrape(url))
        path = outdir / CSV_NAMES[outlet]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{outlet:<10} {len(rows):>6} videos -> {path}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "../../data"))
