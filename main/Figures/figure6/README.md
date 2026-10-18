# Figure 6

Figure 6 shows Fed Interviews Top 200 responses to two standardized shocks:

- Pure forward guidance
- Information forward guidance

## Output

- [`figure6_full.png`](figure6_full.png)

The paper crops this full figure into the two shock panels with LaTeX
`\adjustbox{trim=...}`.

## How it is generated

Run in MATLAB from the package root:

```matlab
addpath('Code/figure4_6')
run_figures_4_5_6(6)
```

## Inputs

- [`Data/figure4_6/reg_interviews_top200.csv`](../../Data/figure4_6/reg_interviews_top200.csv) — 200 announcement-window observations
- Code: [`Code/figure4_6/run_figures_4_5_6.m`](../../Code/figure4_6/run_figures_4_5_6.m),
  [`Code/figure4_6/private/plot_resp.m`](../../Code/figure4_6/private/plot_resp.m)
- Shared MATLAB helpers: [`Code/common/matlab/`](../../Code/common/matlab/)

Only the `TFUT02` and `SP500` columns are used, so the model has two shocks.

## Also written

- `Data/figure4_6/figure6_maxl.mat` — estimated `C`, `W`, `U`, shocks, and variance decomposition

Estimation is deterministic (the starting point is `inv(chol(cov(Y)))` with no
random perturbation), so repeated runs reproduce the figure exactly.
