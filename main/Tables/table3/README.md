# Table 3 Panel A

Panel A reports the effect of a one-standard-deviation forward-guidance change
on ED2, ED3, ED4, and SP500.

## Outputs

- [`table3_panel_a.csv`](table3_panel_a.csv)
- [`table3_panel_a.md`](table3_panel_a.md)

## How it is generated

```text
Data/table3/reg_*.csv
    +
Data/table3/factor_*.csv
    |
    v
Code/table3/03_estimate_table3_panel_a.py
    |
    v
Tables/table3/table3_panel_a.{csv,md}
```

Standard errors are HC0 heteroskedasticity-consistent standard errors.
