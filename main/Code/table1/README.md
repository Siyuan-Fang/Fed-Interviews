# Table 1 Code

## Scripts

| Script | Purpose |
|---|---|
| `generate_matched.py` | Regenerate the 20 matched event-window files from raw data |
| `run_table1.py` | Compute Table 1 from the matched files |

## Run order

To regenerate the matched files and then compute Table 1:

```bash
python3 Code/table1/generate_matched.py
python3 Code/table1/run_table1.py
```

If the matched files already exist and only the table is needed:

```bash
python3 Code/table1/run_table1.py
```

Outputs:

- `Tables/table1/table1.csv`
- `Tables/table1/table1.md`

`generate_matched.py` reads:

- `Data/common/events/`
- `Data/common/raw/ED2.csv`
- `Data/common/raw/ED3.csv`
- `Data/common/raw/ED4.csv`
- `Data/common/raw/SP500.csv`
- `Data/common/auxiliary/macro_data_release_clean.csv`

and writes to `Data/common/matched/`.

## Event windows

| Event type | Before | After |
|---|---:|---:|
| FOMC announcements | 10 minutes | 20 minutes |
| Fed Chair speeches | 15 minutes | 75 minutes |
| Fed Presidents interviews | 15 minutes | 75 minutes |
| FOMC minutes | 10 minutes | 50 minutes |

When a macro data release overlaps the end of the event window, the end point
is moved to the first overlapping macro release time.

## Dependencies

- Python 3
- pandas
- numpy
