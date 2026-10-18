# Data

Shared inputs live under `Data/common/`. Table- or figure-specific data that is
not shared can live under `Data/<id>/`.

## Raw vs committed data

- Committed data should be small, cleaned, and sufficient to reproduce the
  corresponding table or figure.
- Large raw files should not be committed to GitHub. Document where they came
  from and how to obtain them in the relevant `Data/<id>/README.md`.
- Each artifact directory should explain its upstream lineage: which raw data
  and which script produced the committed files.

## Current data

| Artifact | Directory | Description |
|---|---|---|
| Shared inputs | [`common/`](common/) | Event lists, raw futures, matched intraday windows, and macro-release auxiliary data |
| Table 2 | [`table2/`](table2/) | Table-2-specific monthly absolute-change totals |
| Table 3 | [`table3/`](table3/) | Table-3-specific regression inputs and forward-guidance factors |
| Figure 3 | [`figure3/`](figure3/) | FOMC regression input for the MATLAB shock estimation, plus its output |
| Figures 4–6 | [`figure4_6/`](figure4_6/) | Chair-speech and interview regression inputs, plus estimation output |

The shared raw futures files are copied into `common/raw/`, but are ignored by
Git. They are expected in:

```text
Data/common/raw/
├── ED2.csv
├── ED3.csv
├── ED4.csv
└── SP500.csv
```
