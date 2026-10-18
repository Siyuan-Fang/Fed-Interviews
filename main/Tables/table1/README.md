# Table 1

Table 1 reports summary statistics for five monetary policy announcement types:
FOMC announcements, Fed Chair speeches, Fed Presidents interviews top 100 and
top 200, and FOMC minutes.

## Outputs

- [`table1.csv`](table1.csv): paper-style wide table.
- [`table1.md`](table1.md): readable Markdown version.

## How it is generated

```text
Data/common/matched/*.csv
    |
    v
Code/table1/run_table1.py
    |
    v
Tables/table1/table1.{csv,md}
```

ED2 and ED4 changes are in basis points. SP500 changes are 10000 times the log
change, as described in the paper.
