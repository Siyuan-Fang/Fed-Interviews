# Table 3 Code

Table 3 code is split into three stages:

| Script | Purpose |
|---|---|
| `01_prepare_reg_inputs.py` | Build `Data/table3/reg_*.csv` from shared matched files |
| `02_build_forward_guidance.py` | Build standardized forward-guidance factors |
| `03_estimate_table3_panel_a.py` | Estimate Panel A with HC0 standard errors |

## Run order

```bash
python3 Code/table3/01_prepare_reg_inputs.py
python3 Code/table3/02_build_forward_guidance.py
python3 Code/table3/03_estimate_table3_panel_a.py
```

## Methodology

- PCA uses only `ED2`, `ED3`, and `ED4`.
- The first principal component is standardized to have unit standard deviation.
- Its sign is oriented so that the ED2 regression coefficient is positive.
- Panel A uses OLS with HC0 heteroskedasticity-consistent standard errors.
