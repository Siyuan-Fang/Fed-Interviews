# Table 2 Code

## Script

`run_table2.py` reads:

- `Data/table2/overtime_sum_variance.csv` for Panel A totals;
- `Data/common/matched/` for the filtered event counts used in Panel B.

It writes Table 2.

```bash
python3 Code/table2/run_table2.py
```

Outputs:

- `Tables/table2/table2.csv`
- `Tables/table2/table2.md`

## Calculation

- Panel A: `sum(abs(change)) * 100`, reported in percentage points.
- Panel B: `sum(abs(change)) / N * 10000`, reported in basis points.
- Sample filter: `2019-01-01` through `2024-07-31`.
