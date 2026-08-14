# Raw data collection

Builds the sample of Fed officials' financial-television appearances: 180 scheduled
appearances across five outlets (Bloomberg, CNBC, Fox Business, CNN, Yahoo Finance),
each annotated with the programme on air and, where available, the YouTube clip.

## Input

`CALENDAR.xlsx` — an economic-calendar export filtered to Fed-official media
appearances, with columns `Datetime`, `Datetime_UTC`, `Country Code`, `Index`,
`Media`, `Event`. This is licensed vendor data and is not redistributed here; it is
the one input the code cannot regenerate.

## Steps

```bash
pip install -r requirements.txt

python scrape_channels.py ../../data          # 1. channel video metadata -> one CSV per outlet
python shortlist_clips.py ../../data          # 2. filter to Fed clips, resolve upload times
python build_dataset.py CALENDAR.xlsx        # 3. annotate and match -> data_summary_5_media.xlsx
```

Step 1 takes roughly half an hour and returns every video on the five channels. It
cannot return upload dates: YouTube's flat listing omits them. Step 2 therefore keeps
only titles naming an official in `roster.py` and queries those clips individually for
an exact timestamp, which is a few hundred requests rather than a few hundred thousand.

Step 3 assigns each appearance a programme by converting `Datetime_UTC` to US Eastern
and looking it up in the grids in `schedules.py`, sets `Programme_Start_UTC` to the
top of the hour, and attaches the clip by the same speaker on the same outlet whose
upload time is nearest, within one day.

## Files

| File | Role |
| --- | --- |
| `scrape_channels.py` | Channel metadata via yt-dlp |
| `shortlist_clips.py` | Shortlist Fed clips, resolve upload times |
| `build_dataset.py` | Annotate the calendar and match clips |
| `schedules.py` | Programme grids, US Eastern |
| `roster.py` | Officials in the sample |

## Output

180 rows. `Programmes` is populated for 136 appearances; CNN and Yahoo appearances have
no recurring slot and are left blank by design. 123 appearances carry a clip; the rest
had no matching video on the outlet's channel.

## Known departures from the archived file

`data/data_summary_5_media_20251020.xlsx` was assembled with manual steps, so this
rule-based reconstruction does not reproduce it exactly:

- **Programme labels.** The archived file has 146 non-blank labels to this code's 136;
  the extra 10 are Bloomberg appearances falling in gaps between scheduled programmes.
  Its Bloomberg labels are also not internally consistent with any fixed schedule —
  `Bloomberg_The_Close` is attached to appearances at 03:40, 07:30 and 08:00 Eastern,
  and `Bloomberg_Surveillance` to ones at 17:40 and 20:20. Bloomberg's lineup was
  reorganised during the 2018–2025 sample, and these look hand-entered. The grids here
  encode one lineup and leave gaps blank rather than guess.
- **Clip selection.** Nearest-upload-within-a-day recovers 123 of the archived 124
  clips; the remaining one sits more than a day from its scheduled slot.
- **`description`.** Populated for 14 rows in the archived file and not reproduced.
- **`Download_Status` / `Download_Info`.** Written by the separate video-download step,
  not by this pipeline.

Channel handles in `scrape_channels.py` and the matching window in `build_dataset.py`
are the settings most likely to need revisiting.
