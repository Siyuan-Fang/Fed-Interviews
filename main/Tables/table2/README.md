# Table 2

Table 2 reports two importance measures for five monetary policy announcement
types:

- Panel A: sum of absolute changes in percentage points.
- Panel B: mean absolute change per announcement in basis points.

## Outputs

- [`table2.csv`](table2.csv): full-precision table.
- [`table2.md`](table2.md): readable Markdown version.

## How it is generated

```text
Data/table2/overtime_sum_variance.csv
    +
Data/common/matched/*.csv
    |
    v
Code/table2/run_table2.py
    |
    v
Tables/table2/table2.{csv,md}
```

The sample is restricted to `2019-01-01` through `2024-07-31`.
